from PIL import Image, ImageDraw, ImageFont
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]
OUT_PATH = BASE_DIR / "assets" / "line-rich-menu.png"

W, H = 2500, 1686
COLS, ROWS = 3, 2
CELL_W, CELL_H = W // COLS, H // ROWS

GREEN = (22, 185, 88)
DARK = (30, 44, 37)
MUTED = (95, 120, 105)
BORDER = (205, 220, 212)
BG = (250, 253, 251)
WHITE = (255, 255, 255)

ITEMS = [
    ("案件を投稿", "POST", "paper"),
    ("空車を登録", "TRUCK", "truck"),
    ("案件一覧", "LIST", "list"),
    ("管理画面", "ADMIN", "gear"),
    ("使い方", "GUIDE", "help"),
    ("企業検索", "COMPANY", "company"),
]


def find_font(size: int) -> ImageFont.FreeTypeFont:
    candidates = [
        "/System/Library/Fonts/ヒラギノ角ゴシック W6.ttc",
        "/System/Library/Fonts/ヒラギノ角ゴシック W5.ttc",
        "/System/Library/Fonts/ヒラギノ角ゴシック W3.ttc",
        "/System/Library/Fonts/AppleSDGothicNeo.ttc",
        "/System/Library/Fonts/Supplemental/Arial Unicode.ttf",
        "/Library/Fonts/Arial Unicode.ttf",
    ]

    for path in candidates:
        if Path(path).exists():
            return ImageFont.truetype(path, size)

    return ImageFont.load_default()


FONT_TITLE = find_font(92)
FONT_SUB = find_font(42)
FONT_LABEL = find_font(76)


def text_center(draw: ImageDraw.ImageDraw, box, text, font, fill):
    x1, y1, x2, y2 = box
    bbox = draw.textbbox((0, 0), text, font=font)
    tw = bbox[2] - bbox[0]
    th = bbox[3] - bbox[1]
    draw.text(
        (x1 + (x2 - x1 - tw) / 2, y1 + (y2 - y1 - th) / 2),
        text,
        font=font,
        fill=fill,
    )


def rounded_rectangle(draw, box, radius, fill=None, outline=None, width=1):
    if hasattr(draw, "rounded_rectangle"):
        draw.rounded_rectangle(box, radius=radius, fill=fill, outline=outline, width=width)
        return

    draw.rectangle(box, fill=fill, outline=outline)
    if outline and width > 1:
        x1, y1, x2, y2 = box
        for inset in range(1, width):
            draw.rectangle((x1 + inset, y1 + inset, x2 - inset, y2 - inset), outline=outline)


def rectangle(draw, box, fill=None, outline=None, width=1):
    try:
        draw.rectangle(box, fill=fill, outline=outline, width=width)
    except TypeError:
        draw.rectangle(box, fill=fill, outline=outline)
        if outline and width > 1:
            x1, y1, x2, y2 = box
            for inset in range(1, width):
                draw.rectangle((x1 + inset, y1 + inset, x2 - inset, y2 - inset), outline=outline)


def ellipse(draw, box, outline=None, width=1):
    try:
        draw.ellipse(box, outline=outline, width=width)
    except TypeError:
        draw.ellipse(box, outline=outline)
        if outline and width > 1:
            x1, y1, x2, y2 = box
            for inset in range(1, width):
                draw.ellipse((x1 + inset, y1 + inset, x2 - inset, y2 - inset), outline=outline)


def polygon(draw, points, outline=None, width=1):
    try:
        draw.polygon(points, outline=outline, width=width)
    except TypeError:
        draw.polygon(points, outline=outline)


def draw_icon(draw, kind, cx, cy):
    lw = 18
    c = DARK

    if kind == "paper":
        polygon(draw, [(cx - 65, cy + 55), (cx + 95, cy - 85), (cx + 35, cy + 95)], outline=c, width=lw)
        draw.line([(cx - 65, cy + 55), (cx + 20, cy + 25)], fill=c, width=lw)
    elif kind == "truck":
        rounded_rectangle(draw, (cx - 130, cy - 55, cx + 55, cy + 45), radius=12, outline=c, width=lw)
        rectangle(draw, (cx + 55, cy - 20, cx + 130, cy + 45), outline=c, width=lw)
        ellipse(draw, (cx - 85, cy + 35, cx - 35, cy + 85), outline=c, width=lw)
        ellipse(draw, (cx + 65, cy + 35, cx + 115, cy + 85), outline=c, width=lw)
    elif kind == "list":
        for i in range(3):
            y = cy - 65 + i * 65
            rounded_rectangle(draw, (cx - 120, y - 15, cx - 80, y + 25), radius=8, outline=c, width=lw)
            draw.line((cx - 45, y + 5, cx + 125, y + 5), fill=c, width=lw)
    elif kind == "gear":
        ellipse(draw, (cx - 90, cy - 90, cx + 90, cy + 90), outline=c, width=lw)
        ellipse(draw, (cx - 32, cy - 32, cx + 32, cy + 32), outline=c, width=lw)
        draw.line((cx, cy - 135, cx, cy - 95), fill=c, width=lw)
        draw.line((cx, cy + 95, cx, cy + 135), fill=c, width=lw)
        draw.line((cx - 135, cy, cx - 95, cy), fill=c, width=lw)
        draw.line((cx + 95, cy, cx + 135, cy), fill=c, width=lw)
    elif kind == "help":
        ellipse(draw, (cx - 105, cy - 105, cx + 105, cy + 105), outline=c, width=lw)
        text_center(draw, (cx - 90, cy - 100, cx + 90, cy + 80), "?", FONT_TITLE, c)
    elif kind == "chat":
        rounded_rectangle(draw, (cx - 130, cy - 75, cx + 130, cy + 70), radius=25, outline=c, width=lw)
        polygon(draw, [(cx - 45, cy + 70), (cx - 15, cy + 115), (cx + 10, cy + 70)], outline=c, width=lw)
        draw.line((cx - 70, cy - 25, cx + 70, cy - 25), fill=c, width=lw)
        draw.line((cx - 70, cy + 25, cx + 45, cy + 25), fill=c, width=lw)
    elif kind == "company":
        rectangle(draw, (cx - 115, cy - 95, cx + 40, cy + 90), outline=c, width=lw)
        rectangle(draw, (cx - 78, cy - 55, cx - 48, cy - 25), outline=c, width=lw)
        rectangle(draw, (cx - 25, cy - 55, cx + 5, cy - 25), outline=c, width=lw)
        rectangle(draw, (cx - 78, cy + 5, cx - 48, cy + 35), outline=c, width=lw)
        rectangle(draw, (cx - 25, cy + 5, cx + 5, cy + 35), outline=c, width=lw)
        ellipse(draw, (cx + 20, cy - 15, cx + 135, cy + 100), outline=c, width=lw)
        draw.line((cx + 105, cy + 70, cx + 150, cy + 115), fill=c, width=lw)


def main():
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)

    img = Image.new("RGB", (W, H), BG)
    draw = ImageDraw.Draw(img)

    # Header-like subtle background
    draw.rectangle((0, 0, W, H), fill=BG)

    for idx, (label, sub, icon) in enumerate(ITEMS):
        col = idx % COLS
        row = idx // COLS
        x1 = col * CELL_W
        y1 = row * CELL_H
        x2 = x1 + CELL_W
        y2 = y1 + CELL_H

        margin = 28
        rounded_rectangle(
            draw,
            (x1 + margin, y1 + margin, x2 - margin, y2 - margin),
            radius=34,
            fill=WHITE,
            outline=BORDER,
            width=8,
        )

        # icon
        draw_icon(draw, icon, x1 + CELL_W // 2, y1 + 260)

        # sub label
        text_center(
            draw,
            (x1, y1 + 405, x2, y1 + 475),
            sub,
            FONT_SUB,
            MUTED,
        )

        # green bottom button
        bar_h = 210
        rounded_rectangle(
            draw,
            (x1 + margin, y2 - margin - bar_h, x2 - margin, y2 - margin),
            radius=28,
            fill=GREEN,
        )

        text_center(
            draw,
            (x1 + margin, y2 - margin - bar_h, x2 - margin, y2 - margin),
            label,
            FONT_LABEL,
            WHITE,
        )

    img.save(OUT_PATH, "PNG")
    print(f"created: {OUT_PATH}")


if __name__ == "__main__":
    main()
