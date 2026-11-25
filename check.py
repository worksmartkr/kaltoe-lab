"""인스타 연결 확인: 토큰 종류, 계정 ID, 게시 권한 점검 (게시는 안 함)."""
import os, sys
import requests
from dotenv import load_dotenv
load_dotenv()
uid, tok = os.getenv("IG_WORK_USER_ID"), os.getenv("IG_WORK_TOKEN", "").strip()
if not tok:
    sys.exit("IG_WORK_TOKEN 없음")
print("토큰 앞 4글자:", tok[:4], "/ 길이:", len(tok))
ok = False
for host in ["https://graph.instagram.com/v25.0", "https://graph.facebook.com/v25.0"]:
    r = requests.get(f"{host}/me", params={"fields": "user_id,username,id", "access_token": tok}, timeout=30)
    print(host, "/me →", r.status_code, r.json())
    if r.ok:
        me = r.json()
        for cand in [uid, me.get("user_id"), me.get("id")]:
            if not cand:
                continue
            r2 = requests.get(f"{host}/{cand}/content_publishing_limit",
                              params={"fields": "quota_usage,config", "access_token": tok}, timeout=30)
            print(f"  {cand} 게시 한도 →", r2.status_code, r2.json())
            ok = ok or r2.ok
if not ok:
    sys.exit(1)
