import sys
sys.stdout.reconfigure(encoding="utf-8")

from morning_check import morning_check_message
from line_sender import send_broadcast
from notion_client_helper import get_streak, get_upcoming_exams


def _build_header() -> str:
    lines = []

    streak = get_streak()
    if streak >= 2:
        lines.append(f"{streak}日連続勉強中！この調子で！")
    elif streak == 1:
        lines.append("昨日も勉強したね！続けよう！")

    exams = get_upcoming_exams()
    for exam in exams[:3]:
        days = exam["days_left"]
        if days == 0:
            lines.append(f"今日は{exam['name']}の試験日！")
        elif days <= 7:
            lines.append(f"{exam['name']}まであと{days}日！")
        elif days <= 30:
            lines.append(f"{exam['name']}まであと{days}日")

    return "\n".join(lines)


def main():
    header = _build_header()
    msg = morning_check_message(header)
    send_broadcast(msg)
    print("朝のチェックメッセージを送信しました")


if __name__ == "__main__":
    main()
