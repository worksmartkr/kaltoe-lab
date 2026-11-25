"""캐러셀 JSON → 1080x1350 JPG 슬라이드 (Instagram API는 JPEG만 지원).

사용:
  python render.py content/work/20261125_엑셀-단축키.json
  python render.py content/work/*.json
"""
import html, json, sys
from pathlib import Path

import yaml
import pages
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
/* 시각 자료가 있는 슬라이드는 촘촘하게 */
.has-vis .num{{font-size:96px}}
.has-vis .heading{{font-size:62px;margin-top:20px}}
.has-vis .keys{{margin-top:32px}}
.has-vis .key{{font-size:40px;padding:12px 26px}}
.has-vis .body{{font-size:38px;margin-top:36px;line-height:1.55}}
.has-vis .tip{{margin-top:36px;font-size:32px;padding:26px 34px}}
.vis{{margin-top:40px}}
/* 엑셀 표 */
.sheet{{border-collapse:collapse;background:#fff;color:#111;font-size:34px;border-radius:14px;overflow:hidden;
  box-shadow:0 10px 30px rgba(0,0,0,.25)}}
.sheet th{{background:#E8EAED;color:#555;font-weight:600;font-size:26px;padding:8px 14px;border:1px solid #CFD3D8}}
.sheet td{{padding:12px 18px;border:1px solid #DADCE0;white-space:nowrap}}
.sheet td.rn{{background:#E8EAED;color:#555;font-size:24px;text-align:center;padding:8px 12px}}
.sheet td.hl{{background:#C8F7DC;outline:4px solid #16A34A;outline-offset:-4px;font-weight:700}}
.sheet td.bad{{background:#FEE2E2;color:#B91C1C}}
.sheet td.warn{{background:#FEF3C7}}
.sheet td.mute{{color:#9CA3AF}}
.sheet-label{{font-size:26px;font-weight:800;color:{t['sub']};margin-bottom:12px}}
.ba{{display:flex;align-items:center;gap:22px}}
.ba .arrow{{font-size:56px;color:{t['accent']};font-weight:900}}
.fx{{display:flex;align-items:center;gap:0;background:#fff;color:#111;border-radius:12px 12px 0 0;font-size:28px;
  border:1px solid #DADCE0;border-bottom:none;overflow:hidden}}
.fx b{{background:#E8EAED;color:#555;padding:10px 16px;font-style:italic;font-family:serif}}
.fx span{{padding:10px 18px;font-family:'Consolas','DejaVu Sans Mono',monospace}}
.fx + .sheet{{border-radius:0 0 14px 14px}}
/* 수식/코드 */
.code{{background:#0B1020;color:#E5E7EB;border-radius:18px;padding:30px 34px;font-family:'Consolas','DejaVu Sans Mono',monospace;
  font-size:34px;line-height:1.5;white-space:pre-wrap;word-break:break-all;border:2px solid {t['accent']}55}}
.code .lbl{{display:block;font-family:{FONT};font-size:24px;color:{t['accent']};font-weight:800;margin-bottom:10px}}
/* 메뉴 경로 */
.path{{display:flex;flex-wrap:wrap;align-items:center;gap:14px}}
.path .step{{background:#fff;color:#111;border-radius:12px;padding:14px 22px;font-size:32px;font-weight:700;
  box-shadow:0 4px 0 #CBD5E1}}
.path .step.last{{background:{t['accent']};color:{t['bg']};box-shadow:0 4px 0 {t['sub']}}}
.path .sep{{font-size:36px;color:{t['accent']};font-weight:900}}
/* AI 프롬프트 말풍선 */
.chat{{display:flex;flex-direction:column;gap:16px}}
.bubble{{max-width:88%;padding:22px 28px;border-radius:26px;font-size:32px;line-height:1.5;white-space:pre-wrap}}
.bubble.me{{align-self:flex-end;background:{t['accent']};color:{t['bg']};border-bottom-right-radius:8px;font-weight:600}}
.bubble.ai{{align-self:flex-start;background:#fff;color:#111;border-bottom-left-radius:8px}}
.bubble .who{{display:block;font-size:22px;font-weight:800;opacity:.7;margin-bottom:6px}}
/* 체크리스트 */
.checks{{display:flex;flex-direction:column;gap:14px}}
.check{{display:flex;gap:16px;align-items:center;background:{t['card']};border-radius:14px;padding:18px 24px;font-size:32px;font-weight:600}}
.check i{{font-style:normal;font-size:34px}}
"""


def sheet_html(v):
    """v = {cols:[...], rows:[[...]], hl:[[r,c]], bad:[[r,c]], warn:[[r,c]], fx:"=수식", start:1}"""
    cols = v.get("cols") or [chr(65 + i) for i in range(len(v["rows"][0]))]
    marks = {}
    for cls in ("hl", "bad", "warn", "mute"):
        for r, c in v.get(cls, []):
            marks[(r, c)] = cls
    start = v.get("start", 1)
    h = '<table class="sheet"><tr><th></th>' + "".join(f"<th>{esc(c)}</th>" for c in cols) + "</tr>"
    for r, row in enumerate(v["rows"]):
        h += f'<tr><td class="rn">{start + r}</td>'
        for c, cell in enumerate(row):
            cls = marks.get((r, c), "")
            h += f'<td class="{cls}">{esc(str(cell))}</td>'
        h += "</tr>"
    h += "</table>"
    if v.get("fx"):
        h = f'<div><div class="fx"><b>fx</b><span>{esc(v["fx"])}</span></div>{h}</div>'
    if v.get("label"):
        h = f'<div><div class="sheet-label">{esc(v["label"])}</div>{h}</div>'
    return h


def visual_html(v):
    if not v:
        return ""
    t = v["type"]
    if t == "sheet":
        inner = sheet_html(v)
    elif t == "beforeafter":
        inner = ('<div class="ba">' + sheet_html({**v["before"], "label": v["before"].get("label", "전")})
                 + '<div class="arrow">→</div>'
                 + sheet_html({**v["after"], "label": v["after"].get("label", "후")}) + "</div>")
    elif t == "code":
        lbl = f'<span class="lbl">{esc(v["label"])}</span>' if v.get("label") else ""
        inner = f'<div class="code">{lbl}{esc(v["text"])}</div>'
    elif t == "path":
        steps = v["steps"]
        inner = '<div class="path">' + '<span class="sep">›</span>'.join(
            f'<span class="step{" last" if i == len(steps) - 1 else ""}">{esc(x)}</span>'
            for i, x in enumerate(steps)) + "</div>"
    elif t == "chat":
        inner = '<div class="chat">' + "".join(
            f'<div class="bubble {m["role"]}"><span class="who">{"나" if m["role"] == "me" else "AI"}</span>{esc(m["text"])}</div>'
            for m in v["messages"]) + "</div>"
    elif t == "checks":
        inner = '<div class="checks">' + "".join(
            f'<div class="check"><i>{esc(x.get("icon", "✅"))}</i>{esc(x["text"])}</div>' for x in v["items"]) + "</div>"
    else:
        return ""
    return f'<div class="vis vis-{t}">{inner}</div>'


def emph(title):
    # *강조* → 액센트색
    import re
    return re.sub(r"\*(.+?)\*", r"<em>\1</em>", esc(title))


def page(t, inner, idx, total, acc):
    return f"""<!DOCTYPE html><html><head><meta charset="utf-8">
<link href="https://cdn.jsdelivr.net/gh/orioncactus/pretendard/dist/web/static/pretendard.css" rel="stylesheet">
<style>{css(t)}</style></head><body>{inner}
<div class="foot"><span>{esc(acc['handle'])}</span><span>{idx}/{total}</span></div></body></html>"""


MAG_CSS = """
.mag{{position:absolute;inset:0;background:#0B0A10;color:#fff}}
.mag .brand{{position:absolute;top:34px;left:0;right:0;text-align:center;font-size:24px;letter-spacing:6px;font-weight:800;color:#ffffffb0}}
/* 표지 */
.cover-bg{{position:absolute;inset:0;background:radial-gradient(120% 80% at 50% 25%,{acc}55,#1B1030 55%,#0B0A10 100%)}}
.cover-art{{position:absolute;top:120px;left:0;right:0;height:760px;display:flex;align-items:center;justify-content:center}}
.cover-art .vis{{transform:rotate(-4deg) scale(1.25);filter:drop-shadow(0 40px 60px rgba(0,0,0,.55));margin:0}}
.cover-fade{{position:absolute;left:0;right:0;bottom:0;height:640px;background:linear-gradient(transparent,#0B0A10 55%)}}
.cover-txt{{position:absolute;left:70px;right:70px;bottom:90px}}
.pill{{display:inline-block;border:2px solid #ffffff90;border-radius:999px;padding:8px 22px;font-size:24px;font-weight:700;letter-spacing:1px;color:#ffffffd0}}
.cover-title{{font-size:92px;font-weight:900;line-height:1.16;letter-spacing:-3px;margin-top:26px}}
.cover-title em{{font-style:normal;color:{acc}}}
.cover-sub{{font-size:32px;color:#ffffffa8;margin-top:22px;font-weight:500}}
.dots{{position:absolute;bottom:40px;left:0;right:0;text-align:center;font-size:22px;color:#ffffff70;letter-spacing:6px}}
/* 본문 */
.card{{position:absolute;top:34px;left:34px;right:34px;height:700px;border-radius:40px;background:linear-gradient(160deg,#FBFAFF,#EEEAF8);
  display:flex;align-items:center;justify-content:center;overflow:hidden;color:#111}}
.card .vis{{margin:0;transform:scale(1.18)}}
.card .vis-chat,.card .vis-checks{{transform:none;width:86%}}
.cover-art .vis-chat,.cover-art .vis-checks{{width:80%;transform:rotate(-4deg)}}
.cover-art .vis-path{{max-width:900px;transform:rotate(-4deg)}}
.cover-art .vis-beforeafter{{transform:rotate(-4deg) scale(1.05)}}
.card .big-keys{{display:flex;gap:22px;align-items:center}}
.card .big-keys .key{{background:#fff;color:#1F1235;border:3px solid #CFC6E6;border-bottom-width:12px;border-radius:26px;padding:26px 44px;font-size:72px;font-weight:900;
  font-family:'Consolas','DejaVu Sans Mono',{font}}}
.card .big-keys .plus{{font-size:56px;color:{acc};font-weight:900}}
.card .big-icon{{font-size:260px;line-height:1}}
.card .bubble.ai,.card .path .step{{box-shadow:0 6px 18px rgba(0,0,0,.08)}}
.card .check{{background:#fff;color:#111;box-shadow:0 6px 18px rgba(0,0,0,.06)}}
.panel{{position:absolute;left:70px;right:70px;top:780px;bottom:80px}}
.numc{{width:56px;height:56px;border-radius:50%;background:#ffffff1f;display:flex;align-items:center;justify-content:center;font-size:30px;font-weight:800}}
.ph{{font-size:66px;font-weight:900;letter-spacing:-2px;line-height:1.2;margin-top:22px}}
.pb{{font-size:33px;line-height:1.6;color:#D9D6E3;margin-top:22px;font-weight:500}}
.pb b{{color:{acc}}}
.mark{{position:absolute;right:70px;bottom:40px;font-size:22px;font-weight:800;letter-spacing:4px;color:#ffffff80}}
.pg{{position:absolute;left:70px;bottom:40px;font-size:22px;color:#ffffff60}}
/* CTA */
.cta{{position:absolute;inset:0;display:flex;flex-direction:column;justify-content:center;padding:0 80px;background:radial-gradient(100% 70% at 50% 30%,{acc}40,#0B0A10 70%)}}
.cta .t{{font-size:78px;font-weight:900;line-height:1.25;letter-spacing:-2px}}
.cta .kw{{display:inline-block;margin-top:46px;background:{acc};color:#0B0A10;border-radius:22px;padding:26px 40px;font-size:44px;font-weight:900}}
.cta .s{{font-size:32px;color:#ffffffb0;margin-top:30px;line-height:1.5}}
.cta .h{{font-size:40px;font-weight:900;color:{acc};margin-top:60px}}
"""


def mag_page(t, acc, inner):
    extra = MAG_CSS.format(acc=t["accent"], font=FONT).replace("{{", "{").replace("}}", "}")
    return f"""<!DOCTYPE html><html><head><meta charset="utf-8">
<link href="https://cdn.jsdelivr.net/gh/orioncactus/pretendard/dist/web/static/pretendard.css" rel="stylesheet">
<style>{css(t)}{extra}</style></head><body><div class="mag">{inner}</div></body></html>"""


def mag_slides(c, acc):
    t = acc["theme"]
    brand = esc(acc.get("brand", acc["name"]))
    n = len(c["slides"]) + 2
    out = []
    cv = c["cover"]
    art_v = cv.get("visual") or next((s["visual"] for s in c["slides"] if s.get("visual")), None)
    art = visual_html(art_v) if art_v else f'<div class="big-icon" style="font-size:300px">{esc(cv.get("icon", "⌨️"))}</div>'
    out.append(mag_page(t, acc, f"""<div class="cover-bg"></div><div class="brand">{brand}</div>
<div class="cover-art">{art}</div><div class="cover-fade"></div>
<div class="cover-txt"><span class="pill">{esc(cv.get('kicker',''))}</span>
<div class="cover-title">{emph(cv['title'])}</div><div class="cover-sub">{esc(cv.get('subtitle',''))}</div></div>
<div class="dots">● ○ ○ ○ ○</div>"""))
    for i, s in enumerate(c["slides"], 1):
        if s.get("visual"):
            top = visual_html(s["visual"])
        elif s.get("keys"):
            top = '<div class="big-keys">' + '<span class="plus">+</span>'.join(
                f'<span class="key">{esc(k)}</span>' for k in s["keys"]) + "</div>"
        else:
            top = f'<div class="big-icon">{esc(s.get("icon", "💡"))}</div>'
        tip = f'<br><b>TIP</b> {esc(s["tip"])}' if s.get("tip") else ""
        out.append(mag_page(t, acc, f"""<div class="card">{top}</div>
<div class="panel"><div class="numc">{i}</div><div class="ph">{esc(s['heading'])}</div>
<div class="pb">{esc(s['body'])}{tip}</div></div>
<div class="pg">{i + 1}/{n}</div><div class="mark">{brand}</div>"""))
    kw = c.get("dm_keyword")
    kw_html = (f'<div class="kw">댓글에 “{esc(kw)}” 남기기</div><div class="s">{esc(c.get("dm_offer", "자료를 DM으로 보내드려요"))}</div>'
               if kw else f'<div class="kw">댓글 아무거나 남기기 💬</div><div class="s">{esc(c.get("dm_offer", "복사해서 바로 쓰는 정리본을 DM으로 보내드려요"))}</div>')
    cta_t = esc(c.get("cta_title", "저장해두고\n필요할 때 꺼내 쓰세요"))
    out.append(mag_page(t, acc, f"""<div class="cta"><div class="t">{cta_t}</div>
{kw_html}<div class="h">{esc(acc['handle'])}</div></div>"""))
    return out


def slides_html(c, acc):
    if acc["theme"].get("layout") == "magazine":
        return mag_slides(c, acc)
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
        vis = visual_html(s.get("visual"))
        cls = "pad mid has-vis" if vis else "pad mid"
        out.append(page(t, f"""<div class="{cls}">
<div class="num">{i:02d}</div><div class="heading">{esc(s['heading'])}</div>
{keys}{vis}<div class="body">{esc(s['body'])}</div>{tip}</div>""", i + 1, n, acc))
    out.append(page(t, f"""<div class="pad mid">
<div class="cta-title">{esc(acc['cta'])}</div>
<div class="cta-row"><div class="chip"><span>🔖</span>저장</div><div class="chip"><span>📤</span>공유</div>
<div class="chip"><span>➕</span>팔로우</div></div>
<div class="handle">{esc(acc['handle'])}</div></div>""", n, n, acc))
    return out


DM_CTA = ("💬 댓글 아무거나 남기면 오늘 내용 정리본(복사해서 바로 쓰는 버전)을 DM으로 보내드려요!\n"
          "※ 팔로워분들께만 보내드려요")


def with_dm_cta(text):
    """캡션 첫 줄(정리본 주소 계산에 쓰임)은 그대로 두고, 바로 아래에 댓글→DM 안내를 넣음 (접힘 전에 보이게)"""
    lines = text.strip().split("\n")
    return lines[0] + "\n\n" + DM_CTA + ("\n\n" + "\n".join(lines[1:]).strip() if len(lines) > 1 else "")


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
        over = pg.evaluate("""() => [...document.querySelectorAll('.pad, .panel, .card, .cover-txt, .cover-art')].some(p => {
            const r = p.getBoundingClientRect();
            return [...p.querySelectorAll('*')].some(k => { const b = k.getBoundingClientRect();
                return b.width && (b.bottom > r.bottom + 2 || b.right > r.right + 2 || b.left < r.left - 2 || b.top < r.top - 2); }); })""")
        if over:
            print(f"  ⚠️ {json_path.name} {i}번 슬라이드 내용이 넘침")
        f = out_dir / f"{i:02d}.jpg"
        pg.screenshot(path=str(f), type="jpeg", quality=92)
        files.append(f)
    pg.close()
    caption = with_dm_cta(c["caption"]) + "\n\n" + " ".join("#" + h.lstrip("#") for h in c.get("hashtags", []))
    pages.build(c, acc)  # 정리본 페이지 p/<slug>/index.html (DM으로 보낼 링크)
    (out_dir / "caption.txt").write_text(caption, encoding="utf-8")
    print(f"렌더: {out_dir} ({len(files)}장)")
    return out_dir


if __name__ == "__main__":
    with sync_playwright() as p:
        b = p.chromium.launch()
        for path in sys.argv[1:]:
            render(path, b)
        b.close()
