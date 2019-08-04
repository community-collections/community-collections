#!/usr/bin/env python

import os
import sys
import copy
import tempfile
from .settings import cc_user
from .settings import specs
from .settings import default_bootstrap
from .stdtools import bash
from .stdtools import tracebacker
from .settings import default_full  # for settings_resolver


def path_resolve(path):
    """
    Canonical way to resolve paths
    We convert relative paths with tilde to absolute paths without
    resolving symlinks
    """
    return os.path.realpath(os.path.expanduser(path))


def kickstart_yaml():
    """Start with the default user settings if absent."""
    if not os.path.isfile(cc_user):
        print('status writing default settings')
        with open(cc_user, 'w') as fp:
            fp.write(default_bootstrap)
        settings = default_bootstrap
    else:
        print('status found settings at %s' % cc_user)
        with open(cc_user) as fp:
            settings = fp.read()
    return settings


def write_user_yaml(data):
    import yaml
    with open(cc_user, 'w') as fp:
        yaml.dump(data, fp)


def cache_closer(self):
    """Hook before writing the cache."""
    # is this the correct way to pass a hook function into a class method?
    # remove the settings from the cache before saving
    #   since they should be written back to the settings if they are important
    for key in ['settings', 'settings_raw']:
        if key in self.cache:
            del self.cache[key]


# use a subshell command to run commands in conda before completing the
#   first execution of ./cc, before python is ready
#   after which time the cc wrapper script handles the environment
dependency_pathfinder = lambda x: os.path.realpath(
    os.path.expanduser(os.path.join(os.getcwd(), x)))
subshell = lambda x: '. %s && %s' % (
    os.path.join(
        dependency_pathfinder(specs['miniconda']),
        specs['conda_activator']), x)


def settings_resolver(settings_raw):
    """
    Flesh out the settings.
    """
    settings = copy.deepcopy(settings_raw)
    # note that we do a trivial top-level merge here. consider delveset
    for key, val in default_full.items():
        if key not in settings:
            settings[key] = val
    return settings


def enforce_env():
    """Prevent user from using the wrong environment."""
    # get the miniconda root in case it is installed in an arbitrary place
    miniconda_root = os.path.basename((specs['miniconda']).rstrip(os.path.sep))
    if not (
        os.path.dirname(sys.executable).split(os.path.sep)[-4:-1] ==
            [miniconda_root, 'envs', specs['envname']]):
        # some filesystems have an impartial clean which later causes this
        raise Exception(
            ('The python executable (%s) is not located '
             'in a miniconda. This means the environment is misconfigured. '
             'Consider cleaning this build and starting over.') %
            sys.executable)
    else:
        return os.path.sep.join([miniconda_root, 'envs', specs['envname']])


def shell_script(script, subshell=None, bin='bash', strict=True):
    """Run an anonymous bash script."""
    # strict is not connected
    if not subshell:
        subshell = lambda x: x
    out = script.strip()
    print('status executing the following script')
    print('\n'.join(['| '+i for i in out.splitlines()]))
    with tempfile.NamedTemporaryFile(delete=False) as fp:
        fp.write(out.encode())
        fp.close()
    try:
        bash(subshell('%s %s' % (bin, fp.name)))
    except Exception as e:
        tracebacker(e)
        return False
    else:
        return True
