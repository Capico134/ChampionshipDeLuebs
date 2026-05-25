import subprocess
import pygetwindow as gw
import time
import ctypes
import os
import sys
import configparser

# =========================================================
# 1. DPI-AWARENESS ERZWINGEN (Sehr wichtig für 4K+200%)
# =========================================================
if sys.platform == "win32":
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        pass

def get_screen_resolution():
    user32 = ctypes.windll.user32
    return user32.GetSystemMetrics(0), user32.GetSystemMetrics(1)

# =========================================================
# 2. DER INJECTION-CODE (Monkey-Patching)
# =========================================================
LAUNCHER_CODE = r'''
import sys
import runpy
import tkinter as tk
import ctypes
import pygetwindow as gw
import os

# DPI Awareness erzwingen
if sys.platform == "win32":
    try: ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except: pass

scale_factor = float(sys.argv[1])
ini_path = sys.argv[2]
target_script = sys.argv[3]
sys.argv = [target_script] + sys.argv[4:] 

# --- MONKEY PATCHING ERWEITERT ---
OriginalTk = tk.Tk
OriginalToplevel = tk.Toplevel
OriginalPlace = tk.Widget.place
OriginalGeometry = tk.Wm.geometry
OriginalCanvasInit = tk.Canvas.__init__
OriginalCanvasCreate = tk.Canvas._create

def apply_window_logic(window):
    """Hilfsfunktion, um Skalierung und Hotkeys auf JEDES Fenster anzuwenden."""
    window.is_borderless = False
    
    BASE_SCALE = 1.333333
    window.tk.call('tk', 'scaling', BASE_SCALE * scale_factor)
    
    window.bind("<Alt-F12>", lambda e: toggle_border(window))
    window.bind("<Alt-F11>", lambda e: print_coords(window))
    
    # NEU: Der MEGA-CLOU Hotkey (Speichern in config.ini)
    window.bind("<Alt-F8>", lambda e: save_layout_to_config())
    
    if scale_factor < 1.0:
        set_borderless(window, True)

def set_borderless(window, status):
    window.is_borderless = status
    window.overrideredirect(status)

def toggle_border(window):
    new_status = not getattr(window, 'is_borderless', False)
    set_borderless(window, new_status)
    print(f"🔄 Rahmen gewechselt für: {window.winfo_toplevel().title()}")
    window.update_idletasks()

def print_coords(window):
    window.update_idletasks()
    x = int(window.winfo_rootx() / scale_factor)
    y = int(window.winfo_rooty() / scale_factor)
    w = int(window.winfo_width() / scale_factor)
    h = int(window.winfo_height() / scale_factor)
    full_title = window.winfo_toplevel().title()
    short_title = full_title[:12] if full_title else "Fenster"
    print(f"📍 Neuer Code: wait_and_position('{short_title}', {x}, {y}, {w}, {h}, scale_factor)")

def save_layout_to_config():
    """Liest alle Fenster aus und speichert sie als [Layout] in die config.ini"""
    print("\n💾 MEGA-CLOU: Starte Speichervorgang in config.ini...")
    targets = {
        'Shooting DeL': 'shooting',
        'Championship': 'championship',
        'LIVE': 'live',
        'Anzeige': 'anzeige',
        'DeLuebs_Master_Console': 'console'
    }
    
    new_layout = ["[Layout]\n"]
    for title_part, key in targets.items():
        windows = gw.getWindowsWithTitle(title_part)
        if windows:
            win = windows[0]
            x = int(win.left / scale_factor)
            y = int(win.top / scale_factor)
            w = int(win.width / scale_factor)
            h = int(win.height / scale_factor)
            new_layout.append(f"{key} = {x}, {y}, {w}, {h}\n")
    
    # Behutsames Einlesen der Original-Datei (um Kommentare zu retten!)
    lines = []
    if os.path.exists(ini_path):
        with open(ini_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
    
    start_idx, end_idx = -1, -1
    for i, line in enumerate(lines):
        if line.strip() == "[Layout]":
            start_idx = i
        elif start_idx != -1 and line.strip().startswith("["):
            end_idx = i
            break
            
    if start_idx == -1:
        if lines and not lines[-1].endswith('\n'): lines.append('\n')
        lines.append('\n')
        lines.extend(new_layout)
    else:
        if end_idx == -1:
            lines = lines[:start_idx] + new_layout
        else:
            lines = lines[:start_idx] + new_layout + ["\n"] + lines[end_idx:]
            
    with open(ini_path, 'w', encoding='utf-8') as f:
        f.writelines(lines)
        
    print(f"✅ Layout erfolgreich gespeichert in: {ini_path}")

class ScaledTk(OriginalTk):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        apply_window_logic(self)

class ScaledToplevel(OriginalToplevel):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        apply_window_logic(self)

tk.Tk = ScaledTk
tk.Toplevel = ScaledToplevel

def scaled_place(self, cnf={}, **kw):
    for k in ['x', 'y', 'width', 'height']:
        if k in kw and isinstance(kw[k], (int, float, str)):
            try: kw[k] = int(float(kw[k]) * scale_factor)
            except ValueError: pass
    OriginalPlace(self, cnf, **kw)
tk.Widget.place = scaled_place

def scaled_geometry(self, newGeometry=None):
    if newGeometry and isinstance(newGeometry, str) and 'x' in newGeometry:
        import re
        m = re.match(r"(\d+)x(\d+)(.*)", newGeometry)
        if m:
            w, h, rest = m.groups()
            newGeometry = f"{int(int(w) * scale_factor)}x{int(int(h) * scale_factor)}{rest}"
    return OriginalGeometry(self, newGeometry)
tk.Wm.geometry = scaled_geometry

def scaled_canvas_init(self, master=None, cnf={}, **kw):
    for k in ['width', 'height']:
        if k in kw: 
            try: kw[k] = int(float(kw[k]) * scale_factor)
            except ValueError: pass
    OriginalCanvasInit(self, master, cnf, **kw)
tk.Canvas.__init__ = scaled_canvas_init

def scaled_canvas_create(self, itemType, args, kw):
    scaled_args = []
    for a in args:
        try: scaled_args.append(float(a) * scale_factor)
        except (ValueError, TypeError): scaled_args.append(a)
    return OriginalCanvasCreate(self, itemType, tuple(scaled_args), kw)
tk.Canvas._create = scaled_canvas_create

try:
    from PIL import Image, ImageTk
    OriginalPILInit = ImageTk.PhotoImage.__init__
    def scaled_pil_init(self, image=None, size=None, **kw):
        if image is not None and hasattr(image, 'resize') and scale_factor != 1.0:
            new_size = (int(image.width * scale_factor), int(image.height * scale_factor))
            try: resample = Image.Resampling.LANCZOS
            except AttributeError: resample = Image.ANTIALIAS
            image = image.resize(new_size, resample)
        OriginalPILInit(self, image, size, **kw)
    ImageTk.PhotoImage.__init__ = scaled_pil_init
except ImportError:
    pass

runpy.run_path(target_script, run_name='__main__')
'''

# =========================================================
# 3. LADE LOGIK FÜR CONFIG.INI
# =========================================================
def load_layout(ini_path):
    """Liest die Fenster-Koordinaten aus der config.ini (Fallback auf Standardwerte)"""
    # Dein bisheriges Standard-Layout:
    layout = {
        'shooting': [0, 0, 1920, 1080],
        'championship': [1920, 0, 1520, 700],
        'live': [1920, 672, 1520, 720],
        'anzeige': [1120, 1080, 800, 319],
        'console': [0, 1080, 1120, 319]
    }
    
    if os.path.exists(ini_path):
        config = configparser.ConfigParser()
        config.read(ini_path, encoding='utf-8')
        if config.has_section('Layout'):
            print("📂 [Layout] Sektion in config.ini gefunden! Lade persönliche Positionen...")
            for key in layout.keys():
                if config.has_option('Layout', key):
                    try:
                        val = config.get('Layout', key)
                        parts = [int(p.strip()) for p in val.split(',')]
                        if len(parts) == 4:
                            layout[key] = parts
                    except Exception as e:
                        print(f"⚠️ Fehler beim Parsen von '{key}': {e}")
    else:
        print("⚠️ config.ini noch nicht gefunden, nutze Standard-Layout.")
        
    return layout

# =========================================================
# 4. APP STARTER
# =========================================================
def start_scaled_app(cwd, script_name, scale_factor, ini_path, args=[]):
    launcher_path = os.path.join(cwd, "_temp_launcher.py")
    with open(launcher_path, "w", encoding="utf-8") as f:
        f.write(LAUNCHER_CODE)
    
    # NEU: ini_path wird an den Launcher mit übergeben!
    cmd = ["python", "_temp_launcher.py", str(scale_factor), ini_path, script_name] + args
    subprocess.Popen(cmd, cwd=cwd)

# =========================================================
# 5. FENSTER-LOGIK UND SETUP
# =========================================================
def wait_and_position(partial_title, target_x, target_y, target_width, target_height, scale_factor=1.0, max_retries=30, win10_fix=True):
    target_x = int(target_x * scale_factor)
    target_y = int(target_y * scale_factor)
    target_width = int(target_width * scale_factor)
    target_height = int(target_height * scale_factor)

    if win10_fix and scale_factor == 1.0:
        target_x -= 7
        target_width += 14
        target_height += 7

    for versuch in range(max_retries):
        windows = gw.getWindowsWithTitle(partial_title)
        if windows:
            try:
                win = windows[0]
                win.restore()
                win.moveTo(target_x, target_y)
                win.resizeTo(target_width, target_height)
                print(f"✅ '{partial_title}' in Position!")
                return True
            except Exception as e:
                print(f"⚠️ Fehler beim Verschieben von '{partial_title}': {e}")
                return False
        time.sleep(1)
    return False

def setup_studio():
    if sys.platform == "win32":
        console_title = "DeLuebs_Master_Console"
        ctypes.windll.kernel32.SetConsoleTitleW(console_title)
        time.sleep(0.1)

    base_path = os.path.dirname(os.path.abspath(__file__))
    ini_path = os.path.join(base_path, "config.ini")
    shooting_path = os.path.abspath(os.path.join(base_path, "..", "ShootingDeLuebs"))    
    
    # --- NEU: Manueller Skalierungs-Check ---
    manual_scale = None
    if os.path.exists(ini_path):
        config = configparser.ConfigParser()
        config.read(ini_path, encoding='utf-8')
        if config.has_option('Settings', 'manual_scale'):
            try:
                manual_scale = float(config.get('Settings', 'manual_scale'))
                print(f"⚙️ Manueller Skalierungsfaktor aus config.ini: {manual_scale}")
            except ValueError:
                print("⚠️ Ungültiger Wert für manual_scale in config.ini - ignoriere.")

    if manual_scale is not None:
        scale_factor = manual_scale
    else:
        # Automatik-Modus (dein bisheriger Code)
        width, height = get_screen_resolution()
        print(f"🖥️ Erfasste physikalische Auflösung: {width}x{height}")
    
        basis_breite = 3440.0
        if width >= 3840:
            print("📺 4K Monitor erkannt. Nutze Original-Größe (1:1).")
            scale_factor = 1.0
        elif width >= 3400:
            print("🚀 NASA-Cockpit erkannt. Nutze Original-Größe (1:1).")
            scale_factor = 1.0
        else:
            scale_factor = width / basis_breite
            print(f"🔬 Kleinerer Monitor erkannt. Skaliere auf {scale_factor * 100:.1f}%")
  
    # Programme starten
    start_scaled_app(base_path, "MeisterschaftDeLuebs.py", scale_factor, ini_path, ["-beamer_autostart"]) #, "-topmost"])
    if os.path.exists(shooting_path):
        start_scaled_app(shooting_path, "ShootingDeLuebs.py", scale_factor, ini_path)
    
    # NEU: Layout aus config.ini laden
    layout = load_layout(ini_path)
    
    # Fenster mit den geladenen Koordinaten anordnen!
    wait_and_position('Shooting DeL', *layout['shooting'], scale_factor)
    wait_and_position('Championship', *layout['championship'], scale_factor)
    wait_and_position('LIVE', *layout['live'], scale_factor)
    wait_and_position('Anzeige', *layout['anzeige'], scale_factor)
    wait_and_position('DeLuebs_Master_Console', *layout['console'], scale_factor)

    print("\n🎉 Studio-Layout aktiviert. Alles bereit!")
    print("👉 HINWEIS: Drücke Alt+F8 in einem beliebigen App-Fenster, um das aktuelle Layout dauerhaft in der config.ini zu speichern!")

if __name__ == "__main__":
    setup_studio()