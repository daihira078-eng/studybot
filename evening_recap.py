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


def subject_select_message(all_subjects: list, already_recorded: list) -> TextMessage:
    available = [s for s in all_subjects if s["name"] not in already_recorded]
    items = []

    for s in available[:12]:
        items.append(QuickReplyItem(action=PostbackAction(
            label=s["name"][:20],
            data=f"recap_subject={s['name']}",
            display_text=s["name"],
        )))

    if not already_recorded:
        items.append(QuickReplyItem(action=PostbackAction(
            label="今日は無理だった",
            data="recap_no_study=true",
            display_text="今日は無理だった",
        )))
        text = "今日何を勉強した？"
    else:
        text = "他に何を勉強した？"

    return TextMessage(text=text, quick_reply=QuickReply(items=items))


def ask_study_time_message(subject: str = "") -> TextMessage:
    text = f"{subject}を何分勉強した？\n（例: 45分、1時間30分）" if subject else "何分勉強した？\n（例: 45分、1時間30分）"
    return TextMessage(text=text)


def recap_progress_message(subject: str = "") -> TextMessage:
    text = f"{subject}の進み具合は？" if subject else "進み具合は？"
    return TextMessage(
        text=text,
        quick_reply=QuickReply(items=[
            QuickReplyItem(action=PostbackAction(label="始めた",     data="recap_progress=start",  display_text="始めた")),
            QuickReplyItem(action=PostbackAction(label="少し進んだ", data="recap_progress=little", display_text="少し進んだ")),
            QuickReplyItem(action=PostbackAction(label="半分くらい", data="recap_progress=half",   display_text="半分くらい")),
            QuickReplyItem(action=PostbackAction(label="ほぼ完了",   data="recap_progress=almost", display_text="ほぼ完了")),
            QuickReplyItem(action=PostbackAction(label="完了！",     data="recap_progress=done",   display_text="完了！")),
        ]),
    )


def ask_continue_message() -> TextMessage:
    return TextMessage(
        text="他にも勉強した？",
        quick_reply=QuickReply(items=[
            QuickReplyItem(action=PostbackAction(label="はい", data="recap_continue=yes", display_text="はい")),
            QuickReplyItem(action=PostbackAction(label="以上", data="recap_done=true",    display_text="以上")),
        ]),
    )


ENCOURAGEMENTS = {"great": "素晴らしい！その調子で明日も！", "ok": "十分だよ。積み上げが大事！", "bad": "今日は休んで明日また頑張ろう。"}
