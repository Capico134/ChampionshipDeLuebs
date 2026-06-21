# Hardware-Setup: Raspberry Pi 5 für das Live-Turnier einrichten

Diese Anleitung beschreibt, wie du einen Raspberry Pi 5 so einrichtest, dass er perfekt mit *Championship DeLübs* zusammenarbeitet. 

Das Ziel:
1. Der Pi spannt ein eigenes, unabhängiges WLAN auf (Access Point), in das sich der Turnier-PC einloggen kann.
2. Der Pi stellt zwei Netzwerkfreigaben (Samba) zur Verfügung, damit der PC auf die Speicherstände und Live-Daten zugreifen kann.

---

## ⚠️ Wichtiger Hinweis zum Benutzernamen
In dieser Anleitung wird der Benutzername **`deluebs`** verwendet (dies war der Benutzername bei der Entwicklung). 
Wenn dein Pi einen anderen Benutzernamen hat (z.B. den Standardnamen `pi` oder deinen eigenen), musst du in den folgenden Befehlen und Konfigurationen `deluebs` durch deinen eigenen Benutzernamen ersetzen! 
*(Tipp: Du kannst deinen aktuellen Benutzernamen herausfinden, indem du `whoami` in die Pi-Konsole eintippst).*

---

## Schritt 1: Das eigene Turnier-WLAN (Access Point) einrichten

Der Pi soll unabhängig vom Internet-Router der Halle ein eigenes Netzwerk namens "ShootingDeLuebs" bereitstellen. Wir nutzen dafür den NetworkManager (`nmcli`).

Führe diese Befehle nacheinander im Terminal des Raspberry Pi aus:

**1. Die WLAN-Verbindung erstellen:**
sudo nmcli con add type wifi ifname wlan0 mode ap con-name TurnierNet ssid ShootingDeLuebs autoconnect yes

**2. Das WLAN-Passwort festlegen:**
*(Ersetze "DeinPasswort123" durch ein sicheres Passwort mit mindestens 8 Zeichen).*
sudo nmcli con modify TurnierNet wifi-sec.key-mgmt wpa-psk wifi-sec.psk "DeinPasswort123"

**3. Eine feste IP-Adresse vergeben:**
*(Der Pi bekommt die IP `192.168.4.1` und agiert als Router für das Turniernetz).*
sudo nmcli con modify TurnierNet ipv4.method shared ipv4.addresses 192.168.4.1/24

**4. Den Access Point starten:**
sudo nmcli con up TurnierNet

Dein Turnier-WLAN sollte jetzt auf anderen Geräten (z.B. an deinem Smartphone oder Turnier-PC) sichtbar sein!

---

## Schritt 2: Samba für den Datenaustausch vorbereiten (Netzwerklaufwerke)

Damit der Windows-Turnier-PC auf die Daten des Pi zugreifen kann, richten wir Samba (SMB) ein. Wir brauchen zwei Freigaben: Eine für die dauerhaften Highscores und eine auf der extrem schnellen RAM-Disk für den Live-Ticker (das schont die SD-Karte!).

**1. Samba installieren:**
sudo apt update && sudo apt install samba -y

**2. Den Ordner für die dauerhaften Spielstände erstellen:**
mkdir -p /home/deluebs/ShootingDeLuebs/savegames
*(Hinweis: Denke daran, `deluebs` anzupassen, falls dein User anders heißt!)*

**3. Samba konfigurieren:**
Öffne die Konfigurationsdatei mit einem Editor (z.B. nano):
sudo nano /etc/samba/smb.conf

Scrolle ganz nach unten an das Ende der Datei und füge diese beiden Blöcke hinzu:

[savegames]
path = /home/deluebs/ShootingDeLuebs/savegames
writeable = yes
browseable = yes
public = yes
create mask = 0777
directory mask = 0777
force user = deluebs

[shooting_live]
path = /dev/shm/shooting_live
writeable = yes
browseable = yes
public = yes
create mask = 0777
directory mask = 0777
force user = deluebs

*(Speichern und schließen in Nano: `STRG+O`, `Enter`, `STRG+X`)*

**4. Samba-Benutzerpasswort festlegen und Neustart:**
Aus Sicherheitsgründen musst du für den Samba-Zugriff ein Passwort festlegen.
sudo smbpasswd -a deluebs

Starte den Samba-Dienst anschließend neu, um die Änderungen zu übernehmen:
sudo systemctl restart smbd

---

## Schritt 3: Den Turnier-PC verbinden

Das System am Pi ist nun fertig! Jetzt musst du nur noch den Windows-PC einklinken.

1. Verbinde den Windows-PC mit dem neuen WLAN **ShootingDeLuebs**.
2. Binde die beiden Netzwerklaufwerke unter Windows ein. Nutze dafür die feste IP-Adresse des Pi:
   * Für die Highscores (z.B. als Laufwerk Z: verbinden): `\\192.168.4.1\savegames`
   * Für den Live-Ticker (z.B. als Laufwerk Y: verbinden): `\\192.168.4.1\shooting_live`
3. Trage diese verbundenen Netzlaufwerke entsprechend in der `config.ini` deines Turnier-PCs ein.

*(Hinweis zum Live-Ticker-Ordner: Der Ordner `/dev/shm/shooting_live` wird vom Pi automatisch beim Start des Python-Spiels erstellt. Die Samba-Freigabe funktioniert trotzdem schon im Voraus, da der Dienst den Pfad beim Erstellen sofort erkennt).*