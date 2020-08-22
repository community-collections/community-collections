#!/usr/bin/env python

# Python 2/3 compatabilty and color printer
from __future__ import print_function
from __future__ import unicode_literals

import os
import sys
# import re
import json
# import tempfile
import traceback

from . import stdtools  # noqa
from .stdtools import Handler
from .stdtools import command_check
from .stdtools import bash
# from .stdtools import tracebacker

from .settings import specs
from .settings import cc_user
from .misc import subshell
from .misc import dependency_pathfinder
from .misc import shell_script
# from .misc import path_resolve

# INSTALLATION SCRIPTS

# source environment
script_source_env = """
source %(miniconda_activate)s
conda activate %(envname)s
""" % dict(miniconda_activate=os.path.join(specs['miniconda'],
           specs['conda_activator']), envname=specs['envname'])

# generic build script in temporary space
script_temp_build_base = """
set -e
set -x
# environment here
%(source_env)s
set pipefail
tmpdir=$(mktemp -d)
here=$(pwd)
cd $tmpdir
echo "[STATUS] temporary build directory is $tmpdir"
# build here
%%(script)s
cd $here
rm -rf $tmpdir
"""

# option to build with an environment
script_temp_build = script_temp_build_base % dict(source_env='')
script_temp_build_env = script_temp_build_base % \
    dict(source_env=script_source_env)

# one-liner to add a path without redundancy
bash_env_append = (
    '%(name)s () { if [ -s "$1" ] && '
    '[[ ":$%(var)s:" != *":$1:"* ]]; '
    'then export %(var)s=${%(var)s:+$%(var)s:}$1; fi }')

# installation method for miniconda
install_miniconda = script_temp_build % dict(script="""
wget --progress=bar:force """
"""https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh
bash Miniconda3-latest-Linux-x86_64.sh -b -p %(miniconda_path)s -u
""")

# manage library paths for for miniconda
conda_deactivate_ld_path = """#!/bin/bash
pathremove () {
  local IFS=':'
  local NEWPATH
  local DIR
  local PATHVARIABLE=${2:-PATH}
  for DIR in ${!PATHVARIABLE} ; do
    if [ "$DIR" != "$1" ] ; then
      NEWPATH=${NEWPATH:+$NEWPATH:}$DIR
    fi
  done
  export $PATHVARIABLE="$NEWPATH"
}
pathremove $CONDA_PREFIX/lib LD_LIBRARY_PATH
pathremove $CONDA_PREFIX/lib LD_RUN_PATH
"""

conda_activate_ld_path = """#!/bin/bash
# via https://stackoverflow.com/a/24515432/3313859
append() {
  local var=$1
  local val=$2
  local sep=${3:-":"}
  [[ ${!var} =~ (^|"$sep")"$val"($|"$sep") ]] && return # already present
  [[ ${!var} ]] || { printf -v "$var" '%s' "$val" && return; } # empty
  printf -v "$var" '%s%s%s' "${!var}" "$sep" "${val}" # append
}
# append conda library in two places to avoid absent libtcl error
#! this needs review
append LD_LIBRARY_PATH $CONDA_PREFIX/lib
append LD_RUN_PATH $CONDA_PREFIX/lib
#! the printf above does not export
export LD_LIBRARY_PATH
export LD_RUN_PATH
"""

# generic configure-make script
generic_install = script_temp_build_env % dict(script="""
URL=%(url)s
wget --progress=bar:force $URL
SOURCE_FN=${URL##*/}
DN=$(tar tf $SOURCE_FN | head -1 | cut -f1 -d"/")
tar xf $SOURCE_FN
cd $DN
./configure --prefix=%(prefix)s
make -j
make install
""")

# check for lua packages
lua_check = lambda *x: """
function loadrequire(module)
    local function requiref(module)
        require(module)
    end
    res = pcall(requiref,module)
    if not(res) then
        error("cannot find lua module: " .. module )
    end
end
"""+'\n'.join(['loadrequire(\'%s\')' % i for i in x])

# install singularity 3
script_singularity3_install = """
export VERSION=1.13 OS=linux ARCH=amd64
wget --progress=bar:force https://dl.google.com/go/go$VERSION.$OS-$ARCH.tar.gz
tar xf go$VERSION.$OS-$ARCH.tar.gz --checkpoint=.100 && echo
cd go
export PATH=$(realpath .)/bin:$PATH
export GOPATH=$(pwd)/go
export CC=gcc #! intel causes failures here
mkdir -p $GOPATH/src/github.com/sylabs
cd $GOPATH/src/github.com/sylabs
git clone https://github.com/sylabs/singularity.git
cd $GOPATH/src/github.com/sylabs/singularity
# via: https://github.com/golang/dep/issues/2223
go env -w GO111MODULE=off
go get -u -v github.com/golang/dep/cmd/dep
cd $GOPATH/src/github.com/sylabs/singularity
mkdir -p %(prefix)s
./mconfig --prefix=%(prefix)s
make -C builddir
make -C builddir install
"""

# INSTALLATION MANAGEMENT CLASSES


class CCStack:
    """
    Install minimal stack for running CC.
    Decorate via: `SoftwareStack = Convey(state=state)(SoftwareStack)`
    """
    def start_conda(self):
        """Check if the CC conda environment exists."""
        if not command_check(subshell('conda')) == 0:
            print('status cannot find conda')
            print('status installing miniconda')
            has_worked = self.miniconda()
            if not has_worked:
                raise Exception('failed to install Miniconda')
        else:
            print('status found conda')
        print('status checking conda environments')
        result = bash(subshell('conda env list --json'), scroll=False)
        envs = json.loads(result['stdout'])
        print('status checking for the %s environment' % specs['envname'])
        conda_env_path = os.path.join(
            dependency_pathfinder(
                specs['miniconda']), 'envs', specs['envname'])
        if conda_env_path not in envs.get('envs', []):
            print('status failed to find the %s environment' %
                  specs['envname'])
            print('status building the environment')
            self.conda_env()
            print('status done building the environment')
        else:
            print('status found conda environment: %s' % specs['envname'])

    def miniconda(self):
        """
        Install miniconda from a temporary directory using a script.
        """
        script = (install_miniconda % {'miniconda_path': os.path.realpath(
            os.path.expanduser(dependency_pathfinder(specs['miniconda'])))})
        return shell_script(script)

    def conda_env(self, spec_fn='cc_tools/conda_env.yaml'):
        """
        Install the conda environment.
        """

        # spec_fn_abs = os.path.abspath(os.path.expanduser(spec_fn))
        bash(subshell('conda env create --name %s --file %s' % (
            specs['envname'], spec_fn)))
        env_dn_base = os.path.join(
            specs['miniconda'], 'envs', specs['envname'])
        env_dn_activate = os.path.join(
            env_dn_base, 'etc', 'conda', 'activate.d')
        os.makedirs(env_dn_activate)
        with open(os.path.join(env_dn_activate, 'env_vars.sh'), 'w') as fp:
            fp.write(conda_activate_ld_path)
        env_dn_deactivate = os.path.join(
            env_dn_base, 'etc', 'conda', 'deactivate.d')
        os.makedirs(env_dn_deactivate)
        with open(os.path.join(env_dn_deactivate, 'env_vars.sh'), 'w') as fp:
            fp.write(conda_deactivate_ld_path)

    def which(self):
        if not command_check('which -v') == 0:
            raise Exception('cannot find `which` required for execution')


class LmodManager(Handler):
    """
    Install Lmod and note its location
    """
    CHECK_ROOT = 'NEEDS_LMOD_PATH'
    url_lua = (
        # note that this changed from 5.1.4.8 tar.gz to 5.1.4.9 and bz2
        # changes to these locations can break the installer
        # note that the conda installer is working now, so this is deprecated
        'https://sourceforge.net/projects/lmod/files/lua-5.1.4.9.tar.bz2')
    # get the latest release instead: https://github.com/TACC/Lmod/releases
    url_lmod = 'http://sourceforge.net/projects/lmod/files/Lmod-8.3.tar.bz2'
    ERROR_NOTE = (
        'ERROR. '
        'Remove this note and follow these instructions to continue.')
    ERROR_PATH_ENDS_LMOD = ' The lmod root path must end in "lmod".'
    ERROR_NEEDS_BUILD = (
        'Cannot locate Lmod. Set the `build` key to a '
        'desired installation location, remove this error, and refresh '
        'to continue.')
    ERROR_USER_ROOT_MISSING = (
        'User-defined root path %s cannot be found. '
        'Supply the correct path or use `build` instead of `root` '
        'and refresh to install Lmod at the build location.')
    ERROR_USER_ROOT_FAIL = (
        'User-defined root path %s  '
        'exists but we cannot confirm Lmod works. ')
    STATE_ABSENT = 'absent'
    STATE_CONFIRM = 'needs_confirm'
    lua_reqs = ('posix', 'lfs')
    # account for the removal of the lmod root path here
    lmod_bin_check = './lmod/libexec/lmod help'
    default_local_lmod = './lmod'
    lmod_returncode = 0
    # location for modulefiles to add to the module path
    modulefiles = './modulefiles'

    def _check_lmod_prelim(self, path):
        """Check if spack directory exists."""
        if os.path.isdir(path):
            return self.STATE_CONFIRM
        else:
            return self.STATE_ABSENT

    def _enforce_path(self, build):
        """
        For clarity we enforce a true lmod path.
        The path must end in 'lmod'.
        """
        if not (os.path.basename(
                (build+os.path.sep).rstrip(os.path.sep)) == 'lmod'):
            return False
        # now that we are sure the user has lmod in the path we strip it
        build_dn = os.path.dirname(os.path.realpath(os.path.expanduser(
            (build+os.path.sep).rstrip(os.path.sep))))
        return build_dn

    def _install_lmod(self, path):
        """Installation procedure from Lmod straight from the docs."""
        # we check for lua before installing to the conda environment
        needs_lua = False
        if not command_check('which lua') == 0:
            needs_lua = True
        """
        We previously relied on lua from /usr/bin and included the installation
        instructions below to install the lua associated with an lmod version
        from the source via sourceforge. Now that conda can supply lua without
        issue, this is unnecessary, however we still check for lfs and posix.
        To do this, we use the hardcoded lua path inside the conda environment.
        To recap: on a machine with lua and no lfs, lua_bin might exist
        but the lfs check will fail in which case we install a custom lua
        from conda which will automatically have lfs. Either way, we register
        the desired lua path for the post script in the needs_lua block.
        """
        lua_bin = os.path.join(
            specs['miniconda'], 'envs', specs['envname'], 'bin', 'lua')
        if not os.path.isfile(lua_bin):
            lua_bin = 'lua'
        # confirm the lua libraries
        if not shell_script(lua_check(*self.lua_reqs), bin=lua_bin):
            print('status installing lua because we '
                  'could not find one of: %s' % str(self.lua_reqs))
            needs_lua = True
        if needs_lua:
            # register the custom lua to avoid lfs errors in the post script
            #   otherwise self.lua is the lua from the PATH. (see note above)
            self.lua = os.path.join(
                specs['miniconda'], 'envs', specs['envname'], 'bin', 'lua')
            print('status installing lua')
            result = \
                shell_script(generic_install % dict(url=self.url_lua,
                             prefix=self.cache['prefix']), subshell=subshell)
            if not result:
                self._register_error(name='lmod-lua',
                                     error='Failed to install LUA.')
        print('status building lmod at %s (needs lua=%s)' % (path, needs_lua))
        try:
            # prepend the conda path for tcl.h
            # this is repetitive with a similar block in singularity installer
            path_prepend = ('\n'.join([
                'export LIBRARY_PATH=%(lib)s:$LIBRARY_PATH',
                'export C_INCLUDE_PATH=%(include)s:$C_INCLUDE_PATH',
                ]) % dict([(i, os.path.join(os.getcwd(),
                          specs['miniconda'], 'envs', specs['envname'], i))
                          for i in ['lib', 'include']]))
            # pull the latest lmod programatically from the github API
            shell_script(path_prepend+'\n'+generic_install % dict(url=(
                "https://github.com/TACC/Lmod"
                "/archive/$(curl -s %s | jq -r '.tag_name').tar.gz" %
                'https://api.github.com/repos/TACC/Lmod/releases/latest'),
                prefix=path, subshellf=subshell))
        except:
            # if we cannot get the latest, we use the verified version
            shell_script(generic_install % dict(url=self.url_lmod,
                         prefix=path, subshellf=subshell))
        # note that lmod always installs to the lmod subfolder of the prefix
        #   used in configure, and this prefix also contains an lmod folder
        #   hence we use _enforce_path to check for lmod at the end of the
        #   build path from the user, then we install to the parent directory
        #   and then here we add the lmod back on so that the build path and
        #   the root path eventually written to the settings reflect the true
        #   prefix directory under the standard convention
        self.root = os.path.join(path, 'lmod')

    def _check_lmod(self, path):
        """Confirm the Lmod installation."""
        check = command_check(
            self.lmod_bin_check, cwd=path, quiet=True)
        return (check == self.lmod_returncode)

    def _report_ready(self):
        print('status Lmod is reporting ready')
        # use relative path if we installed to a subdirectory
        rel_path = os.path.join('.', os.path.relpath(self.root, os.getcwd()))
        if '..' not in rel_path:
            self.root = rel_path
        # clear errors from previous runs
        self.cache.get('errors', {}).pop('lmod', None)
        # manage the entire connection to lmod in the settings here
        self.cache['settings']['lmod'] = {'root': self.root}
        # pass the custom lua location if necessary
        if hasattr(self, 'lua'):
            self.cache['settings']['lmod']['lua'] = self.lua
        # lmod also includes updates to LMODRC
        # note that we use the keyed nature of profile_mods to overwrite
        #   any similar changes to the profile
        lmodrc_fn = \
            os.path.abspath(os.path.join(os.getcwd(),
                            'cc_tools', 'lmodrc.lua'))
        if 'profile_mods' not in self.cache:
            self.cache['profile_mods'] = {}

        # do not run on previously existing profile
        if 'profile' not in self.cache['settings']:
            self.cache['profile_mods']['lmod_property'] = [
                bash_env_append % dict(name='post_add_luarc', var='LMOD_RC'),
                'post_add_luarc %s' % (lmodrc_fn)]

    def _detect_lmod(self):
        """
        Check if Lmod is available.
        """
        if 'LMOD_CMD' in os.environ:
            # example: '/software/lmod/lmod/libexec/lmod'
            #   path to Lmod is therefore /software/lmod
            lmod_cmd = os.environ['LMOD_CMD']
            split_path = \
                ((lmod_cmd+os.path.sep).rstrip(os.path.sep)).split('/')
            if split_path[-2:] == ['libexec', 'lmod']:
                # the true path to lmod
                return os.path.sep.join(split_path[:-3])
        # check for an orphaned local lmod at the default location
        if self._check_lmod(self.default_local_lmod):
            return self.default_local_lmod
        return False

    def _lmod_profile_changes(self):
        # stage some bashrc changes only if we just installed
        if 'profile_mods' not in self.cache:
            self.cache['profile_mods'] = {}
        init_fn = os.path.abspath(os.path.join(self.root, 'lmod/init/bash'))
        if not os.path.isfile(init_fn):
            raise Exception('cannot find %s' % init_fn)
        # append to the modulepath
        mods = ['export MODULEPATH=${MODULEPATH:+$MODULEPATH:}%s' %
                os.path.abspath(self.modulefiles), 'source %s' % init_fn]
        # Lmod also needs to know the cc root for some of our modulefiles
        mods += ['export _COMCOL_ROOT="%s"' % os.path.realpath(os.getcwd())]
        self.cache['profile_mods']['lmod'] = mods

    # interpret lmod settings (each method below reads possible inputs)

    def error_null(self, error, build=None, root=None):
        """Ignore request if error present."""
        # handler with args error,**kwargs is broken; needs explicit list
        #   of all possible arguments to work. bugfix coming soon
        print(('warning lmod cannot be installed until the user edits %s') %
              cc_user)
        self._register_error(
            name='lmod', error='The lmod section needs user edits.')

    def build(self, build, lua=None):
        """Request to build Lmod."""

        # enforce lmod at the end of the path
        check_path = self._enforce_path(build)
        # handle path error in which root does not end in lmod
        if not check_path:
            self.cache['settings']['lmod']['error'] = (
                self.ERROR_NOTE+self.ERROR_PATH_ENDS_LMOD)
            self._register_error(
                name='lmod',
                error='The Lmod build path is invalid.')
        # continue with the modified path
        else:
            build = check_path

        # check if built
        prelim = self._check_lmod_prelim(build)
        if prelim == self.STATE_CONFIRM:
            if self._check_lmod(build):
                self.root = build
                return self._report_ready()
            else:
                pass
        elif prelim == self.STATE_ABSENT:
            pass
        else:
            raise Exception(
                'Development error: invalid preliminary state for %s: %s' %
                (self.__class__.__name__, prelim))

        # continue with the installation
        try:
            self._install_lmod(path=build)
            # enforced build path installs to a subdir called lmod
            checked = self._check_lmod(path=self.root)
            if not checked:
                raise Exception('Lmod failed check after installation.')
            self._report_ready()
            self._lmod_profile_changes()

        # exceptions are handled later by UseCase
        except Exception as e:
            # save the error for later
            exc_type, exc_obj, exc_tb = sys.exc_info()
            this_error = {
                'formatted': traceback.format_tb(exc_tb),
                'result': str(exc_obj)}
            # error handling in Execute.UseCase
            self._register_error(error=this_error, name='lmod')
            # error message in the settings
            # we need to interpret the error here
            # add a more specific error (python error in the cache)
            self.cache['settings']['lmod']['error'] = (
                self.ERROR_NOTE + ' ' +
                'See ./cc showcache for details on the installation error')

    def detect(self, root, lua=None):
        """Confirm that lmod exists in the path given by the user."""
        # pass through custom lua path when detecting lmod
        if lua:
            self.lua = lua
        # standardize the error messages because some are repeated
        if root == self.CHECK_ROOT:
            lmod_root = self._detect_lmod()
            if lmod_root:
                self.root = lmod_root
                checked = self._check_lmod(path=self.root)
                # after detecting make sure that it works
                if checked:
                    self._lmod_profile_changes()
                    self._report_ready()
                else:
                    self._register_error(
                        name='lmod',
                        error='Failed to find Lmod. '
                        'Need build path from the user.')
                    self.cache['settings']['lmod'] = {
                        'build': self.default_local_lmod,
                        'error': self.ERROR_NOTE + ' ' +
                        self.ERROR_NEEDS_BUILD}
            else:
                self._register_error(
                    name='lmod',
                    error='Failed to find Lmod.' +
                          ' Need build path from the user.')
                self.cache['settings']['lmod'] = {
                    'build': self.default_local_lmod,
                    'error': self.ERROR_NOTE+' '+self.ERROR_NEEDS_BUILD}
        else:
            self.root = root
            if self._check_lmod_prelim(self.root) == self.STATE_ABSENT:
                self._register_error(
                    name='lmod',
                    error='Cannot find user-specified root: %s.' % root)
                self.cache['settings']['lmod'] = {
                    # add in the default
                    'build': self.default_local_lmod,
                    'error': self.ERROR_NOTE + ' ' +
                    self.ERROR_USER_ROOT_MISSING % root}
                return
            # the root is an absolute path to the lmod folder hence we do not
            #   enforce the path here and later we add lmod in _report_ready
            lmod_checked = self._check_lmod(path=self.root)
            if lmod_checked:
                self._report_ready()
            else:
                self._register_error(
                    name='lmod',
                    error=(
                        'Cannot confirm lmod '
                        'despite user-specified root: %s.') % root)
                self.cache['settings']['lmod']['error'] = (
                    self.ERROR_NOTE)
                self.cache['settings']['lmod'] = {
                    # add in the default
                    'build': self.default_local_lmod,
                    'error': self.ERROR_NOTE + ' ' +
                    self.ERROR_USER_ROOT_FAIL % root}


class SingularityManager(Handler):
    CHECK_ROOT = 'NEEDS_SINGULARITY_PATH'
    ERROR_NOTE = (
        'ERROR. '
        'Remove this note and follow these instructions to continue.')
    ERROR_NEEDS_BUILD = (
        'Cannot locate Singularity. Set the `build` key to a '
        'desired installation location, remove this error, and refresh '
        'to continue.')
    ERROR_USER_ROOT_MISSING = (
        'User-defined root path %s cannot be found. '
        'Supply the correct path or use `build` instead of `root` '
        'and refresh to install Lmod at the build location.')
    ERROR_USER_ROOT_FAIL = (
        'User-defined root path %s  '
        'exists but we cannot confirm Lmod works. ')
    STATE_ABSENT = 'absent'
    STATE_CONFIRM = 'needs_confirm'
    check_bin = 'bin/singularity help'
    check_bin_version = 'bin/singularity --version'
    check_returncode = 0
    user_namespace_check = 'cat /proc/sys/user/max_user_namespaces'
    default_build_conf = {'build': './singularity', 'sandbox': False}
    ERROR_USER_NAMESPACES = ((
        'The sandbox flag in the Singularity settings '
        '(%s) is necessary when you lack sudo privileges and wish to install '
        'Singularity in sandbox mode. This also requires user namespaces. '
        'We failed to find user namespaces using "%s".') %
        (cc_user, user_namespace_check))

    def _detect_singularity(self):
        try:
            which_singularity = bash(
                'which singularity', scroll=False, quiet=True)
        # error code on which causes an exception
        except:
            return False
        fn = which_singularity['stdout'].strip()
        if os.path.isfile(fn):
            root = os.path.sep.join(fn.split(os.path.sep)[:-2])
            tail = os.path.sep.join(fn.split(os.path.sep)[-2:])
            # if non-standard binary then reject
            if tail != 'bin/singularity':
                return False
            else:
                return root
        else:
            return False

    def _detect_singularity_local(self):
        """
        Check the local build path for a singularity in case we lost
        the settings file and need to autodetect local singularity that is
        not in the path because it is managed by modulefiles not yet available.
        """
        local_singularity_dn = './singularity'
        local_singularity_fn = './singularity/bin/singularity'
        if (os.path.isdir('./singularity') and
                os.path.isfile(local_singularity_fn)):
            return local_singularity_dn
        else:
            return False

    def _check_singularity_prelim(self, path):
        if os.path.isdir(path):
            return self.STATE_CONFIRM
        else:
            return self.STATE_ABSENT

    def _check_singularity(self, path):
        print('status checking singularity')
        return (command_check(
            self.check_bin,
            cwd=path, quiet=True) == self.check_returncode)

    def _report_ready(self, built=False):
        print('status Singularity is reporting ready')
        self.cache.get('errors', {}).pop('singularity', None)
        if 'singularity' not in self.cache['settings']:
            # upon singularity detection we populate the cc.yaml entry here
            #   and assume that sandbox is irrelevant because it was installed
            #   by a third party presumably with root
            # note that during detection a singularity at
            #   /usr/local/bin/singularity will result in /usr/local being
            #   marked as the path to singularity however this is not an issue
            self.cache['settings']['singularity'] = {}
        # if we are reporting ready and we built it, then we now have a path
        self.cache['settings']['singularity'].pop('build', None)
        # note that we could compare the build to the install path here
        self.cache['settings']['singularity']['path'] = self.path

    def _install_singularity(self, path):
        """Installation procedure for singularity 3 from the docs."""
        path_abs = os.path.abspath(os.path.expanduser(path))
        # we prepend the conda paths in case openssl-dev (openssl-devel)
        #   are not installed on the host
        path_prepend = ('\n'.join([
            'export LIBRARY_PATH=%(lib)s:$LIBRARY_PATH',
            'export C_INCLUDE_PATH=%(include)s:$C_INCLUDE_PATH',
            ]) % dict([(i, os.path.join(os.getcwd(),
                      specs['miniconda'], 'envs', specs['envname'], i))
                      for i in ['lib', 'include']]))
        script_temp_build = script_temp_build_base % dict(
            source_env=script_source_env) % dict(
                    script=path_prepend+'\n' +
                    script_singularity3_install %
                    dict(prefix=path_abs))
        shell_script(script_temp_build)
        self.path = path

    def _check_user_namespaces(self):
        try:
            result = bash(self.user_namespace_check, scroll=False)
        except Exception as e:
            print('error %s' % str(e))
            raise Exception(self.ERROR_USER_NAMESPACES)
        try:
            max_user_ns = int(result['stdout'].strip())
        except Exception as e:
            print('error %s' % str(e))
            raise Exception(self.ERROR_USER_NAMESPACES)
        if max_user_ns < 1:
            raise Exception(
                self.ERROR_USER_NAMESPACES +
                ' Maximum user namespaces is: %d' % max_user_ns)

    def error_null(self, error, path=None, build=None, sandbox=False):
        """Ignore request if error present."""
        print(('warning singularity cannot be installed '
               'until the user edits %s') % cc_user)
        self._register_error(
            name='singularity',
            error='The singularity section needs user edits.')

    def detect(self, path, sandbox=False):
        """Confirm that Singularity exists in the path given by the user."""
        # note that the sandbox is not checked during detection but we pass it
        self.sandbox = sandbox
        if path == self.CHECK_ROOT:
            # look for singularity with "which"
            path = self._detect_singularity()
            # if we lost our cc.yaml we might also check the local
            #   singularity folder, which is a common build location
            #   to find a preexisting build there
            if not path:
                path = self._detect_singularity_local()
            if path:
                self.path = path
                checked = self._check_singularity(path=self.path)
                # after detecting make sure that it works
                if checked:
                    self._report_ready()
                    return
            # failure to detect here
            self._register_error(
                name='singularity',
                error='Failed to find Singularity. '
                'Need build path from the user.')
            # singularity default path is set here
            build_out = dict(self.default_build_conf)
            build_out['error'] = (self.ERROR_NOTE+' '+self.ERROR_NEEDS_BUILD)
            self.cache['settings']['singularity'] = build_out
            return
        else:
            self.path = path
            if self._check_singularity_prelim(self.path) == self.STATE_ABSENT:
                self._register_error(
                    name='singularity',
                    error='Cannot find user-specified path: %s.' % self.path)
                build_out = dict(self.default_build_conf)
                build_out['error'] = (
                    self.ERROR_NOTE + ' ' +
                    self.ERROR_USER_ROOT_MISSING % path)
                self.cache['settings']['singularity'] = build_out
                return
            # note that we have to enforce the path before the check
            checked = self._check_singularity(path=self.path)
            if checked:
                self._report_ready()
                return
            else:
                self._register_error(
                    name='singularity',
                    error=('Cannot confirm singularity '
                           'despite user-specified path: %s.') % self.path)
                build_out = dict(self.default_build_conf)
                build_out['error'] = self.ERROR_NOTE
                self.cache['settings']['singularity'] = build_out
                return

    def build(self, build, sandbox=False):
        """Build singularity."""

        # confirm user namespaces if we are requesting a sandbox
        self.sandbox = sandbox
        if self.sandbox:
            self._check_user_namespaces()

        # check if already built and we lost the config
        checked = self._check_singularity(build)
        if checked:
            print('status detected previously '
                  'installed singularity at %s' % build)
            self.path = build
            self._report_ready()
            return

        # continue with the installation
        try:
            self._install_singularity(path=build)
            checked = self._check_singularity(path=build)
            if not checked:
                raise Exception('Singularity failed check after installation.')
            self.path = build
            # we previously staged some profile/bashrc changes here however
            #   this is deprecated by the use of an external module that can
            #   add singularity to the path
            self._report_ready()

        # exceptions are handled later by UseCase
        # note that the entire construction of SingularityManager is
        #   synonymous with LmodManager and might be a pattern
        #   worth generalizing
        except Exception as e:
            # save the error for later
            exc_type, exc_obj, exc_tb = sys.exc_info()
            this_error = {
                'formatted': traceback.format_tb(exc_tb),
                'result': str(exc_obj)}
            # error handling in Execute.UseCase
            self._register_error(error=this_error, name='singularity')
            # error message in the settings
            # we need to interpret the error here
            # add a more specific error (python error in the cache)
            self.cache['settings']['singularity']['error'] = (
                self.ERROR_NOTE + ' ' +
                'See ./cc showcache for details on the installation error')
