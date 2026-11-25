# 인스타 캐러셀 자동화 (4계정 A/B 테스트)

계정 4개(work / cad / guitar / meat)를 동시에 굴려 보고, **저장+공유율**이 가장 높은 계정에 집중하는 구조입니다.

```
topics/<계정>.txt  →  generate.py (Claude API)  →  content/<계정>/*.json
                   →  render.py (Playwright)    →  output/<계정>/<게시물>/01~NN.jpg + caption.txt
                   →  publish.py (Instagram API) →  posted.jsonl
                   →  metrics.py                 →  metrics.csv + 계정 순위
```

## 1. 설치
```bash
pip install -r requirements.txt
playwright install chromium
copy .env.example .env   # 값 채우기
```

## 2. 바로 해보기 (API 키만 있으면 됨)
```bash
python generate.py work --topic "엑셀 단축키 7개"
python render.py content/work/*.json
```
`output/`에 1080x1350 JPG가 생깁니다. 샘플 4세트는 이미 `output/*/20261125_sample/`에 들어 있습니다.

## 3. 계정 준비 (계정마다 1번)
1. 인스타 계정 4개 만들기 → 설정에서 **프로페셔널(크리에이터) 계정**으로 전환
2. developers.facebook.com → 앱 만들기 → **Instagram API with Instagram Login** 추가
3. 4개 계정을 앱 테스터로 추가하고 로그인 → 장기 액세스 토큰 + user id 발급 → `.env`에 입력
   - 장기 토큰은 60일마다 갱신 필요
4. 이미지 호스팅: **공개** GitHub 저장소 하나 만들어 clone → `IMAGE_REPO_DIR`, `IMAGE_BASE_URL` 설정
   (Instagram API는 공개 URL의 JPEG만 받음)

## 4. 매일 돌리기
```bash
python run_daily.py            # 생성+렌더만 → 눈으로 검수 후
python publish.py output/work/<폴더>
python run_daily.py --publish  # 익숙해지면 완전 자동
```
Windows 작업 스케줄러에 `run_daily.py` 등록 (계정당 하루 1개 권장, 저녁 7~9시).

## 5. 어느 계정을 밀지 판단
2~3주(계정당 15~20개) 올린 뒤:
```bash
python metrics.py
```
- **저장+공유율**(도달 대비) 1순위 지표, 팔로워 증가 2순위
- 하위 2개는 중단, 상위 계정에 주제·빈도 집중

## 주의
- 같은 기기·IP에서 새 계정 여러 개를 동시에 만들면 인증 요구나 제한이 걸릴 수 있으니, 계정 생성은 며칠 간격으로
- 완전 양산형으로 보이면 추천 노출이 줄어듭니다. 초반엔 문안을 직접 검수하고, 내 경험·사례를 한 줄씩 넣는 게 좋습니다
- 디자인 수정: `accounts.yaml`의 theme 색상, `render.py`의 CSS

## GitHub Actions로 완전 자동 (PC 꺼져 있어도 됨)
1. 이 폴더를 **공개** GitHub 저장소로 push (저장소 자체가 이미지 호스팅 역할)
2. Settings → Secrets and variables → Actions 에 등록:
   `ANTHROPIC_API_KEY`, `IG_WORK_USER_ID`, `IG_WORK_TOKEN`
3. Actions 탭 → daily-carousel → Run workflow (publish 체크 해제) 로 테스트 → artifact에서 이미지 확인
4. 매일 19:17(KST)에 자동 생성+게시. 처음엔 schedule을 꺼두고 수동 실행 추천
- 인스타 장기 토큰은 60일마다 갱신해서 Secret 업데이트 필요
- 공개 저장소라 .env는 절대 올리지 말 것 (.gitignore 포함됨)
