#!/usr/bin/env python

# Python 2/3 compatabilty and color printer
from __future__ import print_function
from __future__ import unicode_literals

import os
import sys
import re
import json
import tempfile
import traceback

from . import stdtools
from .stdtools import Handler
from .stdtools import command_check
from .stdtools import bash
from .stdtools import tracebacker

from .settings import specs
from .settings import cc_user
from .misc import subshell
from .misc import dependency_pathfinder
from .misc import shell_script
from .misc import path_resolve

### INSTALLATION SCRIPTS

# source environment
script_source_env = """
source %(miniconda_activate)s
conda activate %(envname)s
"""%dict(miniconda_activate=os.path.join(specs['miniconda'],
    specs['conda_activator']),envname=specs['envname'])

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
script_temp_build = script_temp_build_base%dict(source_env='')
script_temp_build_env = script_temp_build_base%dict(
    source_env=script_source_env)

# installation method for miniconda
install_miniconda = script_temp_build%dict(script="""
wget --progress=bar:force https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh
bash Miniconda3-latest-Linux-x86_64.sh -b -p %(miniconda_path)s -u
""")

# generic configure-make script
generic_install = script_temp_build_env%dict(script="""
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
"""+'\n'.join(['loadrequire(\'%s\')'%i for i in x])

# install singularity 3
script_singularity3_install = """
export VERSION=1.11 OS=linux ARCH=amd64
wget --progress=bar:force https://dl.google.com/go/go$VERSION.$OS-$ARCH.tar.gz
tar xf go$VERSION.$OS-$ARCH.tar.gz --checkpoint=.100 && echo
cd go
export PATH=$(realpath .)/bin:$PATH
export GOPATH=$(pwd)/go
mkdir -p $GOPATH/src/github.com/sylabs
cd $GOPATH/src/github.com/sylabs
git clone https://github.com/sylabs/singularity.git
cd $GOPATH/src/github.com/sylabs/singularity
go get -u -v github.com/golang/dep/cmd/dep
cd $GOPATH/src/github.com/sylabs/singularity
mkdir -p %(prefix)s
./mconfig --prefix=%(prefix)s
make -C builddir
make -C builddir install 
"""

### INSTALLATION MANAGEMENT CLASSES

class CCStack:
    """
    Install minimal stack for running CC.
    Decorate via: `SoftwareStack = Convey(state=state)(SoftwareStack)`
    """
    def start_conda(self):
        """Check if the CC conda environment exists."""
        if not command_check(subshell('conda'))==0:
            print('status cannot find conda')
            print('status installing miniconda')
            has_worked = self.miniconda()
            if not has_worked: 
                raise Exception('failed to install Miniconda')
        else: print('status found conda')
        print('status checking conda environments')
        result = bash(subshell('conda env list --json'),scroll=False)
        envs = json.loads(result['stdout'])
        print('status checking for the %s environment'%specs['envname'])
        conda_env_path = os.path.join(
            dependency_pathfinder(specs['miniconda']),'envs',specs['envname'])
        if conda_env_path not in envs.get('envs',[]):
            print('status failed to find the %s environment'%specs['envname'])
            print('status building the environment')
            self.conda_env()
            print('status done building the environment')
        else: print('status found conda environment: %s'%specs['envname'])
    def miniconda(self):
        """
        Install miniconda from a temporary directory using a script.
        """
        script = (install_miniconda%{'miniconda_path':os.path.realpath(
            os.path.expanduser(dependency_pathfinder(specs['miniconda'])))})
        return shell_script(script)
    def conda_env(self,spec_fn='cc_tools/conda_env.yaml'):
        """
        Install the conda environment.
        """
        spec_fn_abs = os.path.abspath(os.path.expanduser(spec_fn))
        bash(subshell('conda env create --name %s --file %s'%(
            specs['envname'],spec_fn)))
    def which(self):
        if not command_check('which -v')==0:
            raise Exception('cannot find `which` required for execution')

class LmodManager(Handler):
    """
    Install Lmod and note its location
    """
    CHECK_ROOT = 'NEEDS_LMOD_PATH'
    url_lua = (
        #! note that this changed from 5.1.4.8 tar.gz to 5.1.4.9 and bz2
        #! changes to these locations can break the installer
        #! note that the conda installer is working now, so this is deprecated
        'https://sourceforge.net/projects/lmod/files/lua-5.1.4.9.tar.bz2')
    #! get the latest release instead: https://github.com/TACC/Lmod/releases
    url_lmod = 'http://sourceforge.net/projects/lmod/files/Lmod-8.0.tar.bz2'
    ERROR_NOTE = ('ERROR. '
        'Remove this note and follow these instructions to continue.')
    ERROR_PATH_ENDS_LMOD = ' The lmod root path must end in "lmod".'
    ERROR_NEEDS_BUILD = ('Cannot locate Lmod. Set the `build` key to a '
        'desired installation location, remove this error, and refresh '
        'to continue.')
    ERROR_USER_ROOT_MISSING = ('User-defined root path %s cannot be found. '
        'Supply the correct path or use `build` instead of `root` '
        'and refresh to install Lmod at the build location.')
    ERROR_USER_ROOT_FAIL = ('User-defined root path %s  '
        'exists but we cannot confirm Lmod works. ')
    STATE_ABSENT = 'absent'
    STATE_CONFIRM = 'needs_confirm'
    lua_reqs = ('posix','lfs')
    # account for the removal of the lmod root path here
    lmod_bin_check = './lmod/lmod/libexec/lmod help'
    lmod_returncode = 0
    # location for modulefiles to add to the module path
    modulefiles = './modulefiles'

    def _check_lmod_prelim(self,path):
        """Check if spack directory exists."""
        if os.path.isdir(path): return self.STATE_CONFIRM
        else: return self.STATE_ABSENT

    def _enforce_path(self,build):
        """
        For clarity we enforce a true lmod path. 
        The path must end in 'lmod'.
        """
        if not (os.path.basename(
            (build+os.path.sep).rstrip(os.path.sep))=='lmod'):
            return False
        # now that we are sure the user has lmod in the path we strip it
        build_dn = os.path.dirname(os.path.realpath(os.path.expanduser(
            (build+os.path.sep).rstrip(os.path.sep))))
        return build_dn

    def _install_lmod(self,path):
        """Installation procedure from Lmod straight from the docs."""
        # we check for lua before installing to the conda environment
        needs_lua = False
        if not command_check('which lua')==0: needs_lua = True
        """
        We previously relied on lua from /usr/bin and included the installation
        instructions below to install the lua associated with an lmod version
        from the source via sourceforge. Now that conda can supply lua without
        issue, this is unnecessary, however we still check for lfs and posix.
        To do this, we use the hardcoded lua path inside the conda environment.
        """
        lua_bin = os.path.join(specs['miniconda'],
            'envs',specs['envname'],'bin','lua')
        if not os.path.isfile(lua_bin): lua_bin = 'lua'
        # confirm the lua libraries
        if not shell_script(lua_check(*self.lua_reqs),bin=lua_bin):
            print('status installing lua because we '
                'could not find one of: %s'%str(self.lua_reqs))
            needs_lua = True
        if needs_lua:
            #! should we register that a custom lua was installed?
            print('status installing lua')
            result = shell_script(generic_install%dict(url=self.url_lua,
                prefix=self.cache['prefix']),subshell=subshell)
            if not result:
                self._register_error(name='lmod-lua',error=
                    'Failed to install LUA.')
        print('status building lmod at %s (needs lua=%s)'%(path,needs_lua))
        try:
            # prepend the conda path for tcl.h
            #! this is repetitive with a similar block in singularity installer
            path_prepend = ('\n'.join([
                'export LIBRARY_PATH=%(lib)s:$LIBRARY_PATH',
                'export C_INCLUDE_PATH=%(include)s:$C_INCLUDE_PATH',
                ])%dict([(i,os.path.join(os.getcwd(),
                    specs['miniconda'],'envs',specs['envname'],i)) 
                    for i in ['lib','include']]))
            # pull the latest lmod programatically from the github API
            shell_script(path_prepend+'\n'+generic_install%dict(url=(
                "https://github.com/TACC/Lmod"
                "/archive/$(curl -s %s | jq -r '.tag_name').tar.gz"%
                'https://api.github.com/repos/TACC/Lmod/releases/latest'),
                prefix=path,subshellf=subshell))
        except:
            # if we cannot get the latest, we use the verified version
            shell_script(generic_install%dict(url=self.url_lmod,
                prefix=path,subshellf=subshell))
        self.root = path

    def _check_lmod(self,path):
        """Confirm the spack installation."""
        check = command_check(self.lmod_bin_check,cwd=path)
        return (check==self.lmod_returncode)

    def _report_ready(self):
        print('status Lmod is reporting ready')
        # recall that we install the lmod folder into a root path
        self.root = os.path.join(self.root,'lmod')
        rel_path = os.path.join('.',os.path.relpath(self.root,os.getcwd()))
        if '..' not in rel_path: self.root = rel_path
        # clear errors from previous runs
        self.cache['errors'].pop('lmod',None)
        self.cache['settings']['lmod'] = {'root':self.root}

    def _detect_lmod(self):
        """
        Check if Lmod is available.
        """
        if 'LMOD_CMD' in os.environ:
            # example: '/software/lmod/lmod/libexec/lmod'
            #   path to Lmod is therefore /software/lmod
            lmod_cmd = os.environ['LMOD_CMD']
            split_path = ((lmod_cmd+os.path.sep).rstrip(os.path.sep)).split('/')
            if split_path[-3:]==['lmod','libexec','lmod']:
                # the true path to lmod
                return os.path.sep.join(split_path[:-3])
        return False

    ### interpret lmod settings (each method below reads possible inputs)

    def error_null(self,error,build=None,root=None):
        """Ignore request if error present."""
        #! handler with args error,**kwargs is broken; needs explicit list
        #!   of all possible arguments to work. bugfix coming soon
        print(('warning lmod cannot be installed until the user edits %s')
            %cc_user)
        self._register_error(name='lmod',error=
            'The lmod section needs user edits.')

    def build(self,build):
        """Request to build Lmod."""

        # enforce lmod at the end of the path
        check_path = self._enforce_path(build)
        # handle path error in which root does not end in lmod
        if not check_path:
            self.cache['settings']['lmod']['error'] = (
                self.ERROR_NOTE+self.ERROR_PATH_ENDS_LMOD)
            self._register_error(name='lmod',error=
                'The Lmod build path is invalid.')
        # continue with the modified path
        else: build = check_path

        # check if built
        prelim = self._check_lmod_prelim(build)
        if prelim==self.STATE_CONFIRM:
            if self._check_lmod(build):
                self.root = build
                return self._report_ready()
            else: pass
        elif prelim==self.STATE_ABSENT: pass
        else: raise Exception(
            'Development error: invalid preliminary state for %s: %s'%(
                self.__class__.__name__,prelim))

        # continue with the installation
        try: 
            self._install_lmod(path=build)
            checked = self._check_lmod(path=build)
            if not checked:
                raise Exception('Lmod failed check after installation.')
            self.root = build
            self._report_ready()
            # stage some bashrc changes only if we just installed
            if 'bashrc_mods' not in self.cache: 
                self.cache['bashrc_mods'] = []
            init_fn = os.path.abspath(os.path.join(self.root,'lmod/init/bash'))
            mods = ['export MODULEPATH=%s'%
                os.path.abspath(self.modulefiles),'source %s'%init_fn]
            self.cache['bashrc_mods'].extend(mods)

        # exceptions are handled later by UseCase
        except Exception as e: 
            # save the error for later
            exc_type,exc_obj,exc_tb = sys.exc_info()
            this_error = {
                'formatted':traceback.format_tb(exc_tb),
                'result':str(exc_obj)}
            # error handling in Execute.UseCase
            self._register_error(error=this_error,name='lmod')
            # error message in the settings
            #! we need to interpret the error here
            #! add a more specific error (python error in the cache)
            self.cache['settings']['lmod']['error'] = (
                self.ERROR_NOTE+' '+
                'See ./cc showcache for details on the installation error')

    def detect(self,root):
        """Confirm that lmod exists in the path given by the user."""
        #! standardize the error messages because some are repeated
        if root==self.CHECK_ROOT:
            lmod_root = self._detect_lmod()
            if lmod_root:
                self.root = lmod_root
                checked = self._check_lmod(path=self.root)
                # after detecting make sure that it works
                if checked:
                    self._report_ready()
                else: 
                    self._register_error(name='lmod',
                        error='Failed to find Lmod. Need build path from the user.')
                    self.cache['settings']['lmod'] = {
                        'build':'./lmod',
                        'error':self.ERROR_NOTE+' '+self.ERROR_NEEDS_BUILD}
            else:
                self._register_error(name='lmod',
                    error='Failed to find Lmod. Need build path from the user.')
                self.cache['settings']['lmod'] = {
                    'build':'./lmod',
                    'error':self.ERROR_NOTE+' '+self.ERROR_NEEDS_BUILD}
        else:
            self.root = self._enforce_path(root)
            if self._check_lmod_prelim(self.root)==self.STATE_ABSENT:
                self._register_error(name='lmod',
                    error='Cannot find user-specified root: %s.'%root)
                self.cache['settings']['lmod'] = {
                    # add in the default
                    'build':'./lmod',
                    'error':self.ERROR_NOTE+' '+
                    self.ERROR_USER_ROOT_MISSING%root}
                return
            # note that we have to enforce the path before the check
            lmod_checked = self._check_lmod(path=self._enforce_path(root))
            if lmod_checked:
                self._report_ready()
            else: 
                self._register_error(name='lmod',
                    error=('Cannot confirm lmod '
                        'despite user-specified root: %s.')%root)
                self.cache['settings']['lmod']['error'] = (
                    self.ERROR_NOTE)
                self.cache['settings']['lmod'] = {
                    #!! add in the default
                    'build':'./lmod',
                    'error':self.ERROR_NOTE+' '+
                    self.ERROR_USER_ROOT_FAIL%root}

class SingularityManager(Handler):
    CHECK_ROOT = 'NEEDS_SINGULARITY_PATH'
    ERROR_NOTE = ('ERROR. '
        'Remove this note and follow these instructions to continue.')
    ERROR_NEEDS_BUILD = ('Cannot locate Singularity. Set the `build` key to a '
        'desired installation location, remove this error, and refresh '
        'to continue.')
    ERROR_USER_ROOT_MISSING = ('User-defined root path %s cannot be found. '
        'Supply the correct path or use `build` instead of `root` '
        'and refresh to install Lmod at the build location.')
    ERROR_USER_ROOT_FAIL = ('User-defined root path %s  '
        'exists but we cannot confirm Lmod works. ')
    STATE_ABSENT = 'absent'
    STATE_CONFIRM = 'needs_confirm'
    check_bin = 'bin/singularity help'
    check_returncode = 0 
    default_build_conf = {'build':'./singularity'}

    def _detect_singularity(self):
        #! look around to find singularity if it is not in the path?
        return False

    def _check_singularity_prelim(self,path):
        if os.path.isdir(path): return self.STATE_CONFIRM
        else: return self.STATE_ABSENT

    def _check_singularity(self,path):
        print('status checking singularity')
        return (command_check(
            self.check_bin,
            cwd=path)==self.check_returncode)

    def _report_ready(self,):
        print('status Singularity is reporting ready')
        self.cache['errors'].pop('singularity',None)
        self.cache['settings']['singularity'] = {
            'path':self.path}

    def _install_singularity(self,path):
        """Installation procedure for singularity 3 from the docs."""
        path_abs = os.path.abspath(os.path.expanduser(path))
        # we prepend the conda paths in case openssl-dev (openssl-devel)
        #   are not installed on the host
        path_prepend = ('\n'.join([
            'export LIBRARY_PATH=%(lib)s:$LIBRARY_PATH',
            'export C_INCLUDE_PATH=%(include)s:$C_INCLUDE_PATH',
            ])%dict([(i,os.path.join(os.getcwd(),
                specs['miniconda'],'envs',specs['envname'],i)) 
                for i in ['lib','include']]))
        script_temp_build = script_temp_build_base%dict(
            source_env=script_source_env)%dict(script=path_prepend+'\n'+
                script_singularity3_install%dict(prefix=path_abs))
        shell_script(script_temp_build)
        self.path = path

    def error_null(self,error,path=None,build=None):
        """Ignore request if error present."""
        print(('warning singularity cannot be installed '
            'until the user edits %s')%cc_user)
        self._register_error(name='singularity',error=
            'The singularity section needs user edits.')

    def detect(self,path):
        """Confirm that Singularity exists in the path given by the user."""
        if path==self.CHECK_ROOT:
            path = self._detect_singularity()
            if path:
                self.path = path
                checked = self._check_singularity(path=self.path)
                # after detecting make sure that it works
                if checked: 
                    self._report_ready()
                    return
            # failure to detect here
            self._register_error(name='singularity',
                error='Failed to find Singularity. '
                'Need build path from the user.')
            # singularity default path is set here
            build_out = dict(self.default_build_conf)
            build_out['error'] = (self.ERROR_NOTE+' '+self.ERROR_NEEDS_BUILD)
            self.cache['settings']['singularity'] = build_out
            return
        else:
            self.path = path
            if self._check_singularity_prelim(self.path)==self.STATE_ABSENT:
                self._register_error(name='singularity',
                    error='Cannot find user-specified path: %s.'%self.path)
                build_out = dict(self.default_build_conf)
                build_out['error'] = (self.ERROR_NOTE+' '+
                    self.ERROR_USER_ROOT_MISSING%path)
                self.cache['settings']['singularity'] = build_out
                return
            # note that we have to enforce the path before the check
            checked = self._check_singularity(path=self.path)
            if checked: 
                self._report_ready()
                return
            else: 
                self._register_error(name='singularity',
                    error=('Cannot confirm singularity '
                        'despite user-specified path: %s.')%self.path)
                build_out = dict(self.default_build_conf)
                build_out['error'] = self.ERROR_NOTE
                self.cache['settings']['singularity'] = build_out
                return

    def build(self,build):
        """Build singularity."""

        # check if already built and we lost the config
        checked = self._check_singularity(build)
        if checked:
            print('status detected previously '
                'installed singularity at %s'%build)
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
            self._report_ready()
            # stage some bashrc changes only if we just installed
            if 'bashrc_mods' not in self.cache: 
                self.cache['bashrc_mods'] = []
            build_bin_dn = os.path.join(os.path.abspath(os.path.expanduser(build)),'bin')
            mods = ['export PATH=%s:$PATH'%build_bin_dn]
            self.cache['bashrc_mods'].extend(mods)

        # exceptions are handled later by UseCase
        #! note that the entire construction of SingularityManager is
        #!   synonymous with LmodManager and might be a pattern 
        #!   worth generalizing
        except Exception as e: 
            # save the error for later
            exc_type,exc_obj,exc_tb = sys.exc_info()
            this_error = {
                'formatted':traceback.format_tb(exc_tb),
                'result':str(exc_obj)}
            # error handling in Execute.UseCase
            self._register_error(error=this_error,name='singularity')
            # error message in the settings
            #! we need to interpret the error here
            #! add a more specific error (python error in the cache)
            self.cache['settings']['singularity']['error'] = (
                self.ERROR_NOTE+' '+
                'See ./cc showcache for details on the installation error')

class SpackManager(Handler):
    STATE_CONFIRM = 'needs_confirm'
    STATE_ABSENT = 'absent'
    # command and returncode must match
    # calling spack without version is slow and returns 1
    spack_bin_check = './bin/spack --version'
    spack_returncode = 0
    url = 'https://github.com/spack/spack.git'
    ERROR_NOTE = ('ERROR. '
        'Remove this note and follow these instructions to continue.')

    def _check_spack(self,path):
        """Confirm the spack installation."""
        print('status checking spack')
        return (command_check(
            self.spack_bin_check,
            cwd=path)==self.spack_returncode)

    def _check_spack_prelim(self,path):
        """Check if spack directory exists."""
        if os.path.isdir(path): return self.STATE_CONFIRM
        else: return self.STATE_ABSENT

    def _install_spack(self,path):
        """
        Install spack according to the instructions
        """
        print('status installing spack')
        bash('git clone %s %s'%(self.url,path))

    def _report_ready(self,path):
        print('status spack is reporting ready')
        self.cache['errors'].pop('spack',None)
        self.cache['settings']['spack'] = {'path':path}

    def error_null(self,error,build=None,path=None):
        """Ignore request if error present."""
        print(('warning spack cannot be installed until the user edits %s')
            %cc_user)
        self._register_error(name='spack',error=
            'The lmod section needs user edits.')

    def build(self,build):
        """
        Field a spack build request.
        """
        print('status received the build request for spack from the user')
        print('status building at %s'%build)
        self.root = path_resolve(build)
        # check if already built
        prelim = self._check_spack_prelim(build)
        if prelim==self.STATE_CONFIRM:
            if self._check_spack(build):
                return self._report_ready(path=build)
            else: pass
        elif prelim==self.STATE_ABSENT: pass
        else: raise Exception(
            'invalid preliminary state for %s: %s'%(
                self.__class__.__name__,prelim))
        # continue with the installation
        try: 
            self._install_spack(path=build)
            self._check_spack(path=build)
            self._report_ready(path=build)
        # exceptions are handled later by UseCase
        except Exception as e: 
            # save the error for later
            exc_type,exc_obj,exc_tb = sys.exc_info()
            this_error = {
                'formatted':traceback.format_tb(exc_tb),
                'result':str(exc_obj)}
            # error handling in Execute.UseCase
            self._register_error(error=this_error,name='spack')
            # error message in the settings
            #! we need to interpret the error here
            #! add a more specific error (python error in the cache)
            self.cache['settings']['spack']['error'] = (
                self.ERROR_NOTE)
    
    def detect(self,path):
        """
        """
        raise Exception('dev')
