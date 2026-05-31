import os

class HtmlExporter:
    def __init__(self, filename="./savegames/Turnierbericht.html"):
        self.filename = filename

    def generiere_bericht(self, ergebnisse, spielplan=None, ko_spielplan=None, datei_manager=None, silent=False):
        if spielplan is None:
            spielplan = []
        if ko_spielplan is None:
            ko_spielplan = []
            
        os.makedirs(os.path.dirname(self.filename), exist_ok=True)        
        
        stats = [{"n":k, **v} for k,v in ergebnisse.items()]
        if not stats:
            return False, "Keine Daten zum Exportieren vorhanden!"

        # --- NEU: DIE INTELLIGENZ (Zustand aus den Daten ablesen) ---
        
        # Überprüfen, ob überhaupt schon ein einziges Spiel absolviert wurde
        mit_gruppenuebersicht = any(m.get("gespielt", False) for m in spielplan)
        # Sind ALLE Gruppenspiele gespielt?
        gruppen_beendet = bool(spielplan) and all(m.get("gespielt", False) for m in spielplan)
        # Ist das Finale gespielt?
        finale = next((m for m in ko_spielplan if m.get("match_nr") == "FIN"), None)
        spiel_um_platz_3 = next((m for m in ko_spielplan if m.get("match_nr") == "3PL"), None)
        turnier_beendet = finale is not None and finale.get("gespielt") is True
        # -------------------------------------------------------------

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

        ## 2. Prüfen, ob das Turnier (Finale) beendet ist
        #finale = next((m for m in ko_spielplan if m.get("match_nr") == "FIN"), None)
        #spiel_um_platz_3 = next((m for m in ko_spielplan if m.get("match_nr") == "3PL"), None)
        #turnier_beendet = finale is not None and finale.get("gespielt") is True

        # 3. HTML-Grundgerüst bauen
        html = """
        <!DOCTYPE html>
        <html lang="de">
        <head>
            <meta charset="utf-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Shooting DeLübs - Turnierbericht</title>
            <meta http-equiv="cache-control" content="no-cache, no-store, must-revalidate">
            <meta http-equiv="pragma" content="no-cache">
            <meta http-equiv="expires" content="0">
            <style>
                body { background-color: #1a1a1a; color: white; font-family: 'Segoe UI', Arial, sans-serif; padding: 15px; line-height: 1.6; }
                h1 { color: #00ff00; text-align: center; font-size: 2.2em; text-transform: uppercase; letter-spacing: 2px; margin-bottom: 5px; }
                h2 { color: #00ff00; border-bottom: 2px solid #333; padding-bottom: 8px; margin-top: 30px; }
                h3 { color: #ffffff; background-color: #333; padding: 10px; margin-bottom: 0; border-top-left-radius: 5px; border-top-right-radius: 5px; }
                .table-container { max-width: 800px; margin: 0 auto 30px auto; }
                table { width: 100%; border-collapse: collapse; background-color: #222; }
                th, td { border: 1px solid #444; padding: 10px; text-align: center; }
                th { background-color: #2a2a2a; color: #00ff00; font-weight: bold; }
                tr:nth-child(even) { background-color: #262626; }
                .highlight-gold { color: #ffd700; font-weight: bold; }
                .award-box { background-color: #222; max-width: 760px; margin: 20px auto; padding: 15px; border-left: 6px solid #ffcc00; }
                .award-title { color: #ffcc00; margin-top: 0; font-size: 1.3em; }
                
                /* Podium Styles */
                .podium-container { display: flex; justify-content: center; align-items: flex-end; max-width: 800px; margin: 30px auto 70px auto; height: 180px; gap: 10px; }
                .podium-step { display: flex; flex-direction: column; align-items: center; justify-content: flex-end; width: 30%; color: #000; text-align: center; padding-bottom: 10px; border-top-left-radius: 8px; border-top-right-radius: 8px; box-shadow: 0 -4px 10px rgba(0,0,0,0.5); }
                .podium-name { font-weight: bold; font-size: 0.95em; margin-bottom: -130px; background-color: rgba(0,0,0,0.8); color: white; padding: 4px 10px; border-radius: 4px; border: 2px solid white; }
                .step-1 { background: linear-gradient(to bottom, #FFD700, #B8860B); height: 160px; z-index: 3; }
                .step-2 { background: linear-gradient(to bottom, #E0E0E0, #909090); height: 110px; z-index: 2; }
                .step-3 { background: linear-gradient(to bottom, #CD7F32, #8B4513); height: 70px; z-index: 1; }
                .podium-medal { font-size: 2em; margin-bottom: -5px; }
            </style>
        </head>
        <body>
            <h1>🎯 Bericht 🎯</h1>
        """

        # ---> NEUER BLOCK START: PROJEKT-HEADER <---
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
        # ---> NEUER BLOCK ENDE <---

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

        # 5. GRUPPENÜBERSICHT
        if mit_gruppenuebersicht:
            html += "<h2>📊 Die Gruppenphase</h2>"
            
            for gruppe in sorted(gruppen_daten.keys()):
                html += f"""
                <div class="table-container">
                    <h3>GRUPPE {gruppe}</h3>
                    <table>
                        <tr>
                            <th>Pl.</th>
                            <th style="text-align: left;">Name</th>
                            <th>Sp</th>
                            <th>Pkt</th>
                            <th>Diff</th>
                            <th>Gesamt</th>
                        </tr>
                """
                
                for i, s in enumerate(gruppen_daten[gruppe]):
                    html += f"""
                        <tr>
                            <td><strong>{i+1}.</strong></td>
                            <td style="text-align: left;"><strong>{s['n']}</strong></td>
                            <td>{s.get('spiele', 0)}</td>
                            <td style="color: #00ff00; font-weight: bold;">{s.get('punkte', 0)}</td>
                            <td style="color: #aaa;">{s.get('differenz', 0):+.2f}</td>
                            <td class="highlight-gold">{s.get('score_erzielt', 0):.2f}</td>
                        </tr>
                    """
                html += """
                    </table>
                </div>
                """
        # 6. EINZELNE GRUPPENSPIELE
        if spielplan: #mit_gruppenmatches and 
            html += "<h2>⚔️ Alle Gruppenspiele</h2>"
            html += """
            <div class="table-container">
                <table>
                    <tr>
                        <th>Nr.</th>
                        <th>Grp</th>
                        <th style="text-align: left;">Paarung</th>
                        <th>Trf</th>
                        <th>Match-Wertung</th>
                    </tr>
            """
            for m in spielplan:
                # Prüfen, ob das Spiel schon absolviert wurde
                if m.get("gespielt"):
                    treffer = f"{m.get('base1', 0)} : {m.get('base2', 0)}"
                    gesamt = f"{m.get('total1', 0):.2f} : {m.get('total2', 0):.2f}"
                else:
                    treffer = "- : -"
                    gesamt = "- : -"

                html += f"""
                    <tr>
                        <td style="color: #aaa;">{m.get('match_nr', '-')}</td>
                        <td style="color: #aaa;">{m.get('gruppe', '-')}</td>
                        <td style="text-align: left;"><strong>{m.get('spieler1', '')}</strong> vs. <strong>{m.get('spieler2', '')}</strong></td>
                        <td style="color: #00ff00; font-weight: bold;">{treffer}</td>
                        <td style="color: #aaa;">{gesamt}</td>
                    </tr>
                """
            html += """
                </table>
            </div>
            """

        # 7. DIE K.O.-PHASE
        if ko_spielplan: 
            html += "<h2>🏆 Die K.O.-Phase</h2>"
            html += """
            <div class="table-container">
                <table>
                    <tr>
                        <th>Phase</th>
                        <th style="text-align: left;">Paarung</th>
                        <th>Trf</th>
                        <th>Match-Wertung</th>
                        <th>Sieger</th>
                    </tr>
            """
            for m in ko_spielplan:
                # --- ELA FIX: Den Übersetzer fragen! ---
                match_nr = m.get('match_nr', '')
                phase = datei_manager.get_match_name(match_nr) if datei_manager else match_nr
                
                paarung = f"<strong>{m.get('spieler1', '')}</strong> vs. <strong>{m.get('spieler2', '')}</strong>"
                
                if m.get("gespielt"):
                    treffer = f"{m.get('base1', 0)} : {m.get('base2', 0)}"
                    gesamt = f"{m.get('total1', 0):.2f} : {m.get('total2', 0):.2f}"
                    
                    # --- ELA: Stechen-Ergebnis als Unterzeile hinzufügen ---
                    if m.get("stechen_beendet"):
                        stechen_str = f"{m.get('stechen_b1', 0)}:{m.get('stechen_b2', 0)}"
                        gesamt += f"<br><small style='color: #ffd700;'>(ST: {stechen_str})</small>"
                    # -------------------------------------------------------
                    
                    sieger = f"<span class='highlight-gold'>🏆 {m.get('winner', '')}</span>"
                else:
                    treffer = "- : -"
                    gesamt = "- : -"
                    sieger = "---"

                html += f"""
                    <tr>
                        <td style="color: #aaa;">{phase}</td>
                        <td style="text-align: left;">{paarung}</td>
                        <td style="color: #00ff00; font-weight: bold;">{treffer}</td>
                        <td style="color: #aaa;">{gesamt}</td>
                        <td>{sieger}</td>
                    </tr>
                """
            html += """
                </table>
            </div>
            """

        # 8. SONDERWERTUNGEN
        if gruppen_beendet:
            html += "<h2>⭐ Sonderwertungen</h2>"
            
            # ==========================================
            # TEIL 1: GRUPPENPHASE
            # ==========================================
            html += "<h3 style='background-color: transparent; color: #00ff00; border-bottom: 1px solid #333; margin-top: 10px; padding-left: 0;'>🎖️ GRUPPENPHASE</h3>"
            
            spieler_scores = {}
            for match in spielplan:
                if match.get("gespielt"):
                    # WICHTIG: Manuell genullte / übersprungene Matches ignorieren!
                    if match.get("pi_match_id") == "MANUELL" and match.get("total1", 0) == 0 and match.get("total2", 0) == 0:
                        continue
                        
                    p1, p2 = match.get("spieler1"), match.get("spieler2")
                    s1, s2 = match.get("total1", 0), match.get("total2", 0)
                    
                    if p1: spieler_scores.setdefault(p1, []).append(s1)
                    if p2: spieler_scores.setdefault(p2, []).append(s2)

            # --- 1. PECHVOGEL ---
            ehrentafel = sorted(stats, key=lambda x: x.get("score_erzielt", 0), reverse=True)
            min_punkte = min([s.get("punkte", 0) for s in stats]) if stats else 0
            kandidaten = [s for s in stats if s.get("punkte", 0) == min_punkte]
            
            if kandidaten:
                max_pech_score = max([s.get("score_erzielt", 0) for s in kandidaten])
                # Sammle alle Spieler, die genau diesen Max-Score (bei wenigsten Punkten) haben
                pechvoegel = [s["n"] for s in kandidaten if s.get("score_erzielt", 0) == max_pech_score]
                namen_str = " & ".join([f"<strong>{n}</strong>" for n in pechvoegel])
                
                html += f"""
                <div class="award-box">
                    <h3 class="award-title">🍀 Der "Pechvogel des Tages"</h3>
                    <p>Der Sonderpreis der Herzen geht an {namen_str}!<br>
                    Viel Pech führte zu nur {min_punkte} Turnierpunkten in der Gruppenphase. Dennoch wurde eine bärenstarke <span class="highlight-gold">Gesamtleistung von {max_pech_score:.2f}</span> abgeliefert.</p>
                </div>
                """

            # --- 2. UHRWERK (Geringste Schwankung) ---
            uhrwerk_kandidaten = []
            for s in stats:
                name = s["n"]
                scores = spieler_scores.get(name, [])
                if len(scores) > 1:
                    # FIX: Wir runden die Basiswerte ZUERST auf 2 Stellen!
                    min_score = round(min(scores), 2)
                    max_score = round(max(scores), 2)
                    
                    # Jetzt rechnet er mit den exakt gleichen Zahlen, die auch der Leser sieht
                    schwankung = round(max_score - min_score, 2)
                    
                    uhrwerk_kandidaten.append((name, schwankung, min_score, max_score))
            
            if uhrwerk_kandidaten:
                best_schwankung = min([k[1] for k in uhrwerk_kandidaten])
                # Wir holen uns alle Sieger inklusive ihrer Detail-Werte
                sieger_uhrwerk = [k for k in uhrwerk_kandidaten if k[1] == best_schwankung]
                
                html += f"""
                <div class="award-box">
                    <h3 class="award-title">⏱️ Das "Uhrwerk"</h3>
                    <p>Präzise wie ein Schweizer Uhrwerk! Die konstanteste Leistung des Tages mit einer minimalen Differenz von nur <span class="highlight-gold">{best_schwankung:.2f} in der Match-Wertung</span>:</p>
                    <ul style="list-style-type: none; padding-left: 0;">
                """
                
                # Für jeden Sieger eine Zeile mit den exakten Werten generieren
                for (name, schwankung, min_s, max_s) in sieger_uhrwerk:
                    html += f"<li style='margin-bottom: 5px;'><strong>{name}</strong> <em>({min_s:.2f} bis {max_s:.2f})</em></li>"
                    
                html += "</ul></div>"

            # --- 3. SPÄTZÜNDER (Größte Steigerung) ---
            spaetzuender_kandidaten = []
            for s in stats:
                name = s["n"]
                scores = spieler_scores.get(name, [])
                if len(scores) > 1:
                    # FIX: Auch hier zuerst auf 2 Stellen runden!
                    erstes_match = round(scores[0], 2)
                    bestes_match = round(max(scores), 2)
                    
                    steigerung = round(bestes_match - erstes_match, 2)
                    if steigerung > 0: 
                        spaetzuender_kandidaten.append((name, steigerung, erstes_match, bestes_match))

            if spaetzuender_kandidaten:
                best_steigerung = max([k[1] for k in spaetzuender_kandidaten])
                sieger_spaet = [k for k in spaetzuender_kandidaten if k[1] == best_steigerung]
                
                html += f"""
                <div class="award-box">
                    <h3 class="award-title">🚀 Der "Spätzünder"</h3>
                    <p>Der Preis für das größte Comeback!<br>
                    Mit einer gewaltigen Leistungssteigerung von <span class="highlight-gold">{best_steigerung:.2f} in der Match-Wertung</span> im Turnierverlauf:</p>
                    <ul style="list-style-type: none; padding-left: 0;">
                """
                
                for (name, steigerung, start, best) in sieger_spaet:
                    html += f"<li style='margin-bottom: 5px;'><strong>{name}</strong> <em>(gesteigert von {start:.2f} auf {best:.2f})</em></li>"
                    
                html += "</ul></div>"

            # --- TOP 5 TABELLE ---
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

            # ==========================================
            # TEIL 2: K.O.-PHASE (Fotofinish & Nerven aus Stahl)
            # ==========================================
            fotofinish_matches = []
            min_diff = float('inf')
            
            nerven_spieler = []
            max_ko_score = -1.0

        if turnier_beendet:
            # K.O.-Daten durchsuchen
            if ko_spielplan:
                for match in ko_spielplan:
                    if match.get("gespielt"):
                        # Manuelle Leermatches ignorieren
                        if match.get("pi_match_id") == "MANUELL" and match.get("total1", 0) == 0 and match.get("total2", 0) == 0:
                            continue
                            
                        t1 = match.get("total1", 0.0)
                        t2 = match.get("total2", 0.0)
                        p1 = match.get("spieler1", "Unbekannt")
                        p2 = match.get("spieler2", "Unbekannt")
                        # --- ELA FIX: Auch hier den Übersetzer fragen! ---
                        match_nr = match.get("match_nr", "")
                        phase = datei_manager.get_match_name(match_nr) if datei_manager else match_nr
                        
                        # 1. Fotofinish prüfen (Runden auf 3 Nachkommastellen für sicheren Float-Vergleich)
                        diff = round(abs(t1 - t2), 3)
                        if diff < min_diff:
                            min_diff = diff
                            fotofinish_matches = [(p1, p2, t1, t2, diff, phase)]
                        elif diff == min_diff:
                            fotofinish_matches.append((p1, p2, t1, t2, diff, phase))
                            
                        # 2. Nerven aus Stahl prüfen
                        for score, player in [(round(t1, 2), p1), (round(t2, 2), p2)]:
                            if score > max_ko_score:
                                max_ko_score = score
                                nerven_spieler = [(player, phase)]
                            elif score == max_ko_score:
                                nerven_spieler.append((player, phase))

            # Nur rendern, wenn es K.O.-Matches gab
            if fotofinish_matches or nerven_spieler:
                html += "<h3 style='background-color: transparent; color: #00ff00; border-bottom: 1px solid #333; margin-top: 40px; padding-left: 0;'>🎖️ K.O.-PHASE</h3>"
                
                # --- 4. FOTOFINISH ---
                if fotofinish_matches:
                    html += f"""
                    <div class="award-box" style="border-left-color: #ff3333;">
                        <h3 class="award-title" style="color: #ff3333;">📸 Das Fotofinish</h3>
                        <p>Das dramatischste Duell auf Messers Schneide!<br>
                        Mit unfassbaren <span style="color: #ff3333; font-weight: bold;">{min_diff:.3f}</span> Unterschied in der Match-Wertung trennten sich:</p>
                        <ul style="list-style-type: none; padding-left: 0;">
                    """
                    for (p1, p2, t1, t2, diff, phase) in fotofinish_matches:
                        html += f"<li style='margin-bottom: 5px;'><strong>{p1}</strong> ({t1:.2f}) vs <strong>{p2}</strong> ({t2:.2f}) <em>(im {phase})</em></li>"
                    html += "</ul></div>"
                    
                # --- 5. NERVEN AUS STAHL ---
                if nerven_spieler:
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
                    

        html += """
        </body>
        </html>
        """

        try:
            with open(self.filename, "w", encoding="utf-8") as f:
                f.write(html)
            
            # NEU: Öffnet den Browser NUR, wenn silent = False ist (beim manuellen Klick)
            if not silent and os.name == 'nt':
                absoluter_pfad = os.path.abspath(self.filename)
                os.startfile(absoluter_pfad)
                
            return True, f"Der Bericht wurde erfolgreich erstellt!\nEr liegt im Ordner: savegames\nDu kannst ihn jetzt in WhatsApp teilen."
        except Exception as e:
            return False, f"Fehler beim Speichern oder Öffnen:\n{e}"