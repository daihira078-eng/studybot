ENERGY_LABELS = {"high": "良好", "mid": "普通", "low": "疲れ気味"}
TIME_LABELS = {"short": "1時間未満", "mid": "1〜2時間", "long": "2時間以上"}

MAX_SUBJECTS = {
    ("high", "long"): 99,
    ("high", "mid"): 3,
    ("high", "short"): 2,
    ("mid", "long"): 3,
    ("mid", "mid"): 2,
    ("mid", "short"): 1,
    ("low", "long"): 2,
    ("low", "mid"): 1,
    ("low", "short"): 1,
}


def generate_tasks(subjects: list, today_label: str, energy: str = "mid", time: str = "mid") -> str:
    limit = MAX_SUBJECTS.get((energy, time), len(subjects))
    subjects = subjects[:limit]

    energy_label = ENERGY_LABELS.get(energy, "普通")
    time_label = TIME_LABELS.get(time, "1〜2時間")

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

    lines.append("今日も頑張れ！")
    return "\n".join(lines)
