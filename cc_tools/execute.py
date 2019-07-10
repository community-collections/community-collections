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
    # tracebacks during development hidden from the user
    _debug = True
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
            # add modifications to existing ones in the settings
            mods_prev = self.cache['settings'].get('bashrc',{}).get('mods',[])
            mods = mods_prev + mods
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
                root=LmodManager.CHECK_ROOT)

        ### INSTALLERS

        # instantiate a connection to Lmod
        try: lmod_inst = Convey(cache=self.cache,
            _register_error=register_error
            )(LmodManager)(**lmod)
        # defer exceptions
        except Exception as e: 
            if self._debug: tracebacker(e)
            pass

        # instantiate a connection to Singularity
        try: singularity_inst = Convey(
            cache=self.cache,
            _register_error=register_error
            )(SingularityManager)(**singularity)
        # defer exceptions
        except Exception as e: 
            if self._debug: tracebacker(e)
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
        # turn tracebacks on again if we complete the loop
        else: self.cache['traceback_off'] = False

        # confirm essential modulefiles
        #! hardcoding the modulefile location for now
        singularity_module_fn = 'modulefiles/singularity.lua'
        singularity_modulefile = [
            'help([[ Singularity installed by community-collections ]])',
            'prepend_path("PATH","%s")'%
                os.path.join(singularity_inst.path,'bin')]
        with open(singularity_module_fn,'w') as fp:
            fp.write('\n'.join(singularity_modulefile))
        
        # save the case for later
        self.cache['case'] = {
            'lmod':lmod_inst.root,
            'modulefiles':lmod_inst.modulefiles,
            'singularity':singularity_inst.path,}
        # optional information
        if spack and spack_inst!=False:
            self.cache['case']['spack'] = spack_inst.abspath

        self._shutdown()
        # pass the arguments through
        return kwargs

### Modulefile Templates

whitelist_basic = """
local images_dn = "%(image_spot)s"
local target = "%(target)s"
local source = "%(source)s"

load('singularity')

function resolve_tilde(s)
    return(s:gsub("^~",os.getenv("HOME")))
end

local images_dn_abs = resolve_tilde(images_dn)
local target_fn = pathJoin(images_dn_abs,target)

if mode()=="load" then
    if lfs.attributes(images_dn_abs,'mode')==nil then
        io.stderr:write("[CC] making a cache directory: " .. images_dn_abs .. "\\n")
        lfs.mkdir(images_dn_abs)
    end
    if lfs.attributes(target_fn,'mode')==nil then
        -- cc/env includes squashfs tools
        -- !! conda.lua and env.lua were conflicting so I hardcoded one in the other
        load('cc/env')
        io.stderr:write("[CC] fetching " .. target .. "\\n")
        local cmd = 'singularity pull ' .. target_fn .. ' ' .. source
        execute {cmd=cmd,modeA={"load"}}
        -- !! should we conditionally unload this if it was not loaded before, for opaqueness?
        unload('cc/env')
    end
    set_shell_function('%(bin_name)s',"singularity run " .. target_fn,"singularity run " .. target_fn)
end
"""

class ModuleFileBase(Handler):
    _internals = {'name':'_name','meta':'meta'}
    @property
    def image_spot(self):
        #! no init for Handler means this is the best way to get the image spot
        #! self.images = Convey(cache=self.cache)(ImageCache)()
        return self.cache['settings']['images']
    
    def versionless(self,name,versionless=True):
        #! clumsy. replace 'julia: versionless' with a subdict?
        if not versionless: raise Exception('handler call went awry')
        # make the directory
        #! alternate file structure with compiler versions?
        dn = os.path.join(self.cache['case']['modulefiles'],name)
        if not os.path.isdir(dn): os.mkdir(dn)
        detail = dict(image_spot=self.image_spot)
        #! hardcoded example during development
        detail['target'] = 'julia.sif'
        #! detail['source'] = 'library://sylabs/examples/julia:latest'
        detail['source'] = 'docker://julia'
        detail['bin_name'] = 'julia'
        """
        modulefiles:
            1. base modulefile for latest links to a version number
            2. version number linked to generic
            3. generic modulefile infers its name and does the right singularity pulll
        questions
            how does the generic modulefile know it's name?
            how does it know where to do the pull from? from cc.yaml? from an internal toc?
            how does it check the cache location?
        note that we need lua functions that answer all of these questions
        pseudocode for the modulefile:
            on load, make a cache directory if absent and run singularity pull
            then add a shell function
            to handle versions, inject the version into the download image file name
            then use symbolic links for the version number and the latest
            see "whitelist_basic" template above
        """
        is_tcl,text = False,whitelist_basic
        fn = os.path.join(dn,'%s%s'%(name,'.lua' if not is_tcl else ''))
        with open(fn,'w') as fp:
            fp.write(text%detail)

class Execute(Handler):
    """
    The main execution loop. "Runs" the user setting file.
    Always decorate via: `Execute = Convey(state=state)(Execute)`
    """
    def whitelist(self,whitelist,images):
        """
        Handle the whitelist scenario.
        """
        # separate the whitelist from the software settings
        self.whitelist = whitelist
        # build modulefiles for everything on the whitelist
        for key,val in self.whitelist.items():
            # base case in which there is no subdict and we ask for versionless
            if val=='versionless':
                # convey the state/cache for global settings
                Convey(cache=self.state)(ModuleFileBase)(
                    name=key,versionless=True).solve
            #!!! development
            else: print('warning cannot process: %s,%s'%(key,str(val)))
        print('status community-collections is ready!')
