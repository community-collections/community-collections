#!/usr/bin/env python

# Python 2/3 compatabilty and color printer
from __future__ import print_function
from __future__ import unicode_literals

import os
import json
import tempfile

from . import stdtools
from .stdtools import Handler
from .stdtools import command_check
from .stdtools import bash

from .settings import specs
from .settings import conda_spec
from .misc import subshell
from .misc import dependency_pathfinder
from .misc import shell_script

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
# build here
%%(script)s
cd $here
rm -rf $tmpdir
"""

# option to build with an environment
script_temp_build = script_temp_build_base%dict(source_env='')
script_temp_build_env = script_temp_build_base%dict(
    source_env=script_source_env)

install_miniconda = script_temp_build%dict(script="""
wget https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh
bash Miniconda3-latest-Linux-x86_64.sh -b -p %(miniconda_path)s -u
""")

generic_install = script_temp_build_env%dict(script="""
URL=%(url)s
wget $URL
SOURCE_FN=${URL##*/}
DN=$(tar tf $SOURCE_FN | head -1 | cut -f1 -d"/")
tar xvf $SOURCE_FN
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

class CCStack:
    """
    Install minimal stack for running CC.
    Decorate via: `SoftwareStack = Convey(state=state)(SoftwareStack)`
    """
    def start_conda(self):
        """Check if the CC conda environment exists."""
        if not command_check(subshell('conda'))==0:
            #! add auto-conda installation here
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
            #! hacking in the right path here but this should be generalized
            dependency_pathfinder(specs['miniconda']),'envs',specs['envname'])
        if conda_env_path not in envs.get('envs',[]):
            print('status failed to find the %s environment'%specs['envname'])
            print('status building the environment')
            self.conda_env()
            #! save results to the config?
            #! write_config({'conda_env':conda_env_path},config_fn=self.config_fn)
            print('status done building the environment')
        else: print('status found conda environment: %s'%specs['envname'])
    def miniconda(self):
        """
        Install miniconda from a temporary directory using a script.
        """
        script = (install_miniconda%{'miniconda_path':os.path.realpath(
            os.path.expanduser(dependency_pathfinder(specs['miniconda'])))})
        return shell_script(script)
    def conda_env(self):
        """
        Install the conda environment.
        """
        spec_fn = 'anaconda.yaml'
        with open(spec_fn,'w') as fp:
            fp.write(conda_spec)
        bash(subshell('conda env create --file %s'%spec_fn))
    def which(self):
        if not command_check('which -v')==0:
            raise Exception('cannot find `which` required for execution')

class LmodManager(Handler):
    """
    Interface to Lmod
    """
    CHECK_ROOT = 'NEEDS_LMOD_PATH'
    BUILD_INSTRUCT = ('ERROR: cannot find Lmod. '
        'Replace this entire line with `build: ./lmod` to build in the standard '
        'location or choose a different path.')
    BUILD_INSTRUCT_FAIL = ('ERROR: user-defined Lmod path is absent ('
        'or does not end in `lmod`, which is the default name): %s')
    def _confirm_lmod(self):
        #! confirm that lmod is correctly installed?
        return 
    def detect(self,root,modulefiles):
        print('status detecting lmod')
        if root==self.CHECK_ROOT:
            self.cache['lmod_error'] = 'needs_edit'
            self.cache['settings']['lmod'] = {
                'modulefiles':modulefiles,
                'build':self.BUILD_INSTRUCT}
            # lmod directory exists
        elif os.path.isdir(root):
            self._confirm_lmod()
            # save the path to lmod
            self.cache['settings']['lmod'] = {'root':root,'modulefiles':modulefiles}
        else:
            if not os.path.isdir(root):
                self.cache['settings']['lmod'] = {
                    'build':self.BUILD_INSTRUCT_FAIL%root,
                    'modulefiles':modulefiles}
                self.cache['lmod_error'] = 'needs_edit'
            else:
                self._confirm_lmod()
        self.root = root
        self.modulefiles = modulefiles
    def build(self,build,modulefiles):
        """
        Install Lmod in the simplest possible way.
        """
        url_lua = \
            'https://downloads.sourceforge.net/project/lmod/lua-5.1.4.8.tar.gz'
        # for clarity we enforce a true lmod path
        if not (
            os.path.basename((build+os.path.sep).rstrip(os.path.sep))=='lmod'):
            self.cache['lmod_error'] = 'needs_edit'
            self.cache['settings']['lmod'] = {
                'build':self.BUILD_INSTRUCT_FAIL%build,
                'modulefiles':modulefiles}
            raise Exception('incorrect lmod path (must end in lmod)')
        # now that we are sure the user has lmod in the path we strip it
        build_dn = os.path.dirname(os.path.realpath(os.path.expanduser(
            (build+os.path.sep).rstrip(os.path.sep))))
        lua_reqs = ('posix','lfs')
        # we check for lua before installing to the conda environment
        needs_lua = False
        if not command_check('which lua')==0: needs_lua = True
        if not shell_script(lua_check(*lua_reqs),bin='lua'):
            print('status installing lua because we '
                'could not find one of: %s'%str(lua_reqs))
            needs_lua = True
        #! should we register this installation somewhere?
        if needs_lua:
            shell_script(generic_install%dict(url=url_lua,
                prefix=self.cache['prefix']),subshell=subshell)
        print('status building lmod at %s'%build_dn)
        shell_script(generic_install%dict(url=
            'http://sourceforge.net/projects/lmod/files/Lmod-6.1.tar.bz2',
            prefix=build_dn,subshell=subshell))
        # modulefiles location is checked by UseCase
        self.root = build
        self.modulefiles = modulefiles
        # clean up the error in case we arrived here after build instructions
        if 'lmod_error' in self.cache: 
            del self.cache['lmod_error']
        # note that lmod is installed
        self.cache['settings']['lmod'] = dict(
            root=build,modulefiles=modulefiles)

class SingularityManager(Handler):
    """
    Interact with (detect and install) Singularity.
    """
    singularity_bin_name = 'singularity'
    singularity_returncode = 1
    CHECK_PATH = 'NEEDS_SINGULARITY_PATH'
    BUILD_INSTRUCT_FAIL_START = 'ERROR: cannot find Singularity '
    BUILD_INSTRUCT = (BUILD_INSTRUCT_FAIL_START+
        'Replace this build message with `build: /path/to/new/install` if '
        'you want us to install it. Otherwise supply a path to the binary '
        'with `path: /path/to/singularity`.')
    BUILD_INSTRUCT_FAIL_START = 'ERROR: cannot find Singularity '
    BUILD_INSTRUCT_FAIL = (BUILD_INSTRUCT_FAIL_START+
        'at user-supplied path: %s. '
        'Replace this build message with `build: /path/to/new/install` if '
        'you want us to install it. Otherwise supply a path to the binary '
        'with `path: /path/to/singularity`.')

    def install(self,build):
        """Install singularity if we receive a build request."""
        print('status installing singularity')
        #! clumsy way to check both build instructions, even the path scold
        if (build==self.BUILD_INSTRUCT 
            or re.match(self.BUILD_INSTRUCT_FAIL_START,build)):
            self.cache['singularity_error'] = 'needs_edit'
            raise Exception('pending installation!')
        #! needs installer here
        #! assume relative path
        print('status installing to %s'%os.path.join(os.getcwd(),build))
        self.cache['singularity_error'] = 'needs_install'
        self.abspath = 'PENDING_INSTALL'
        raise Exception('pending installation!')

    def detect(self,path):
        """
        Check singularity before continuing.
        """
        # CHECK_PATH is the default if no singularity entry (see UseCase.main)
        if path==self.CHECK_PATH:
            # check the path
            singularity_path = (
                command_check(self.singularity_bin_name)==
                self.singularity_returncode)
            # found singularity
            if singularity_path:
                self.abspath = bash('which %s'%self.singularity_bin_name,
                    scroll=False)['stdout'].strip()
                # since we found singularity we update the settings for user
                self.cache['settings']['singularity'] = {
                    'path':self.abspath} 
                print('status found singularity at %s'%self.abspath)
                return
            # cannot find singularity and CHECK_PATH asked for it so we build
            else: 
                # redirect to the build instructions
                self.cache['settings']['singularity'] = {
                    'build':self.BUILD_INSTRUCT} 
                # transmit the error to the UseCase parent
                self.cache['singularity_error'] = 'needs_edit'
                raise Exception('status failed to find Singularity')
        # if the user has replaced the CHECK_PATH flag 
        else:
            singularity_path = (
                command_check(self.singularity_bin_name)==
                self.singularity_returncode)
            # confirmed singularity hence no modifications needed
            if singularity_path: 
                self.abspath = path
                print('status confirmed singularity at %s'%self.abspath)
                return
            else: 
                # tell the user we could not find the path they sent
                self.cache['settings']['singularity'] = {
                    'build':self.BUILD_INSTRUCT_FAIL%path} 
                # transmit the error to the UseCase parent
                self.cache['singularity_error'] = 'needs_edit'
                raise Exception('status failed to find user-specified Singularity')
