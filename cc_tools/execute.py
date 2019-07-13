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
import re
from . import stdtools
from .stdtools import Handler
from .stdtools import tracebacker
from .stdtools import say
from .statetools import Convey
from .installers import SingularityManager
from .installers import LmodManager
from .installers import SpackManager
from .misc import write_user_yaml
from .settings import cc_user,default_modulefile_settings,specs
from .stdtools import bash
from .modulefile_templates import modulefile_basic
from .modulefile_templates import shell_connection_run,shell_connection_exec

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

    def main(self,
        singularity=None,lmod=None,spack=None,module_settings=None,
        **kwargs):
        print('status inferring use case')

        ### DEFAULTS

        # default module configuration
        if not module_settings:
            module_settings = default_modulefile_settings
        # module settings are saved in the state/cache
        self.cache['module_settings'] = module_settings

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
        singularity_modulefile = [
            'help([[ Singularity installed by community-collections ]])',
            'prepend_path("PATH","%s")'%
                os.path.join(os.path.realpath(singularity_inst.path),'bin')]
        # infer the version from singularity
        #! should this be done with another version checker?
        result = bash('./singularity/bin/singularity version',scroll=False)
        try: version = re.match(r'^(\d+\.\d+(?:\.\d+))',result['stdout']).group(1)
        except: raise Exception('failed to infer Singularity version')
        singularity_module_dn = 'modulefiles/cc/singularity'
        if not os.path.isdir(singularity_module_dn): 
            os.makedirs(singularity_module_dn)
        singularity_module_fn = 'modulefiles/cc/singularity/%s.lua'%version
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

class VersionCheck(Handler):
    _internals = {'name':'_name','meta':'meta'}
    def _version_number_compare(self,v1,v2):
        # via https://stackoverflow.com/questions/1714027
        def normalize(v):
            return [int(x) for x in re.sub(r'(\.0+)*$','', v).split(".")]
        # cmp is gone in python 3
        cmp = lambda a,b: (a > b) - (a < b)
        return cmp(normalize(v1),normalize(v2))
    def _version_check(self,version_this,op,version):
        return not (
            (op=='=' and not self._version_number_compare(version_this,version)==0) or
            (op=='>' and not self._version_number_compare(version_this,version)>0) or
            (op=='>=' and not self._version_number_compare(version_this,version)>=0))
    def _version_syntax(self,req):
        regex_version = r'^(=|==|>=|>)?([\d+\.]+)(.*?)$'
        op,version,suffix = None,0,None
        match = re.match(regex_version,req)
        if match: op,version,suffix = re.match(regex_version,req).groups()
        return op,version,suffix
    def _extract_number(self,result):
        items = []
        for i in result:
            match = re.match(r'^([\d\.]+)(.*?)$',i['name'])
            if match: reduced = match.groups()
            else: reduced = (i['name'],)
            items.append(reduced)
        return items
    def _check_version(self,splits,target,prefer_no_suffix=True):
        op,version,suffix = self._version_syntax(target) 
        if op==None: op = "=="
        candidates = []
        for split in splits:
            # the number extracter tries to ignore suffixes i.e. 1.2.3-wheezy
            this = split[0]
            # if the user supplied a suffix and we are seeking equality
            if suffix and op=="==" and version+suffix==''.join(split):
                candidates.append(''.join(split))
            # a normal version number without a suffix is checked against 
            #   all other version numbers and prefer_no_suffix determines if
            #   we allow found suffies to come along
            elif not suffix and (re.match(r'^[\d\.]+$',this) and
                self._version_check(this,op,version)):
                # insist on clean version numbers
                if not prefer_no_suffix or split[1]=='':
                    candidates.append(''.join(split))
                else: pass
        #print(candidates)
        #import ipdb;ipdb.set_trace()
        return candidates
    def docker(self,name,docker_version,prefer_no_suffix=True):
        """Check the dockerhub registry."""
        # import these inside the function because they come with anaconda
        import urllib,json
        import urllib.request
        url = "https://registry.hub.docker.com/v1/repositories/%s/tags"%name
        try: response = urllib.request.urlopen(url)
        except:
            raise Exception('failed to curl from: %s'%url)
        result = json.load(response)
        # we split the version to ignore suffixes
        splits = self._extract_number(result)
        # compare the requested version against the splits
        candidates = self._check_version(splits=splits,target=docker_version,
            prefer_no_suffix=prefer_no_suffix)
        return candidates
    def shub(self,shub_version):
        return shub_version

class PrepModuleRequest(Handler):
    _internals = {'name':'_name','meta':'meta'}
    def main(self,name,detail):
        """
        Requested modules are pre-processed here. This is largely designed to
        apply defaults and prepare them for processing by ModuleRequest.
        """
        result = {}
        # when detail is not a dict we assume it is the version
        if not isinstance(detail,dict):
            result['version'] = detail
            result['name'] = name
        # if the detail is a dict then it passes through
        else: 
            result['name'] = name
            if name in detail: 
                raise Exception('cannopt use "name" in a module request')
            result.update(**detail)
        return result

class ModuleRequest(Handler):
    _internals = {'name':'_name','meta':'meta'}
    @property
    def image_spot(self): return self.cache['settings']['images']
    def _write_modulefile(self,dn,fn,text,is_tcl=False):
        # write the modulefile
        fn = '%s%s'%(fn,'.lua' if not is_tcl else '')
        fn = os.path.join(dn,fn)
        with open(fn,'w') as fp: fp.write(text)
    def singularity_pull(self,name,source=None,
        version='latest',shell=None,calls=None,repo=None):
        """Develop a singularity pull function."""
        # always use lua
        is_tcl,text = False,modulefile_basic

        # prepare the spot for the image
        if not source: source = self.cache['module_settings']['source']
        dn = os.path.join(self.cache['case']['modulefiles'],name)
        if not os.path.isdir(dn): os.mkdir(dn)
        # the modulefile uses the relative path to the conda env for mksquashfs
        conda_env_relpath = os.path.join(os.path.relpath(specs['miniconda']),
            'envs',specs['envname'])
        detail = dict(
            image_spot=self.image_spot,
            conda_env=conda_env_relpath)

        # prepare the source for the pull command
        if source=='docker':
            #! +++ assume docker repo is the same as the module name
            repo_name = name if not repo else repo
            # the source will bne suffixed with the tag in the modulefile
            #   this is necessary when using the symlink method
            detail['source'] = 'docker://%s:'%repo_name
            #! note our Handler trick that uses the kwargs
            #!   this may seem counterintuitive
            versions = VersionCheck(name=repo_name,
                docker_version=version).solve
            if not versions:
                #! better error message
                raise Exception(('cannot satisfy dockerhub version: '
                    '%s:%s')%(repo_name,version))
        elif source=='shub':
            #! custom repo_name?
            shub_repo_name = name
            shub_version = VersionCheck(docker_version=version).solve
            shub_call = '%s:%s'%(shub_repo_name,shub_version)
            detail['source'] = 'docker://%s'%shub_call
        elif source=='library':
            repo_name = name if not repo else repo
            detail['source'] = 'library://%s:'%repo_name
            #! no version checking on the library yet
            versions = ('latest',)
        else: raise Exception('UNDER DEVELOPMENT, source: %s'%source)

        # prepare shell functions
        shell_calls = ''
        if ((calls and name not in calls) or not calls) and shell!=False:
            # +++ by default map the module name to singularity run
            # +++ allow the shell parameter to use a different alias
            shell_calls += shell_connection_run%dict(
                alias=name if shell==None else shell)
        # +++ extra aliases
        elif calls:
            # a list of calls implies identical aliases otherwise use dict
            if isinstance(calls,list):
                calls = dict([(i,i) for i in calls])
            for k,v in calls.items():
                shell_calls += shell_connection_exec%dict(alias=k,target=v)
        detail['shell_connections'] = shell_calls

        # write a single hidden base modulefile
        if versions:
            self._write_modulefile(dn=dn,fn='.base',
                text=text%detail)

        # loop over valid versions and create modulefiles
        # +++ assume that we want all tags that satisfy the version
        for tag in versions:
            modulefile_name = tag
            # +++ assume sif file
            # +++ formulate the module file name to resemble the lmod name
            name_image_base = '%s-%s'%(name,tag)
            #! the name is coded in the modulefile after implementing symlinks
            #!   detail['target'] = '%s.sif'%name_image_base
            """ the secret sauce: link to the base lua file which auto-detects
                its name to point to the right image. the act of symlinking
                all of the versions according to cc.yaml and the use of ">="
                means that we get the latest version, symlink it, and then
                Lmod automatically serves the latest available version. this
                only requires periodic ./cc refresh commands to stay current
            """
            target_link = os.path.join(dn,modulefile_name+'.lua')
            if not os.path.isfile(target_link):
                os.symlink(os.path.join('.base.lua',),
                    target_link)

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
            # preprocess the items
            prepped = PrepModuleRequest(name=key,detail=val).solve
            request = Convey(cache=self.state)(ModuleRequest)(**prepped).solve
        print('status community-collections is ready!')
