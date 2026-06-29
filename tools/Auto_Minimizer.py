import time
import os
import pygetwindow as gw
import keyboard
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from datetime import datetime

# --- 1. DER CLEVERE WÄCHTER ---
class DateiWächter(FileSystemEventHandler):
    def on_modified(self, event):
        heute_str = datetime.now().strftime("%Y-%m-%d")
        ziel_datei = f"Turnier_{heute_str}.html"
        
        if os.path.basename(event.src_path) == ziel_datei:
            oeffne_schleuse()

# --- 2. DIE SCHLEUSE ÖFFNEN ---
def oeffne_schleuse():
    print("🚨 Neues Ergebnis erkannt! Kiosk macht Platz...")
    
    champ = gw.getWindowsWithTitle("Championship")
    if champ:
        try:
            champ[0].minimize()
        except Exception:
            pass

# --- 3. DIE SCHLEUSE SCHLIESSEN ---
def schliesse_schleuse():
    print("🔒 Schleuse wird verriegelt. Zurück zum Turnier!")
    
    champ = gw.getWindowsWithTitle("Championship")
    if champ:
        try:
            champ[0].restore()
            champ[0].activate()
        except Exception:
            pass

# --- HAUPTPROGRAMM ---
if __name__ == "__main__":
    # Hotkey registrieren (Global!)
    # ESC ist super intuitiv. Alternativen wären 'f1' oder 'alt+enter'
    keyboard.add_hotkey('esc', schliesse_schleuse)
    
    # Pfad zum savegames Ordner (robust relativ zur Python-Datei berechnet)
    base_path = os.path.dirname(os.path.abspath(__file__))
    savegames_pfad = os.path.join(base_path, "..\savegames")
    
    # Wächter starten
    if os.path.exists(savegames_pfad):
        observer = Observer()
        observer.schedule(DateiWächter(), path=savegames_pfad, recursive=False)
        observer.start()
        print(f"🛡️ WhatsApp-Schleuse aktiv! Überwache: {savegames_pfad}")
        print("👉 Drücke ESC, um die Schleuse wieder zu schließen.")
        
        try:
            while True: time.sleep(1)
        except KeyboardInterrupt:
            observer.stop()
    else:
        print(f"❌ Fehler: Ordner '{savegames_pfad}' existiert nicht!")