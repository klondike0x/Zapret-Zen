"""Minimal Discord Rich Presence client using stdlib."""

from __future__ import annotations

import json
import logging
import os
import struct
import sys
import threading
import time
from typing import IO

logger = logging.getLogger(__name__)

APP_ID = "1539264958054006825"

OP_HANDSHAKE = 0
OP_FRAME = 1
OP_CLOSE = 2
OP_PING = 3
OP_PONG = 4


def _encode(opcode: int, payload: dict) -> bytes:
    data = json.dumps(payload).encode("utf-8")
    return struct.pack("<II", opcode, len(data)) + data


def _decode_header(f) -> tuple[int, int]:
    header = b""
    while len(header) < 8:
        chunk = f.read(8 - len(header))
        if not chunk:
            raise ConnectionError("pipe closed")
        header += chunk
    return struct.unpack("<II", header)


def _read_payload(f, length: int) -> dict:
    data = b""
    while len(data) < length:
        chunk = f.read(length - len(data))
        if not chunk:
            raise ConnectionError("pipe closed")
        data += chunk
    return json.loads(data.decode("utf-8"))


def _connect_win32(pipe_path: str) -> IO[bytes] | None:
    """Connect to a Windows named pipe via CreateFile + open_osfhandle."""
    import ctypes
    from ctypes import wintypes

    INVALID_HANDLE_VALUE = wintypes.HANDLE(-1).value

    kernel32 = ctypes.windll.kernel32
    handle = kernel32.CreateFileW(
        pipe_path,
        0xC0000000,
        0,
        None,
        3,
        0,
        None,
    )
    if handle == INVALID_HANDLE_VALUE:
        return None

    try:
        import msvcrt
        fd = msvcrt.open_osfhandle(handle, 0)
        if fd < 0:
            kernel32.CloseHandle(handle)
            return None
        return os.fdopen(fd, "r+b", buffering=0)
    except Exception:
        kernel32.CloseHandle(handle)
        return None


def _connect_unix(pipe_path: str) -> IO[bytes] | None:
    """Connect using AF_UNIX socket on Linux/macOS."""
    import socket
    sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    sock.settimeout(3)
    try:
        sock.connect(pipe_path)
        return sock.makefile("rwb", buffering=0)
    except Exception:
        sock.close()
        return None


def _find_and_connect():
    """Try to find and connect to Discord IPC pipe, return a file-like object."""
    if sys.platform == "win32":
        for i in range(10):
            pipe_path = f"\\\\.\\pipe\\discord-ipc-{i}"
            f = _connect_win32(pipe_path)
            if f is not None:
                logger.info("Discord RPC: connected to %s", pipe_path)
                return f
    else:
        env = os.environ
        runtime = env.get("XDG_RUNTIME_DIR") or env.get("TMPDIR") or "/tmp"
        for i in range(10):
            pipe_path = os.path.join(runtime, f"discord-ipc-{i}")
            f = _connect_unix(pipe_path)
            if f is not None:
                logger.info("Discord RPC: connected to %s", pipe_path)
                return f
    return None


class DiscordRPCService:
    def __init__(self) -> None:
        self._detail = "Использует для обхода блокировок."
        self._running = False
        self._thread: threading.Thread | None = None
        self._stop_event = threading.Event()

    def configure(self, enabled: bool, detail: str) -> None:
        self._detail = detail
        if enabled and not self._running:
            self.start()
        elif not enabled and self._running:
            self.stop()

    def start(self) -> None:
        if self._running:
            return
        self._stop_event = threading.Event()
        self._running = True
        self._thread = threading.Thread(
            target=self._run, args=(self._stop_event,),
            daemon=True, name="discord-rpc",
        )
        self._thread.start()
        logger.info("Discord RPC: started")

    def stop(self) -> None:
        if not self._running:
            return
        self._running = False
        self._stop_event.set()
        self._thread = None
        logger.info("Discord RPC: stopped")

    @property
    def is_running(self) -> bool:
        return self._running

    def update_presence(self, detail: str | None = None) -> None:
        self._detail = detail or self._detail

    def _run(self, stop: threading.Event) -> None:
        f = None
        while self._running and not stop.is_set():
            try:
                f = _find_and_connect()
                if f is None:
                    stop.wait(timeout=5)
                    continue

                logger.info("Discord RPC: sending handshake")
                f.write(_encode(OP_HANDSHAKE, {"v": 1, "client_id": APP_ID}))
                f.flush()

                _, length = _decode_header(f)
                hello = _read_payload(f, length)
                logger.info("Discord RPC: hello evt=%s", hello.get("evt"))
                if hello.get("evt") != "READY":
                    f.close()
                    f = None
                    stop.wait(timeout=5)
                    continue

                logger.info("Discord RPC: READY, setting presence")
                self._set_presence(f, self._detail)
                self._listen(f, stop)

            except Exception as exc:
                logger.info("Discord RPC: %s", exc)
            finally:
                if f is not None:
                    try:
                        f.close()
                    except Exception:
                        pass
                    f = None
                stop.wait(timeout=5)

        if f is not None:
            try:
                f.close()
            except Exception:
                pass

    def _listen(self, f, stop: threading.Event) -> None:
        last_update = 0.0
        while self._running and not stop.is_set():
            try:
                opcode, length = _decode_header(f)
            except (ConnectionError, OSError, struct.error):
                break
            if opcode == OP_CLOSE:
                break
            if opcode == OP_PING:
                try:
                    _read_payload(f, length)
                except Exception:
                    break
                try:
                    f.write(_encode(OP_PONG, {}))
                    f.flush()
                except Exception:
                    break
                continue
            try:
                _read_payload(f, length)
            except Exception:
                break
            if time.monotonic() - last_update > 15:
                try:
                    self._set_presence(f, self._detail)
                    last_update = time.monotonic()
                except Exception:
                    break

    def _set_presence(self, f, detail: str) -> None:
        payload = {
            "cmd": "SET_ACTIVITY",
            "args": {
                "pid": os.getpid(),
                "activity": {
                    "details": detail,
                    "assets": {"large_image": "large", "large_text": "Zapret Zen"},
                },
            },
            "nonce": str(int(time.monotonic() * 1000)),
        }
        f.write(_encode(OP_FRAME, payload))
        f.flush()
        logger.info("Discord RPC: presence set (detail=%s)", detail)
