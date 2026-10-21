"""Generate the Fluxop README banner.

Produces a white-background banner with the app logo (neon-cyan bolt on a
dark, corner-cut square) on the left and the wordmark "FLUXOP" beside
it. Reuses the exact colours of the app icon so the README matches the app.

Run:  python make_banner.py
Output: assets/readme-banner.png
"""
from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "assets" / "readme-banner.png"

# --- colours taken from the app icon / UI ------------------------------------
CYAN = (0, 212, 255)          # --primary, the bolt and glow
DARK_TOP = (6, 19, 31)        # #06131f
DARK_BOT = (3, 10, 18)        # #030a12
DARK_BORDER = (13, 58, 85)    # #0d3a55
WHITE = (255, 255, 255)
INK = (8, 20, 30)             # wordmark colour (near-black for contrast on white)

SCALE = 6                     # supersample for crisp edges


def _font(size: int, bold: bool = True) -> ImageFont.FreeTypeFont:
    """Best-effort monospace/tech font; falls back to Pillow's default."""
    candidates = [
        "consolab.ttf" if bold else "consola.ttf",
        "CascadiaCode.ttf",
        "seguisb.ttf",
        "arialbd.ttf" if bold else "arial.ttf",
    ]
    for name in candidates:
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    return ImageFont.load_default()


def _dark_square(size: int) -> Image.Image:
    """The app's logo tile: dark gradient square with cut corners + cyan border."""
    s = size * SCALE
    tile = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    # vertical gradient
    grad = Image.new("RGBA", (1, s))
    for y in range(s):
        t = y / max(1, s - 1)
        grad.putpixel((0, y), (
            int(DARK_TOP[0] * (1 - t) + DARK_BOT[0] * t),
            int(DARK_TOP[1] * (1 - t) + DARK_BOT[1] * t),
            int(DARK_TOP[2] * (1 - t) + DARK_BOT[2] * t),
            255,
        ))
    grad = grad.resize((s, s))

    # corner-cut hexagon (25% / 75% chamfers), matching the app's clip-path
    cut = int(s * 0.25)
    mask = Image.new("L", (s, s), 0)
    ImageDraw.Draw(mask).polygon(
        [
            (cut, 0), (s - cut, 0), (s, cut),
            (s, s - cut), (s - cut, s), (cut, s),
            (0, s - cut), (0, cut),
        ],
        fill=255,
    )
    tile.paste(grad, (0, 0), mask)

    # cyan border following the same outline
    draw = ImageDraw.Draw(tile)
    bw = max(2, s // 90)
    draw.line(
        [
            (cut, 0), (s - cut, 0), (s, cut),
            (s, s - cut), (s - cut, s), (cut, s),
            (0, s - cut), (0, cut), (cut, 0),
        ],
        fill=(*DARK_BORDER, 255), width=bw,
    )

    # neon bolt (path scaled from the app sprite: M13 2 L4 14 h6 l-2 8 9-12 h-6 z)
    bolt_pts = [(13, 2), (4, 14), (10, 14), (8, 22), (17, 10), (11, 10)]
    minx = min(p[0] for p in bolt_pts)
    maxx = max(p[0] for p in bolt_pts)
    miny = min(p[1] for p in bolt_pts)
    maxy = max(p[1] for p in bolt_pts)
    span = max(maxx - minx, maxy - miny)
    pad = s * 0.26
    inner = s - 2 * pad
    k = inner / span

    def tx(p: tuple[int, int]) -> tuple[float, float]:
        # centre the bolt inside the tile
        ox = pad + (inner - (maxx - minx) * k) / 2
        oy = pad + (inner - (maxy - miny) * k) / 2
        return (ox + (p[0] - minx) * k, oy + (p[1] - miny) * k)

    bolt = [tx(p) for p in bolt_pts]

    # glow: a few blurred copies under the solid bolt
    glow = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    ImageDraw.Draw(glow).polygon(bolt, fill=(*CYAN, 190))
    from PIL import ImageFilter
    glow = glow.filter(ImageFilter.GaussianBlur(s * 0.045))
    tile = Image.alpha_composite(tile, glow)
    ImageDraw.Draw(tile).polygon(bolt, fill=(*CYAN, 255))

    return tile.resize((size, size), Image.LANCZOS)


def main() -> None:
    tile_size = 200
    text = "FLUXOP"

    # measure with a large font, then downscale everything at the end via SCALE
    f_size = 96 * SCALE
    font = _font(f_size)
    # letter spacing (tracking) like the app's header
    tracking = int(f_size * 0.16)

    tmp = ImageDraw.Draw(Image.new("RGBA", (10, 10)))
    widths = [tmp.textlength(ch, font=font) for ch in text]
    text_w = int(sum(widths) + tracking * (len(text) - 1))
    bbox = font.getbbox("H")
    cap = bbox[3] - bbox[1]

    gap = int(26 * SCALE)
    pad_x = int(48 * SCALE)
    pad_y = int(40 * SCALE)
    tile_px = tile_size * SCALE

    content_h = max(tile_px, cap)
    W = pad_x * 2 + tile_px + gap + text_w
    H = pad_y * 2 + content_h

    img = Image.new("RGB", (W, H), WHITE)

    tile = _dark_square(tile_size)
    ty = pad_y + (content_h - tile_px) // 2
    img.paste(tile, (pad_x, ty), tile)

    # wordmark, drawn letter by letter to apply tracking
    draw = ImageDraw.Draw(img)
    x = pad_x + tile_px + gap
    baseline_ty = pad_y + (content_h - cap) // 2 - bbox[1]
    for i, ch in enumerate(text):
        draw.text((x, baseline_ty), ch, font=font, fill=INK)
        x += widths[i] + tracking

    # light cyan accent bar under the wordmark for a techy touch
    accent_h = max(2, int(3 * SCALE))
    accent_y = pad_y + (content_h - cap) // 2 + cap + int(10 * SCALE)
    draw.rectangle(
        [pad_x + tile_px + gap, accent_y,
         pad_x + tile_px + gap + text_w, accent_y + accent_h],
        fill=CYAN,
    )

    final = img.resize((W // SCALE, H // SCALE), Image.LANCZOS)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    final.save(OUT)
    print(f"Wrote {OUT} ({final.size[0]}x{final.size[1]})")


if __name__ == "__main__":
    main()
