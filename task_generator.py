from morning_check import TIME_LABELS

MAX_SUBJECTS = {
    ("low",  "short"): 1,
    ("low",  "mid"):   1,
    ("low",  "long"):  2,
    ("mid",  "short"): 1,
    ("mid",  "mid"):   2,
    ("mid",  "long"):  3,
    ("high", "short"): 2,
    ("high", "mid"):   3,
    ("high", "long"):  99,
}

ENERGY_LABELS = {"high": "良好", "mid": "普通", "low": "疲れ気味"}


def _tone(energy: str, time: str) -> str:
    if energy == "low":
        return "無理せず少しだけやろう。少しでもOK！"
    if energy == "high" and time == "long":
        return "今日は頑張り時！全力でいこう！"
    return "今日も頑張れ！"


def generate_tasks(subjects: list, today_label: str, energy: str = "mid", time: str = "mid") -> str:
    limit = MAX_SUBJECTS.get((energy, time), len(subjects))
    subjects = subjects[:limit]

    energy_label = ENERGY_LABELS.get(energy, "普通")
    time_label = TIME_LABELS.get((energy, time), "")

    if not subjects:
        return (
            f"=== 今日の勉強課題 ===\n"
            f"{today_label}曜日（体調:{energy_label}・{time_label}）\n\n"
            "今日の科目が登録されていません。\n"
            "Notionに科目を追加してください！"
        )

    lines = [f"=== 今日の勉強課題 ===", f"{today_label}曜日（体調:{energy_label}・{time_label}）\n"]
    for s in subjects:
        lines.append(f"■ {s['name']}")
        lines.append(f"  カテゴリ【{s['category']}】難易度【{s['difficulty']}】")
        if s["memo"]:
            lines.append(f"  メモ: {s['memo']}")
        lines.append("")

    lines.append(_tone(energy, time))
    return "\n".join(lines)
