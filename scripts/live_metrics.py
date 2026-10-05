#!/usr/bin/env python3
"""Gera os SVGs "ao vivo" do perfil a partir de repos privados.

Publica somente números agregados. Nomes de repos e URLs ficam no secret
METRICS_CONFIG (JSON), nunca neste arquivo:

{
  "deploy_workflows": [{"repo": "owner/repo", "workflow": "deploy.yml"}],
  "deploy_environments": [{"repo": "owner/repo", "environment": "Production"}],
  "commit_repos": ["owner/repo"],
  "products": [{"key": "kalibra", "url": "https://..."}]
}

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
from brand import AMBER, BLACK, BODY, DISPLAY, GRAY, SILVER, TEAL, WHITE, font_css  # noqa: E402

API = "https://api.github.com"
TOKEN = os.environ["METRICS_TOKEN"]
CONFIG = json.loads(os.environ["METRICS_CONFIG"])
NOW = datetime.now(timezone.utc)
SINCE = NOW - timedelta(days=30)
SINCE_ISO = SINCE.strftime("%Y-%m-%dT%H:%M:%SZ")
BRT = timezone(timedelta(hours=-3))


def gh(path):
    req = urllib.request.Request(
        API + path,
        headers={
            "Authorization": f"Bearer {TOKEN}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        },
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def parse(ts):
    return datetime.strptime(ts, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)


def deploys():
    total, last = 0, None
    for d in CONFIG.get("deploy_workflows", []):
        data = gh(
            f"/repos/{d['repo']}/actions/workflows/{d['workflow']}/runs"
            f"?status=success&created=>={SINCE_ISO}&per_page=1"
        )
        total += data["total_count"]
        if data["workflow_runs"]:
            t = parse(data["workflow_runs"][0]["updated_at"])
            last = max(last, t) if last else t
    for d in CONFIG.get("deploy_environments", []):
        page = 1
        while True:
            items = gh(
                f"/repos/{d['repo']}/deployments"
                f"?environment={d['environment']}&per_page=100&page={page}"
            )
            recent = [parse(i["created_at"]) for i in items if parse(i["created_at"]) >= SINCE]
            total += len(recent)
            if recent:
                last = max([last, *recent]) if last else max(recent)
            if len(items) < 100 or len(recent) < len(items):
                break
            page += 1
    return total, last


def commits():
    total = 0
    for repo in CONFIG.get("commit_repos", []):
        page = 1
        while True:
            items = gh(f"/repos/{repo}/commits?since={SINCE_ISO}&per_page=100&page={page}")
            total += len(items)
            if len(items) < 100:
                break
            page += 1
    return total


def check(url):
    start = time.monotonic()
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "profile-status-check"})
        with urllib.request.urlopen(req, timeout=20) as r:
            ok = r.status < 400
    except (urllib.error.URLError, TimeoutError):
        ok = False
    return ok, round((time.monotonic() - start) * 1000)


def ago(t):
    if t is None:
        return "—"
    h = int((NOW - t).total_seconds() // 3600)
    if h < 1:
        return "agora"
    if h < 48:
        return f"há {h}h"
    return f"há {h // 24}d"


def live_svg(cells, stamp):
    w, h = 880, 150
    col = (w - 48) / len(cells)
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}">',
        "<style>" + font_css("sg-400", "inter-300", "inter-600") + "</style>",
        f'<rect width="{w}" height="{h}" rx="16" fill="{BLACK}"/>',
    ]
    for i, (value, label) in enumerate(cells):
        x = 40 + i * col
        color = AMBER if i == 0 else WHITE
        parts.append(
            f'<text x="{x}" y="78" font-family="{DISPLAY}" font-weight="400" font-size="46" '
            f'letter-spacing="-1.5" fill="{color}">{escape(value)}</text>'
        )
        parts.append(
            f'<text x="{x + 2}" y="104" font-family="{BODY}" font-weight="600" font-size="11" '
            f'letter-spacing=".9" fill="{GRAY}">{escape(label.upper())}</text>'
        )
    parts.append(
        f'<text x="{w - 40}" y="{h - 18}" text-anchor="end" font-family="{BODY}" font-weight="300" '
        f'font-size="11" fill="{GRAY}">atualizado {escape(stamp)}</text>'
    )
    parts.append("</svg>")
    return "\n".join(parts)


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

    live = 0
    status = {}
    for p in CONFIG.get("products", []):
        ok, ms = check(p["url"])
        live += ok
        checks = [c for c in history.get(p["key"], []) if parse(c["t"]) >= SINCE]
        checks.append({"t": NOW.strftime("%Y-%m-%dT%H:%M:%SZ"), "ok": ok, "ms": ms})
        history[p["key"]] = checks
        pct = 100 * sum(c["ok"] for c in checks) / len(checks)
        status[p["key"]] = (ok, f"{pct:.1f}%".replace(".0%", "%") if pct < 100 else "100%", ms)

    with open(hist_path, "w") as f:
        json.dump(history, f)

    n_deploys, last = deploys()
    cells = [
        (str(n_deploys), "deploys em 30 dias"),
        (str(commits()), "commits em 30 dias"),
        (str(live), "produtos no ar"),
        (ago(last), "último deploy"),
    ]
    stamp = NOW.astimezone(BRT).strftime("%d/%m %H:%M BRT")
    with open(os.path.join(out, "live.svg"), "w") as f:
        f.write(live_svg(cells, stamp))
    for key, (up, uptime, ms) in status.items():
        with open(os.path.join(out, f"status-{key}.svg"), "w") as f:
            f.write(status_svg(up, uptime, ms))


if __name__ == "__main__":
    main()
