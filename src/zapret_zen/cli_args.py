from __future__ import annotations

import argparse


def build_worker_arg_group(parser: argparse.ArgumentParser) -> None:
    """Add tg-ws-proxy worker arguments to an existing parser."""
    parser.add_argument("--tg-host", default="127.0.0.1")
    parser.add_argument("--tg-port", type=int, default=1443)
    parser.add_argument("--tg-secret", default="")
    parser.add_argument("--tg-verbose", action="store_true")
    parser.add_argument("--tg-dc-ip", action="append", default=[])
    parser.add_argument("--tg-cfproxy-enabled", default="true")
    parser.add_argument("--tg-cfproxy-priority", default="true")
    parser.add_argument("--tg-cfproxy-domain", default="")
    parser.add_argument("--tg-fake-tls-domain", default="")
    parser.add_argument("--tg-buf-kb", type=int, default=256)
    parser.add_argument("--tg-pool-size", type=int, default=4)
    parser.add_argument("--parent-pid", type=int, default=0)
    parser.add_argument("--hub-token", default="")


def parse_bool_flag(value: str) -> bool:
    return str(value).lower() not in {"0", "false", "no", "off"}
