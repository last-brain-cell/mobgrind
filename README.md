# SpiderAFK

AFK XP-farm macro for a Minecraft spider spawner, with a tray-icon app for macOS
and Windows. Clicks to attack on a jittered interval, scrolls one hotbar slot
each swing so your 9 swords wear evenly, and watches the screen to eat only when
you're actually hungry and to stop if you die.

> Most servers ban auto-clickers. Use it on your own world or where it's allowed.

## Download

Grab the latest build from the [**Releases**](../../releases/latest) page —
`SpiderAFK-macOS.zip` or `SpiderAFK-Windows.exe`. No Python, no cloning.

- **macOS:** unzip, then run once to clear Gatekeeper:
  `xattr -dr com.apple.quarantine SpiderAFK.app` (or System Settings → Privacy &
  Security → "Open Anyway"). First launch asks for Accessibility + Screen
  Recording — grant both and relaunch.
- **Windows:** run the `.exe`. SmartScreen may warn on the unsigned build — "More
  info" → "Run anyway".

## Run from source

```
pip install -r requirements.txt
python3 spider_afk_app.py      # tray app (Start / Pause / Calibrate / Quit)
# or headless CLI:
python3 spider_afk.py --calibrate
python3 spider_afk.py          # F8 pause/resume, F9 quit
```

macOS: grant **Accessibility** and **Screen Recording** to whatever launches it
(your terminal, or the built .app) in System Settings → Privacy & Security.

## Calibrate

Point it at your HUD once so the vision layer works. In the tray app use
**Calibrate** (two 5-second countdowns); from the CLI use `--calibrate`. You hover
the leftmost hunger haunch, then the screen center. Without calibration it falls
back to timer-based eating and no death detection.

## Build a downloadable binary

PyInstaller is not a cross-compiler — build on the OS you target.

```
pip install pyinstaller

# macOS  -> dist/SpiderAFK.app
pyinstaller --name SpiderAFK --windowed --onedir \
  --hidden-import pynput.keyboard._darwin --hidden-import pynput.mouse._darwin \
  spider_afk_app.py

# Windows -> dist\SpiderAFK.exe
pyinstaller --name SpiderAFK --windowed --onefile \
  --hidden-import pynput.keyboard._win32 --hidden-import pynput.mouse._win32 \
  spider_afk_app.py
```

Unsigned builds trip Gatekeeper (macOS) and SmartScreen (Windows). For your own
machine, clear the macOS quarantine with
`xattr -dr com.apple.quarantine dist/SpiderAFK.app`. Distributing to other people
cleanly needs code signing + notarization (Apple Developer account; a Windows
signing cert).

## Tuning

The knobs live at the top of `spider_afk.py` — click interval, jitter, scroll
direction, eat hold/cooldown, hunger sensitivity, and the death-detection
thresholds. They're thresholds against your setup, so expect to tune them.
