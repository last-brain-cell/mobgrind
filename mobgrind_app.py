#!/usr/bin/env python3
"""MobGrind — cross-platform system-tray app for the AFK mob-farm macro.

Shows a tray icon (macOS menu bar / Windows notification area) with
Start/Stop, Pause, Calibrate and Quit. The macro itself lives in mobgrind.py;
this is only the UI, so it runs the same on Mac and Windows.

Run from source:  pip install pystray pillow pyautogui pynput
                  python3 mobgrind_app.py

Build a downloadable binary (must build ON the OS you target — PyInstaller
is not a cross-compiler):
  pip install pyinstaller
  macOS:    pyinstaller --name MobGrind --windowed --onedir \\
              --hidden-import pynput.keyboard._darwin \\
              --hidden-import pynput.mouse._darwin mobgrind_app.py
            # result: dist/MobGrind.app  (zip it, or make a .dmg with hdiutil)
  Windows:  pyinstaller --name MobGrind --windowed --onefile \\
              --hidden-import pynput.keyboard._win32 \\
              --hidden-import pynput.mouse._win32 mobgrind_app.py
            # result: dist\\MobGrind.exe
"""
import threading
import time

import pyautogui
import pystray
from PIL import Image, ImageDraw

import mobgrind as engine

IDLE, RUNNING, PAUSED, BUSY = (120, 120, 120), (60, 200, 90), (230, 170, 40), (70, 150, 230)


def make_icon(color):
    """A simple sword glyph (mob-agnostic), tinted by state."""
    img = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.line((16, 48, 46, 18), fill=color, width=6)          # blade (bottom-left -> top-right)
    d.line((12, 40, 24, 52), fill=color, width=5)          # crossguard
    d.line((12, 52, 20, 52), fill=color, width=5)          # pommel
    return img


class MobGrindApp:
    def __init__(self):
        self.running = False
        self.paused = False
        self.busy = False  # calibrating
        engine.load_settings()
        self.icon = pystray.Icon(
            "mobgrind",
            icon=make_icon(IDLE),
            title="MobGrind",
            menu=pystray.Menu(
                pystray.MenuItem(lambda i: "Stop" if self.running else "Start",
                                 self.on_start, default=True),
                pystray.MenuItem(lambda i: "Resume" if self.paused else "Pause",
                                 self.on_pause, enabled=lambda i: self.running),
                pystray.MenuItem("Calibrate", self.on_calibrate,
                                 enabled=lambda i: not self.running and not self.busy),
                pystray.Menu.SEPARATOR,
                pystray.MenuItem("Settings", self._settings_menu()),
                pystray.Menu.SEPARATOR,
                pystray.MenuItem("Quit", self.on_quit),
            ),
        )

    # --- settings submenu (native radio groups; changes apply live and persist) ---
    def _settings_menu(self):
        def choices(attr, options):
            def item(label, val):
                def action(icon, it):
                    self._set(attr, val)
                def checked(it):
                    return getattr(engine, attr) == val
                return pystray.MenuItem(label, action, checked=checked, radio=True)
            return pystray.Menu(*[item(lbl, v) for lbl, v in options])

        return pystray.Menu(
            pystray.MenuItem("Attack interval", choices("CLICK_EVERY",
                [("4s", 4.0), ("5s", 5.0), ("6s", 6.0), ("7s", 7.0), ("8s", 8.0), ("10s", 10.0)])),
            pystray.MenuItem("Timing jitter", choices("JITTER",
                [("Off", 0.0), ("+/-0.3s", 0.3), ("+/-0.6s", 0.6), ("+/-1.0s", 1.0)])),
            pystray.MenuItem("Eat hold", choices("EAT_HOLD",
                [("2s", 2.0), ("3s", 3.0), ("4s", 4.0), ("5s", 5.0), ("6s", 6.0)])),
            pystray.MenuItem("Start delay", choices("START_DELAY",
                [("5s", 5.0), ("10s", 10.0), ("15s", 15.0)])),
            pystray.MenuItem("Eat sensitivity", choices("HUNGER_DISTANCE",
                [("Low", 80), ("Medium", 60), ("High", 40)])),
            pystray.MenuItem("Reverse sword scroll",
                             lambda icon, it: self._set("SCROLL_DIR", -engine.SCROLL_DIR),
                             checked=lambda it: engine.SCROLL_DIR == 1),
        )

    def _set(self, attr, value):
        engine.set_value(attr, value)
        self.icon.update_menu()

    # --- helpers ---
    def notify(self, msg):
        try:
            self.icon.notify(msg, "MobGrind")
        except Exception:
            pass  # notifications aren't guaranteed on every backend
        self.icon.title = f"MobGrind — {msg}"

    def refresh(self):
        color = BUSY if self.busy else PAUSED if self.paused else RUNNING if self.running else IDLE
        self.icon.icon = make_icon(color)
        self.icon.update_menu()

    # --- menu actions (run on the backend's thread) ---
    def on_start(self, icon, item):
        if self.busy:
            return
        if not self.running:
            self.running = True
            self.paused = False
            self.refresh()
            self.notify(f"Starting in {engine.START_DELAY:.0f}s — focus the game")
            threading.Thread(target=self._run, daemon=True).start()
        else:
            self.running = False  # the loop checks this and exits

    def on_pause(self, icon, item):
        self.paused = not self.paused
        self.refresh()

    def on_calibrate(self, icon, item):
        if self.busy or self.running:
            return
        threading.Thread(target=self._calibrate, daemon=True).start()

    def on_quit(self, icon, item):
        self.running = False
        self.icon.stop()

    # --- worker threads ---
    def _run(self):
        try:
            time.sleep(engine.START_DELAY)
            calib = engine.load_calib()
            if not calib:
                self.notify("No calibration — eating on a timer, no death detection.")
            clicks, meals, mins = engine.run(
                calib,
                stop=lambda: not self.running,
                paused=lambda: self.paused,
                log=self.notify,
            )
            self.notify(f"Done — {mins:.1f} min, {clicks} attacks, {meals} meals.")
        except Exception as e:  # fail-safe corner, screen-read error, etc.
            self.notify(f"Stopped: {e}")
        finally:
            self.running = False
            self.paused = False
            self.refresh()

    def _calibrate(self):
        self.busy = True
        self.refresh()
        try:
            self.notify("Hover the LEFTMOST hunger haunch — capturing in 5s")
            time.sleep(5)
            hx, hy = pyautogui.position()
            hcolor = list(pyautogui.pixel(hx, hy))
            self.notify("Now hover the screen CENTER — capturing in 5s")
            time.sleep(5)
            cx, cy = pyautogui.position()
            engine.save_calib([hx, hy], hcolor, [cx, cy])
            self.notify(f"Calibrated — hunger {tuple(hcolor)}")
        except Exception as e:
            self.notify(f"Calibration failed: {e}")
        finally:
            self.busy = False
            self.refresh()

    def run(self):
        self.icon.run()


if __name__ == "__main__":
    MobGrindApp().run()
