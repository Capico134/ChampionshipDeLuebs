import os
import datetime
from TurnierLogikDeLuebs import generiere_setzliste
import datetime # <--- WICHTIG: Für den Datums-Fallback!

class HtmlExporter:
    def __init__(self, filename="./savegames/Turnierbericht.html"):
        self.filename = filename

    # --- NEU: meta_daten als Parameter hinzugefügt ---
    def generiere_bericht(self, ergebnisse, spielplan=None, ko_spielplan=None, datei_manager=None, meta_daten=None, silent=False):
        if spielplan is None:
            spielplan = []
        if ko_spielplan is None:
            ko_spielplan = []
        if meta_daten is None:
            meta_daten = {}
            
        os.makedirs(os.path.dirname(self.filename), exist_ok=True)        
        
        stats = [{"n":k, **v} for k,v in ergebnisse.items()]
        if not stats:
            return False, "Keine Daten zum Exportieren vorhanden!"

        # --- DIE INTELLIGENZ (Zustand aus den Daten ablesen) ---
        mit_gruppenuebersicht = any(m.get("gespielt", False) for m in spielplan)
        gruppen_beendet = (bool(spielplan) and all(m.get("gespielt", False) for m in spielplan)) or len(ko_spielplan) > 0
        finale = next((m for m in ko_spielplan if m.get("match_nr") == "FIN"), None)
        spiel_um_platz_3 = next((m for m in ko_spielplan if m.get("match_nr") == "3PL"), None)
        turnier_beendet = finale is not None and finale.get("gespielt") is True

        # =================================================================
        # --- 1. ELA-ERWEITERUNG: TURNIER-DATUM AUS _META ERMITTELN ---
        # =================================================================
        turnier_datum = ""
        
        # 1. Der neue, absolut saubere Weg über _meta
        meta_ts = meta_daten.get("timestamp", "")
        if meta_ts and " " in meta_ts:
            try:
                # "2026-06-14" wird für die deutsche Optik zu "14.06.26"
                dt = datetime.datetime.strptime(meta_ts.split(" ")[0], "%Y-%m-%d")
                turnier_datum = dt.strftime("%d.%m.%y")
            except ValueError:
                pass
                
        # 2. Fallback: Falls _meta doch mal fehlt, schauen wir in alte Spielpläne
        if not turnier_datum:
            for m in spielplan:
                ts = m.get("timestamp", "")
                if ts and len(ts) >= 8:
                    turnier_datum = ts.split(" ")[0]
                    break
        
        # 3. Absoluter Notfall-Fallback
        if not turnier_datum:
            turnier_datum = "-"#datetime.datetime.now().strftime("%d.%m.%y")

        # --- DYNAMISCHER DATEINAME ---
        # Wenn der Dateiname noch auf dem Standard "Turnierbericht.html" steht,
        # formatieren wir ihn um zu "Turnier_YYYY-MM-DD.html"
        if os.path.basename(self.filename) == "Turnierbericht.html":
            try:
                # Wir wandeln "14.06.26" um in das saubere ISO-Format "2026-06-14"
                dt = datetime.datetime.strptime(turnier_datum, "%d.%m.%y")
                iso_datum = dt.strftime("%Y-%m-%d")
                
                # Pfad neu zusammensetzen (behält den Ordner "./savegames/" bei)
                verzeichnis = os.path.dirname(self.filename)
                self.filename = os.path.join(verzeichnis, f"Turnier_{iso_datum}.html")
            except Exception as e:
                print(f"⚠️ Hinweis: Dynamischer Dateiname konnte nicht berechnet werden: {e}")


        # 1. Daten nach Gruppen aufteilen und sortieren
        gruppen_daten = {}
        for s in stats:
            g = s.get("gruppe", "Unbekannt")
            if g not in gruppen_daten:
                gruppen_daten[g] = []
            gruppen_daten[g].append(s)

        for g in gruppen_daten:
            gruppen_daten[g] = sorted(
                gruppen_daten[g], 
                key=lambda x: (x.get("punkte", 0), x.get("differenz", 0), x.get("score_erzielt", 0)), 
                reverse=True
            )

        # --- OPTIMIERUNG (C): Logik für Qualifikanten nach oben gezogen! ---
        virtuelle_setzliste = generiere_setzliste(ergebnisse, gruppen_daten)
        limit = 8 if len(virtuelle_setzliste) > 8 else 4
        qualifiziert = {x["name"] for x in virtuelle_setzliste[:limit]}
        # -------------------------------------------------------------------

        # 3. HTML-Grundgerüst bauen
        html = f"""
        <!DOCTYPE html>
        <html lang="de">
        <head>
            <meta charset="utf-8">
            <meta name="viewport" content="width=850">
            <title>Shooting DeLübs - Turnierbericht</title>
            <meta http-equiv="cache-control" content="no-cache, no-store, must-revalidate">
            <meta http-equiv="pragma" content="no-cache">
            <meta http-equiv="expires" content="0">
            <style>
                body {{ background-color: #111111; color: white; font-family: 'Segoe UI', Arial, sans-serif; padding: 15px; line-height: 1.6; }}
                
                h1 {{ color: #00ff00; text-align: center; font-size: 2.2em; text-transform: uppercase; letter-spacing: 2px; margin-bottom: 5px; }}
                .turnier-datum {{ text-align: center; color: #888888; font-size: 1.1em; margin-bottom: 30px; font-weight: bold; }}
                
                h2 {{ color: #00ff00; border-bottom: 2px solid #333; padding-bottom: 8px; margin-top: 30px; }}
                h3 {{ color: #ffffff; background-color: #333; padding: 10px; margin-bottom: 0; border-top-left-radius: 5px; border-top-right-radius: 5px; }}
                .table-container {{ max-width: 1000px; margin: 0 auto 30px auto; overflow-x: auto; }}
                table {{ width: 100%; border-collapse: collapse; background-color: #222; }}
                th, td {{ border: 1px solid #444; padding: 10px; text-align: center; }}
                th {{ background-color: #2a2a2a; color: #00ff00; font-weight: bold; }}
                tr:nth-child(even) {{ background-color: #262626; }}
                .highlight-gold {{ color: #ffd700; font-weight: normal; }}
                .award-box {{ background-color: #222; max-width: 960px; margin: 20px auto; padding: 15px; border-left: 6px solid #ffcc00; }}
                .award-title {{ color: #ffcc00; margin-top: 0; font-size: 1.3em; }}
                
                /* Podium Styles */
                .podium-container {{ display: flex; justify-content: center; align-items: flex-end; max-width: 1000px; margin: 30px auto 70px auto; height: 180px; gap: 10px; }}
                .podium-step {{ display: flex; flex-direction: column; align-items: center; justify-content: flex-end; width: 30%; color: #000; text-align: center; padding-bottom: 10px; border-top-left-radius: 8px; border-top-right-radius: 8px; box-shadow: 0 -4px 10px rgba(0,0,0,0.5); }}
                .podium-name {{ font-weight: bold; font-size: 0.95em; margin-bottom: -130px; background-color: rgba(0,0,0,0.8); color: white; padding: 4px 10px; border-radius: 4px; border: 2px solid white; }}
                .step-1 {{ background: linear-gradient(to bottom, #FFD700, #B8860B); height: 160px; z-index: 3; }}
                .step-2 {{ background: linear-gradient(to bottom, #E0E0E0, #909090); height: 110px; z-index: 2; }}
                .step-3 {{ background: linear-gradient(to bottom, #CD7F32, #8B4513); height: 70px; z-index: 1; }}
                .podium-medal {{ font-size: 2em; margin-bottom: -5px; }}
                
                .section-block {{ padding: 15px 20px; border-radius: 12px; margin-bottom: 30px; overflow-x: auto; }}
                .bg-light {{ background-color: #2c2c2c; border: 1px solid #333; box-shadow: 0 4px 12px rgba(0,0,0,0.4); }}
                .bg-dark {{ background-color: #181818; border: 1px solid #262626; box-shadow: 0 4px 12px rgba(0,0,0,0.4); }}                
            </style>
        </head>
        <body>
            <h1>🎯 Bericht 🎯</h1>
            <div class="turnier-datum">📅 Turniertag: {turnier_datum}</div>
        """


        # --- NEU: SPIELER-FILTER (JS & DROPDOWN) ---
        alle_spieler = sorted(list(ergebnisse.keys()))
        options_html = "\n".join([f'<option value="{p}">{p}</option>' for p in alle_spieler])
        
        html += f"""
        <div style="text-align: center; margin-bottom: 30px; background: #222; padding: 15px; border-radius: 8px; border: 1px solid #444; max-width: 800px; margin-left: auto; margin-right: auto;">
            <label for="playerSelect" style="color: #00ff00; font-weight: bold; font-size: 1.1em;">🔍 Spieler-Fokus: </label>
            <select id="playerSelect" onchange="highlightPlayer()" style="padding: 8px; background: #111; color: white; border: 1px solid #555; border-radius: 4px; font-size: 1.1em; margin-left: 10px; cursor: pointer;">
                <option value="">-- Gesamte Ansicht --</option>
                {options_html}
            </select>
        </div>

        <script>
        function highlightPlayer() {{
            const sel = document.getElementById('playerSelect').value;
            
            // 1. Gruppentabellen hervorheben
            document.querySelectorAll('.stand-row').forEach(row => {{
                row.style.outline = 'none';
                row.style.backgroundColor = row.dataset.origbg || '';
                
                if(sel && row.dataset.player === sel) {{
                    if(!row.dataset.origbg) row.dataset.origbg = row.style.backgroundColor;
                    row.style.outline = '2px solid #ffd700';
                    row.style.backgroundColor = 'rgba(255, 215, 0, 0.15)';
                }}
            }});

            // 2. Einzelne Matches (Namen & Punkte) hervorheben
            document.querySelectorAll('.match-row').forEach(row => {{
                row.querySelectorAll('.hl-target').forEach(el => {{
                    el.style.color = el.dataset.origcol || '';
                    el.style.textShadow = 'none';
                    el.style.backgroundColor = 'transparent';
                }});
                
                if(!sel) return;

                if(row.dataset.p1 === sel) {{
                    row.querySelectorAll('.p1-hl').forEach(el => {{
                        if(!el.dataset.origcol) el.dataset.origcol = el.style.color || 'inherit';
                        el.style.color = '#000000'; // Text wird schwarz
                        el.style.backgroundColor = '#ffd700'; // Hintergrund wird gold
                        el.style.padding = '1px 5px'; // Ein bisschen Luft links und rechts
                        el.style.borderRadius = '4px'; // Abgerundete Ecken
                        el.style.textShadow = 'none'; // Schatten komplett aus
                    }});
                }}
                if(row.dataset.p2 === sel) {{
                    row.querySelectorAll('.p2-hl').forEach(el => {{
                        if(!el.dataset.origcol) el.dataset.origcol = el.style.color || 'inherit';
                        el.style.color = '#000000'; // Text wird schwarz
                        el.style.backgroundColor = '#ffd700'; // Hintergrund wird gold
                        el.style.padding = '1px 5px'; // Ein bisschen Luft links und rechts
                        el.style.borderRadius = '4px'; // Abgerundete Ecken
                        el.style.textShadow = 'none'; // Schatten komplett aus     
                    }});
                }}
            }});
        }}
        </script>
        """



        # PROJEKT-HEADER
        html += """
        <div style="text-align: center; background-color: #252525; padding: 20px; border-radius: 15px; margin: 20px auto; max-width: 760px; border: 2px solid #39FF14;">
            <h2 style="color: #39FF14; margin-top: 0; margin-bottom: 5px; border: none; padding: 0;">Shooting DeLübs</h2>
            <p style="color: #cccccc; font-size: 16px; margin-top: 0; margin-bottom: 15px;">Das Open-Source Meisterschafts-System für Schützen</p>
            
            <div style="display: flex; justify-content: center; gap: 15px; flex-wrap: wrap;">
                <a href="https://github.com/Capico134/ShootingDeLuebs" target="_blank" 
                   style="color: white; text-decoration: none; background: #333; padding: 8px 15px; border-radius: 8px; border: 1px solid #555;">
                   🛠️ GitHub
                </a>
                <a href="https://youtube.com/@DeLuebs" target="_blank" 
                   style="color: white; text-decoration: none; background: #c4302b; padding: 8px 15px; border-radius: 8px;">
                   📺 YouTube
                </a>
                <a href="https://DeLuebs.de" target="_blank" 
                   style="color: white; text-decoration: none; background: #0056b3; padding: 8px 15px; border-radius: 8px;">
                   🌐 Homepage
                </a>
            </div>
        </div>
        """

        # 4. Der Kopfbereich (Podium oder normaler Untertitel)
        if turnier_beendet:
            winner = finale.get("winner", "Unbekannt")
            loser = finale.get("loser", "Unbekannt") 
            platz3 = spiel_um_platz_3.get("winner", "Unbekannt") if spiel_um_platz_3 else "---"

            html += f"""
            <p style="text-align: center; color: #ffd700; font-size: 1.5em; font-weight: bold; margin-top: 0;">🏆 ENDSTAND MEISTERSCHAFT 🏆</p>
            
            <div class="podium-container">
                <div class="podium-step step-2">
                    <div class="podium-name">{loser}</div>
                    <div class="podium-medal">🥈</div>
                    <strong>2. Platz</strong>
                </div>
                <div class="podium-step step-1">
                    <div class="podium-name">{winner}</div>
                    <div class="podium-medal">🥇</div>
                    <strong>1. Platz</strong>
                </div>
                <div class="podium-step step-3">
                    <div class="podium-name">{platz3}</div>
                    <div class="podium-medal">🥉</div>
                    <strong>3. Platz</strong>
                </div>
            </div>
            """
        else:
            html += """
            <p style="text-align: center; color: #aaa; margin-top: 0;">Aktuelle Tabellenstände und Platzierungen</p>
            """

        # --- DER AUTOMATISCHE FARB-SCHALTER ---
        use_light_bg = True
        def get_section_start():
            nonlocal use_light_bg
            cls = "bg-light" if use_light_bg else "bg-dark"
            use_light_bg = not use_light_bg
            return f'<div class="section-block {cls}">'
        
        # =================================================================
        # --- NEU: SMARTE MODUS-ERKENNUNG FÜR DEN BERICHT ---
        # =================================================================
        # 1. Sind wir im Derby? (Wenn alle Spiele in der Gruppe "Derby" sind)
        is_derby = bool(spielplan and all(m.get("gruppe") == "Derby" for m in spielplan))
        
        # 2. Was ist das Haupt-Programm? (Für normale Turniere)
        haupt_programm = ""
        if spielplan:
            for m in spielplan:
                if m.get("programm_name") and m.get("programm_name") != "-":
                    haupt_programm = m.get("programm_name")
                    break
        # =================================================================
        
        # 5. GRUPPENÜBERSICHT
        if mit_gruppenuebersicht:
            html += get_section_start()
            if is_derby:
                html += "<h2>📊 Derby-Statistik</h2>"
            else:
                html += "<h2>📊 Die Gruppenphase</h2>"
            
            for gruppe in sorted(gruppen_daten.keys()):
                html += f"""
                <div class="table-container">
                    <h3>GRUPPE {gruppe}</h3>
                    <table>
                        <tr>
                            <th>Platz</th>
                            <th style="text-align: left;">Name</th>
                            <th>Spiele</th>
                            <th>Turnierpunkte</th>
                            <th>Diff</th>
                            <th>Gesamtleistung</th>
                        </tr>
                """
                
                for i, s in enumerate(gruppen_daten[gruppe]):
                    ist_qualifiziert = gruppen_beendet and s['n'] in qualifiziert
                    rang_text = f"<strong>{i+1}. Q</strong>" if ist_qualifiziert else f"<strong>{i+1}.</strong>"
                    row_bg = "background-color: rgba(0, 255, 0, 0.12);" if ist_qualifiziert else ""
                    rang_color = "#00ff00" if ist_qualifiziert else "inherit"
                    
                    html += f"""
                        <tr class="stand-row" data-player="{s['n']}" style="{row_bg}">
                            <td style="color: {rang_color};">{rang_text}</td>
                            <td style="text-align: left;"><strong>{s['n']}</strong></td>
                            <td>{s.get('spiele', 0)}</td>
                            <td style="color: #00ff00; font-weight: bold;">{s.get('punkte', 0)}</td>
                            <td style="color: #ffffff;">{s.get('differenz', 0):+.2f}</td>
                            <td class="highlight-gold">{s.get('score_erzielt', 0):.2f}</td>
                        </tr>
                    """
                html += """
                    </table>
                </div>
                """
            html += "</div>"


        # 6. EINZELNE GRUPPENSPIELE
        if spielplan: 
            html += get_section_start()
            
            # --- NEU: Dynamische Überschrift ---
            if is_derby:
                html += "<h2>⚔️ Alle Derby-Spiele</h2>"
            else:
                prog_zusatz = f" <span style='font-size: 1em; color: #ffffff; font-weight: normal;'>{haupt_programm}</span>" if haupt_programm else ""
                html += f"<h2>⚔️ Alle Gruppenspiele{prog_zusatz}</h2>"
                
            html += """
            <div class="table-container">
                <table>
                    <tr style="border-bottom: 2px solid #00ff00;">
                        <th>Nr.</th>
                        <th>Zeit</th>
            """
            
            # --- NEU: Dynamische Spalte "Grp" vs "Programm" ---
            if is_derby:
                html += "            <th style='min-width: 110px;'>Programm</th>\n"
            else:
                html += "            <th>Grp</th>\n"
                
            html += """
                        <th style="text-align: left;">Paarung</th>
                        <th>Turnierpunkte</th>
                        <th style='min-width: 70px;'>Treffer</th>
                        <th style='min-width: 95px;'>Match-Wertung</th>
                        </tr>
            """
            letzte_gruppe = None
            
            for m in spielplan:
                aktuelle_gruppe = m.get('gruppe', '-')
                
                if letzte_gruppe is not None and aktuelle_gruppe != letzte_gruppe:
                    tr_style = ' style="border-top: 2px solid #777;"'
                else:
                    tr_style = ''
                    
                letzte_gruppe = aktuelle_gruppe 
                
                if m.get("gespielt"):
                    # 1. Versuch: Die neue, echte Startzeit ("23:47:51")
                    start_z = m.get("start_zeit", "")
                    if start_z:
                        uhrzeit = start_z[:5] # Nimm einfach die ersten 5 Zeichen ("23:47")
                    else:
                        # 2. Fallback für alte Matches: Den Timestamp ("14.06.26 20:24:00") zerteilen
                        ts = m.get("timestamp", "")
                        uhrzeit = ts.split(" ")[1][:5] if (ts and " " in ts) else "--:--"

                    b1, b2 = m.get('base1', 0), m.get('base2', 0)
                    
                    # Werte in SPANs einpacken, damit JS sie links/rechts färben kann
                    treffer = f"<span class='hl-target p1-hl'>{b1}</span> : <span class='hl-target p2-hl'>{b2}</span>"
                    gesamt = f"<span class='hl-target p1-hl'>{m.get('total1', 0):.2f}</span> : <span class='hl-target p2-hl'>{m.get('total2', 0):.2f}</span>"
                    prog_name = m.get("programm_name", "-")
                    
                    if b1 > b2: p1_tp, p2_tp = "3", "0"
                    elif b1 < b2: p1_tp, p2_tp = "0", "3"
                    else: p1_tp, p2_tp = "1", "1"
                    t_punkte = f"<span class='hl-target p1-hl'>{p1_tp}</span> : <span class='hl-target p2-hl'>{p2_tp}</span>"
                    
                else:
                    uhrzeit = "--:--"
                    treffer = "- : -"
                    gesamt = "- : -"
                    t_punkte = "- : -"
                    prog_name = "-"

                html += f"""
                    <tr class="match-row" data-p1="{m.get('spieler1', '')}" data-p2="{m.get('spieler2', '')}"{tr_style}>
                        <td style="color: #ffffff;">{m.get('match_nr', '-')}</td>
                        <td style="color: #888888; font-weight: 500;">{uhrzeit}</td>
                """
                
                # --- Modus-abhängige Zelle ---
                if is_derby:
                    html += f'        <td style="color: #ffffff;">{prog_name}</td>\n'
                else:
                    html += f'        <td style="color: #ffffff;">{aktuelle_gruppe}</td>\n'

                html += f"""
                        <td style="text-align: left;"><strong><span class="hl-target p1-hl">{m.get('spieler1', '')}</span></strong> vs. <strong><span class="hl-target p2-hl">{m.get('spieler2', '')}</span></strong></td>
                        <td style="color: #00ff00; font-weight: bold;">{t_punkte}</td>
                        <td style="color: #ffffff; font-weight: bold;">{treffer}</td>
                        <td style="color: #ffd700;">{gesamt}</td>
                    </tr>
                """
            html += """
                </table>
            </div>
            """
            html += "</div>"


    # 7. DIE K.O.-PHASE
        if ko_spielplan: 
            html += get_section_start() 
            html += "<h2>🏆 Die K.O.-Phase</h2>"
            html += """
            <div class="table-container">
                <table>
                    <tr style="border-bottom: 2px solid #00ff00;">
                        <th>Phase</th>
                        <th>Zeit</th>
                        <th>Programm</th>
                        <th style="text-align: left;">Paarung</th>
                        <th>Match-Wertung</th>
                        <th>Treffer</th>
                        <th>Sieger</th>
                    </tr>
            """
            for m in ko_spielplan:
                match_nr = m.get('match_nr', '')
                phase = datei_manager.get_match_name(match_nr) if datei_manager else match_nr
                
                paarung = f"<strong><span class='hl-target p1-hl'>{m.get('spieler1', '')}</span></strong> vs. <strong><span class='hl-target p2-hl'>{m.get('spieler2', '')}</span></strong>"
                
                if m.get("gespielt"):
                    # 1. Versuch: Die neue, echte Startzeit ("23:47:51")
                    start_z = m.get("start_zeit", "")
                    if start_z:
                        uhrzeit = start_z[:5] 
                    else:
                        ts = m.get("timestamp", "")
                        uhrzeit = ts.split(" ")[1][:5] if (ts and " " in ts) else "--:--"

                    treffer = f"<span class='hl-target p1-hl'>{m.get('base1', 0)}</span> : <span class='hl-target p2-hl'>{m.get('base2', 0)}</span>"
                    gesamt = f"<span class='hl-target p1-hl'>{m.get('total1', 0):.2f}</span> : <span class='hl-target p2-hl'>{m.get('total2', 0):.2f}</span>"
                    
                    sieger = f"<span class='highlight-gold'>🏆 {m.get('winner', '')}</span>"
                else:
                    uhrzeit = "--:--"
                    treffer = "- : -"
                    gesamt = "- : -"
                    sieger = "---"
                    prog_name = "-"

                html += f"""
                    <tr class="match-row" data-p1="{m.get('spieler1', '')}" data-p2="{m.get('spieler2', '')}">
                        <td style="color: #ffffff;">{phase}</td>
                        <td style="color: #888888; font-weight: 500;">{uhrzeit}</td>
                        <td style="color: #ffffff;">{prog_name}</td>
                        <td style="text-align: left;">{paarung}</td>
                        <td style="color: #00ff00; font-weight: bold;">{gesamt}</td>
                        <td style="color: #ffffff;">{treffer}</td>
                        <td>{sieger}</td>
                    </tr>
                """
            html += """
                </table>
            </div>
            """
            html += "</div>"


        # 8. SONDERWERTUNGEN
        if gruppen_beendet:
            html += "<h2 style='border-bottom: none; border-top: 2px solid #333; padding-top: 20px; margin-top: 40px;'>⭐ Sonderwertungen</h2>"
            
            html += get_section_start()
            html += "<h3 style='background-color: transparent; color: #00ff00; border-bottom: 1px solid #333; margin-top: 10px; padding-left: 0;'>🎖️ GRUPPENPHASE</h3>"
            
            # ==========================================
            # SETZLISTE FÜR DIE K.O.-PHASE
            # ==========================================
            html += """
                <div class="table-container">
                    <h3 style="background-color: #1a3a1a; border-bottom: 1px solid #00ff00; color: #00ff00; font-size: 1.1em; padding: 8px;">✅ Die finale Setzliste (Qualifikanten)</h3>
                    <table>
                        <tr>
                            <th>Setzplatz</th>
                            <th style="text-align: left;">Schütze</th>
                            <th>Grp.</th>
                            <th>Turnierpunkte</th>
                            <th>Diff</th>
                            <th>Gesamtleistung</th>
                        </tr>
            """
            for i, q in enumerate(virtuelle_setzliste[:limit]):
                html += f"""
                    <tr style="background-color: rgba(0, 255, 0, 0.08);">
                        <td style="color: #00ff00;"><strong>{i+1}.</strong></td>
                        <td style="text-align: left;"><strong>{q['name']}</strong></td>
                        <td>{q.get('gruppe', '-')}</td>
                        <td style="color: #00ff00; font-weight: bold;">{q.get('punkte', 0)}</td>
                        <td style="color: #ffffff;">{q.get('differenz', 0):+.2f}</td>
                        <td class="highlight-gold">{q.get('score_erzielt', 0):.2f}</td>
                    </tr>
                """
            html += """
                    </table>
                </div>
            """

            spieler_scores = {}
            for match in spielplan:
                if match.get("gespielt"):
                    if match.get("pi_match_id") == "MANUELL" and match.get("total1", 0) == 0 and match.get("total2", 0) == 0:
                        continue
                        
                    p1, p2 = match.get("spieler1"), match.get("spieler2")
                    s1, s2 = match.get("total1", 0), match.get("total2", 0)
                    
                    if p1: spieler_scores.setdefault(p1, []).append(s1)
                    if p2: spieler_scores.setdefault(p2, []).append(s2)

            # --- 1. PECHVOGEL ---
            ausgeschiedene = [s for s in stats if s["n"] not in qualifiziert]
            if ausgeschiedene:
                max_pech_score = max([round(s.get("score_erzielt", 0), 2) for s in ausgeschiedene])
                pechvoegel = [s["n"] for s in ausgeschiedene if round(s.get("score_erzielt", 0), 2) == max_pech_score]
                namen_str = " & ".join([f"<strong>{n}</strong>" for n in pechvoegel])
                
                html += f"""
                <div class="award-box">
                    <h3 class="award-title">🍀 Der "Pechvogel des Tages"</h3>
                    <p>Der Sonderpreis der Herzen geht an {namen_str}!<br>
                    Trotz einer bärenstarken <span class="highlight-gold">Gesamtleistung von {max_pech_score:.2f}</span> hat es in einer gnadenlosen Gruppe leider nicht für den Einzug in die K.O.-Phase gereicht. Das ist wahres Pech!</p>
                </div>
                """

            # --- 2. UHRWERK ---
            uhrwerk_kandidaten = []
            for s in stats:
                name = s["n"]
                scores = spieler_scores.get(name, [])
                if len(scores) > 1:
                    min_score = round(min(scores), 2)
                    max_score = round(max(scores), 2)
                    if max_score > 0:
                        schwankung = round(max_score - min_score, 2)
                        uhrwerk_kandidaten.append((name, schwankung, min_score, max_score))
            
            if uhrwerk_kandidaten:
                best_schwankung = min([k[1] for k in uhrwerk_kandidaten])
                sieger_uhrwerk = [k for k in uhrwerk_kandidaten if k[1] == best_schwankung]
                
                html += f"""
                <div class="award-box">
                    <h3 class="award-title">⏱️ Das "Uhrwerk"</h3>
                    <p>Präzise wie ein Schweizer Uhrwerk! Die konstanteste Leistung des Tages mit einer minimalen Differenz von nur <span class="highlight-gold">{best_schwankung:.2f} in der Match-Wertung</span>:</p>
                    <ul style="list-style-type: none; padding-left: 0;">
                """
                for (name, schwankung, min_s, max_s) in sieger_uhrwerk:
                    html += f"<li style='margin-bottom: 5px;'><strong>{name}</strong> <em>({min_s:.2f} bis {max_s:.2f})</em></li>"
                html += "</ul></div>"

            # --- 3. SPÄTZÜNDER ---
            spaetzuender_kandidaten = []
            for s in stats:
                name = s["n"]
                scores = spieler_scores.get(name, [])
                if len(scores) > 1:
                    erstes_match = round(scores[0], 2)
                    letztes_match = round(scores[-1], 2)
                    
                    steigerung = round(letztes_match - erstes_match, 2)
                    if steigerung > 0: 
                        spaetzuender_kandidaten.append((name, steigerung, erstes_match, letztes_match))

            if spaetzuender_kandidaten:
                best_steigerung = max([k[1] for k in spaetzuender_kandidaten])
                sieger_spaet = [k for k in spaetzuender_kandidaten if k[1] == best_steigerung]
                
                html += f"""
                <div class="award-box">
                    <h3 class="award-title">🚀 Der "Spätzünder"</h3>
                    <p>Der Preis für das größte Comeback!<br>
                    Mit einer gewaltigen Leistungssteigerung von <span class="highlight-gold">{best_steigerung:.2f} in der Match-Wertung</span> vom ersten bis zum letzten Gruppenspiel:</p>
                    <ul style="list-style-type: none; padding-left: 0;">
                """
                for (name, steigerung, start, best) in sieger_spaet:
                    html += f"<li style='margin-bottom: 5px;'><strong>{name}</strong> <em>(gesteigert von {start:.2f} auf {best:.2f})</em></li>"
                html += "</ul></div>"

            # --- TOP 5 TABELLE ---
            ehrentafel = sorted(stats, key=lambda x: x.get("score_erzielt", 0), reverse=True)
            
            html += """
                <div class="table-container">
                    <h3 style="background-color: #222; border-bottom: 1px solid #444; color: #aaa; font-size: 1em; padding: 5px;">Top 5 - Die stärkste Gesamtleistung</h3>
                    <table>
                        <tr><th>Rang</th><th style="text-align: left;">Schütze</th><th>Turnierpunkte</th><th>Gesamtleistung</th></tr>
            """
            for i, s in enumerate(ehrentafel[:5]):
                rang_icon = "🥇" if i == 0 else "🥈" if i == 1 else "🥉" if i == 2 else f"{i+1}."
                html += f"""
                    <tr>
                        <td><strong>{rang_icon}</strong></td>
                        <td style="text-align: left;"><strong>{s['n']}</strong></td>
                        <td>{s.get('punkte', 0)}</td>
                        <td class="highlight-gold">{s.get('score_erzielt', 0):.2f}</td>
                    </tr>
                """
            html += """
                    </table>
                </div>
            """
            html += "</div>"


            # ==========================================
            # K.O.-PHASE (Fotofinish & Nerven aus Stahl)
            # ==========================================
            fotofinish_matches = []
            min_diff = float('inf')
            
            nerven_spieler = []
            max_ko_score = -1.0

        if turnier_beendet:
            if ko_spielplan:
                for match in ko_spielplan:
                    if match.get("gespielt"):
                        if match.get("pi_match_id") == "MANUELL" and match.get("total1", 0) == 0 and match.get("total2", 0) == 0:
                            continue
                            
                        t1 = match.get("total1", 0.0)
                        t2 = match.get("total2", 0.0)
                        p1 = match.get("spieler1", "Unbekannt")
                        p2 = match.get("spieler2", "Unbekannt")
                        match_nr = match.get("match_nr", "")
                        phase = datei_manager.get_match_name(match_nr) if datei_manager else match_nr
                        
                        diff = round(abs(t1 - t2), 3)
                        if diff < min_diff:
                            min_diff = diff
                            fotofinish_matches = [(p1, p2, t1, t2, diff, phase)]
                        elif diff == min_diff:
                            fotofinish_matches.append((p1, p2, t1, t2, diff, phase))
                            
                        for score, player in [(round(t1, 2), p1), (round(t2, 2), p2)]:
                            if score > max_ko_score:
                                max_ko_score = score
                                nerven_spieler = [(player, phase)]
                            elif score == max_ko_score:
                                nerven_spieler.append((player, phase))

            if fotofinish_matches or nerven_spieler:
                html += get_section_start()
                html += "<h3 style='background-color: transparent; color: #00ff00; border-bottom: 1px solid #333; margin-top: 10px; padding-left: 0;'>🎖️ K.O.-PHASE</h3>"
                
                if fotofinish_matches:
                    html += f"""
                    <div class="award-box" style="border-left-color: #ff3333;">
                        <h3 class="award-title" style="color: #ff3333;">📸 Das Fotofinish</h3>
                        <p>Das dramatischste Duell auf Messers Schneide!<br>
                        Mit unfassbaren <span style="color: #ff3333; font-weight: bold;">{min_diff:.2f}</span> Unterschied in der Match-Wertung trennten sich:</p>
                        <ul style="list-style-type: none; padding-left: 0;">
                    """
                    for (p1, p2, t1, t2, diff, phase) in fotofinish_matches:
                        html += f"<li style='margin-bottom: 5px;'><strong>{p1}</strong> ({t1:.2f}) vs <strong>{p2}</strong> ({t2:.2f}) <em>(im {phase})</em></li>"
                    html += "</ul></div>"
                    
                if nerven_spieler and max_ko_score > 0:
                    html += f"""
                    <div class="award-box" style="border-left-color: #00ccff;">
                        <h3 class="award-title" style="color: #00ccff;">🧊 Nerven aus Stahl</h3>
                        <p>Wer behält die absolute Ruhe, wenn es um alles geht? <br>
                        Die höchste Match-Wertung im gnadenlosen K.O.-Modus (mit sensationellen <span style="color: #00ccff; font-weight: bold;">{max_ko_score:.2f}</span>) stammt von:</p>
                        <ul style="list-style-type: none; padding-left: 0;">
                    """
                    for (name, phase) in nerven_spieler:
                        html += f"<li style='margin-bottom: 5px;'><strong>{name}</strong> <em>(geschossen im {phase})</em></li>"
                    html += "</ul></div>"
                    
                html += "</div>"
                    
        html += """
        </body>
        </html>
        """

        try:
            with open(self.filename, "w", encoding="utf-8") as f:
                f.write(html)
            
            # Für die Erfolgsmeldung isolieren wir den reinen Dateinamen (z.B. Turnier_2026-06-14.html)
            reiner_dateiname = os.path.basename(self.filename)

            if not silent and os.name == 'nt':
                absoluter_pfad = os.path.abspath(self.filename)
                os.startfile(absoluter_pfad)
                
            return True, f"Der Bericht wurde erfolgreich erstellt!\n\nDatei: savegames/{reiner_dateiname}\n\nDu kannst ihn jetzt öffnen und in WhatsApp teilen."
        except Exception as e:
            return False, f"Fehler beim Speichern oder Öffnen:\n{e}"