"""칼퇴연구소 프로필 사진 (보라 + 시험관 + 키캡) → preview/profile.jpg"""
from pathlib import Path
from playwright.sync_api import sync_playwright

OUT = Path(__file__).parent.parent / "preview"
OUT.mkdir(exist_ok=True)
HTML = """<html><head><meta charset="utf-8">
<link href="https://cdn.jsdelivr.net/gh/orioncactus/pretendard/dist/web/static/pretendard.css" rel="stylesheet">
<style>*{margin:0;padding:0;box-sizing:border-box}
body{width:1080px;height:1080px;font-family:Pretendard,"Noto Sans CJK KR",sans-serif;display:flex;align-items:center;justify-content:center;
background:radial-gradient(circle at 50% 40%,#A78BFA,#6D28D9 60%,#3B0764)}
.k{width:560px;height:400px;background:#C4B5FD;border-radius:90px;padding-bottom:46px;filter:drop-shadow(0 40px 50px rgba(0,0,0,.35))}
.t{width:100%;height:100%;background:#fff;border-radius:90px;display:flex;align-items:center;justify-content:center;
box-shadow:inset 0 -14px 0 rgba(0,0,0,.08),inset 0 10px 0 rgba(255,255,255,.5);color:#4C1D95;font-size:190px;font-weight:900;letter-spacing:-10px}
</style></head><body><div style="display:flex;flex-direction:column;align-items:center;gap:10px">
<div style="font-size:230px;line-height:1;filter:drop-shadow(0 20px 30px rgba(0,0,0,.35))">🧪</div>
<div class="k"><div class="t">칼퇴</div></div></div></body></html>"""

with sync_playwright() as p:
    b = p.chromium.launch()
    pg = b.new_page(viewport={"width": 1080, "height": 1080})
    pg.set_content(HTML, wait_until="networkidle")
    pg.screenshot(path=str(OUT / "profile.jpg"), type="jpeg", quality=92)
    b.close()
print("preview/profile.jpg")
