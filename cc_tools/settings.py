#!/usr/bin/env python

"""
SETTINGS FOR COMMUNITY COLLECTIONS
"""

# the user settings file which comprises most of the user interface
cc_user = 'cc.yaml'

conda_name = 'community-collections'
specs = {
    # hardcoded by the cc wrapper for speed
    'miniconda':'./miniconda',
    'conda_activator':'etc/profile.d/conda.sh',
    # hardcoded by the cc wrapper for speed
    'envname':'community-collections',}

# this default is used by kickstart_yaml
default_bootstrap = \
"""# Community-Collections settings
images: ~/.cc_images
whitelist:
  R:
    source: docker
    version: '>=3.6'
  julia:
    source: docker
    version: '>=1.0.1'
"""

#! other (?) default parameters. explain this
default_full = {
    #'checkup':'careful',
    #'singularity_default_cache':'/where/to/cache',
    #! previously Singularity.NEEDS_PATH
    'singularity':{'path':'NEEDS_SINGULARITY_PATH'},}

# default modulefile settings
default_modulefile_settings = dict(
    source='docker',)
