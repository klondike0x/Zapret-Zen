from __future__ import annotations

import base64
import concurrent.futures
import os
import random
import socket
import ssl
import string
import time
import urllib.request
from pathlib import Path
from typing import Any

DEFAULT_TG_DC_IPS = ("149.154.167.51", "149.154.167.91")
CF_DOMAINS_FILE_REL = ("tg-ws-proxy", ".github", "cfproxy-domains.txt")
CFPROXY_DOMAINS_URL = (
    "https://raw.githubusercontent.com/Flowseal/tg-ws-proxy/main",
    "/.github/cfproxy-domains.txt",
)
_MAX_WORKERS = 6
_PROBE_TIMEOUT = 3.5
_MIN_FRESH_DOMAINS = 3
_WS_PATH = "/apiws"
_DEFAULT_DC_IDS = (2, 4)


def decode_domain(value: str) -> str:
    name = str(value or "").strip().lower()
    if not name.endswith(".com"):
        return name
    prefix = name[:-4]
    letters = sum(1 for ch in prefix if ch.isalpha())
    decoded = "".join(
        chr((ord(ch) - (97 if ch > "`" else 65) - letters) % 26 + (97 if ch > "`" else 65))
        if ch.isalpha()
        else ch
        for ch in prefix
    )
    return decoded + ".com"


def _split_domain_text(value: str) -> list[str]:
    items: list[str] = []
    for raw in str(value or "").replace("\n", " ").replace(",", " ").replace(";", " ").split():
        item = str(raw).strip().lower()
        if item and item not in items:
            items.append(item)
    return items


def fetch_fresh_bridge_domains() -> list[str]:
    try:
        url = CFPROXY_DOMAINS_URL[0] + CFPROXY_DOMAINS_URL[1] + "?" + "".join(
            random.choices(string.ascii_letters, k=7)
        )
        request = urllib.request.Request(url, headers={"User-Agent": "tg-ws-proxy"})
        with urllib.request.urlopen(request, timeout=10) as response:
            text = response.read().decode("utf-8", errors="replace")
        domains = [
            decode_domain(line)
            for line in text.splitlines()
            if line.strip() and not line.strip().startswith("#")
        ]
        seen: list[str] = []
        for item in domains:
            if item and item not in seen:
                seen.append(item)
        return seen
    except Exception:
        return []


def collect_bridge_domains(runtime_dir: Path, configured: str = "") -> list[str]:
    domains: list[str] = []
    fresh = fetch_fresh_bridge_domains()
    if len(fresh) >= _MIN_FRESH_DOMAINS:
        domains.extend(fresh)
    source = runtime_dir.joinpath(*CF_DOMAINS_FILE_REL)
    if source.exists():
        try:
            for raw in source.read_text(encoding="utf-8", errors="ignore").splitlines():
                name = decode_domain(str(raw).strip())
                if name and name not in domains:
                    domains.append(name)
        except Exception:
            pass
    for item in _split_domain_text(configured):
        if item and item not in domains:
            domains.append(item)
    return domains


def probe_ws_upgrade(host: str, domain: str, timeout: float = _PROBE_TIMEOUT) -> float | None:
    host = str(host or "").strip().lower()
    domain = str(domain or "").strip().lower()
    if not host or not domain:
        return None
    sock: socket.socket | None = None
    started = time.perf_counter()
    try:
        host_ip = socket.gethostbyname(host)
        sock = socket.create_connection((host_ip, 443), timeout=timeout)
        sock.settimeout(timeout)
        context = ssl.create_default_context()
        context.check_hostname = False
        context.verify_mode = ssl.CERT_NONE
        tls = context.wrap_socket(sock, server_hostname=domain)
        sock = None
        ws_key = base64.b64encode(os.urandom(16)).decode()
        request = (
            f"GET {_WS_PATH} HTTP/1.1\r\n"
            f"Host: {domain}\r\n"
            f"Upgrade: websocket\r\n"
            f"Connection: Upgrade\r\n"
            f"Sec-WebSocket-Key: {ws_key}\r\n"
            f"Sec-WebSocket-Version: 13\r\n"
            f"Sec-WebSocket-Protocol: binary\r\n"
            f"\r\n"
        )
        tls.sendall(request.encode("ascii"))
        buffer = b""
        while True:
            chunk = tls.recv(4096)
            if not chunk:
                break
            buffer += chunk
            if b"\r\n\r\n" in buffer or b"\n\n" in buffer:
                break
        tls.close()
        line = buffer.splitlines()[0].decode("utf-8", errors="replace").strip() if buffer else ""
        parts = line.split(" ", 2)
        if len(parts) >= 2 and parts[0].startswith("HTTP/"):
            try:
                if int(parts[1]) == 101:
                    return round((time.perf_counter() - started) * 1000, 1)
            except ValueError:
                pass
        return None
    except Exception:
        return None
    finally:
        if sock is not None:
            try:
                sock.close()
            except Exception:
                pass


def probe_bridge(domain: str, dc_ids: list[int], timeout: float = _PROBE_TIMEOUT) -> float | None:
    domain = str(domain or "").strip().lower()
    if not domain:
        return None
    for dc_id in dc_ids:
        latency = probe_ws_upgrade(f"kws{dc_id}.{domain}", f"kws{dc_id}.{domain}", timeout=timeout)
        if latency is not None:
            return latency
    return None


def probe_tcp_connect(ip: str, port: int = 443, timeout: float = _PROBE_TIMEOUT) -> float | None:
    started = time.perf_counter()
    sock: socket.socket | None = None
    try:
        sock = socket.create_connection((str(ip).strip(), int(port)), timeout=timeout)
        return round((time.perf_counter() - started) * 1000, 1)
    except Exception:
        return None
    finally:
        if sock is not None:
            try:
                sock.close()
            except Exception:
                pass


def probe_bridges(domains: list[str], dc_ids: list[int]) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=_MAX_WORKERS) as executor:
        futures = {executor.submit(probe_bridge, domain, dc_ids): domain for domain in domains}
        for future in concurrent.futures.as_completed(futures):
            domain = futures[future]
            results.append({"domain": domain, "latency": future.result()})
    reachable = [item for item in results if item.get("latency") is not None]
    reachable.sort(key=lambda item: item["latency"])
    return reachable


def probe_direct(dc_ips: list[str]) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=_MAX_WORKERS) as executor:
        futures = {executor.submit(probe_tcp_connect, ip): ip for ip in dc_ips}
        for future in concurrent.futures.as_completed(futures):
            ip = futures[future]
            results.append({"ip": ip, "latency": future.result()})
    reachable = [item for item in results if item.get("latency") is not None]
    reachable.sort(key=lambda item: item["latency"])
    return reachable


def parse_dc_ips(dc_ip_setting: str) -> list[str]:
    ips: list[str] = []
    for raw in str(dc_ip_setting or "").splitlines():
        part = raw.split(":", 1)[-1].strip()
        if part and part not in ips:
            ips.append(part)
    return ips or list(DEFAULT_TG_DC_IPS)


def parse_dc_ids(dc_ip_setting: str) -> list[int]:
    ids: list[int] = []
    for raw in str(dc_ip_setting or "").splitlines():
        try:
            dc_id = int(raw.split(":", 1)[0].strip())
        except ValueError:
            continue
        if dc_id and dc_id not in ids:
            ids.append(dc_id)
    return ids or list(_DEFAULT_DC_IDS)


def decide_tuning(bridge_results: list[dict[str, Any]], direct_results: list[dict[str, Any]]) -> dict[str, Any]:
    best_bridge = bridge_results[0] if bridge_results else None
    direct_best = direct_results[0]["latency"] if direct_results else None
    changes: dict[str, Any] = {}
    if best_bridge is not None and direct_best is not None:
        if best_bridge["latency"] <= direct_best:
            changes["tg_proxy_cfproxy_enabled"] = True
            changes["tg_proxy_cfproxy_domain"] = " ".join(item["domain"] for item in bridge_results[:3])
            mode = "bridge"
            summary = (
                f"Мост {best_bridge['domain']} ({best_bridge['latency']} мс) "
                f"быстрее прямого соединения ({direct_best} мс)."
            )
        else:
            changes["tg_proxy_cfproxy_enabled"] = True
            changes["tg_proxy_cfproxy_domain"] = ""
            mode = "direct"
            summary = (
                f"Прямое соединение ({direct_best} мс) быстрее мостов, "
                f"оставлен автоматический подбор доменов мостов."
            )
    elif best_bridge is not None:
        changes["tg_proxy_cfproxy_enabled"] = True
        changes["tg_proxy_cfproxy_domain"] = " ".join(item["domain"] for item in bridge_results[:3])
        mode = "bridge"
        summary = (
            f"Прямое соединение недоступно, выбран мост {best_bridge['domain']} ({best_bridge['latency']} мс)."
        )
    elif direct_best is not None:
        changes["tg_proxy_cfproxy_enabled"] = True
        changes["tg_proxy_cfproxy_domain"] = ""
        mode = "direct"
        summary = (
            "Мосты не обнаружены, используется прямое соединение "
            "и автоматический подбор доменов мостов."
        )
    else:
        changes["tg_proxy_cfproxy_enabled"] = True
        changes["tg_proxy_cfproxy_domain"] = ""
        mode = "auto"
        summary = (
            "Рабочие мосты и прямое соединение не обнаружены. "
            "Ручной список доменов сброшен, оставлен автоматический подбор tg-ws-proxy."
        )
    return {"changes": changes, "summary": summary, "mode": mode}