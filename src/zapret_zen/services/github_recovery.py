from __future__ import annotations

import time
from typing import Any, Callable

from zapret_zen.services.github_network import GitHubNetworkClient, is_recoverable_github_error
from zapret_zen.services.logging_service import LoggingManager
from zapret_zen.services.settings import SettingsManager


class GitHubRecovery:
    """Handles GitHub connectivity recovery by trying different Zapret configurations."""

    def __init__(
        self,
        logging: LoggingManager,
        settings: SettingsManager,
        start_component: Callable[[str], Any],
        stop_component: Callable[[str], Any],
        is_image_running: Callable[[str], bool],
        list_zapret_generals: Callable[[], list[dict[str, str]]],
    ) -> None:
        self.logging = logging
        self.settings = settings
        self._start_component = start_component
        self._stop_component = stop_component
        self._is_image_running = is_image_running
        self._list_zapret_generals = list_zapret_generals

    def with_github_connectivity_recovery(self, operation: Callable[[], Any], purpose: str) -> Any:
        snapshot = self._capture_snapshot()
        errors: list[str] = []
        try:
            result = self._try_operation(operation, errors, f"{purpose}: current")
            if result[0]:
                return result[1]

            if bool(snapshot["was_running"]):
                self._stop_component("zapret")
                time.sleep(0.8)
                result = self._try_operation(operation, errors, f"{purpose}: stopped")
                if result[0]:
                    return result[1]

                self._restore_snapshot(snapshot, restart=True)
                time.sleep(1.2)
                result = self._try_operation(operation, errors, f"{purpose}: original-restarted")
                if result[0]:
                    return result[1]

            for candidate in self._recovery_candidates(snapshot):
                self._stop_component("zapret")
                self._apply_recovery_settings(
                    selected_zapret_general=str(candidate["general_id"]),
                    zapret_ipset_mode=str(candidate["ipset_mode"]),
                    zapret_game_filter_mode=str(candidate["game_mode"]),
                    zapret_udp_exclude_ports=str(snapshot["zapret_udp_exclude_ports"]),
                )
                state = self._start_component("zapret")
                if getattr(state, "status", None) != "running":
                    errors.append(f"{purpose}: failed to start temporary Zapret profile {candidate}")
                    continue
                time.sleep(1.0)
                result = self._try_operation(operation, errors, f"{purpose}: {candidate['label']}")
                if result[0]:
                    return result[1]
        finally:
            self._restore_snapshot(snapshot, restart=bool(snapshot["was_running"]))
        raise RuntimeError("; ".join(errors) or "GitHub request failed after Zapret recovery")

    def _try_operation(self, operation: Callable[[], Any], errors: list[str], label: str) -> tuple[bool, Any]:
        try:
            return True, operation()
        except Exception as error:
            errors.append(f"{label}: {error}")
            self.logging.log("warning", "GitHub recovery attempt failed", attempt=label, error=str(error))
            if not is_recoverable_github_error(error):
                raise
            time.sleep(0.8)
            return False, None

    def _capture_snapshot(self) -> dict[str, object]:
        settings = self.settings.get()
        return {
            "selected_zapret_general": settings.selected_zapret_general,
            "zapret_ipset_mode": settings.zapret_ipset_mode,
            "zapret_game_filter_mode": settings.zapret_game_filter_mode,
            "zapret_udp_exclude_ports": settings.zapret_udp_exclude_ports,
            "was_running": self._is_image_running("winws.exe"),
        }

    def _restore_snapshot(self, snapshot: dict[str, object], *, restart: bool) -> None:
        self.settings.update(
            selected_zapret_general=str(snapshot.get("selected_zapret_general", "") or ""),
            zapret_ipset_mode=str(snapshot.get("zapret_ipset_mode", "loaded") or "loaded"),
            zapret_game_filter_mode=str(snapshot.get("zapret_game_filter_mode", "disabled") or "disabled"),
            zapret_udp_exclude_ports=str(snapshot.get("zapret_udp_exclude_ports", "51820") or "51820"),
        )
        if restart:
            try:
                self._stop_component("zapret")
                self._start_component("zapret")
            except Exception as error:
                self.logging.log("warning", "Failed to restore Zapret after GitHub recovery", error=str(error))
        else:
            try:
                self._stop_component("zapret")
            except Exception:
                pass

    def _apply_recovery_settings(self, **changes: str) -> None:
        current = self.settings.get()
        for key, value in changes.items():
            setattr(current, key, value)

    def _recovery_candidates(self, snapshot: dict[str, object]) -> list[dict[str, str]]:
        current_general = str(snapshot.get("selected_zapret_general", "") or "").strip()
        base_general = ""
        for option in self._list_zapret_generals():
            if str(option.get("name", "")).lower() == "general.bat" and str(option.get("bundle_id", "")) == "base":
                base_general = str(option.get("id", "") or "")
                break
        favorite_general = next((item for item in self.settings.get().favorite_zapret_generals if str(item).strip()), "")
        general_fallback = favorite_general or base_general
        raw: list[tuple[str, str, str, str]] = [
            ("current loaded/disabled", current_general, "loaded", "disabled"),
            ("current any/disabled", current_general, "any", "disabled"),
            ("current loaded/tcp+udp", current_general, "loaded", "tcpudp"),
        ]
        if general_fallback and general_fallback != current_general:
            raw.append(("fallback loaded/disabled", general_fallback, "loaded", "disabled"))
        candidates: list[dict[str, str]] = []
        seen: set[tuple[str, str, str]] = set()
        for label, general_id, ipset_mode, game_mode in raw:
            if not general_id:
                continue
            key = (general_id, ipset_mode, game_mode)
            if key in seen:
                continue
            seen.add(key)
            candidates.append(
                {
                    "label": label,
                    "general_id": general_id,
                    "ipset_mode": ipset_mode,
                    "game_mode": game_mode,
                }
            )
        return candidates
