@echo off
echo ==========================================
echo   CHAMPIONSHIP KIOSK AUTOSTART
echo ==========================================

:: 1. Magie: Springe IMMER in das Hauptverzeichnis (ein Ordner nach oben)
cd /d "%~dp0.."

:: 2. Warten auf das Raspberry Pi Netzwerk
echo Warte auf Raspberry Pi (WLAN/Netzwerk)...
:LOOP
ping -n 1 192.168.4.1 >nul
if errorlevel 1 (
    echo Waiting for connection
    timeout /t 2 >nul
    goto LOOP
)

:: 3. Laufwerk mappen
echo Pi gefunden! Verbinde Laufwerk Z:...
net use Z: \\192.168.4.1\shooting_live /persistent:no

:: 4. Update-Service starten
echo.
echo Starte Update-Routine...
:: Da wir jetzt virtuell im Hauptverzeichnis sind, klappt der Aufruf über tools\...
call tools\GitUpdate.bat

:: 5. Hauptprogramm starten
echo.
echo Starte Shooting DeLuebs / Championship...
:: Die Start.bat liegt direkt im Hauptverzeichnis
call Start.bat

:: 6. Fallback, falls das Python-Tool komplett abbricht
echo.
echo ==========================================
echo KIOSK-SYSTEM WURDE UNERWARTET BEENDET!
echo ==========================================
pause