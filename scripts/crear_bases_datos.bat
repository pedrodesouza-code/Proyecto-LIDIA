@echo off
REM =============================================================================
REM SINIA-UY -- Lanzador de crear_bases_datos.py para Windows
REM =============================================================================
REM Doble click sobre este .bat o ejecutalo desde la raiz del proyecto.
REM Activa el venv si existe y ejecuta el script de creacion.
REM =============================================================================

setlocal
cd /d "%~dp0\.."

if exist ".venv\Scripts\activate.bat" (
    echo Activando venv...
    call .venv\Scripts\activate.bat
) else (
    echo [aviso] No se encontro .venv. Asegurate de tener psycopg2-binary y pymongo instalados:
    echo         pip install psycopg2-binary pymongo python-dotenv
)

echo.
python scripts\crear_bases_datos.py %*
set EXITCODE=%ERRORLEVEL%

echo.
pause
exit /b %EXITCODE%
