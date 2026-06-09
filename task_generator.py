import os
import re
import requests
from dotenv import load_dotenv
from morning_check import TIME_LABELS

load_dotenv()

ENERGY_LABELS = {"high": "良好", "mid": "普通", "low": "疲れ気味"}

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


def _tone(energy: str, time: str) -> str:
    if energy == "low":
        return "無理せず少しだけやろう。少しでもOK！"
    if energy == "high" and time == "long":
        return "今日は頑張り時！全力でいこう！"
    return "今日も頑張れ！"


def _ask_ai(subjects: list, today_label: str, energy: str, time: str) -> str:
    energy_label = ENERGY_LABELS.get(energy, "普通")
    time_label = TIME_LABELS.get((energy, time), "")

    subject_lines = "\n".join(
        f"- {s['name']}（カテゴリ:{s['category']} / 難易度:{s['difficulty']}"
        + (f" / メモ:{s['memo']}" if s["memo"] else "")
        + ("）\n  [詳細]\n" + "\n".join(f"  {l}" for l in s["detail"].splitlines()) if s.get("detail") else "）")
        for s in subjects
    )

    task_count = {"high": "2〜3個", "mid": "1〜2個", "low": "1個"}.get(energy, "1〜2個")

    prompt = f"""あなたは大学生の勉強をサポートするコーチです。
今日（{today_label}曜日）の状況：体調={energy_label}、使える時間={time_label}

勉強する科目：
{subject_lines}

各科目に対して、今日やるべき具体的な課題を{task_count}ずつ命令口調で提示してください。
メモがある場合はそれを最優先で参考にし、ない場合は科目名から内容を推測して、具体的なトピック・問題タイプ・章を指定した課題にしてください。
難易度・使える時間に応じて内容を調整してください。
フォーマット：
■ 科目名
  → 課題内容

絵文字・余計な説明は不要。課題だけを簡潔に。"""

    try:
        key = os.environ.get("GROQ_API_KEY", "")
        resp = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
            json={"model": "llama-3.3-70b-versatile", "messages": [{"role": "user", "content": prompt}], "max_tokens": 512},
            timeout=30,
        )
        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"].strip()
    except Exception as e:
        print(f"Groq error: {e}")
        return _fallback(subjects)


def _fallback(subjects: list) -> str:
    lines = []
    for s in subjects:
        lines.append(f"■ {s['name']}")
        lines.append(f"  カテゴリ【{s['category']}】難易度【{s['difficulty']}】")
        if s["memo"]:
            lines.append(f"  メモ: {s['memo']}")
        lines.append("")
    return "\n".join(lines)


def _parse_tasks(text: str) -> list:
    result = []
    for block in re.split(r'\n?■\s*', text):
        block = block.strip()
        if not block:
            continue
        lines = block.split('\n')
        name = lines[0].strip()
        tasks = [l.strip().lstrip('→').strip() for l in lines[1:] if '→' in l]
        if name:
            result.append({"name": name, "tasks": tasks})
    return result


def generate_tasks_structured(subjects: list, today_label: str, energy: str = "mid", time: str = "mid"):
    limit = MAX_SUBJECTS.get((energy, time), len(subjects))
    subjects = subjects[:limit]
    energy_label = ENERGY_LABELS.get(energy, "普通")
    time_label = TIME_LABELS.get((energy, time), "")
    header = f"=== 今日の勉強課題 ===\n{today_label}曜日（体調:{energy_label}・{time_label}）"
    tone = _tone(energy, time)
    if not subjects:
        return header + "\n\n今日の科目が登録されていません。", [], tone
    body_text = _ask_ai(subjects, today_label, energy, time)
    parsed = _parse_tasks(body_text)
    if not parsed:
        parsed = [{"name": s["name"], "tasks": []} for s in subjects]
    return header, parsed, tone


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

    header = f"=== 今日の勉強課題 ===\n{today_label}曜日（体調:{energy_label}・{time_label}）\n\n"
    body = _ask_ai(subjects, today_label, energy, time)
    footer = f"\n\n{_tone(energy, time)}"

    return header + body + footer
