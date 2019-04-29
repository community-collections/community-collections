-- via: echo "source  miniconda/etc/profile.d/conda.sh" > tmp.sh
-- via: $LMOD_DIR/sh_to_modulefile ./tmp.sh > tmp.lua
setenv("CONDA_EXE","/home/user/community-collections/miniconda/bin/conda")
setenv("CONDA_PYTHON_EXE","/home/user/community-collections/miniconda/bin/python")
setenv("CONDA_SHLVL","0")
prepend_path("PATH","/home/user/community-collections/miniconda/condabin")
setenv("_CE_CONDA","")
setenv("_CE_M","")
