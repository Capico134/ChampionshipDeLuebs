@echo off
echo.
echo ===========================================
echo   Championship DeLuebs - Update-Service 📊
echo ===========================================
echo.
git fetch origin
git reset --hard origin/main
echo.
echo ===========================================
echo   Shooting DeLuebs - Update-Service 🎯
echo ===========================================
echo.
echo Suche nach neuen Versionen auf GitHub...
echo.
:: Führt den Pull-Befehl aus, um Änderungen zu laden
cd ..\ShootingDeLuebs
git fetch origin
git reset --hard origin/main
echo -------------------------------------------
echo Update-Vorgang abgeschlossen.
echo.
pause