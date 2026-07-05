"""
Screenshot capture script for Zapret-Zen README.
Takes PNG screenshots of each main page in light and dark themes, with rounded corners.
Usage: .venv\Scripts\python.exe scripts\take_screenshots.py
"""

import sys
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT))

OUTPUT = ROOT / "assets"
OUTPUT.mkdir(parents=True, exist_ok=True)

RADIUS = 18
PAGES = [(0, "dashboard"), (1, "services"), (3, "mods")]
THEMES = ["light", "dark"]

_CATALOG_DATA = [
    {
        "Title": "Unified Pack",
        "Description": "Объединённый набор правил для обхода блокировок популярных сервисов: Discord, YouTube, Twitter/X, Reddit и других.",
        "Author": "peshk0v",
        "Tag": "unified-by-peshk0v",
        "Version": "1.9.9",
    },
    {
        "Title": "Gaming Pack",
        "Description": "Правила для игровых сервисов: Steam, Epic Games, Ubisoft Connect, Rockstar Launcher, Minecraft.",
        "Author": "peshk0v",
        "Tag": "gaming-by-peshk0v",
        "Version": "2.1.0",
    },
    {
        "Title": "Social Pack",
        "Description": "Базовый набор для социальных сетей и мессенджеров: Telegram, VK, Instagram.",
        "Author": "community",
        "Tag": "social-by-community",
        "Version": "1.3.0",
    },
    {
        "Title": "Cloudflare Bypass",
        "Description": "Дополнительные стратегии обхода для сервисов, защищённых Cloudflare.",
        "Author": "peshk0v",
        "Tag": "cloudflare-bypass",
        "Version": "1.0.5",
    },
    {
        "Title": "Media Pack",
        "Description": "Правила для стриминговых сервисов: Twitch, YouTube, Kick, SoundCloud.",
        "Author": "modder_x",
        "Tag": "media-streaming",
        "Version": "0.8.2",
    },
    {
        "Title": "DPI Light",
        "Description": "Минимальный набор правил для обхода DPI без лишних стратегий.",
        "Author": "light-user",
        "Tag": "dpi-light",
        "Version": "1.0.0",
    },
]


def main():
    import multiprocessing
    multiprocessing.freeze_support()

    from PySide6.QtCore import QTimer, QCoreApplication
    from PySide6.QtWidgets import QApplication

    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    app.setApplicationName("Zapret-Zen")
    app.setOrganizationName("ZapretZen")

    from zapret_zen.bootstrap import bootstrap_application, build_startup_snapshot

    print("Bootstrapping...")
    try:
        ctx = bootstrap_application()
    except Exception as e:
        import traceback
        traceback.print_exc()
        return 1

    print("Building startup snapshot...")
    try:
        snap = build_startup_snapshot(ctx)
    except Exception as e:
        import traceback
        traceback.print_exc()
        return 1

    ctx.backend = None
    ctx.settings.update(theme="light")

    print("Creating MainWindow...")
    from zapret_zen.ui.main_window import MainWindow

    window = MainWindow(
        ctx,
        launch_hidden=False,
        startup_show_onboarding=False,
        startup_snapshot=snap if isinstance(snap, dict) else None,
        skip_autosettings=True,
    )
    app._screenshot_window = window

    window._submit_backend_task = lambda *a, **kw: None
    window._settings_dialog = None
    window._prime_cached_dialogs = lambda: None

    from PIL import Image, ImageDraw

    def grab_pil(widget):
        pixmap = widget.grab()
        qimg = pixmap.toImage()
        w, h = qimg.width(), qimg.height()
        ptr = qimg.constBits()
        arr = bytes(ptr)
        return Image.frombuffer("RGBA", (w, h), arr, "raw", "BGRA", 0, 1)

    def round_corners(img, radius=RADIUS):
        mask = Image.new("L", img.size, 0)
        draw = ImageDraw.Draw(mask)
        draw.rounded_rectangle((0, 0, img.width, img.height), radius=radius, fill=255)
        result = img.copy()
        result.putalpha(mask)
        return result

    def open_mods_catalog():
        mods_page = window._mods_page
        mods_page._catalog_data = list(_CATALOG_DATA)
        mods_page._catalog_loaded = True
        mods_page._catalog_installed_ids = {"unified-by-peshk0v", "gaming-by-peshk0v"}
        mods_page._catalog_installed_versions = {"unified-by-peshk0v": "1.9.9", "gaming-by-peshk0v": "2.1.0"}
        mods_page._show_catalog()

    def close_mods_catalog():
        mods_page = window._mods_page
        mods_page._show_local()

    theme_queue = list(THEMES)
    page_queue = []

    def start_theme_cycle():
        if not theme_queue:
            print("All screenshots done, quitting...")
            QTimer.singleShot(200, app.quit)
            return
        theme = theme_queue.pop()
        print(f"\n=== Theme: {theme} ===")
        ctx.settings.update(theme=theme)
        window._apply_theme()
        page_queue.extend([(idx, name, theme) for idx, name in reversed(PAGES)])
        QTimer.singleShot(500, capture_next)

    def capture_next():
        if not page_queue:
            QTimer.singleShot(200, start_theme_cycle)
            return
        idx, name, theme = page_queue.pop()
        print(f"  Switching to page {idx} ({name})...")
        window._switch_page(idx)
        if name == "mods":
            QTimer.singleShot(600, lambda n=name, t=theme: open_mods_catalog() or QTimer.singleShot(400, lambda n=n, t=t: do_capture(n, t)))
        else:
            QTimer.singleShot(1000, lambda n=name, t=theme: do_capture(n, t))

    def do_capture(name, theme):
        QCoreApplication.processEvents()
        try:
            img = grab_pil(window)
            rounded = round_corners(img)
            path = OUTPUT / f"screenshot_{name}_{theme}.png"
            rounded.save(str(path), "PNG")
            print(f"    Saved: {path} ({img.width}x{img.height})")
        except Exception as e:
            import traceback
            print(f"    Error: {e}")
            traceback.print_exc()
        if name == "mods":
            QTimer.singleShot(100, lambda: close_mods_catalog())
        QTimer.singleShot(200, capture_next)

    print("Showing window...")
    window.show()
    QTimer.singleShot(3000, start_theme_cycle)

    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
