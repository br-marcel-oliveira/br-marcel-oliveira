#!/usr/bin/env python3
"""Gera os selos de status/uptime dos produtos do perfil.

As URLs ficam no secret METRICS_CONFIG (JSON), nunca neste arquivo:

{"products": [{"key": "kalibra", "url": "https://..."}]}

Uso: python scripts/live_metrics.py <dir_saida>
Lê/grava <dir_saida>/history.json (checagens de uptime dos últimos 30 dias).
"""
import json
import os
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timedelta, timezone
from xml.sax.saxutils import escape

sys.path.insert(0, os.path.dirname(__file__))
from brand import AMBER, BLACK, BODY, SILVER, TEAL, WHITE, font_css  # noqa: E402

CONFIG = json.loads(os.environ["METRICS_CONFIG"])
NOW = datetime.now(timezone.utc)
SINCE = NOW - timedelta(days=30)


def parse(ts):
    return datetime.strptime(ts, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)


def check(url):
    start = time.monotonic()
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "profile-status-check"})
        with urllib.request.urlopen(req, timeout=20) as r:
            ok = r.status < 400
    except (urllib.error.URLError, TimeoutError):
        ok = False
    return ok, round((time.monotonic() - start) * 1000)


def status_svg(up, uptime, latency):
    w, h = 370, 30
    dot = TEAL if up else AMBER
    state = "ONLINE" if up else "OFFLINE"
    detail = f"uptime {uptime} · checagens periódicas · {latency} ms"
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}">'
        "<style>" + font_css("inter-300", "inter-600")
        + "@keyframes p{0%,100%{opacity:1}50%{opacity:.35}}.d{animation:p 2s ease-in-out infinite}</style>"
        f'<rect width="{w}" height="{h}" rx="15" fill="{BLACK}"/>'
        f'<circle class="d" cx="17" cy="15" r="4.5" fill="{dot}"/>'
        f'<text x="30" y="19" font-family="{BODY}" font-weight="600" font-size="11" letter-spacing=".9" '
        f'fill="{WHITE}">{state}</text>'
        f'<text x="{98 if up else 106}" y="19" font-family="{BODY}" font-weight="300" font-size="11" '
        f'fill="{SILVER}">{escape(detail)}</text>'
        "</svg>"
    )


def main():
    out = sys.argv[1]
    os.makedirs(out, exist_ok=True)
    hist_path = os.path.join(out, "history.json")
    history = {}
    if os.path.exists(hist_path):
        with open(hist_path) as f:
            history = json.load(f)

    status = {}
    for p in CONFIG.get("products", []):
        ok, ms = check(p["url"])
        checks = [c for c in history.get(p["key"], []) if parse(c["t"]) >= SINCE]
        checks.append({"t": NOW.strftime("%Y-%m-%dT%H:%M:%SZ"), "ok": ok, "ms": ms})
        history[p["key"]] = checks
        pct = 100 * sum(c["ok"] for c in checks) / len(checks)
        status[p["key"]] = (ok, f"{pct:.1f}%".replace(".0%", "%") if pct < 100 else "100%", ms)

    with open(hist_path, "w") as f:
        json.dump(history, f)

    for key, (up, uptime, ms) in status.items():
        with open(os.path.join(out, f"status-{key}.svg"), "w") as f:
            f.write(status_svg(up, uptime, ms))


if __name__ == "__main__":
    main()
