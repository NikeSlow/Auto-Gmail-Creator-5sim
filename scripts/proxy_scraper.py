#!/usr/bin/env python3
# region tool-tag
# Auto-Gmail-Creator-5sim | component:proxy-scraper | v1
# Scrapes public lists, validates, exports data/working_proxies.json + data/Proxy_DB.csv (HTTP/HTTPS rows)
# endregion
"""
Advanced Proxy Scraper & Validator — integrated with Auto-Gmail-Creator-5sim.

Aggregates proxies from community GitHub/jsDelivr lists, validates with
threaded requests (HTTP / HTTPS / SOCKS4 / SOCKS5 via PySocks), exports JSON
and a single-column CSV compatible with data/Proxy_DB.csv (host:port).
"""

from __future__ import annotations

import argparse
import csv
import json
import random
import time
import concurrent.futures
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional

import requests
import urllib3
from fake_useragent import UserAgent

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

LogFn = Optional[Callable[[str], None]]

REQUEST_TIMEOUT = 10
MAX_WORKERS = 50
MAX_PROXIES_PER_TYPE = 400
TEST_URLS = [
    "http://httpbin.org/ip",
    "https://httpbin.org/ip",
]
OUTPUT_JSON_NAME = "working_proxies.json"
PROXY_CSV_NAME = "Proxy_DB.csv"


class ProxyScraper:
    SOURCES = {
        "TheSpeedX_HTTP": "https://raw.githubusercontent.com/TheSpeedX/SOCKS-List/master/http.txt",
        "TheSpeedX_SOCKS4": "https://raw.githubusercontent.com/TheSpeedX/SOCKS-List/master/socks4.txt",
        "TheSpeedX_SOCKS5": "https://raw.githubusercontent.com/TheSpeedX/SOCKS-List/master/socks5.txt",
        "proxifly_HTTP": "https://cdn.jsdelivr.net/gh/proxifly/free-proxy-list@main/proxies/protocols/http/data.txt",
        "proxifly_HTTPS": "https://cdn.jsdelivr.net/gh/proxifly/free-proxy-list@main/proxies/protocols/https/data.txt",
        "proxifly_SOCKS4": "https://cdn.jsdelivr.net/gh/proxifly/free-proxy-list@main/proxies/protocols/socks4/data.txt",
        "proxifly_SOCKS5": "https://cdn.jsdelivr.net/gh/proxifly/free-proxy-list@main/proxies/protocols/socks5/data.txt",
        "Thordata_ALL": "https://raw.githubusercontent.com/Thordata/awesome-free-proxy-list/main/proxies/all.txt",
    }

    @staticmethod
    def _ua() -> str:
        try:
            return UserAgent().random
        except Exception:
            return (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            )

    @classmethod
    def fetch_proxies_from_url(cls, url: str, source_name: str, log: LogFn) -> List[str]:
        proxy_list: List[str] = []
        line_fn = log or print
        try:
            headers = {"User-Agent": cls._ua()}
            response = requests.get(url, headers=headers, timeout=20)
            if response.status_code == 200:
                for line in response.text.splitlines():
                    line = line.strip()
                    if line and not line.startswith("#"):
                        if ":" in line and len(line.split(":")) == 2:
                            proxy_list.append(line)
                line_fn(f"  OK {source_name}: {len(proxy_list)} proxies")
            else:
                line_fn(f"  WARN {source_name}: HTTP {response.status_code}")
        except Exception as e:
            line_fn(f"  ERR {source_name}: {str(e)[:80]}")
        return proxy_list

    @classmethod
    def scrape_all_sources(
        cls,
        log: LogFn = None,
        max_per_type: int = MAX_PROXIES_PER_TYPE,
    ) -> Dict[str, List[str]]:
        all_proxies: Dict[str, List[str]] = {}
        line_fn = log or print
        line_fn("\nScraping proxy sources...")
        for source_name, url in cls.SOURCES.items():
            proxy_type = source_name.rsplit("_", 1)[-1]
            proxies = cls.fetch_proxies_from_url(url, source_name, log)
            random.shuffle(proxies)
            proxies = proxies[:max_per_type]
            if proxy_type not in all_proxies:
                all_proxies[proxy_type] = []
            all_proxies[proxy_type].extend(proxies)
        for ptype in all_proxies:
            all_proxies[ptype] = list(dict.fromkeys(all_proxies[ptype]))
        return all_proxies


def _proxy_dict_for_requests(host_port: str, proxy_type: str) -> Dict[str, str]:
    pt = proxy_type.upper()
    if pt in ("HTTP", "HTTPS", "ALL"):
        u = f"http://{host_port}"
        return {"http": u, "https": u}
    if pt == "SOCKS5":
        u = f"socks5h://{host_port}"
        return {"http": u, "https": u}
    if pt == "SOCKS4":
        u = f"socks4://{host_port}"
        return {"http": u, "https": u}
    u = f"http://{host_port}"
    return {"http": u, "https": u}


class ProxyValidator:
    @staticmethod
    def test_single_proxy(
        proxy: str,
        proxy_type: str,
        user_agent: str,
    ) -> Optional[Dict[str, Any]]:
        proxy_dict = _proxy_dict_for_requests(proxy, proxy_type)
        headers = {"User-Agent": user_agent}
        response_times: List[float] = []

        for test_url in TEST_URLS:
            try:
                start = time.perf_counter()
                resp = requests.get(
                    test_url,
                    proxies=proxy_dict,
                    headers=headers,
                    timeout=REQUEST_TIMEOUT,
                    verify=False,
                )
                elapsed = time.perf_counter() - start
                if resp.status_code == 200:
                    response_times.append(elapsed)
                else:
                    return None
            except Exception:
                return None

        if not response_times:
            return None
        avg_rt = sum(response_times) / len(response_times)
        return {
            "proxy": proxy,
            "type": proxy_type,
            "avg_response_time": round(avg_rt, 3),
            "tested_at": datetime.now(timezone.utc).isoformat(),
        }

    @classmethod
    def validate_proxies(
        cls,
        proxy_dict: Dict[str, List[str]],
        max_workers: int = MAX_WORKERS,
        log: LogFn = None,
        should_stop: Optional[Callable[[], bool]] = None,
    ) -> List[Dict[str, Any]]:
        line_fn = log or print
        tasks: List[tuple[str, str]] = []
        for proxy_type, plist in proxy_dict.items():
            for proxy in plist:
                tasks.append((proxy, proxy_type))

        line_fn(f"\nValidating {len(tasks)} proxies ({max_workers} workers)...")
        working: List[Dict[str, Any]] = []
        try:
            ua = UserAgent().random
        except Exception:
            ua = ProxyScraper._ua()

        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as ex:
            futs = {
                ex.submit(cls.test_single_proxy, p, pt, ua): (p, pt)
                for p, pt in tasks
            }
            done = 0
            for fut in concurrent.futures.as_completed(futs):
                if should_stop and should_stop():
                    ex.shutdown(wait=False, cancel_futures=True)
                    line_fn("Validation stopped by user.")
                    break
                done += 1
                if done % 200 == 0:
                    line_fn(f"  Progress: {done}/{len(tasks)}")
                try:
                    res = fut.result()
                except Exception:
                    res = None
                if res:
                    working.append(res)

        line_fn(f"Done: {len(working)} working proxies.")
        return working


def export_http_csv_for_app(
    working: List[Dict[str, Any]],
    csv_path: str,
    log: LogFn = None,
) -> int:
    """Write host:port rows for app.py set_driver (HTTP / HTTPS / ALL only)."""
    line_fn = log or print
    rows: List[List[str]] = []
    seen: set[str] = set()
    for w in working:
        t = str(w.get("type", "")).upper()
        if t not in ("HTTP", "HTTPS", "ALL"):
            continue
        host_port = w["proxy"]
        if host_port not in seen:
            seen.add(host_port)
            rows.append([host_port])
    rows.sort(key=lambda r: r[0])
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerows(rows)
    line_fn(f"Wrote {len(rows)} HTTP-capable rows to {csv_path}")
    return len(rows)


class ProxyManager:
    @staticmethod
    def run(
        data_dir: str,
        log: LogFn = None,
        max_workers: int = MAX_WORKERS,
        max_per_type: int = MAX_PROXIES_PER_TYPE,
        should_stop: Optional[Callable[[], bool]] = None,
    ) -> List[Dict[str, Any]]:
        import os

        line_fn = log or print
        os.makedirs(data_dir, exist_ok=True)
        json_path = os.path.join(data_dir, OUTPUT_JSON_NAME)
        csv_path = os.path.join(data_dir, PROXY_CSV_NAME)

        line_fn("=" * 60)
        line_fn("  PROXY SCRAPER & VALIDATOR (Auto-Gmail-Creator-5sim)")
        line_fn(f"  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        line_fn("=" * 60)

        raw = ProxyScraper.scrape_all_sources(log=log, max_per_type=max_per_type)
        if should_stop and should_stop():
            return []

        working = ProxyValidator.validate_proxies(
            raw, max_workers=max_workers, log=log, should_stop=should_stop
        )
        working.sort(key=lambda x: (x["avg_response_time"], x["proxy"]))

        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(working, f, indent=2, ensure_ascii=False)
        line_fn(f"Saved JSON: {json_path}")

        export_http_csv_for_app(working, csv_path, log=log)
        return working


def main() -> None:
    p = argparse.ArgumentParser(description="Scrape and validate proxies for Auto-Gmail-Creator-5sim")
    p.add_argument(
        "--data-dir",
        default="./data",
        help="Directory for working_proxies.json and Proxy_DB.csv",
    )
    p.add_argument("--workers", type=int, default=MAX_WORKERS)
    p.add_argument("--max-per-type", type=int, default=MAX_PROXIES_PER_TYPE)
    args = p.parse_args()
    ProxyManager.run(
        data_dir=args.data_dir,
        log=print,
        max_workers=args.workers,
        max_per_type=args.max_per_type,
    )


if __name__ == "__main__":
    main()
