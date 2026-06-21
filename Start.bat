@echo off
setlocal enabledelayedexpansion

:: 1. Standardwert definieren
set "PROGRAM=MeisterschaftDeLuebs.py"

:: 2. Prüfen, ob config.ini existiert
if exist config.ini (
    :: Finde Zeilen mit "StartFramework", die NICHT mit # oder ; anfangen
    for /f "tokens=1,2 delims==" %%A in ('findstr /i "^[ \t]*[^#;].*StartFramework" config.ini') do (
        
        :: Den Wert auf der rechten Seite nehmen und alle Leerzeichen entfernen
        set "VALUE=%%B"
        set "VALUE=!VALUE: =!"
        
        :: Prüfen, ob der Wert "True" ist
        if /i "!VALUE!"=="True" (
            set "PROGRAM=StartFramework.py"
        )
    )
) else (
    echo [HINWEIS] Keine config.ini gefunden. Starte Standard-Modus.
)

:: 3. Programm starten
echo ==================================================
echo Starte: !PROGRAM!
echo ==================================================
echo.

python !PROGRAM!

:: Pause am Ende
pause