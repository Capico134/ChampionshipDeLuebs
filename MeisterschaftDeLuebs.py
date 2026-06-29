import tkinter as tk
from DateiManagerDeLuebs import DateiManager
from MatchManagerDeLuebs import MatchManager
#from TurnierLogikDeLuebs import TurnierLogik
from TurnierGUIDeLuebs import TurnierGUI
import subprocess # 
import sys # <--- NEU: Für die Start-Argumente

def get_current_version():
    """Holt die dynamische Versionsnummer direkt aus Git."""
    try:
        raw_git = subprocess.check_output(
            ["git", "describe", "--tags", "--always", "--dirty"], 
            stderr=subprocess.DEVNULL
        ).strip().decode("utf-8")

        # Wir säubern es für die Anzeige, behalten aber die Info
        clean_version = raw_git.lstrip('v') 
        return clean_version
        
    except Exception:
        # Fallback für Leute, die sich das als .zip ohne Git laden
        return "1.0.2-zip"

def main():
    root = tk.Tk()
    aktuelle_version = get_current_version()
    print(f"🏆 Championship DeLübs [v{aktuelle_version}]")

    soll_beamer_starten = "-beamer_autostart" in sys.argv 
    soll_topmost = "-topmost" in sys.argv
    
    datei_manager = DateiManager()
    match_manager = MatchManager(app_version=aktuelle_version)
    #turnier_logik = TurnierLogik()
    
    # 1. Das Fenster wird nur gebaut (__init__)
    app = TurnierGUI(root, datei_manager, match_manager, aktuelle_version, soll_beamer_starten, soll_topmost)
    
    # 2. NEU: Der Motor wird gestartet!
    app.start_turnier()
    
    # 3. Fenster an Windows übergeben
    root.mainloop()

if __name__ == "__main__":
    main()