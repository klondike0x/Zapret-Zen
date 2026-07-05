from __future__ import annotations

import json
import shutil
import time
from dataclasses import asdict, fields, is_dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from zapret_zen.domain import AppPaths
from zapret_zen.ui.theme import ensure_theme_files


class StorageManager:
    def __init__(self, paths: AppPaths) -> None:
        self.paths = paths

    def ensure_layout(self) -> None:
        for field_info in fields(self.paths):
            path = getattr(self.paths, field_info.name)
            if isinstance(path, Path):
                path.mkdir(parents=True, exist_ok=True)
        self._ensure_sample_files()
        ensure_theme_files(self.paths.themes_dir)

    def _ensure_sample_files(self) -> None:
        components_file = self.paths.data_dir / "components.json"
        zapret_version = self._detect_zapret_version()
        tg_version = self._detect_tgws_version()
        default_components = [
            {
                "id": "zapret",
                "name": "Zapret",
                "description": "РћСЃРЅРѕРІРЅРѕР№ РјРѕРґСѓР»СЊ РѕР±С…РѕРґР° Р±Р»РѕРєРёСЂРѕРІРѕРє РґР»СЏ СЃР°Р№С‚РѕРІ Рё СЃРµСЂРІРёСЃРѕРІ.",
                "version": zapret_version,
                "source": "https://github.com/Flowseal/zapret-discord-youtube",
                "command": ["cmd.exe", "/c", "general.bat"],
                "enabled": True,
                "autostart": False,
            },

            {
                "id": "tg-ws-proxy",
                "name": "Tg-Ws-Proxy",
                "description": "Прокси для Telegram через локальный порт.",
                "version": tg_version,
                "source": "https://github.com/Flowseal/tg-ws-proxy",
                "command": ["TgWsProxy_windows.exe"],
                "enabled": True,
                "autostart": False,
            },
            {
                "id": "dns-manager",
                "name": "DNS Manager",
                "description": "Управление DNS-серверами Windows.",
                "version": "1.1",
                "source": "https://github.com/peshk0v/Zapret-Zen",
                "command": [],
                "enabled": False,
                "autostart": False,
            },
        ]
        existing = self.read_json(components_file, default=[]) or []
        by_id = {item.get("id"): item for item in existing if isinstance(item, dict)}
        normalized_components: list[dict[str, Any]] = []
        for default_item in default_components:
            merged = dict(default_item)
            current = by_id.get(default_item["id"])
            if isinstance(current, dict):
                merged["enabled"] = bool(current.get("enabled", merged["enabled"]))
                merged["autostart"] = bool(current.get("autostart", merged["autostart"]))
            normalized_components.append(merged)
        if existing != normalized_components:
            self.write_json(components_file, normalized_components)

        profiles_file = self.paths.data_dir / "profiles.json"
        if not profiles_file.exists():
            self.write_json(
                profiles_file,
                [
                    {
                        "id": "default",
                        "name": "Default",
                        "description": "Default operational profile",
                        "base_config_path": str(self.paths.default_packs_dir),
                    }
                ],
            )

        settings_file = self.paths.data_dir / "settings.json"
        if not settings_file.exists():
            self.write_json(settings_file, {})

        self._ensure_default_bundled_mod_and_index(settings_file)

        base_config = self.paths.default_packs_dir / "base_config.json"
        if not base_config.exists():
            self.write_json(
                base_config,
                {
                    "rules": ["base-rule-1", "base-rule-2"],
                    "dns": {"primary": "1.1.1.1", "secondary": "8.8.8.8"},
                },
            )

        readme_hint = self.paths.configs_dir / "README.txt"
        if not readme_hint.exists():
            readme_hint.write_text(
                "This folder contains editable user configuration files for Zapret-Zen.\n",
                encoding="utf-8",
            )

        for filename in ("list-general-user.txt", "list-exclude-user.txt", "ipset-all-user.txt", "ipset-exclude-user.txt"):
            path = self.paths.configs_dir / filename
            if not path.exists():
                path.write_text("", encoding="utf-8")

        self._ensure_icon_assets()

    def _detect_zapret_version(self) -> str:
        service_bat = self.paths.runtime_dir / "zapret-discord-youtube" / "service.bat"
        if not service_bat.exists():
            return "unknown"
        try:
            for line in service_bat.read_text(encoding="utf-8", errors="ignore").splitlines():
                if "LOCAL_VERSION" not in line:
                    continue
                value = line.split("=", 1)[-1].strip().strip('"').strip()
                value = value.replace("set", "").replace("LOCAL_VERSION", "").replace("=", "").strip('" ').strip()
                if value:
                    return value
        except Exception:
            return "unknown"
        return "unknown"

    def _detect_tgws_version(self) -> str:
        pyproject = self.paths.runtime_dir / "tg-ws-proxy" / "pyproject.toml"
        init_py = self.paths.runtime_dir / "tg-ws-proxy" / "proxy" / "__init__.py"
        try:
            if init_py.exists():
                for line in init_py.read_text(encoding="utf-8", errors="ignore").splitlines():
                    stripped = line.strip()
                    if stripped.startswith("__version__") and "=" in stripped:
                        return stripped.split("=", 1)[-1].strip().strip('"').strip("'")
            if pyproject.exists():
                for line in pyproject.read_text(encoding="utf-8", errors="ignore").splitlines():
                    stripped = line.strip()
                    if stripped.startswith("version") and "=" in stripped:
                        return stripped.split("=", 1)[-1].strip().strip('"').strip("'")
        except Exception:
            return "unknown"
        return "unknown"

    def _ensure_default_bundled_mod_and_index(self, settings_file: Path) -> None:
        legacy_mod_id = "gaming-by-peshk0v"
        default_mod_id = "unified-by-peshk0v"
        default_mod_meta = {
            "id": default_mod_id,
            "name": "Hub",
            "description": "Позволяет обойти блокировки самых популярных сервисов, включая игровые сервисы, социальные сети и другие платформы.",
            "author": "peshk0v",
            "version": "1.9.9a-unified3",
            "source_url": "bundled://unified-by-peshk0v",
            "category": "gaming",
            "tags": ["gaming", "social", "cloudflare", "ubisoft", "arc-raiders"],
            "dependencies": [],
            "conflicts": [],
            "changelog": "Default unified bundle included.",
        }

        installed_path = self.paths.data_dir / "installed_mods.json"
        installed = self.read_json(installed_path, default=[]) or []
        if not isinstance(installed, list):
            installed = []
        existing_default = next(
            (
                item
                for item in installed
                if isinstance(item, dict) and item.get("id") == default_mod_id
            ),
            None,
        )
        desired_version = str(default_mod_meta.get("version", "1.9.9a-unified2"))
        default_bundle = self._ensure_default_bundled_mod(
            default_mod_id,
            default_mod_meta,
            force_refresh=not isinstance(existing_default, dict) or str(existing_default.get("version", "")) != desired_version,
        )

        mods_index_path = self.paths.cache_dir / "mods_index.json"
        mods_index = self.read_json(mods_index_path, default=[]) or []
        if not isinstance(mods_index, list):
            mods_index = []
        filtered_index: list[dict[str, Any]] = []
        for item in mods_index:
            if not isinstance(item, dict):
                continue
            if item.get("id") in {"sample-hosts-pack", legacy_mod_id}:
                continue
            filtered_index.append(item)
        if not any(isinstance(item, dict) and item.get("id") == default_mod_id for item in filtered_index):
            filtered_index.append(default_mod_meta)
        if mods_index != filtered_index:
            self.write_json(mods_index_path, filtered_index)

        cleaned_installed: list[dict[str, Any]] = []
        legacy_enabled = False
        for item in installed:
            if not isinstance(item, dict):
                continue
            if item.get("id") == "sample-hosts-pack":
                continue
            if item.get("id") == legacy_mod_id:
                legacy_enabled = bool(item.get("enabled"))
                continue
            cleaned_installed.append(item)
        if default_bundle is not None:
            existing_default = next((item for item in cleaned_installed if item.get("id") == default_mod_id), None)
            if existing_default is None:
                default_bundle["enabled"] = legacy_enabled
                cleaned_installed.append(default_bundle)
            else:
                existing_default.update(
                    {
                        "path": default_bundle["path"],
                        "version": default_bundle["version"],
                        "name": default_bundle.get("name", ""),
                        "author": default_bundle.get("author", ""),
                        "description": default_bundle.get("description", ""),
                        "source_url": default_bundle.get("source_url", ""),
                        "source_type": default_bundle.get("source_type", "zapret_bundle"),
                        "general_scripts": default_bundle.get("general_scripts", []),
                    }
                )
        if installed != cleaned_installed:
            self.write_json(installed_path, cleaned_installed)

        settings_data = self.read_json(settings_file, default={}) or {}
        if isinstance(settings_data, dict):
            enabled_mods = settings_data.get("enabled_mod_ids", [])
            if isinstance(enabled_mods, list):
                normalized_enabled = [m for m in enabled_mods if m not in {"sample-hosts-pack", legacy_mod_id}]
                if legacy_mod_id in enabled_mods and default_mod_id not in normalized_enabled:
                    normalized_enabled.append(default_mod_id)
                if normalized_enabled != enabled_mods:
                    settings_data["enabled_mod_ids"] = normalized_enabled
                    self.write_json(settings_file, settings_data)

        legacy_dir = self.paths.mods_dir / legacy_mod_id
        if legacy_dir.exists():
            shutil.rmtree(legacy_dir, ignore_errors=True)

    def _ensure_default_bundled_mod(
        self,
        mod_id: str,
        meta: dict[str, Any],
        *,
        force_refresh: bool = False,
    ) -> dict[str, Any] | None:
        sample_root = self.paths.install_root / "sample_data" / "default_mods" / mod_id
        source_candidates = [
            sample_root,
            self.paths.runtime_dir / "zapret-discord-youtube",
            Path(r"C:\zapret-discord-youtube-1.9.7"),
        ]
        source_root = next((path for path in source_candidates if self._looks_like_zapret_bundle(path)), None)
        if source_root is None:
            return None

        target_dir = self.paths.mods_dir / mod_id
        if force_refresh or not self._looks_like_materialized_mod_bundle(target_dir):
            self._copy_filtered_zapret_bundle(source_root, target_dir, skip_base_duplicates=source_root != sample_root)

        general_scripts = sorted(
            script.name
            for script in target_dir.glob("*.bat")
            if not script.name.lower().startswith("service")
        )
        return {
            "id": mod_id,
                "version": str(meta.get("version", "1.9.9a-unified2")),
            "path": str(target_dir),
            "enabled": False,
            "name": str(meta.get("name", "")),
            "author": str(meta.get("author", "")),
            "description": str(meta.get("description", "")),
            "source_url": str(meta.get("source_url", "")),
            "source_type": "zapret_bundle",
            "general_scripts": general_scripts,
            "emoji": "🪄",
        }

    def _looks_like_materialized_mod_bundle(self, path: Path) -> bool:
        if not path.exists():
            return False
        has_general = any(
            script.is_file() and not script.name.lower().startswith("service")
            for script in path.glob("*.bat")
        )
        return has_general and (path / "bin").is_dir() and (path / "lists").is_dir()

    def _looks_like_zapret_bundle(self, path: Path) -> bool:
        return (path / "bin").is_dir() and (path / "lists").is_dir()

    def _copy_filtered_zapret_bundle(self, source_root: Path, target_dir: Path, *, skip_base_duplicates: bool = True) -> None:
        base_general_names = set()
        if skip_base_duplicates:
            base_general_names = {
                item.name.lower()
                for item in (self.paths.runtime_dir / "zapret-discord-youtube").glob("*.bat")
                if not item.name.lower().startswith("service")
            }
        if target_dir.exists():
            shutil.rmtree(target_dir, ignore_errors=True)
        target_dir.mkdir(parents=True, exist_ok=True)

        for script in source_root.glob("*.bat"):
            if script.name.lower().startswith("service"):
                continue
            if script.name.lower() in base_general_names:
                continue
            shutil.copy2(script, target_dir / script.name)

        for folder in ("bin", "lists", "utils"):
            (target_dir / folder).mkdir(parents=True, exist_ok=True)

        bin_suffixes = {".exe", ".dll", ".bin", ".sys", ".cmd"}
        for item in (source_root / "bin").glob("*"):
            if not item.is_file():
                continue
            if item.suffix.lower() in bin_suffixes:
                (target_dir / "bin").mkdir(parents=True, exist_ok=True)
                shutil.copy2(item, target_dir / "bin" / item.name)

        for item in (source_root / "lists").glob("*.txt"):
            (target_dir / "lists").mkdir(parents=True, exist_ok=True)
            shutil.copy2(item, target_dir / "lists" / item.name)

        base_utils = self.paths.runtime_dir / "zapret-discord-youtube" / "utils"
        if base_utils.exists():
            for item in base_utils.glob("*"):
                if item.is_file():
                    (target_dir / "utils").mkdir(parents=True, exist_ok=True)
                    shutil.copy2(item, target_dir / "utils" / item.name)

        source_utils = source_root / "utils"
        if source_utils.exists():
            for item in source_utils.glob("*"):
                if item.is_file():
                    (target_dir / "utils").mkdir(parents=True, exist_ok=True)
                    shutil.copy2(item, target_dir / "utils" / item.name)

    def _ensure_icon_assets(self) -> None:
        icons_dir = self.paths.ui_assets_dir / "icons"
        icons_dir.mkdir(parents=True, exist_ok=True)
        bundled_dir = Path(__file__).resolve().parent.parent / "assets" / "icons"
        for svg_file in sorted(bundled_dir.glob("*.svg")):
            target = icons_dir / svg_file.name
            if target.exists():
                continue
            target.write_text(svg_file.read_text(encoding="utf-8"), encoding="utf-8")

    def read_json(self, path: Path, default: Any | None = None) -> Any:
        if not path.exists():
            return default
        try:
            content = path.read_text(encoding="utf-8-sig")
        except OSError:
            return default
        if not content.strip():
            self._backup_invalid_json(path, "empty")
            return default
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            self._backup_invalid_json(path, "invalid")
            return default

    def write_json(self, path: Path, payload: Any) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        data = asdict(payload) if is_dataclass(payload) else payload
        temp_path = path.with_name(f"{path.name}.tmp-{datetime.utcnow().strftime('%Y%m%d%H%M%S%f')}")
        try:
            with temp_path.open("w", encoding="utf-8") as file:
                json.dump(data, file, indent=2, ensure_ascii=False)
                file.write("\n")
            for attempt in range(3):
                try:
                    temp_path.replace(path)
                    break
                except PermissionError:
                    if attempt < 2:
                        time.sleep(0.1)
                    else:
                        with path.open("w", encoding="utf-8") as f:
                            json.dump(data, f, indent=2, ensure_ascii=False)
                            f.write("\n")
        finally:
            if temp_path.exists():
                try:
                    temp_path.unlink()
                except OSError:
                    pass

    def _backup_invalid_json(self, path: Path, reason: str) -> None:
        if not path.exists():
            return
        stamp = datetime.utcnow().strftime("%Y%m%d-%H%M%S-%f")
        backup_path = path.with_name(f"{path.name}.{reason}-{stamp}.bak")
        try:
            shutil.copy2(path, backup_path)
        except OSError:
            pass

    def create_backup(self, source: Path, reason: str) -> Path:
        stamp = datetime.utcnow().strftime("%Y%m%d-%H%M%S")
        backup_dir = self.paths.backups_dir / f"{stamp}-{reason}"
        backup_dir.mkdir(parents=True, exist_ok=True)
        destination = backup_dir / source.name
        if source.is_dir():
            shutil.copytree(source, destination, dirs_exist_ok=True)
        elif source.exists():
            shutil.copy2(source, destination)
        return backup_dir

