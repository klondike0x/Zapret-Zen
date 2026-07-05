<div align="center">

# Zapret Zen

A Windows utility for fast DPI bypass

<picture>
  <img alt="Zapret-Zen banner" src="assets/Hello.png" width="720">
</picture>

[![Python](https://img.shields.io/badge/Python-3.11%2B-3776AB?logo=python&logoColor=white)](https://python.org)
[![PySide6](https://img.shields.io/badge/PySide6-6.7%2B-41CD52?logo=qt&logoColor=white)](https://doc.qt.io/qtforpython/)
[![License](https://img.shields.io/badge/License-MIT-yellow?logo=github)](LICENSE)
[![Version](https://img.shields.io/badge/Version-2.1-blue?logo=github)](https://github.com/peshk0v/Zapret-Zen/releases)

</div>

## 🖼️ Screenshots

<div align="center">

| Dashboard | Services | Mods |
|:---:|:---:|:---:|
| <picture><source media="(prefers-color-scheme: dark)" srcset="assets/screenshot_dashboard_dark.png"><source media="(prefers-color-scheme: light)" srcset="assets/screenshot_dashboard_light.png"><img src="assets/screenshot_dashboard_light.png" width="280" alt="Dashboard"></picture> | <picture><source media="(prefers-color-scheme: dark)" srcset="assets/screenshot_services_dark.png"><source media="(prefers-color-scheme: light)" srcset="assets/screenshot_services_light.png"><img src="assets/screenshot_services_light.png" width="280" alt="Services"></picture> | <picture><source media="(prefers-color-scheme: dark)" srcset="assets/screenshot_mods_dark.png"><source media="(prefers-color-scheme: light)" srcset="assets/screenshot_mods_light.png"><img src="assets/screenshot_mods_light.png" width="280" alt="Mods"></picture> |

</div>

## ⚙️ Features

| Feature | Description |
| :--- | :--- |
| 🛡️ **Bypass blocking** | Manage zapret and tg-ws-proxy components: start, stop, status, autostart |
| 🎛️ **Service presets** | Convenient service selection by categories |
| 🧩 **Mod system** | Install, update and disable community mods that extend rule sets |
| 🎨 **Dynamic themes** | Choose a mode (Light / Dark / OLED) and accent color — the UI adapts in real time |
| 🩺 **Diagnostics** | Built-in system checks: connectivity, DNS, component health |
| ⚙️ **Auto-configuration** | Automatic strategy selection based on chosen services |
| 🔔 **Notifications** | Internal notification system for events and updates |
| 📥 **System tray** | Minimize to tray and launch in tray on autostart |
| 🔄 **Auto-updates** | Check for app and mod updates via GitHub Releases |
| 🌐 **Localization** | Full UI translation in Russian and English |

## 💻 Installation

### Portable (recommended)

1. Download `zapret_zen_<version>_portable_win_<architecture>.zip` from [Releases](https://github.com/peshk0v/Zapret-Zen/releases) for your CPU architecture.
2. Extract to any folder.
3. Run `zapret_zen.exe`.

### Installer

1. Download `install_zapretzen_<version>_universal.exe` from [Releases](https://github.com/peshk0v/Zapret-Zen/releases).
2. Run it — the installer will deploy the app and register it in the installed programs list.

## 📞 Feedback

| Type | Link |
| :--- | :--- |
| 🐛 **Report a bug** | [Create Issue](https://github.com/peshk0v/Zapret-Zen/issues/new) |
| 🤔 **Question or suggestion** | [Go to Discussions](https://github.com/peshk0v/Zapret-Zen/discussions) |
| 📰 **News and updates** | [Subscribe on Telegram](https://t.me/zapzen) |

## 🛠️ For developers

### Requirements

- Python 3.11
- Windows 10+

### Setup

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e .[dev]
```

### Run from source

```powershell
.\.venv\Scripts\python.exe -m zapret_zen.main
```

### Build portable version

```powershell
.\.venv\Scripts\python.exe scripts\sync_app_icon.py
.\.venv\Scripts\pyinstaller.exe packaging/zapret_zen.spec --distpath dist_pyinstaller --workpath build_pyinst --noconfirm
```

### Build installer

```powershell
# After building the portable version, create a payload archive:
$tempDir = Join-Path $env:TEMP "zapretzen_payload"
$payloadRoot = Join-Path $tempDir "zapret_zen"
Copy-Item -LiteralPath dist_pyinstaller\zapret_zen -Destination $payloadRoot -Recurse -Force
Compress-Archive -Path (Join-Path $tempDir "*") -DestinationPath installer_payload\win_x64.zip -CompressionLevel Optimal -Force
Remove-Item $tempDir -Recurse -Force

# Build the installer:
.\.venv\Scripts\pyinstaller.exe packaging/install_zapretzen.spec --distpath dist_installer --workpath build_installer --noconfirm
```

### Project structure

```
Zapret-Zen/
├── assets/           # README assets
├── configs/          # User configs (rule overrides)
├── data/             # App state (settings, profiles, notifications)
├── installer/        # Installer source code
├── mods/             # Installed community mods
├── packaging/        # .spec files for PyInstaller
├── runtime/          # Bundled tools (zapret, tg-ws-proxy, dns-manager)
├── scripts/          # Build, screenshot and utility scripts
├── src/zapret_zen/   # Application source code
│   ├── domain/       # Data models (settings, components, services)
│   ├── services/     # Business logic (backend, settings, merging, updates)
│   └── ui/           # PySide6 interface
├── themes/           # Custom theme JSON files
└── ui_assets/        # Icons, fonts, service logos
```

## 🧲 Third-party projects

| Tool | Author |
|------------|--------|
| [zapret-discord-youtube](https://github.com/Flowseal/zapret-discord-youtube) | **Flowseal** |
| [tg-ws-proxy](https://github.com/Flowseal/tg-ws-proxy) | **Flowseal** |
| [zapret](https://github.com/bol-van/zapret-win-bundle) ecosystem | **bol-van** |

> [!CAUTION]
>
> ### Authorship
> **Zapret Zen** is a modification of the [Zapret Hub](https://github.com/goshkow/Zapret-Hub) project by [goshkow](https://github.com/goshkow).
>
> This application does not claim authorship of the bundled tools, the interface, or the manager built on top of these tools. Users may modify the files themselves, but the authorship of the original projects is retained.
>
> The program itself lists the tools and their authors.

## ©️ License

[MIT](LICENSE)
- - -
<div align="center">
<img width="479" height="113" alt="image" src="https://github.com/user-attachments/assets/c7e3eb82-185f-4786-b2bc-72061fa3b018" />
</div>
