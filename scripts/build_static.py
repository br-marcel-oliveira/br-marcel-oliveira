#!/usr/bin/env python3
"""Gera os SVGs estáticos do perfil (banner, fluxo de entrega, logo do condomínio).

Rodar localmente quando o texto mudar; a saída vai commitada em assets/.
Requer fonttools + brotli (medição de texto): pip install fonttools brotli
Uso: python scripts/build_static.py [<simbolo-condominio.svg> <logo-kalibra.png>]
"""
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


def constellation(x0, y0, w, h, n=110, seed=7):
    """Porta para SVG da constelação da landing moit.com.br (moit_theme/js/brain_constellation).

    Mesmos blobs do cérebro, raio de conexão (16% do menor lado), opacidade da linha
    por distância e deriva de ±14px por ponto. No SVG a opacidade de cada linha é
    fixada pela distância inicial (o canvas recalcula a cada quadro).
    """
    rng = random.Random(seed)
    blobs = [(.34, .44, .20), (.5, .36, .22), (.66, .44, .20), (.42, .6, .18), (.58, .6, .18), (.5, .52, .24)]

    def inside(nx, ny):
        return any((nx - bx) ** 2 + ((ny - by) * 1.15) ** 2 <= r * r for bx, by, r in blobs)

    pts = []
    tries = 0
    while len(pts) < n and tries < n * 60:
        tries += 1
        nx, ny = rng.random(), rng.random()
        if inside(nx, ny):
            pts.append((x0 + nx * w, y0 + ny * h, (rng.random() - .5) * .12, (rng.random() - .5) * .12))

    def drift(o, v):
        # Onda triangular o -> o±14 -> o -> o∓14 -> o, na velocidade do canvas (60 fps).
        sign = 1 if v >= 0 else -1
        period = max(8.0, min(40.0, 56 / max(abs(v), .01) / 60))
        vals = ";".join(f"{o + d:.0f}" for d in (0, 14 * sign, 0, -14 * sign, 0))
        return f'dur="{period:.0f}s" repeatCount="indefinite" values="{vals}"'

    max_d2 = (min(w, h) * .16) ** 2
    out = []
    for i in range(len(pts)):
        for j in range(i + 1, len(pts)):
            xi, yi, vxi, vyi = pts[i]
            xj, yj, vxj, vyj = pts[j]
            d2 = (xi - xj) ** 2 + (yi - yj) ** 2
            if d2 > max_d2:
                continue
            alpha = (1 - d2 / max_d2) * .5
            if alpha < .06:  # quase invisível; corta peso do arquivo
                continue
            out.append(
                f'<line x1="{xi:.0f}" y1="{yi:.0f}" x2="{xj:.0f}" y2="{yj:.0f}" stroke="{VIOLET}" '
                f'stroke-opacity="{alpha:.2f}">'
                f'<animate attributeName="x1" {drift(xi, vxi)}/><animate attributeName="y1" {drift(yi, vyi)}/>'
                f'<animate attributeName="x2" {drift(xj, vxj)}/><animate attributeName="y2" {drift(yj, vyj)}/>'
                "</line>"
            )
    for x, y, vx, vy in pts:
        out.append(
            f'<circle cx="{x:.0f}" cy="{y:.0f}" r="1.6" fill="{VIOLET}" fill-opacity=".85">'
            f'<animate attributeName="cx" {drift(x, vx)}/><animate attributeName="cy" {drift(y, vy)}/></circle>'
        )
    return "\n".join(out)


def banner():
    W, H = 880, 362
    phrases = [
        "Head de TI · Founder @ MOIT · AI-native builder",
        "FastAPI · Next.js · Postgres · Azure · Terraform",
        "do problema de negócio ao deploy em produção",
    ]
    n, cyc = len(phrases), 4 * len(phrases)
    tx, ty = 48, 302
    s = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" role="img" '
        'aria-label="Marcel Oliveira — 26 anos liderando TI, usando tecnologia para gerar valor para o negócio.">',
        "<style>" + font_css("sg-400", "inter-300", "inter-600") + "</style>",
        f'<rect width="{W}" height="{H}" rx="16" fill="{BLACK}"/>',
        f'<clipPath id="bn"><rect width="{W}" height="{H}" rx="16"/></clipPath>',
        '<g clip-path="url(#bn)">' + constellation(480, -50, 400, 470, n=130) + "</g>",
        f'<rect x="{tx}" y="44" width="92" height="24" rx="12" fill="{VIOLET}"/>',
        f'<text x="{tx + 46}" y="60.5" text-anchor="middle" font-family="{BODY}" font-weight="600" font-size="11" '
        f'letter-spacing=".9" fill="{WHITE}">SHIPPING</text>',
        f'<text x="{tx + 108}" y="60.5" font-family="{BODY}" font-weight="600" font-size="11" letter-spacing=".9" '
        f'fill="{GRAY}">FLORIANÓPOLIS · BRASIL</text>',
        f'<text x="{tx - 3}" y="146" font-family="{DISPLAY}" font-weight="400" font-size="70" letter-spacing="-3" '
        f'fill="{WHITE}">Marcel Oliveira</text>',
        f'<text x="{tx}" y="194" font-family="{DISPLAY}" font-weight="400" font-size="27" letter-spacing="-.6" '
        f'fill="{SILVER}">26 anos liderando TI,</text>',
        f'<text x="{tx}" y="228" font-family="{DISPLAY}" font-weight="400" font-size="27" letter-spacing="-.6" '
        f'fill="{SILVER}">usando tecnologia para <tspan fill="{AMBER}">gerar</tspan></text>',
        f'<text x="{tx}" y="262" font-family="{DISPLAY}" font-weight="400" font-size="27" letter-spacing="-.6" '
        f'fill="{AMBER}">valor para o negócio<tspan fill="{SILVER}">.</tspan></text>',
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
