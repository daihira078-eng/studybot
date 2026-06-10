"""
リッチメニュー登録スクリプト（1回だけ実行）
事前に: pip install pillow
"""
import os
import json
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
HW, HH = W // 2, H // 2

CELLS = [
    {"label": "朝の課題を見る", "emoji": "☀️", "color": (74, 144, 217),  "data": "menu=morning",  "display": "朝の課題を見る"},
    {"label": "夜の振り返り",   "emoji": "🌙", "color": (63, 81, 181),   "data": "menu=evening",  "display": "夜の振り返り"},
    {"label": "今週の記録",     "emoji": "📊", "color": (72, 169, 153),  "data": "menu=weekly",   "display": "今週の記録"},
    {"label": "ストリーク確認", "emoji": "🔥", "color": (255, 152, 0),   "data": "menu=streak",   "display": "ストリーク確認"},
]

POSITIONS = [
    (0,  0,  HW, HH),
    (HW, 0,  W,  HH),
    (0,  HH, HW, H),
    (HW, HH, W,  H),
]


def _hex_to_rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))


def create_image(path="rich_menu.png"):
    img = Image.new("RGB", (W, H), (255, 255, 255))
    draw = ImageDraw.Draw(img)

    font_large = None
    font_small = None
    for font_path in [
        "C:/Windows/Fonts/YuGothB.ttc",
        "C:/Windows/Fonts/meiryob.ttc",
        "C:/Windows/Fonts/msgothic.ttc",
    ]:
        try:
            font_large = ImageFont.truetype(font_path, 110)
            font_small = ImageFont.truetype(font_path, 75)
            break
        except Exception:
            continue
    if font_large is None:
        font_large = ImageFont.load_default()
        font_small = font_large

    for cell, (x1, y1, x2, y2) in zip(CELLS, POSITIONS):
        draw.rectangle([x1, y1, x2 - 1, y2 - 1], fill=cell["color"])
        draw.rectangle([x1, y1, x2 - 1, y2 - 1], outline=(255, 255, 255), width=6)

        cx = (x1 + x2) // 2
        cy = (y1 + y2) // 2

        # ラベルテキスト
        text = cell["label"]
        bbox = draw.textbbox((0, 0), text, font=font_large)
        tw = bbox[2] - bbox[0]
        th = bbox[3] - bbox[1]
        draw.text((cx - tw // 2, cy - th // 2), text, fill=(255, 255, 255), font=font_large)

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
