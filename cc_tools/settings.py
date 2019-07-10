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
    'envname':'community-collections',
    #! under development. where we dump the images
    #! 'image_cache_spot':'./cache'
    }

# this default is used by kickstart_yaml
default_bootstrap = """
whitelist:
  julia: versionless
  tensorflow: 666.6
images: ~/.cc_images
""".strip()

#! other (?) default parameters
default_full = {
    #'checkup':'careful',
    #'singularity_default_cache':'/where/to/cache',
    #! previously Singularity.NEEDS_PATH
    'singularity':{'path':'NEEDS_SINGULARITY_PATH'},}
