"""
リッチメニュー登録スクリプト（1回だけ実行）
事前に: pip install pillow
"""
import os
import json
import math
import requests
from dotenv import load_dotenv

load_dotenv()

try:
    from PIL import Image, ImageDraw, ImageFont
except ImportError:
    print("Pillowが必要です: pip install pillow")
    exit(1)

ACCESS_TOKEN = os.environ["LINE_CHANNEL_ACCESS_TOKEN"]
HEADERS = {"Authorization": f"Bearer {ACCESS_TOKEN}"}

W, H = 2500, 1686
COLS, ROWS = 3, 2
CW, CH = W // COLS, H // ROWS

CELLS = [
    {"label": "朝の課題",    "accent": (255, 165, 0),   "data": "menu=morning",   "display": "朝の課題を見る"},
    {"label": "勉強を記録",  "accent": (100, 120, 220),  "data": "menu=record",    "display": "勉強を記録する"},
    {"label": "今日の記録",  "accent": (0,  180, 160),   "data": "menu=today_log", "display": "今日の記録を確認"},
    {"label": "今週の記録",  "accent": (80, 190, 100),   "data": "menu=weekly",    "display": "今週の記録"},
    {"label": "ストリーク",  "accent": (240, 80,  80),   "data": "menu=streak",    "display": "ストリーク確認"},
    {"label": "自由課題",    "accent": (150, 100, 220),  "data": "menu=free_task", "display": "科目別に課題を出す"},
]

POSITIONS = [
    (col * CW, row * CH, (col + 1) * CW, (row + 1) * CH)
    for row in range(ROWS) for col in range(COLS)
]
POSITIONS[-1] = (2 * CW, CH, W, H)

ICON_FUNCTIONS = []


def load_font(size):
    for path in [
        "C:/Windows/Fonts/YuGothB.ttc",
        "C:/Windows/Fonts/meiryob.ttc",
        "C:/Windows/Fonts/msgothic.ttc",
    ]:
        try:
            return ImageFont.truetype(path, size)
        except Exception:
            continue
    return ImageFont.load_default()


def draw_sun(draw, cx, cy, r, color, lw=12):
    draw.ellipse([cx-r, cy-r, cx+r, cy+r], outline=color, width=lw)
    ray = int(r * 0.55)
    for i in range(8):
        angle = math.radians(i * 45)
        x1 = cx + int((r + 18) * math.cos(angle))
        y1 = cy + int((r + 18) * math.sin(angle))
        x2 = cx + int((r + 18 + ray) * math.cos(angle))
        y2 = cy + int((r + 18 + ray) * math.sin(angle))
        draw.line([x1, y1, x2, y2], fill=color, width=lw)


def draw_moon(draw, cx, cy, r, color, lw=12):
    draw.arc([cx-r, cy-r, cx+r, cy+r], start=30, end=330, fill=color, width=lw)
    draw.arc([cx-int(r*0.5), cy-r, cx+int(r*1.3), cy+r], start=210, end=150, fill=(255,255,255), width=lw+4)
    draw.arc([cx-int(r*0.5), cy-r, cx+int(r*1.3), cy+r], start=210, end=150, fill=color, width=lw)


def draw_clipboard(draw, cx, cy, r, color, lw=12):
    x1, y1, x2, y2 = cx - r, cy - int(r * 0.9), cx + r, cy + int(r * 1.1)
    draw.rectangle([x1, y1, x2, y2], outline=color, width=lw)
    bw = int(r * 0.6)
    bh = int(r * 0.25)
    draw.rectangle([cx - bw, y1 - bh, cx + bw, y1 + bh], fill=(255,255,255), outline=color, width=lw)
    for i, offset in enumerate([-0.35, 0, 0.4]):
        ly = cy + int(r * offset)
        draw.line([x1 + int(r*0.3), ly, x2 - int(r*0.25), ly], fill=color, width=lw - 2)


def draw_barchart(draw, cx, cy, r, color, lw=10):
    bars = [0.5, 0.85, 0.65]
    bw = int(r * 0.45)
    gap = int(r * 0.15)
    total_w = len(bars) * bw + (len(bars) - 1) * gap
    start_x = cx - total_w // 2
    base_y = cy + r
    draw.line([start_x - 10, base_y, cx + r + 10, base_y], fill=color, width=lw)
    for i, h_ratio in enumerate(bars):
        bx = start_x + i * (bw + gap)
        bh = int(r * 1.6 * h_ratio)
        draw.rectangle([bx, base_y - bh, bx + bw, base_y], outline=color, width=lw)


def draw_flame(draw, cx, cy, r, color, lw=12):
    pts = [
        (cx, cy - r),
        (cx + int(r*0.7), cy - int(r*0.2)),
        (cx + int(r*0.5), cy + int(r*0.3)),
        (cx + int(r*0.8), cy + r),
        (cx, cy + int(r*0.6)),
        (cx - int(r*0.8), cy + r),
        (cx - int(r*0.5), cy + int(r*0.3)),
        (cx - int(r*0.7), cy - int(r*0.2)),
    ]
    draw.polygon(pts, outline=color, fill=None)
    draw.line(pts + [pts[0]], fill=color, width=lw)


def draw_book(draw, cx, cy, r, color, lw=12):
    lx1, lx2 = cx - r, cx - int(r * 0.1)
    rx1, rx2 = cx + int(r * 0.1), cx + r
    top, bot = cy - int(r * 0.75), cy + int(r * 0.85)
    draw.rectangle([lx1, top, lx2, bot], outline=color, width=lw)
    draw.rectangle([rx1, top, rx2, bot], outline=color, width=lw)
    draw.line([cx, top, cx, bot], fill=color, width=lw)
    for offset in [-0.25, 0.1, 0.45]:
        ly = cy + int(r * offset)
        draw.line([lx1 + int(r*0.2), ly, lx2 - int(r*0.15), ly], fill=color, width=lw - 4)
        draw.line([rx1 + int(r*0.15), ly, rx2 - int(r*0.2), ly], fill=color, width=lw - 4)


def draw_pencil(draw, cx, cy, r, color, lw=12):
    angle = math.radians(45)
    dx, dy = int(r * math.cos(angle)), int(r * math.sin(angle))
    pts = [
        (cx - dx, cy + dy),
        (cx + dx, cy - dy),
        (cx + dx + int(r*0.25), cy - dy + int(r*0.25)),
        (cx - dx + int(r*0.25), cy + dy + int(r*0.25)),
    ]
    draw.polygon(pts, outline=color, fill=None)
    draw.line([pts[0], pts[1]], fill=color, width=lw)
    draw.line([pts[1], pts[2]], fill=color, width=lw)
    draw.line([pts[2], pts[3]], fill=color, width=lw)
    draw.line([pts[3], pts[0]], fill=color, width=lw)
    tip_x = cx - dx - int(r*0.3)
    tip_y = cy + dy + int(r*0.3)
    draw.line([pts[3][0], pts[3][1], tip_x, tip_y], fill=color, width=lw)
    draw.line([pts[0][0], pts[0][1], tip_x, tip_y], fill=color, width=lw)


DRAW_ICONS = [draw_sun, draw_pencil, draw_clipboard, draw_barchart, draw_flame, draw_book]


def create_image(path="rich_menu.png"):
    img = Image.new("RGB", (W, H), (255, 255, 255))
    draw = ImageDraw.Draw(img)

    font_label = load_font(100)

    for i, (cell, (x1, y1, x2, y2)) in enumerate(zip(CELLS, POSITIONS)):
        accent = cell["accent"]
        cx = (x1 + x2) // 2
        cy = (y1 + y2) // 2

        # アクセントバー（上部）
        draw.rectangle([x1, y1, x2, y1 + 14], fill=accent)

        # アイコン描画（上寄り中央）
        icon_cx = cx
        icon_cy = cy - 100
        DRAW_ICONS[i](draw, icon_cx, icon_cy, 110, accent, lw=13)

        # ラベル
        bbox = draw.textbbox((0, 0), cell["label"], font=font_label)
        tw = bbox[2] - bbox[0]
        draw.text((cx - tw // 2, cy + 60), cell["label"], fill=(50, 50, 50), font=font_label)

        # セル境界線
        draw.rectangle([x1, y1, x2 - 1, y2 - 1], outline=(220, 220, 220), width=3)

    # 外枠
    draw.rectangle([0, 0, W - 1, H - 1], outline=(200, 200, 200), width=4)

    img.save(path)
    print(f"画像生成: {path}")
    return path


def create_rich_menu():
    menu = {
        "size": {"width": W, "height": H},
        "selected": True,
        "name": "StudyBot Menu",
        "chatBarText": "メニュー",
        "areas": [
            {
                "bounds": {"x": x1, "y": y1, "width": x2 - x1, "height": y2 - y1},
                "action": {
                    "type": "postback",
                    "data": cell["data"],
                    "displayText": cell["display"],
                },
            }
            for cell, (x1, y1, x2, y2) in zip(CELLS, POSITIONS)
        ],
    }
    resp = requests.post(
        "https://api.line.me/v2/bot/richmenu",
        headers={**HEADERS, "Content-Type": "application/json"},
        data=json.dumps(menu),
    )
    resp.raise_for_status()
    menu_id = resp.json()["richMenuId"]
    print(f"リッチメニュー作成: {menu_id}")
    return menu_id


def upload_image(menu_id, image_path):
    with open(image_path, "rb") as f:
        resp = requests.post(
            f"https://api-data.line.me/v2/bot/richmenu/{menu_id}/content",
            headers={**HEADERS, "Content-Type": "image/png"},
            data=f.read(),
        )
    resp.raise_for_status()
    print("画像アップロード完了")


def set_default(menu_id):
    resp = requests.post(
        f"https://api.line.me/v2/bot/user/all/richmenu/{menu_id}",
        headers=HEADERS,
    )
    resp.raise_for_status()
    print(f"デフォルト設定完了: {menu_id}")


if __name__ == "__main__":
    image_path = create_image()
    menu_id = create_rich_menu()
    upload_image(menu_id, image_path)
    set_default(menu_id)
    print("\nリッチメニューの設定が完了しました！")
