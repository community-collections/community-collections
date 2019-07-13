#!/usr/env/bin python

modulefile_basic = """
local images_dn = "%(image_spot)s"
-- the source is suffixed with the tag, which is identical to the Lmod version
local source = "%(source)s:" .. myModuleVersion()
local conda_env = "%(conda_env)s"
local target = myModuleName() .. "-" .. myModuleVersion() .. ".sif"

load('cc/singularity')

function resolve_tilde(s)
    return(s:gsub("^~",os.getenv("HOME")))
end

local images_dn_abs = resolve_tilde(images_dn)
local target_fn = pathJoin(images_dn_abs,target)

function check_image_sizes() 
    io.stderr:write("[CC] checking image sizes " .. images_dn_abs .. "\\n")
    total_size = 0
    for path in lfs.dir(images_dn_abs) do
        -- better way to select only files?
        if path ~= "." and path ~= ".." then
            local size = tonumber(lfs.attributes(
                pathJoin(images_dn_abs,path), "size"))
            total_size = total_size + size
            local size_str = string.format("%%.0fMB",size/1000000)
            io.stderr:write(size_str .. " " .. path .. "\\n")
        end
    end
    local size_str = string.format("%%.0fMB",total_size/1000000)
    io.stderr:write(size_str .. " \\n")
end

if mode()=="load" then

    -- make a cache directory
    if lfs.attributes(images_dn_abs,'mode')==nil then
        io.stderr:write(
            "[CC] making a cache directory: " .. images_dn_abs .. "\\n")
        lfs.mkdir(images_dn_abs)
    end
    -- download the image
    if lfs.attributes(target_fn,'mode')==nil then
        append_path("PATH",pathJoin(os.getenv("_COMCOL_ROOT"),conda_env,"bin"))
        local cmd = 'singularity pull ' .. target_fn .. ' ' .. source
        io.stderr:write(
            "[CC] community collections downloads the containers on-demand\\n")
        io.stderr:write(
            "[CC] downloading the image: " .. images_dn_abs .. "\\n")
        os.execute(cmd)
        remove_path("PATH",pathJoin(os.getenv("_COMCOL_ROOT"),conda_env,"bin"))
        io.stderr:write("[CC] downloaded the image: " .. target_fn .. "\\n")
        check_image_sizes()
        io.stderr:write("[CC] please be mindful of your quota\\n")
        io.stderr:write("[CC] the module is ready: " .. myModuleName() .. "\\n")
    end
    -- interface to the container
%(shell_connections)s
end
"""

shell_connection_exec = """    set_shell_function('%(alias)s',
        "singularity exec " .. target_fn .. ' %(target)s "$@"',
        "singularity exec " .. target_fn .. '%(target)s "$*"')
"""

shell_connection_run = """    set_shell_function('%(alias)s',
        "singularity run " .. target_fn,
        "singularity run " .. target_fn)
"""
