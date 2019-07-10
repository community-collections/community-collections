local conda_prefix = os.getenv("CONDA_PREFIX")
if (conda_prefix == nil or conda_prefix == "") then
  -- only load cc/conda if it is not loaded 
  -- otherwise it unloads itself due to CONDA_EXE check
  if (not isloaded("cc/conda")) then 
    -- mark cc/conda as inherited from me
    setenv("_CC_CONDA_INHERIT",1)
    load("cc/conda") 
  end
  -- end
  cmd = "conda activate community-collections"
  execute{cmd=cmd, modeA = {"load"}}
else
  cmd = "conda deactivate"
  execute{cmd=cmd, modeA = {"unload"}}
  -- if cc/conda was inherited we unload it
  if os.getenv("_CC_CONDA_INHERIT")~=nil then
    unload('cc/conda')
    setenv("_CC_CONDA_INHERIT",0)
  end
end