from linebot.v3.messaging import (
    FlexMessage, FlexBubble, FlexCarousel,
    FlexBox, FlexText, FlexButton, FlexSeparator,
    PostbackAction,
)

COLORS = ["#4A90D9", "#7B68EE", "#48A999", "#E8834E", "#C05780"]

DIFFICULTY_BADGE = {
    "易":   ("★☆☆", "#4CAF50"),
    "普通": ("★★☆", "#FF9800"),
    "難":   ("★★★", "#F44336"),
    "easy":   ("★☆☆", "#4CAF50"),
    "normal": ("★★☆", "#FF9800"),
    "hard":   ("★★★", "#F44336"),
}

NUMBERS = ["①", "②", "③", "④", "⑤"]


def build_task_flex(subjects_tasks: list) -> FlexMessage:
    bubbles = []

    for i, item in enumerate(subjects_tasks):
        name = item["name"]
        tasks = item["tasks"]
        difficulty = item.get("difficulty", "")
        days_left = item.get("days_left")
        color = COLORS[i % len(COLORS)]

        badge_text, badge_color = DIFFICULTY_BADGE.get(difficulty, (None, None))

        # ヘッダー
        header_contents = [
            FlexText(text=name, weight="bold", size="lg", color="#FFFFFF", wrap=True, flex=1),
        ]
        if badge_text:
            header_contents.append(FlexText(
                text=badge_text,
                size="sm",
                color=badge_color or "#FFFFFF",
                align="end",
                flex=0,
            ))

        # ボディ
        body_contents = []
        if not tasks:
            body_contents.append(FlexText(
                text="内容を確認しよう",
                wrap=True,
                size="sm",
                color="#aaaaaa",
            ))
        else:
            for j, task in enumerate(tasks):
                num = NUMBERS[j] if j < len(NUMBERS) else f"{j+1}."
                body_contents.append(FlexBox(
                    layout="horizontal",
                    margin="sm",
                    contents=[
                        FlexText(text=num, size="sm", color=color, flex=0, weight="bold"),
                        FlexText(text=task, wrap=True, size="sm", color="#333333", margin="sm"),
                    ],
                ))

        if days_left is not None and 0 <= days_left <= 60:
            body_contents.append(FlexSeparator(margin="md"))
            if days_left == 0:
                countdown = "今日が試験日！"
                countdown_color = "#F44336"
            elif days_left <= 7:
                countdown = f"試験まであと {days_left} 日！"
                countdown_color = "#FF9800"
            else:
                countdown = f"試験まであと {days_left} 日"
                countdown_color = "#888888"
            body_contents.append(FlexText(
                text=f"📅 {countdown}",
                size="xs",
                color=countdown_color,
                margin="sm",
                weight="bold",
            ))

        bubble = FlexBubble(
            size="kilo",
            header=FlexBox(
                layout="horizontal",
                background_color=color,
                padding_all="lg",
                contents=header_contents,
            ),
            body=FlexBox(
                layout="vertical",
                spacing="sm",
                padding_all="lg",
                contents=body_contents,
            ),
            footer=FlexBox(
                layout="horizontal",
                spacing="sm",
                padding_all="sm",
                contents=[
                    FlexButton(
                        action=PostbackAction(
                            label="✅ 完了",
                            data=f"action=complete&subject={name}",
                            display_text=f"✅ {name} 完了！",
                        ),
                        style="primary",
                        color="#4CAF50",
                        height="sm",
                    ),
                    FlexButton(
                        action=PostbackAction(
                            label="⏭ スキップ",
                            data=f"action=skip&subject={name}",
                            display_text=f"⏭ {name} スキップ",
                        ),
                        style="secondary",
                        height="sm",
                    ),
                ],
            ),
        )
        bubbles.append(bubble)

    if not bubbles:
        return None

    container = FlexCarousel(contents=bubbles) if len(bubbles) > 1 else bubbles[0]
    return FlexMessage(alt_text="今日の勉強課題", contents=container)
