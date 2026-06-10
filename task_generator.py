import os
import re
import requests
from dotenv import load_dotenv
from morning_check import TIME_LABELS

load_dotenv()

ENERGY_LABELS = {"high": "良好", "mid": "普通", "low": "疲れ気味"}

# (energy, time) → (課題数, 難易度ヒント)
# 時間が優先、体調が量を調整
TASK_CONFIG = {
    ("low",  "short"): (1, "易しめ"),   # 30分未満
    ("low",  "mid"):   (1, "易しめ"),   # 30分〜1時間
    ("low",  "long"):  (1, "普通"),     # 1〜2時間・疲れ→1個
    ("mid",  "short"): (1, "普通"),     # 30分〜1時間
    ("mid",  "mid"):   (2, "難し目"),   # 1〜2時間・2個→難し目
    ("mid",  "long"):  (3, "普通"),     # 2時間以上・3個→普通目
    ("high", "short"): (2, "難し目"),   # 1〜2時間・2個→難し目
    ("high", "mid"):   (3, "普通"),     # 2〜4時間・3個→普通目
    ("high", "long"):  (3, "難し目"),   # 4時間以上・難し目
}

MAX_SUBJECTS = {
    ("low",  "short"): 1,
    ("low",  "mid"):   1,
    ("low",  "long"):  1,
    ("mid",  "short"): 1,
    ("mid",  "mid"):   2,
    ("mid",  "long"):  2,
    ("high", "short"): 2,
    ("high", "mid"):   2,
    ("high", "long"):  3,
}


def _tone(energy: str, time: str) -> str:
    if energy == "low":
        return "無理せず少しだけやろう。少しでもOK！"
    if energy == "high" and time == "long":
        return "今日は頑張り時！全力でいこう！"
    return "今日も頑張れ！"


def _ask_ai(subjects: list, today_label: str, energy: str, time: str, understanding: dict = None) -> str:
    energy_label = ENERGY_LABELS.get(energy, "普通")
    time_label = TIME_LABELS.get((energy, time), "")

    subject_lines = "\n".join(
        f"- {s['name']}（カテゴリ:{s['category']} / 難易度:{s['difficulty']}"
        + (f" / メモ:{s['memo']}" if s["memo"] else "")
        + ("）\n  [詳細]\n" + "\n".join(f"  {l}" for l in s["detail"].splitlines()) if s.get("detail") else "）")
        for s in subjects
    )

    understanding_lines = ""
    if understanding:
        lines = [f"- {name}: {level}" for name, level in understanding.items() if name in {s["name"] for s in subjects}]
        if lines:
            understanding_lines = "\n昨日の理解度：\n" + "\n".join(lines) + "\n（「難しかった」は易しめに、「バッチリ！」は少し難しめに調整）"

    task_count, difficulty = TASK_CONFIG.get((energy, time), (2, "普通"))

    prompt = f"""あなたは大学生の勉強をサポートするコーチです。
今日（{today_label}曜日）の状況：体調={energy_label}、使える時間={time_label}
{understanding_lines}
勉強する科目：
{subject_lines}

各科目に対して、今日扱うトピックを1つ決め、そのトピックの具体的な課題を{task_count}個ずつ命令口調で提示してください。
難易度は「{difficulty}」を意識して設定してください。
メモがある場合はそれを最優先で参考にし、ない場合は科目名から内容を推測して、具体的なトピック・問題タイプ・章を指定した課題にしてください。
昨日の理解度も考慮して内容を調整してください。
フォーマット（このフォーマット厳守）：
■ 科目名
  【テーマ】テーマ名
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
        theme = ""
        tasks = []
        for line in lines[1:]:
            line = line.strip()
            if "【テーマ】" in line:
                theme = line.replace("【テーマ】", "").strip().lstrip("：: ").strip()
            elif '→' in line:
                tasks.append(line.lstrip('→').strip())
        if name:
            result.append({"name": name, "theme": theme, "tasks": tasks})
    return result


def generate_tasks_structured(subjects: list, today_label: str, energy: str = "mid", time: str = "mid", understanding: dict = None):
    limit = MAX_SUBJECTS.get((energy, time), len(subjects))
    subjects = subjects[:limit]
    energy_label = ENERGY_LABELS.get(energy, "普通")
    time_label = TIME_LABELS.get((energy, time), "")
    header = f"=== 今日の勉強課題 ===\n{today_label}曜日（体調:{energy_label}・{time_label}）"
    tone = _tone(energy, time)
    if not subjects:
        return header + "\n\n今日の科目が登録されていません。", [], tone
    body_text = _ask_ai(subjects, today_label, energy, time, understanding)
    parsed = _parse_tasks(body_text)
    if not parsed:
        parsed = [{"name": s["name"], "tasks": []} for s in subjects]
    subject_map = {s["name"]: s for s in subjects}
    for item in parsed:
        s = subject_map.get(item["name"], {})
        item["difficulty"] = s.get("difficulty", "")
        item["days_left"] = s.get("days_left")
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
