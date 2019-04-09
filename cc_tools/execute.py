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
    BASHRC_MODS = [
        'export MODULEPATH=%(modulefiles)s',
        'source %(root)s/lmod/init/bash']

    def _handle_bashrc(self):
        """
        This function picks up any bashrc modifications and puts them in the 
        settings file after which time the user can deploy them with 
        update_bashrc.
        """
        pass

    def _shutdown(self):
        """
        End this session of the UseCase by updating the settings.
        """
        write_user_yaml(self.cache['settings'])
        self._handle_bashrc()

    def main(self,singularity=None,lmod=None,spack=None,**kwargs):
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

        # SEQUENTIALLY CONNECT TO COMPONENTS
        # beware the following except loops are hard to debug
        debug = True

        """

        # instantiate a connection to Singularity
        try: singularity_inst = Convey(
            cache=self.cache,
            _register_error=register_error
            )(SingularityManager)(**singularity)
        # defer exceptions
        except Exception as e: 
            if debug: tracebacker(e)
            else: pass

        # instantiate a connection to Lmod
        try: lmod_inst = Convey(cache=self.cache,
            _register_error=register_error
            )(LmodManager)(**lmod)
        # defer exceptions
        except Exception as e: 
            if debug: tracebacker(e)
            else: pass

        """

        # include spack only if requested
        if spack:
            try: spack_inst = Convey(
                cache=self.cache,
                _register_error=register_error
                )(SpackManager)(**spack)
            except Exception as e: 
                if debug: tracebacker(e)
                else: pass
                # null value since this is optional
                spack_inst = False

        # consume and report the python errors
        errors = self.cache.pop('errors',{})
        for name,error in errors.items():
            print('error caught error during "%s"'%name)
            print('\n'.join(error['formatted']).strip())
            print('status resulting error was: %s'%error['result'])

        #!!! # handle any errors above
        #!!! #! standardize the error reporting flags?
        #!!! has_singularity_error = self.cache.get('singularity_error',False)
        #!!! has_lmod_error = self.cache.get('lmod_error',False)
        #!!! if (has_singularity_error or has_lmod_error): 
        if errors:
            self._shutdown()
            # exceptions are too verbose so we tell user to edit and exit
            print(say('[CC]','mag_gray')+' '+say('[STATUS]','red_black')+
                ' Edit %s and rerun to continue.'%cc_user)
            sys.exit(1)

        # check the modulefiles location
        modulefiles_dn = os.path.realpath(
            os.path.expanduser(lmod_inst.modulefiles))
        if not os.path.isdir(modulefiles_dn):
            print('status failed to find modulefiles directory')
            print('status mkdir %s'%modulefiles_dn)
            os.mkdir(modulefiles_dn)

        # save lmod modulepath data to the cache
        #! need a standardized way of reporting what needs to be added to shells
        bashrc_subs = dict(root=lmod_inst.root,
            modulefiles=modulefiles_dn)
        self.cache['settings']['bashrc'] = {'instructions':(
            'Run ./cc update_bashrc to add modules to your environment '
            'automatically. Alternately, you can dd the items in the "mods" '
            'list in the bashrc dictionary to '
            'your ~/.bashrc file (be sure to remove yaml syntax). '
            'Run `source ~/.bashrc` log back in to continue. '
            'Either way, this step will make the `module` command available. '),
            'mods':[i%bashrc_subs for i in self.BASHRC_MODS]}
        # save the case for later
        self.cache['case'] = {
            'singularity':singularity_inst.abspath,
            'lmod':lmod_inst.root,
            'modulefiles':modulefiles_dn}
        # optional information
        if spack_inst!=False:
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

