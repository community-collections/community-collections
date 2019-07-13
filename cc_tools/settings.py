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
"""### Community-Collections settings

# default place to store images
images: ~/.cc_images
module_settings:
  # choose the default source
  # if you omit module_settings, docker is the default
  source: docker
# standard set of modules
whitelist:
  R:
    calls:
    - R
    - Rscript
    repo: r-base
    source: docker
    version: '>=3.6'
  julia:
    source: docker
    version: '>=1.0.1'
  lolcow:
    repo: leconte/examples/lolcow
    source: library
    #! no version checking on the library yet
    version: latest
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
