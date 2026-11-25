"""저작권 걱정 없는 배경음악 직접 생성 (로파이 느낌 코드 + 잔잔한 비트).

  python music.py out.wav 30     # 30초짜리 생성

외부 음원을 쓰지 않고 코드로 합성하므로 저작권 문제가 없음.
seed를 바꾸면 코드 진행·리듬이 조금씩 달라져 게시물마다 다른 느낌을 줄 수 있음.
"""
import sys, wave
import numpy as np

SR = 44100
BPM = 84
PROGS = [  # (근음 MIDI, 코드 구성음 반음 간격)
    [(48, [0, 4, 7, 11]), (45, [0, 3, 7, 10]), (41, [0, 4, 7, 11]), (43, [0, 4, 7, 10])],   # Cmaj7 Am7 Fmaj7 G7
    [(41, [0, 4, 7, 11]), (43, [0, 4, 7, 10]), (40, [0, 3, 7, 10]), (45, [0, 3, 7, 10])],   # Fmaj7 G7 Em7 Am7
    [(45, [0, 3, 7, 10]), (41, [0, 4, 7, 11]), (48, [0, 4, 7, 11]), (43, [0, 4, 7, 10])],   # Am7 Fmaj7 Cmaj7 G7
]


def hz(m):
    return 440.0 * 2 ** ((m - 69) / 12)


def env(n, a=0.02, r=0.3):
    e = np.ones(n)
    na, nr = int(a * SR), int(r * SR)
    e[:na] = np.linspace(0, 1, na)
    e[-nr:] *= np.linspace(1, 0, nr)
    return e


def pad(m, dur):
    n = int(dur * SR)
    t = np.arange(n) / SR
    f = hz(m)
    w = 0.6 * np.sin(2 * np.pi * f * t) + 0.25 * np.sin(2 * np.pi * 2 * f * t) + 0.1 * np.sin(2 * np.pi * 3 * f * t)
    w *= 1 + 0.003 * np.sin(2 * np.pi * 5 * t)  # 살짝 흔들림
    return w * env(n, 0.15, 0.6)


def kick():
    n = int(0.25 * SR)
    t = np.arange(n) / SR
    f = 110 * np.exp(-t * 18) + 45
    return np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 9)


def hat(rng):
    n = int(0.06 * SR)
    return rng.standard_normal(n) * np.exp(-np.arange(n) / SR * 70) * 0.25


def add(buf, start, w):
    start = max(0, int(start))
    end = min(len(buf), start + len(w))
    if end > start:
        buf[start:end] += w[:end - start]


def make(seconds=30, seed=0):
    rng = np.random.default_rng(seed)
    prog = PROGS[seed % len(PROGS)]
    beat = 60 / BPM
    bar = beat * 4
    total = int(seconds * SR)
    mix = np.zeros(total + SR * 2)
    t0, i = 0.0, 0
    while t0 < seconds:
        root, iv = prog[i % 4]
        for k, s in enumerate(iv):  # 코드 패드
            w = pad(root + 12 + s, bar + 0.4) * (0.10 if k else 0.12)
            add(mix, t0 * SR, w)
        bw = pad(root, bar) * 0.18  # 베이스
        add(mix, t0 * SR, bw)
        for b in range(4):  # 비트: 킥 1·3박, 하이햇 8분음표
            tb = t0 + b * beat
            if b in (0, 2) or (b == 3 and rng.random() < 0.3):
                k = kick() * 0.5
                add(mix, tb * SR, k)
            for h in (0, 0.5):
                hh = hat(rng) * (1 if h else 0.6)
                add(mix, (tb + h * beat + rng.normal(0, 0.006)) * SR, hh)
        for _ in range(2):  # 멜로디 몇 음 (코드톤 위주)
            tm = t0 + rng.integers(0, 8) * beat / 2
            m = root + 24 + iv[rng.integers(0, len(iv))]
            w = pad(m, beat * 0.9) * 0.08
            add(mix, tm * SR, w)
        t0 += bar
        i += 1
    mix = mix[:total]
    # 로우패스 느낌(단순 이동평균) + 페이드
    mix = np.convolve(mix, np.ones(6) / 6, mode="same")
    fade = int(1.5 * SR)
    mix[:fade] *= np.linspace(0, 1, fade)
    mix[-fade:] *= np.linspace(1, 0, fade)
    mix /= np.max(np.abs(mix)) + 1e-9
    return (mix * 0.8 * 32767).astype(np.int16)


def save(path, seconds=30, seed=0):
    d = make(seconds, seed)
    st = np.repeat(d[:, None], 2, axis=1)
    with wave.open(str(path), "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(st.tobytes())
    return path


if __name__ == "__main__":
    save(sys.argv[1], float(sys.argv[2]) if len(sys.argv) > 2 else 30)
