"""렌더된 캐러셀을 Instagram에 게시 (Instagram API with Instagram Login).

Instagram API는 이미지를 '공개 URL'로만 받습니다. 그래서:
  1) 이미지를 공개 저장소에 올리고 (기본: 공개 GitHub 저장소 → raw URL)
  2) 각 URL로 캐러셀 아이템 컨테이너 생성
  3) CAROUSEL 컨테이너 생성 → media_publish

사용:
  python publish.py output/work/20261125_엑셀-단축키
  python publish.py output/work/20261125_엑셀-단축키 --dry-run

.env:
  IG_WORK_USER_ID=...   IG_WORK_TOKEN=...      (계정 키 대문자)
  IMAGE_REPO_DIR=C:/path/to/public-image-repo  (로컬 clone 경로)
  IMAGE_BASE_URL=https://raw.githubusercontent.com/<user>/<repo>/main
"""
import argparse, json, os, shutil, subprocess, sys, time
from pathlib import Path

import requests
from dotenv import load_dotenv

ROOT = Path(__file__).parent
load_dotenv(ROOT / ".env")
_TOK = os.getenv("IG_WORK_TOKEN", "")
# IGAA… 로 시작하면 인스타 로그인 토큰 → graph.instagram.com, 아니면 페이스북 로그인 토큰 → graph.facebook.com
API = os.getenv("IG_API_BASE") or ("https://graph.instagram.com/v25.0" if _TOK.startswith("IG")
                                   else "https://graph.facebook.com/v25.0")


def creds(key):
    uid, tok = os.getenv(f"IG_{key.upper()}_USER_ID"), os.getenv(f"IG_{key.upper()}_TOKEN")
    if not (uid and tok):
        sys.exit(f".env에 IG_{key.upper()}_USER_ID / IG_{key.upper()}_TOKEN 설정 필요")
    return uid, tok


def host_images(folder: Path, key: str):
    repo = Path(os.environ["IMAGE_REPO_DIR"])
    base = os.environ["IMAGE_BASE_URL"].rstrip("/")
    rel = Path("images") / key / folder.name
    dst = repo / rel
    dst.mkdir(parents=True, exist_ok=True)
    imgs = sorted(folder.glob("*.jpg"))
    for f in imgs + list(folder.glob("reel.mp4")):
        shutil.copy2(f, dst / f.name)
    subprocess.run(["git", "-C", str(repo), "add", "."], check=True)
    subprocess.run(["git", "-C", str(repo), "commit", "-m", f"add {rel.as_posix()}"], check=False)
    subprocess.run(["git", "-C", str(repo), "push"], check=True)
    gh_tok, gh_repo = os.getenv("GITHUB_TOKEN"), os.getenv("GITHUB_REPOSITORY")
    if gh_tok and gh_repo:  # GitHub Pages 재배포 요청 (봇 push는 자동 배포가 안 될 수 있음)
        r = requests.post(f"https://api.github.com/repos/{gh_repo}/pages/builds",
                          headers={"Authorization": f"Bearer {gh_tok}", "Accept": "application/vnd.github+json"}, timeout=30)
        print("Pages 빌드 요청:", r.status_code)
    urls = [f"{base}/{rel.as_posix()}/{f.name}" for f in imgs]
    if (folder / "reel.mp4").exists():
        urls.append(f"{base}/{rel.as_posix()}/reel.mp4")
    for u in urls:  # GitHub Pages 배포 대기 (보통 1~2분)
        for _ in range(100):
            if requests.head(u, timeout=10).status_code == 200:
                break
            time.sleep(3)
    return urls


def post(path, tok, **data):
    r = requests.post(f"{API}/{path}", data={**data, "access_token": tok}, timeout=60)
    if not r.ok:
        sys.exit(f"API 오류 {r.status_code}: {r.text}")
    return r.json()


def wait_ready(cid, tok, tries=30):
    for _ in range(tries):
        r = requests.get(f"{API}/{cid}", params={"fields": "status_code", "access_token": tok}, timeout=30).json()
        if r.get("status_code") == "FINISHED":
            return
        if r.get("status_code") == "ERROR":
            sys.exit(f"컨테이너 오류: {r}")
        time.sleep(3)


def publish_reel_only(folder):
    """이미 캐러셀을 올린 게시물의 릴스만 따로 올릴 때"""
    folder = Path(folder)
    key = folder.parent.name
    caption = (folder / "caption.txt").read_text(encoding="utf-8")
    uid, tok = creds(key)
    urls = host_images(folder, key)
    if not urls[-1].endswith(".mp4"):
        sys.exit("reel.mp4 없음 — 먼저 python reel.py 실행")
    publish_reel(uid, tok, key, folder.name, urls[-1], caption)


def publish(folder, dry=False):
    folder = Path(folder)
    key = folder.parent.name
    imgs = sorted(folder.glob("*.jpg"))
    if not 2 <= len(imgs) <= 10:
        sys.exit(f"캐러셀은 2~10장이어야 해요 (현재 {len(imgs)}장)")
    caption = (folder / "caption.txt").read_text(encoding="utf-8")
    if dry:
        print(f"[dry-run] {key}: {len(imgs)}장\n{caption}")
        return
    uid, tok = creds(key)
    urls = host_images(folder, key)
    reel_url = urls.pop() if urls[-1].endswith(".mp4") else None
    children = []
    for u in urls:
        c = post(f"{uid}/media", tok, image_url=u, is_carousel_item="true")["id"]
        wait_ready(c, tok)
        children.append(c)
    car = post(f"{uid}/media", tok, media_type="CAROUSEL", children=",".join(children), caption=caption)["id"]
    wait_ready(car, tok)
    media_id = post(f"{uid}/media_publish", tok, creation_id=car)["id"]
    log_post(key, folder.name, media_id, "carousel")
    print(f"게시 완료: {key} media_id={media_id}")
    if reel_url:
        try:
            publish_reel(uid, tok, key, folder.name, reel_url, caption)
        except SystemExit as e:  # 릴스 실패해도 캐러셀은 이미 올라감
            print(f"릴스 실패(캐러셀은 게시됨): {e}")


def publish_reel(uid, tok, key, name, video_url, caption):
    # share_to_feed=false → 프로필 그리드엔 캐러셀만, 릴스 탭·추천에 릴스 노출
    rid = post(f"{uid}/media", tok, media_type="REELS", video_url=video_url,
               caption=caption, share_to_feed="false")["id"]
    wait_ready(rid, tok, tries=100)  # 영상 처리 최대 약 5분
    media_id = post(f"{uid}/media_publish", tok, creation_id=rid)["id"]
    log_post(key, name, media_id, "reel")
    print(f"릴스 게시 완료: {key} media_id={media_id}")


def log_post(key, name, media_id, kind):
    with (ROOT / "posted.jsonl").open("a", encoding="utf-8") as f:
        f.write(json.dumps({"account": key, "folder": name, "media_id": media_id, "type": kind,
                            "posted_at": time.strftime("%Y-%m-%d %H:%M")}, ensure_ascii=False) + "\n")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("folder")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--reel-only", action="store_true")
    a = ap.parse_args()
    publish_reel_only(a.folder) if a.reel_only else publish(a.folder, a.dry_run)
