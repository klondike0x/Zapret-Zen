from __future__ import annotations

from dataclasses import asdict
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse
import json
import re
import random
import shutil
import tempfile
import zipfile
import random
import ctypes
import sys

from zapret_zen import __version__
from zapret_zen.domain import InstalledMod, ModIndexItem
from zapret_zen.services.github_network import GitHubNetworkClient
from zapret_zen.services.logging_service import LoggingManager
from zapret_zen.services.merge import MergeEngine
from zapret_zen.services.settings import SettingsManager
from zapret_zen.services.storage import StorageManager

_MODS_REPO_OWNER = "peshk0v"
_MODS_REPO = "Zapret-Mods"
_MODS_REPO_BRANCH = "master"
_MODS_REPO_URL = f"https://github.com/{_MODS_REPO_OWNER}/{_MODS_REPO}"
_MODS_RAW_BASE = f"https://raw.githubusercontent.com/{_MODS_REPO_OWNER}/{_MODS_REPO}/{_MODS_REPO_BRANCH}"
_MODS_MIRROR_BASE = f"https://cdn.jsdelivr.net/gh/{_MODS_REPO_OWNER}/{_MODS_REPO}@{_MODS_REPO_BRANCH}"
_MODS_CONTENTS_API = f"https://api.github.com/repos/{_MODS_REPO_OWNER}/{_MODS_REPO}/contents"
_MODS_TREE_API = f"https://data.jsdelivr.com/v1/packages/gh/{_MODS_REPO_OWNER}/{_MODS_REPO}@{_MODS_REPO_BRANCH}"
_MODS_CATALOG_FILE = "mods_catalog.json"
_MODS_SKIP_DIRS = {".github", ".git"}
_MODS_REPO_FILE_SUFFIXES = {".bat", ".txt", ".ps1", ".json", ".enabled"}
_REPO_CATALOG_TTL_SECONDS = 6 * 3600

_MOD_SETTING_ENUMS = {
    "zapret_ipset_mode": {"loaded", "none", "any"},
    "zapret_game_filter_mode": {"disabled", "tcp", "udp", "tcpudp"},
    "tg_proxy_media_mode": {"default", "media_fix", "empty"},
}
_MOD_SETTING_STRINGS = {
    "zapret_udp_exclude_ports",
    "tg_proxy_host",
    "tg_proxy_dc_ip",
    "tg_proxy_cfproxy_domain",
    "tg_proxy_fake_tls_domain",
}
_MOD_SETTING_BOOLS = {"tg_proxy_cfproxy_enabled", "tg_proxy_cfproxy_priority"}
_MOD_SETTING_PORTS = {"tg_proxy_port"}
_MOD_SETTING_POSITIVE_INTS = {"tg_proxy_buf_kb", "tg_proxy_pool_size"}
MOD_SETTING_KEYS = (
    set(_MOD_SETTING_ENUMS) | _MOD_SETTING_STRINGS | _MOD_SETTING_BOOLS
    | _MOD_SETTING_PORTS | _MOD_SETTING_POSITIVE_INTS
)


def _normalize_mod_setting(key: str, value: object) -> object | None:
    if key in _MOD_SETTING_ENUMS:
        text = str(value).strip().lower()
        if key == "zapret_game_filter_mode" and text == "all":
            return "tcpudp"
        return text if text in _MOD_SETTING_ENUMS[key] else None
    if key in _MOD_SETTING_BOOLS:
        if isinstance(value, bool):
            return value
        return str(value).strip().lower() in {"1", "true", "yes", "on"}
    if key in _MOD_SETTING_PORTS:
        try:
            port = int(value)
        except (TypeError, ValueError):
            return None
        return port if 1 <= port <= 65535 else None
    if key in _MOD_SETTING_POSITIVE_INTS:
        try:
            number = int(value)
        except (TypeError, ValueError):
            return None
        return number if number > 0 else None
    if key in _MOD_SETTING_STRINGS:
        return str(value).strip()
    return None


class ModsManager:
    METADATA_FILENAME = "mod.json"
    UNKNOWN_AUTHOR = "неизвестен"
    ALLOWED_MOD_SUFFIXES = {".txt", ".ps1", ".bat", ".json"}
    _EMOJI_CHOICES = ["✨", "🪄", "🔥", "⚡", "🧩", "🎮", "🌐", "🛡️", "🚀", "💎", "📦", "🧪"]
    def __init__(
        self,
        storage: StorageManager,
        logging: LoggingManager,
        merge: MergeEngine,
        settings: SettingsManager,
        *,
        processes: object | None = None,
    ) -> None:
        self.storage = storage
        self.logging = logging
        self.merge = merge
        self.settings = settings
        recovery = getattr(processes, "with_github_connectivity_recovery", None)
        self.github = GitHubNetworkClient(logging, recovery_runner=recovery if callable(recovery) else None)
        self._repo_file_base: str | None = None
        self._repo_tree: list[object] | None = None
        self._repo_catalog: dict[str, dict[str, str]] = {}
        self._repo_discovered = False
        self._installed_path = self.storage.paths.data_dir / "installed_mods.json"
        if not self._installed_path.exists():
            self.storage.write_json(self._installed_path, [])
        self._cleanup_orphaned_installed()
        self._cleanup_installed_duplicate_generals()

    _STALE_INDEX_IDS = {"unified-by-peshk0v"}

    def fetch_index(self, *, refresh_remote: bool = False) -> list[ModIndexItem]:
        settings = self.settings.get()
        cache_path = self.storage.paths.cache_dir / "mods_index.json"
        if settings.mods_index_url:
            if refresh_remote:
                try:
                    payload = self.github.github_json(settings.mods_index_url, timeout=10, purpose="mods-index", retry=False)
                    if isinstance(payload, list):
                        payload = [item for item in payload if isinstance(item, dict) and item.get("id") not in self._STALE_INDEX_IDS]
                    self.storage.write_json(cache_path, payload)
                    self.logging.log("info", "Mods index refreshed from URL", url=settings.mods_index_url)
                except Exception as error:
                    self.logging.log("warning", "Failed to refresh mods index from URL", url=settings.mods_index_url, error=str(error))
        elif not self._repo_discovered and (refresh_remote or not self._repo_catalog_present_and_fresh()):
            self._repo_discovered = True
            try:
                self.discover_repo_catalog()
            except Exception as error:
                self.logging.log("warning", "Failed to discover Zapret-Mods catalog", error=str(error))
        raw = self.storage.read_json(cache_path, default=[]) or []
        if isinstance(raw, list):
            raw = [item for item in raw if isinstance(item, dict) and item.get("id") not in self._STALE_INDEX_IDS]
        return [ModIndexItem(**item) for item in raw]

    def discover_repo_catalog(self) -> bool:
        file_base = self._select_repo_file_base()
        if not file_base:
            self.logging.log("info", "Zapret-Mods sources unavailable, catalog skipped")
            return False
        folders = self._repo_mod_folders()
        if not folders:
            self.logging.log("warning", "Zapret-Mods folders listing unavailable")
            return False
        catalog: list[dict[str, object]] = []
        catalog_data: dict[str, dict[str, str]] = {}
        seen_ids: set[str] = set()
        for folder in folders:
            try:
                meta = self._repo_mod_metadata(file_base, folder)
            except Exception as error:
                self.logging.log("warning", "Zapret-Mods catalog metadata read failed", folder=folder, error=str(error))
                continue
            if not isinstance(meta, dict):
                continue
            mod_id = str(meta.get("id", "") or "").strip()
            if not mod_id or mod_id in seen_ids:
                continue
            seen_ids.add(mod_id)
            category = str(meta.get("category", "") or "").strip().lower() or "general"
            catalog.append(
                {
                    "id": mod_id,
                    "name": str(meta.get("name", "") or "") or mod_id,
                    "description": str(meta.get("description", "") or ""),
                    "author": str(meta.get("author", "") or "") or self.UNKNOWN_AUTHOR,
                    "version": str(meta.get("version", "") or ""),
                    "source_url": str(meta.get("source_url", "") or "") or _MODS_REPO_URL,
                    "category": category,
                    "changelog": str(meta.get("changelog", "") or ""),
                }
            )
            catalog_data[mod_id] = {"dir": folder, "emoji": str(meta.get("emoji", "") or "").strip()}
        if not catalog:
            self.logging.log("warning", "Zapret-Mods catalog is empty")
            return False
        self.storage.write_json(self.storage.paths.cache_dir / "mods_index.json", catalog)
        self.storage.write_json(self.storage.paths.cache_dir / _MODS_CATALOG_FILE, catalog_data)
        self._repo_catalog = catalog_data
        self.logging.log("info", "Zapret-Mods catalog discovered", mods=len(catalog), source=file_base)
        return True

    def _repo_catalog_present_and_fresh(self) -> bool:
        cache_path = self.storage.paths.cache_dir / "mods_index.json"
        try:
            if not cache_path.exists():
                return False
            if not (self.storage.read_json(cache_path, default=[]) or []):
                return False
            return (datetime.now() - datetime.fromtimestamp(cache_path.stat().st_mtime)).total_seconds() < _REPO_CATALOG_TTL_SECONDS
        except Exception:
            return False

    def _repo_catalog_entry(self, mod_id: str) -> dict[str, str]:
        if not self._repo_catalog:
            try:
                data = self.storage.read_json(self.storage.paths.cache_dir / _MODS_CATALOG_FILE, default={}) or {}
                self._repo_catalog = data if isinstance(data, dict) else {}
            except Exception:
                self._repo_catalog = {}
        return dict(self._repo_catalog.get(mod_id, {}) or {})

    def _select_repo_file_base(self) -> str | None:
        if self._repo_file_base is not None:
            return self._repo_file_base or None
        for base in (_MODS_RAW_BASE, _MODS_MIRROR_BASE):
            if self.github.probe_url(f"{base}/README.md", timeout=6):
                self._repo_file_base = base
                return base
        self._repo_file_base = ""
        return None

    def _repo_mod_folders(self) -> list[str]:
        folders: list[str] = []
        try:
            entries = self.github.github_json(_MODS_CONTENTS_API, timeout=10, purpose="zapret-mods-listing", retry=False)
            if isinstance(entries, list):
                for entry in entries:
                    if not isinstance(entry, dict):
                        continue
                    if str(entry.get("type", "") or "").lower() not in {"dir", "directory"}:
                        continue
                    name = str(entry.get("name", "") or "").strip()
                    if name and name not in _MODS_SKIP_DIRS:
                        folders.append(name)
        except Exception:
            folders = []
        if folders:
            return sorted(folders)
        for node in self._repo_tree_files():
            if not isinstance(node, dict):
                continue
            if str(node.get("type", "") or "").lower() not in {"dir", "directory"}:
                continue
            name = str(node.get("name", "") or "").strip()
            if name and name not in _MODS_SKIP_DIRS:
                folders.append(name)
        return sorted(folders)

    def _repo_tree_files(self) -> list[object]:
        if self._repo_tree is None:
            try:
                payload = self.github.github_json(_MODS_TREE_API, timeout=12, purpose="zapret-mods-tree", retry=False)
                files = payload.get("files") if isinstance(payload, dict) else None
                self._repo_tree = files if isinstance(files, list) else []
            except Exception:
                self._repo_tree = []
        return list(self._repo_tree)

    def _repo_mod_metadata(self, file_base: str, folder: str) -> dict[str, object]:
        payload = self.github.github_json(f"{file_base}/{folder}/mod.json", timeout=10, purpose="zapret-mods-metadata", retry=False)
        return payload if isinstance(payload, dict) else {}

    def _repo_folder_files(self, folder: str) -> list[str]:
        try:
            entries = self.github.github_json(f"{_MODS_CONTENTS_API}/{folder}", timeout=12, purpose="zapret-mods-files", retry=False)
            if isinstance(entries, list):
                rel: list[str] = []
                for entry in entries:
                    if not isinstance(entry, dict):
                        continue
                    name = str(entry.get("name", "") or "").strip()
                    if not name:
                        continue
                    if str(entry.get("type", "") or "").lower() in {"dir", "directory"}:
                        rel.extend(f"{name}/{sub}" for sub in self._repo_folder_files(f"{folder}/{name}"))
                    else:
                        rel.append(name)
                if rel:
                    return self._filter_repo_mod_files(rel)
        except Exception:
            pass
        prefix = f"{folder}/"
        tree_rel = self._flatten_repo_tree(self._repo_tree_files())
        return self._filter_repo_mod_files([path[len(prefix):] for path in tree_rel if path.startswith(prefix)])

    @staticmethod
    def _flatten_repo_tree(nodes: list[object]) -> list[str]:
        result: list[str] = []
        for node in nodes:
            if not isinstance(node, dict):
                continue
            name = str(node.get("name", "") or "").strip()
            if not name:
                continue
            if str(node.get("type", "") or "").lower() in {"dir", "directory"}:
                result.extend(f"{name}/{sub}" for sub in ModsManager._flatten_repo_tree(node.get("files") or []))
            else:
                result.append(name)
        return result

    @staticmethod
    def _filter_repo_mod_files(rels: list[str]) -> list[str]:
        result: list[str] = []
        for rel in rels:
            rel = str(rel or "").replace("\\", "/")
            if not rel or Path(rel).suffix.lower() not in _MODS_REPO_FILE_SUFFIXES:
                continue
            parts = Path(rel).parts
            if ".github" in parts or ".git" in parts:
                continue
            if rel.startswith(".") or "/." in rel:
                continue
            if rel == "mod.json":
                result.append(rel)
                continue
            name = rel.rsplit("/", 1)[-1].lower()
            if name.startswith(("readme", "license", "changelog")):
                continue
            result.append(rel)
        return sorted(set(result))

    def list_installed(self) -> list[InstalledMod]:
        self._auto_register_mods()
        raw = self.storage.read_json(self._installed_path, default=[]) or []
        return [InstalledMod(**item) for item in raw]

    def _auto_register_mods(self) -> None:
        mods_dir = self.storage.paths.mods_dir
        if not mods_dir.exists():
            return
        installed = self.storage.read_json(self._installed_path, default=[]) or []
        if not isinstance(installed, list):
            installed = []
        registered_ids = {item.get("id") for item in installed if isinstance(item, dict)}
        changed = False
        for mod_dir in sorted(mods_dir.iterdir()):
            if not mod_dir.is_dir():
                continue
            mod_id = mod_dir.name
            if mod_id in registered_ids:
                continue
            meta_path = mod_dir / self.METADATA_FILENAME
            if not meta_path.is_file():
                continue
            try:
                meta = json.loads(meta_path.read_text(encoding="utf-8"))
            except Exception:
                continue
            if not isinstance(meta, dict):
                continue
            general_scripts = sorted(
                script.name for script in mod_dir.glob("*.bat") if script.is_file() and not script.name.lower().startswith("service")
            )
            lists_exist = (mod_dir / "lists").is_dir() and any((mod_dir / "lists").iterdir())
            if not general_scripts and not lists_exist:
                continue
            entry = InstalledMod(
                id=mod_id,
                version=str(meta.get("version", datetime.utcnow().strftime("%Y.%m.%d"))),
                path=str(mod_dir),
                name=str(meta.get("name", mod_id)),
                author=str(meta.get("author", self.UNKNOWN_AUTHOR)),
                description=str(meta.get("description", "")),
                source_url=str(meta.get("source_url", "")),
                enabled=False,
                source_type="zapret_bundle",
                general_scripts=general_scripts,
                emoji=random.choice(self._EMOJI_CHOICES),
            )
            installed.append(asdict(entry))
            changed = True
            registered_ids.add(mod_id)
            self.logging.log("info", "Auto-registered mod from disk", mod_id=mod_id, path=str(mod_dir))
        if changed:
            self.storage.write_json(self._installed_path, installed)

    def move(self, mod_id: str, direction: int) -> list[InstalledMod]:
        installed = self.list_installed()
        index = next((i for i, item in enumerate(installed) if item.id == mod_id), -1)
        if index < 0:
            return installed
        target = max(0, min(len(installed) - 1, index + direction))
        if target == index:
            return installed
        item = installed.pop(index)
        installed.insert(target, item)
        self.storage.write_json(self._installed_path, [asdict(entry) for entry in installed])
        self.merge.rebuild()
        return installed

    def set_emoji(self, mod_id: str, emoji: str) -> InstalledMod:
        installed = self.list_installed()
        entry = next(item for item in installed if item.id == mod_id)
        entry.emoji = emoji.strip() or entry.emoji
        self.storage.write_json(self._installed_path, [asdict(item) for item in installed])
        return entry

    def update_metadata(
        self,
        mod_id: str,
        *,
        name: str,
        description: str,
        author: str,
        version: str,
    ) -> InstalledMod:
        installed = self.list_installed()
        entry = next(item for item in installed if item.id == mod_id)
        entry.name = name.strip() or entry.name or mod_id
        entry.description = description.strip()
        entry.author = author.strip() or entry.author or self.UNKNOWN_AUTHOR
        entry.version = version.strip() or entry.version or datetime.utcnow().strftime("%Y.%m.%d")
        self.storage.write_json(self._installed_path, [asdict(item) for item in installed])
        self._write_mod_metadata_file(entry)
        self.logging.log("info", "Mod metadata updated", mod_id=mod_id)
        return entry

    def create_empty(self, *, name: str, description: str = "", author: str = UNKNOWN_AUTHOR) -> InstalledMod:
        mod_id = self._unique_mod_id(name or "custom-mod")
        target_dir = self.storage.paths.mods_dir / mod_id
        (target_dir / "lists").mkdir(parents=True, exist_ok=True)
        (target_dir / "utils").mkdir(parents=True, exist_ok=True)
        (target_dir / "lists" / "list-general.txt").write_text("", encoding="utf-8")
        installed = self.list_installed()
        entry = InstalledMod(
            id=mod_id,
            version=datetime.utcnow().strftime("%Y.%m.%d"),
            path=str(target_dir),
            name=name.strip() or mod_id,
            author=author.strip() or self.UNKNOWN_AUTHOR,
            description=description.strip(),
            enabled=False,
            source_type="zapret_bundle",
            general_scripts=[],
            emoji=random.choice(self._EMOJI_CHOICES),
        )
        installed.insert(0, entry)
        self.storage.write_json(self._installed_path, [asdict(item) for item in installed])
        self._write_mod_metadata_file(entry)
        self.logging.log("info", "Empty mod created", mod_id=mod_id)
        return entry

    def list_files(self, mod_id: str) -> list[dict[str, object]]:
        root = self._editable_mod_root(mod_id)
        records: list[dict[str, object]] = []
        for path in sorted(root.rglob("*")):
            if not path.is_file() or path.name == self.METADATA_FILENAME:
                continue
            if "__pycache__" in path.parts or ".git" in path.parts:
                continue
            if not self._is_supported_mod_file(path):
                continue
            records.append({"path": path.relative_to(root).as_posix(), "size": path.stat().st_size})
        return records

    def read_file(self, mod_id: str, relative_path: str) -> str:
        return self._safe_mod_file(mod_id, relative_path, must_exist=True).read_text(encoding="utf-8", errors="ignore")

    def write_file(self, mod_id: str, relative_path: str, content: str) -> None:
        target = self._safe_mod_file(mod_id, relative_path, must_exist=False)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
        self._refresh_general_scripts(mod_id)
        self.merge.rebuild()

    def delete_file(self, mod_id: str, relative_path: str) -> None:
        target = self._safe_mod_file(mod_id, relative_path, must_exist=True)
        target.unlink()
        self._refresh_general_scripts(mod_id)
        self.merge.rebuild()

    def install(self, mod_id: str) -> InstalledMod:
        item = next(entry for entry in self.fetch_index() if entry.id == mod_id)
        if self._is_repo_mod_item(item):
            return self._install_repo_mod(item)
        target_dir = self.storage.paths.mods_dir / mod_id
        target_dir.mkdir(parents=True, exist_ok=True)
        payload_path = target_dir / "payload.json"
        if not payload_path.exists():
            self.storage.write_json(
                payload_path,
                {
                    "rules": [f"{mod_id}-rule"],
                    "metadata": {"installed_from": item.source_url},
                },
            )

        installed = self.list_installed()
        existing = next((entry for entry in installed if entry.id == mod_id), None)
        if existing:
            existing.version = item.version
            existing.path = str(target_dir)
            result = existing
        else:
            result = InstalledMod(id=mod_id, version=item.version, path=str(target_dir), enabled=False)
            installed.append(result)

        self.storage.write_json(self._installed_path, [asdict(entry) for entry in installed])
        self.logging.log("info", "Mod installed", mod_id=mod_id, version=item.version)
        return result

    def _is_repo_mod_item(self, item: ModIndexItem) -> bool:
        source = str(item.source_url or "").strip().rstrip("/")
        return bool(source) and (source == _MODS_REPO_URL.rstrip("/") or source.startswith(_MODS_REPO_URL.rstrip("/") + "/"))

    def _install_repo_mod(self, item: ModIndexItem) -> InstalledMod:
        data = self._repo_catalog_entry(item.id)
        folder = str(data.get("dir", "") or "").strip() or item.id
        file_base = self._select_repo_file_base()
        if not file_base:
            raise RuntimeError(f"Zapret-Mods sources are unreachable ({item.id})")
        files = [rel for rel in self._repo_folder_files(folder) if rel != "mod.json"]
        target_dir = self.storage.paths.mods_dir / item.id
        if target_dir.exists():
            shutil.rmtree(target_dir, ignore_errors=True)
        target_dir.mkdir(parents=True, exist_ok=True)
        downloaded = 0
        for rel in files:
            destination = target_dir / rel
            try:
                payload = self.github.github_bytes(f"{file_base}/{folder}/{rel}", timeout=40, purpose="zapret-mod-download")
            except Exception as error:
                self.logging.log("warning", "Zapret-Mods file download failed", mod_id=item.id, path=rel, error=str(error))
                continue
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(payload)
            self._strip_zone_identifier(destination)
            downloaded += 1
        meta_path = target_dir / "mod.json"
        if not meta_path.is_file():
            try:
                mod_meta = self._repo_mod_metadata(file_base, folder)
            except Exception:
                mod_meta = {}
            if isinstance(mod_meta, dict) and mod_meta:
                (target_dir / "mod.json").write_text(json.dumps(mod_meta, ensure_ascii=False, indent=2), encoding="utf-8")
        if downloaded == 0:
            raise RuntimeError("No mod files could be downloaded")
        general_scripts = sorted(
            script.name for script in target_dir.glob("*.bat") if script.is_file() and not script.name.lower().startswith("service")
        )
        lists_present = (target_dir / "lists").is_dir() and any((target_dir / "lists").iterdir())
        if not general_scripts and not lists_present:
            raise RuntimeError("Downloaded mod bundle has no compatible files")
        emoji = str(data.get("emoji", "") or "").strip()
        installed = self.list_installed()
        existing = next((entry for entry in installed if entry.id == item.id), None)
        if existing is not None:
            existing.version = item.version or existing.version
            existing.path = str(target_dir)
            existing.name = item.name or existing.name
            existing.author = item.author or existing.author
            existing.description = item.description or existing.description
            existing.source_url = item.source_url or existing.source_url or _MODS_REPO_URL
            existing.general_scripts = general_scripts
            existing.emoji = emoji or existing.emoji
            result = existing
        else:
            result = InstalledMod(
                id=item.id,
                version=item.version or datetime.utcnow().strftime("%Y.%m.%d"),
                path=str(target_dir),
                name=item.name or item.id,
                author=item.author or self.UNKNOWN_AUTHOR,
                description=item.description or "",
                source_url=item.source_url or _MODS_REPO_URL,
                enabled=False,
                source_type="zapret_bundle",
                general_scripts=general_scripts,
                emoji=emoji,
            )
            installed.append(result)
        self.storage.write_json(self._installed_path, [asdict(entry) for entry in installed])
        self.logging.log("info", "Zapret-Mods bundle installed", mod_id=item.id, folder=folder, files=downloaded)
        return result

    def set_enabled(self, mod_id: str, enabled: bool) -> InstalledMod:
        installed = self.list_installed()
        entry = next(item for item in installed if item.id == mod_id)
        entry.enabled = enabled
        self.storage.write_json(self._installed_path, [asdict(item) for item in installed])
        enabled_ids = {item.id for item in installed if item.enabled}
        self.settings.update(enabled_mod_ids=sorted(enabled_ids))
        self.merge.rebuild()
        if enabled:
            self.apply_declared_settings(mod_id)
        self.logging.log("info", "Mod state changed", mod_id=mod_id, enabled=enabled)
        return entry

    def read_declared_settings(self, mod_id: str) -> dict[str, object]:
        entry = next((item for item in self.list_installed() if item.id == mod_id), None)
        if entry is None:
            return {}
        meta_path = Path(entry.path) / self.METADATA_FILENAME
        if not meta_path.is_file():
            return {}
        try:
            metadata = json.loads(meta_path.read_text(encoding="utf-8-sig"))
        except (OSError, ValueError):
            return {}
        raw = metadata.get("settings") if isinstance(metadata, dict) else None
        if not isinstance(raw, dict):
            return {}
        result: dict[str, object] = {}
        for raw_key, raw_value in raw.items():
            key = str(raw_key).strip()
            normalized = _normalize_mod_setting(key, raw_value)
            if normalized is None:
                reason = "unknown" if key not in MOD_SETTING_KEYS else "rejected"
                self.logging.log("warning", f"Mod setting {reason}", mod_id=mod_id, key=key)
                continue
            result[key] = normalized
        return result

    def apply_declared_settings(self, mod_id: str) -> bool:
        overrides = self.read_declared_settings(mod_id)
        if not overrides:
            return False
        self._write_overrides_into_default_profile(overrides)
        active_id = str(self.settings.get().active_profile_id or "default").strip()
        if active_id == "default":
            self.settings.update(**overrides)
        self.logging.log("info", "Mod settings applied to default profile", mod_id=mod_id, keys=sorted(overrides))
        return True

    def _write_overrides_into_default_profile(self, overrides: dict[str, object]) -> None:
        profiles_path = self.storage.paths.data_dir / "profiles.json"
        profiles = self.storage.read_json(profiles_path, default=[]) or []
        if not isinstance(profiles, list):
            return
        for item in profiles:
            if isinstance(item, dict) and item.get("id") == "default":
                snapshot = item.get("settings_snapshot")
                if not isinstance(snapshot, dict):
                    snapshot = {}
                snapshot.update(overrides)
                item["settings_snapshot"] = snapshot
                self.storage.write_json(profiles_path, profiles)
                return

    def remove(self, mod_id: str) -> None:
        installed = [item for item in self.list_installed() if item.id != mod_id]
        self.storage.write_json(self._installed_path, [asdict(item) for item in installed])
        target_dir = self.storage.paths.mods_dir / mod_id
        if target_dir.exists():
            self.storage.create_backup(target_dir, "pre-remove-mod")
            shutil.rmtree(target_dir)
        self.merge.rebuild()
        self.logging.log("info", "Mod removed", mod_id=mod_id)

    def export_mod(self, mod_id: str, target_dir: str) -> Path:
        entry = next(item for item in self.list_installed() if item.id == mod_id)
        source_dir = Path(entry.path)
        if not source_dir.exists():
            raise FileNotFoundError(f"Modification path not found: {source_dir}")
        destination = Path(target_dir)
        if destination.suffix.lower() == ".zip":
            destination.parent.mkdir(parents=True, exist_ok=True)
            zip_path = destination
        else:
            destination.mkdir(parents=True, exist_ok=True)
            zip_path = destination / f"{entry.id}-{entry.version or __version__}.zip"
        if zip_path.exists():
            zip_path.unlink()
        with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
            for path in source_dir.rglob("*"):
                if path.name == "__pycache__" or ".git" in path.parts:
                    continue
                if path.is_dir():
                    continue
                if path.name == self.METADATA_FILENAME:
                    continue
                if not self._is_supported_mod_file(path):
                    continue
                archive.write(path, path.relative_to(source_dir))
            archive.writestr(self.METADATA_FILENAME, self._metadata_json(entry))
        self.logging.log("info", "Mod exported", mod_id=mod_id, target=str(zip_path))
        return zip_path

    def import_from_path(self, source_path: str) -> InstalledMod:
        return self.import_from_paths([source_path])

    def import_from_paths(self, source_paths: list[str], suggested_name: str | None = None) -> InstalledMod:
        valid_sources = [Path(item) for item in source_paths if item]
        if not valid_sources:
            raise ValueError("Nothing was selected for import.")

        for source in valid_sources:
            if not source.exists():
                raise FileNotFoundError(f"Path not found: {source}")

        with tempfile.TemporaryDirectory(prefix="zapret_zen_mod_") as temp_dir:
            staged_root = Path(temp_dir) / "staged"
            staged_root.mkdir(parents=True, exist_ok=True)
            for source in valid_sources:
                self._stage_source_for_import(source, staged_root)

            fallback_name = suggested_name or next((item.stem if item.is_file() else item.name for item in valid_sources), "mod")
            return self._import_staged_bundle(staged_root, suggested_name=fallback_name)

    def import_from_github(self, repo_url: str) -> InstalledMod:
        owner, repo, api_url = self._normalize_github_repo(repo_url)
        if owner.lower() == "flowseal" and repo.lower() == "zapret-discord-youtube":
            raise ValueError("Оригинальный репозиторий Flowseal уже встроен в приложение и не может быть добавлен как модификация.")

        self.logging.log("info", "GitHub mod import started", repo=repo, owner=owner)
        repo_info = self.github.github_json(api_url, timeout=15, purpose="github-mod-metadata")
        if not isinstance(repo_info, dict):
            raise ValueError("GitHub repository metadata is invalid.")

        zip_url = str(repo_info.get("zipball_url") or "").strip()
        repo_name = str(repo_info.get("name") or repo).strip() or repo
        description = str(repo_info.get("description") or "").strip()
        author = str((repo_info.get("owner") or {}).get("login") or owner).strip() or owner
        if not zip_url:
            raise ValueError("GitHub repository metadata does not contain a zipball URL.")

        with tempfile.TemporaryDirectory(prefix="zapret_zen_github_") as temp_dir:
            zip_path = Path(temp_dir) / f"{repo_name}.zip"
            self.github.github_download(zip_url, zip_path, timeout=30, purpose="github-mod-download")
            return self._import_from_github_zip(zip_path, repo_name, author, description, repo_url)

    def _import_from_github_zip(
        self,
        zip_path: Path,
        repo_name: str,
        author: str,
        description: str,
        repo_url: str,
    ) -> InstalledMod:
        with tempfile.TemporaryDirectory(prefix="zapret_zen_github_unzip_") as temp_dir:
            temp_root = Path(temp_dir) / "unzipped"
            temp_root.mkdir(parents=True, exist_ok=True)
            self._extract_zip_filtered(zip_path, temp_root)
            entry = self._import_staged_bundle(
                temp_root,
                suggested_name=repo_name,
                display_name=repo_name,
                author=author,
                description=description,
                source_url=repo_url,
            )
        return entry

    def _import_staged_bundle(
        self,
        staged_root: Path,
        *,
        suggested_name: str,
        display_name: str | None = None,
        author: str = UNKNOWN_AUTHOR,
        description: str = "",
        source_url: str = "",
    ) -> InstalledMod:
        metadata = self._read_staged_metadata(staged_root)
        if metadata:
            suggested_name = str(metadata.get("name") or suggested_name)
            display_name = str(metadata.get("name") or display_name or suggested_name)
            author = str(metadata.get("author") or author or self.UNKNOWN_AUTHOR)
            description = str(metadata.get("description") or description)
            source_url = str(metadata.get("source_url") or source_url)
        general_sources, list_sources, bin_sources, utils_sources = self._collect_import_candidates(staged_root)
        general_scripts = self._dedupe_general_names(sorted(general_sources))
        if not general_scripts and not list_sources:
            raise ValueError(
                "Не найдено ни одного совместимого general-файла или списка. Добавьте .bat-конфиг или .txt-листы Zapret."
            )

        mod_id = self._unique_mod_id(suggested_name)
        target_dir = self.storage.paths.mods_dir / mod_id
        self._materialize_mod_bundle(
            target_dir=target_dir,
            general_sources={name: general_sources[name] for name in general_scripts if name in general_sources},
            list_sources=list_sources,
            bin_sources=bin_sources,
            utils_sources=utils_sources,
        )

        installed = self.list_installed()
        entry = InstalledMod(
            id=mod_id,
            version=str(metadata.get("version") or datetime.utcnow().strftime("%Y.%m.%d")) if metadata else datetime.utcnow().strftime("%Y.%m.%d"),
            path=str(target_dir),
            name=display_name or suggested_name,
            author=author or self.UNKNOWN_AUTHOR,
            description=description or self._build_bundle_description(general_scripts, list_sources),
            source_url=source_url,
            enabled=True,
            source_type="zapret_bundle",
            general_scripts=general_scripts,
            emoji=random.choice(self._EMOJI_CHOICES),
        )
        installed.insert(0, entry)
        self.storage.write_json(self._installed_path, [asdict(item) for item in installed])
        self._write_mod_metadata_file(entry, metadata)

        enabled_ids = {item.id for item in installed if item.enabled}
        self.settings.update(enabled_mod_ids=sorted(enabled_ids))
        self.merge.rebuild()
        self.apply_declared_settings(entry.id)
        self.logging.log("info", "Zapret bundle imported", mod_id=mod_id, path=str(target_dir), generals=general_scripts, source=source_url or "local")
        return entry

    def _build_bundle_description(self, general_scripts: list[str], list_sources: dict[str, list[Path]]) -> str:
        parts: list[str] = []
        if general_scripts:
            parts.append(f"General: {len(general_scripts)}")
        if list_sources:
            parts.append(f"Lists: {len(list_sources)}")
        return " | ".join(parts)

    def _metadata_json(self, entry: InstalledMod, extra: dict[str, object] | None = None) -> str:
        payload = {
            "schema": "zapret-zen-mod-v1",
            "id": entry.id,
            "name": entry.name or entry.id,
            "description": entry.description,
            "author": entry.author or self.UNKNOWN_AUTHOR,
            "version": entry.version,
            "source_url": entry.source_url,
            "source_type": entry.source_type,
            "emoji": entry.emoji,
        }
        if isinstance(extra, dict):
            for key, value in extra.items():
                if key in payload or key in {"schema", "id"}:
                    continue
                payload[key] = value
        import json

        return json.dumps(payload, ensure_ascii=False, indent=2)

    def _write_mod_metadata_file(self, entry: InstalledMod, extra: dict[str, object] | None = None) -> None:
        root = Path(entry.path)
        if not root.exists():
            return
        (root / self.METADATA_FILENAME).write_text(self._metadata_json(entry, extra), encoding="utf-8")

    def _read_staged_metadata(self, root: Path) -> dict[str, object]:
        for candidate in root.rglob(self.METADATA_FILENAME):
            if not candidate.is_file():
                continue
            try:
                import json

                payload = json.loads(candidate.read_text(encoding="utf-8"))
                return payload if isinstance(payload, dict) else {}
            except Exception:
                return {}
        return {}

    def _editable_mod_root(self, mod_id: str) -> Path:
        entry = next(item for item in self.list_installed() if item.id == mod_id)
        root = Path(entry.path)
        if not root.exists():
            raise FileNotFoundError(f"Modification path not found: {root}")
        return root

    @staticmethod
    def _strip_zone_identifier(path: Path) -> None:
        if sys.platform != "win32":
            return
        try:
            kernel32 = ctypes.windll.kernel32
            target = str(path) + ":Zone.Identifier"
            kernel32.DeleteFileW(target)
        except Exception:
            pass

    def _safe_mod_file(self, mod_id: str, relative_path: str, *, must_exist: bool) -> Path:
        root = self._editable_mod_root(mod_id).resolve()
        rel = str(relative_path or "").strip().replace("\\", "/")
        if not self._is_supported_mod_path(rel):
            raise ValueError("Modification files can only be .txt, .ps1, or .bat.")
        if not rel or rel.startswith("/") or ".." in Path(rel).parts:
            raise ValueError("Invalid modification file path.")
        target = (root / rel).resolve()
        if root not in target.parents and target != root:
            raise ValueError("Modification file path escapes the mod folder.")
        if must_exist and not target.exists():
            raise FileNotFoundError(f"Modification file not found: {rel}")
        return target

    def _refresh_general_scripts(self, mod_id: str) -> None:
        installed = self.list_installed()
        entry = next(item for item in installed if item.id == mod_id)
        root = Path(entry.path)
        entry.general_scripts = sorted(
            script.name for script in root.glob("*.bat") if script.is_file() and not script.name.lower().startswith("service")
        )
        self.storage.write_json(self._installed_path, [asdict(item) for item in installed])

    def _materialize_mod_bundle(
        self,
        *,
        target_dir: Path,
        general_sources: dict[str, Path],
        list_sources: dict[str, list[Path]],
        bin_sources: dict[str, Path],
        utils_sources: dict[str, Path],
    ) -> None:
        if target_dir.exists():
            shutil.rmtree(target_dir, ignore_errors=True)
        target_dir.mkdir(parents=True, exist_ok=True)

        lists_target = target_dir / "lists"
        utils_target = target_dir / "utils"
        lists_target.mkdir(parents=True, exist_ok=True)
        utils_target.mkdir(parents=True, exist_ok=True)

        for name, script in general_sources.items():
            dest = target_dir / name
            shutil.copy2(script, dest)
            self._strip_zone_identifier(dest)

        for name, source in utils_sources.items():
            dest = utils_target / name
            shutil.copy2(source, dest)
            self._strip_zone_identifier(dest)

        for name, sources in list_sources.items():
            merged: list[str] = []
            seen: set[str] = set()
            for source in sources:
                for raw in source.read_text(encoding="utf-8", errors="ignore").splitlines():
                    line = raw.strip()
                    if not line or line in seen:
                        continue
                    seen.add(line)
                    merged.append(line)
            (lists_target / name).write_text("\n".join(merged) + ("\n" if merged else ""), encoding="utf-8")

    def _stage_source_for_import(self, source: Path, staged_root: Path) -> None:
        if source.is_dir():
            target = staged_root / source.name
            if target.exists():
                target = staged_root / f"{source.name}_{datetime.utcnow().strftime('%H%M%S%f')}"
            self._copy_tree_filtered(source, target)
            return

        if source.suffix.lower() == ".zip":
            unpack_dir = staged_root / f"{source.stem}_{datetime.utcnow().strftime('%H%M%S%f')}"
            unpack_dir.mkdir(parents=True, exist_ok=True)
            self._extract_zip_filtered(source, unpack_dir)
            return

        if self._is_supported_mod_file(source):
            shutil.copy2(source, staged_root / source.name)

    def _collect_import_candidates(self, root: Path) -> tuple[dict[str, Path], dict[str, list[Path]], dict[str, Path], dict[str, Path]]:
        general_sources: dict[str, Path] = {}
        list_sources: dict[str, list[Path]] = {}
        bin_sources: dict[str, Path] = {}
        utils_sources: dict[str, Path] = {}

        for file_path in root.rglob("*"):
            if not file_path.is_file():
                continue
            if not self._is_supported_mod_file(file_path):
                continue
            lowered = file_path.name.lower()
            suffix = file_path.suffix.lower()
            parent_lower = file_path.parent.name.lower()

            if suffix == ".bat" and not lowered.startswith("service"):
                if lowered not in general_sources:
                    general_sources[file_path.name] = file_path
                continue

            if suffix == ".txt":
                if lowered.startswith(("readme", "license", "changelog")):
                    continue
                if parent_lower == "lists" or lowered.startswith(("list-", "ipset", "hosts")):
                    list_sources.setdefault(file_path.name, []).append(file_path)
                    continue
                if self._looks_like_runtime_list(file_path):
                    list_sources.setdefault(file_path.name, []).append(file_path)
                    continue

            if suffix == ".ps1" or parent_lower == "utils":
                utils_sources.setdefault(file_path.name, file_path)

        return general_sources, list_sources, bin_sources, utils_sources

    def _is_supported_mod_file(self, path: Path) -> bool:
        if path.name == self.METADATA_FILENAME:
            return True
        return path.suffix.lower() in self.ALLOWED_MOD_SUFFIXES

    def _is_supported_mod_path(self, relative_path: str) -> bool:
        path = Path(str(relative_path or "").replace("\\", "/"))
        return path.name != self.METADATA_FILENAME and path.suffix.lower() in self.ALLOWED_MOD_SUFFIXES

    def _copy_tree_filtered(self, source: Path, target: Path) -> None:
        for file_path in source.rglob("*"):
            if not file_path.is_file() or not self._is_supported_mod_file(file_path):
                continue
            if "__pycache__" in file_path.parts or ".git" in file_path.parts:
                continue
            rel = file_path.relative_to(source)
            destination = target / rel
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(file_path, destination)

    def _extract_zip_filtered(self, source: Path, target: Path) -> None:
        with zipfile.ZipFile(source, "r") as archive:
            for member in archive.infolist():
                if member.is_dir():
                    continue
                rel = Path(member.filename.replace("\\", "/"))
                if rel.is_absolute() or ".." in rel.parts:
                    continue
                if rel.name != self.METADATA_FILENAME and not self._is_supported_mod_path(rel.as_posix()):
                    continue
                destination = target / rel
                destination.parent.mkdir(parents=True, exist_ok=True)
                with archive.open(member, "r") as src, destination.open("wb") as dst:
                    shutil.copyfileobj(src, dst)

    def _looks_like_runtime_list(self, file_path: Path) -> bool:
        try:
            sample = file_path.read_text(encoding="utf-8", errors="ignore")[:4096]
        except Exception:
            return False
        if not sample.strip():
            return False
        return any(marker in sample.lower() for marker in (".com", ".gg", ".ru", ".net", "/", ":"))

    def _dedupe_general_names(self, names: list[str]) -> list[str]:
        result: list[str] = []
        seen: set[str] = set()
        for name in names:
            lowered = name.lower()
            if lowered in seen:
                continue
            seen.add(lowered)
            result.append(name)
        return result

    def _normalize_github_repo(self, repo_url: str) -> tuple[str, str, str]:
        raw = repo_url.strip()
        if not raw:
            raise ValueError("Ссылка на GitHub пустая.")
        if raw.endswith(".git"):
            raw = raw[:-4]
        parsed = urlparse(raw)
        if parsed.netloc.lower() not in {"github.com", "www.github.com"}:
            raise ValueError("Поддерживаются только обычные ссылки на GitHub-репозитории.")
        parts = [part for part in parsed.path.split("/") if part]
        if len(parts) < 2:
            raise ValueError("Не удалось распознать owner/repo в ссылке GitHub.")
        owner, repo = parts[0], parts[1]
        return owner, repo, f"https://api.github.com/repos/{owner}/{repo}"

    def _detect_zapret_bundle_root(self, root: Path) -> Path:
        if self._looks_like_zapret_bundle(root):
            return root
        for child in root.iterdir():
            if child.is_dir() and self._looks_like_zapret_bundle(child):
                return child
        raise ValueError("Selected source does not look like a zapret bundle (service.bat/bin/lists not found).")

    def _looks_like_zapret_bundle(self, path: Path) -> bool:
        return (path / "service.bat").exists() and (path / "bin").is_dir() and (path / "lists").is_dir()

    def _scan_general_scripts(self, bundle_root: Path, skip_base_duplicates: bool = False) -> list[str]:
        scripts: list[str] = []
        base_names = self._base_general_names() if skip_base_duplicates else set()
        for script in bundle_root.glob("*.bat"):
            name = script.name.lower()
            if name.startswith("service"):
                continue
            if name in base_names:
                continue
            scripts.append(script.name)
        return sorted(scripts)

    def _base_general_names(self) -> set[str]:
        base_root = self.storage.paths.runtime_dir / "zapret-discord-youtube"
        names: set[str] = set()
        if not base_root.exists():
            return names
        for script in base_root.glob("*.bat"):
            lowered = script.name.lower()
            if lowered.startswith("service"):
                continue
            names.add(lowered)
        return names

    def _cleanup_orphaned_installed(self) -> None:
        installed = self.list_installed()
        cleaned = [item for item in installed if Path(item.path).exists()]
        if len(cleaned) != len(installed):
            removed_ids = {item.id for item in installed} - {item.id for item in cleaned}
            self.storage.write_json(self._installed_path, [asdict(item) for item in cleaned])
            for mod_id in removed_ids:
                self.logging.log("info", "Removed orphaned installed mod entry", mod_id=mod_id)

    def _cleanup_installed_duplicate_generals(self) -> None:
        installed = self.list_installed()
        changed = False
        for item in installed:
            if item.source_type != "zapret_bundle":
                continue
            bundle = Path(item.path)
            if not bundle.exists():
                continue
            for f in bundle.rglob("*"):
                if f.is_file():
                    self._strip_zone_identifier(f)
            normalized = sorted(
                {
                    script.name
                    for script in bundle.glob("*.bat")
                    if script.is_file() and not script.name.lower().startswith("service")
                }
            )
            if sorted(item.general_scripts) != normalized:
                item.general_scripts = normalized
                changed = True
        if changed:
            self.storage.write_json(self._installed_path, [asdict(item) for item in installed])

    def _unique_mod_id(self, name: str) -> str:
        slug = re.sub(r"[^a-zA-Z0-9_-]+", "-", name).strip("-").lower() or "mod"
        stamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
        return f"{slug}-{stamp}"
