from linebot.v3.messaging import (
    FlexMessage, FlexBubble, FlexCarousel,
    FlexBox, FlexText, FlexButton, FlexSeparator,
    PostbackAction,
)

COLORS = ["#4A90D9", "#7B68EE", "#48A999", "#E8834E", "#C05780"]


def build_task_flex(subjects_tasks: list, tone: str = "") -> FlexMessage:
    bubbles = []

    for i, item in enumerate(subjects_tasks):
        name = item["name"]
        tasks = item["tasks"]
        color = COLORS[i % len(COLORS)]

        body_contents = []
        for task in tasks:
            body_contents.append(FlexText(
                text=f"→ {task}",
                wrap=True,
                size="sm",
                color="#444444",
                margin="sm",
            ))

        if not body_contents:
            body_contents.append(FlexText(
                text="内容を確認しよう",
                wrap=True,
                size="sm",
                color="#aaaaaa",
            ))

        if tone:
            body_contents.append(FlexSeparator(margin="md"))
            body_contents.append(FlexText(
                text=tone,
                size="xs",
                color="#888888",
                margin="sm",
                wrap=True,
            ))

        bubble = FlexBubble(
            size="kilo",
            header=FlexBox(
                layout="vertical",
                background_color=color,
                padding_all="lg",
                contents=[FlexText(
                    text=name,
                    weight="bold",
                    size="lg",
                    color="#FFFFFF",
                    wrap=True,
                )],
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
