#!/usr/bin/env python

import os,sys
import copy
from .settings import cc_user
from .settings import specs
from .settings import default_bootstrap

def kickstart_yaml():
    """Start with the default user settings if absent."""
    if not os.path.isfile(cc_user):
        print('status writing default settings')
        with open(cc_user,'w') as fp:
            fp.write(default_bootstrap)
        settings = default_bootstrap
    else: 
        print('status found settings at %s'%cc_user)
        with open(cc_user) as fp: 
            settings = fp.read()
    return settings

def write_user_yaml(data):
    import yaml
    with open(cc_user,'w') as fp:
        yaml.dump(data,fp)

# use a subshell command to run commands in conda before completing the
#   first execution of ./cc, before python is ready
#   after which time the cc wrapper script handles the environment
dependency_pathfinder = lambda x: os.path.realpath(
    os.path.expanduser(os.path.join(os.getcwd(),x)))
subshell = lambda x: '. %s && %s'%(
    os.path.join(
        dependency_pathfinder(specs['miniconda']),
        specs['conda_activator']),x)

from .settings import default_full

def settings_resolver(settings_raw):
    """
    Flesh out the settings.
    """
    settings = copy.deepcopy(settings_raw)
    #! note that we do a trivial top-level merge here. consider delveset
    for key,val in default_full.items():
        if key not in settings:
            settings[key] = val
    return settings

def enforce_env():
    """Prevent user from using the wrong environment."""
    # get the miniconda root in case it is installed in an arbitrary place
    miniconda_root = os.path.basename((specs['miniconda']).rstrip(os.path.sep))
    if not (
        os.path.dirname(sys.executable).split(os.path.sep)[-4:-1]==
        [miniconda_root,'envs',specs['envname']]):
        raise Exception(('The python executable (%s) is not located '
            'in a miniconda which probably means you need to '
            'kickstart with: ./cc bootstrap')%sys.executable)
