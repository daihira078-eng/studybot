from linebot.v3.messaging import (
    TextMessage,
    QuickReply,
    QuickReplyItem,
    PostbackAction,
)

ENERGY_LABELS = {"high": "良好", "mid": "普通", "low": "疲れ気味"}

TIME_OPTIONS = {
    "low":  [("30分未満",   "short"), ("30分〜1時間", "mid"), ("1〜2時間",  "long")],
    "mid":  [("30分〜1時間","short"), ("1〜2時間",   "mid"), ("2時間以上", "long")],
    "high": [("1〜2時間",  "short"), ("2〜4時間",   "mid"), ("4時間以上", "long")],
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


def morning_check_message(header: str = ""):
    text = f"{header}\nおはよう！今日の体調を教えて。" if header else "おはよう！今日の体調を教えて。"
    return TextMessage(
        text=text,
        quick_reply=QuickReply(items=[
            QuickReplyItem(action=PostbackAction(label="良好",     data="energy=high", display_text="良好")),
            QuickReplyItem(action=PostbackAction(label="普通",     data="energy=mid",  display_text="普通")),
            QuickReplyItem(action=PostbackAction(label="疲れ気味", data="energy=low",  display_text="疲れ気味")),
        ]),
    )


def time_check_message(energy: str):
    label = ENERGY_LABELS.get(energy, "普通")
    options = TIME_OPTIONS.get(energy, TIME_OPTIONS["mid"])
    items = [
        QuickReplyItem(action=PostbackAction(
            label=opt_label,
            data=f"energy={energy}&time={opt_key}",
            display_text=opt_label,
        ))
        for opt_label, opt_key in options
    ]
    return TextMessage(
        text=f"体調:{label}だね。今日使える時間は？",
        quick_reply=QuickReply(items=items),
    )
