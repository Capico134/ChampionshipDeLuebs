import itertools
import math
import random

def generiere_spielplan(namen, gruppen_groesse=4, zufall=False):
    # --- NEU: Prüfung auf doppelte Namen (Sicherheitsschranke) ---
    if len(namen) != len(set(namen)):
        # Wir suchen gezielt heraus, welche Namen doppelt sind, für eine saubere Fehlermeldung
        doppelte = set([name for name in namen if namen.count(name) > 1])
        raise ValueError(f"Jeder Teilnehmername muss einzigartig sein!\nFolgende Namen sind doppelt: {', '.join(doppelte)}")
    
    # ELA: Wenn "zufall" wahr ist, mischen wir eine Kopie der Liste
    if zufall:
        namen = namen.copy()
        random.shuffle(namen)

    anzahl = len(namen)
    anzahl_gruppen = math.ceil(anzahl / gruppen_groesse)
    gruppen_namen = [chr(65 + i) for i in range(anzahl_gruppen)] 
    
    gruppen = {}
    for i, g_name in enumerate(gruppen_namen):
        start = i * gruppen_groesse
        end = start + gruppen_groesse
        gruppen[g_name] = namen[start:end]
    
    # --- Heimspiel-Tracker für faire Links/Rechts-Verteilung in ungeraden Gruppen ---
    heim_spiele = {spieler: 0 for spieler in namen}
    
    gruppen_phasen = {}
    for g_name, mitglieder in gruppen.items():
        n = len(mitglieder)
        if n < 2:
            gruppen_phasen[g_name] = []
            continue
            
        phasen = []
        
        # =================================================================
        # DER HYBRID-MOTOR: Wählt die perfekte Logik je nach Gruppengröße
        # =================================================================
        
        if n % 2 == 0:
            # 1. GERADE GRUPPEN (z.B. 4 oder 6 Spieler) -> Perfekte Kreis-Methode
            # Verhindert den Bug, dass bei 6 Spielern jemand dreimal schießt.
            spieler = mitglieder.copy()
            runden = n - 1
            for runde in range(runden):
                phase = []
                for i in range(n // 2):
                    heim = spieler[i]
                    gast = spieler[n - 1 - i]
                    
                    # Fairer Wechsel von linker/rechter Seite für den Anker-Spieler
                    if i == 0 and runde % 2 != 0:
                        phase.append((gast, heim))
                    else:
                        phase.append((heim, gast))
                phasen.append(phase)
                spieler.insert(1, spieler.pop())
                
        else:
            # 2. UNGERADE GRUPPEN (z.B. 3 oder 5 Spieler) -> Dein Original-Code!
            # Zwingt jeden an den Schießstand, notfalls schießt jemand doppelt!
            paarungen = list(itertools.combinations(mitglieder, 2))
            while paarungen:
                uncovered = set(mitglieder)
                phase = []
                
                # Runde 1: Versuche alle unverbrauchten zu paaren
                for paar in paarungen[:]:
                    if not uncovered: break
                    a, b = paar
                    if a in uncovered and b in uncovered:
                        if heim_spiele[a] <= heim_spiele[b]:
                            phase.append((a, b))
                            heim_spiele[a] += 1
                        else:
                            phase.append((b, a))
                            heim_spiele[b] += 1
                        uncovered.discard(a)
                        uncovered.discard(b)
                        paarungen.remove(paar)
                
                # Runde 2: Wer noch nicht geschossen hat, muss jetzt gegen jemanden ran, der schon dran war
                for paar in paarungen[:]:
                    if not uncovered: break
                    a, b = paar
                    if a in uncovered or b in uncovered:
                        if heim_spiele[a] <= heim_spiele[b]:
                            phase.append((a, b))
                            heim_spiele[a] += 1
                        else:
                            phase.append((b, a))
                            heim_spiele[b] += 1
                        uncovered.discard(a)
                        uncovered.discard(b)
                        paarungen.remove(paar)

                phasen.append(phase)
                
        gruppen_phasen[g_name] = phasen

    # =================================================================
    # DER WECHSEL-MODUS (Phase 1 A, Phase 1 B, Phase 2 A...)
    # =================================================================
    spielplan = []
    match_nr = 1
    max_phasen = max((len(ph) for ph in gruppen_phasen.values()), default=0)
    
    for phase_idx in range(max_phasen):
        for g_name in gruppen_namen:
            phasen = gruppen_phasen.get(g_name, [])
            if phase_idx < len(phasen):
                for p in phasen[phase_idx]:
                    spielplan.append({
                        "match_nr": match_nr,
                        "gruppe": g_name,
                        "spieler1": p[0],
                        "spieler2": p[1],
                        "gespielt": False
                    })
                    match_nr += 1
                    
    return gruppen, spielplan


def generiere_setzliste(ergebnisse, gruppen): #Für KO-Phase
    """Erstellt die absolut faire, universelle Rangliste (Seeding) aller Spieler."""
    # 1. Tabellen pro Gruppe berechnen
    qualifikanten = []
    for g_name in sorted(gruppen.keys()):
        tabelle = []
        for name, stats in ergebnisse.items():
            if stats["gruppe"] == g_name:
                row = {"name": name}
                row.update(stats)
                tabelle.append(row)
        tabelle.sort(key=lambda x: (x["punkte"], x["differenz"], x["score_erzielt"]), reverse=True)
        if tabelle:
            qualifikanten.append(tabelle)

    # 2. Die universelle Setzliste (Seeding) aufbauen
    erste, zweite, weitere = [], [], []
    for tab in qualifikanten:
        if len(tab) > 0: erste.append(tab[0])
        if len(tab) > 1: zweite.append(tab[1])
        if len(tab) > 2: weitere.extend(tab[2:])
        
    sort_key = lambda x: (x["punkte"], x["differenz"], x["score_erzielt"])
    erste.sort(key=sort_key, reverse=True)
    zweite.sort(key=sort_key, reverse=True)
    weitere.sort(key=sort_key, reverse=True)
    
    return erste + zweite + weitere


def berechne_ko_phase(ergebnisse, gruppen, anzahl_teilnehmer, klasse=None): 
    # NEU: Direkter Aufruf der Funktion (ohne TurnierLogik. davor)
    setzliste = generiere_setzliste(ergebnisse, gruppen)

    if anzahl_teilnehmer <= 4:
        while len(setzliste) < 4: setzliste.append({"name": "Freilos"})
        return [
            {"match_nr": "3PL",  "spieler1": setzliste[2]["name"], "spieler2": setzliste[3]["name"]},
            {"match_nr": "FIN",  "spieler1": setzliste[0]["name"], "spieler2": setzliste[1]["name"]}
        ]
        
    elif anzahl_teilnehmer <= 8:
        while len(setzliste) < 4: setzliste.append({"name": "Freilos"})
        return [
            {"match_nr": "HF1",  "spieler1": setzliste[0]["name"], "spieler2": setzliste[3]["name"]},
            {"match_nr": "HF2",  "spieler1": setzliste[1]["name"], "spieler2": setzliste[2]["name"]},
            {"match_nr": "3PL",  "spieler1": "?", "spieler2": "?"},
            {"match_nr": "FIN",  "spieler1": "?", "spieler2": "?"}
        ]
        
    else:
        while len(setzliste) < 8: setzliste.append({"name": "Freilos"})
        return [
            {"match_nr": "VF1",  "spieler1": setzliste[0]["name"], "spieler2": setzliste[7]["name"]},
            {"match_nr": "VF2",  "spieler1": setzliste[1]["name"], "spieler2": setzliste[6]["name"]},
            {"match_nr": "VF3",  "spieler1": setzliste[2]["name"], "spieler2": setzliste[5]["name"]},
            {"match_nr": "VF4",  "spieler1": setzliste[3]["name"], "spieler2": setzliste[4]["name"]},
            {"match_nr": "HF1",  "spieler1": "?", "spieler2": "?"},
            {"match_nr": "HF2",  "spieler1": "?", "spieler2": "?"},
            {"match_nr": "3PL",  "spieler1": "?", "spieler2": "?"},
            {"match_nr": "FIN",  "spieler1": "?", "spieler2": "?"}
        ]