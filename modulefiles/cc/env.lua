local conda_prefix = os.getenv("CONDA_PREFIX")
if (conda_prefix == nil or conda_prefix == "") then
  -- !!! is activation the same in csh?
  load('cc/conda')
  cmd = "conda activate community-collections"
  execute{cmd=cmd, modeA = {"load"}}
else
  cmd = "conda deactivate"
  execute{cmd=cmd, modeA = {"unload"}}
  unload('cc/conda')
end
