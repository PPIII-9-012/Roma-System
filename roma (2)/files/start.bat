@echo off
setlocal
cd /d "%~dp0"

echo precioauto corriendo en http://localhost:5000
echo.

python backend.py
pause
