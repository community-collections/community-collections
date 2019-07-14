require 'io'
require 'lfs'

-- POSTSCRIPT for an image download
-- This script runs after an image is downloaded
-- to tell the user the size of their cache directory
-- arguments are: the image directory, the downloaded file, and the module name

local images_dn_abs = arg[1]
local target_fn = arg[2]
local my_module_name = arg[3]

function check_image_sizes() 
    io.stderr:write("[CC] checking image sizes at " .. images_dn_abs .. "\n")
    total_size = 0
    for path in lfs.dir(images_dn_abs) do
        -- better way to select only files?
        if path ~= "." and path ~= ".." then
            -- pathJoin is not available outside lmod
            local size = tonumber(lfs.attributes(
                images_dn_abs .. "/" .. path, "size"))
            total_size = total_size + size
            local size_str = string.format("%6.0fMB",size/1000000)
            io.stderr:write(size_str .. " " .. path .. "\n")
        end
    end
    local size_str = string.format("%6.0fMB TOTAL",total_size/1000000)
    io.stderr:write(size_str .. "\n")
end

io.stderr:write("[CC] downloaded the image: " .. target_fn .. "\n")
check_image_sizes()
io.stderr:write("[CC] please be mindful of your quota\n")
io.stderr:write("[CC] note that singularity may use a similar cache\n")
io.stderr:write("[CC] the module is ready: " .. my_module_name .. "\n")
