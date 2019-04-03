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

from statetools import Parser
from statetools import Cacher
from statetools import Convey

import stdtools
from stdtools import color_printer
# emphasize text printed from cc
color_printer(prefix=stdtools.say('[CC]','mag_gray'))

from cc_tools import Execute
from cc_tools import Preliminary
from cc_tools import CCStack
from cc_tools import UseCase
from settings import kickstart_yaml
from settings import cc_user
from settings import settings_resolver

# manage the state
state = {}

# send the state to the classes
Execute = Convey(state=state)(Execute)
CCStack = Convey(state=state)(CCStack)
UseCase = Convey(state=state)(UseCase)

@Cacher(
    # the interface uses the cache
    cache_fn='cache.json',
    cache=state)

class Interface(Parser):
    """
    A single call to this interface.
    """
    def go(self):
        """
        Build the environment, detect existing components, 
        and write a configuration.
        """
        # the ready flag indicates that miniconda reqs are installed
        if not self.cache.get('ready',False):
            #! disable the cache for this execution?
            #! make this step faster
            print('status establishing environment')
            # ensure conda environment is available because we need yaml
            stack = CCStack()
            stack.start_conda()
            stack.which()
            #! check that this worked?
            self.cache['ready'] = True
            self.standard_write()
        # continue once cache reports ready
        else: pass
        """
        is this environment-sourcing method optimal?
        note that we run the subshell function which modifies the 
        environment every time it runs. it might be better to make the
        cc tool dependent on the environment explicitly. for example we could:
        miniconda/envs/community-collections/bin/python ./cc debug
        """
        print('status entering subshell')
        #! replace os.system with a bash(subshell(cmd)) call
        os.system(('. miniconda/etc/profile.d/conda.sh '
            '&& conda activate community-collections && ./cc refresh'))

    def refresh(self):
        """
        Main execution loop.
        """
        print('status welcome to the "real" environment ...')
        # ensure that a cc.yaml file exists
        kickstart_yaml()
        import yaml
        with open(cc_user) as fp: 
            raw = yaml.load(fp,Loader=yaml.SafeLoader)
        # save the raw yaml
        self.cache['yaml_raw'] = raw
        # resolve the yaml with defaults if they are missing
        settings = settings_resolver(raw)
        self.cache['yaml'] = settings
        # preliminary changes to settings
        settings = Preliminary(**settings).solve
        # infer use case and remove associated keys
        settings = Convey(cache=self.cache)(UseCase)(**settings).solve
        # run the main loop by sending the yaml to the main handler
        me = Execute(name='CCExecuteLoop',**settings)
        # transmit variables to debug
        self.subshell = dict(me=me)
        # debug is also CLI function so no args
        self.debug()

    def nuke(self):
        """Testing only! Reset things! Be careful!"""
        print('status cleaning')
        os.system('rm -rf miniconda cc.yaml __pycache__ config.json *.pyc cache.dat')
        print('status done')

if __name__=='__main__':
    Interface()
