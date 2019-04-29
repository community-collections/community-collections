help(
[[Community-collections python envrionment.
This module is for reference only. It provides the conda executable installed
by community collections via miniconda. This does not load the python 
environment used by community-collections but instead simply simulates the use 
of "source miniconda/etc/profile.d/conda.sh" which is the preferred method. 
Note that users will also have to update their RC files in the usual way, to 
properly use "conda" after loading this module.
]])
-- !? development note: what is the canonical way to 
-- via: echo "source  miniconda/etc/profile.d/conda.sh && conda activate community-collections" > tmp.sh
-- via: $LMOD_DIR/sh_to_modulefile ./tmp.sh > tmp.lua
setenv("CONDA_DEFAULT_ENV","community-collections")
setenv("CONDA_EXE","/home/user/community-collections/miniconda/bin/conda")
setenv("CONDA_PREFIX","/home/user/community-collections/miniconda/envs/community-collections")
setenv("CONDA_PROMPT_MODIFIER","(community-collections) ")
setenv("CONDA_PYTHON_EXE","/home/user/community-collections/miniconda/bin/python")
setenv("CONDA_SHLVL","1")
prepend_path("PATH","/home/user/community-collections/miniconda/condabin")
prepend_path("PATH","/home/user/community-collections/miniconda/envs/community-collections/bin"
)
setenv("_CE_CONDA","")
setenv("_CE_M","")
