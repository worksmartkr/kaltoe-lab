"""1회 실행: 계정마다 캐러셀 1개 → 렌더 + 릴스 영상 → (옵션) 캐러셀·릴스 게시.

문안 출처
  - queue/<계정>/*.json 이 있으면 파일명 순서대로 하나 꺼내 씀 (API 비용 0)
  - 큐가 비었고 ANTHROPIC_API_KEY 가 있으면 generate.py 로 자동 생성

  python run_daily.py                      # 렌더만 (큐에서 빼지 않음, 미리보기용)
  python run_daily.py --publish            # 렌더 + 게시, 성공하면 큐에서 content/ 로 이동
  python run_daily.py --accounts work
"""
import argparse, os, shutil, sys
from pathlib import Path

from playwright.sync_api import sync_playwright

import generate, render, publish, reel

ROOT = Path(__file__).parent


def next_content(key):
    q = sorted((ROOT / "queue" / key).glob("*.json"))
    if q:
        return q[0]
    if os.getenv("ANTHROPIC_API_KEY"):
        return generate.generate(key)
    sys.exit(f"queue/{key} 비었음 — 문안을 더 채워주세요")


ap = argparse.ArgumentParser()
ap.add_argument("--publish", action="store_true")
ap.add_argument("--accounts", nargs="*")
a = ap.parse_args()

keys = a.accounts or list(generate.load_accounts().keys())
with sync_playwright() as p:
    b = p.chromium.launch()
    for k in keys:
        try:
            j = next_content(k)
            out = render.render(j, b)
            reel.make_reel(out)
            if a.publish:
                publish.publish(out)
                if j.parent.parent.name == "queue":  # 게시 성공 후에만 큐에서 제거
                    dst = ROOT / "content" / k / j.name
                    dst.parent.mkdir(parents=True, exist_ok=True)
                    shutil.move(j, dst)
        except SystemExit as e:
            print(f"[{k}] 건너뜀: {e}")
    b.close()
