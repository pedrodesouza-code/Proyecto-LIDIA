@echo off
REM Inicia MongoDB local en una ventana separada usando el dbpath del proyecto.

set "MONGOD=C:\Program Files\MongoDB\Server\6.0\bin\mongod.exe"
set "DBPATH=C:\Users\rqf18\mongodb_data"
set "LOGPATH=C:\Users\rqf18\mongodb_logs\mongod.log"

if not exist "%MONGOD%" (
    echo [ERROR] No se encontro mongod.exe en:
    echo         %MONGOD%
    pause
    exit /b 1
)

if not exist "%DBPATH%" (
    echo [ERROR] No se encontro el dbpath:
    echo         %DBPATH%
    pause
    exit /b 1
)

if not exist "C:\Users\rqf18\mongodb_logs" (
    mkdir "C:\Users\rqf18\mongodb_logs"
)

echo Iniciando MongoDB local en puerto 27017...
start "MongoDB Local" "%MONGOD%" --dbpath "%DBPATH%" --logpath "%LOGPATH%" --port 27017 --bind_ip 127.0.0.1 --logappend
echo Listo. Espera unos segundos y luego ejecuta:
echo   python scripts\verificar_bases_locales.py
pause
