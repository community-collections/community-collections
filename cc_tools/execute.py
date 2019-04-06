#!/usr/bin/env python

# Python 2/3 compatabilty and color printer
from __future__ import print_function
from __future__ import unicode_literals

"""
Execution logic for CC. 
Handles the transformation of settings files (the YAML file) to actions.
"""

import os
from . import stdtools
from .stdtools import Handler
from .statetools import Convey
from .installers import SingularityManager
from .installers import LmodManager
from .misc import write_user_yaml
from .settings import cc_user

class Preliminary(Handler):
    """Clean up the user settings. Runs before Execute."""
    def ignore_report(self,report=None,bashrc=None,**kwargs):
        return kwargs

class UseCase(Handler):
    """Clean up the user settings. Runs before Execute."""
    BASHRC_MODS = [
        'export MODULEPATH=%(modulefiles)s',
        'source %(root)s/lmod/init/bash']
    def main(self,singularity=None,lmod=None,**kwargs):
        print('status inferring use case')
        # default singularity settings
        if not singularity:
            #! note that this might be better handled by the settings_resolver?
            singularity = dict(path=SingularityManager.CHECK_PATH)
        # default lmod settings
        if not lmod:
            lmod = dict(
                root=LmodManager.CHECK_ROOT,
                modulefiles='./modulefiles')
        # beware the following except loops are hard to debug
        # instantiate a connection to Singularity
        try: singularity = Convey(cache=self.cache)(
            SingularityManager)(**singularity)
        # defer exceptions
        except Exception as e: 
            print(e)
            raise 
        # instantiate a connection to Lmod
        try: lmod = Convey(cache=self.cache)(LmodManager)(**lmod)
        # defer exceptions
        except Exception as e: 
            print(e)
            raise 
        # handle any errors above
        #! standardize the error reporting flags?
        has_singularity_error = self.cache.get('singularity_error',False)
        has_lmod_error = self.cache.get('lmod_error',False)
        if (has_singularity_error or has_lmod_error): 
            write_user_yaml(self.cache['yaml'])    
            raise Exception(('Caught errors. Edit %s to continue.')%cc_user)
        # check the modulefiles location
        modulefiles_dn = os.path.realpath(os.path.expanduser(lmod.modulefiles))
        if not os.path.isdir(modulefiles_dn):
            print('status failed to find modulefiles directory')
            print('status mkdir %s'%modulefiles_dn)
            os.mkdir(modulefiles_dn)
        # save lmod modulepath data to the cache
        #! need a standardized way of reporting what needs to be added to shells
        bashrc_subs = dict(root=lmod.root,
            modulefiles=modulefiles_dn)
        self.cache['yaml']['bashrc'] = {'instructions':(
            'Add the items in the "mods" dict in the bashrc dictionary to '
            'your ~/.bashrc file in order to use community collections. '
            'Be sure to remove leading hyphens (due to yaml). '
            'Source that file or log out and log back in to continue.'),
            'mods':[i%bashrc_subs for i in self.BASHRC_MODS]}
        # save the case for later
        self.cache['case'] = {
            'singularity':singularity.abspath,
            'lmod':lmod.root,
            'modulefiles':modulefiles_dn}
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
        print('warning if you got here then we found the software we need')
        print('warning ready to do something with LUA files?')
