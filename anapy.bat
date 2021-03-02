@FOR /F "delims=" %%i IN ('@call "C:\Users\%USERNAME%\Miniconda3\Scripts\conda.exe" ..activate "cmd.exe" %1') DO @SET "NEW_PATH=%%i"
@SET PATH=%NEW_PATH%;%PATH%
python %2