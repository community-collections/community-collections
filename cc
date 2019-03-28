#!/bin/bash
"exec" "python" "-B" "$0" "$@"

# Python 2/3 compatabilty and color printer
from __future__ import print_function
from __future__ import unicode_literals

"""
Prototype for the Python interface to Community Collections (CC).
Currently offering this to the user via: `alias cc="python $(pwd)/cc"`.
"""

import sys
import os
import subprocess
import argparse
import inspect
import json

from cc_tools import bash
from cc_tools import command_check
from cc_tools import prepare_print
prepare_print()

### SETTINGS

conda_name = 'community-collections'
# all paths relative to community collections root
dependency_pathfinder = lambda x: os.path.realpath(
    os.path.expanduser(os.path.join(os.getcwd(),x)))

# master specification listing
specs = {
    'miniconda':'miniconda',
    'conda_activator':'etc/profile.d/conda.sh',
    'envname':'community-collections'}

#! attach the prefix somehow in the class below?
#! systematic way to manage prefix paths?
subshell = lambda x: '. %s && %s'%(
    os.path.join(
        dependency_pathfinder(specs['miniconda']),
        specs['conda_activator']
        ),x)

### TOOLS

# special printing happens before imports
prepare_print()

def write_config(config):
    #! do we need a lock system here? probably not
    with open(config_fn) as fp:
        json.dump(config,fp)

def read_config():
    with open(config_fn,'r') as fp: 
        result = json.load(fp)
    return result

### FRAMEWORK

#! testing environment because rpb had trouble getting nvchecker in a centos7 docker
env_test = """name: community-collections
#! channels:
#!  - conda-forge
dependencies:
#! broken? - lua-luaposix
- python>=3.6
#! - curl was not working
- pycurl
- pip
- pip:
  - nvchecker
"""

#! move this to temporary folder?
#! standardize the installation paths?
#! is tmp clean safe?
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
).strip().splitlines()

class Installer:
    def miniconda(self):
        for command in bootstrap_miniconda:
            bash(command)
    def conda_env(self):
        #! test environment
        spec_fn = 'env_test.yaml'
        with open(spec_fn,'w') as fp:
            fp.write(env_test)
        bash(subshell('conda env create --file %s'%spec_fn))

class Detector:
    def conda(self):
        if not command_check(subshell('conda')):
            #! add auto-conda installation here
            print('status cannot find conda')
            print('status installing miniconda')
            Installer().miniconda()
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
            Installer().conda_env()
            #! save results to the config?
            write_config({'conda_env':conda_env_path})
            print('status done building the environment')
        else: print('status found conda environment: %s'%specs['envname'])

class CCInterface:
    """
    A single call to this interface.
    """
    def __init__(self,config_fn='config.json'):
        self.config_fn = config_fn
    def bootstrap(self,**kwargs):
        """
        Build the environment, detect existing components, 
        and write a configuration.
        """
        kwargs.pop('command')
        if kwargs: raise Exception('unprocessed kwargs: %s'%kwargs)
        print('status community collections bootstrap')
        detect = Detector()
        detect.conda()
        print('status done bootstrap')

if __name__=='__main__':

    # argument parser linked to the CCInterface class above
    subcommand_names = [func for func in dir(CCInterface) 
        if callable(getattr(CCInterface, func))
        and not func.startswith('_')]
    parser = argparse.ArgumentParser(
        description='Manage Community Collections (CC).')
    parser.add_argument('command',type=str,
        choices=subcommand_names,
        help='The command for the CC interface.')
    # run the argparse
    args = parser.parse_args()
    #! instance can be customized later
    action = CCInterface()
    # run the interface
    getattr(action,args.command)(**vars(args))
