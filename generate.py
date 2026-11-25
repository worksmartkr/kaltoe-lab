"""주제 → 캐러셀 문안(JSON) 생성 (Claude API).

사용:
  python generate.py work                 # topics/work.txt 맨 위 주제 하나 소비
  python generate.py work --topic "엑셀 단축키 7개"
  python generate.py all                  # 모든 계정 1개씩
"""
import argparse, datetime, json, os, re, sys
from pathlib import Path

import yaml

ROOT = Path(__file__).parent
MODEL = os.getenv("CLAUDE_MODEL", "claude-sonnet-4-5")

SCHEMA_HINT = """{
  "topic": "주제",
  "cover": {"kicker": "짧은 머리말(10자 이내)", "title": "후킹 제목(줄바꿈은 \\n, 2~3줄, 줄당 12자 이내, 강조 단어 하나는 *단어*로 감싸기)", "subtitle": "한 줄 부제"},
  "slides": [
    {"heading": "소제목(18자 이내)", "body": "본문 2~3문장(80자 이내)", "keys": ["Ctrl","E"], "tip": "선택: 한 줄 팁"}
  ],
  "caption": "인스타 캡션(3~5줄, 첫 줄이 후킹)",
  "hashtags": ["해시태그 8~12개, # 없이"]
}"""


def load_accounts():
    return yaml.safe_load((ROOT / "accounts.yaml").read_text(encoding="utf-8"))["accounts"]


def pop_topic(key):
    f = ROOT / "topics" / f"{key}.txt"
    if not f.exists():
        sys.exit(f"주제 파일 없음: {f}")
    lines = [l for l in f.read_text(encoding="utf-8").splitlines() if l.strip()]
    if not lines:
        sys.exit(f"{f} 주제가 다 떨어졌어요")
    f.write_text("\n".join(lines[1:]) + "\n", encoding="utf-8")
    return lines[0].strip()


def build_prompt(acc, topic):
    return f"""너는 인스타그램 정보형 캐러셀 작가야.
계정: {acc['name']} ({acc['handle']})
니치: {acc['niche']}
타깃: {acc['audience']}
톤: {acc['tone']}

주제: {topic}

규칙:
- 본문 슬라이드 5~7장. 한 장에 한 가지 포인트만.
- 사실이 정확해야 함. 확실하지 않은 수치·주장은 쓰지 마.
- 다른 계정 문구를 베끼지 말고, 저장하고 싶을 만큼 구체적으로.
- keys는 단축키처럼 키캡으로 보여줄 게 있을 때만, 아니면 생략.
- 반드시 아래 JSON 형식만 출력(코드블록·설명 금지):
{SCHEMA_HINT}"""


def call_claude(prompt):
    import anthropic  # pip install anthropic
    client = anthropic.Anthropic()  # ANTHROPIC_API_KEY 환경변수
    msg = client.messages.create(model=MODEL, max_tokens=2000,
                                 messages=[{"role": "user", "content": prompt}])
    text = msg.content[0].text.strip()
    text = re.sub(r"^```(json)?|```$", "", text, flags=re.M).strip()
    return json.loads(text)


def validate(c):
    assert c["cover"]["title"] and 3 <= len(c["slides"]) <= 8, "슬라이드 개수 이상"
    for s in c["slides"]:
        assert s.get("heading") and s.get("body"), "빈 슬라이드"
    return c


def slugify(s):
    return re.sub(r"[^\w가-힣]+", "-", s).strip("-")[:30]


def generate(key, topic=None):
    acc = load_accounts()[key]
    topic = topic or pop_topic(key)
    content = validate(call_claude(build_prompt(acc, topic)))
    out = ROOT / "content" / key / f"{datetime.date.today():%Y%m%d}_{slugify(topic)}.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(content, ensure_ascii=False, indent=2), encoding="utf-8")
    print("생성:", out)
    return out


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("account", help="계정 키 또는 all")
    ap.add_argument("--topic")
    a = ap.parse_args()
    keys = load_accounts().keys() if a.account == "all" else [a.account]
    for k in keys:
        generate(k, a.topic)
