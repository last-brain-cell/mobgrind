#!/usr/bin/env python3
"""Cross-platform system-tray app for the spider AFK macro.

Shows a tray icon (macOS menu bar / Windows notification area) with
Start/Stop, Pause, Calibrate and Quit. The macro itself lives in
spider_afk.py; this is only the UI, so it runs the same on Mac and Windows.

Run from source:  pip install pystray pillow pyautogui pynput
                  python3 spider_afk_app.py

Build a downloadable binary (must build ON the OS you target — PyInstaller
is not a cross-compiler):
  pip install pyinstaller
  macOS:    pyinstaller --name SpiderAFK --windowed --onedir \\
              --hidden-import pynput.keyboard._darwin \\
              --hidden-import pynput.mouse._darwin spider_afk_app.py
            # result: dist/SpiderAFK.app  (zip it, or make a .dmg with hdiutil)
  Windows:  pyinstaller --name SpiderAFK --windowed --onefile \\
              --hidden-import pynput.keyboard._win32 \\
              --hidden-import pynput.mouse._win32 spider_afk_app.py
            # result: dist\\SpiderAFK.exe
"""
import threading
import time

import pyautogui
import pystray
from PIL import Image, ImageDraw

import spider_afk as engine

IDLE, RUNNING, PAUSED, BUSY = (120, 120, 120), (60, 200, 90), (230, 170, 40), (70, 150, 230)


def make_icon(color):
    """A simple spider-ish glyph: round body + eight little legs, tinted by state."""
    img = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    for sx in (-1, 1):
        for i in range(4):
            y = 20 + i * 8
            d.line((32, 34, 32 + sx * 26, y), fill=color, width=3)
    d.ellipse((22, 18, 42, 38), fill=color)   # head/body
    d.ellipse((24, 36, 40, 56), fill=color)   # abdomen
    return img


class AFKApp:
    def __init__(self):
        self.running = False
        self.paused = False
        self.busy = False  # calibrating
        self.icon = pystray.Icon(
            "spider_afk",
            icon=make_icon(IDLE),
            title="Spider AFK",
            menu=pystray.Menu(
                pystray.MenuItem(lambda i: "Stop" if self.running else "Start",
                                 self.on_start, default=True),
                pystray.MenuItem(lambda i: "Resume" if self.paused else "Pause",
                                 self.on_pause, enabled=lambda i: self.running),
                pystray.MenuItem("Calibrate", self.on_calibrate,
                                 enabled=lambda i: not self.running and not self.busy),
                pystray.Menu.SEPARATOR,
                pystray.MenuItem("Quit", self.on_quit),
            ),
        )

    # --- helpers ---
    def notify(self, msg):
        try:
            self.icon.notify(msg, "Spider AFK")
        except Exception:
            pass  # notifications aren't guaranteed on every backend
        self.icon.title = f"Spider AFK — {msg}"

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
    AFKApp().run()
