"""게시물 성과 수집 + 계정별 비교 → metrics.csv, 계정 순위 출력.

어떤 계정을 밀지 판단하는 기준: 도달 대비 저장+공유 비율 (save/share rate)
  - 정보형 캐러셀은 좋아요보다 저장·공유가 알고리즘에 더 중요
  - 팔로워 증가도 같이 봄

사용: python metrics.py
"""
import csv, json, os
from collections import defaultdict
from pathlib import Path

import requests
from dotenv import load_dotenv

ROOT = Path(__file__).parent
load_dotenv(ROOT / ".env")
API = "https://graph.instagram.com/v23.0"
METRICS = "reach,views,saved,shares,likes,comments,follows"


def insights(media_id, tok):
    r = requests.get(f"{API}/{media_id}/insights",
                     params={"metric": METRICS, "access_token": tok}, timeout=30)
    if not r.ok:  # 지원 안 되는 지표가 있으면 기본 지표만 재시도
        r = requests.get(f"{API}/{media_id}/insights",
                         params={"metric": "reach,saved,shares,likes,comments", "access_token": tok}, timeout=30)
    r.raise_for_status()
    return {m["name"]: m["values"][0]["value"] for m in r.json()["data"]}


def followers(key):
    uid, tok = os.getenv(f"IG_{key.upper()}_USER_ID"), os.getenv(f"IG_{key.upper()}_TOKEN")
    r = requests.get(f"{API}/{uid}", params={"fields": "followers_count", "access_token": tok}, timeout=30)
    return r.json().get("followers_count", 0) if r.ok else 0


def main():
    log = ROOT / "posted.jsonl"
    if not log.exists():
        print("아직 게시 기록이 없어요")
        return
    rows = []
    for line in log.read_text(encoding="utf-8").splitlines():
        p = json.loads(line)
        tok = os.getenv(f"IG_{p['account'].upper()}_TOKEN")
        try:
            m = insights(p["media_id"], tok)
        except Exception as e:
            print("skip", p["media_id"], e)
            continue
        reach = m.get("reach", 0) or 1
        rows.append({**p, **m, "save_share_rate": round((m.get("saved", 0) + m.get("shares", 0)) / reach * 100, 2)})
    if not rows:
        return
    keys = sorted({k for r in rows for k in r})
    with (ROOT / "metrics.csv").open("w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=keys)
        w.writeheader()
        w.writerows(rows)

    agg = defaultdict(lambda: {"posts": 0, "reach": 0, "saved": 0, "shares": 0})
    for r in rows:
        a = agg[r["account"]]
        a["posts"] += 1
        for k in ("reach", "saved", "shares"):
            a[k] += r.get(k, 0)
    print(f"{'계정':8}{'게시':>5}{'평균도달':>10}{'저장+공유율':>12}{'팔로워':>8}")
    ranked = sorted(agg.items(), key=lambda kv: (kv[1]["saved"] + kv[1]["shares"]) / max(kv[1]["reach"], 1), reverse=True)
    for k, a in ranked:
        rate = (a["saved"] + a["shares"]) / max(a["reach"], 1) * 100
        print(f"{k:8}{a['posts']:>5}{a['reach'] // a['posts']:>10}{rate:>11.2f}%{followers(k):>8}")


if __name__ == "__main__":
    main()
