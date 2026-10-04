#!/usr/bin/env python3
"""Gera os SVGs estáticos do perfil (banner, fluxo de entrega, logo do condomínio).

Rodar localmente quando o texto mudar; a saída vai commitada em assets/.
Requer fonttools + brotli (medição de texto): pip install fonttools brotli
Uso: python scripts/build_static.py [<simbolo-condominio.svg> <logo-kalibra.png>]
"""
import math
import os
import random
import re
import sys
from xml.sax.saxutils import escape

from fontTools.ttLib import TTFont

sys.path.insert(0, os.path.dirname(__file__))
from brand import AMBER, BLACK, BODY, DISPLAY, FONTS_DIR, GRAY, SILVER, VIOLET, WHITE, font_css  # noqa: E402

ASSETS = os.path.join(os.path.dirname(__file__), "..", "assets")
_metrics = {}


def text_width(font, text, size, tracking=0.0):
    if font not in _metrics:
        f = TTFont(os.path.join(FONTS_DIR, f"{font}.woff2"))
        _metrics[font] = (f.getBestCmap(), f["hmtx"].metrics, f["head"].unitsPerEm)
    cmap, hmtx, upm = _metrics[font]
    units = sum(hmtx[cmap[ord(c)]][0] for c in text if ord(c) in cmap)
    return units * size / upm + tracking * len(text)


def constellation(x0, y0, w, h, seed=7):
    """Constelação de partículas em forma de cérebro (assinatura da landing MOIT)."""
    rng = random.Random(seed)
    cx, cy = x0 + w / 2, y0 + h / 2

    def inside(x, y):
        nx, ny = (x - cx) / (w / 2), (y - cy) / (h / 2)
        lobe = ((nx + 0.05) / 0.95) ** 2 + ((ny + 0.12) / 0.78) ** 2 <= 1
        stem = ((nx - 0.18) / 0.32) ** 2 + ((ny - 0.62) / 0.3) ** 2 <= 1
        return lobe or stem

    pts = []
    tries = 0
    while len(pts) < 78 and tries < 20000:
        tries += 1
        x, y = x0 + rng.random() * w, y0 + rng.random() * h
        if inside(x, y) and all((x - a) ** 2 + (y - b) ** 2 > 17 ** 2 for a, b in pts):
            pts.append((x, y))

    edges = set()
    for i, (x, y) in enumerate(pts):
        near = sorted(range(len(pts)), key=lambda j: (pts[j][0] - x) ** 2 + (pts[j][1] - y) ** 2)[1:4]
        for j in near:
            if math.dist(pts[i], pts[j]) < 58:
                edges.add(tuple(sorted((i, j))))

    out = [f'<g stroke="{WHITE}" stroke-opacity=".16" stroke-width=".8">']
    out += [f'<line x1="{pts[a][0]:.1f}" y1="{pts[a][1]:.1f}" x2="{pts[b][0]:.1f}" y2="{pts[b][1]:.1f}"/>' for a, b in edges]
    out.append("</g>")
    for i, (x, y) in enumerate(pts):
        color = VIOLET if i % 9 == 0 else AMBER if i % 17 == 0 else WHITE
        r = 2.6 if color != WHITE else 1.2 + rng.random() * 1.3
        cls = f' class="tw t{i % 4}"' if i % 3 == 0 else ""
        out.append(f'<circle{cls} cx="{x:.1f}" cy="{y:.1f}" r="{r:.1f}" fill="{color}"/>')
    return "\n".join(out)


def banner():
    W, H = 880, 330
    phrases = [
        "Head de TI · Founder @ MOIT · AI-native builder",
        "FastAPI · Next.js · Postgres · Azure · Terraform",
        "do problema de negócio ao deploy em produção",
    ]
    n, cyc = len(phrases), 4 * len(phrases)
    tx, ty = 48, 268
    s = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" role="img" '
        'aria-label="Marcel Oliveira — 26 anos liderando TI. Agora eu coloco produto no ar.">',
        "<style>" + font_css("sg-400", "inter-300", "inter-600")
        + "@keyframes tw{0%,100%{opacity:1}50%{opacity:.2}}"
        ".tw{animation:tw 3s ease-in-out infinite}.t1{animation-delay:.7s}.t2{animation-delay:1.5s}.t3{animation-delay:2.2s}"
        "</style>",
        f'<rect width="{W}" height="{H}" rx="16" fill="{BLACK}"/>',
        constellation(560, 30, 290, 270),
        f'<rect x="{tx}" y="44" width="92" height="24" rx="12" fill="{VIOLET}"/>',
        f'<text x="{tx + 46}" y="60.5" text-anchor="middle" font-family="{BODY}" font-weight="600" font-size="11" '
        f'letter-spacing=".9" fill="{WHITE}">SHIPPING</text>',
        f'<text x="{tx + 108}" y="60.5" font-family="{BODY}" font-weight="600" font-size="11" letter-spacing=".9" '
        f'fill="{GRAY}">FLORIANÓPOLIS · BRASIL</text>',
        f'<text x="{tx - 3}" y="146" font-family="{DISPLAY}" font-weight="400" font-size="70" letter-spacing="-3" '
        f'fill="{WHITE}">Marcel Oliveira</text>',
        f'<text x="{tx}" y="194" font-family="{DISPLAY}" font-weight="400" font-size="27" letter-spacing="-.6" '
        f'fill="{SILVER}">26 anos liderando TI.</text>',
        f'<text x="{tx}" y="228" font-family="{DISPLAY}" font-weight="400" font-size="27" letter-spacing="-.6" '
        f'fill="{SILVER}">Agora eu <tspan fill="{AMBER}">coloco produto no ar</tspan>.</text>',
    ]
    kt, xs = [], []
    for i, p in enumerate(phrases):
        w = text_width("inter-300", p, 15) + 4
        b, e = i / n, (i + 1) / n
        times = f"0;{b:.4f};{b + .5 / cyc:.4f};{b + 2 / cyc:.4f};{e - .3 / cyc:.4f};{e:.4f};1"
        s.append(
            f'<clipPath id="c{i}"><rect x="{tx}" y="{ty - 16}" height="24" width="0"><animate attributeName="width" '
            f'dur="{cyc}s" repeatCount="indefinite" keyTimes="{times}" values="0;0;0;{w:.0f};{w:.0f};0;0"/></rect></clipPath>'
        )
        s.append(
            f'<text clip-path="url(#c{i})" x="{tx}" y="{ty}" font-family="{BODY}" font-weight="300" font-size="15" '
            f'fill="{SILVER}">{escape(p)}</text>'
        )
        kt += [b, b + .5 / cyc, b + 2 / cyc, e - .3 / cyc]
        xs += [tx, tx, tx + w, tx + w]
    kt.append(1)
    xs.append(tx)
    s.append(
        f'<rect x="{tx}" y="{ty - 14}" width="2" height="18" fill="{VIOLET}">'
        f'<animate attributeName="x" dur="{cyc}s" repeatCount="indefinite" '
        f'keyTimes="{";".join(f"{k:.4f}" for k in kt)}" values="{";".join(f"{x:.0f}" for x in xs)}"/>'
        '<animate attributeName="opacity" values="1;0;1" dur="1s" repeatCount="indefinite"/></rect>'
    )
    s.append("</svg>")
    return "\n".join(s)


def flow():
    W, H = 880, 250
    steps = [
        ("Problema", "de negócio", "onde dói, em número"),
        ("Spec", "e design", "decisão escrita antes do código"),
        ("Plano em", "incrementos", "entregas pequenas e reversíveis"),
        ("Build com", "agentes de IA", "eu dirijo, a IA acelera"),
        ("Testes", "golden + CI", "casos reais como gabarito"),
        ("Produção", "IaC + OIDC", "deploy sem senha, sem clique"),
    ]
    pad, line_y = 40, 56
    col = (W - 2 * pad) / len(steps)
    dur = 7.2
    s = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" role="img" '
        'aria-label="Como eu entrego: problema de negócio, spec e design, plano em incrementos, build com agentes de IA, testes golden e CI, produção com IaC e OIDC.">',
        "<style>" + font_css("sg-400", "sg-600", "inter-300") + "</style>",
        f'<rect width="{W}" height="{H}" rx="16" fill="{BLACK}"/>',
        f'<line x1="{pad}" y1="{line_y}" x2="{W - pad - col + 12}" y2="{line_y}" stroke="{WHITE}" stroke-opacity=".18"/>',
    ]
    last = W - pad - col + 12
    widest = max(text_width("sg-400", t, 21, -.4) for st in steps for t in st[:2])
    title_size = min(21, round(21 * (col - 16) / widest, 1))
    for i, (l1, l2, sub) in enumerate(steps):
        x = pad + i * col
        frac = (x - pad) / (last - pad)
        on = min(frac, 0.999)
        s.append(
            f'<circle cx="{x + 6}" cy="{line_y}" r="5" fill="{BLACK}" stroke="{WHITE}" stroke-opacity=".5">'
            f'<animate attributeName="fill" dur="{dur}s" repeatCount="indefinite" '
            f'keyTimes="0;{on:.3f};{min(on + .08, 1):.3f};1" values="{BLACK};{BLACK};{VIOLET};{VIOLET}"/></circle>'
        )
        s.append(
            f'<text x="{x}" y="{line_y + 42}" font-family="{DISPLAY}" font-weight="600" font-size="13" '
            f'letter-spacing=".5" fill="{AMBER}">{i + 1:02d}</text>'
        )
        for k, ln in enumerate((l1, l2)):
            s.append(
                f'<text x="{x}" y="{line_y + 74 + k * 26}" font-family="{DISPLAY}" font-weight="400" '
                f'font-size="{title_size}" letter-spacing="-.4" fill="{WHITE}">{escape(ln)}</text>'
            )
        words, lines, cur = sub.split(), [], ""
        for wd in words:
            trial = (cur + " " + wd).strip()
            if text_width("inter-300", trial, 13) > col - 18 and cur:
                lines.append(cur)
                cur = wd
            else:
                cur = trial
        lines.append(cur)
        for k, ln in enumerate(lines):
            s.append(
                f'<text x="{x}" y="{line_y + 132 + k * 18}" font-family="{BODY}" font-weight="300" font-size="13" '
                f'fill="{GRAY}">{escape(ln)}</text>'
            )
    s.append(
        f'<circle r="4" cy="{line_y}" fill="{VIOLET}"><animate attributeName="cx" dur="{dur}s" repeatCount="indefinite" '
        f'values="{pad + 6};{last + 6}" keyTimes="0;1"/>'
        f'<animate attributeName="opacity" dur="{dur}s" repeatCount="indefinite" values="0;1;1;0" keyTimes="0;.04;.94;1"/></circle>'
    )
    s.append("</svg>")
    return "\n".join(s)


def logo_tile_png(png_path):
    """Logo do Kalibra (PNG) recortado no mesmo tile preto arredondado."""
    import base64

    data = base64.b64encode(open(png_path, "rb").read()).decode()
    size = 144
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{size}" height="{size}" viewBox="0 0 {size} {size}">'
        f'<clipPath id="r"><rect width="{size}" height="{size}" rx="32"/></clipPath>'
        f'<rect width="{size}" height="{size}" rx="32" fill="{BLACK}"/>'
        f'<image clip-path="url(#r)" width="{size}" height="{size}" href="data:image/png;base64,{data}"/>'
        "</svg>"
    )


def logo_tile(symbol_svg):
    """Símbolo do condomínio sobre tile preto (o símbolo claro some em fundo branco)."""
    src = open(symbol_svg).read()
    inner = re.search(r"<svg[^>]*>(.*)</svg>", src, re.S).group(1)
    vb = re.search(r'viewBox="([^"]+)"', src).group(1)
    size, pad = 144, 22
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{size}" height="{size}" viewBox="0 0 {size} {size}">'
        f'<rect width="{size}" height="{size}" rx="32" fill="{BLACK}"/>'
        f'<svg x="{pad}" y="{pad}" width="{size - 2 * pad}" height="{size - 2 * pad}" viewBox="{vb}">{inner}</svg>'
        "</svg>"
    )


if __name__ == "__main__":
    os.makedirs(ASSETS, exist_ok=True)
    with open(os.path.join(ASSETS, "banner.svg"), "w") as f:
        f.write(banner())
    with open(os.path.join(ASSETS, "como-eu-entrego.svg"), "w") as f:
        f.write(flow())
    if len(sys.argv) > 2:
        with open(os.path.join(ASSETS, "logo-condominio.svg"), "w") as f:
            f.write(logo_tile(sys.argv[1]))
        with open(os.path.join(ASSETS, "logo-kalibra.svg"), "w") as f:
            f.write(logo_tile_png(sys.argv[2]))
