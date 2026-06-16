from __future__ import annotations

import argparse

from zapret_zen.cli_args import build_worker_arg_group, parse_bool_flag
from zapret_zen.workers import run_tg_ws_proxy_worker


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--worker", choices=["tg-ws-proxy"], required=True)
    build_worker_arg_group(parser)
    known, _ = parser.parse_known_args(argv)

    if known.worker == "tg-ws-proxy":
        return run_tg_ws_proxy_worker(
            host=known.tg_host,
            port=known.tg_port,
            secret=known.tg_secret,
            verbose=known.tg_verbose,
            dc_ip=list(known.tg_dc_ip or []),
            cfproxy_enabled=parse_bool_flag(known.tg_cfproxy_enabled),
            cfproxy_priority=parse_bool_flag(known.tg_cfproxy_priority),
            cfproxy_domain=known.tg_cfproxy_domain,
            fake_tls_domain=known.tg_fake_tls_domain,
            buf_kb=known.tg_buf_kb,
            pool_size=known.tg_pool_size,
        )
    raise SystemExit(2)

if __name__ == "__main__":
    raise SystemExit(main())
