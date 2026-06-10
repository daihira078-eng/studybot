from linebot.v3.messaging import (
    FlexMessage, FlexBubble,
    FlexBox, FlexText, FlexButton, FlexSeparator,
    PostbackAction, TextMessage, QuickReply, QuickReplyItem,
)


def evening_check_message() -> FlexMessage:
    button_defs = [
        ("頑張れた！ 🔥", "recap_energy=great", "#4CAF50"),
        ("まあまあ 😊",   "recap_energy=ok",    "#FF9800"),
        ("イマイチ 😴",   "recap_energy=bad",   "#9E9E9E"),
    ]
    body_contents = [
        FlexText(
            text="今日の頑張り度合いは？",
            size="md",
            color="#333333",
            weight="bold",
        ),
        FlexSeparator(margin="md"),
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
            background_color="#3F51B5",
            padding_all="lg",
            contents=[
                FlexText(text="🌙 お疲れ様！", weight="bold", size="xl", color="#FFFFFF"),
                FlexText(text="今日の勉強を振り返ろう", size="sm", color="#C5CAE9"),
            ],
        ),
        body=FlexBox(
            layout="vertical",
            spacing="sm",
            padding_all="lg",
            contents=body_contents,
        ),
    )
    return FlexMessage(alt_text="お疲れ様！今日の振り返り", contents=bubble)


def subject_select_message(today_subjects: list, all_subjects: list, already_recorded: list) -> FlexMessage:
    today_names = {s["name"] for s in today_subjects}
    available_today = [s for s in today_subjects if s["name"] not in already_recorded]
    available_other = [s for s in all_subjects if s["name"] not in already_recorded and s["name"] not in today_names]

    body_contents = []
    is_first = not already_recorded

    if available_today:
        body_contents.append(FlexText(
            text="今日の科目" if is_first else "他に今日の科目",
            size="xs",
            color="#888888",
            weight="bold",
        ))
        for s in available_today[:8]:
            body_contents.append(FlexButton(
                action=PostbackAction(
                    label=s["name"][:20],
                    data=f"recap_subject={s['name']}",
                    display_text=s["name"],
                ),
                style="primary",
                color="#4A90D9",
                height="sm",
                margin="xs",
            ))

    if available_other:
        body_contents.append(FlexSeparator(margin="md"))
        body_contents.append(FlexText(
            text="その他の科目",
            size="xs",
            color="#888888",
            weight="bold",
            margin="md",
        ))
        for s in available_other[:6]:
            body_contents.append(FlexButton(
                action=PostbackAction(
                    label=s["name"][:20],
                    data=f"recap_subject={s['name']}",
                    display_text=s["name"],
                ),
                style="secondary",
                height="sm",
                margin="xs",
            ))

    body_contents.append(FlexSeparator(margin="md"))
    if is_first:
        body_contents.append(FlexButton(
            action=PostbackAction(label="今日は無理だった", data="recap_no_study=true", display_text="今日は無理だった"),
            style="secondary",
            color="#9E9E9E",
            height="sm",
            margin="sm",
        ))
    else:
        body_contents.append(FlexButton(
            action=PostbackAction(label="以上で終わる", data="recap_done=true", display_text="以上"),
            style="primary",
            color="#3F51B5",
            height="sm",
            margin="sm",
        ))

    header_text = "今日何を勉強した？" if is_first else "他にも勉強した？"

    bubble = FlexBubble(
        size="kilo",
        header=FlexBox(
            layout="vertical",
            background_color="#3F51B5",
            padding_all="md",
            contents=[
                FlexText(text=header_text, weight="bold", size="lg", color="#FFFFFF"),
            ],
        ),
        body=FlexBox(
            layout="vertical",
            spacing="xs",
            padding_all="md",
            contents=body_contents,
        ),
    )
    return FlexMessage(alt_text=header_text, contents=bubble)


def ask_study_time_message(subject: str = "") -> TextMessage:
    text = f"⏱ {subject}を何分勉強した？\n（例: 45、1時間30分）" if subject else "⏱ 何分勉強した？\n（例: 45、1時間30分）"
    return TextMessage(text=text)


def recap_progress_message(subject: str = "") -> FlexMessage:
    options = [
        ("始めた",     "recap_progress=start",  "#9E9E9E"),
        ("少し進んだ", "recap_progress=little",  "#2196F3"),
        ("半分くらい", "recap_progress=half",    "#FF9800"),
        ("ほぼ完了",   "recap_progress=almost",  "#8BC34A"),
        ("完了！",     "recap_progress=done",    "#4CAF50"),
    ]
    body_contents = []
    for label, data, color in options:
        body_contents.append(FlexButton(
            action=PostbackAction(label=label, data=data, display_text=label),
            style="primary",
            color=color,
            height="sm",
            margin="xs",
        ))

    header_text = f"📖 {subject}の進み具合は？" if subject else "📖 進み具合は？"
    bubble = FlexBubble(
        size="kilo",
        header=FlexBox(
            layout="vertical",
            background_color="#3F51B5",
            padding_all="md",
            contents=[FlexText(text=header_text, weight="bold", size="md", color="#FFFFFF", wrap=True)],
        ),
        body=FlexBox(
            layout="vertical",
            spacing="xs",
            padding_all="md",
            contents=body_contents,
        ),
    )
    return FlexMessage(alt_text="進み具合は？", contents=bubble)


def ask_continue_message() -> FlexMessage:
    bubble = FlexBubble(
        size="kilo",
        body=FlexBox(
            layout="vertical",
            spacing="sm",
            padding_all="lg",
            contents=[
                FlexText(text="他にも勉強した？", size="md", color="#333333", weight="bold"),
                FlexSeparator(margin="md"),
                FlexButton(
                    action=PostbackAction(label="はい、追加する", data="recap_continue=yes", display_text="はい"),
                    style="primary",
                    color="#4A90D9",
                    height="sm",
                    margin="md",
                ),
                FlexButton(
                    action=PostbackAction(label="以上で終わる", data="recap_done=true", display_text="以上"),
                    style="secondary",
                    height="sm",
                    margin="sm",
                ),
            ],
        ),
    )
    return FlexMessage(alt_text="他にも勉強した？", contents=bubble)


ENCOURAGEMENTS = {"great": "素晴らしい！その調子で明日も！", "ok": "十分だよ。積み上げが大事！", "bad": "今日は休んで明日また頑張ろう。"}
