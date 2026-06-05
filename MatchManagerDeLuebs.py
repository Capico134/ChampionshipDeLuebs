from enum import Enum, auto
from TurnierLogikDeLuebs import berechne_ko_phase

class TurnierPhase(Enum):
    NICHT_GESTARTET = auto()
    GRUPPENPHASE = auto()
    GRUPPEN_ABGESCHLOSSEN = auto()
    KO_PHASE = auto()
    BEENDET = auto()

class MatchManager:
    def __init__(self):
        self.teilnehmer = []
        self.gruppen = {}      
        self.spielplan = []    
        self.aktuelles_match_index = 0
        self.ergebnisse = {}   
        self.gruppen_zeiten = {}
        
#        self.phase = "GRUPPE" 
        # --- ELA: Sauberer initialer Status ---
        self.phase = TurnierPhase.NICHT_GESTARTET

        self.ko_spielplan = []
        self.ko_aktuell_index = 0

    # --- NEU: ELA Event-System ---
        self._on_match_changed_listeners = []        
   
    def bind_match_changed(self, callback_func):
        """Erlaubt anderen Modulen, sich auf Match-Wechsel zu abonnieren."""
        self._on_match_changed_listeners.append(callback_func)

    def _trigger_match_changed(self):
        """Sendet das Signal an alle Abonnenten."""
        for listener in self._on_match_changed_listeners:
            listener()   

    def setze_aktuelles_match(self, idx, is_ko=False):
        """Setzt den Match-Zeiger manuell (z.B. nach einem Reset)."""
        if is_ko:
            self.ko_aktuell_index = idx
        else:
            self.aktuelles_match_index = idx
        self._trigger_match_changed()
   
    def lade_teilnehmer(self, namensliste):
        self.teilnehmer = namensliste

    def setze_turnier_daten(self, gruppen_dict, spielplan_liste):
        self.gruppen = gruppen_dict
        self.spielplan = spielplan_liste
        self.aktuelles_match_index = 0
        self.ergebnisse = {}
        self.gruppen_zeiten = {g: "" for g in self.gruppen.keys()}
#        self.phase = "GRUPPE"
        self.phase = TurnierPhase.GRUPPENPHASE
        
        self.ko_spielplan = []
        self.ko_aktuell_index = 0
        
        for gruppe, spieler_liste in self.gruppen.items():
            for spieler in spieler_liste:
                self.ergebnisse[spieler] = {
                    "gruppe": gruppe, "spiele": 0, "punkte": 0,           
                    "score_erzielt": 0.0, "score_kassiert": 0.0, "differenz": 0.0       
                }
        self._trigger_match_changed()

    def starte_ko_phase(self): # <--- Nimmt keine Parameter mehr entgegen!
        self.phase = TurnierPhase.KO_PHASE       
        self.ko_aktuell_index = 0
        
        # --- ELA: Der Manager berechnet seinen K.O.-Baum jetzt selbst! ---
        anzahl = len(self.ergebnisse)
        self.ko_spielplan = berechne_ko_phase(self.ergebnisse, self.gruppen, anzahl)
        
        self._trigger_match_changed()
        return True

    def get_aktuelles_match(self):
        if self.phase == TurnierPhase.GRUPPENPHASE:
            if self.aktuelles_match_index < len(self.spielplan): return self.spielplan[self.aktuelles_match_index]
        elif self.phase == TurnierPhase.KO_PHASE:
            if self.ko_aktuell_index < len(self.ko_spielplan): return self.ko_spielplan[self.ko_aktuell_index]
        return None

    def get_naechstes_match(self):
        plan = self.ko_spielplan if self.phase == TurnierPhase.KO_PHASE else self.spielplan
        aktuell_idx = self.ko_aktuell_index if self.phase == TurnierPhase.KO_PHASE else self.aktuelles_match_index

        # Wir scannen die Liste von oben nach unten.
        # Wir suchen das erste Spiel, das noch NICHT gespielt ist 
        # UND das nicht das aktuell laufende ist.
        for i, m in enumerate(plan):
            if not m.get("gespielt", False) and i != aktuell_idx:
                return m
                
        return None # Wenn es kein weiteres offenes Spiel gibt

    def match_abschliessen(self):
        if self.phase == TurnierPhase.GRUPPENPHASE:
            neuer_index = len(self.spielplan)
            for i, m in enumerate(self.spielplan):
                if not m.get("gespielt", False):
                    neuer_index = i
                    break
            
            self.aktuelles_match_index = neuer_index
            self._trigger_match_changed() # <--- NEU: Vor dem Return klingeln!
            return self.aktuelles_match_index < len(self.spielplan)
            
        else: # KO_PHASE
            neuer_index = len(self.ko_spielplan)
            for i, m in enumerate(self.ko_spielplan):
                if not m.get("gespielt", False):
                    neuer_index = i
                    break
                    
            self.ko_aktuell_index = neuer_index
            self._trigger_match_changed() # <--- NEU: Vor dem Return klingeln!
            return self.ko_aktuell_index < len(self.ko_spielplan)

    def match_vorziehen(self, ziel_index):
        if self.phase == TurnierPhase.KO_PHASE: return False
        if ziel_index > self.aktuelles_match_index:
            match_zum_vorziehen = self.spielplan.pop(ziel_index)
            self.spielplan.insert(self.aktuelles_match_index, match_zum_vorziehen)
            self._trigger_match_changed()
            return True
        return False

    def trage_ergebnis_ein(self, base1, base2, total1, total2, pi_match_id="-"):
        match = self.get_aktuelles_match()
        if not match: return
        
        # --- FIX: Direkt die sauberen Argumente ins Update packen ---
        match.update({
            "base1": base1, 
            "base2": base2, 
            "total1": total1, 
            "total2": total2, 
            "pi_match_id": pi_match_id, 
            "gespielt": True
        })
            
        # --- ELA: Der Domino-Effekt! ---
        # Wenn Basis-Werte (neu) eingetragen werden, verfällt ein eventuelles altes Stechen sofort.
        match.pop("stechen_notwendig", None)
        match.pop("stechen_beendet", None)
        match.pop("stechen_b1", None)
        match.pop("stechen_b2", None)
        # -------------------------------

        if self.phase == TurnierPhase.GRUPPENPHASE:
            self.recalculate_stats()
        else:
            s1, s2 = match["spieler1"], match["spieler2"]
            if base1 > base2: winner, loser = s1, s2
            elif base2 > base1: winner, loser = s2, s1
            else: 
                winner = s1 if total1 >= total2 else s2
                loser = s2 if winner == s1 else s1
            
            match["winner"] = winner
            match["loser"] = loser
            self.update_ko_tree(match["match_nr"], winner, loser)
            
        # --- ELA: Alles in einem Abwasch erledigen! ---
        self.match_abschliessen() # Springt automatisch ein Spiel weiter und triggert den Event!
        self._evaluiere_turnier_status() # Prüft, ob das Turnier/die Phase nun vorbei ist
        
        # Hinweis: _trigger_match_changed() müssen wir hier NICHT nochmal rufen, 
        # weil match_abschliessen() das bereits für uns tut!
        return True

    def evaluiere_match_szenario(self, t1, t2):
        """
        Prüft ein eingehendes Ergebnis und sagt der GUI, welches Szenario vorliegt.
        Rückgabe: 'STECHEN_AKTIV', 'GLEICHSTAND', 'NORMAL' oder 'FEHLER'
        """
        match = self.get_aktuelles_match()
        if not match: 
            return "FEHLER"
            
        # Szenario A: Wir sind bereits in einem laufenden Stechen
        if match.get("stechen_notwendig"):
            return "STECHEN_AKTIV"
            
        # Szenario B: K.O.-Phase und exakter Gleichstand (auf 2 Nachkommastellen)
        is_ko = self.phase in [TurnierPhase.KO_PHASE, TurnierPhase.BEENDET]
        if is_ko and round(t1, 2) == round(t2, 2):
            return "GLEICHSTAND"
            
        # Szenario C: Ein ganz normales Match (Gruppe oder klares K.O.-Match)
        return "NORMAL"


    def update_ko_tree(self, nr, winner, loser):
        """Verteilt Gewinner und Verlierer (für Platz 3) im Baum."""
        for m in self.ko_spielplan:
            # Gewinner rücken vor
            if nr == "VF1" and m["match_nr"] == "HF1": m["spieler1"] = winner
            if nr == "VF2" and m["match_nr"] == "HF1": m["spieler2"] = winner
            if nr == "VF3" and m["match_nr"] == "HF2": m["spieler1"] = winner
            if nr == "VF4" and m["match_nr"] == "HF2": m["spieler2"] = winner
            if nr == "HF1" and m["match_nr"] == "FIN": m["spieler1"] = winner
            if nr == "HF2" and m["match_nr"] == "FIN": m["spieler2"] = winner
            # Verlierer rücken ins Spiel um Platz 3
            if nr == "HF1" and m["match_nr"] == "3PL": m["spieler1"] = loser
            if nr == "HF2" and m["match_nr"] == "3PL": m["spieler2"] = loser

    def recalculate_stats(self):
        """Baut die gesamte Tabelle aller Spieler anhand der Match-Historie komplett neu auf."""
        for name in self.ergebnisse:
            self.ergebnisse[name].update({"spiele": 0, "punkte": 0, "score_erzielt": 0.0, "score_kassiert": 0.0, "differenz": 0.0})
            
        for m in self.spielplan:
            if m.get("gespielt"):
                s1, s2 = m["spieler1"], m["spieler2"]
                b1, b2, t1, t2 = m["base1"], m["base2"], m["total1"], m["total2"]
                
                if b1 == b2: p1, p2 = 1, 1
                elif b1 > b2: p1, p2 = 3, 0
                else: p1, p2 = 0, 3

                for s, p, erzielt, kassiert in [(s1, p1, t1, t2), (s2, p2, t2, t1)]:
                    if s in self.ergebnisse:
                        self.ergebnisse[s]["spiele"] += 1
                        self.ergebnisse[s]["punkte"] += p
                        self.ergebnisse[s]["score_erzielt"] += erzielt
                        self.ergebnisse[s]["score_kassiert"] += kassiert
                        self.ergebnisse[s]["differenz"] = self.ergebnisse[s]["score_erzielt"] - self.ergebnisse[s]["score_kassiert"]

    def rename_player(self, old_name, new_name):
        # 1. Basics prüfen: Existiert der alte Name und ist der neue Name nicht leer?
        if old_name not in self.ergebnisse or not new_name: 
            return False
            
        # 2. DER SCHUTZWALL: Überschreiben verbieten, um Datenverlust zu verhindern!
        if new_name in self.ergebnisse: 
            return False 
            
        # 3. Kaskadierendes Update
        if old_name in self.teilnehmer: 
            self.teilnehmer[self.teilnehmer.index(old_name)] = new_name
            
        for g, players in self.gruppen.items():
            if old_name in players: 
                players[players.index(old_name)] = new_name
                
        # Den Key im Dictionary austauschen, Werte (Statistiken) behalten
        self.ergebnisse[new_name] = self.ergebnisse.pop(old_name)
        
        # Gruppenphase updaten
        for m in self.spielplan:
            if m.get("spieler1") == old_name: m["spieler1"] = new_name
            if m.get("spieler2") == old_name: m["spieler2"] = new_name
            
        # K.O.-Phase updaten
        for m in self.ko_spielplan:
            if m.get("spieler1") == old_name: m["spieler1"] = new_name
            if m.get("spieler2") == old_name: m["spieler2"] = new_name
            if m.get("winner") == old_name: m["winner"] = new_name
            if m.get("loser") == old_name: m["loser"] = new_name # <-- NEU: Auch den Verlierer umbenennen (wichtig für Spiel um Platz 3)
            
        return True

    def get_tabelle(self, gruppen_name):
        tabelle = []
        for name, stats in self.ergebnisse.items():
            if stats["gruppe"] == gruppen_name:
                row = {"name": name}; row.update(stats); tabelle.append(row)
        tabelle.sort(key=lambda x: (x["punkte"], x["differenz"], x["score_erzielt"]), reverse=True)
        return tabelle

    def update_player_stats(self, name, spiele, punkte, erzielt, kassiert):
        if name in self.ergebnisse:
            try:
                self.ergebnisse[name]["spiele"] = int(spiele)
                self.ergebnisse[name]["punkte"] = int(punkte)
                self.ergebnisse[name]["score_erzielt"] = float(erzielt)
                self.ergebnisse[name]["score_kassiert"] = float(kassiert)
                self.ergebnisse[name]["differenz"] = self.ergebnisse[name]["score_erzielt"] - self.ergebnisse[name]["score_kassiert"]
                return True
            except ValueError: return False
        return False

    def edit_match(self, idx, b1, b2, t1, t2, is_ko=False):
        plan = self.ko_spielplan if is_ko else self.spielplan
        if 0 <= idx < len(plan):
            m = plan[idx]
            try:
                m["base1"], m["base2"] = int(b1), int(b2)
                m["total1"], m["total2"] = float(t1), float(t2)
                m["gespielt"] = True
                if "pi_match_id" not in m: m["pi_match_id"] = "MANUELL"
                
                # --- ELA: Auch beim harten Modifizieren greift der Domino-Effekt! ---
                m.pop("stechen_notwendig", None)
                m.pop("stechen_beendet", None)
                m.pop("stechen_b1", None)
                m.pop("stechen_b2", None)
                # --------------------------------------------------------------------
                
                if not is_ko:
                    self.recalculate_stats()
                else:
                    # In der KO-Phase Gewinner neu ermitteln und Baum updaten
                    s1, s2 = m["spieler1"], m["spieler2"]
                    if m["base1"] > m["base2"]: w, l = s1, s2
                    elif m["base2"] > m["base1"]: w, l = s2, s1
                    else: 
                        w = s1 if m["total1"] >= m["total2"] else s2
                        l = s2 if w == s1 else s1
                    m["winner"], m["loser"] = w, l
                    self.update_ko_tree(m["match_nr"], w, l)
                    
                # --- ELA: HIER SIND DIE BEIDEN FEHLENDEN ZEILEN ---
                self._evaluiere_turnier_status() 
                self._trigger_match_changed()
                
                return True
            except ValueError: return False
        return False

    def reset_match(self, idx, is_ko=False):
        plan = self.ko_spielplan if is_ko else self.spielplan
        if 0 <= idx < len(plan):
            m = plan[idx]
            m["gespielt"] = False
            
            # --- ELA: Stechen-Zombies in die Lösch-Liste aufgenommen! ---
            keys_zum_loeschen = [
                "base1", "base2", "total1", "total2", "pi_match_id", "winner", "loser",
                "stechen_notwendig", "stechen_beendet", "stechen_b1", "stechen_b2"
            ]
            for k in keys_zum_loeschen:
                m.pop(k, None)
            # ------------------------------------------------------------
            
            if not is_ko:
                self.recalculate_stats()
            # Hinweis: Beim Resetten eines KO-Matches werden die Folge-Matches (noch) nicht geleert,
            # aber man kann das Match nun neu spielen.
            
            # --- ELA-ARCHITEKTUR: Die State-Machine regelt sich selbst ---
            if self.phase in [TurnierPhase.BEENDET, TurnierPhase.GRUPPEN_ABGESCHLOSSEN]:
                self.phase = TurnierPhase.KO_PHASE if is_ko else TurnierPhase.GRUPPENPHASE            
            
            return True
        return False


    def get_state(self):
        return {
            "teilnehmer": self.teilnehmer, "gruppen": self.gruppen,
            "spielplan": self.spielplan, "aktuelles_match_index": self.aktuelles_match_index,
            "ergebnisse": self.ergebnisse, "gruppen_zeiten": self.gruppen_zeiten,
            
            # WICHTIG: Der Key bleibt "turnier_modus", die Variable ist self.phase
            "turnier_modus": self.phase.name, 
            
            "ko_spielplan": self.ko_spielplan,
            "ko_aktuell_index": self.ko_aktuell_index
        }

    def load_state(self, state_dict):
        self.teilnehmer = state_dict.get("teilnehmer", [])
        self.gruppen = state_dict.get("gruppen", {})
        self.spielplan = state_dict.get("spielplan", [])
        self.aktuelles_match_index = state_dict.get("aktuelles_match_index", 0)
        self.ergebnisse = state_dict.get("ergebnisse", {})
        self.gruppen_zeiten = state_dict.get("gruppen_zeiten", {})

        # 1. Wert aus der JSON lesen (Fallback: NICHT_GESTARTET)
        geladener_modus = state_dict.get("turnier_modus", "NICHT_GESTARTET").upper()
        # 2. Übersetzungs-Wörterbuch für alte oder manuell falsch getippte Versionen
        legacy_mapping = {
            "GRUPPE": "GRUPPENPHASE",
            "KO": "KO_PHASE"
        }
        geladener_modus = legacy_mapping.get(geladener_modus, geladener_modus)
        # 3. Kugelsichere Umwandlung ins Enum (Verhindert Absturz bei Tippfehlern in der JSON)
        try:
            self.phase = TurnierPhase[geladener_modus]
        except KeyError:
            print(f"⚠️ Warnung: Unbekannter Turnier-Modus '{geladener_modus}' in JSON. Setze auf NICHT_GESTARTET.")
            self.phase = TurnierPhase.NICHT_GESTARTET

        self.ko_spielplan = state_dict.get("ko_spielplan", [])
        self.ko_aktuell_index = state_dict.get("ko_aktuell_index", 0)
        self._evaluiere_turnier_status()
        self._trigger_match_changed()
        
    def _evaluiere_turnier_status(self):
        """Prüft vollautomatisch, ob alle Spiele einer Phase gespielt wurden und schaltet die Enum um."""
        
        if self.phase in [TurnierPhase.GRUPPENPHASE, TurnierPhase.GRUPPEN_ABGESCHLOSSEN]:
            alle_fertig = len(self.spielplan) > 0 and all(m.get("gespielt", False) for m in self.spielplan)
            # Automatischer Wechsel! (Auch zurück zur GRUPPENPHASE, falls man ein Match resettet)
            self.phase = TurnierPhase.GRUPPEN_ABGESCHLOSSEN if alle_fertig else TurnierPhase.GRUPPENPHASE
            
        elif self.phase in [TurnierPhase.KO_PHASE, TurnierPhase.BEENDET]:
            alle_fertig = len(self.ko_spielplan) > 0 and all(m.get("gespielt", False) for m in self.ko_spielplan)
            # Automatischer Wechsel, sobald das letzte K.O.-Match beendet ist!
            self.phase = TurnierPhase.BEENDET if alle_fertig else TurnierPhase.KO_PHASE
            
    def aktiviere_stechen(self, b1, b2, t1, t2, pi_match_id):
        match = self.get_aktuelles_match()
        if not match: return
        
        # Wir speichern das unentschiedene Haupt-Ergebnis ab, 
        # ABER wir setzen noch keinen Sieger und rücken nicht vor!
        match["base1"] = b1
        match["base2"] = b2
        match["total1"] = t1
        match["total2"] = t2
        match["pi_match_id"] = pi_match_id
        
        # DAS MAGISCHE FLAG:
        match["stechen_notwendig"] = True

    def trage_stechen_ein(self, stechen_b1, stechen_b2):
        match = self.get_aktuelles_match()
        if not match: return
        
        # Wir speichern die Stechen-Punkte separat ab
        match["stechen_b1"] = stechen_b1
        match["stechen_b2"] = stechen_b2
        
        # Den Sieger ermitteln
        if stechen_b1 > stechen_b2:
            match["winner"] = match["spieler1"]
            match["loser"] = match["spieler2"]
        else:
            match["winner"] = match["spieler2"]
            match["loser"] = match["spieler1"]
            
        match["gespielt"] = True
        match.pop("stechen_notwendig", None) # Flag wieder löschen
        match["stechen_beendet"] = True      # Für den HTML-Bericht als Notiz
        
        self.update_ko_tree(match["match_nr"], match["winner"], match["loser"])
        
        
        self.match_abschliessen()  # Jetzt rücken wir vor!  