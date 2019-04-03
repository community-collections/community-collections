#!/usr/bin/env python

# Python 2/3 compatabilty and color printer
from __future__ import print_function
from __future__ import unicode_literals

"""
Execution logic for CC. 
Handles the transformation of settings files (the YAML file) to actions.
"""

import stdtools
from stdtools import Handler
from statetools import Convey
from .installers import Singularity
from settings import write_user_yaml
from settings import cc_user

class Preliminary(Handler):
    """Clean up the user settings. Runs before Execute."""
    def ignore_report(self,report=None,**kwargs):
        return kwargs

class UseCase(Handler):
    """Clean up the user settings. Runs before Execute."""
    def main(self,singularity=None,lmod=None,**kwargs):
        print('status inferring use case')
        # default singularity settings
        if not singularity:
            #! note that this might be better handled by the settings_resolver?
            singularity = dict(path=Singularity.CHECK_PATH)
        # instantiate a connection to Singularity
        try: singularity = Convey(cache=self.cache)(Singularity)(**singularity)
        # defer exceptions
        except Exception: pass
        #! repeat this pattern for lmod here
        # handle any errors above
        has_singularity_error = self.cache.get('singularity_error',False)
        if (has_singularity_error): 
            write_user_yaml(self.cache['yaml'])    
            raise Exception(('Caught errors. Edit %s to continue.')%cc_user)
        # save the case for later
        self.cache['case'] = {'singularity':singularity.abspath}
        # rewrite the settings here since the installer classes modify them
        write_user_yaml(self.cache['yaml'])
        # pass the arguments through
        return kwargs

class Execute(Handler):
    """
    The main execution loop. "Runs" the user setting file.
    Always decorate via: `Execute = Convey(state=state)(Execute)`
    """
    def whitelist(self,whitelist):
        """
        Handle the whitelist scenario.
        """
        # separate the whitelist from the software settings
        self.whitelist = whitelist
        print('warning bleeding edge is here ...')
        print('warning if you got here then we found the softare we need')
        print('warning ready to do something with LUA files?')
