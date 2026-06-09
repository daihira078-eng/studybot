from linebot.v3.messaging import (
    TextMessage,
    QuickReply,
    QuickReplyItem,
    PostbackAction,
)

ENERGY_LABELS = {"high": "良好", "mid": "普通", "low": "疲れ気味"}
TIME_LABELS = {"short": "1時間未満", "mid": "1〜2時間", "long": "2時間以上"}


def morning_check_message():
    return TextMessage(
        text="おはよう！今日の体調を教えて。",
        quick_reply=QuickReply(items=[
            QuickReplyItem(action=PostbackAction(label="良好", data="energy=high", display_text="良好")),
            QuickReplyItem(action=PostbackAction(label="普通", data="energy=mid", display_text="普通")),
            QuickReplyItem(action=PostbackAction(label="疲れ気味", data="energy=low", display_text="疲れ気味")),
        ]),
    )


def time_check_message(energy: str):
    label = ENERGY_LABELS.get(energy, "普通")
    return TextMessage(
        text=f"体調:{label}だね。今日使える時間は？",
        quick_reply=QuickReply(items=[
            QuickReplyItem(action=PostbackAction(label="1時間未満", data=f"energy={energy}&time=short", display_text="1時間未満")),
            QuickReplyItem(action=PostbackAction(label="1〜2時間", data=f"energy={energy}&time=mid", display_text="1〜2時間")),
            QuickReplyItem(action=PostbackAction(label="2時間以上", data=f"energy={energy}&time=long", display_text="2時間以上")),
        ]),
    )
