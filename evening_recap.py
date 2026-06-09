from linebot.v3.messaging import (
    TextMessage,
    QuickReply,
    QuickReplyItem,
    PostbackAction,
)


def evening_check_message():
    return TextMessage(
        text="お疲れ様！今日の勉強を振り返ろう。\n頑張り度合いは？",
        quick_reply=QuickReply(items=[
            QuickReplyItem(action=PostbackAction(label="頑張れた！", data="recap_energy=great", display_text="頑張れた！")),
            QuickReplyItem(action=PostbackAction(label="まあまあ",   data="recap_energy=ok",    display_text="まあまあ")),
            QuickReplyItem(action=PostbackAction(label="イマイチ",   data="recap_energy=bad",   display_text="イマイチ")),
        ]),
    )


def ask_study_time_message():
    return TextMessage(text="今日は何分勉強できた？\n（例: 45分、1時間30分）")


def recap_progress_message():
    return TextMessage(
        text="課題の進み具合は？",
        quick_reply=QuickReply(items=[
            QuickReplyItem(action=PostbackAction(label="始めた",     data="recap_progress=start",  display_text="始めた")),
            QuickReplyItem(action=PostbackAction(label="少し進んだ", data="recap_progress=little", display_text="少し進んだ")),
            QuickReplyItem(action=PostbackAction(label="半分くらい", data="recap_progress=half",   display_text="半分くらい")),
            QuickReplyItem(action=PostbackAction(label="ほぼ完了",   data="recap_progress=almost", display_text="ほぼ完了")),
            QuickReplyItem(action=PostbackAction(label="完了！",     data="recap_progress=done",   display_text="完了！")),
        ]),
    )


ENERGY_LABELS   = {"great": "頑張れた！", "ok": "まあまあ", "bad": "イマイチ"}
PROGRESS_LABELS = {"start": "始めた", "little": "少し進んだ", "half": "半分くらい", "almost": "ほぼ完了", "done": "完了！"}
ENCOURAGEMENTS  = {"great": "素晴らしい！その調子で明日も！", "ok": "十分だよ。積み上げが大事！", "bad": "今日は休んで明日また頑張ろう。"}


def recap_summary(energy: str, time_text: str, progress: str) -> str:
    e   = ENERGY_LABELS.get(energy, energy)
    p   = PROGRESS_LABELS.get(progress, progress)
    enc = ENCOURAGEMENTS.get(energy, "お疲れ様！")
    return f"今日の記録を保存したよ！\n頑張り:{e} / 時間:{time_text} / 進行度:{p}\n\n{enc}"
