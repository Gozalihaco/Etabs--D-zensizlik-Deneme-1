@echo off
setlocal EnableDelayedExpansion
cd /d "%~dp0"
set "MODE=%~1"
set "APP=ETABS-Duzensizlik"
set "PF86=%ProgramFiles(x86)%"

echo ============================================================
echo  %APP% - Windows derlemesi
echo ============================================================

rem ---- 1. Python (yalnizca derleyen bilgisayarda gerekir)
set "PY="
where py >nul 2>nul && set "PY=py -3"
if not defined PY where python >nul 2>nul && set "PY=python"
if not defined PY goto :nopython
%PY% -c "import struct,sys;sys.exit(0 if struct.calcsize('P')==8 else 1)"
if errorlevel 1 goto :not64

rem ---- 2. Sanal ortam ve paketler
if not exist ".venv\Scripts\python.exe" %PY% -m venv .venv
if errorlevel 1 goto :fail
set "VPY=.venv\Scripts\python.exe"
"%VPY%" -m pip install --upgrade pip -q
"%VPY%" -m pip install -q -r requirements-build.txt
if errorlevel 1 goto :fail

rem ---- 3. PDF kutuphaneleri (programin internetsiz calismasi icin exe'ye gomulur)
if not exist lib mkdir lib
if not exist "lib\jspdf.umd.min.js" curl -fsSL -o "lib\jspdf.umd.min.js" "https://cdnjs.cloudflare.com/ajax/libs/jspdf/2.5.1/jspdf.umd.min.js"
if errorlevel 1 goto :fail
if not exist "lib\jspdf.plugin.autotable.min.js" curl -fsSL -o "lib\jspdf.plugin.autotable.min.js" "https://cdnjs.cloudflare.com/ajax/libs/jspdf-autotable/3.5.31/jspdf.plugin.autotable.min.js"
if errorlevel 1 goto :fail

rem ---- 4. Exe
echo [1/3] Exe olusturuluyor...
"%VPY%" -m PyInstaller --noconfirm --clean --onedir --console --name "%APP%" --icon app.ico ^
  --add-data "etabs_duzensizlik.html;." --add-data "lib;lib" ^
  --collect-submodules comtypes --hidden-import comtypes.client ^
  etabs_bridge.py
if errorlevel 1 goto :fail

if not exist cikti mkdir cikti
echo [2/3] Tasinabilir zip hazirlaniyor...
powershell -NoProfile -Command "Compress-Archive -Path 'dist\%APP%\*' -DestinationPath 'cikti\%APP%-Tasinabilir.zip' -Force"

rem ---- 5. Kurulum dosyasi (Inno Setup)
echo [3/3] Kurulum dosyasi olusturuluyor...
set "ISCC="
if exist "!PF86!\Inno Setup 6\ISCC.exe" set "ISCC=!PF86!\Inno Setup 6\ISCC.exe"
if not defined ISCC if exist "%ProgramFiles%\Inno Setup 6\ISCC.exe" set "ISCC=%ProgramFiles%\Inno Setup 6\ISCC.exe"
if not defined ISCC if exist "%LOCALAPPDATA%\Programs\Inno Setup 6\ISCC.exe" set "ISCC=%LOCALAPPDATA%\Programs\Inno Setup 6\ISCC.exe"
if not defined ISCC if /i "%MODE%"=="ci" choco install innosetup -y --no-progress >nul
if not defined ISCC if exist "!PF86!\Inno Setup 6\ISCC.exe" set "ISCC=!PF86!\Inno Setup 6\ISCC.exe"
if not defined ISCC goto :noinno
"!ISCC!" /Q installer.iss
if errorlevel 1 goto :fail

echo.
echo TAMAM. Paylasilacak dosyalar "cikti" klasorunde:
echo   cikti\%APP%-Kurulum.exe      (onerilen)
echo   cikti\%APP%-Tasinabilir.zip  (kurulumsuz)
goto :end

:noinno
echo.
echo [UYARI] Inno Setup bulunamadi, kurulum dosyasi olusturulmadi.
echo Tasinabilir surum hazir: cikti\%APP%-Tasinabilir.zip
echo Kurulum dosyasi icin Inno Setup 6'yi kurun: https://jrsoftware.org/isdl.php
goto :end

:nopython
echo [HATA] Derleme icin Python gerekli: https://www.python.org/downloads/  (kurulumda "Add python.exe to PATH" isaretleyin)
echo Python kurmak istemiyorsaniz README'deki GitHub ile derleme yontemini kullanin.
goto :failend
:not64
echo [HATA] 64-bit Python gerekli (ETABS 64-bit oldugu icin).
goto :failend
:fail
echo.
echo [HATA] Derleme basarisiz. Yukaridaki mesaja bakin.
:failend
if /i not "%MODE%"=="ci" pause
exit /b 1
:end
if /i not "%MODE%"=="ci" pause
exit /b 0
