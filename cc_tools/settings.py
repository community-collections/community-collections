#!/usr/bin/env python

"""
SETTINGS FOR COMMUNITY COLLECTIONS
"""

# the user settings file which comprises most of the user interface
cc_user = 'cc.yaml'

conda_name = 'community-collections'
specs = {
    'miniconda':'./miniconda',
    'conda_activator':'etc/profile.d/conda.sh',
    'envname':'community-collections'}

# conda dependencies for CC
conda_spec = """name: %s
channels:
  - conda-forge
dependencies:
  - python>=3.6
  - pycurl
  - pyyaml
  - pip
  - pip:
    - nvchecker
    - ipdb
"""%specs['envname']

### COMMUNITY COLLECTIONS DEFAULTS

default_bootstrap = """
whitelist:
  julia: versionless
  tensorflow: 666.6
#! note that we will include singularity, lmod, etc keys as well
""".strip()

#! other (?) default parameters
default_full = {
    #'checkup':'careful',
    #'singularity_default_cache':'/where/to/cache',
    #! previously Singularity.NEEDS_PATH
    'singularity':{'path':'NEEDS_SINGULARITY_PATH'},
    }
