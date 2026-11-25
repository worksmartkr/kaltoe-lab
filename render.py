"""캐러셀 JSON → 1080x1350 JPG 슬라이드 (Instagram API는 JPEG만 지원).

사용:
  python render.py content/work/20261125_엑셀-단축키.json
  python render.py content/work/*.json
"""
import html, json, sys
from pathlib import Path

import yaml
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).parent
W, H = 1080, 1350
FONT = "'Pretendard','Noto Sans KR','Noto Sans CJK KR','Malgun Gothic',sans-serif"


def esc(s):
    return html.escape(s or "").replace("\\n", "<br>").replace("\n", "<br>")


def css(t):
    return f"""
*{{margin:0;padding:0;box-sizing:border-box}}
body{{width:{W}px;height:{H}px;background:{t['bg']};color:{t['text']};font-family:{FONT};
  word-break:keep-all;overflow:hidden;position:relative}}
.pad{{position:absolute;inset:90px 90px 120px 90px;display:flex;flex-direction:column}}
.foot{{position:absolute;left:90px;right:90px;bottom:60px;display:flex;justify-content:space-between;
  font-size:26px;color:{t['sub']};font-weight:600}}
.kicker{{display:inline-block;align-self:flex-start;background:{t['accent']};color:{t['bg']};
  font-weight:800;font-size:34px;padding:12px 26px;border-radius:999px}}
.title{{font-size:104px;font-weight:900;line-height:1.18;letter-spacing:-3px;margin-top:60px}}
.title em{{font-style:normal;color:{t['accent']}}}
.subtitle{{font-size:38px;color:{t['sub']};margin-top:44px;line-height:1.5;font-weight:500}}
.swipe{{margin-top:auto;font-size:32px;font-weight:700;color:{t['accent']}}}
.num{{font-size:160px;font-weight:900;color:{t['accent']};line-height:1;letter-spacing:-4px}}
.mid{{justify-content:center}}
.heading{{font-size:76px;font-weight:900;line-height:1.25;letter-spacing:-2px;margin-top:40px}}
.keys{{display:flex;gap:18px;align-items:center;margin-top:56px;flex-wrap:wrap}}
.key{{background:{t['card']};border:3px solid {t['sub']}55;border-bottom-width:9px;border-radius:20px;
  padding:18px 34px;font-size:52px;font-weight:800;font-family:'Consolas','DejaVu Sans Mono',{FONT}}}
.plus{{font-size:44px;color:{t['sub']};font-weight:700}}
.body{{font-size:46px;line-height:1.62;margin-top:56px;font-weight:500}}
.tip{{margin-top:70px;background:{t['card']};border-left:10px solid {t['accent']};border-radius:18px;
  padding:34px 40px;font-size:36px;line-height:1.5;font-weight:600}}
.tip b{{color:{t['accent']}}}
.cta-title{{font-size:88px;font-weight:900;line-height:1.25;letter-spacing:-2px}}
.cta-row{{display:flex;gap:24px;margin-top:70px}}
.chip{{flex:1;background:{t['card']};border-radius:24px;padding:36px 0;text-align:center;
  font-size:36px;font-weight:800}}
.chip span{{display:block;font-size:64px;margin-bottom:10px}}
.handle{{font-size:50px;font-weight:900;color:{t['accent']};margin-top:70px}}
"""


def emph(title):
    # *강조* → 액센트색
    import re
    return re.sub(r"\*(.+?)\*", r"<em>\1</em>", esc(title))


def page(t, inner, idx, total, acc):
    return f"""<!DOCTYPE html><html><head><meta charset="utf-8">
<link href="https://cdn.jsdelivr.net/gh/orioncactus/pretendard/dist/web/static/pretendard.css" rel="stylesheet">
<style>{css(t)}</style></head><body>{inner}
<div class="foot"><span>{esc(acc['handle'])}</span><span>{idx}/{total}</span></div></body></html>"""


def slides_html(c, acc):
    t = acc["theme"]
    n = len(c["slides"]) + 2
    out = []
    cv = c["cover"]
    out.append(page(t, f"""<div class="pad">
<div class="kicker">{esc(cv.get('kicker',''))}</div>
<div class="title">{emph(cv['title'])}</div>
<div class="subtitle">{esc(cv.get('subtitle',''))}</div>
<div class="swipe">옆으로 넘겨보세요 →</div></div>""", 1, n, acc))
    for i, s in enumerate(c["slides"], 1):
        keys = ""
        if s.get("keys"):
            keys = '<div class="keys">' + '<span class="plus">+</span>'.join(
                f'<span class="key">{esc(k)}</span>' for k in s["keys"]) + "</div>"
        tip = f'<div class="tip"><b>TIP</b> &nbsp;{esc(s["tip"])}</div>' if s.get("tip") else ""
        out.append(page(t, f"""<div class="pad mid">
<div class="num">{i:02d}</div><div class="heading">{esc(s['heading'])}</div>
{keys}<div class="body">{esc(s['body'])}</div>{tip}</div>""", i + 1, n, acc))
    out.append(page(t, f"""<div class="pad mid">
<div class="cta-title">{esc(acc['cta'])}</div>
<div class="cta-row"><div class="chip"><span>🔖</span>저장</div><div class="chip"><span>📤</span>공유</div>
<div class="chip"><span>➕</span>팔로우</div></div>
<div class="handle">{esc(acc['handle'])}</div></div>""", n, n, acc))
    return out


def render(json_path, browser):
    json_path = Path(json_path)
    key = json_path.parent.name
    acc = yaml.safe_load((ROOT / "accounts.yaml").read_text(encoding="utf-8"))["accounts"][key]
    c = json.loads(json_path.read_text(encoding="utf-8"))
    out_dir = ROOT / "output" / key / json_path.stem
    out_dir.mkdir(parents=True, exist_ok=True)
    pg = browser.new_page(viewport={"width": W, "height": H})
    files = []
    for i, h in enumerate(slides_html(c, acc), 1):
        pg.set_content(h, wait_until="networkidle")
        f = out_dir / f"{i:02d}.jpg"
        pg.screenshot(path=str(f), type="jpeg", quality=92)
        files.append(f)
    pg.close()
    caption = c["caption"] + "\n\n" + " ".join("#" + h.lstrip("#") for h in c.get("hashtags", []))
    (out_dir / "caption.txt").write_text(caption, encoding="utf-8")
    print(f"렌더: {out_dir} ({len(files)}장)")
    return out_dir


if __name__ == "__main__":
    with sync_playwright() as p:
        b = p.chromium.launch()
        for path in sys.argv[1:]:
            render(path, b)
        b.close()
