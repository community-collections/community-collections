#/usr/bin/env python

# Python 2/3 compatabilty and color printer
from __future__ import print_function
from __future__ import unicode_literals

"""
Prototype for the Python interface to Community Collections (CC).
Currently offering this to the user via: `alias cc="python $(pwd)/cc"`.
"""

import sys
import os

import cc_tools
from cc_tools.statetools import Parser
from cc_tools.statetools import Cacher
from cc_tools.statetools import Convey
from cc_tools.statetools import StateDict

import cc_tools.stdtools
from cc_tools.stdtools import color_printer
from cc_tools.stdtools import confirm
# emphasize text printed from cc
color_printer(prefix=cc_tools.stdtools.say('[CC]','mag_gray'))

from cc_tools import Execute
from cc_tools import Preliminary
from cc_tools import CCStack
from cc_tools import UseCase
from cc_tools.settings import cc_user
from cc_tools.settings import specs
from cc_tools.misc import kickstart_yaml
from cc_tools.misc import settings_resolver
from cc_tools.misc import enforce_env
from cc_tools.misc import write_user_yaml

# manage the state
state = StateDict()

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
    def _get_settings(self):
        import yaml
        with open(cc_user) as fp: 
            raw = yaml.load(fp,Loader=yaml.SafeLoader)
        # save the raw yaml
        self.cache['yaml_raw'] = raw
        # resolve the yaml with defaults if they are missing
        settings = settings_resolver(raw)
        self.cache['yaml'] = settings
        return settings

    def bootstrap(self):
        """
        Build the environment, detect existing components, 
        and write a configuration.
        """
        # the ready flag indicates that miniconda reqs are installed
        if not self.cache.get('ready',False):
            # note the following procedure uses the subshell function
            #   to source the newly-installed environment but hereafter
            #   the cc wrapper script will find the right environment
            print('status establishing environment')
            # ensure conda environment is available because we need yaml
            stack = CCStack()
            stack.start_conda()
            stack.which()
            # this step gets the prefix for later and serves as a check
            miniconda_root = os.path.basename((
                specs['miniconda']).rstrip(os.path.sep))
            self.cache['prefix'] = os.path.join(os.getcwd(),
                os.path.sep.join([miniconda_root,'envs',specs['envname']]))
            self.cache['ready'] = True
            self.standard_write()
        # continue once cache reports ready
        else: pass
        # after the a bootstrap we call refresh to continue
        print('status entering subshell')
        os.system('./cc refresh')

    def refresh(self,debug=False):
        """
        Main execution loop.
        """
        # turn on state debugging
        if debug: self.cache._debug = True
        # rerun the bootstrap if not ready or cache was removed
        if not self.cache.get('ready',False):
            print('status failed to find cache so running bootstrap again')
            self.bootstrap()
            return
        # ensure that a cc.yaml file exists
        kickstart_yaml()
        enforce_env()
        settings = self._get_settings()
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

    def deploy_bashrc(self):
        self._get_settings()
        mods = self.cache.get('yaml',{}).get('bashrc',{}).get('mods',[])
        if mods:
            print('status proposed modifications to ~/.bashrc:')
            print('\n'.join(mods))
            if confirm('okay to add the above to your ~/.bashrc?',):
                bashrc_fn = os.path.expanduser('~/.bashrc')
                if os.path.isfile(bashrc_fn):
                    with open(bashrc_fn) as fp: text = fp.read()
                    text += '\n'+'\n'.join(mods)
                    with open(bashrc_fn,'w') as fp: 
                        fp.write(text)
                print('status to continue, log in again or '
                    'run this: source ~/.bashrc')
                if 'bashrc' in self.cache['yaml']:
                    del self.cache['yaml']['bashrc']
                write_user_yaml(self.cache['yaml'])
        else: print('status no bashrc notes in the settings')

    def nuke(self):
        """Testing only! Reset things! Be careful!"""
        print('status cleaning')
        os.system('rm -rf '+' '.join([
            'miniconda','cc.yaml','__pycache__',
            'config.json','*.pyc','cache.json',
            'modules','stage','lmod','Miniconda*.sh','tmp',
            ]))
        os.system('mkdir tmp')
        print('status done')

if __name__=='__main__':
    Interface()
