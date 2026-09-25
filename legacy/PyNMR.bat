@cd /d %~dp0
@if not EXIST anaenv (
  @echo Please create anaenv file which written your anaconda environment name
  @pause
  @exit 1
)
@set /p ANAENV=<anaenv

@cmd.exe /K anapy.bat %ANAENV% main.py