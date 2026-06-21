@echo off
echo ===========================================
echo   Shooting DeLuebs - Update-Service 🎯
echo ===========================================
echo.
echo Suche nach neuen Versionen auf GitHub...
echo.
:: Führt den Pull-Befehl aus, um Änderungen zu laden
cd ..\..\ShootingDeLuebs
git fetch origin
:: Zeigt die rot/grünen Änderungen an, bevor überschrieben wird
git diff --stat --color HEAD origin/main
git reset --hard origin/main
echo.
echo ===========================================
echo   Championship DeLuebs - Update-Service 📊
echo ===========================================
echo.
cd ..\ChampionshipDeLuebs
git fetch origin
:: Zeigt die rot/grünen Änderungen an, bevor überschrieben wird
git diff --stat --color HEAD origin/main
git reset --hard origin/main
echo.
echo -------------------------------------------
echo Update-Vorgang abgeschlossen.
echo.
pause