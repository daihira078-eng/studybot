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
COLS, ROWS = 3, 2
CW, CH = W // COLS, H // ROWS  # 833, 843

CELLS = [
    {"label": "朝の課題",    "sub": "今日の課題を確認",   "base": (74,  144, 217), "data": "menu=morning",   "display": "朝の課題を見る"},
    {"label": "夜の振り返り","sub": "今日の勉強を記録",    "base": (63,  81,  181), "data": "menu=evening",   "display": "夜の振り返り"},
    {"label": "今日の記録",  "sub": "記録した内容を確認",  "base": (0,   137, 123), "data": "menu=today_log", "display": "今日の記録を確認"},
    {"label": "今週の記録",  "sub": "週間レポートを表示",  "base": (67,  160, 71),  "data": "menu=weekly",    "display": "今週の記録"},
    {"label": "ストリーク",  "sub": "連続勉強日数を確認",  "base": (251, 140, 0),   "data": "menu=streak",    "display": "ストリーク確認"},
    {"label": "ログリセット","sub": "途中データを初期化",   "base": (117, 117, 117), "data": "menu=reset",     "display": "ログリセット"},
]

POSITIONS = [
    (col * CW, row * CH, (col + 1) * CW, (row + 1) * CH)
    for row in range(ROWS) for col in range(COLS)
]
POSITIONS[-1] = (2 * CW, CH, W, H)  # 最後のセルを端まで広げる


def lighten(color, f=0.4):
    return tuple(min(255, int(c + (255 - c) * f)) for c in color)


def darken(color, f=0.25):
    return tuple(max(0, int(c * (1 - f))) for c in color)


def draw_gradient(draw, x1, y1, x2, y2, color_top, color_bottom, steps=60):
    for i in range(steps):
        t = i / steps
        r = int(color_top[0] + (color_bottom[0] - color_top[0]) * t)
        g = int(color_top[1] + (color_bottom[1] - color_top[1]) * t)
        b = int(color_top[2] + (color_bottom[2] - color_top[2]) * t)
        y_from = y1 + (y2 - y1) * i // steps
        y_to   = y1 + (y2 - y1) * (i + 1) // steps
        draw.rectangle([x1, y_from, x2, y_to], fill=(r, g, b))


def load_font(size):
    for path in [
        "C:/Windows/Fonts/YuGothB.ttc",
        "C:/Windows/Fonts/meiryob.ttc",
        "C:/Windows/Fonts/msgothic.ttc",
        "C:/Windows/Fonts/arial.ttf",
    ]:
        try:
            return ImageFont.truetype(path, size)
        except Exception:
            continue
    return ImageFont.load_default()


def create_image(path="rich_menu.png"):
    img = Image.new("RGB", (W, H), (30, 30, 30))
    draw = ImageDraw.Draw(img)

    font_main = load_font(95)
    font_sub  = load_font(52)

    for cell, (x1, y1, x2, y2) in zip(CELLS, POSITIONS):
        base  = cell["base"]
        top   = lighten(base, 0.35)
        bot   = darken(base, 0.20)

        draw_gradient(draw, x1, y1, x2, y2, top, bot)

        # 左端アクセントライン
        draw.rectangle([x1, y1, x1 + 8, y2], fill=(255, 255, 255, 80))

        # セパレーター
        draw.rectangle([x1, y1, x2, y1 + 3], fill=(255, 255, 255))
        draw.rectangle([x1, y1, x1 + 3, y2], fill=(255, 255, 255))

        cx = (x1 + x2) // 2
        cy = (y1 + y2) // 2

        # メインラベル（少し上寄せ）
        bbox = draw.textbbox((0, 0), cell["label"], font=font_main)
        tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
        draw.text((cx - tw // 2, cy - th // 2 - 40), cell["label"],
                  fill=(255, 255, 255), font=font_main)

        # サブラベル
        bbox2 = draw.textbbox((0, 0), cell["sub"], font=font_sub)
        tw2 = bbox2[2] - bbox2[0]
        draw.text((cx - tw2 // 2, cy + th // 2 + 10), cell["sub"],
                  fill=(255, 255, 255, 180), font=font_sub)

    # 外枠
    draw.rectangle([0, 0, W - 1, H - 1], outline=(255, 255, 255), width=4)

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
