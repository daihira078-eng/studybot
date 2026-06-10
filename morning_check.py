from datetime import datetime, timedelta, timezone
from linebot.v3.messaging import (
    FlexMessage, FlexBubble,
    FlexBox, FlexText, FlexButton, FlexSeparator,
    PostbackAction,
)

_JST = timezone(timedelta(hours=9))
_WEEKDAY_JP = ["月", "火", "水", "木", "金", "土", "日"]

TIME_OPTIONS = {
    "low":  [("30分未満", "short"), ("30分〜1時間", "mid"), ("1〜2時間", "long")],
    "mid":  [("30分〜1時間", "short"), ("1〜2時間", "mid"), ("2時間以上", "long")],
    "high": [("1〜2時間", "short"), ("2〜4時間", "mid"), ("4時間以上", "long")],
}

TIME_LABELS = {
    ("low",  "short"): "30分未満",
    ("low",  "mid"):   "30分〜1時間",
    ("low",  "long"):  "1〜2時間",
    ("mid",  "short"): "30分〜1時間",
    ("mid",  "mid"):   "1〜2時間",
    ("mid",  "long"):  "2時間以上",
    ("high", "short"): "1〜2時間",
    ("high", "mid"):   "2〜4時間",
    ("high", "long"):  "4時間以上",
}

ENERGY_LABELS = {"high": "良好 💪", "mid": "普通 😊", "low": "疲れ気味 😴"}
ENERGY_COLORS = {"high": "#4CAF50", "mid": "#FF9800", "low": "#9E9E9E"}


def morning_check_message(header: str = "") -> FlexMessage:
    now = datetime.now(_JST)
    date_label = f"{now.month}/{now.day}（{_WEEKDAY_JP[now.weekday()]}）"

    body_contents = [
        FlexText(
            text="今日の体調を教えて",
            size="md",
            color="#333333",
            weight="bold",
        ),
    ]

    if header:
        body_contents.append(FlexSeparator(margin="md"))
        for line in header.split("\n"):
            if line.strip():
                body_contents.append(FlexText(
                    text=line.strip(),
                    size="sm",
                    color="#888888",
                    wrap=True,
                    margin="sm",
                ))

    body_contents.append(FlexSeparator(margin="lg"))

    button_defs = [
        ("💪 良好", "energy=high", "#4CAF50"),
        ("😊 普通", "energy=mid",  "#FF9800"),
        ("😴 疲れ気味", "energy=low", "#9E9E9E"),
    ]
    for label, data, color in button_defs:
        body_contents.append(FlexButton(
            action=PostbackAction(label=label, data=data, display_text=label),
            style="primary",
            color=color,
            height="sm",
            margin="sm",
        ))

    bubble = FlexBubble(
        size="kilo",
        header=FlexBox(
            layout="vertical",
            background_color="#4A90D9",
            padding_all="lg",
            contents=[
                FlexText(text="☀️ おはよう！", weight="bold", size="xl", color="#FFFFFF"),
                FlexText(text=date_label, size="sm", color="#C5E8FF"),
            ],
        ),
        body=FlexBox(
            layout="vertical",
            spacing="sm",
            padding_all="lg",
            contents=body_contents,
        ),
    )
    return FlexMessage(alt_text="おはよう！今日の体調は？", contents=bubble)


def time_check_message(energy: str) -> FlexMessage:
    energy_label = ENERGY_LABELS.get(energy, "普通 😊")
    energy_color = ENERGY_COLORS.get(energy, "#FF9800")
    options = TIME_OPTIONS.get(energy, TIME_OPTIONS["mid"])

    body_contents = [
        FlexBox(
            layout="horizontal",
            contents=[
                FlexText(text="体調：", size="sm", color="#888888", flex=0),
                FlexText(text=energy_label, size="sm", color=energy_color, weight="bold"),
            ],
        ),
        FlexText(
            text="今日使える時間は？",
            size="md",
            color="#333333",
            weight="bold",
            margin="md",
        ),
        FlexSeparator(margin="md"),
    ]

    for opt_label, opt_key in options:
        body_contents.append(FlexButton(
            action=PostbackAction(
                label=opt_label,
                data=f"energy={energy}&time={opt_key}",
                display_text=opt_label,
            ),
            style="primary",
            color="#4A90D9",
            height="sm",
            margin="sm",
        ))

    bubble = FlexBubble(
        size="kilo",
        header=FlexBox(
            layout="vertical",
            background_color="#4A90D9",
            padding_all="lg",
            contents=[
                FlexText(
                    text="⏰ 使える時間は？",
                    weight="bold",
                    size="lg",
                    color="#FFFFFF",
                ),
            ],
        ),
        body=FlexBox(
            layout="vertical",
            spacing="sm",
            padding_all="lg",
            contents=body_contents,
        ),
    )
    return FlexMessage(alt_text="今日使える時間は？", contents=bubble)
