#!/usr/bin/env python3
"""MobGrind — AFK XP-farm macro for a Minecraft mob spawner, with a vision layer.

Works for any spawner you can AFK on (spiders, zombies, skeletons, …). Every
~CLICK_EVERY seconds (with jitter) it left-clicks (attack) then scrolls one
hotbar slot, so your 9 swords rotate and wear evenly. It watches the screen so
it's not just a stopwatch:
  * eats only when your hunger bar actually drops (not on a fixed timer)
  * detects the death screen and stops, so a bad session doesn't run for hours

Setup (macOS):
  1. pip install pyautogui pynput
  2. System Settings > Privacy & Security > Accessibility: allow your terminal
     AND, separately, Screen Recording (needed to read pixels).
  3. Calibrate once:  python3 mobgrind.py --calibrate
  4. Run:             python3 mobgrind.py

Hotkeys while running:  F8 = pause/resume   F9 = quit
(F8/F9 are used because Minecraft doesn't bind them — letter keys would leak
into the game.) Ctrl+C or mouse-to-top-left-corner also stops it.
"""
import argparse
import json
import math
import os
import time

import pyautogui

CALIB_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "mobgrind_calib.json")

# --- tuning knobs ---
CLICK_EVERY = 6.0        # base seconds between attacks
JITTER = 0.6             # +/- random wobble on each interval (less robotic / detectable)
SCROLL_DIR = -1          # -1 scrolls down a slot, 1 up; flip if swords cycle the wrong way
EAT_HOLD = 5.0           # how long to hold right-click to eat (eating needs ~1.6s)
START_DELAY = 10.0       # seconds to tab into the game before it begins

HUNGER_DISTANCE = 60     # RGB distance from "full" color that counts as hungry; raise if it over-eats
FOOD_FALLBACK = 450.0    # eat anyway after this long even if vision missed it (safety net)
EAT_COOLDOWN = 20.0      # don't try to eat again within this many seconds

DEATH_RED_MARGIN = 40    # how much red must beat green+blue avg to look like the death overlay
DEATH_MAX_BRIGHT = 160   # death overlay is dark-ish; ignore bright-red things above this
DEATH_FRACTION = 0.6     # fraction of sampled points that must be red-dark
# death must read positive on two consecutive cycles (~12s) so a hurt-flash doesn't trigger it

pyautogui.FAILSAFE = True  # slam mouse to top-left corner to abort

# --- shared state (toggled by the hotkey listener thread) ---
STATE = {"paused": False, "quit": False}


def color_distance(a, b):
    return math.sqrt(sum((x - y) ** 2 for x, y in zip(a, b)))


def is_red_dark(rgb):
    """True if a pixel looks like the death-screen red overlay."""
    r, g, b = rgb[:3]
    return r - (g + b) / 2 >= DEATH_RED_MARGIN and r <= DEATH_MAX_BRIGHT


def load_calib():
    try:
        with open(CALIB_FILE) as f:
            return json.load(f)
    except FileNotFoundError:
        return None


def calibrate():
    print("Open Minecraft WINDOWED (not fullscreen) with a fairly full hunger bar.")
    print("Click this terminal once to focus it, then move the mouse over each target")
    print("and press Enter here WITHOUT clicking — the mouse stays parked on the spot.\n")
    input("1) Hover over the LEFTMOST hunger haunch (it empties first), then press Enter... ")
    hx, hy = pyautogui.position()
    hcolor = list(pyautogui.pixel(hx, hy))
    print(f"   hunger point ({hx},{hy}) color {tuple(hcolor)}")

    input("2) Hover over the CENTER of your screen, then press Enter... ")
    cx, cy = pyautogui.position()

    save_calib([hx, hy], hcolor, [cx, cy])
    print(f"\nSaved to {CALIB_FILE}. Now run: python3 mobgrind.py")


def save_calib(hunger_xy, hunger_full, center_xy):
    calib = {"hunger_xy": hunger_xy, "hunger_full": hunger_full, "center_xy": center_xy}
    with open(CALIB_FILE, "w") as f:
        json.dump(calib, f, indent=2)
    return calib


def looks_dead(center_xy):
    """Sample a grid around screen center; True if most points are red-dark."""
    cx, cy = center_xy
    hits = total = 0
    for dx in (-200, -100, 0, 100, 200):
        for dy in (-120, 0, 120):
            try:
                if is_red_dark(pyautogui.pixel(cx + dx, cy + dy)):
                    hits += 1
                total += 1
            except Exception:
                pass
    return total > 0 and hits / total >= DEATH_FRACTION


def eat():
    pyautogui.mouseDown(button="right")
    time.sleep(EAT_HOLD)
    pyautogui.mouseUp(button="right")


def is_hungry(calib):
    if not calib:
        return False
    px = pyautogui.pixel(*calib["hunger_xy"])
    return color_distance(px, calib["hunger_full"]) >= HUNGER_DISTANCE


def run(calib, stop, paused, log=print):
    """Core macro loop. stop() and paused() are callables; log(msg) reports events.

    Returns (clicks, meals, minutes). Shared by the CLI and the tray app so the
    attack/eat/death logic lives in exactly one place.
    """
    import random
    last_eat = 0.0
    death_streak = 0
    clicks = meals = 0
    started = time.monotonic()

    while not stop():
        if paused():
            time.sleep(0.3)
            continue

        now = time.monotonic()

        # death check (calibrated runs only) — needs two positive cycles in a row
        if calib:
            if looks_dead(calib["center_xy"]):
                death_streak += 1
                if death_streak >= 2:
                    log("Looks like you died — stopping. Check the game.")
                    break
            else:
                death_streak = 0

        # eat when actually hungry, or as a timed fallback, respecting a cooldown
        if now - last_eat >= EAT_COOLDOWN and (is_hungry(calib) or now - last_eat >= FOOD_FALLBACK):
            eat()
            meals += 1
            last_eat = time.monotonic()

        pyautogui.click()               # attack
        pyautogui.scroll(SCROLL_DIR)    # next sword
        clicks += 1
        time.sleep(max(0.5, CLICK_EVERY + random.uniform(-JITTER, JITTER)))

    return clicks, meals, (time.monotonic() - started) / 60


def start_hotkeys():
    try:
        from pynput import keyboard
    except ImportError:
        print("(pynput not installed — hotkeys off. `pip install pynput` for F8/F9.)")
        return

    def on_press(key):
        if key == keyboard.Key.f8:
            STATE["paused"] = not STATE["paused"]
            print("[paused]" if STATE["paused"] else "[resumed]")
        elif key == keyboard.Key.f9:
            STATE["quit"] = True

    keyboard.Listener(on_press=on_press, daemon=True).start()


def main():
    calib = load_calib()
    if not calib:
        print("No calibration found — eating on a timer and skipping death detection.")
        print("Run `python3 mobgrind.py --calibrate` for the smart version.\n")

    start_hotkeys()
    print(f"Starting in {START_DELAY:.0f}s — click into Minecraft. F8 pause, F9 quit.")
    time.sleep(START_DELAY)

    clicks, meals, mins = run(
        calib,
        stop=lambda: STATE["quit"],
        paused=lambda: STATE["paused"],
        log=lambda m: print("\a\n" + m),
    )
    print(f"\nDone. {mins:.1f} min, {clicks} attacks, {meals} meals.")


def selftest():
    assert color_distance((0, 0, 0), (0, 0, 0)) == 0
    assert round(color_distance((0, 0, 0), (3, 4, 0))) == 5
    assert is_red_dark((120, 20, 20))          # dark red overlay -> dead
    assert not is_red_dark((240, 30, 30))      # bright red (hurt flash / blocks) -> not
    assert not is_red_dark((100, 100, 100))    # grey HUD -> not
    print("selftest ok")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--calibrate", action="store_true")
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args()
    try:
        if args.selftest:
            selftest()
        elif args.calibrate:
            calibrate()
        else:
            main()
    except KeyboardInterrupt:
        print("\nStopped.")
