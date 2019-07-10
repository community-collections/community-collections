local conda_prefix = os.getenv("CONDA_PREFIX")
if (conda_prefix == nil or conda_prefix == "") then
  -- !!! is activation the same in csh?
  -- !!! hardcoded this below: load('cc/conda')
  
  -- REDUNDANT CODE. this is cc/conda.lua however there were loading problems!
  local root = pathJoin(os.getenv("_COMCOL_ROOT"),'miniconda')
  setenv("ANACONDA3ROOT", root)
  setenv("PYTHONROOT", root)
  local python_version = capture(root .. "/bin/python -V |& awk '{print $2}'")
  local conda_version = capture(root .. "/bin/conda --version |& awk '{print $2}'")
  function trim(s)
     return (s:gsub("^%s*(.-)%s*$", "%1"))
  end
  conda_version = trim(conda_version)
  help([[ Loads the Miniconda environment supporting Community-Collections. ]])
  whatis("Sets the environment to use the Community-Collections Miniconda.")
  local conda_exe = os.getenv("CONDA_EXE")
  local myShell = myShellName()
  -- rpb removes two prepends of bin and condabin to prevent lingering conda
  -- if CONDA_EXE is unset then trigger source of conda.{sh,csh}
  if (conda_exe == nil or conda_exe == "") then
    if (myShell == "bash") then
        cmd = "source " .. root .. "/etc/profile.d/conda.sh"
    else
        cmd = "source " .. root .. "/etc/profile.d/conda.csh"
    end
    execute{cmd=cmd, modeA = {"load"}}
  else
    if (myShell == "bash") then
        cmd = "conda deactivate; " ..
              "unset ANACONDA3ROOT; unset PYTHONROOT; unset CONDA_EXE; " ..
              "unset CONDA_PYTHON_EXE; unset _CE_CONDA; unset _CE_M; " ..
              "unset __add_sys_prefix_to_path; unset __conda_activate; " ..
              "unset __conda_reactivate; unset __conda_hashr; unset CONDA_SHLVL; " ..
              "unset conda"
    else
        cmd = "conda deactivate; " ..
              "unsetenv CONDA_EXE; unsetenv _CONDA_ROOT; unsetenv _CONDA_EXE; " ..
              "unsetenv CONDA_PYTHON_EXE; unset CONDA_SHLVL; unalias conda"
    end
    execute{cmd=cmd, modeA = {"unload"}}
    -- rpb removes condabin so conda cannot be accessed after unloading
    remove_path("PATH",pathJoin(os.getenv("_COMCOL_ROOT"),"miniconda","condabin"))
  end
  -- REDUNDANT CODE.end of redundant code

  cmd = "conda activate community-collections"
  execute{cmd=cmd, modeA = {"load"}}
else
  cmd = "conda deactivate"
  execute{cmd=cmd, modeA = {"unload"}}
  -- !!! not necessary because redundant code: unload('cc/conda')
end
