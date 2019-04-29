-- supply the python that comes with the community-collections miniconda
-- !? detect the current folder?
local nameroot = '/home/user/community-collections/miniconda/'
prepend_path("PATH", pathJoin(nameroot, "bin"))
prepend_path("LD_LIBRARY_PATH",pathJoin(nameroot, "lib"))
-- !? automatically get the version number below from miniconda?
prepend_path("LD_LIBRARY_PATH",pathJoin(nameroot, "lib/python3.7"))
prepend_path("LD_LIBRARY_PATH",pathJoin(nameroot, "lib/python3.7/site-packages"))