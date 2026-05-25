import tkinter as tk
from tkinter import font
from TurnierLogikDeLuebs import generiere_setzliste
from MatchManagerDeLuebs import TurnierPhase
import math

def truncate_text(text, max_length):
    """Kürzt einen Text auf max_length und hängt '...' an, falls er zu lang ist."""
    if len(text) > max_length:
        return text[:max_length-1] + "." # -1 für den Punkt
    return text
    

class SmartTicker:
    def __init__(self, parent_window, width):
        self.parent = parent_window
        self.width = width
        
        # Zentrale Einstellungen (keine "Magic Numbers" mehr im Code verstreut)
        self.height = 40
        self.bg_color = "#1a1a1a"
        self.text_color = "#39FF14" # Neongrün
        self.speed = -3
        self.interval = 20
        self.font = font.Font(family="Arial", size=16, weight="bold")

        # Das Canvas aufbauen
        self.canvas = tk.Canvas(self.parent, width=self.width, height=self.height, bg=self.bg_color, highlightthickness=0)
        self.canvas.place(relx=0, rely=1.0, anchor="sw", relwidth=1.0, height=self.height)
        
        self.scroll_job = None
        self.text_id = None

    def show_message(self, text):
        # Ticker über alle anderen Frames legen
        self.parent.tk.call('raise', self.canvas._w)
        
        # Alte Animation stoppen & Canvas leeren
        if self.scroll_job:
            self.parent.after_cancel(self.scroll_job)
            self.scroll_job = None
        self.canvas.delete("all")

        if not text:
            return 

        text_width = self.font.measure(text)
        y_center = self.height / 2 # Berechnet die vertikale Mitte automatisch

        if text_width <= self.width:
            self.canvas.create_text(
                self.width / 2, y_center, 
                text=text, font=self.font, fill=self.text_color, anchor=tk.CENTER
            )
        else:
            self.text_id = self.canvas.create_text(
                self.width, y_center, 
                text=text, font=self.font, fill=self.text_color, anchor=tk.W
            )
            self._scroll()

    def _scroll(self):
        self.canvas.move(self.text_id, self.speed, 0)
        bbox = self.canvas.bbox(self.text_id)
        if bbox and bbox[2] < 0: 
            self.canvas.coords(self.text_id, self.width, self.height / 2)
        self.scroll_job = self.parent.after(self.interval, self._scroll)

class PublicDisplay(tk.Toplevel):
    def __init__(self, parent, match_manager, pause_callback=None, matches_per_page_var=None, groups_per_page_var=None, datei_manager=None): # <-- NEU
        super().__init__(parent)
        self.match_manager = match_manager
        self.pause_callback = pause_callback
        self.datei_manager = datei_manager # <-- NEU
        
        self.title("LIVE")
        #self.attributes('-fullscreen', True) 
        self.configure(bg="#1a1a1a") 

        #self.view_state = 0  #ENTFERNT DURCH MEHRSEITENANZEIGE
        
        # --- ARCHITEKTUR: Playlist & Paginierung ---
        self.matches_per_page_var = matches_per_page_var
        self.groups_per_page_var = groups_per_page_var
        
        self.playlist = []          # Speichert die Abfolge der Screens
        self.playlist_index = 0     # Aktueller Index in der Playlist
        self.timer_id = None

        #self.ticker_font = font.Font(family="Arial", size=16, weight="bold")
        self.beamer_width = 1280 # Breite deines Beamers (720p = 1280x720)
        self.ticker = SmartTicker(self, self.beamer_width)
        
        #self.beamer_texte = beamer_texte or {}
        
        # Das schwarze/dunkle Band am unteren Rand
        self.ticker_canvas = tk.Canvas(self, width=self.beamer_width, height=15, bg="#1a1a1a", highlightthickness=0)
        self.ticker_canvas.place(relx=0, rely=1.0, anchor="sw", relwidth=1.0, height=42)
        
        self.scroll_job = None # Speichert den Animations-Loop
        self.text_id = None


        self.setup_ui()
        self.refresh_display()
        
        self.is_paused = False
        
        # Wir binden die Tasten an das Hauptfenster (parent) UND an den Beamer (self)
        # So funktioniert es immer, egal wo du gerade hingeklickt hast.
        parent.bind("<Pause>", self.toggle_pause)
        parent.bind("<p>", self.toggle_pause)
        parent.bind("<P>", self.toggle_pause)
        self.bind("<Pause>", self.toggle_pause)
        self.bind("<p>", self.toggle_pause)
        self.bind("<P>", self.toggle_pause)        
        
        
        self.is_borderless = False # Merkt sich, ob Vollbild an oder aus ist
        self.bind("<F12>", self.toggle_borderless)
        parent.bind("<F12>", self.toggle_borderless)
        

    def toggle_borderless(self, event=None):
        self.is_borderless = not self.is_borderless
        # Den Rahmen ein- oder ausschalten
        self.overrideredirect(self.is_borderless)
        
        #if self.is_borderless:
        #    # Maximiert das rahmenlose Fenster (perfekt für den Beamer)
        #    self.state('zoomed')
        #else:
        #    # Bringt das Fenster in den normalen Fenstermodus zurück
        #    self.state('normal')


    def setup_ui(self):
        self.columnconfigure(0, weight=1, uniform="equal_cols") 
        self.columnconfigure(1, weight=1, uniform="equal_cols")
        self.rowconfigure(1, weight=1)

        # HIER: 'header' in 'self.header_label' ändern!
        self.header_label = tk.Label(self, text="SHOOTING DELÜBS - MEISTERSCHAFT", 
                          font=("Arial", 36, "bold"), bg="#333", fg="white", pady=15)
        self.header_label.grid(row=0, column=0, columnspan=2, sticky="ew")

        # Linke Seite (Wird dynamisch befüllt)
        self.left_frame = tk.Frame(self, bg="#1a1a1a", padx=40, pady=40)
        self.left_frame.grid(row=1, column=0, sticky="nsew")

        # Rechte Seite (Wechselnde Ansicht)
        self.right_frame = tk.Frame(self, bg="#222", padx=10, pady=10)
        self.right_frame.grid(row=1, column=1, sticky="nsew")

        self.table_container = tk.Frame(self.right_frame, bg="#222")
        self.table_container.pack(fill="both", expand=True)

    def refresh_display(self):
        match = self.match_manager.get_aktuelles_match()
        next_m = self.match_manager.get_naechstes_match()
        phase = getattr(self.match_manager, 'phase', TurnierPhase.NICHT_GESTARTET)

        # Prüfen ob Finale gespielt ist
        is_ko = phase in [TurnierPhase.KO_PHASE, TurnierPhase.BEENDET]
        finale = next((m for m in self.match_manager.ko_spielplan if m.get("match_nr") == "FIN"), None) if is_ko else None
        
        # Linke Seite komplett neu aufbauen
        for widget in self.left_frame.winfo_children(): widget.destroy()

        if phase == TurnierPhase.BEENDET and finale and finale.get("winner"):
            # --- TURNIER BEENDET -> PODEST AUF DER LINKEN SEITE ---
            self.render_podium(self.left_frame, finale)
        else:
            # --- TURNIER LÄUFT ODER WARTET -> NORMALE ANZEIGE LINKS ---
            self.lbl_status = tk.Label(self.left_frame, font=("Arial", 20), bg="#1a1a1a", fg="#aaaaaa")
            self.lbl_status.pack(anchor="w")

            if match:
                self.match_frame = tk.Frame(self.left_frame, bg="#1a1a1a")
                self.match_frame.pack(anchor="w", pady=20, fill="x")

                self.lbl_p1_name = tk.Label(self.match_frame, text=match['spieler1'], font=("Arial", 40, "bold"), bg="#1a1a1a", fg="white")
                self.lbl_p1_name.grid(row=0, column=0, sticky="w", padx=(0, 20))
                self.lbl_score_p1 = tk.Label(self.match_frame, text="0", font=("Arial", 48, "bold"), bg="#1a1a1a", fg="#39FF14")
                self.lbl_score_p1.grid(row=0, column=1, sticky="w")

                tk.Label(self.match_frame, text="vs.", font=("Arial", 24), bg="#1a1a1a", fg="#aaaaaa").grid(row=1, column=0, columnspan=2, pady=10)

                self.lbl_p2_name = tk.Label(self.match_frame, text=match['spieler2'], font=("Arial", 40, "bold"), bg="#1a1a1a", fg="white")
                self.lbl_p2_name.grid(row=2, column=0, sticky="w", padx=(0, 20))
                self.lbl_score_p2 = tk.Label(self.match_frame, text="0", font=("Arial", 48, "bold"), bg="#1a1a1a", fg="#39FF14")
                self.lbl_score_p2.grid(row=2, column=1, sticky="w")

                self.lbl_match_status = tk.Label(self.left_frame, text="Warten auf Start...", font=("Arial", 20, "bold"), bg="#1a1a1a", fg="gray")
                self.lbl_match_status.pack(anchor="w", pady=(0, 20))

                # Wenn es keine Gruppe gibt, jagen wir die match_nr (z.B. 'HF1') durch unseren Übersetzer!
                gruppen_text = match.get('gruppe', self.datei_manager.get_match_name(match.get('match_nr', '')))
                # NACHHER:
                if match.get("stechen_notwendig"):
                    prefix = "🚨 STECHEN: "
                else:
                    prefix = "GRUPPE " if 'gruppe' in match else "KO-MATCH: "
                self.lbl_status.config(text=f"AKTUELL: {prefix}{gruppen_text}")
                
            else:
                # Dein neuer Funktionsname!
                haupt_text, sub_text = self.datei_manager.get_beamer_text(phase)
                
                self.lbl_match = tk.Label(self.left_frame, text=haupt_text, font=("Arial", 40, "bold"), bg="#1a1a1a", fg="white")
                self.lbl_match.pack(anchor="w", pady=20)
                self.lbl_status.config(text=sub_text)

            self.lbl_next = tk.Label(self.left_frame, font=("Arial", 24), bg="#1a1a1a", fg="#00ff00", justify="left")
            self.lbl_next.pack(anchor="w", pady=20)
            
            if next_m:
                # Auch hier: Übersetzer statt Magic String!
                n_phase = next_m.get('gruppe', self.datei_manager.get_match_name(next_m.get('match_nr', '')))
                self.lbl_next.config(text=f"NEXT: {n_phase}\n{next_m['spieler1']} vs. {next_m['spieler2']}")
            else:
                self.lbl_next.config(text="ALS NÄCHSTES: ---")

        # --- FIX: BEI JEDEM REFRESH PLAYLIST ZWINGEND NEU BAUEN UND INDEX SCHÜTZEN ---
        self.build_playlist()
        if self.playlist_index >= len(self.playlist):
            self.playlist_index = 0

        # Rechte Seite updaten
        self.render_right_side()
        self.restart_timer()

    def build_playlist(self):
        self.playlist = []
        is_ko = getattr(self.match_manager, 'phase', TurnierPhase.NICHT_GESTARTET) in [TurnierPhase.KO_PHASE, TurnierPhase.BEENDET]

        matches_per_page = self.matches_per_page_var.get()
        groups_per_page = self.groups_per_page_var.get()

        if not is_ko:
            # Gruppenphase: Wir rotieren Tabellen und den Detail-Spielplan
            anzahl_gruppen = len(self.match_manager.gruppen)
            seiten_gruppen = math.ceil(anzahl_gruppen / groups_per_page) 
            for page in range(max(1, seiten_gruppen)):
                self.playlist.append(("TABLES", page))
                
            plan = self.match_manager.spielplan
            seiten_plan = math.ceil(len(plan) / matches_per_page)
            for page in range(max(1, seiten_plan)):
                self.playlist.append(("SCHEDULE", page))
        else:
            # --- ELA: K.O.-Phase --- 
            # Hier rotieren wir NUR NOCH das ultimative All-In-One Bracket!
            anzahl_ko_matches = len(self.match_manager.ko_spielplan)
            seiten_ko = math.ceil(anzahl_ko_matches / matches_per_page)
            for page in range(max(1, seiten_ko)):
                self.playlist.append(("KO_BRACKET", page))

    def advance_view(self):
        self.build_playlist()
        
        if not self.playlist:
            self.restart_timer()
            return
            
        # SRE-SCHUTZWALL: Falls die Playlist geschrumpft ist
        if self.playlist_index >= len(self.playlist):
            self.playlist_index = 0
            page_changed = True
        else:
            old_index = self.playlist_index
            self.playlist_index = (self.playlist_index + 1) % len(self.playlist)
            page_changed = (old_index != self.playlist_index)
            
        # --- DER MAGISCHE FILTER ---
        # Wir reißen die Tabelle nur noch ab, wenn wir WIRKLICH auf eine andere Seite geblättert haben!
        if page_changed:
            self.render_right_side()
            
        self.restart_timer()


    def render_podium(self, parent_frame, fin_match):
        """Erzeugt das heroische Siegerpodest (jetzt für die linke Seite)."""
        tk.Label(parent_frame, text="🏆DELÜBS MEISTER🏆", font=("Arial", 32, "bold"), bg="#1a1a1a", fg="#ffd700").pack(pady=(0, 40))
        
        p_frame = tk.Frame(parent_frame, bg="#1a1a1a")
        p_frame.pack(expand=True)

        p3m = next((m for m in self.match_manager.ko_spielplan if m.get("match_nr") == "3PL"), None)

        sieger = [
            {"pos": "2. Platz", "name": truncate_text(fin_match.get("loser", "---"),12), "color": "#c0c0c0", "h": 150},
            {"pos": "1. Platz", "name": truncate_text(fin_match.get("winner", "---"),12), "color": "#ffd700", "h": 220},
            {"pos": "3. Platz", "name": truncate_text(p3m.get("winner", "---"),12) if p3m else "---", "color": "#cd7f32", "h": 100}
        ]

        for s in sieger:
            f = tk.Frame(p_frame, bg=s["color"], width=180, height=s["h"])
            # HIER IST DER FIX: anchor="s" anstelle von anchor="bottom"
            f.pack(side="left", anchor="s", padx=10)
            f.pack_propagate(False)
            tk.Label(f, text=s["pos"], font=("Arial", 14, "bold"), bg=s["color"]).pack(pady=5)
            tk.Label(f, text=s["name"], font=("Arial", 16, "bold"), bg=s["color"], wraplength=160).pack(expand=True)

    # --- Der Rest bleibt identisch ---
    def toggle_view(self):
        self.view_state = 1 - self.view_state
        self.render_right_side()
        self.restart_timer()

    def restart_timer(self):
        if self.timer_id: 
            self.after_cancel(self.timer_id)
        # NEU: Der Timer stößt jetzt direkt die seitenbasierte Playlist-Rotation an
        if not getattr(self, 'is_paused', False):
            self.timer_id = self.after(10000, self.advance_view)

    def toggle_pause(self, event=None):
        self.is_paused = not self.is_paused
        
        if self.is_paused:
            if self.timer_id:
                self.after_cancel(self.timer_id)
                self.timer_id = None
            self.header_label.config(text="SHOOTING DELÜBS - MEISTERSCHAFT ⏸️", fg="#ffd700")
        else:
            self.header_label.config(text="SHOOTING DELÜBS - MEISTERSCHAFT", fg="white")
            self.restart_timer()

        # --- NEU: Den Manager informieren, statt selbst einzugreifen ---
        if self.pause_callback:
            self.pause_callback(self.is_paused)

    def render_right_side(self):
        for widget in self.table_container.winfo_children(): widget.destroy()

        # Fallback & Initialisierung
        if not self.playlist:
            self.build_playlist()
            self.playlist_index = 0

        # Welchen Screen sollen wir zeigen?
        view_type, page = self.playlist[self.playlist_index]

        # Info für den Header generieren (z.B. "Seite 1/3")
        total_pages_for_type = sum(1 for v, p in self.playlist if v == view_type)
        page_info = f" (Seite {page + 1}/{total_pages_for_type})" if total_pages_for_type > 1 else ""

        # Verteiler (Separation of Concerns)
        if view_type == "TABLES":
            self.update_tables(page, page_info)
        elif view_type == "KO_BRACKET":
            self.update_ko_bracket(page, page_info)
        elif view_type == "SCHEDULE":
            self.update_match_schedule(page, page_info)

    def update_match_schedule(self, page=0, page_info=""):
        # --- ELA: Toter Code entfernt! Diese Ansicht läuft NUR noch in der Gruppenphase ---
        plan = self.match_manager.spielplan
        
        titel = f"DETAILLIERTER SPIELPLAN{page_info}"
        tk.Label(self.table_container, text=titel, font=("Arial", 22, "bold"), bg="#222", fg="#00ff00").pack(pady=(0, 10))
        
        # --- HEADER ---
        h_frame = tk.Frame(self.table_container, bg="#444"); h_frame.pack(fill="x")
        
        header_font = ("Arial", 12)
        header_fg = "#cccccc" 
        
        # --- ELA: Wieder sauber in "Nr." und "Grp" getrennt ---
        tk.Label(h_frame, text="Nr.", font=header_font, bg="#444", fg=header_fg, width=4, anchor="center").pack(side="left")
        tk.Label(h_frame, text="Grp", font=header_font, bg="#444", fg=header_fg, width=4, anchor="center").pack(side="left")
        # --------------------------------------------------------
        
        tk.Label(h_frame, text="Paarung", font=header_font, bg="#444", fg=header_fg, width=24, anchor="w").pack(side="left", padx=5)
        tk.Label(h_frame, text="Trf", font=header_font, bg="#444", fg=header_fg, width=8, anchor="center").pack(side="left")
        tk.Label(h_frame, text="Match-Wertung", font=header_font, bg="#444", fg=header_fg, width=14, anchor="center").pack(side="left")
        tk.Label(h_frame, text="Pkt", font=header_font, bg="#444", fg=header_fg, width=4, anchor="center").pack(side="left")

        akt_match = self.match_manager.get_aktuelles_match()
        akt_nr = akt_match["match_nr"] if akt_match else ""

        # --- Slicing für die Seiten ---
        matches_per_page = self.matches_per_page_var.get()
        start_idx = page * matches_per_page
        end_idx = start_idx + matches_per_page
        page_matches = plan[start_idx:end_idx]

        for i, m in enumerate(page_matches):
            is_active = (str(m["match_nr"]) == str(akt_nr))
            bg_color = "#444" if is_active else ("#333" if i % 2 == 0 else "#2a2a2a")
            fg_color = "#00ff00" if is_active else "white"
            
            f = tk.Frame(self.table_container, bg=bg_color); f.pack(fill="x", pady=1)
            
            paarung = f"{m['spieler1']} vs. {m['spieler2']}"
            
            if m.get("gespielt"):
                treffer = f"{m.get('base1', 0)}:{m.get('base2', 0)}"
                wertung = f"{m.get('total1', 0):.2f}:{m.get('total2', 0):.2f}"
                
                # --- Pkt-Berechnung direkt ohne is_ko Check ---
                b1, b2 = m.get('base1', 0), m.get('base2', 0)
                if b1 > b2: p_text = "3:0"
                elif b1 < b2: p_text = "0:3"
                else: p_text = "1:1"
            else: 
                treffer, wertung, p_text = "-:-", "-:-", "-:-"

            data_font = ("Arial", 12)
            
            # --- ELA: Jetzt getrennte Labels für Nummer und Gruppe ---
            tk.Label(f, text=str(m['match_nr']), font=data_font, bg=bg_color, fg=fg_color, width=4, anchor="center").pack(side="left")
            tk.Label(f, text=m.get('gruppe', ''), font=data_font, bg=bg_color, fg=fg_color, width=4, anchor="center").pack(side="left")
            # ---------------------------------------------------------
            
            tk.Label(f, text=paarung, font=("Arial", 12, "bold" if is_active else "normal"), bg=bg_color, fg=fg_color, width=24, anchor="w").pack(side="left", padx=5)
            tk.Label(f, text=treffer, font=data_font, bg=bg_color, fg="#ffd700", width=8, anchor="center").pack(side="left")
            tk.Label(f, text=wertung, font=data_font, bg=bg_color, fg="#aaa", width=14, anchor="center").pack(side="left")
            tk.Label(f, text=p_text, font=data_font, bg=bg_color, fg="#00ff00", width=4, anchor="center").pack(side="left")
            
    def update_tables(self, page=0, page_info=""):
        # --- FEHLENDE VARIABLEN HINZUGEFÜGT ---
        akt_match = self.match_manager.get_aktuelles_match()
        akt_gruppe = akt_match['gruppe'] if akt_match and 'gruppe' in akt_match else ""
        # --------------------------------------

        gruppen_keys = sorted(list(self.match_manager.gruppen.keys()))
        
        # --- ELA: Slicing der Gruppen für die aktuelle Seite ---
        groups_per_page = self.groups_per_page_var.get()
        start_idx = page * groups_per_page
        end_idx = start_idx + groups_per_page
        page_gruppen_keys = gruppen_keys[start_idx:end_idx]
        
        # Titel (Optional, falls du hier auch Seite X/Y anzeigen willst)
        if page_info:
            tk.Label(self.table_container, text=f"GRUPPENPHASE {page_info}", font=("Arial", 22, "bold"), bg="#222", fg="#00ff00").pack(pady=(0, 5))
        # Wir greifen auf self.match_manager.ergebnisse zu und nutzen die TurnierLogik
        daten_basis = getattr(self.match_manager, 'ergebnisse', {})
        setzliste = generiere_setzliste(daten_basis, self.match_manager.gruppen)
        
        # Limit anhand der gleichen Logik wie im K.O.-Baum berechnen
        limit = 8 if len(setzliste) > 8 else 4
        qualified_names = [x["name"] for x in setzliste[:limit]]

        # Der große "Enthüllungs"-Trigger: Sind alle Gruppenspiele durch?
        gruppen_beendet = (akt_match is None and getattr(self.match_manager, 'phase', TurnierPhase.NICHT_GESTARTET) == TurnierPhase.GRUPPEN_ABGESCHLOSSEN)

        for g in page_gruppen_keys:
            # --- ELA: Info-Text auslesen und dynamisch formatieren ---
            info_text = self.match_manager.gruppen_zeiten.get(g, "").strip()
            titel_text = f"GRUPPE {g} - {info_text}" if info_text else f"GRUPPE {g}"
            # ---------------------------------------------------------
            
            daten = self.match_manager.get_tabelle(g)
            titel_farbe = "#00ff00" if g == akt_gruppe else "white"
            
            t_frame = tk.Frame(self.table_container, bg="#222"); t_frame.pack(fill="x", pady=(10, 2))
            
            # NEU: Wir nutzen den formatierten titel_text
            tk.Label(t_frame, text=titel_text, font=("Arial", 18, "bold"), bg="#222", fg=titel_farbe).pack(anchor="w")
            
            h_frame = tk.Frame(self.table_container, bg="#444"); h_frame.pack(fill="x")
            
            # --- FIX: "bold" entfernt und fg="#cccccc" (Silber-Grau) für den Look wie im Spielplan ---
            for t, w in [("Pl.",4), ("Name",15), ("Sp",3), ("Pkt",4), ("Diff",8), ("Gesamt",8)]:
                # NEU: Weiche für die Ausrichtung. Name = linksbündig ("w"), Rest = zentriert ("center")
                ausrichtung = "w" if t == "Name" else "center"
                tk.Label(h_frame, text=t, font=("Arial", 14), bg="#444", fg="#cccccc", width=w, anchor=ausrichtung).pack(side="left")
                
            for i, s in enumerate(daten):
                # --- Farbliche Hervorhebung für die Qualifizierten ---
                is_qualified = gruppen_beendet and (s['name'] in qualified_names)

                if is_qualified:
                    bg = "#113311"       # Edles, dunkles Neongrün für die Zeile
                    name_fg = "#39FF14"  # Knalliges Neongrün für den Namen
                    rang_text = "Q"      # 'Q' statt Platzierung
                else:
                    bg = "#333" if i % 2 == 0 else "#2a2a2a"
                    name_fg = "white"
                    rang_text = f"{i+1}."

                f = tk.Frame(self.table_container, bg=bg); f.pack(fill="x", pady=1)
                
                # --- Alle Daten (außer Name) zentrieren ---
                tk.Label(f, text=rang_text, font=("Arial", 14, "bold"), bg=bg, fg="white" if not is_qualified else "#39FF14", width=4, anchor="center").pack(side="left")
                tk.Label(f, text=s['name'], font=("Arial", 14, "bold" if is_qualified else "normal"), bg=bg, fg=name_fg, width=15, anchor="w").pack(side="left")
                tk.Label(f, text=s['spiele'], font=("Arial", 14), bg=bg, fg="white", width=3, anchor="center").pack(side="left")
                tk.Label(f, text=s['punkte'], font=("Arial", 14, "bold"), bg=bg, fg="#00ff00", width=4, anchor="center").pack(side="left")
                tk.Label(f, text=f"{s['differenz']:+.2f}", font=("Arial", 14), bg=bg, fg="#aaa", width=8, anchor="center").pack(side="left")
                tk.Label(f, text=f"{s.get('score_erzielt', 0):.2f}", font=("Arial", 14, "bold"), bg=bg, fg="#ffd700", width=8, anchor="center").pack(side="left")

    def update_ko_bracket(self, page=0, page_info=""):
        titel = f"K.O.-PHASE - TURNIERBAUM{page_info}"
        tk.Label(self.table_container, text=titel, font=("Arial", 22, "bold"), bg="#222", fg="#00ff00").pack(pady=(0, 10))
        
        # --- DER PERFEKT AUSGERICHTETE HEADER ---
        h_frame = tk.Frame(self.table_container, bg="#444"); h_frame.pack(fill="x")
        
        # NEUE BREITEN & ALIGNMENTS:
        # Runde: width=5 (Schließt die Lücke zur Paarung)
        # Paarung: width=24, anchor="w" (Linksbündig, bündig mit der Überschrift)
        # Wertung: width=10, anchor="center"
        # Sieger: width=20, anchor="w"
        tk.Label(h_frame, text="Rnd", font=("Arial", 14), bg="#444", fg="#cccccc", width=3, anchor="w").pack(side="left", padx=10)
        tk.Label(h_frame, text="Paarung", font=("Arial", 14), bg="#444", fg="#cccccc", width=23, anchor="w").pack(side="left")
        tk.Label(h_frame, text="Wertung", font=("Arial", 14), bg="#444", fg="#cccccc", width=9, anchor="center").pack(side="left")
        tk.Label(h_frame, text="Sieger", font=("Arial", 14), bg="#444", fg="#cccccc", width=22, anchor="w").pack(side="left", padx=10)
        
        matches_per_page = self.matches_per_page_var.get()
        start_idx = page * matches_per_page
        end_idx = start_idx + matches_per_page
        page_matches = self.match_manager.ko_spielplan[start_idx:end_idx]
        
        akt_match = self.match_manager.get_aktuelles_match()
        akt_nr = akt_match["match_nr"] if akt_match else ""
        
        for i, m in enumerate(page_matches):
            is_active = (str(m["match_nr"]) == str(akt_nr))
            bg = "#444" if is_active else ("#333" if i % 2 == 0 else "#2a2a2a")
            f = tk.Frame(self.table_container, bg=bg); f.pack(fill="x", pady=1)
            
            # 1. Runde (Breite auf 5 angepasst)
            tk.Label(f, text=str(m['match_nr']), font=("Arial", 14), bg=bg, fg="#aaa", width=3, anchor="w").pack(side="left", padx=10)
            
            # 2. Paarung (Gekürzt auf max 26 Zeichen)
            paarung_text = f"{m['spieler1']} vs. {m['spieler2']}"
            # WICHTIG: Die Zahl hier bestimmt, ab wann die ... erscheinen
            paarung_text_kurz = truncate_text(paarung_text, 28) 
            
            tk.Label(f, text=paarung_text_kurz, font=("Arial", 14, "bold" if is_active else "normal"), bg=bg, fg="#00ff00" if is_active else "white", width=23, anchor="w").pack(side="left")
            
            # 3. Wertung (Die Logik erweitern!)
            if m.get("gespielt"):
                # Haupt-Wertung
                wertung_text = f"{m.get('total1', 0):.2f}:{m.get('total2', 0):.2f}"
                
                # --- ELA: Stechen-Ergebnis als Unterzeile anzeigen ---
                if m.get("stechen_beendet"):
                    stechen_text = f"ST: {m.get('stechen_b1')}:{m.get('stechen_b2')}"
                    wertung_display = f"{wertung_text}\n({stechen_text})"
                else:
                    wertung_display = wertung_text
                # -----------------------------------------------------
            else:
                wertung_display = "-:-"
            
            # Label etwas höher machen, damit der Zeilenumbruch Platz hat
            tk.Label(f, text=wertung_display, font=("Arial", 12), bg=bg, fg="#aaa", width=9, height=2, anchor="center").pack(side="left")
            
            # 4. Sieger
            winner_name = m.get("winner")
            if winner_name:
                winner_kurz = truncate_text(winner_name, 14)
                winner_text = f"🏆 {winner_kurz}"
                winner_color = "#ffd700"
            else:
                winner_text = "---"
                winner_color = "#555555"
                
            tk.Label(f, text=winner_text, font=("Arial", 14, "bold"), bg=bg, fg=winner_color, width=22, anchor="w").pack(side="left", padx=10)

    def update_beamer_text(self, neuer_text):
        self.ticker.show_message(neuer_text)
        
    def scroll_text(self):
        # Verschiebt den Text um 3 Pixel nach links
        self.ticker_canvas.move(self.text_id, -3, 0)
        
        # Prüfen, ob der Text komplett links aus dem Bild verschwunden ist
        bbox = self.ticker_canvas.bbox(self.text_id)
        if bbox and bbox[2] < 0: 
            # Wieder rechts außerhalb des Bildes anfangen
            self.ticker_canvas.coords(self.text_id, self.beamer_width, 30) 
            
        # Die Funktion ruft sich alle 20 Millisekunden selbst auf
        self.scroll_job = self.after(20, self.scroll_text)            
        
    #AB HIER LIVE TICKER
    def update_live_score(self, p1_points, p2_points, status):
        """Aktualisiert die Live-Punkte und den Status auf dem Beamer."""
        
        # 1. Punktestand immer aktualisieren (sofern physisch noch auf dem Bildschirm vorhanden)
        if p1_points is not None:
            if hasattr(self, 'lbl_score_p1') and self.lbl_score_p1.winfo_exists():
                self.lbl_score_p1.config(text=str(p1_points))
                
        if p2_points is not None:
            if hasattr(self, 'lbl_score_p2') and self.lbl_score_p2.winfo_exists():
                self.lbl_score_p2.config(text=str(p2_points))

        # 2. Status-Logik nach deinem sauberen Workflow (auch hier prüfen, ob das Label existiert)
        if hasattr(self, 'lbl_match_status') and self.lbl_match_status.winfo_exists():
            if status == "SICHERHEIT":
                self.lbl_match_status.config(text="🏁 MATCH BEENDET 🏁", fg="white")
            elif status == "WARTEN":
                # Das senden wir manuell aus der GUI bei "ERGEBNIS ABHOLEN"
                self.lbl_match_status.config(text="Warten auf Start...", fg="gray")
            elif status != "":
                # EGAL welcher andere Status vom Pi kommt (FEUER, LADEN, BEREIT, etc.)
                self.lbl_match_status.config(text="🔥 MATCH LÄUFT 🔥", fg="red")