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


THEMES = {
    "dark": {"bg": "#0d1117", "border": "#30363d", "fg": "#e6edf3", "muted": "#8b949e",
             "accent": "#3ddc97", "down": "#f85149"},
    "light": {"bg": "#ffffff", "border": "#d0d7de", "fg": "#1f2328", "muted": "#59636e",
              "accent": "#1a7f37", "down": "#cf222e"},
}
SANS = "-apple-system,BlinkMacSystemFont,'Segoe UI','Noto Sans',Helvetica,sans-serif"
MONO = "ui-monospace,SFMono-Regular,Menlo,Consolas,monospace"


def live_svg(t, cells, stamp):
    w, h = 800, 132
    col = w / len(cells)
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}">',
        f'<rect x="0.5" y="0.5" width="{w - 1}" height="{h - 1}" rx="12" fill="{t["bg"]}" stroke="{t["border"]}"/>',
    ]
    for i, (value, label) in enumerate(cells):
        x = i * col + 28
        if i:
            parts.append(f'<line x1="{i * col}" y1="28" x2="{i * col}" y2="92" stroke="{t["border"]}"/>')
        color = t["accent"] if i == 0 else t["fg"]
        parts.append(
            f'<text x="{x}" y="66" font-family="{SANS}" font-size="34" font-weight="700" '
            f'fill="{color}">{escape(value)}</text>'
        )
        parts.append(
            f'<text x="{x}" y="90" font-family="{MONO}" font-size="12" fill="{t["muted"]}">{escape(label)}</text>'
        )
    parts.append(
        f'<text x="{w - 20}" y="{h - 14}" text-anchor="end" font-family="{MONO}" font-size="10" '
        f'fill="{t["muted"]}">atualizado {escape(stamp)}</text>'
    )
    parts.append("</svg>")
    return "\n".join(parts)


def status_svg(t, up, uptime, latency):
    w, h = 340, 28
    dot = t["accent"] if up else t["down"]
    state = "API ONLINE" if up else "API OFFLINE"
    detail = f"uptime 30d {uptime} · {latency} ms"
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}">'
        f'<style>@keyframes p{{0%,100%{{opacity:1}}50%{{opacity:.35}}}}.d{{animation:p 2s ease-in-out infinite}}</style>'
        f'<rect x="0.5" y="0.5" width="{w - 1}" height="{h - 1}" rx="14" fill="{t["bg"]}" stroke="{t["border"]}"/>'
        f'<circle class="d" cx="16" cy="14" r="4" fill="{dot}"/>'
        f'<text x="28" y="18" font-family="{MONO}" font-size="11" font-weight="700" fill="{dot}">{state}</text>'
        f'<text x="118" y="18" font-family="{MONO}" font-size="11" fill="{t["muted"]}">{escape(detail)}</text>'
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
    for name, theme in THEMES.items():
        with open(os.path.join(out, f"live-{name}.svg"), "w") as f:
            f.write(live_svg(theme, cells, stamp))
        for key, (up, uptime, ms) in status.items():
            with open(os.path.join(out, f"status-{key}-{name}.svg"), "w") as f:
                f.write(status_svg(theme, up, uptime, ms))


if __name__ == "__main__":
    main()
