#!/usr/bin/env python

# Python 2/3 compatabilty and color printer
from __future__ import print_function
from __future__ import unicode_literals

"""
Execution logic for CC. 
Handles the transformation of settings files (the YAML file) to actions.
"""

import os
import sys
from . import stdtools
from .stdtools import Handler
from .stdtools import tracebacker
from .stdtools import say
from .statetools import Convey
from .installers import SingularityManager
from .installers import LmodManager
from .installers import SpackManager
from .misc import write_user_yaml
from .settings import cc_user

def register_error(self,name,error):
    """
    During development we track errors in the cache.
    This could be moved inside a class later.
    """
    if 'errors' not in self.cache:
        self.cache['errors'] = {}
    self.cache['errors'][name] = error

class Preliminary(Handler):
    """Clean up the user settings. Runs before Execute."""
    def ignore_report(self,report=None,bashrc=None,**kwargs):
        return kwargs

class UseCase(Handler):
    """Clean up the user settings. Runs before Execute."""

    def _shutdown(self):
        """
        End this session of the UseCase by updating the settings.
        """
        self._stage_bashrc_changes()
        write_user_yaml(self.cache['settings'])

    def _stage_bashrc_changes(self):
        """
        Add a list of bashrc changes to the user settings.
        The user can apply the changes with ./cc update_bashrc
        """
        mods = self.cache.pop('bashrc_mods',[])
        if mods:
            self.cache['settings']['bashrc'] = {'instructions':(
                'Run ./cc update_bashrc to add modules to your environment '
                'automatically. Alternately, you can add the items in the '
                '"mods" list in the bashrc dictionary to '
                'your ~/.bashrc file (be sure to remove yaml syntax). '
                'Run `source ~/.bashrc` or log in again to use CC properly. '),
                'mods':mods}

    def main(self,singularity=None,lmod=None,spack=None,**kwargs):
        print('status inferring use case')

        ### DEFAULTS

        # default singularity settings
        if not singularity:
            #! note that this might be better handled by the settings_resolver?
            singularity = dict(path=SingularityManager.CHECK_PATH)

        # default lmod settings
        if not lmod:
            lmod = dict(
                # the default signals to the manager to detect lmod
                root=LmodManager.CHECK_ROOT,
                modulefiles='./modulefiles')

        ### INSTALLERS

        """
        # DEVELOPMENT
        # instantiate a connection to Singularity
        try: singularity_inst = Convey(
            cache=self.cache,
            _register_error=register_error
            )(SingularityManager)(**singularity)
        # defer exceptions
        except Exception as e: 
            if debug: tracebacker(e)
            else: pass
        """

        # instantiate a connection to Lmod
        try: lmod_inst = Convey(cache=self.cache,
            _register_error=register_error
            )(LmodManager)(**lmod)
        # defer exceptions
        except Exception as e: 
            tracebacker(e)
            pass

        # include spack only if requested
        if spack:
            try: spack_inst = Convey(
                cache=self.cache,
                _register_error=register_error
                )(SpackManager)(**spack)
            # null value since this is optional
            except Exception as e: spack_inst = False

        # report the python errors
        # note that errors remain in the cache until they are removed
        #   by a refresh run that ends in e.g. report_ready
        errors = self.cache.get('errors',{})
        for name,error in errors.items():
            print('error caught error during "%s"'%name)
            if isinstance(error,dict):
                print('\n'.join(error['formatted']).strip())
                print('status python error: %s'%error['result'])
            # if not a dict we send a string to explain the error
            else: print('status received error: %s'%error)

        # exit on error
        if errors:
            self._shutdown()
            # exceptions are too verbose so we tell user to edit and exit
            print(say('[CC]','mag_gray')+' '+say('[STATUS]','red_black')+
                ' Edit %s and rerun to continue.'%cc_user)
            # note that we do not show a real traceback on this exception
            self.cache['traceback_off'] = True
            raise Exception('exiting for user edits')
        
        # save the case for later
        self.cache['case'] = {
            'lmod':lmod_inst.root,
            'modulefiles':lmod_inst.modulefiles}
        # optional information
        if spack and spack_inst!=False:
            self.cache['case']['spack'] = spack_inst.abspath

        self._shutdown()
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
