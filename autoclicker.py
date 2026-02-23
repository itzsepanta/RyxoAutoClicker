import ctypes
import time
import random
import threading
import json
import os
from datetime import datetime

import customtkinter as ctk
import keyboard
import pystray
from pystray import MenuItem as item
from PIL import Image, ImageDraw

# ====================== LOW-LEVEL SENDINPUT (ANTI-DETECTION) ======================
class MOUSEINPUT(ctypes.Structure):
    _fields_ = [("dx", ctypes.c_long),
                ("dy", ctypes.c_long),
                ("mouseData", ctypes.c_ulong),
                ("dwFlags", ctypes.c_ulong),
                ("time", ctypes.c_ulong),
                ("dwExtraInfo", ctypes.POINTER(ctypes.c_ulong))]

class INPUT_UNION(ctypes.Union):
    _fields_ = [("mi", MOUSEINPUT)]

class INPUT(ctypes.Structure):
    _fields_ = [("type", ctypes.c_ulong),
                ("union", INPUT_UNION)]

INPUT_MOUSE = 0
MOUSEEVENTF_LEFTDOWN = 0x0002
MOUSEEVENTF_LEFTUP = 0x0004
MOUSEEVENTF_RIGHTDOWN = 0x0008
MOUSEEVENTF_RIGHTUP = 0x0010
MOUSEEVENTF_MOVE = 0x0001

def send_mouse(flags, dx=0, dy=0):
    extra = ctypes.c_ulong(0)
    mi = MOUSEINPUT(dx, dy, 0, flags, 0, ctypes.pointer(extra))
    inp = INPUT(INPUT_MOUSE, INPUT_UNION(mi=mi))
    ctypes.windll.user32.SendInput(1, ctypes.byref(inp), ctypes.sizeof(inp))

def human_click(button='left'):
    if button == 'left':
        down, up = MOUSEEVENTF_LEFTDOWN, MOUSEEVENTF_LEFTUP
    else:
        down, up = MOUSEEVENTF_RIGHTDOWN, MOUSEEVENTF_RIGHTUP
    
    send_mouse(down)
    time.sleep(random.uniform(0.001, 0.012))  # Human-like button hold time
    send_mouse(up)

# ====================== MAIN APPLICATION ======================
class AutoClicker:
    def __init__(self):
        self.root = ctk.CTk()
        self.root.title("AutoClicker v2.1")
        self.root.geometry("680x780")
        self.root.resizable(False, False)
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        self.running = False
        self.click_thread = None
        self.clicks_count = 0
        self.start_time = None
        self.config_file = "autoclicker_config.json"
        self.tray_icon = None

        # Default settings
        self.settings = {
            "button": "left",
            "cps": 12.0,
            "randomize": True,
            "variance": 25,      # Percentage variance (0-100)
            "jitter": False,
            "jitter_chance": 15, # Chance of jitter per click (%)
            "hotkey": "F6",
            "max_clicks": 0,     # 0 = unlimited
            "max_duration": 0    # Seconds, 0 = unlimited
        }
        self.load_config()

        self.setup_ui()
        keyboard.add_hotkey(self.settings["hotkey"], self.toggle_clicker)

        # System Tray Setup
        self.root.protocol("WM_DELETE_WINDOW", self.minimize_to_tray)
        self.setup_tray()

    def setup_ui(self):
        # Title
        title = ctk.CTkLabel(self.root, text="Ryxo AutoClicker", font=ctk.CTkFont(size=24, weight="bold"))
        title.pack(pady=20)

        # Settings Frame
        settings_frame = ctk.CTkFrame(self.root)
        settings_frame.pack(padx=20, pady=10, fill="x")

        # Click Button
        ctk.CTkLabel(settings_frame, text="Click Button:").grid(row=0, column=0, padx=10, pady=8, sticky="w")
        self.btn_var = ctk.StringVar(value=self.settings["button"])
        ctk.CTkOptionMenu(settings_frame, values=["left", "right"], variable=self.btn_var).grid(row=0, column=1, padx=10, pady=8)

        # CPS
        ctk.CTkLabel(settings_frame, text="CPS (Clicks Per Second):").grid(row=1, column=0, padx=10, pady=8, sticky="w")
        self.cps_slider = ctk.CTkSlider(settings_frame, from_=1, to=100, number_of_steps=990, command=self.update_cps_label)
        self.cps_slider.set(self.settings["cps"])
        self.cps_slider.grid(row=1, column=1, padx=10, pady=8, sticky="ew")
        self.cps_label = ctk.CTkLabel(settings_frame, text=f"{self.settings['cps']:.1f}")
        self.cps_label.grid(row=1, column=2, padx=10)

        # Variance
        ctk.CTkLabel(settings_frame, text="Human Variance (%):").grid(row=2, column=0, padx=10, pady=8, sticky="w")
        self.var_slider = ctk.CTkSlider(settings_frame, from_=0, to=100, command=self.update_var_label)
        self.var_slider.set(self.settings["variance"])
        self.var_slider.grid(row=2, column=1, padx=10, pady=8, sticky="ew")
        self.var_label = ctk.CTkLabel(settings_frame, text=f"{self.settings['variance']}%")
        self.var_label.grid(row=2, column=2, padx=10)

        # Switches
        self.random_switch = ctk.CTkSwitch(settings_frame, text="Randomize (Gaussian)", onvalue=True, offvalue=False)
        self.random_switch.select() if self.settings["randomize"] else self.random_switch.deselect()
        self.random_switch.grid(row=3, column=0, columnspan=2, pady=8, sticky="w", padx=10)

        self.jitter_switch = ctk.CTkSwitch(settings_frame, text="Jitter Micro-Movement (anti-detection)", onvalue=True, offvalue=False)
        self.jitter_switch.select() if self.settings["jitter"] else self.jitter_switch.deselect()
        self.jitter_switch.grid(row=4, column=0, columnspan=2, pady=8, sticky="w", padx=10)

        # Hotkey
        ctk.CTkLabel(settings_frame, text="Start/Stop Hotkey:").grid(row=5, column=0, padx=10, pady=8, sticky="w")
        self.hotkey_entry = ctk.CTkEntry(settings_frame)
        self.hotkey_entry.insert(0, self.settings["hotkey"])
        self.hotkey_entry.grid(row=5, column=1, padx=10, pady=8)

        # Max Clicks
        ctk.CTkLabel(settings_frame, text="Max Clicks (0=unlimited):").grid(row=6, column=0, padx=10, pady=8, sticky="w")
        self.max_clicks_entry = ctk.CTkEntry(settings_frame)
        self.max_clicks_entry.insert(0, str(self.settings.get("max_clicks", 0)))
        self.max_clicks_entry.grid(row=6, column=1, padx=10, pady=8)

        # Control Buttons
        control_frame = ctk.CTkFrame(self.root)
        control_frame.pack(pady=20, fill="x", padx=20)

        self.start_btn = ctk.CTkButton(control_frame, text="Start (F6)", fg_color="green", command=self.toggle_clicker, width=150)
        self.start_btn.pack(side="left", padx=20, pady=10)

        self.save_btn = ctk.CTkButton(control_frame, text="Save Settings", command=self.save_config)
        self.save_btn.pack(side="left", padx=10)

        self.load_btn = ctk.CTkButton(control_frame, text="Load Settings", command=self.load_config)
        self.load_btn.pack(side="left", padx=10)

        # Realtime Stats
        self.stats_label = ctk.CTkLabel(self.root, text="Stats: 0 clicks | Real CPS: 0.0 | Time: 00:00", font=ctk.CTkFont(size=14))
        self.stats_label.pack(pady=10)

        self.status_label = ctk.CTkLabel(self.root, text="Ready — Hotkey: " + self.settings["hotkey"], text_color="yellow")
        self.status_label.pack(pady=5)

        # Update stats every 200ms
        self.root.after(200, self.update_stats)

    def update_cps_label(self, val):
        self.cps_label.configure(text=f"{val:.1f}")

    def update_var_label(self, val):
        self.var_label.configure(text=f"{int(val)}%")

    def toggle_clicker(self):
        if self.running:
            self.stop_clicker()
        else:
            self.start_clicker()

    def start_clicker(self):
        if self.running:
            return
        self.running = True
        self.start_time = time.time()
        self.clicks_count = 0
        self.start_btn.configure(text="Stop (F6)", fg_color="red")
        self.status_label.configure(text="Running...", text_color="green")
        
        self.click_thread = threading.Thread(target=self.clicker_loop, daemon=True)
        self.click_thread.start()

    def stop_clicker(self):
        self.running = False
        if self.click_thread and self.click_thread.is_alive():
            self.click_thread.join(timeout=0.5)
        self.start_btn.configure(text="Start (F6)", fg_color="green")
        self.status_label.configure(text="Stopped", text_color="red")

    def clicker_loop(self):
        button = self.btn_var.get()
        cps = self.cps_slider.get()
        variance_pct = self.var_slider.get() / 100.0
        jitter_enabled = self.jitter_switch.get()
        max_clicks = int(self.max_clicks_entry.get() or 0)
        
        while self.running:
            if max_clicks > 0 and self.clicks_count >= max_clicks:
                self.stop_clicker()
                break

            human_click(button)
            self.clicks_count += 1

            # Human-like delay
            base_delay = 1.0 / cps
            if self.random_switch.get():
                delay = random.gauss(base_delay, base_delay * variance_pct)
                delay = max(0.001, min(delay, base_delay * 3))  # Clamp
            else:
                delay = base_delay

            time.sleep(delay)

            # Optional Jitter (for more human-like behavior)
            if jitter_enabled and random.randint(1, 100) <= self.settings.get("jitter_chance", 15):
                dx = random.choice([-2, -1, 1, 2])
                dy = random.choice([-2, -1, 1, 2])
                send_mouse(MOUSEEVENTF_MOVE, dx, dy)
                time.sleep(random.uniform(0.003, 0.008))
                send_mouse(MOUSEEVENTF_MOVE, -dx, -dy)

    def update_stats(self):
        if self.running and self.start_time:
            elapsed = time.time() - self.start_time
            real_cps = self.clicks_count / elapsed if elapsed > 0 else 0
            mins, secs = divmod(int(elapsed), 60)
            self.stats_label.configure(
                text=f"Stats: {self.clicks_count:,} clicks | Real CPS: {real_cps:.2f} | Time: {mins:02d}:{secs:02d}"
            )
        self.root.after(200, self.update_stats)

    def save_config(self):
        self.settings.update({
            "button": self.btn_var.get(),
            "cps": self.cps_slider.get(),
            "randomize": bool(self.random_switch.get()),
            "variance": int(self.var_slider.get()),
            "jitter": bool(self.jitter_switch.get()),
            "hotkey": self.hotkey_entry.get().lower(),
            "max_clicks": int(self.max_clicks_entry.get() or 0)
        })
        try:
            with open(self.config_file, "w", encoding="utf-8") as f:
                json.dump(self.settings, f, indent=4)
            self.status_label.configure(text="Settings Saved ✓", text_color="cyan")
        except Exception as e:
            print("Save Error:", e)

    def load_config(self):
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, "r", encoding="utf-8") as f:
                    loaded = json.load(f)
                    self.settings.update(loaded)
                
                self.btn_var.set(self.settings["button"])
                self.cps_slider.set(self.settings["cps"])
                self.var_slider.set(self.settings["variance"])
                if self.settings["randomize"]:
                    self.random_switch.select()
                else:
                    self.random_switch.deselect()
                if self.settings.get("jitter", False):
                    self.jitter_switch.select()
                self.hotkey_entry.delete(0, "end")
                self.hotkey_entry.insert(0, self.settings["hotkey"])
                self.max_clicks_entry.delete(0, "end")
                self.max_clicks_entry.insert(0, str(self.settings.get("max_clicks", 0)))
            except:
                pass

    def setup_tray(self):
        # Create a simple icon
        image = Image.new('RGB', (64, 64), color=(73, 109, 137))
        d = ImageDraw.Draw(image)
        d.text((10, 10), "AC", fill=(255, 255, 0))

        menu = (
            item('Show', self.show_window),
            item('Quit', self.quit_app)
        )
        self.tray_icon = pystray.Icon('autoclicker', image, 'Ryxo AutoClicker', menu)

    def minimize_to_tray(self):
        self.root.withdraw()
        self.tray_icon.run()

    def show_window(self):
        self.tray_icon.stop()
        self.root.after(0, self.root.deiconify)

    def quit_app(self):
        self.tray_icon.stop()
        self.root.quit()

    def run(self):
        self.root.mainloop()

if __name__ == "__main__":
    # Important: For some games, run the program as Administrator
    app = AutoClicker()
    print("Ryxo AutoClicker is ready! Hotkey:", app.settings["hotkey"])
    app.run()