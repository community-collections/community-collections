#!/usr/bin/env python

# Python 2/3 compatabilty and color printer
from __future__ import print_function
from __future__ import unicode_literals

"""
Python interface to Community Collections (CC).
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

# emphasize text printed from cc
color_printer(prefix=cc_tools.stdtools.say('[CC]', 'mag_gray'))

# manage the state
global_debug = False  # for testing only
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
            raw = yaml.load(fp, Loader=yaml.SafeLoader)
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
        if not self.cache.get('ready', False):
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
            self.cache['prefix'] = \
                os.path.join(os.getcwd(),
                             os.path.sep.join(
                                 [miniconda_root, 'envs', specs['envname']]))
            self.cache['ready'] = True
            self._standard_write()
        # continue once cache reports ready
        else:
            pass
        # after the a bootstrap we call refresh to continue
        # the Cacher class maintains a "state" called cache that is transmitted
        #   to class instances and stores important information about the
        #   execution flow. after installing dependencies, to use them we need
        #   a new subshell. hence we write the cache now and turn off writing
        #   so the Cacher-based read/write of the cache in the subshell is not
        #   overriddden by this, the parent. we save first with try_else
        # self._try_else()
        self.cache['languish'] = True
        # you lose colors if you do this: bash('./cc refresh')
        # relative path okay here?
        print('status running a subshell to complete the installation')
        os.system('./cc refresh')
        sys.exit(0)

    def refresh(self, debug=False):
        """
        The MAIN function. Start here.
        Update modulefiles and install necessary components.
        This command interprets cc.yaml, which is created if needed.
        Install Community-Collections with this command, edit cc.yaml
        to customize it, and then refresh again.
        """
        # turn on state debugging
        if debug:
            self.cache._debug = True
        # rerun the bootstrap if not ready or cache was removed
        if not self.cache.get('ready', False):
            print('status failed to find cache so running bootstrap again')
            self._bootstrap()
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
        me = Execute(name='CCExecuteLoop', **settings)
        # transmit variables to debug
        self.subshell = dict(me=me)
        # debug is also CLI function so no args
        # self.debug()

    def profile(self, explicit=False, bashrc=True, profile='profile_cc.sh'):
        """
        Add changes to a bashrc file.
        Note that the explicit flag will direct changes to a profile.
        """
        self._get_settings()
        mods = \
            self.cache.get('settings', {}).get('profile', {}).get('mods', [])
        if not explicit:
            profile_detail = dict(
                fn=os.path.abspath(os.path.expanduser(profile)),
                mods=list(mods))
            mods = ['source %s' % profile_detail['fn']]
        else:
            profile_detail = None
        # always write a profile script
        if profile_detail and profile_detail['mods']:
            # removed overwrite protection because the profile is permanently
            #   stored in the settings hence you can regenerate it at will
            with open(profile_detail['fn'], 'w') as fp:
                fp.write('\n'.join(profile_detail['mods']))
            print('status to use CC, run: source %s' %
                  os.path.abspath(profile_detail['fn']))
        # by default the bashrc flag signals an update to the bashrc
        # otherwise the above code only writes the profile script
        if mods and bashrc:
            print('status proposed modifications to ~/.bashrc:')
            print('\n'.join(mods))
            if confirm('okay to add the above to your ~/.bashrc?',):
                bashrc_fn = os.path.expanduser('~/.bashrc')
                if os.path.isfile(bashrc_fn):
                    with open(bashrc_fn) as fp:
                        text = fp.read()
                    previous = [m for m in mods if re.search(m, text)]
                    if any(previous):
                        raise Exception(
                            'refusing to update because bashrc contains '
                            ' modifications from a previous run: %s' %
                            str(previous))
                    text += '\n# community-collections\n'+'\n'.join(mods)+'\n'
                    with open(bashrc_fn, 'w') as fp:
                        fp.write(text)
                print('status to continue, log in again or '
                      'use "source ~/.bashrc"')
                # should we record this in the cache?
                if 'bashrc' in self.cache['settings']:
                    del self.cache['settings']['bashrc']
                write_user_yaml(self.cache['settings'])
        else:
            print('status no bashrc notes in the settings')

    def clean(self, sure=False):
        """
        Remove all installed components from this folder.
        Use this command before reinstalling supporting software with
        the refresh command.
        """
        import shutil
        print('status cleaning')
        fns = [i for j in [glob.glob(k) for k in [
            'miniconda', 'cc.yaml', '__pycache__',
            'config.json', '*.pyc', 'cache.json',
            'modules', 'stage', 'lmod', 'Miniconda*.sh', 'tmp',
            'spack', 'singularity', 'profile_cc.sh',
            ]] for i in j]
        fns += [i for i in glob.glob('modulefiles/*') if i != 'modulefiles/cc']
        self.cache = {}
        print('status removing: %s' % ', '.join(fns))
        if sure or confirm('okay to remove the files above?',):
            for fn in fns:
                shutil.rmtree(fn) if os.path.isdir(fn) else os.remove(fn)
            # os.mkdir('tmp')
            print('status done')

    def showcache(self):
        """
        Print the internal cache for the cc program during debugging.
        """
        self.cache._debug = False
        from cc_tools.stdtools import treeview
        treeview(self.cache, style='json')

    def enable(self):
        """
        Use sudo to enable many features provided by Singularity 3.
        This command reports the setuid modifications to the Singularity
        installation.
        """
        self.capable(enable=True)

    def capable(self, enable=False):
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
        singularity_path = self.cache.get('settings', {}).get(
            'singularity', {}).get('path', {})
        if not singularity_path:
            print('warning cannot find singularity/path in %s' % cc_user)
        starter_fn = os.path.join(singularity_path,
                                  'libexec', 'singularity',
                                  'bin', 'starter-suid')
        st = os.stat(starter_fn)
        correct_suid_bit = oct(st.st_mode)[-4:] == '4755'
        if not correct_suid_bit:
            print('warning the starter needs permissions 4755: %s' %
                  starter_fn)
        root_owns = pwd.getpwuid(os.stat(starter_fn).st_uid).pw_uid == 0
        if not root_owns:
            print('warning root must own: %s' % starter_fn)
        etc_ownership = {}
        etc_sudo_owns = ['singularity.conf', 'capability.json', 'ecl.toml']
        for fn in etc_sudo_owns:
            # standard installation uses /etc not /usr/etc
            if singularity_path == '/usr':
                singularity_path_etc = '/etc'
            else:
                singularity_path_etc = os.path.join(singularity_path, 'etc')
            fn_abs = os.path.join(singularity_path_etc, 'singularity', fn)
            owned = pwd.getpwuid(os.stat(fn_abs).st_uid).pw_uid == 0
            etc_ownership[fn_abs] = owned
            if not owned:
                print('warning root must own: %s' % fn_abs)
        recommend = []
        for fn in etc_ownership:
            if not etc_ownership[fn]:
                recommend += ['chown root:root %s' % (fn)]
        if not root_owns:
            recommend += ['chown root:root %s' % (starter_fn)]
        # if root does not own the suid file then we must also chmod
        #   because the ownership change will drop the suid bit
        if not correct_suid_bit or not root_owns:
            recommend += ['chmod 4755 %s' % (starter_fn)]
        if recommend:
            print('status run the following commands as '
                  'root to give singularity the standard permissions: ')
            print('\n'+'\n'.join(recommend)+'\n')
            print('status Run "sudo ./cc enable" to do this automatically.')
            if enable:
                print('status attempting to run the commands above')
                from cc_tools.misc import shell_script
                result = shell_script('\n'.join(recommend), strict=True)
                if not result:
                    # under development
                    raise Exception('setting admin rights failed')
        else:
            print('status singularity is owned by root and ready for use')

    def test(self, name, sandbox=False, sure=False):
        """
        Run a unit test. Simulations the installs, settings edits, and refresh.
        """
        if not sure:
            # we force the sure flag to avoid interfacing the bash function
            #   with user input for now
            raise Exception(
                'You must pass the "--sure" flag however BE CAREFUL because '
                'this deletes any locally-installed software.')
        commands = {
            'base': [
                './cc clean --sure',
                './cc refresh',
                'patch cc.yaml cc_tools/test_install_lmod.diff',
                './cc refresh', ]+(
                    ['patch cc.yaml cc_tools/test_sandbox.diff']
                    if sandbox else []) +
                ['patch cc.yaml cc_tools/test_install_singularity.diff',  # noqa
                './cc refresh',
                './cc profile --no-bashrc',
                # note that after this test you can remove cc.yaml and refresh
                #   in which case lmod is found but singularity needs a path
                ],
            }
        if name not in commands:
            raise Exception('invalid test "%s". select from: %s' % (
                name, commands.keys()))
        for cmd in commands[name]:
            # bash function fails here with ascii error bash(cmd,announce=True)
            # issue: fix the bash function and replace the system call below
            os.system(cmd)

    def docs(self, push=False):
        """
        Render sphinx docs.
        """
        # we call a custom make target which gets the path to miniconda sphinx
        import shutil
        builddir = 'docs/build'
        if os.path.exists(builddir) and os.path.isdir(builddir):
            shutil.rmtree(builddir)
        bash('make custom_html', cwd='docs')
        upstream = (
            'https://github.com/community-collections/'
            'community-collections.github.io.git')
        if push:
            """
            the community-collections repository hosts the docs source which
            can be built and rendered locally from miniconda but also
            pushed to a separate repository (by the authors)
            note that you may need to use:
                git config --global user.email
                git config --global user.name
            """
            # explicit git from conda because containers only have git<2
            git_path = os.path.join(os.getcwd(),
                                    'miniconda', 'envs', specs['envname'],
                                    'bin', 'git')
            detail = dict(git=git_path, upstream=upstream)
            where = 'docs/build/html'
            commands = [
                '%(git)s init || echo "already initialized"',
                '%(git)s remote add origin '
                '%(upstream)s || echo "origin exists"',
                '%(git)s fetch origin master',
                '%(git)s checkout -b new_changes || git checkout new_changes',
                '%(git)s add .',
                '%(git)s commit -m "refreshing docs on '
                '$(date +%%Y.%%m.%%d.%%H%%M)"',
                '%(git)s checkout master',
                # note that this require a newer git
                '%(git)s merge -X theirs --allow-unrelated-histories '
                '-m "refreshing docs" new_changes',
                '%(git)s commit -m "refreshing docs" || '
                'echo "committed already" # nothing to commit',
                '%(git)s push', ]
            for cmd in commands:
                bash(cmd % detail, cwd=where, announce=True)


if __name__ == '__main__':
    Interface()
