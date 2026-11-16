@echo off
setlocal
cd /d "%~dp0"
echo.
echo FOTO PAPEL - COMPILACION WINDOWS
where py >nul 2>nul
if %ERRORLEVEL%==0 (
  set "PYTHON=py"
) else (
  set "PYTHON=python"
)
%PYTHON% --version >nul 2>nul
if errorlevel 1 (
  echo No se ha encontrado Python. Utiliza GitHub Actions siguiendo el README.
  pause
  exit /b 1
)
%PYTHON% -m pip install -r requirements.txt || goto error
%PYTHON% -m PyInstaller --noconfirm --clean --onefile --windowed --name FotoPapel --icon icono.ico --collect-submodules PIL --collect-submodules reportlab main.py || goto error
echo.
echo LISTO: El programa esta en dist\FotoPapel.exe
explorer "%CD%\dist"
pause
exit /b 0
:error
echo Ha ocurrido un error al compilar.
pause
exit /b 1
