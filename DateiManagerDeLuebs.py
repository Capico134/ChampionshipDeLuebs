import configparser
import json
import csv
import os
import datetime
import glob

class DateiManager:
    def __init__(self, config_file='config.ini'):
        self.config = configparser.ConfigParser()
        self.highscore_pfad = r'..\ShootingDeLuebs\savegames\highscore.json' # Standard-Fallback
        self.next_match_pfad = r'..\ShootingDeLuebs\savegames\next_match.csv' # Standard-Fallback
        self.live_ticker_path = r'..\ShootingDeLuebs\savegames\live_match.json' # Standard-Fallback
        
        self.ticker_templates = [] # Standardmäßig leer
        self.beamer_texte = {
            'NICHT_GESTARTET_HAUPT': "Turnier startet\nin Kürze! ⏳",
            'NICHT_GESTARTET_SUB': "TEILNEHMER MACHT EUCH BEREIT",
            'GRUPPEN_ABGESCHLOSSEN_HAUPT': "Gruppenphase\nbeendet! ⏳",
            'GRUPPEN_ABGESCHLOSSEN_SUB': "WARTE AUF K.O.-PHASE...",
            'GRUPPENPHASE_HAUPT': "Warte auf\nnächstes Match...",
            'GRUPPENPHASE_SUB': "",
            'KO_PHASE_HAUPT': "Warte auf\nnächstes Match...",
            'KO_PHASE_SUB': ""
        }
        
        # --- LÖSUNG FRAGE 1: KUGELSICHERE DEFAULTS FÜR MATCH-NAMEN ---
        self.match_namen = {
            'VF': 'Viertelfinale',
            'HF': 'Halbfinale',
            '3PL': 'Spiel um Platz 3',
            'FIN': 'Finale'
        }
        
        self._lade_config(config_file)

    def _lade_config(self, config_file):
        """Lädt die Pfade und Nachrichten aus der config.ini."""
        if os.path.exists(config_file):
            try:
                # FIX: Hier explizit encoding='utf-8' hinzufügen!
                self.config.read(config_file, encoding='utf-8') 
                
                if 'Paths' in self.config:
                    self.highscore_pfad = self.config['Paths'].get('highscore_file', self.highscore_pfad)
                    self.next_match_pfad = self.config['Paths'].get('next_match_file', self.next_match_pfad)
                    self.live_ticker_path = self.config['Paths'].get('live_ticker_file', self.live_ticker_path)

                if 'Messages' in self.config:
                    raw_templates = self.config['Messages'].get('templates', "")
                    if raw_templates:
                        self.ticker_templates = [t.strip() for t in raw_templates.split('\n') if t.strip()]

                if 'BeamerTexte' in self.config:
                    for key in self.config['BeamerTexte']:
                        # \n im String wieder in echte Zeilenumbrüche umwandeln
                        self.beamer_texte[key.upper()] = self.config['BeamerTexte'][key].replace('\\n', '\n')

                if 'MatchNamen' in self.config:
                    for key in self.config['MatchNamen']:
                        # Bei "Viertelfinale" brauchen wir eigentlich keine Zeilenumbrüche,
                        # aber wir speichern es sauber ab (key.upper() macht z.B. "VF" draus)
                        self.match_namen[key.upper()] = self.config['MatchNamen'][key].strip()

                
                print(f"✅ Config erfolgreich geladen (UTF-8).")
            except Exception as e:
                print(f"❌ Fehler beim Lesen der Config: {e}")
        else:
            print(f"WARNUNG: Keine {config_file} gefunden.")

    #Öffnet die highscore.json und gibt die Daten komplett
    def lese_highscore(self):
        """Liest die Highscore.json sicher aus."""
        if not os.path.exists(self.highscore_pfad):
            print(f"Fehler: Highscore-Datei '{self.highscore_pfad}' nicht gefunden.")
            return None

        try:
            with open(self.highscore_pfad, 'r', encoding='utf-8') as file:
                daten = json.load(file)
                return daten
        except json.JSONDecodeError:
            print("Fehler: Highscore.json ist beschädigt (ungültiges JSON).")
            return None
        except Exception as e:
            print(f"Netzwerk/Lese-Fehler bei Highscore.json: {e}")
            return None

    def schreibe_next_match(self, spieler1, spieler2, zyklen=5, ladezeit=30):
        """Schreibt das nächste Match für den Raspberry Pi in die CSV."""
        try:
            # 'w' überschreibt die Datei jedes Mal neu – genau was wir wollen!
            with open(self.next_match_pfad, 'w', newline='', encoding='utf-8') as file:
                writer = csv.writer(file)
                # Header schreiben (falls Shooting DeLübs das erwartet)
                writer.writerow(['Spieler1', 'Spieler2', 'Zyklen', 'Ladezeit'])
                # Daten schreiben
                writer.writerow([spieler1, spieler2, zyklen, ladezeit])
            print(f"Erfolg: Match {spieler1} vs {spieler2} in {self.next_match_pfad} geschrieben.")
            return True
        except Exception as e:
            print(f"Fehler beim Schreiben von next_match.csv: {e}")
            return False

    def speichere_turnier_stand(self, daten):
        """Speichert den Stand mit Zeitstempel im Ordner 'savegames'."""
        if not os.path.exists("savegames"):
            os.makedirs("savegames")
            
        zeitpunkt = datetime.datetime.now().strftime("%Y-%m-%d_%H%M%S")
        dateiname = f"savegames/Turnier_{zeitpunkt}.json"
        
        try:
            with open(dateiname, 'w', encoding='utf-8') as f:
                json.dump(daten, f, indent=4, ensure_ascii=False)
            print(f"Autosave erstellt: {dateiname}")
            return True
        except Exception as e:
            print(f"Fehler beim Autosave: {e}")
            return False

    def finde_neuesten_pfad(self):
        """Sucht die neueste .json Datei im savegames-Ordner und gibt NUR den Pfad zurück."""
        liste = glob.glob("savegames/turnier_*.json")
        if not liste:
            return None
        
        # Alphabetisch sortieren (ELA-Weg)
        liste.sort()
        return liste[-1]

    def lade_stand_aus_datei(self, pfad):
        """Öffnet einen ganz bestimmten Pfad und lädt die JSON-Daten."""
        try:
            with open(pfad, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"Fehler beim Laden von {pfad}: {e}")
            return None

    def loesche_live_datei(self):
            """Löscht die Live-Ticker-Datei, falls sie existiert."""
            if os.path.exists(self.live_ticker_path):
                try:
                    os.remove(self.live_ticker_path)
                    print(f"Live-Daten gelöscht: {self.live_ticker_path}")
                    return True
                except Exception as e:
                    print(f"Fehler beim Löschen der Live-Daten: {e}")
                    return False
            return True # Datei war eh nicht da, also Ziel erreicht

    def get_match_name(self, match_nr):
        """Macht aus 'VF1' den Text 'Viertelfinale' anhand der config.ini"""
        # 1. Sicherstellen, dass es ein String ist und alle Zahlen am Ende abschneiden
        basis_id = str(match_nr).rstrip("0123456789").upper()
        
        # 2. Im Dictionary nachschauen. 
        # Fallback: Falls es nicht in der config steht, geben wir einfach die ID (z.B. "VF") zurück.
        return self.match_namen.get(basis_id, basis_id)

    def get_beamer_text(self, phase_enum):
        """Liefert das passende (Haupttext, Subtext) Tuple für den Beamer."""
        # Das .name Attribut eines Enums macht aus TurnierPhase.KO_PHASE den String "KO_PHASE"
        phase_str = phase_enum.name 
        
        haupt_text = self.beamer_texte.get(f"{phase_str}_HAUPT", "Warte...")
        sub_text = self.beamer_texte.get(f"{phase_str}_SUB", "")
        
        return haupt_text, sub_text

# --- Kurzer Testlauf (wird nur ausgeführt, wenn du diese Datei direkt startest) ---
if __name__ == "__main__":
    manager = DateiManager()
    # Teste das Schreiben
    manager.schreibe_next_match("Max", "Lisa", 5, 30)