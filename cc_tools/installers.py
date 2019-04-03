#!/usr/bin/env python

# Python 2/3 compatabilty and color printer
from __future__ import print_function
from __future__ import unicode_literals

import os
import json
import tempfile

from stdtools import Handler
from stdtools import command_check
from stdtools import bash

from settings import subshell
from settings import specs
from settings import dependency_pathfinder
from settings import conda_spec

bootstrap_miniconda = ("""
tmpdir=$(mktemp)
here=$(pwd)
cd $tmpdir
wget -N https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh
bash Miniconda3-latest-Linux-x86_64.sh -b -p %(miniconda_path)s -u
rm -rf $tmpdir
"""
# custom paths added here
%{'miniconda_path':dependency_pathfinder(specs['miniconda'])}
).strip()

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
            self.miniconda()
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
        Install miniconda from a mktemp using a temporary script.
        """
        with tempfile.NamedTemporaryFile(delete=False) as fp:
            fp.write(bootstrap_miniconda)
            fp.close()
            bash('bash %s'%fp.name)
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

class Singularity(Handler):
    """
    Interact with (detect and install) Singularity.
    """
    singularity_bin_name = 'singularityX -v'
    singularity_returncode = 1
    CHECK_PATH = 'NEEDS_SINGULARITY_PATH'
    BUILD_INSTRUCT = ('ERROR: cannot find Singularity. '
        'Replace this build message with `build: /path/to/new/install` if '
        'you want us to install it. Otherwise supply a path to the binary '
        'with `path: /path/to/singularity`.')
    BUILD_INSTRUCT_FAIL = ('ERROR: cannot find Singularity '
        'at user-supplied path: %s. '
        'Replace this build message with `build: /path/to/new/install` if '
        'you want us to install it. Otherwise supply a path to the binary '
        'with `path: /path/to/singularity`.')

    def install(self,build):
        """Install singularity if we receive a build request."""
        print('status installing singularity')
        #! needs installer here
        #! assume relative path
        print('status installing to %s'%os.path.join(os.getcwd(),build))
        self.cache['singularity_error'] = 'needs_install'
        self.abspath = 'PENDING_INSTALL'
        raise Exception

    def detect(self,path):
        """
        Check singularity before continuing.
        """
        # CHECK_PATH is the default if no singularity entry (see UseCase.main)
        if path==self.CHECK_PATH:
            # check the path
            #! store expected return codes in settings?
            singularity_path = (
                command_check(self.singularity_bin_name)==
                self.singularity_returncode)
            # found singularity
            if singularity_path:
                self.abspath = bash('which %s'%self.singularity_bin_name,
                    scroll=False)['stdout'].strip()
                # since we found singularity we update the settings for user
                self.cache['yaml']['singularity_error'] = {
                    'path':self.abspath} 
                print('status found singularity at '%self.abspath)
                return
            # cannot find singularity and CHECK_PATH asked for it so we build
            else: 
                # redirect to the build instructions
                self.cache['yaml']['singularity'] = {
                    'build':Singularity.BUILD_INSTRUCT} 
                # transmit the error to the UseCase parent
                self.cache['singularity_error'] = 'needs_edit'
                #! accumulate exceptions and show multiple ones, or do loops
                print('status failed to find Singularity')
                raise Exception
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
                self.cache['yaml']['singularity'] = {
                    'build':Singularity.BUILD_INSTRUCT_FAIL%path} 
                # transmit the error to the UseCase parent
                self.cache['singularity_error'] = 'needs_edit'
                #! accumulate exceptions and show multiple ones, or do loops
                print('status failed to find user-specified Singularity')
                raise Exception
