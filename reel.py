"""캐러셀 슬라이드(JPG) → 릴스용 세로 영상(1080x1920 MP4).

  python reel.py output/work/002_xlookup      # → output/work/002_xlookup/reel.mp4

- 슬라이드를 세로 화면 가운데에 놓고 위아래는 배경색으로 채움
- 표지 2.5초, 나머지 3.5초씩 (읽을 시간)
- 무음 오디오 트랙 포함 (인스타 업로드 호환용)
"""
import subprocess, sys
from pathlib import Path

import yaml

ROOT = Path(__file__).parent
COVER_SEC, SLIDE_SEC = 2.5, 3.5


def make_reel(folder):
    folder = Path(folder)
    key = folder.parent.name
    bg = yaml.safe_load((ROOT / "accounts.yaml").read_text(encoding="utf-8"))["accounts"][key]["theme"]["bg"]
    imgs = sorted(folder.glob("[0-9][0-9].jpg"))
    lst = folder / "reel_list.txt"
    lines = []
    for i, f in enumerate(imgs):
        lines += [f"file '{f.resolve().as_posix()}'", f"duration {COVER_SEC if i == 0 else SLIDE_SEC}"]
    lines.append(f"file '{imgs[-1].resolve().as_posix()}'")  # concat 마지막 프레임 유지용
    lst.write_text("\n".join(lines) + "\n", encoding="utf-8")
    out = folder / "reel.mp4"
    vf = (f"scale=1080:1350,pad=1080:1920:0:285:color={bg.lstrip('#')},"
          "format=yuv420p,fps=30")
    subprocess.run([
        "ffmpeg", "-y", "-loglevel", "error",
        "-f", "concat", "-safe", "0", "-i", str(lst),
        "-f", "lavfi", "-i", "anullsrc=channel_layout=stereo:sample_rate=44100",
        "-vf", vf, "-c:v", "libx264", "-preset", "medium", "-crf", "20",
        "-c:a", "aac", "-b:a", "128k", "-shortest", "-movflags", "+faststart",
        str(out)], check=True)
    lst.unlink()
    print("릴스:", out)
    return out


if __name__ == "__main__":
    for d in sys.argv[1:]:
        make_reel(d)
