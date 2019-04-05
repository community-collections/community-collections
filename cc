#!/bin/bash

# COMMUNITY COLLECTIONS INTERFACE SCRIPT
# USAGE: 
#   ./cc --help 
#   ./cc (envrun) <commands for conda environment>
#   ./cc (run) <conda binary name> <args>

#! hardcoded environment name and miniconda path below
MINICONDA_PATH=$PWD/miniconda
CC_ENV_NAME=community-collections
PYENV=$MINICONDA_PATH/envs/$CC_ENV_NAME/bin/python
# figure out which python to use 
if [[ ! -f $PYENV ]]; then PYENV=python; fi

# run within the full anaconda environment
if [[ "$1" == "envrun" ]]; then
   . miniconda/etc/profile.d/conda.sh
   conda activate community-collections
   shift
   exec $@
# run something in the anaconda bin (faster than envrun)
elif [[ "$1" == "run" ]]; then
   PATH=$MINICONDA_PATH/envs/$CC_ENV_NAME/bin:$PATH
   shift
   exec $@
# standard interface
else 
  $PYENV -B interface.py $@
fi
