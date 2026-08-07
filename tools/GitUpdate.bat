@echo off
echo ===========================================
echo   Update-Service wird vorbereitet...
echo ===========================================
echo.

:: Magie: Springe IMMER in das Hauptverzeichnis von Championship (wo die tools/ Datei liegt)
cd /d "%~dp0.."

echo ===========================================
echo   Shooting DeLuebs - Update-Service 🎯
echo ===========================================
echo.
:: Prüfe, ob der Ordner nebenan überhaupt existiert
if exist "..\ShootingDeLuebs\" (
    :: Gehe in den Ordner (und merke dir, wo wir gerade waren)
    pushd "..\ShootingDeLuebs"
    
    echo Suche nach neuen Versionen auf GitHub...
    git fetch origin
    git --no-pager diff --stat --color HEAD origin/main
    git reset --hard origin/main
    
    :: Springe zurück zu Championship
    popd
) else (
    echo [INFO] Der Ordner "ShootingDeLuebs" wurde auf diesem PC nicht gefunden.
    echo        Das Update wird uebersprungen!
)
echo.

echo ===========================================
echo   TargetVision DeLuebs - Update-Service 🎯
echo ===========================================
echo.
:: Prüfe, ob der Ordner nebenan überhaupt existiert
if exist "..\TargetVisionDeLuebs\" (
    :: Gehe in den Ordner (und merke dir, wo wir gerade waren)
    pushd "..\TargetVisionDeLuebs"
    
    echo Suche nach neuen Versionen auf GitHub...
    git fetch origin
    git --no-pager diff --stat --color HEAD origin/main
    git reset --hard origin/main
    
    :: Springe zurück zu Championship
    popd
) else (
    echo [INFO] Der Ordner "TargetVisionDeLuebs" wurde auf diesem PC nicht gefunden.
    echo        Das Update wird uebersprungen!
)
echo.


echo ===========================================
echo   Championship DeLuebs - Update-Service 📊
echo ===========================================
echo.
echo Suche nach neuen Versionen auf GitHub...
:: Da wir durch popd (oder direkt) im Root von Championship sind, laeuft das Update sicher
git fetch origin
git --no-pager diff --stat --color HEAD origin/main
git reset --hard origin/main
echo.

echo -------------------------------------------
echo Update-Vorgang abgeschlossen.
echo.
pause