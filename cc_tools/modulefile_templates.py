#!/usr/env/bin python

modulefile_basic_base = """
local images_dn = "%%(image_spot)s"
-- the source is suffixed with the tag, which is identical to the Lmod version
local source = "%%(source)s" .. myModuleVersion()
local conda_env = "%%(conda_env)s"
local target = myModuleName() .. "-" .. myModuleVersion() .. ".sif"

load('cc/singularity')

function resolve_tilde(s)
    return(s:gsub("^~",os.getenv("HOME")))
end

local images_dn_abs = resolve_tilde(images_dn)
local target_fn = pathJoin(images_dn_abs,target)

if lfs.attributes(target_fn) then
    add_property("cc_status","ready")
else
    add_property("cc_status","available")
end
%%(extras)s
if mode()=="load" then

    -- make a cache directory
    if lfs.attributes(images_dn_abs,'mode')==nil then
        io.stderr:write(
            "[CC] making a cache directory: " .. images_dn_abs .. "\\n")
        lfs.mkdir(images_dn_abs)
    end
    -- download the image
    if lfs.attributes(target_fn,'mode')==nil then
        local conda_bin = pathJoin(os.getenv("_COMCOL_ROOT"),conda_env,"bin")
        local prefix = "PATH=$PATH:" .. conda_bin .. " "
        -- after download we report on the size
        local suffix = (" && " .. pathJoin(conda_bin,"lua") .. " " .. 
            pathJoin(os.getenv("_COMCOL_ROOT"),"cc_tools","post_download.lua") 
            .. " " .. images_dn .. " " .. target_fn .. " " .. myModuleName())
        local cmd = (prefix .. 
            "%(singularity_pull)s " .. target_fn .. " " .. 
            source .. suffix)
        execute{cmd=cmd,modeA={"load"}}
    end
    -- interface to the container
%%(shell_connections)s
end
"""

modulefile_basic = modulefile_basic_base%dict(
    singularity_pull='singularity pull')

modulefile_sandbox = modulefile_basic_base%dict(
    singularity_pull='singularity build --sandbox')

shell_connection_exec = """    set_shell_function('%(alias)s',
        "singularity exec " .. target_fn .. ' %(target)s "$@"',
        "singularity exec " .. target_fn .. '%(target)s "$*"')
"""

shell_connection_run = """    set_shell_function('%(alias)s',
        "singularity run " .. target_fn,
        "singularity run " .. target_fn)
"""

shell_connection_exec_sandbox = """    set_shell_function('%(alias)s',
        "singularity exec --userns " .. target_fn .. ' %(target)s "$@"',
        "singularity exec --userns " .. target_fn .. '%(target)s "$*"')
"""

shell_connection_run_sandbox = """    set_shell_function('%(alias)s',
        "singularity run --userns " .. target_fn,
        "singularity run --userns " .. target_fn)
"""

