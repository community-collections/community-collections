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
if [[ ! -f $PYENV ]]; then 
  unset PYENV
  # search for common python aliases
  calls=(python3 python2 python)
  for call in ${calls[@]}; do
    type $call &> /dev/null
    has_python=$?
    if [[ $has_python -eq 0 ]]; then
      PYENV=$call
      break
    fi
  done
  if [[ -z $PYENV ]]; then
    echo "[ERROR] cannot find python"
    exit 1
  fi
fi

# run within the full anaconda environment
if [[ "$1" == "envrun" ]]; then
   source miniconda/etc/profile.d/conda.sh
   conda activate community-collections
   ${@:2}
# run something in the anaconda bin (faster than envrun)
elif [[ "$1" == "run" ]]; then
   PATH=$MINICONDA_PATH/envs/$CC_ENV_NAME/bin:$PATH
   ${@:2}
# standard interface
else 
  $PYENV -B interface.py $@
fi
