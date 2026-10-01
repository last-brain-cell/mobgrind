# MobGrind

AFK XP-farm macro for Minecraft mob spawners, with a tray-icon app for macOS and
Windows. Works for any spawner you can AFK on (spiders, zombies, skeletons, …).
It clicks to attack on a jittered interval, scrolls one hotbar slot each swing so
your 9 swords wear evenly, and watches the screen to eat only when you're actually
hungry and to stop if you die.

> Most servers ban auto-clickers. Use it on your own world or where it's allowed.

## Download

Grab the latest build from the [**Releases**](../../releases/latest) page —
`MobGrind-macOS.dmg` or `MobGrind-Windows.exe`. No Python, no cloning.

- **macOS:** open the `.dmg`, drag MobGrind into Applications. On an unsigned
  build, clear Gatekeeper once:
  `xattr -dr com.apple.quarantine /Applications/MobGrind.app` (or System Settings
  → Privacy & Security → "Open Anyway"). First launch asks for Accessibility +
  Screen Recording — grant both and relaunch.
- **Windows:** run the `.exe`. SmartScreen may warn on the unsigned build — "More
  info" → "Run anyway".

## Run from source

```
pip install -r requirements.txt
python3 mobgrind_app.py      # tray app (Start / Pause / Calibrate / Quit)
# or headless CLI:
python3 mobgrind.py --calibrate
python3 mobgrind.py          # F8 pause/resume, F9 quit
```

macOS: grant **Accessibility** and **Screen Recording** to whatever launches it
(your terminal, or the built .app) in System Settings → Privacy & Security.

## Calibrate

Point it at your HUD once so the vision layer works. In the tray app use
**Calibrate** (two 5-second countdowns); from the CLI use `--calibrate`. You hover
the leftmost hunger haunch, then the screen center. Without calibration it falls
back to timer-based eating and no death detection.

## Build a downloadable binary

CI does this for you on tag push (see `.github/workflows/release.yml`). To build
by hand, PyInstaller is not a cross-compiler — build on the OS you target:

```
pip install pyinstaller

# macOS  -> dist/MobGrind.app
pyinstaller --name MobGrind --windowed --onedir \
  --hidden-import pynput.keyboard._darwin --hidden-import pynput.mouse._darwin \
  mobgrind_app.py

# Windows -> dist\MobGrind.exe
pyinstaller --name MobGrind --windowed --onefile \
  --hidden-import pynput.keyboard._win32 --hidden-import pynput.mouse._win32 \
  mobgrind_app.py
```

Unsigned builds trip Gatekeeper (macOS) and SmartScreen (Windows). For your own
machine, clear the macOS quarantine with
`xattr -dr com.apple.quarantine dist/MobGrind.app`. Distributing to other people
cleanly needs code signing + notarization (Apple Developer account; a Windows
signing cert).

## Release

```
git tag v1.2.0 && git push origin v1.2.0
```

CI builds both binaries and attaches them to the matching Release.

## Tuning

The knobs live at the top of `mobgrind.py` — click interval, jitter, scroll
direction, eat hold/cooldown, hunger sensitivity, and the death-detection
thresholds. They're thresholds against your setup, so expect to tune them.
