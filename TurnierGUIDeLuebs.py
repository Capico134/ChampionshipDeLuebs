import tkinter as tk
from tkinter import ttk, messagebox
import os
from PublicDisplayDeLuebs import PublicDisplay
from HtmlDeLuebs import HtmlExporter
from TurnierLogikDeLuebs import generiere_spielplan, berechne_ko_phase
from MatchManagerDeLuebs import TurnierPhase
import json #Für Live-Ticker
import ctypes
import datetime # <--- WICHTIG: Import für die Zeit
import tkinter.font as tkFont
import random # Für Derby-Zufall

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
        
        # =====================================================================
        # 🚀 GLOBALER SCHRIFTGRÖSSEN-BOOSTER (Perfekt für Laptops)
        # =====================================================================
       
        # 1b. Klassische Tkinter-Standardschriften vergrößern (Standard ist oft 9 oder 10)
        groesse_hauptschrift = 14  # <-- Hier kannst du die globale Größe anpassen!
        self.root.option_add("*Text.font", ("Segoe UI", groesse_hauptschrift))
        self.root.option_add("*Entry.font", ("Segoe UI", groesse_hauptschrift))
        self.root.option_add("*Listbox.font", ("Segoe UI", groesse_hauptschrift))
        
        for font_name in ["TkDefaultFont", "TkTextFont", "TkMenuFont"]:
            try:
                tkFont.nametofont(font_name).configure(size=groesse_hauptschrift)
            except Exception:
                pass
        try:
            tkFont.nametofont("TkHeadingFont").configure(size=groesse_hauptschrift + 1, weight="bold")
        except Exception:
            pass
                
        # 2. Modernen TTK-Style konfigurieren (für ttk.Label, ttk.Button, ttk.Treeview)
        self.style = ttk.Style()
        self.style.configure(".", font=("Segoe UI", groesse_hauptschrift))
        
        # 3. SPEZIAL-TUNING FÜR DIE TABELLEN (Treeview)
        # Wenn Schriften größer werden, müssen die Zeilen mehr Platz nach oben/unten haben!
        self.style.configure("Treeview.Heading", font=("Segoe UI", groesse_hauptschrift, "bold"))
        self.style.configure("Treeview", font=("Segoe UI", groesse_hauptschrift - 1), rowheight=25) # rowheight=32 gibt ordentlich Luft!
        # =====================================================================
        
        self.datei_manager = datei_manager
        self.match_manager = match_manager
        # --- NEU: ELA - Einmal das Radio abonnieren ---
        self.match_manager.bind_match_changed(self.match_zu_pi)
                
        self.version = version
        self.time_entries = {}
        self.html_exporter = HtmlExporter()
        
        
        self.beamer_window = None
        self.auto_beamer = auto_beamer 
        
        # --- ELA-CLEANUP: Alle Status- und Live-Variablen zentral deklarieren ---
        self.last_raw_data = ""           # Ersetzt das alte self.last_mtime
        #self.live_match_finished = False  
        # NEU: Unsere beiden neuen Status-Schalter für das flackerfreie Live-Polling!
        self.match_is_live = False
        self.zeige_ergebnis_screen = False     
        self.debug_live_polling = False         # FÜR DEBUGGING!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
        
        # --- Tkinter Kontroll-Variablen (Kein "Erfinden" mehr in den Sub-Routinen!) ---
        self.var_matches_per_page = tk.IntVar(value=20)
        self.var_groups_per_page = tk.IntVar(value=3)
        self.gruppen_groesse_var = tk.IntVar(value=4)
        self.zufall_var = tk.BooleanVar(value=True)
        self.derby_var = tk.BooleanVar(value=False)
        self.ticker_var = tk.StringVar() 
        # -------------------------------------------------------------------------

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
        # ==========================================================
        # 1. FUSSLIESTE ZUERST EINPACKEN!
        # (Damit sie ihren Platz fest reserviert und niemals verschwindet)
        # ==========================================================
        bottom_bar = ttk.Frame(self.root)
        bottom_bar.pack(side=tk.BOTTOM, fill=tk.X, padx=10, pady=6)

        # 1a. Status ganz links ankleben
        self.status_label = ttk.Label(bottom_bar, text="Bereit", font=("Arial", 10))
        self.status_label.pack(side=tk.LEFT)

        # 1b. Container für Beamer-Controls ganz rechts ankleben
        beamer_controls = ttk.Frame(bottom_bar)
        beamer_controls.pack(side=tk.RIGHT)

        self.btn_beamer = ttk.Button(beamer_controls, text="📺 BEAMER-ANZEIGE ÖFFNEN", command=self.open_beamer)
        self.btn_beamer.pack(side=tk.LEFT, padx=(0, 20))

        ttk.Label(beamer_controls, text="Matches pro Seite:").pack(side=tk.LEFT, padx=(0, 5))
        ttk.Spinbox(beamer_controls, from_=5, to=50, width=4, textvariable=self.var_matches_per_page).pack(side=tk.LEFT, padx=(0, 15))

        ttk.Label(beamer_controls, text="Gruppen pro Seite:").pack(side=tk.LEFT, padx=(0, 5))
        ttk.Spinbox(beamer_controls, from_=1, to=10, width=4, textvariable=self.var_groups_per_page).pack(side=tk.LEFT)    

        # ==========================================================
        # 2. DANN ERST DAS NOTEBOOK ERSTELLEN UND EINPACKEN
        # (Es füllt jetzt brav nur noch den verbleibenden Platz aus)
        # ==========================================================
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

    def build_setup_tab(self):
        # --- NEU: ELA-LÖSUNG (Alle Hauptaktionen immer oben griffbereit) ---
        action_frame = ttk.LabelFrame(self.setup_frame, text=" 🚀 Turnier-Steuerung ", padding=10)
        action_frame.pack(fill=tk.X, pady=(0, 15))

        # 1. Neues Turnier ganz links (als primäre Aktion)
        ttk.Button(action_frame, text="⚔️ NEUES TURNIER STARTEN", 
                   command=self.turnier_starten).pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)

        # 2. Letzten Stand laden
        neueste_datei = self.datei_manager.finde_neuesten_pfad()
        if neueste_datei:
            dateiname = os.path.basename(neueste_datei)
            ttk.Button(action_frame, text=f"▶ LETZTEN STAND FORTSETZEN ({dateiname})", 
                       command=lambda: self.load_specific_state(neueste_datei)).pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)

        # 3. Anderen Stand laden
        ttk.Button(action_frame, text="📂 ANDEREN STAND LADEN...", 
                   command=self.load_manual_state).pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        # ---------------------------------------------------------------------

        # 1. Gruppengröße
        rahmen_top = ttk.Frame(self.setup_frame)
        rahmen_top.pack(fill=tk.X, pady=(0, 10))

        ttk.Label(rahmen_top, text="Gruppengröße:", font=("Arial", 12)).pack(side=tk.LEFT, padx=(0, 10))
        #self.gruppen_groesse_var = tk.IntVar(value=4) 
        ttk.Spinbox(rahmen_top, from_=2, to=8, textvariable=self.gruppen_groesse_var, width=5, font=("Arial", 12)).pack(side=tk.LEFT)

        # --- NEU: Der Checkbutton für Zufallsgruppen ---
        #self.zufall_var = tk.BooleanVar(value=True) # Standardmäßig an
        ttk.Checkbutton(
            rahmen_top, 
            text="Spieler zufällig auf Gruppen verteilen", 
            variable=self.zufall_var
        ).pack(side=tk.LEFT, padx=(30, 0))

        # --- NEU: Derby Checkbox ---
        ttk.Checkbutton(
            rahmen_top, 
            text="Derby-Modus (Freies Spiel)", 
            variable=self.derby_var
        ).pack(side=tk.LEFT, padx=(30, 0))

        # 2. Das Label für das Textfeld anpassen
        ttk.Label(self.setup_frame, text="Neues Turnier: Teilnehmer (Ein Name pro Zeile):", font=("Arial", 12)).pack(anchor=tk.W)
        
        # Durch fill=tk.BOTH und expand=True nimmt sich das Textfeld den restlichen Platz.
        # Es scrollt intern, wenn es viele Namen sind, aber schiebt die UI nicht mehr kaputt!
        self.name_input = tk.Text(self.setup_frame, height=15, width=40)
        self.name_input.pack(fill=tk.BOTH, expand=True, pady=10)
        
        if os.path.exists("teilnehmer.txt"):
            with open("teilnehmer.txt", "r", encoding="utf-8") as f:
                self.name_input.insert(tk.END, f.read())
        else:
            self.name_input.insert(tk.END, "Petra\nSarah\nTom\nBernd\nBen\nLisa\nMax\nHannes\nAnna\nJulia\nMichaela\nChris")
            
        # Der alte Start-Button ganz unten wurde entfernt!
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
        # --- NEU: "programm" als Spalte hinzugefügt ---
        columns = ("nr", "status", "gruppe", "paarung", "punkte", "diff", "pi_id", "programm")
        self.tree_matches = ttk.Treeview(self.control_frame, columns=columns, show="headings", height=6)
        
        # --- NEU: "Programm" in den Headern und Breite "150" hinzugefügt ---
        for col, txt, w in zip(columns, ["Nr.", "Status", "Gruppe", "Paarung", "Punkte", "Gesamt (Diff)", "Pi-ID", "Programm"], [40, 80, 60, 200, 80, 140, 60, 150]):
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
        # --- NEU: "programm" als Spalte vor den "winner" gepackt ---
        cols = ("nr", "status", "typ", "paarung", "punkte", "diff", "pi_id", "programm", "winner")
        self.tree_ko = ttk.Treeview(self.ko_frame, columns=cols, show="headings", height=6)
        
        # --- NEU: "Programm" in den Headern und Breite "150" hinzugefügt ---
        for c, t, w in zip(cols, ["Nr.", "Status", "Typ", "Paarung", "Punkte", "Gesamt (Diff)", "Pi-ID", "Programm", "Sieger"], [40, 80, 100, 200, 80, 140, 60, 150, 120]):
            self.tree_ko.heading(c, text=t)
            self.tree_ko.column(c, width=w, anchor="center" if c != "paarung" else "w")
            
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
    # --- LOGIK ---
    def turnier_starten(self):
        namen_text = self.name_input.get("1.0", tk.END).strip()
        namen = [n for n in namen_text.split("\n") if n.strip()]
        
        try:
            gruppen_groesse = self.gruppen_groesse_var.get()
        except tk.TclError:
            gruppen_groesse = 4 

        # --- NEU: Derby prüfen ---
        soll_derby_sein = self.derby_var.get()
        soll_zufall_sein = self.zufall_var.get() # <--- ELA: Zustand der Zufalls-Checkbox holen
        
        self.match_manager.derby_modus = soll_derby_sein
        
        if soll_derby_sein:
            # Im Derby ignorieren wir Teilnehmer-Regeln und bauen einen leeren Plan!
            
            # --- NEU: Zufallsmix auch im Derby! ---
            if soll_zufall_sein:
                import random
                random.shuffle(namen)
                
            gruppen = {"Derby": namen}
            plan = []
        else:
            if len(namen) < gruppen_groesse or len(namen) % gruppen_groesse != 0:
                messagebox.showerror("Fehler", f"Aktuell {len(namen)} Teilnehmer.\nDie Teilnehmerzahl muss ein Vielfaches der Gruppengröße ({gruppen_groesse}) sein!")
                return
                
            try:
                gruppen, plan = generiere_spielplan(namen, gruppen_groesse, zufall=soll_zufall_sein)
            except ValueError as e:
                messagebox.showerror("Namen-Fehler", str(e))
                return
            
        with open("teilnehmer.txt", "w", encoding="utf-8") as f:
            f.write(namen_text)
            
        self.match_manager.setze_turnier_daten(gruppen, plan)
        self.build_time_inputs()
        self.notebook.select(1)
        self._abschluss_routine()
        
        
    def start_ko_phase_gui(self):
        # 1. Smarte Warnung anhand der State-Machine
        if getattr(self.match_manager, "phase", None) == TurnierPhase.GRUPPENPHASE:
            msg = "⚠️ ACHTUNG: Die Gruppenphase ist noch NICHT beendet!\n\nMöchtest du die K.O.-Phase wirklich jetzt schon mit dem aktuellen Zwischenstand erzwingen?"
            if not messagebox.askyesno("K.O.-Phase erzwingen", msg, icon='warning'): 
                return
        else:
            if not messagebox.askyesno("KO Start", "Gruppenphase wirklich beenden?"): 
                return
        
        # 2. Die eigentliche Logik ausführen -> Nur noch ein Befehl!
        self.match_manager.starte_ko_phase()
        
        # 3. Zentrale Abschlussarbeiten (GUI Update, Speichern & HTML-Druck)
        self._abschluss_routine()
        
        # 4. Zum K.O.-Tab wechseln
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
        
        # --- FIX: NAMENS-CHECK FÜR BEIDE MODI (Turnier & Derby) ---
        if self.match_manager.derby_modus and self.match_manager.phase == TurnierPhase.GRUPPENPHASE:
            # Im Derby schauen wir ins Wartezimmer, falls Namen gesendet wurden!
            erw_s1 = getattr(self.match_manager, 'derby_pending_p1', None) or s1 
            erw_s2 = getattr(self.match_manager, 'derby_pending_p2', None) or s2
        else:
            # Im Turnier schauen wir auf den festen Spielplan
            match = self.match_manager.get_aktuelles_match()
            if match:
                erw_s1, erw_s2 = match["spieler1"], match["spieler2"]
            else:
                erw_s1, erw_s2 = ("Unbekannt", "Unbekannt")
            
        is_ko = (getattr(self.match_manager, "phase", None) in [TurnierPhase.KO_PHASE, TurnierPhase.BEENDET])

        # --- 1. GRUNDTEXT BAUEN (Je nach Szenario) ---
        if szenario == "STECHEN_AKTIV":
            titel = "Stechen bestätigen"
            msg = f"🔥 ERGEBNIS STECHEN 🔥\n\n{s1}: {b1} Treffer\n{s2}: {b2} Treffer\n\nErgebnis übernehmen und Sieger eintragen?"
            
        elif szenario == "GLEICHSTAND":
            titel = "Fotofinish!"
            msg = f"🚨 GLEICHSTAND IM K.O.-MATCH! 🚨\nBeide Schützen haben exakt {t1:.2f} Punkte!\n\nSoll das Stechen jetzt gestartet werden?"
            
        else: # NORMAL
            titel = "Bestätigen"
            msg = f"Ergebnis vom Pi (Match ID: {pi_id}):\n\n"
            if is_ko: msg += f"[{s1}]\n➔ Wertung: {t1:.3f}  (Treffer: {b1})\n\n[{s2}]\n➔ Wertung: {t2:.3f}  (Treffer: {b2})\n\n"
            else:     msg += f"[{s1}]\n➔ Treffer: {b1}  (Wertung: {t1:.3f})\n\n[{s2}]\n➔ Treffer: {b2}  (Wertung: {t2:.3f})\n\n"
            msg += "Ergebnis in den Turnierplan übernehmen?"

        # --- 2. WARNUNGEN PRÜFEN UND OBEN ANHÄNGEN ---
        warnungen = ""

        # Check A: Namens-Abweichung (Greift jetzt auch im Derby, wenn das Wartezimmer gefüllt war!)
        if s1 != erw_s1 or s2 != erw_s2:
            warnungen += f"⚠️ ACHTUNG: NAMENS-ABWEICHUNG! ⚠️\nErwartet: [{erw_s1}] vs [{erw_s2}]\n\n"

        # Check B: Zeit-Abweichung (Älter als 2 Minuten oder in der Zukunft)
        timestamp_str = d.get("timestamp", "")
        if timestamp_str:
            try:
                import datetime # Fallback, falls nicht global importiert
                match_zeit = datetime.datetime.strptime(timestamp_str, "%d.%m.%y %H:%M:%S")
                differenz_sekunden = (datetime.datetime.now() - match_zeit).total_seconds()
                
                if differenz_sekunden > 120 or differenz_sekunden < -120:
                    warnungen += f"⏱️ ACHTUNG: ZEIT-FEHLER! ⏱️\nDieses Match ist vom {timestamp_str}!\nEntweder ein altes Match, oder die Pi-Uhr geht falsch!\n\n"
            except ValueError:
                pass # Falls das Datum mal kaputt formatiert ist, Programm nicht crashen

        # Wenn es eine oder beide Warnungen gab, bauen wir sie prominent ein!
        if warnungen:
            msg = f"{warnungen}----------------------------------------\n\n{msg}"
            titel = "⚠️ WARNUNG: " + titel
            
        return titel, msg   

    def _fuehre_ergebnis_aktion_aus(self, szenario, d):
        b1, b2 = d.get("punkte_durchgang", 0), d.get("punkte_durchgang_pl2", 0)
        t1, t2 = d.get("gesamtpunkte", 0), d.get("gesamtpunkte_pl2", 0)
        pi_id = d.get("match_id", "-")
        prog_name = d.get("programm_name", "Unbekanntes Programm")
        start_z = d.get("start_zeit", "--:--") 
        timestamp_z = d.get("timestamp", "--:--")
        
        # --- NEU: Spieler auslesen für das dynamische Derby-Match ---
        s_1 = d.get("spieler", "Unbekannt")
        s_2 = d.get("spieler2", "Gegner") or "Gegner"

        if szenario == "STECHEN_AKTIV":
            self.match_manager.trage_stechen_ein(b1, b2)
        elif szenario == "GLEICHSTAND":
            self.match_manager.aktiviere_stechen(b1, b2, t1, t2, pi_id)
            self.match_zu_pi() 
        else:
            self.match_manager.trage_ergebnis_ein(
                b1, b2, t1, t2, pi_id, 
                programm_name=prog_name, 
                start_zeit=start_z, 
                timestamp=timestamp_z,
                s1=s_1, s2=s_2 # <--- NEU: Die Spielernamen mit übergeben!
            )
        self.zeige_ergebnis_screen = False
        self._abschluss_routine()

    def _abschluss_routine(self):
        """Erledigt alle Speicher- und Update-Aufgaben nach jedem veränderten Match zentral."""
        self.update_all_displays()
        
        # --- FIX: Wir holen uns den State und speichern ihn in der Variable 'turnier_state' ---
        turnier_state = self.match_manager.get_state()
        
        # Jetzt übergeben wir einfach die Variable zum Speichern...
        self.datei_manager.speichere_turnier_stand(turnier_state)
        self.datei_manager.loesche_live_datei()
        
        # ...und können die Variable unten bei _meta problemlos auslesen!
        self.html_exporter.generiere_bericht(
            ergebnisse=self.match_manager.ergebnisse, 
            spielplan=self.match_manager.spielplan,
            ko_spielplan=self.match_manager.ko_spielplan,
            datei_manager=self.datei_manager,
            meta_daten=turnier_state.get("_meta", {}), 
            silent=True 
        )   
            
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
            self._abschluss_routine()
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
                # --- ELA: Nur noch der zentrale Aufruf für UI, Speichern und HTML! ---
                self._abschluss_routine() 
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
            # 1. Daten und Phase im Manager zurücksetzen
            self.match_manager.reset_match(idx, is_ko)
            
            # 2. DER CLOU: Wir sortieren nichts um! 
            # Wir setzen einfach den aktuellen Spiel-Index auf dieses Match.
            self.match_manager.setze_aktuelles_match(idx, is_ko)
            
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
        
        # --- FIX: Senden & Abholen sauber trennen! ---
        if self.match_manager.derby_modus and not is_ko:
            # Im Derby: Senden immer erlaubt (öffnet Popup), Skip deaktiviert
            self.btn_send_pi_grp.config(state=tk.NORMAL)
            self.btn_skip_grp.config(state=tk.DISABLED)
        else:
            # Normales Turnier: Nur erlaubt, wenn es ein nächstes Match gibt
            self.btn_send_pi_grp.config(state=tk.DISABLED if (is_ko or not match) else tk.NORMAL)
            self.btn_skip_grp.config(state=tk.DISABLED if (is_ko or not match) else tk.NORMAL)
        
        # Abholen ist in der gesamten Gruppenphase (auch im Derby!) IMMER erlaubt!
        self.btn_get_pi_grp.config(state=tk.DISABLED if is_ko else tk.NORMAL)
        
        # --------------------------------------------
        
        if not is_ko and match: 
            self.lbl_group_match.config(text=f"AKTUELL: Match {match['match_nr']} - {match['spieler1']} vs {match['spieler2']}")
        elif self.match_manager.derby_modus and not is_ko:
            self.lbl_group_match.config(text="--- Derby-Modus aktiv: Warte auf Ergebnisse vom Pi ---")
        elif is_ko: 
            self.lbl_group_match.config(text="--- Gruppenphase beendet (Archiv) ---")
        for item in self.tree_matches.get_children(): self.tree_matches.delete(item)
        for i, m in enumerate(self.match_manager.spielplan):
            
            # --- FIX: Das Häkchen wird jetzt an die echten Daten gekoppelt ---
            status = "✔" if m.get("gespielt") else ("🟢" if i == self.match_manager.aktuelles_match_index else "-")
            # ------------------------------------------------------------------
            
            if m.get("gespielt"):
                p_txt, d_txt, id_txt = f"{m.get('base1', 0)} : {m.get('base2', 0)}", f"{m.get('total1', 0):.3f} : {m.get('total2', 0):.3f}", str(m.get("pi_match_id", "-"))
            else: p_txt, d_txt, id_txt = "- : -", "- : -", "-"
            
            # --- NEU: Den programm_name hinten an die values anhängen! ---
            self.tree_matches.insert("", tk.END, iid=str(i), values=(
                m['match_nr'], 
                status, 
                m['gruppe'], 
                f"{m['spieler1']} vs {m['spieler2']}", 
                p_txt, d_txt, id_txt, 
                m.get("programm_name", "-") # <--- HIER
            ))
    
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
            
            # --- NEU: Den programm_name vor den winner klemmen! ---
            self.tree_ko.insert("", tk.END, iid=str(i), values=(
                m['match_nr'], 
                status, 
                self.datei_manager.get_match_name(m['match_nr']),
                f"{m['spieler1']} vs {m['spieler2']}", 
                p_txt, d_txt, id_txt, 
                m.get("programm_name", "-"), # <--- HIER
                m.get("winner", "-")
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
        # --- NEU: Derby-Weiche (NUR in der Gruppenphase!) ---
        if getattr(self.match_manager, 'derby_modus', False) and getattr(self.match_manager, 'phase', None) == TurnierPhase.GRUPPENPHASE:
            self._oeffne_derby_send_dialog()
            return
            
        # --- Der normale (strenge) Turnier-Ablauf für KO-Phase & Standard-Gruppen ---
        match = self.match_manager.get_aktuelles_match()
        if match and self.datei_manager.schreibe_next_match(match['spieler1'], match['spieler2']):
            self.status_label.config(text=f"✅ Daten für {match['spieler1']} vs {match['spieler2']} gesendet!", foreground="green")
            # Nach 5 Sekunden wieder auf Standard setzen
            self.root.after(5000, lambda: self.status_label.config(text="Bereit", foreground="black"))

    def _oeffne_derby_send_dialog(self):
        """Öffnet ein komfortables Popup, um im Derby Spieler an den Pi zu senden."""
        dialog = tk.Toplevel(self.root)
        dialog.title("Derby: Nächstes Match")
        dialog.geometry("500x400")
        dialog.configure(bg="#2b2b2b")
        
        tk.Label(dialog, text="Wer geht an den Schießstand?", font=("Arial", 18, "bold"), bg="#2b2b2b", fg="white").pack(pady=(20, 20))
        
        bekannte_spieler = sorted(list(self.match_manager.ergebnisse.keys()))
        
        # ==========================================================
        # --- DIE AUTO-SUGGEST KI (König & Herausforderer) ---
        # ==========================================================
        last_winner = ""
        last_winner_side = 0
        
        # 1. Den King of the Hill ermitteln (Gewinner des letzten Matches)
        if self.match_manager.spielplan:
            letztes_match = self.match_manager.spielplan[-1]
            if letztes_match.get("gespielt"):
                t1 = letztes_match.get("total1", 0)
                t2 = letztes_match.get("total2", 0)
                
                # Wer hat gewonnen und auf welcher Seite stand er?
                if t1 >= t2: 
                    last_winner = letztes_match.get("spieler1", "")
                    last_winner_side = 1
                else: 
                    last_winner = letztes_match.get("spieler2", "")
                    last_winner_side = 2

        # 2. Spielerliste nach absolvierten Spielen sortieren
        spieler_stats = self.match_manager.ergebnisse
        sortierte_spieler = sorted(spieler_stats.keys(), key=lambda s: spieler_stats[s].get("spiele", 0))

        # 3. Die Zuweisungs-Logik
        if not last_winner:
            # --- FALL A: ALLERERSTES MATCH AM ABEND ---
            # Wir nehmen einfach die ersten beiden Spieler aus der Liste (falls vorhanden)
            kandidat_1 = sortierte_spieler[0] if len(sortierte_spieler) > 0 else ""
            kandidat_2 = sortierte_spieler[1] if len(sortierte_spieler) > 1 else ""
            
            # Position zufällig auswürfeln
            import random
            vorschlaege = [kandidat_1, kandidat_2]
            random.shuffle(vorschlaege)
            
        else:
            # --- FALL B: NORMALES DERBY-MATCH ---
            kandidat_1 = last_winner
            kandidat_2 = ""

            # Denjenigen mit den wenigsten Spielen suchen, der NICHT der König ist!
            for s in sortierte_spieler:
                if s != last_winner:
                    kandidat_2 = s
                    break

            # Zwanghafter Seitenwechsel für den King!
            if last_winner_side == 1:
                # King war links, muss jetzt nach rechts
                vorschlaege = [kandidat_2, kandidat_1]
            else:
                # King war rechts, muss jetzt nach links
                vorschlaege = [kandidat_1, kandidat_2]
        # ==========================================================

        # --- Spieler 1 ---
        tk.Label(dialog, text="Spieler 1:", font=("Arial", 14), bg="#2b2b2b", fg="#aaaaaa").pack()
        cb_p1 = ttk.Combobox(dialog, values=bekannte_spieler, font=("Arial", 16), width=20)
        cb_p1.pack(pady=(0, 15))
        if vorschlaege[0]: cb_p1.set(vorschlaege[0]) # <--- Auto-Suggest eintragen
        
        # --- Spieler 2 ---
        tk.Label(dialog, text="Spieler 2:", font=("Arial", 14), bg="#2b2b2b", fg="#aaaaaa").pack()
        cb_p2 = ttk.Combobox(dialog, values=bekannte_spieler, font=("Arial", 16), width=20)
        cb_p2.pack(pady=(0, 25))
        if vorschlaege[1]: cb_p2.set(vorschlaege[1]) # <--- Auto-Suggest eintragen
        
        def senden():
            p1 = cb_p1.get().strip()
            p2 = cb_p2.get().strip()
            
            if not p1 or not p2:
                messagebox.showwarning("Halt!", "Bitte für beide Seiten einen Namen auswählen oder eintragen.", parent=dialog)
                return
                
            erfolg = self.datei_manager.schreibe_next_match(p1, p2, 5, 30)
            
            if erfolg:
                # --- Das Wartezimmer für den Beamer füllen! ---
                self.match_manager.derby_pending_p1 = p1
                self.match_manager.derby_pending_p2 = p2
                
                # Den Beamer sofort zwingen, sich neu zu zeichnen (verhindert Wartezeiten)
                if self.beamer_window and tk.Toplevel.winfo_exists(self.beamer_window):
                    self.beamer_window.refresh_display()
                
                dialog.destroy()
            else:
                messagebox.showerror("Fehler", "Netzwerkfehler: Konnte nicht an den Pi gesendet werden.", parent=dialog)

        # Senden Button
        btn = tk.Button(dialog, text="🚀 An Pi senden", font=("Arial", 16, "bold"), bg="#00ff00", fg="black", command=senden)
        btn.pack(pady=10)
        
        # Fokus setzen
        cb_p1.focus_set()


    def open_rename_dialog(self):
        sel = self.tree_overview.selection()
        if not sel: return
        old_name = self.tree_overview.item(sel[0])['values'][0]
        
        d = tk.Toplevel(self.root)
        d.title("Umbenennen")
        d.geometry("300x150")
        d.grab_set()
        
        ttk.Label(d, text=f"Neuer Name für '{old_name}':").pack(pady=10)
        ent = ttk.Entry(d, width=20)
        ent.insert(0, old_name)
        ent.pack(pady=5)
        
        def save():
            new_name = ent.get().strip()
            
            # 1. Abfangen von leeren Namen oder gar keiner Änderung
            if not new_name or new_name == old_name:
                return
                
            # 2. NEUER SCHUTZWALL: Prüfen, ob der Name schon im System existiert!
            if new_name in self.match_manager.ergebnisse:
                msg = (f"⚠️ Namenskonflikt!\n\nDer Name '{new_name}' existiert bereits im Turnier.\n\n"
                       f"Um Datenverlust zu vermeiden, wähle bitte einen eindeutigen Ersatznamen, "
                       f"z. B. '{new_name}_für_{old_name}'.")
                messagebox.showwarning("Fehler beim Umbenennen", msg)
                return

            # 3. Wenn alles sicher ist, umbenennen!
            if self.match_manager.rename_player(old_name, new_name):
                self.update_all_displays()
                self.datei_manager.speichere_turnier_stand(self.match_manager.get_state())
                d.destroy()
                
        ttk.Button(d, text="UMBENENNEN", command=save).pack(pady=15)

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
        # Einfach machen, nicht mehr fragen! Und da silent=False (Standard), öffnet sich der Browser.
        erfolg, nachricht = self.html_exporter.generiere_bericht(
            ergebnisse=self.match_manager.ergebnisse, 
            spielplan=self.match_manager.spielplan,
            ko_spielplan=self.match_manager.ko_spielplan, 
            datei_manager=self.datei_manager
        )
 
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
        # Wir setzen BEIDES zurück, um das Caching auszutricksen
        self.last_mtime = 0
        self.last_raw_data = "" 
        #self.live_match_finished = False 
        self.check_live_data()

    def check_live_data(self):
        live_file = self.datei_manager.live_ticker_path
        zeit_jetzt = datetime.datetime.now().strftime("%H:%M:%S.%f")[:-3]
        
        # 1. GIBT ES DIE DATEI?
        if not os.path.exists(live_file):
            # WICHTIGER SCHUTZ: Nur auf "WARTEN" setzen, wenn kein Match läuft 
            # UND wir nicht gerade absichtlich das Endergebnis anzeigen!
            if not getattr(self, 'match_is_live', False) and not getattr(self, 'zeige_ergebnis_screen', False):
                if self.beamer_window and tk.Toplevel.winfo_exists(self.beamer_window):
                    self.beamer_window.update_live_score(0, 0, "WARTEN")
        else:
            # 2. DATEI IST DA! Wir lesen sie sofort aus (SMB-Cache umgehen)
            try:
                try:
                    with open(live_file, "r", encoding="utf-8") as f:
                        raw_data = f.read()
                except PermissionError:
                    # Pi schreibt exakt in dieser Millisekunde. Wir brechen ab und warten 333ms.
                    self.root.after(333, self.check_live_data)
                    return
                except UnicodeDecodeError:
                    try:
                        with open(live_file, "r", encoding="latin-1") as f:
                            raw_data = f.read()
                    except PermissionError:
                        self.root.after(333, self.check_live_data)
                        return

                # 3. DATEI INHALTLICH VERARBEITEN
                if raw_data.strip():
                    try:
                        data = json.loads(raw_data)
                        timeline = data.get("timeline", []) if isinstance(data, dict) else data
                        
                        p1_treffer, p2_treffer = 0, 0
                        p1_speed, p2_speed = 0.0, 0.0
                        current_status = ""
                        ruhephasen = ["LADEN", "ACHTUNG", "SICHERHEIT", "RESET", "VORBEREITEN"]
                        
                        # Wir spulen das Match chronologisch ab
                        for ev in timeline:
                            current_status = ev.get("m", "")
                            if current_status not in ruhephasen: 
                                p1_treffer = ev.get("p1_pd", 0) + ev.get("p1_pz", 0)
                                p2_treffer = ev.get("p2_pd", 0) + ev.get("p2_pz", 0)
                                p1_speed   = ev.get("p1_spd", 0.0) + ev.get("p1_spz", 0.0)
                                p2_speed   = ev.get("p2_spd", 0.0) + ev.get("p2_spz", 0.0)
                            else:
                                p1_treffer = ev.get("p1_pd", 0)
                                p2_treffer = ev.get("p2_pd", 0)
                                p1_speed   = ev.get("p1_spd", 0.0)
                                p2_speed   = ev.get("p2_spd", 0.0)
                                
                        # Namen auslesen
                        if timeline:
                            last_ev = timeline[-1]
                            p1_name = last_ev.get("p1_name", "Spieler 1")
                            p2_name = last_ev.get("p2_name", "Spieler 2")
                        else:
                            p1_name, p2_name = "Spieler 1", "Spieler 2"

                        # Status merken, damit wir wissen, ob wir löschen dürfen ohne zu flackern!
                        if current_status == "SICHERHEIT":
                            self.zeige_ergebnis_screen = True
                            self.match_is_live = False
                        else:
                            # Auch "RESET" oder "VORBEREITEN" zählen noch als Live-Match!
                            self.zeige_ergebnis_screen = False
                            self.match_is_live = True

                        # Punkte berechnen
                        is_ko = getattr(self.match_manager, "phase", None) in [TurnierPhase.KO_PHASE, TurnierPhase.BEENDET]
                        current_match = self.match_manager.get_aktuelles_match()
                        stechen_laeuft = current_match.get("stechen_notwendig") if current_match else False
                        
                        if is_ko and not stechen_laeuft:
                            p1_score = f"{(p1_treffer + p1_speed):.2f}"
                            p2_score = f"{(p2_treffer + p2_speed):.2f}"
                        else:
                            p1_score = str(p1_treffer)
                            p2_score = str(p2_treffer)
                                
                        # An den Beamer senden
                        if self.beamer_window and tk.Toplevel.winfo_exists(self.beamer_window):
                            self.beamer_window.update_live_score(
                                p1_score, p2_score, current_status,
                                p1_base=p1_treffer, p2_base=p2_treffer,
                                p1_total=(p1_treffer + p1_speed), p2_total=(p2_treffer + p2_speed),
                                p1_name=p1_name, p2_name=p2_name 
                            )

                        # ==============================================================
                        # --- DEIN GENIALER HACK: DATEI SOFORT LÖSCHEN! ---
                        # Wir haben die Daten verarbeitet. Weg damit!
                        # So MUSS Windows beim nächsten Treffer die Datei frisch vom Pi holen!
                        # ==============================================================

                        # --- OPTIONAL: Debug-Kopie erstellen, bevor wir löschen ---
                        if getattr(self, 'debug_live_polling', False):
                            import shutil
                            debug_dir = "debug_logs"
                            if not os.path.exists(debug_dir):
                                os.makedirs(debug_dir)
                            
                            # Eindeutigen Dateinamen mit Zeitstempel erzeugen
                            # z.B. 2026-06-20_04-39-18_123_live.json
                            timestamp_name = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S_%f")[:-3]
                            debug_file_path = os.path.join(debug_dir, f"{timestamp_name}_live.json")
                            
                            try:
                                # Wir kopieren den Inhalt des Strings (raw_data) direkt in die neue Datei,
                                # anstatt shutil.copy zu nutzen. Das ist sicherer, falls Windows die 
                                # Originaldatei gerade komisch behandelt.
                                with open(debug_file_path, "w", encoding="utf-8") as debug_file:
                                    debug_file.write(raw_data)
                            except Exception as e:
                                print(f"⚠️ Konnte Debug-Kopie nicht speichern: {e}")
                        # -----------------------------------------------------------
                        try:
                            os.remove(live_file)
                        except Exception:
                            pass # Falls Windows die Datei gerade nicht loslässt, löschen wir sie beim nächsten Mal.
                            
                    except json.JSONDecodeError:
                        pass # Datei war vom Pi noch nicht fertig geschrieben.
                        
            except Exception as e:
                print(f"⚠️ [{zeit_jetzt}] Fehler in check_live_data: {e}")

        # Immer fleißig weiterticken!
        self.root.after(333, self.check_live_data)

#NETZWERKFREIGABE:       
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

