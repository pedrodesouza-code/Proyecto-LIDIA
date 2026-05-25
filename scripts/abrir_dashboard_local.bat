@echo off
REM Abre el dashboard Streamlit local en una ventana separada.

set "PORT=8502"
set "PROJECT_ROOT=%~dp0.."

pushd "%PROJECT_ROOT%"

where py >nul 2>nul
if errorlevel 1 (
    echo [ERROR] No se encontro el lanzador de Python "py".
    echo         Instala Python o ajusta este script para usar python.exe directo.
    pause
    exit /b 1
)

echo Iniciando dashboard local en:
echo   http://localhost:%PORT%
echo.
echo Se abrira una nueva ventana con Streamlit.
echo Deja esa ventana abierta mientras uses la app.

start "Dashboard Streamlit" cmd /k "py -3 -m streamlit run dashboard/app.py --server.port %PORT%"

timeout /t 8 >nul
start "" "http://localhost:%PORT%"

echo Si el navegador tarda, espera unos segundos mas y recarga la pagina.
pause
