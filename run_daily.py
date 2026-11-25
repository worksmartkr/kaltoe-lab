"""하루 1회 실행: 모든 계정에 대해 생성 → 렌더 → (옵션) 게시.

  python run_daily.py              # 생성+렌더만 (검수용, 기본값)
  python run_daily.py --publish    # 검수 없이 바로 게시까지

처음 2~3주는 --publish 없이 돌리고 output/ 이미지를 직접 확인한 뒤 올리는 걸 추천.
Windows 작업 스케줄러 / cron 에 등록해서 사용.
"""
import argparse

from playwright.sync_api import sync_playwright

import generate, render, publish

ap = argparse.ArgumentParser()
ap.add_argument("--publish", action="store_true")
ap.add_argument("--accounts", nargs="*")
a = ap.parse_args()

keys = a.accounts or list(generate.load_accounts().keys())
with sync_playwright() as p:
    b = p.chromium.launch()
    for k in keys:
        try:
            j = generate.generate(k)
            out = render.render(j, b)
            if a.publish:
                publish.publish(out)
        except SystemExit as e:
            print(f"[{k}] 건너뜀: {e}")
    b.close()
