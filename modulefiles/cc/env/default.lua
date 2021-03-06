local conda_prefix = os.getenv("CONDA_PREFIX")
if mode()=="load" then setenv("_CC_ENV_LOADED",1) 
else setenv("_CC_ENV_LOADED",0) end
if (conda_prefix == nil or conda_prefix == "") or mode()=="load" then
  -- only load cc/conda if it is not loaded 
  -- otherwise it unloads itself due to CONDA_EXE check
  if (not isloaded("cc/conda")) then 
    -- mark cc/conda as inherited from me
    setenv("_CC_CONDA_INHERIT",1)
    load("cc/conda") 
  end
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
