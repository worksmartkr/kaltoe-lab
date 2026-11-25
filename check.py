"""인스타 연결 확인: 토큰 종류, 계정 ID, 게시 권한 점검 (게시는 안 함)."""
import os, sys
import requests
from dotenv import load_dotenv
load_dotenv()
uid, tok = os.getenv("IG_WORK_USER_ID", "").strip(), os.getenv("IG_WORK_TOKEN", "").strip()
if not tok:
    sys.exit("IG_WORK_TOKEN 없음")
print("토큰 앞 4글자:", tok[:4], "/ 길이:", len(tok))
host = "https://graph.instagram.com/v25.0" if tok.startswith("IG") else "https://graph.facebook.com/v25.0"
get = lambda path, **p: requests.get(f"{host}/{path}", params={**p, "access_token": tok}, timeout=30)
r = get("me", fields="id,name")
print("토큰 주인 →", r.status_code, r.json())
cands = [uid] if uid else []
if not tok.startswith("IG"):  # 페이스북 로그인 토큰: 연결된 인스타 비즈니스 계정 찾기
    a = get("me/accounts", fields="name,instagram_business_account")
    print("연결된 페이지 →", a.status_code, a.json())
    for pg in a.json().get("data", []):
        if pg.get("instagram_business_account"):
            cands.append(pg["instagram_business_account"]["id"])
    # 댓글→DM 웹훅이 오도록 페이지를 앱에 구독 (여러 번 해도 안전)
    a2 = get("me/accounts", fields="id,name,access_token")
    for pg in a2.json().get("data", []):
        ptok = pg.get("access_token") or tok
        s = requests.post(f"{host}/{pg['id']}/subscribed_apps",
                          params={"subscribed_fields": "feed,messages", "access_token": ptok}, timeout=30)
        print(f"페이지 {pg.get('name')} 웹훅 구독 →", s.status_code, s.json())
        g = requests.get(f"{host}/{pg['id']}/subscribed_apps", params={"access_token": ptok}, timeout=30)
        print("  현재 구독 →", g.status_code, g.json())
ok = False
for cand in dict.fromkeys(cands):
    r1 = get(cand, fields="username,followers_count,media_count")
    r2 = get(f"{cand}/content_publishing_limit", fields="quota_usage,config")
    print(f"인스타 {cand} →", r1.status_code, r1.json())
    print(f"  게시 한도 →", r2.status_code, r2.json())
    ok = ok or (r1.ok and r2.ok)
    if r1.ok:  # 댓글→DM 웹훅: 인스타 계정을 앱에 구독
        s = requests.post(f"{host}/{cand}/subscribed_apps",
                          params={"subscribed_fields": "comments,messages", "access_token": tok}, timeout=30)
        print("  인스타 웹훅 구독 →", s.status_code, s.json())
        g = get(f"{cand}/subscribed_apps")
        print("  현재 구독 →", g.status_code, g.json())
if not ok:
    sys.exit(1)
print("✅ 연결 OK")
