"""Design system MOIT aplicado aos SVGs do perfil.

Paleta e tipografia da landing moit.com.br. As fontes (Space Grotesk e Inter,
licença OFL) vão embutidas em base64 porque SVG servido como <img> não carrega
fonte externa.
"""
import base64
import os

BLACK = "#000000"
WHITE = "#ffffff"
GRAY = "#9a9a9a"  # secundário
SILVER = "#bdbdbd"  # terciário
VIOLET = "#8052ff"  # pill / ação
AMBER = "#ffb829"
TEAL = "#15846e"

DISPLAY = "'Space Grotesk',sans-serif"
BODY = "'Inter',sans-serif"

FONTS_DIR = os.path.join(os.path.dirname(__file__), "..", "assets", "fonts")
_FACES = {
    "sg-400": ("Space Grotesk", 400),
    "sg-600": ("Space Grotesk", 600),
    "inter-300": ("Inter", 300),
    "inter-600": ("Inter", 600),
}


def font_css(*names):
    rules = []
    for name in names:
        family, weight = _FACES[name]
        with open(os.path.join(FONTS_DIR, f"{name}.woff2"), "rb") as f:
            data = base64.b64encode(f.read()).decode()
        rules.append(
            f"@font-face{{font-family:'{family}';font-weight:{weight};"
            f"src:url(data:font/woff2;base64,{data}) format('woff2')}}"
        )
    return "".join(rules)
