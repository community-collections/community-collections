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
import glob
import re

import cc_tools
from cc_tools.statetools import Parser
from cc_tools.statetools import Cacher
from cc_tools.statetools import Convey
from cc_tools.statetools import StateDict

import cc_tools.stdtools
from cc_tools.stdtools import color_printer
from cc_tools.stdtools import confirm
from cc_tools.stdtools import bash
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
from cc_tools.misc import cache_closer

# manage the state
global_debug = False #! testing only
state = StateDict(debug=global_debug)

# send the state to the classes
Execute = Convey(state=state)(Execute)
CCStack = Convey(state=state)(CCStack)
UseCase = Convey(state=state)(UseCase)

@Cacher(
    cache_fn='cache.json',
    closer=cache_closer,
    cache=state,)

class Interface(Parser):
    """
    A single call to this interface.
    """
    def _get_settings(self):
        import yaml
        with open(cc_user) as fp: 
            raw = yaml.load(fp,Loader=yaml.SafeLoader)
        # save the raw yaml
        self.cache['settings_raw'] = raw
        # resolve the yaml with defaults if they are missing
        settings = settings_resolver(raw)
        self.cache['settings'] = settings
        return settings

    def _bootstrap(self):
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
            self._standard_write()
        # continue once cache reports ready
        else: pass
        # after the a bootstrap we call refresh to continue
        # the Cacher class maintains a "state" called cache that is transmitted
        #   to class instances and stores important information about the 
        #   execution flow. after installing dependencies, to use them we need
        #   a new subshell. hence we write the cache now and turn off writing
        #   so the Cacher-based read/write of the cache in the subshell is not
        #   overriddden by this, the parent. we save first with try_else
        #! self._try_else()
        self.cache['languish'] = True
        #! you lose colors if you do this: bash('./cc refresh')
        #! relative path okay here?
        print('status running a subshell to complete the installation')
        os.system('./cc refresh')
        sys.exit(0)

    def refresh(self,debug=False):
        """
        The MAIN function. Start here. 
        Update modulefiles and install necessary components. 
        This command interprets cc.yaml, which is created if needed.
        Install Community-Collections with this command, edit cc.yaml 
        to customize it, and then refresh again.
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
        #! self.debug()

    def profile(self,explicit=False,bashrc=True,profile='profile_cc.sh'):
        """
        Add changes to a bashrc file.
        Note that the explicit flag will direct changes to a profile.
        """
        self._get_settings()
        mods = self.cache.get('settings',{}).get('bashrc',{}).get('mods',[])
        if not explicit: 
            profile_detail = dict(
                fn=os.path.abspath(os.path.expanduser(profile)),
                mods=list(mods))
            mods = ['source %s'%profile_detail['fn']]
        else: profile_detail = None
        # always write a profile script
        if profile_detail and profile_detail['mods']: 
        #! ideally we would compare the existing profile to
            #!   see if we need to add to it but for now we are strict
            if os.path.isfile(profile_detail['fn']):
                raise Exception('refusing to overwrite %s'%profile_detail['fn'])
            with open(profile_detail['fn'],'w') as fp:
                fp.write('\n'.join(profile_detail['mods']))
            print('status to use CC, run: source %s'%
                os.path.abspath(profile_detail['fn']))
        # by default the bashrc flag signals an update to the bashrc
        # otherwise the above code only writes the profile script
        if mods and bashrc:
            print('status proposed modifications to ~/.bashrc:')
            print('\n'.join(mods))
            if confirm('okay to add the above to your ~/.bashrc?',):
                bashrc_fn = os.path.expanduser('~/.bashrc')
                if os.path.isfile(bashrc_fn):
                    with open(bashrc_fn) as fp: text = fp.read()
                    previous = [m for m in mods if 
                        re.search(m,text)]
                    if any(previous):
                        raise Exception('refusing to update because bashrc contains '
                            ' modifications from a previous run: %s'%str(previous))
                    text += '\n# community-collections\n'+'\n'.join(mods)+'\n'
                    with open(bashrc_fn,'w') as fp: 
                        fp.write(text)
                print('status to continue, log in again or '
                    'run this: source ~/.bashrc')
                #! should we record this in the cache?
                if 'bashrc' in self.cache['settings']:
                    del self.cache['settings']['bashrc']
                write_user_yaml(self.cache['settings'])
        else: print('status no bashrc notes in the settings')

    def reset(self,sure=False):
        """
        Remove all installed components from this folder. 
        Use this command to reinstall supporting software.
        """
        import shutil
        print('status cleaning')
        fns = [i for j in [glob.glob(k) for k in [
            'miniconda','cc.yaml','__pycache__',
            'config.json','*.pyc','cache.json',
            'modules','stage','lmod','Miniconda*.sh','tmp',
            'spack','singularity','profile_cc.sh',
            ]] for i in j]
        fns += [i for i in glob.glob('modulefiles/*') if i!='modulefiles/cc']
        self.cache = {}
        print('status removing: %s'%', '.join(fns))
        if sure or confirm('okay to remove the files above?',):
            for fn in fns: 
                shutil.rmtree(fn) if os.path.isdir(fn) else os.remove(fn)
            #! os.mkdir('tmp')
            print('status done')

    def showcache(self):
        """
        Print the internal cache for the cc program during debugging.
        """
        self.cache._debug = False
        from cc_tools.stdtools import treeview
        treeview(self.cache,style='pprint')

    def enable(self):
        """
        Use sudo to enable many features provided by Singularity 3. 
        This command reports the setuid modifications to the Singularity
        installation.
        """
        self.capable(enable=True)

    def capable(self,enable=False):
        """
        This command checks if the administrator has enabled Singularity.
        If Singularity does not have the setuid enabled, it will provide
        instructions for a root user to enable it. See the "enable" 
        subcommand to do this automatically.
        """
        # catch errors here
        self.cache['traceback_off'] = False
        import pwd
        self._get_settings()
        singularity_path = self.cache.get('settings',{}).get(
            'singularity',{}).get('path',{})
        if not singularity_path:
            print('warning cannot find singularity/path in %s'%cc_user)
        starter_fn = os.path.join(singularity_path,
            'libexec','singularity','bin','starter-suid') 
        st = os.stat(starter_fn)
        correct_suid_bit = oct(st.st_mode)[-4:]=='4755'
        if not correct_suid_bit:
            print('warning the starter needs permissions 4755: %s'%starter_fn)
        root_owns = pwd.getpwuid(os.stat(starter_fn).st_uid).pw_uid==0
        if not root_owns:
            print('warning root must own: %s'%starter_fn)
        etc_ownership = {}
        etc_sudo_owns = ['singularity.conf','capability.json','ecl.toml']
        for fn in etc_sudo_owns:
            fn_abs = os.path.join(singularity_path,'etc','singularity',fn)
            owned = pwd.getpwuid(os.stat(fn_abs).st_uid).pw_uid==0
            etc_ownership[fn_abs] = owned
            if not owned: print('warning root must own: %s'%fn_abs)
        recommend = []
        for fn in etc_ownership:
            if not etc_ownership[fn]:
                recommend += ['chown root:root %s'%(fn)]
        if not root_owns:
            recommend += ['chown root:root %s'%(starter_fn)]
        # if root does not own the suid file then we must also chmod
        #   because the ownership change will drop the suid bit
        if not correct_suid_bit or not root_owns:
            recommend += ['chmod 4755 %s'%(starter_fn)]
        if recommend:
            print('status run the following commands as '
                'root to give singularity the standard permissions: ')
            print('\n'+'\n'.join(recommend)+'\n')
            if force:
                print('status attempting to run the commands above')
                from cc_tools.misc import shell_script
                result = shell_script('\n'.join(recommend))
                if not result:
                    #! under development
                    raise Exception('setting admin rights failed')
        else: print('status singularity is owned by root and ready for use')

if __name__=='__main__':
    Interface()
