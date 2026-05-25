import tkinter as tk
from tkinter import ttk, messagebox
import os
from PublicDisplayDeLuebs import PublicDisplay
from HtmlDeLuebs import HtmlExporter
from TurnierLogikDeLuebs import generiere_spielplan, berechne_ko_phase
from MatchManagerDeLuebs import TurnierPhase
import json #Für Live-Ticker
import ctypes

# --- Windows High-DPI Fix für gestochen scharfe Schriften ---
try:
    # Sagt Windows: "Skaliere mich nicht wie ein Bild, ich rendere Schriften selbst scharf!"
    ctypes.windll.shcore.SetProcessDpiAwareness(1)
except Exception:
    pass # Falls das Skript mal auf Linux/Mac oder einem alten Windows läuft, ignorieren wir es.
# ------------------------------------------------------------

class TurnierGUI:
    def __init__(self, root, datei_manager, match_manager, version, auto_beamer=False, always_on_top=False):
        # 1. Variablen und Zustände speichern (Keine Aktionen!)
        self.root = root
        self.datei_manager = datei_manager
        self.match_manager = match_manager
        # --- NEU: ELA - Einmal das Radio abonnieren ---
        self.match_manager.bind_match_changed(self.match_zu_pi)
                
        self.version = version
        self.time_entries = {}
        self.html_exporter = HtmlExporter()
        self.beamer_window = None
        self.auto_beamer = auto_beamer # Speichern wir uns für den Motorstart
        self.last_mtime = 0            # Variable anlegen, aber noch nix starten!
        
        self.quick_messages = self.datei_manager.ticker_templates       
        
        # 2. Fenster definieren
        self.root.title(f"Championship DeLübs v{self.version}")
        self.root.geometry("1200x850")
        if always_on_top:
            self.root.attributes('-topmost', True)

        # Status-Variablen anlegen (mit sauberen Default-Werten)
        self.var_matches_per_page = tk.IntVar(value=20)
        self.var_groups_per_page = tk.IntVar(value=3)
        
        # 3. UI aufbauen
        self.setup_ui()
        
        # 4. Key-Bindings
        self.root.bind("<Control_L>", self.ergebnis_abholen)
        
        ## --- NEU: ELA - Konfigurierbare Beamer-Steuerleiste ---
        #self.beamer_frame = tk.Frame(self.root)
        #self.beamer_frame.pack(pady=10)
        #
        ## Der Button kommt ganz nach links
        #self.btn_beamer = ttk.Button(self.beamer_frame, text="📺 BEAMER-ANZEIGE ÖFFNEN", command=self.open_beamer)
        #self.btn_beamer.pack(side="left", padx=(0, 30)) # 30px Abstand nach rechts
        #
        #
        ## Spinbox 1: Matches pro Seite
        #tk.Label(self.beamer_frame, text="Matches pro Seite:").pack(side="left", padx=(0, 5))
        #ttk.Spinbox(self.beamer_frame, from_=5, to=50, width=4, textvariable=self.var_matches_per_page).pack(side="left", padx=(0, 20))
        #
        ## Spinbox 2: Gruppen pro Seite
        #tk.Label(self.beamer_frame, text="Gruppen pro Seite:").pack(side="left", padx=(0, 5))
        #ttk.Spinbox(self.beamer_frame, from_=1, to=10, width=4, textvariable=self.var_groups_per_page).pack(side="left")
        #
        # FERTIG! Die __init__ ist jetzt dumm, sauber und extrem schnell.

    # --- NEU: Diese Methode kümmert sich um den eigenen Titel ---
    def set_pause_title(self, is_paused):
        if is_paused:
            self.root.title(f"Championship DeLübs v{self.version} [⏸️ PAUSIERT]")
        else:
            self.root.title(f"Championship DeLübs v{self.version}")


    def start_turnier(self):
        """Zündet den 'Motor': Startet das Live-Polling und ggf. den Beamer."""
        
        # 1. Beamer Autostart (ohne starren Timer, sondern logisch eventbasiert)
        if self.auto_beamer:
            print("Autostart-Signal empfangen: Beamer wird geladen...")
            self.root.after_idle(self.open_beamer)
            
        # 2. Alte Ticker-Dateien aufräumen
        self.datei_manager.loesche_live_datei()
        
        # 3. Den Hintergrund-Herzschlag (Live-Polling) starten
        self.start_live_polling()

    def after_load_setup(self):
        """Aktualisiert alle Anzeigen und Tabs, nachdem ein Spielstand geladen wurde."""
        self.update_all_displays()
        self.build_time_inputs()
        
        # Cleverer Tab-Wechsel: Sind wir schon in der K.O.-Phase?
        if getattr(self.match_manager, "phase", None) in [TurnierPhase.KO_PHASE, TurnierPhase.BEENDET]:
            self.notebook.select(3) # Springe direkt zum K.O.-Tab
        else:
            self.notebook.select(1) # Springe zur Gruppenphase


    def setup_ui(self):
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        self.setup_frame = ttk.Frame(self.notebook, padding=20)
        self.notebook.add(self.setup_frame, text=" 1. Teilnehmer-Setup ")
        self.build_setup_tab()

        self.control_frame = ttk.Frame(self.notebook, padding=20)
        self.notebook.add(self.control_frame, text=" 2. Gruppen-Matches ")
        self.build_control_tab()

        self.overview_frame = ttk.Frame(self.notebook, padding=20)
        self.notebook.add(self.overview_frame, text=" 3. Teilnehmer-Statistik ")
        self.build_overview_tab()
        
        self.ko_frame = ttk.Frame(self.notebook, padding=20)
        self.notebook.add(self.ko_frame, text=" 4. K.O.-Phase 🏆 ")
        self.build_ko_tab()
        
        # ==========================================================
        # --- NEU: ELA - Kombinierte Fußleiste (Status + Beamer) ---
        # ==========================================================
        bottom_bar = ttk.Frame(self.root)
        bottom_bar.pack(side=tk.BOTTOM, fill=tk.X, padx=10, pady=5)

        # 1. Status ganz links ankleben
        self.status_label = ttk.Label(bottom_bar, text="Bereit", font=("Arial", 10))
        self.status_label.pack(side=tk.LEFT)

        # 2. Container für Beamer-Controls ganz rechts ankleben
        beamer_controls = ttk.Frame(bottom_bar)
        beamer_controls.pack(side=tk.RIGHT)

        # Innerhalb des Containers von links nach rechts anordnen:
        self.btn_beamer = ttk.Button(beamer_controls, text="📺 BEAMER-ANZEIGE ÖFFNEN", command=self.open_beamer)
        self.btn_beamer.pack(side=tk.LEFT, padx=(0, 20))

        ttk.Label(beamer_controls, text="Matches pro Seite:").pack(side=tk.LEFT, padx=(0, 5))
        ttk.Spinbox(beamer_controls, from_=5, to=50, width=4, textvariable=self.var_matches_per_page).pack(side=tk.LEFT, padx=(0, 15))

        ttk.Label(beamer_controls, text="Gruppen pro Seite:").pack(side=tk.LEFT, padx=(0, 5))
        ttk.Spinbox(beamer_controls, from_=1, to=10, width=4, textvariable=self.var_groups_per_page).pack(side=tk.LEFT)    

    def build_setup_tab(self):
        # --- NEU: ELA-LÖSUNG (Laden direkt im UI statt als Startup-Popup) ---
        resume_frame = ttk.LabelFrame(self.setup_frame, text=" 💾 Gespeicherte Turniere ", padding=10)
        resume_frame.pack(fill=tk.X, pady=(0, 15))

        neueste_datei = self.datei_manager.finde_neuesten_pfad()
        if neueste_datei:
            dateiname = os.path.basename(neueste_datei)
            ttk.Button(resume_frame, text=f"▶ LETZTEN STAND FORTSETZEN ({dateiname})", 
                       command=lambda: self.load_specific_state(neueste_datei)).pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)

        ttk.Button(resume_frame, text="📂 ANDEREN STAND LADEN...", 
                   command=self.load_manual_state).pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        # ---------------------------------------------------------------------

        # 1. Gruppengröße
        rahmen_top = ttk.Frame(self.setup_frame)
        rahmen_top.pack(fill=tk.X, pady=(0, 10))

        ttk.Label(rahmen_top, text="Gruppengröße:", font=("Arial", 12)).pack(side=tk.LEFT, padx=(0, 10))
        self.gruppen_groesse_var = tk.IntVar(value=4) 
        ttk.Spinbox(rahmen_top, from_=2, to=8, textvariable=self.gruppen_groesse_var, width=5, font=("Arial", 12)).pack(side=tk.LEFT)

        # --- NEU: Der Checkbutton für Zufallsgruppen ---
        self.zufall_var = tk.BooleanVar(value=True) # Standardmäßig an
        ttk.Checkbutton(
            rahmen_top, 
            text="Spieler zufällig auf Gruppen verteilen", 
            variable=self.zufall_var
        ).pack(side=tk.LEFT, padx=(30, 0))

        # 2. Das Label für das Textfeld anpassen
        ttk.Label(self.setup_frame, text="Neues Turnier: Teilnehmer (Ein Name pro Zeile):", font=("Arial", 12)).pack(anchor=tk.W)
        self.name_input = tk.Text(self.setup_frame, height=15, width=40)
        self.name_input.pack(fill=tk.X, pady=10)
        
        if os.path.exists("teilnehmer.txt"):
            with open("teilnehmer.txt", "r", encoding="utf-8") as f:
                self.name_input.insert(tk.END, f.read())
        else:
            self.name_input.insert(tk.END, "Petra\nSarah\nTom\nBernd\nBen\nLisa\nMax\nHannes\nAnna\nJulia\nMichaela\nChris")
            
        ttk.Button(self.setup_frame, text="NEUES TURNIER STARTEN", command=self.turnier_starten).pack(fill=tk.X, pady=10)

    # --- Die zwei neuen Helfer-Funktionen für die Buttons ---
    def load_specific_state(self, pfad):
        stand = self.datei_manager.lade_stand_aus_datei(pfad)
        self.match_manager.load_state(stand)
        self.after_load_setup()
        #self.match_zu_pi()

    def load_manual_state(self):
        from tkinter import filedialog
        gewaehlte_datei = filedialog.askopenfilename(
            initialdir="savegames",
            title="Turnierstand auswählen",
            filetypes=[("JSON Dateien", "*.json")]
        )
        if gewaehlte_datei:
            self.load_specific_state(gewaehlte_datei)

    def build_control_tab(self):
        self.lbl_group_match = ttk.Label(self.control_frame, text="Kein Gruppenmatch aktiv", font=("Arial", 14, "bold"))
        self.lbl_group_match.pack(pady=(0, 10))

        self.group_btn_frame = ttk.Frame(self.control_frame)
        self.group_btn_frame.pack(fill=tk.X)
        
        self.btn_send_pi_grp = ttk.Button(self.group_btn_frame, text="GRUPPE -> PI SENDEN", command=self.match_zu_pi)
        self.btn_send_pi_grp.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=5)
        self.btn_skip_grp = ttk.Button(self.group_btn_frame, text="ÜBERSPRINGEN / MANUELL", command=self.match_ueberspringen)
        self.btn_skip_grp.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=5)
        self.btn_get_pi_grp = ttk.Button(self.group_btn_frame, text="ERGEBNIS ABHOLEN", command=self.ergebnis_abholen)
        self.btn_get_pi_grp.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=5)

        self.time_frame = ttk.LabelFrame(self.control_frame, text=" Zeitplan ", padding=10)
        self.time_frame.pack(fill=tk.X, pady=10)

        # --- FIX: DAS SANDWICH-PRINZIP (Erst unten, dann die Mitte) ---
        
        # 1. Ticker-Frame (Ganz unten ankleben)
        ticker_frame_grp = ttk.LabelFrame(self.control_frame, text=" 📢 Regie-Nachricht an Beamer senden ", padding=5)
        ticker_frame_grp.pack(side=tk.BOTTOM, fill=tk.X, pady=(10, 0))
        
        if not hasattr(self, 'ticker_var'):
            self.ticker_var = tk.StringVar() 
            
        combo_grp = ttk.Combobox(ticker_frame_grp, values=self.quick_messages, state="readonly", width=30)
        combo_grp.set("Vorlagen auswählen...")
        combo_grp.pack(side=tk.LEFT, padx=5)
        combo_grp.bind("<<ComboboxSelected>>", self.load_ticker_template)
            
        ttk.Entry(ticker_frame_grp, textvariable=self.ticker_var, font=("Arial", 11)).pack(side=tk.LEFT, expand=True, fill=tk.X, padx=5)
        ttk.Button(ticker_frame_grp, text="SENDEN", command=self.send_ticker_msg).pack(side=tk.LEFT, padx=2)
        ttk.Button(ticker_frame_grp, text="LÖSCHEN", command=self.clear_ticker_msg).pack(side=tk.LEFT, padx=2)

        # 2. Action-Frame (Über dem Ticker ankleben)
        action_frame = ttk.Frame(self.control_frame)
        action_frame.pack(side=tk.BOTTOM, fill=tk.X)
        ttk.Button(action_frame, text="⬇ VORZIEHEN", command=lambda: self.match_vorziehen_gui(False)).pack(side=tk.LEFT, expand=True, fill=tk.X, padx=2)
        ttk.Button(action_frame, text="✎ EDITIEREN", command=lambda: self.edit_match_gui(False)).pack(side=tk.LEFT, expand=True, fill=tk.X, padx=2)
        ttk.Button(action_frame, text="🔄 NEU STARTEN", command=lambda: self.reset_match_gui(False)).pack(side=tk.LEFT, expand=True, fill=tk.X, padx=2)

        # 3. Treeview (Füllt jetzt automatisch den kompletten restlichen Platz in der Mitte auf!)
        columns = ("nr", "status", "gruppe", "paarung", "punkte", "diff", "pi_id")
        self.tree_matches = ttk.Treeview(self.control_frame, columns=columns, show="headings", height=12)
        
        for col, txt, w in zip(columns, ["Nr.", "Status", "Gruppe", "Paarung", "Punkte", "Gesamt (Diff)", "Pi-ID"], [40, 80, 60, 200, 80, 140, 60]):
            self.tree_matches.heading(col, text=txt)
            self.tree_matches.column(col, width=w, anchor="center" if col != "paarung" else "w")
            
        self.tree_matches.pack(side=tk.TOP, fill=tk.BOTH, expand=True, pady=(10, 10))

    def build_ko_tab(self):
        self.lbl_ko_match = ttk.Label(self.ko_frame, text="K.O.-Phase nicht gestartet", font=("Arial", 14, "bold"))
        self.lbl_ko_match.pack(pady=(0, 10))
        
        self.ko_pi_frame = ttk.Frame(self.ko_frame)
        self.ko_pi_frame.pack(fill=tk.X, pady=5)

        self.btn_start_ko = ttk.Button(self.ko_frame, text="⚡ GRUPPENPHASE BEENDEN & KO STARTEN ⚡", command=self.start_ko_phase_gui)
        self.btn_start_ko.pack(fill=tk.X, pady=10)
        
        # --- FIX: DAS SANDWICH-PRINZIP ---

        # 1. Ticker-Frame (Ganz unten ankleben)
        ticker_frame_ko = ttk.LabelFrame(self.ko_frame, text=" 📢 Regie-Nachricht an Beamer senden ", padding=5)
        ticker_frame_ko.pack(side=tk.BOTTOM, fill=tk.X, pady=(10, 0))
        
        combo_ko = ttk.Combobox(ticker_frame_ko, values=self.quick_messages, state="readonly", width=30)
        combo_ko.set("Vorlagen auswählen...")
        combo_ko.pack(side=tk.LEFT, padx=5)
        combo_ko.bind("<<ComboboxSelected>>", self.load_ticker_template)
        
        ttk.Entry(ticker_frame_ko, textvariable=self.ticker_var, font=("Arial", 11)).pack(side=tk.LEFT, expand=True, fill=tk.X, padx=5)
        ttk.Button(ticker_frame_ko, text="SENDEN", command=self.send_ticker_msg).pack(side=tk.LEFT, padx=2)
        ttk.Button(ticker_frame_ko, text="LÖSCHEN", command=self.clear_ticker_msg).pack(side=tk.LEFT, padx=2)

        # 2. Action-Frame (Über dem Ticker ankleben)
        ko_actions = ttk.Frame(self.ko_frame)
        ko_actions.pack(side=tk.BOTTOM, fill=tk.X)
        ttk.Button(ko_actions, text="⬇ VORZIEHEN (Blockiert)", state=tk.DISABLED).pack(side=tk.LEFT, expand=True, fill=tk.X, padx=2)
        ttk.Button(ko_actions, text="✎ EDITIEREN", command=lambda: self.edit_match_gui(True)).pack(side=tk.LEFT, expand=True, fill=tk.X, padx=2)
        ttk.Button(ko_actions, text="🔄 NEU STARTEN", command=lambda: self.reset_match_gui(True)).pack(side=tk.LEFT, expand=True, fill=tk.X, padx=2)

        # 3. Treeview (Füllt die Mitte)
        # 'phase' zu 'typ' oder 'runde' ändern, damit es sauber ist
        cols = ("nr", "status", "typ", "paarung", "punkte", "diff", "pi_id", "winner")
        self.tree_ko = ttk.Treeview(self.ko_frame, columns=cols, show="headings", height=10)
        # Und in der zip-Schleife darunter das Wort "Phase" durch "Runde" oder "Typ" ersetzen:
        for c, t, w in zip(cols, ["Nr.", "Status", "Typ", "Paarung", "Punkte", "Gesamt (Diff)", "Pi-ID", "Sieger"], [40, 80, 100, 200, 80, 140, 60, 120]):
            self.tree_ko.heading(c, text=t); self.tree_ko.column(c, width=w, anchor="center" if c != "paarung" else "w")
        self.tree_ko.pack(side=tk.TOP, fill=tk.BOTH, expand=True, pady=(10, 10))

    def load_ticker_template(self, event):
        combo = event.widget # Findet heraus, welches Dropdown benutzt wurde
        auswahl = combo.get()
        if auswahl and auswahl != "Vorlagen auswählen...":
            self.ticker_var.set(auswahl) # Schreibt den Text in das Eingabefeld
            combo.set("Vorlagen auswählen...") # Setzt das Dropdown auf den Platzhalter zurück

    def send_ticker_msg(self):
        msg = self.ticker_var.get().strip()
        if not self.beamer_window or not tk.Toplevel.winfo_exists(self.beamer_window):
            messagebox.showwarning("Fehler", "Der Beamer ist aktuell geschlossen!")
            return
            
        if msg:
            self.beamer_window.update_beamer_text(msg) # HIER KORRIGIERT
            
    def clear_ticker_msg(self):
        self.ticker_var.set("") # Löscht das Eingabefeld
        if self.beamer_window and tk.Toplevel.winfo_exists(self.beamer_window):
            self.beamer_window.update_beamer_text("") # HIER KORRIGIERT


#    def build_overview_tab(self):
#        self.tree_overview = ttk.Treeview(self.overview_frame, columns=("n","g","s","p","d","sc"), show="headings")
#        for c, h in zip(("n","g","s","p","d","sc"), ["Name","Grp","Sp","Pkt","Diff","Score"]):
#            self.tree_overview.heading(c, text=h); self.tree_overview.column(c, width=100, anchor="center")
#        self.tree_overview.pack(fill=tk.BOTH, expand=True)
#        
#        btn_box = ttk.Frame(self.overview_frame)
#        btn_box.pack(pady=10)
#        ttk.Button(btn_box, text="🔄 SPIELER UMBENENNEN", command=self.open_rename_dialog).pack(side=tk.LEFT, padx=10)

    def build_overview_tab(self):
        self.tree_overview = ttk.Treeview(self.overview_frame, columns=("n","g","s","p","d","sc"), show="headings")
        for c, h in zip(("n","g","s","p","d","sc"), ["Name","Grp","Sp","Pkt","Diff","Score"]):
            self.tree_overview.heading(c, text=h); self.tree_overview.column(c, width=100, anchor="center")
        self.tree_overview.pack(fill=tk.BOTH, expand=True)
        
        btn_box = ttk.Frame(self.overview_frame)
        btn_box.pack(pady=10)
        ttk.Button(btn_box, text="🔄 SPIELER UMBENENNEN", command=self.open_rename_dialog).pack(side=tk.LEFT, padx=10)
        
        # --- NEU: Der HTML Export Button ---
        ttk.Button(btn_box, text="🌐 HTML-BERICHT EXPORTIEREN", command=self.export_html_bericht).pack(side=tk.LEFT, padx=10)


    # --- LOGIK ---
    def turnier_starten(self):
        namen_text = self.name_input.get("1.0", tk.END).strip()
        namen = [n for n in namen_text.split("\n") if n.strip()] # Leere Zeilen ignorieren
        
        # 1. Die eingestellte Gruppengröße sicher auslesen
        try:
            gruppen_groesse = self.gruppen_groesse_var.get()
        except tk.TclError:
            gruppen_groesse = 4 # Fallback, falls das Feld leer gemacht wurde

        # 2. Dynamische Prüfung der Teilnehmerzahl anhand der neuen Variable
        if len(namen) < gruppen_groesse or len(namen) % gruppen_groesse != 0:
            messagebox.showerror(
                "Fehler", 
                f"Aktuell {len(namen)} Teilnehmer.\nDie Teilnehmerzahl muss ein Vielfaches der Gruppengröße ({gruppen_groesse}) sein!"
            )
            return
            
        with open("teilnehmer.txt", "w", encoding="utf-8") as f:
            f.write(namen_text)
            
        # 3. Den neuen Zufall-Schalter auslesen
        soll_zufall_sein = self.zufall_var.get()
            
        # 4. Den dynamischen Parameter an unsere TurnierLogik übergeben!
        gruppen, plan = generiere_spielplan(namen, gruppen_groesse, zufall=soll_zufall_sein)
        
        self.match_manager.setze_turnier_daten(gruppen, plan)
        self.update_all_displays()
        self.build_time_inputs()
        self.notebook.select(1)
        self.datei_manager.speichere_turnier_stand(self.match_manager.get_state())

    def start_ko_phase_gui(self):
        # 1. Smarte Warnung anhand der State-Machine
        if getattr(self.match_manager, "phase", None) == TurnierPhase.GRUPPENPHASE:
            msg = "⚠️ ACHTUNG: Die Gruppenphase ist noch NICHT beendet!\n\nMöchtest du die K.O.-Phase wirklich jetzt schon mit dem aktuellen Zwischenstand erzwingen?"
            # Zeigt ein echtes gelbes Warn-Icon an!
            if not messagebox.askyesno("K.O.-Phase erzwingen", msg, icon='warning'): 
                return
        else:
            if not messagebox.askyesno("KO Start", "Gruppenphase wirklich beenden?"): 
                return
        
        # 2. Die eigentliche Logik ausführen
        anzahl = len(self.match_manager.ergebnisse) 
        
        vf = berechne_ko_phase(self.match_manager.ergebnisse, self.match_manager.gruppen, anzahl)
        self.match_manager.starte_ko_phase(vf)
        self.update_all_displays()
        self.notebook.select(3)

    def ergebnis_abholen(self, event=None):
        if event and isinstance(event.widget, (tk.Entry, ttk.Entry, tk.Text, ttk.Combobox)): return
        
        daten = self.datei_manager.lese_highscore()
        if not daten: return
        d = daten[-1] # d steht für data (Macht den Code kürzer)

        # 1. Manager fragen, was Phase ist (Die pure Logik)
        szenario = self.match_manager.evaluiere_match_szenario(d.get("gesamtpunkte", 0), d.get("gesamtpunkte_pl2", 0))
        if szenario == "FEHLER": return

        # 2. Den Text für die Messagebox bauen (Die pure Optik)
        titel, msg = self._baue_ergebnis_text(szenario, d)

        # 3. User fragen & Manager die Aktion ausführen lassen
        if messagebox.askyesno(titel, msg):
            self._fuehre_ergebnis_aktion_aus(szenario, d)

    def _baue_ergebnis_text(self, szenario, d):
        b1, b2 = d.get("punkte_durchgang", 0), d.get("punkte_durchgang_pl2", 0)
        t1, t2 = d.get("gesamtpunkte", 0), d.get("gesamtpunkte_pl2", 0)
        s1, s2 = d.get("spieler", "Unbekannt"), d.get("spieler2", "Gegner") or "Gegner"
        pi_id = d.get("match_id", "-")
        
        match = self.match_manager.get_aktuelles_match()
        erw_s1, erw_s2 = match["spieler1"], match["spieler2"]
        is_ko = (getattr(self.match_manager, "phase", None) in [TurnierPhase.KO_PHASE, TurnierPhase.BEENDET])

        if szenario == "STECHEN_AKTIV":
            return "Stechen bestätigen", f"🔥 ERGEBNIS STECHEN 🔥\n\n{s1}: {b1} Treffer\n{s2}: {b2} Treffer\n\nErgebnis übernehmen und Sieger eintragen?"
            
        elif szenario == "GLEICHSTAND":
            return "Fotofinish!", f"🚨 GLEICHSTAND IM K.O.-MATCH! 🚨\nBeide Schützen haben exakt {t1:.2f} Punkte!\n\nSoll das Stechen jetzt gestartet werden?"
            
        else: # NORMAL
            msg = f"Ergebnis vom Pi (Match ID: {pi_id}):\n\n"
            if is_ko: msg += f"[{s1}]\n➔ Wertung: {t1:.3f}  (Treffer: {b1})\n\n[{s2}]\n➔ Wertung: {t2:.3f}  (Treffer: {b2})\n\n"
            else:     msg += f"[{s1}]\n➔ Treffer: {b1}  (Wertung: {t1:.3f})\n\n[{s2}]\n➔ Treffer: {b2}  (Wertung: {t2:.3f})\n\n"
                
            if s1 != erw_s1 or s2 != erw_s2:
                msg += f"⚠️ ACHTUNG: NAMENS-ABWEICHUNG! ⚠️\nErwartet: [{erw_s1}] vs [{erw_s2}]\n"
                msg += "Möchtest du dieses Ergebnis TROTZDEM eintragen?"
            else:
                msg += "Ergebnis in den Turnierplan übernehmen?"
            return "Bestätigen", msg            

    def _fuehre_ergebnis_aktion_aus(self, szenario, d):
        b1, b2 = d.get("punkte_durchgang", 0), d.get("punkte_durchgang_pl2", 0)
        t1, t2 = d.get("gesamtpunkte", 0), d.get("gesamtpunkte_pl2", 0)
        pi_id = d.get("match_id", "-")

        # 1. Den Manager die richtige Funktion ausführen lassen
        if szenario == "STECHEN_AKTIV":
            self.match_manager.trage_stechen_ein(b1, b2)
        elif szenario == "GLEICHSTAND":
            self.match_manager.aktiviere_stechen(b1, b2, t1, t2, pi_id)
            self.match_zu_pi() # Den Pi nochmal antriggern 
        else:
            self.match_manager.trage_ergebnis_ein(b1, b2, t1, t2, pi_id)

        # 2. Einmalig aufräumen und speichern für ALLE Szenarien (DRY-Prinzip!)
        self.update_all_displays()
        self.datei_manager.speichere_turnier_stand(self.match_manager.get_state())
        self.datei_manager.loesche_live_datei()
            
    def open_score_dialog(self, title, match, start_values, save_callback):
        """Allgemeine ELA-Schablone für alle Match-Eingabe-Popups."""
        d = tk.Toplevel(self.root)
        d.title(title)
        d.geometry("350x300")
        d.grab_set()
        
        s1, s2 = match['spieler1'], match['spieler2']
        ttk.Label(d, text=f"{s1} vs {s2}", font=("Arial", 12, "bold")).pack(pady=10)
        
        fields = [
            (f"Punkte {s1}", start_values[0]), 
            (f"Punkte {s2}", start_values[1]),
            (f"Diff-Score {s1}", start_values[2]), 
            (f"Diff-Score {s2}", start_values[3])
        ]
        
        entries = []
        for label, val in fields:
            f = ttk.Frame(d)
            f.pack(fill="x", padx=20, pady=5)
            ttk.Label(f, text=label, width=25).pack(side="left")
            e = ttk.Entry(f)
            e.insert(0, str(val))
            e.pack(side="left", expand=True, fill="x")
            entries.append(e)
            
        def on_save():
            try:
                # 1. Werte sicher auslesen
                b1, b2 = int(entries[0].get()), int(entries[1].get())
                t1, t2 = float(entries[2].get()), float(entries[3].get())
                
                # 2. Den übergebenen Callback (die eigentliche Logik) ausführen
                if save_callback(b1, b2, t1, t2):
                    d.destroy() # Fenster nur schließen, wenn Speichern erfolgreich war
            except ValueError:
                messagebox.showerror("Fehler", "Bitte gültige Zahlen eingeben (Punkte = ganzzahlig, Diff-Score = Komma mit Punkt).")

        ttk.Button(d, text="SPEICHERN & BERECHNEN", command=on_save).pack(pady=20)

    def match_ueberspringen(self):
        match = self.match_manager.get_aktuelles_match()
        if not match:
            messagebox.showinfo("Info", "Es gibt aktuell kein laufendes Match!")
            return
            
        # Die Logik, die beim Speichern ausgeführt werden soll (Der Callback)
        def save_action(b1, b2, t1, t2):
            self.match_manager.trage_ergebnis_ein(b1, b2, t1, t2, "MANUELL")
            self.update_all_displays()
            self.datei_manager.speichere_turnier_stand(self.match_manager.get_state())
            self.datei_manager.loesche_live_datei()
            return True # Signalisiert der Schablone, dass sie sich schließen darf

        # Schablone aufrufen (Startwerte sind alle 0)
        self.open_score_dialog("Match manuell werten / Überspringen", match, [0, 0, 0.0, 0.0], save_action)

    def edit_match_gui(self, is_ko=False):
        tree = self.tree_ko if is_ko else self.tree_matches
        plan = self.match_manager.ko_spielplan if is_ko else self.match_manager.spielplan
        
        sel = tree.selection()
        if not sel: 
            messagebox.showinfo("Info", "Bitte wähle zuerst ein Match in der Tabelle aus!")
            return
            
        idx = int(sel[0])
        m = plan[idx]
        
        if "?" in [m.get("spieler1"), m.get("spieler2")]:
            messagebox.showwarning("Achtung", "Dieses K.O.-Match hat noch keine festen Spieler. Erst die Vorrunden beenden!")
            return

        if not m.get("gespielt"):
            messagebox.showwarning("Achtung", "Dieses Match hat noch nicht stattgefunden!\n\nUm es manuell zu werten, bitte zuerst das Spiel in der Regie aufrufen (über 'VORZIEHEN') und dann den 'ÜBERSPRINGEN'-Button nutzen.")
            return
            
        # Die Logik, die beim Editieren ausgeführt werden soll (Der Callback)
        def save_action(b1, b2, t1, t2):
            if self.match_manager.edit_match(idx, b1, b2, t1, t2, is_ko):
                self.update_all_displays()
                self.datei_manager.speichere_turnier_stand(self.match_manager.get_state())
                return True
            return False

        # Schablone aufrufen (Startwerte sind die bereits gespeicherten Ergebnisse)
        start_vals = [m.get('base1', 0), m.get('base2', 0), m.get('total1', 0.0), m.get('total2', 0.0)]
        self.open_score_dialog("Match Editieren", m, start_vals, save_action)


    def reset_match_gui(self, is_ko=False):
        tree = self.tree_ko if is_ko else self.tree_matches
        plan = self.match_manager.ko_spielplan if is_ko else self.match_manager.spielplan
        sel = tree.selection()
        if not sel: return
        
        idx = int(sel[0])
        m = plan[idx]
        
        # Nur Matches, die bereits ein Ergebnis haben ("gespielt"), können neu gestartet werden
        if not m.get("gespielt"): return
        
        if messagebox.askyesno("Match Reset", f"Match {m['match_nr']} wirklich zurücksetzen und NEU STARTEN?"):
            # 1. Daten im Manager zurücksetzen (Punkte und "gespielt"-Flag löschen)
            self.match_manager.reset_match(idx, is_ko)
            
            # 2. DER CLOU: Wir sortieren nichts um! 
            # Wir setzen einfach den aktuellen Spiel-Index auf dieses Match.
            # Das funktioniert in BEIDEN Phasen (Gruppe & KO) perfekt.
            #self.match_manager.aktuelles_match_index = idx
            self.match_manager.setze_aktuelles_match(idx, is_ko)
            
            # 3. Sofort die Namen an den Pi / Beamer senden
            #self.match_zu_pi()
            
            # 4. GUI aktualisieren und Stand speichern
            self.update_all_displays()
            self.datei_manager.speichere_turnier_stand(self.match_manager.get_state())
            
            self.status_label.config(text=f"🔄 Match {m['match_nr']} wurde zurückgesetzt und neu gestartet.", foreground="blue")         

    def match_vorziehen_gui(self, is_ko=False):
        if is_ko: return # KO darf nicht vorgezogen werden
        selected = self.tree_matches.selection()
        if not selected: return
        if self.match_manager.match_vorziehen(int(selected[0])): 
            self.update_all_displays()
            #self.match_zu_pi() #Neue Spielernamen an Pi senden

    # --- UI UPDATES ---
    def update_control_ui(self):
        is_ko = (self.match_manager.phase in [TurnierPhase.KO_PHASE, TurnierPhase.BEENDET])
        match = self.match_manager.get_aktuelles_match()
        
        state = tk.DISABLED if (is_ko or not match) else tk.NORMAL
        self.btn_send_pi_grp.config(state=state)
        self.btn_get_pi_grp.config(state=state)
        
        if not is_ko and match: self.lbl_group_match.config(text=f"AKTUELL: Match {match['match_nr']} - {match['spieler1']} vs {match['spieler2']}")
        elif is_ko: self.lbl_group_match.config(text="--- Gruppenphase beendet (Archiv) ---")

        for item in self.tree_matches.get_children(): self.tree_matches.delete(item)
        for i, m in enumerate(self.match_manager.spielplan):
            
            # --- FIX: Das Häkchen wird jetzt an die echten Daten gekoppelt ---
            status = "✔" if m.get("gespielt") else ("🟢" if i == self.match_manager.aktuelles_match_index else "-")
            # ------------------------------------------------------------------
            
            if m.get("gespielt"):
                p_txt, d_txt, id_txt = f"{m.get('base1', 0)} : {m.get('base2', 0)}", f"{m.get('total1', 0):.3f} : {m.get('total2', 0):.3f}", str(m.get("pi_match_id", "-"))
            else: p_txt, d_txt, id_txt = "- : -", "- : -", "-"
            self.tree_matches.insert("", tk.END, iid=str(i), values=(m['match_nr'], status, m['gruppe'], f"{m['spieler1']} vs {m['spieler2']}", p_txt, d_txt, id_txt))
    
    def update_ko_ui(self):
        # 1. Nur noch die reine State-Machine abfragen! Kein Rechnen mehr!
        phase = self.match_manager.phase
        match = self.match_manager.get_aktuelles_match()
        
        # 2. Button- & Label-Logik anhand des Enums
        if phase in [TurnierPhase.KO_PHASE, TurnierPhase.BEENDET]:
            self.btn_start_ko.config(state=tk.DISABLED)
            
            # Wir bauen die Buttons einmalig auf, sobald die K.O.-Phase läuft
            if not self.ko_pi_frame.winfo_children():
                ttk.Button(self.ko_pi_frame, text="KO-MATCH -> PI SENDEN", command=self.match_zu_pi).pack(side=tk.LEFT, expand=True, fill=tk.X, padx=5)
                ttk.Button(self.ko_pi_frame, text="ÜBERSPRINGEN / MANUELL", command=self.match_ueberspringen).pack(side=tk.LEFT, expand=True, fill=tk.X, padx=5)
                ttk.Button(self.ko_pi_frame, text="KO-ERGEBNIS ABHOLEN", command=self.ergebnis_abholen).pack(side=tk.LEFT, expand=True, fill=tk.X, padx=5)
                
            if phase == TurnierPhase.BEENDET: 
                self.lbl_ko_match.config(text="🏆 TURNIER BEENDET 🏆")
            else: 
                match_name_text = self.datei_manager.get_match_name(match['match_nr'])
                self.lbl_ko_match.config(text=f"KO-MATCH: {match_name_text} - {match['spieler1']} vs {match['spieler2']}" if match else "WAAAANNNNNN????_Warte auf K.O.-Match...")
                
        elif phase == TurnierPhase.GRUPPEN_ABGESCHLOSSEN:
            # Gruppenphase ist fertig!
            self.btn_start_ko.config(state=tk.NORMAL)
            self.lbl_ko_match.config(text="✅ GRUPPENPHASE BEENDET! Klick zum Start der K.O.-Runde.")
            
        else: # NICHT_GESTARTET oder GRUPPENPHASE
            # ELA-Notausgang: Button in der Gruppenphase aktivieren, aber Text anpassen
            if phase == TurnierPhase.GRUPPENPHASE:
                self.btn_start_ko.config(state=tk.NORMAL)
                self.lbl_ko_match.config(text="⏳ Gruppenphase läuft (K.O.-Start kann erzwungen werden)...")
            else:
                self.btn_start_ko.config(state=tk.DISABLED)
                self.lbl_ko_match.config(text="⏳ Warte auf Turnierstart...")

        # 4. Tabelle leeren
        for item in self.tree_ko.get_children(): 
            self.tree_ko.delete(item)
        
        # 5. Tabelle neu befüllen
        is_ko = (phase in [TurnierPhase.KO_PHASE, TurnierPhase.BEENDET])
        akt_nr = match["match_nr"] if (is_ko and match) else ""
        
        for i, m in enumerate(self.match_manager.ko_spielplan):
            is_active = (str(m["match_nr"]) == str(akt_nr))
            status = "✔" if m.get("gespielt") else ("🟢" if is_active else "-")
            
            if m.get("gespielt"):
                p_txt = f"{m.get('base1', 0)} : {m.get('base2', 0)}"
                d_txt = f"{m.get('total1', 0):.3f} : {m.get('total2', 0):.3f}"
                id_txt = str(m.get("pi_match_id", "-"))
            else:
                p_txt, d_txt, id_txt = "- : -", "- : -", "-"
            
            self.tree_ko.insert("", tk.END, iid=str(i), values=(
                m['match_nr'], 
                status, 
                self.datei_manager.get_match_name(m['match_nr']), # <--- HIER ÜBERSETZEN WIR LIVE!
                f"{m['spieler1']} vs {m['spieler2']}", 
                p_txt, d_txt, id_txt, m.get("winner", "-")
            ))

    def update_overview_ui(self):
        for item in self.tree_overview.get_children(): self.tree_overview.delete(item)
        stats = sorted([{"n":k, **v} for k,v in self.match_manager.ergebnisse.items()], key=lambda x: (x["gruppe"], x["punkte"], x["differenz"]), reverse=True)
        for s in stats: self.tree_overview.insert("", tk.END, values=(s["n"], s["gruppe"], s["spiele"], s["punkte"], f"{s['differenz']:+.2f}", f"{s['score_erzielt']:.2f}"))

    # --- Helfer ---
    def update_all_displays(self):
        self.update_control_ui()
        self.update_ko_ui()
        self.update_overview_ui()
        if self.beamer_window and tk.Toplevel.winfo_exists(self.beamer_window): self.beamer_window.refresh_display()

    def match_zu_pi(self):
        match = self.match_manager.get_aktuelles_match()
        if match and self.datei_manager.schreibe_next_match(match['spieler1'], match['spieler2']):
            self.status_label.config(text=f"✅ Daten für {match['spieler1']} vs {match['spieler2']} gesendet!", foreground="green")
            # Nach 5 Sekunden wieder auf Standard setzen
            self.root.after(5000, lambda: self.status_label.config(text="Bereit", foreground="black"))

    def open_rename_dialog(self):
        sel = self.tree_overview.selection()
        if not sel: return
        old_name = self.tree_overview.item(sel[0])['values'][0]
        d = tk.Toplevel(self.root); d.title("Umbenennen"); d.geometry("300x150"); d.grab_set()
        ttk.Label(d, text=f"Neuer Name für '{old_name}':").pack(pady=10)
        ent = ttk.Entry(d, width=20); ent.insert(0, old_name); ent.pack(pady=5)
        def save():
            new_name = ent.get().strip()
            if new_name and self.match_manager.rename_player(old_name, new_name):
                self.update_all_displays(); self.datei_manager.speichere_turnier_stand(self.match_manager.get_state()); d.destroy()
        ttk.Button(d, text="UMBENNEN", command=save).pack(pady=15)

    def build_time_inputs(self):
        for widget in self.time_frame.winfo_children(): widget.destroy()
        for g in sorted(self.match_manager.gruppen.keys()):
            f = ttk.Frame(self.time_frame)
            f.pack(side=tk.LEFT, padx=5)
            ttk.Label(f, text=f"Grp {g}:").pack(side=tk.LEFT)
            
            # ELA: Breite von 7 auf 20 erhöht und Standardwert auf "" gesetzt
            ent = ttk.Entry(f, width=20)
            ent.insert(0, self.match_manager.gruppen_zeiten.get(g, ""))
            ent.pack(side=tk.LEFT)
            
            self.time_entries[g] = ent
        ttk.Button(self.time_frame, text="Sichern", command=self.save_times).pack(side=tk.RIGHT)

    def save_times(self):
        for g, ent in self.time_entries.items(): self.match_manager.gruppen_zeiten[g] = ent.get()
        self.update_all_displays()

    def export_html_bericht(self):
        mit_gruppenuebersicht = messagebox.askyesno(
            "Gruppenübersicht", 
            "Gruppenübersichten angezeigen?"
        )

        # --- NEU: Abfrage für die Gruppenmatches ---
        mit_gruppenmatches = messagebox.askyesno(
            "Gruppenspiele", 
            "Spielplan Gruppenphase anzeigen?"
        )

        mit_sonderwertungen = messagebox.askyesno(
            "Sonderwertungen", 
            "Sonderwertungen anzeigen ('Pechvogel' und Top-5 Gesamt-Score)?"
        )
        
        # --- NEU: Wir übergeben jetzt auch den 'spielplan' und die neue Entscheidung ---
        erfolg, nachricht = self.html_exporter.generiere_bericht(
            ergebnisse=self.match_manager.ergebnisse, 
            spielplan=self.match_manager.spielplan,
            ko_spielplan=self.match_manager.ko_spielplan, 
            mit_gruppenuebersicht=mit_gruppenuebersicht,
            mit_sonderwertungen=mit_sonderwertungen,
            mit_gruppenmatches=mit_gruppenmatches,
            datei_manager=self.datei_manager # <--- HIER DEN ÜBERSETZER MITGEBEN
        )
        
        if erfolg:
            pass
            #messagebox.showinfo("Erfolg", nachricht)
        else:
            messagebox.showwarning("Achtung", nachricht)


 
    def open_beamer(self):
        if not hasattr(self, 'beamer_window') or not self.beamer_window or not tk.Toplevel.winfo_exists(self.beamer_window):
            
            # ARCHITEKTUR-FIX: Wir übergeben die OBJEKTE selbst, NICHT deren statischen Wert!
            self.beamer_window = PublicDisplay(
                self.root, 
                self.match_manager, 
                self.set_pause_title,
                matches_per_page_var=self.var_matches_per_page,
                groups_per_page_var=self.var_groups_per_page,
                # FIX: Wir übergeben direkt den schlauen Manager statt nur des nackten Dictionaries!
                datei_manager=self.datei_manager 
            )
            
            # 1. Vollbild erzwingen AUS!
            self.beamer_window.attributes('-fullscreen', False)
            
            # 2. Beamer-Fenster in einer guten HD-Ready Größe als normales Fenster öffnen
            self.beamer_window.geometry('1280x720+50+50') 
            
            # 3. Zusätzliches Key-Binding
            self.beamer_window.bind("<Control_L>", self.ergebnis_abholen)
            
        else: 
            self.beamer_window.lift()


#AB HIER LIVE POLLING
        
    def start_live_polling(self):
        self.last_mtime = 0
        # Flag, um sich zu merken, ob das Match im "SICHERHEIT"-Modus ist
        self.live_match_finished = False 
        self.check_live_data()

    def check_live_data(self):
        live_file = self.datei_manager.live_ticker_path
        
        # 1. GIBT ES DIE DATEI ÜBERHAUPT?
        if not os.path.exists(live_file):
            # Keine Datei = Match ist abgerechnet oder noch keines gestartet
            if self.beamer_window and tk.Toplevel.winfo_exists(self.beamer_window):
                self.beamer_window.update_live_score(0, 0, "WARTEN")
            self.last_mtime = 0
        else:
            # 2. DATEI IST DA -> MATCH LÄUFT!
            current_mtime = os.path.getmtime(live_file)
            
            if current_mtime > self.last_mtime:
                try:
                    with open(live_file, "r") as f:
                        data = json.load(f)
                    
                    # Falls du später mal {"metadata": ..., "timeline": [...]} nutzt:
                    timeline = data.get("timeline", []) if isinstance(data, dict) else data
                    
                    # --- NEU: ELA-Variablen für getrennte Werte ---
                    p1_treffer, p2_treffer = 0, 0
                    p1_speed, p2_speed = 0.0, 0.0
                    current_status = ""
                    
                    ruhephasen = ["LADEN", "ACHTUNG", "SICHERHEIT", "RESET", "VORBEREITEN"]
                    
                    # Wir spulen das Match chronologisch ab
                    for ev in timeline:
                        current_status = ev.get("m", "")
                        a = ev.get("a", "")
                        
                        # DIE ENTSCHEIDENDE LOGIK:
                        if a == "shoot" and current_status not in ruhephasen:
                            # Im aktiven Match: Basis + aktueller Zyklus addieren
                            p1_treffer = ev.get("p1_pd", 0) + ev.get("p1_pz", 0)
                            p2_treffer = ev.get("p2_pd", 0) + ev.get("p2_pz", 0)
                            p1_speed   = ev.get("p1_spd", 0.0) + ev.get("p1_spz", 0.0)
                            p2_speed   = ev.get("p2_spd", 0.0) + ev.get("p2_spz", 0.0)
                        elif current_status in ruhephasen:
                            # In Pausen/Sicherheit: Nur Basis-Werte nutzen (Zyklus ist 0 oder schon verbucht)
                            p1_treffer = ev.get("p1_pd", 0)
                            p2_treffer = ev.get("p2_pd", 0)
                            p1_speed   = ev.get("p1_spd", 0.0)
                            p2_speed   = ev.get("p2_spd", 0.0)

                    is_ko = getattr(self.match_manager, "phase", None) in [TurnierPhase.KO_PHASE, TurnierPhase.BEENDET]
                    if is_ko and not self.match_manager.get_aktuelles_match().get("stechen_notwendig"):
                        # K.O.-Phase (Normal): Speedpunkte addieren & auf 2 Nachkommastellen runden
                        p1_score = f"{(p1_treffer + p1_speed):.2f}"
                        p2_score = f"{(p2_treffer + p2_speed):.2f}"
                    else:
                        # Gruppenphase ODER Stechen: Nur reine Treffer anzeigen
                        p1_score = str(p1_treffer)
                        p2_score = str(p2_treffer)
                            
                    # Finalen Stand an den Beamer senden
                    if self.beamer_window and tk.Toplevel.winfo_exists(self.beamer_window):
                        self.beamer_window.update_live_score(p1_score, p2_score, current_status)
                        
                    self.last_mtime = current_mtime
                    
                except Exception as e:
                    pass # Lese-Kollision ignorieren

        # 3. ENDLOSSCHLEIFE AUFRECHTERHALTEN
        # Wichtig: Dies muss GANZ am Ende stehen, auf der gleichen Einrückungsebene 
        # wie das `if not os.path.exists...`, damit das Polling niemals stehen bleibt!
        self.root.after(500, self.check_live_data)
        #except Exception as e:
        #    # Hier geben wir den exakten Fehlertyp und die Nachricht aus
        #    print(f"❌ KRITISCHER FEHLER im Live-Ticker:")
        #    print(f"   Fehlermeldung: {str(e)}")
        #    print(f"   Versuchter Pfad: {self.datei_manager.live_ticker_path}")
        #    #pass
        
        
#sudo nano /etc/samba/smb.conf  
#Diesen Block ganz unten am Ende der Datei einfügen:
#[Live]
#   path = /dev/shm/shooting_live
#   browseable = yes
#   read only = no
#   guest ok = yes
#   force user = pi
#   create mask = 0666
#   directory mask = 0777      
#
#sudo systemctl restart smbd            

