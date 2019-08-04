#!/usr/bin/env python

"""
SETTINGS FOR COMMUNITY COLLECTIONS
"""

# this default is used by kickstart_yaml
import os

# the user settings file which comprises most of the user interface
cc_user = 'cc.yaml'

conda_name = 'community-collections'
specs = {
    # hardcoded by the cc wrapper for speed
    'miniconda': './miniconda',
    'conda_activator': 'etc/profile.d/conda.sh',
    # hardcoded by the cc wrapper for speed
    'envname': 'community-collections', }

with open(os.path.join(
          os.path.dirname(__file__), 'defaults_cc.yaml')) as fp:
    default_bootstrap = fp.read()

# default settings used by settings_resolver
# and also deprecated by the Manager classes
default_full = {}

# default modulefile settings
# these can be overridden by "module_settings" in cc.yaml
default_modulefile_settings = dict(
    source='docker',)
