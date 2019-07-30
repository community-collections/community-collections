require 'io'
require 'lfs'

-- POSTSCRIPT for an image download
-- This script runs after an image is downloaded
-- to tell the user the size of their cache directory
-- arguments are: the image directory, the downloaded file, and the module name

local images_dn_abs = arg[1]
local target_fn = arg[2]
local my_module_name = arg[3]

function isDir(name)
    -- via https://stackoverflow.com/a/21637668/3313859
    local cd = lfs.currentdir()
    local is = lfs.chdir(name) and true or false
    lfs.chdir(cd)
    return is
end

function os.capture(cmd, raw)
    -- via https://stackoverflow.com/a/326715/3313859
    local f = assert(io.popen(cmd, 'r'))
    local s = assert(f:read('*a'))
    f:close()
    if raw then return s end
    s = string.gsub(s, '^%s+', '')
    s = string.gsub(s, '%s+$', '')
    s = string.gsub(s, '[\n\r]+', ' ')
    return s
end

function check_image_sizes() 
    io.stderr:write("[CC] checking image sizes at " .. images_dn_abs .. "\n")
    total_size = 0
    has_sandboxes = false
    for path in lfs.dir(images_dn_abs) do
        -- better way to select only files?
        if path ~= "." and path ~= ".." then
            if isDir(images_dn_abs .. "/" .. path) then
                local result_du = os.capture(
                    "du -s " .. images_dn_abs .. "/" .. path)
                local size = tonumber(string.match(result_du,'^%d+'))
                total_size = total_size + size/1024
                local size_str = string.format("%6.0fMB",size/1024)
                io.stderr:write(size_str .. " " .. path .. "\n")
                has_sandboxes = true
            else
                -- pathJoin is not available outside lmod
                local size = tonumber(lfs.attributes(
                    images_dn_abs .. "/" .. path, "size"))
                total_size = total_size + size/1000000
                local size_str = string.format("%6.0fMB",size/1000000)
                io.stderr:write(size_str .. " " .. path .. "\n")
            end
        end
    end
    local size_str = string.format("%6.0fMB TOTAL",total_size)
    io.stderr:write(size_str .. "\n")
    if has_sandboxes then 
        io.stderr:write("[CC] note that your image folder contains " ..
            "sandboxes\n[CC] and sandboxes often have many files!" .. "\n")
    end
    -- run du on the singularity folder as a warning
    if isDir(os.getenv("HOME") .. "/" .. ".singularity") then
        local result_du = os.capture(
            "du -s " .. os.getenv("HOME") .. "/" .. ".singularity")
        local size = tonumber(string.match(result_du,'^%d+'))
        if size>16 then
            total_size = total_size + size/1024
            io.stderr:write(string.format(
                "[CC] the ~/.singularity folder is also %.0fMB\n",size/1024))
            io.stderr:write("[CC] you can clear the singularity cache with: " ..
                "\"singularity cache clean -f\"" .. "\n")
        end
    end
end

io.stderr:write("[CC] downloaded the image: " .. target_fn .. "\n")
check_image_sizes()
io.stderr:write("[CC] please be mindful of your quota\n")
io.stderr:write("[CC] the module is ready: " .. my_module_name .. "\n")
