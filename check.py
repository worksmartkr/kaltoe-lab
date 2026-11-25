"""인스타 연결 확인: 토큰과 계정 ID가 맞는지, 게시 권한이 있는지 점검 (게시는 안 함)."""
import os, sys
import requests
from dotenv import load_dotenv
load_dotenv()
API = os.getenv("IG_API_BASE", "https://graph.facebook.com/v25.0")
uid, tok = os.getenv("IG_WORK_USER_ID"), os.getenv("IG_WORK_TOKEN")
if not (uid and tok):
    sys.exit("IG_WORK_USER_ID / IG_WORK_TOKEN 없음")
r = requests.get(f"{API}/{uid}", params={"fields": "username,name,followers_count,media_count", "access_token": tok}, timeout=30)
print("계정:", r.status_code, r.json())
r2 = requests.get(f"{API}/{uid}/content_publishing_limit", params={"fields": "quota_usage,config", "access_token": tok}, timeout=30)
print("게시 한도:", r2.status_code, r2.json())
if not r.ok:
    sys.exit(1)
