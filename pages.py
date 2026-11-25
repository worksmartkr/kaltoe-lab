"""게시물별 '정리본' 웹페이지 생성 → p/<slug>/index.html (GitHub Pages로 공개)

slug = 캡션 첫 줄의 SHA-1 앞 10자리. DM 서버(dm-worker)가 댓글 달린 게시물의
캡션을 읽어 같은 방식으로 slug를 계산하므로, 따로 매핑 파일이 필요 없음.
"""
import hashlib, html, json, re, sys, unicodedata
from pathlib import Path

ROOT = Path(__file__).parent
PROMPTS_URL = "https://worksmartkr.github.io/kaltoe-lab/prompts/"


def slug_for(caption: str) -> str:
    first = next((l.strip() for l in caption.splitlines() if l.strip()), "")
    first = unicodedata.normalize("NFC", first)
    return hashlib.sha1(first.encode("utf-8")).hexdigest()[:10]


def esc(s):
    return html.escape(str(s or ""))


def plain(s):
    return re.sub(r"\*(.+?)\*", r"\1", str(s or "")).replace("\n", " ").strip()


def copy_block(text, label=""):
    lab = f'<div class="lab">{esc(label)}</div>' if label else ""
    return (f'<div class="code">{lab}<pre>{esc(text)}</pre>'
            f'<button class="cp" onclick="cp(this)">복사</button></div>')


def table(rows, cols=None, hl=(), bad=(), warn=()):
    hl, bad, warn = ({tuple(x) for x in s} for s in (hl, bad, warn))
    out = ['<div class="tw"><table>']
    if cols:
        out.append("<tr><th></th>" + "".join(f"<th>{esc(c)}</th>" for c in cols) + "</tr>")
    for r, row in enumerate(rows):
        cells = []
        for ci, v in enumerate(row):
            cls = "hl" if (r, ci) in hl else "bad" if (r, ci) in bad else "warn" if (r, ci) in warn else ""
            cells.append(f'<td class="{cls}">{esc(v)}</td>')
        out.append(f"<tr><th>{r + 1}</th>{''.join(cells)}</tr>")
    out.append("</table></div>")
    return "".join(out)


def visual(v):
    if not v:
        return ""
    t = v.get("type")
    if t == "code":
        return copy_block(v.get("text", ""), v.get("label", ""))
    if t == "sheet":
        fx = copy_block(v["fx"], "수식") if v.get("fx") else ""
        return fx + table(v.get("rows", []), v.get("cols"), v.get("hl", []), v.get("bad", []), v.get("warn", []))
    if t == "beforeafter":
        side = lambda k, cls: (f'<div class="ba {cls}"><div class="lab">{esc(v[k].get("label", k))}</div>'
                               + table(v[k].get("rows", []), v[k].get("cols"), v[k].get("hl", []), v[k].get("bad", []))
                               + "</div>")
        return f'<div class="bagrid">{side("before", "b")}{side("after", "a")}</div>'
    if t == "chat":
        out = []
        for m in v.get("messages", []):
            if m.get("role") == "me":  # 내가 보낸 말 = 그대로 쓰는 프롬프트 → 복사 버튼
                out.append(copy_block(m.get("text", ""), "프롬프트"))
            else:
                out.append(f'<div class="ai"><span>AI</span>{esc(m.get("text", ""))}</div>')
        return "".join(out)
    if t == "checks":
        return "<ul class='checks'>" + "".join(
            f"<li><b>{esc(i.get('icon', '✅'))}</b>{esc(i.get('text', ''))}</li>" for i in v.get("items", [])) + "</ul>"
    if t == "path":
        return '<div class="path">' + '<i>→</i>'.join(f"<span>{esc(s)}</span>" for s in v.get("steps", [])) + "</div>"
    return ""


CSS = """
*{box-sizing:border-box}body{margin:0;background:#1E1033;color:#FAF5FF;font-family:Pretendard,-apple-system,'Apple SD Gothic Neo','Noto Sans KR',sans-serif;line-height:1.6}
.wrap{max-width:720px;margin:0 auto;padding:28px 18px 60px}
.kick{display:inline-block;background:#A78BFA;color:#1E1033;font-weight:800;font-size:13px;border-radius:99px;padding:4px 12px}
h1{font-size:28px;line-height:1.3;margin:14px 0 6px}.sub{color:#C4B5FD;margin:0 0 22px}
.step{background:#2E1A4D;border-radius:18px;padding:18px;margin:14px 0}
.step h2{font-size:19px;margin:0 0 8px;display:flex;gap:10px;align-items:center}
.n{flex:none;width:28px;height:28px;border-radius:50%;background:#A78BFA;color:#1E1033;font-size:15px;display:grid;place-items:center}
.step p{margin:6px 0;color:#EDE9FE}.tip{background:#1E1033;border-left:4px solid #A78BFA;border-radius:8px;padding:8px 12px;font-size:15px}
.code{position:relative;background:#0B0A10;border-radius:12px;padding:12px 70px 12px 14px;margin:10px 0}
.code pre{margin:0;white-space:pre-wrap;word-break:break-all;font-family:ui-monospace,Menlo,Consolas,monospace;font-size:15px;color:#E9D5FF}
.code .lab,.ba .lab{font-size:12px;color:#A78BFA;font-weight:700;margin-bottom:4px}
.cp{position:absolute;top:10px;right:10px;border:0;border-radius:8px;background:#A78BFA;color:#1E1033;font-weight:800;padding:6px 10px;cursor:pointer}
.tw{overflow-x:auto;margin:10px 0}table{border-collapse:collapse;font-size:14px;background:#fff;color:#111;border-radius:8px;overflow:hidden}
th,td{border:1px solid #ddd;padding:5px 9px;white-space:nowrap}th{background:#F3F4F6;color:#6B7280;font-weight:600}
td.hl{background:#DCFCE7;font-weight:700}td.bad{background:#FEE2E2;color:#B91C1C;font-weight:700}td.warn{background:#FEF9C3}
.bagrid{display:grid;grid-template-columns:1fr 1fr;gap:10px}.ba.b .lab{color:#FCA5A5}.ba.a .lab{color:#86EFAC}
.ai{background:#1E1033;border-radius:12px;padding:10px 12px;margin:8px 0;white-space:pre-wrap}.ai span{font-size:12px;font-weight:800;color:#A78BFA;margin-right:8px}
.checks{list-style:none;padding:0;margin:8px 0}.checks li{padding:4px 0}.checks b{margin-right:8px}
.path{display:flex;flex-wrap:wrap;gap:6px;align-items:center;margin:8px 0}.path span{background:#1E1033;border:1px solid #A78BFA;border-radius:8px;padding:4px 10px}.path i{color:#A78BFA;font-style:normal}
.keys kbd{display:inline-block;background:#FAF5FF;color:#1E1033;border-radius:8px;padding:3px 10px;font-weight:800;box-shadow:0 3px 0 #A78BFA;margin:2px}
.foot{margin-top:28px;text-align:center;color:#C4B5FD}.foot a{color:#FAF5FF}
.btn{display:inline-block;margin-top:10px;background:#A78BFA;color:#1E1033!important;text-decoration:none;font-weight:800;border-radius:12px;padding:12px 18px}
"""


def build(c: dict, acc: dict) -> Path:
    cv = c.get("cover", {})
    title = plain(cv.get("title", c.get("topic", "")))
    slug = slug_for(c["caption"])
    steps = []
    for i, s in enumerate(c.get("slides", []), 1):
        keys = ('<div class="keys">' + " + ".join(f"<kbd>{esc(k)}</kbd>" for k in s["keys"]) + "</div>"
                if s.get("keys") else "")
        tip = f'<p class="tip"><b>TIP</b> {esc(s["tip"])}</p>' if s.get("tip") else ""
        body = "".join(f"<p>{esc(l)}</p>" for l in str(s.get("body", "")).split("\n") if l.strip())
        steps.append(f'<section class="step"><h2><span class="n">{i}</span>{esc(s.get("heading", ""))}</h2>'
                     f'{body}{keys}{visual(s.get("visual"))}{tip}</section>')
    handle = acc.get("handle", "")
    page = f"""<!DOCTYPE html><html lang="ko"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>{esc(title)} | {esc(acc.get('name', ''))}</title>
<meta name="robots" content="noindex"><style>{CSS}</style></head><body><div class="wrap">
<span class="kick">{esc(cv.get('kicker', '정리본'))}</span><h1>{esc(title)}</h1><p class="sub">{esc(plain(cv.get('subtitle', '')))}</p>
{''.join(steps)}
<div class="foot">매일 저녁 7시, 칼퇴 팁 올라가요 🏃<br>
<a class="btn" href="https://www.instagram.com/{esc(handle.lstrip('@'))}/">{esc(handle)} 팔로우</a><br><br>
<a href="{PROMPTS_URL}">보너스: 업무용 AI 프롬프트 30 →</a></div>
</div><script>function cp(b){{navigator.clipboard.writeText(b.parentNode.querySelector('pre').innerText).then(()=>{{b.textContent='복사됨!';setTimeout(()=>b.textContent='복사',1200)}})}}</script>
</body></html>"""
    out = ROOT / "p" / slug / "index.html"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(page, encoding="utf-8")
    return out


if __name__ == "__main__":
    import yaml
    accs = yaml.safe_load((ROOT / "accounts.yaml").read_text(encoding="utf-8"))["accounts"]
    for f in sys.argv[1:]:
        p = Path(f)
        print(build(json.loads(p.read_text(encoding="utf-8")), accs[p.parent.name]))
