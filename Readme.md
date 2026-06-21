# Championship DeLübs 📊

Die professionelle Regie-Zentrale für das **Shooting DeLübs** System. 
Dieses Tool verwaltet Turniere, generiert faire Spielpläne und steuert die Live-Anzeige für Zuschauer.

## 🚀 Schnellstart (In 3 Schritten zum Turnier)
Wir haben den Startprozess extrem vereinfacht. Du musst keine Kommandozeilen-Parameter auswendig lernen:

1. **Installieren:** Lade dieses Repository herunter und installiere die nötigen Python-Bibliotheken (`pip install -r requirements.txt`).
2. **Konfigurieren:** Kopiere die Datei `config.example.ini` und benenne sie in `config.ini` um.
3. **Starten:** Führe einfach die **`Start.bat`** aus!

Der intelligente Launcher (`Start.bat`) liest Deine `config.ini` vollautomatisch aus und entscheidet selbst, ob er das reine Basis-Turnier oder das komplette Studio-Kiosk-System lädt.

## Features
- **Dynamische Turnierlogik**: Automatische Generierung von Gruppenphasen und K.O.-Bäumen.
- **Live-Anzeige**: Separates Public-Display (Beamer-Output) für aktuelle Spielstände und Tabellen.
- **DPI-Aware**: Optimiert für 1080p-Ausgabe, auch auf hochauflösenden 4K-Systemen.
- **Robuste Verwaltung**: Integrierter State-Manager für Savegames und Match-Historie.

## 🖥️ Pro-Features & Kiosk-System
Für den echten Turniereinsatz am Schießstand (Multi-Monitor-Setups, Beamer, Regie-PC/Laptop) bringt dieses Projekt eine mächtige Erweiterung mit. 

Wenn du in deiner `config.ini` den Wert `StartFramework = True` setzt, aktiviert die `Start.bat` im Hintergrund automatisch das **StartFramework**:
* **Hardware-Agnostisch:** Passt die Tkinter-Skalierung dynamisch an (egal ob 1080p-Laptop oder 4K-TV), sodass das Layout nie zerschossen wird.
* **Smartes Layout-Memory:** Ordne das Hauptmenü und das Beamer-Fenster einmal an. Drücke `Alt+F8`, und das Framework speichert die exakten Koordinaten dauerhaft in der `config.ini`. Beim nächsten Start fliegt alles an seinen Platz.
* **Rahmenloser Kiosk-Modus:** Blende Fensterrahmen (z.B. für den Beamer) per `Alt+F12` ein oder aus. 

## 🛠️ Nützliche Helfer-Skripte (im `tools/`-Ordner)
* **`Auto_Minimizer.py`:** Ein kleines Hintergrund-Tool, das Turnierexporte überwacht, bei Abschluss blitzschnell das Hauptfenster für einfaches Teilen (z.B. per E-Mail) minimiert und es per `ESC` sofort wieder in den Fokus holt.
* **`ZZ_GitUpdate.bat`:** Sorgt für automatische, reibungslose Updates direkt aus dem GitHub-Repository.

## 🔗 System-Verbund & Hardware
Dieses Programm arbeitet Hand in Hand mit [Shooting DeLübs](https://github.com/Capico134/ShootingDeLuebs) (Die Treffer-Erfassung & Hardware-Steuerung).

Willst du das volle Live-Erlebnis am Schießstand? 
👉 **[Hier geht's zur Hardware-Anleitung für das Raspberry Pi 5 Setup](Hardware-Setup-Pi5.md)**

---
*Lizenz: CC BY-NC-SA 4.0 - Erstellt für die Leidenschaft am Sport und sauberem Code.*