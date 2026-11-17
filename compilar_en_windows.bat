@echo off
setlocal
cd /d "%~dp0"
echo.
echo REVELO v1.2 - COMPILACION WINDOWS
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
%PYTHON% -m PyInstaller --noconfirm --clean --onefile --windowed --name Revelo --icon icono.ico --collect-submodules PIL --collect-submodules reportlab --collect-all pypdfium2 --collect-all pillow_heif --collect-all qrcode --add-data "icono.ico;." --add-data "logo_cabecera.png;." main.py || goto error
echo.
echo LISTO: El programa esta en dist\Revelo.exe
explorer "%CD%\dist"
pause
exit /b 0
:error
echo Ha ocurrido un error al compilar.
pause
exit /b 1
