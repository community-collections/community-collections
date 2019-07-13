#!/usr/env/bin python

modulefile_basic = """
local images_dn = "%(image_spot)s"
local target = "%(target)s"
local source = "%(source)s"

load('cc/singularity')

function resolve_tilde(s)
    return(s:gsub("^~",os.getenv("HOME")))
end

local images_dn_abs = resolve_tilde(images_dn)
local target_fn = pathJoin(images_dn_abs,target)

if mode()=="load" then
    if lfs.attributes(images_dn_abs,'mode')==nil then
        io.stderr:write("[CC] making a cache directory: " .. images_dn_abs .. "\\n")
        lfs.mkdir(images_dn_abs)
    end
    if lfs.attributes(target_fn,'mode')==nil then
        -- if squashfs comes from cc/env we prepend the path here
        -- this is a hack in place of a ml cc/env which would be much more elegant but could not be unloaded
        -- utterly failed to load cc/env and unload it. something appears to be asynchronous (beyond just the lmod execute)
        append_path("PATH",pathJoin(os.getenv("_COMCOL_ROOT"),"miniconda/envs/community-collections/bin"))
        local cmd = 'singularity pull ' .. target_fn .. ' ' .. source
        -- execute {cmd=cmd,modeA={"load"}}
        io.stderr:write("[CC] community collections downloads the containers on-demand\\n")
        io.stderr:write("[CC] downloading the image: " .. images_dn_abs .. "\\n")
        os.execute(cmd)
        -- cleanup the squashfs hack (note: it would be nice to only remove this 
        --   if it was not in there before to avoid conflicts with cc/env)
        remove_path("PATH",pathJoin(os.getenv("_COMCOL_ROOT"),"miniconda/envs/community-collections/bin"))
        io.stderr:write("[CC] downloaded the image: " .. target_fn .. "\\n")
    end
    -- !! add shell functions here for specific commands when they come from a recipe?
    -- set_shell_function('%(bin_name)s',"singularity exec " .. target_fn .. ' %(bin_name)s "$@"',"singularity exec " .. target_fn .. '%(bin_name)s "$*"')
end
"""