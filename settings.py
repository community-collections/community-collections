#!/usr/bin/env python

import os
import copy

"""
SETTINGS FOR COMMUNITY COLLECTIONS
"""

# the user file
#! make this flexible?
cc_user = 'cc.yaml'

def write_user_yaml(data):
    import yaml
    with open(cc_user,'w') as fp:
        yaml.dump(data,fp)

### DEFAULTS

default_bootstrap = """
whitelist:
  julia: versionless
  tensorflow: 666.6
#! note that we will include singularity, lmod, etc keys as well
""".strip()

# conda environment specified here
conda_spec = """name: community-collections
#! channels:
#!  - conda-forge
dependencies:
#! broken? - lua-luaposix
- python>=3.6
#! - curl was not working
- pycurl
- pyyaml
- pip
- pip:
  - nvchecker
  - ipdb
"""

# default parameters
#! for SINGULARITY_NEEDS_PATH from installers import Singularity
default_full = {
	#'checkup':'careful',
	#'singularity_default_cache':'/where/to/cache',
	#! previously Singularity.NEEDS_PATH
	'singularity':{'path':'NEEDS_SINGULARITY_PATH'},
	}

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

### ENVIRONMENT HELPERS

conda_name = 'community-collections'
# all paths relative to community collections root
dependency_pathfinder = lambda x: os.path.realpath(
    os.path.expanduser(os.path.join(os.getcwd(),x)))

# master specification listing
specs = {
    'miniconda':'miniconda',
    'conda_activator':'etc/profile.d/conda.sh',
    'envname':'community-collections'}

#! attach the prefix somehow in the class below?
#! systematic way to manage prefix paths?
subshell = lambda x: '. %s && %s'%(
    os.path.join(
        dependency_pathfinder(specs['miniconda']),
        specs['conda_activator']
        ),x)

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
