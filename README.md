# StatsBomb 축구 전술 분석 웹 서비스

StatsBomb Open Data를 기반으로 경기별 팀 전술 기조와 하이라이트 장면의 선수 움직임을 바둑판(그리드) 형태로 렌더링하는 인터랙티브 웹 서비스입니다.

## 주요 기능

- **경기 전술 기조 요약**: 포메이션(소유/비소유 평균 위치), 구역 점유율 히트맵, 패스 네트워크, 선수 이동 벡터, 빌드업 방향, 압박 지수(PPDA), 전환(트랜지션) 속도
- **하이라이트 자동 추출**: 골·페널티 + xG ≥ 0.25 슈팅을 포제션 기반 클립 윈도우로 자동 선정
- **바둑판 렌더링**: 120×80 좌표를 그리드로 나눈 피치 위에 선수 토큰·이동 벡터·점유 히트맵을 표시
- **움직임 예측(360 전용)**: 현재 속도 기반 +2초 단기 외삽을 고스트 토큰(점선)으로 표시
- **인터랙티브 재생**: 하이라이트 프레임 재생/일시정지, 속도 조절, 타임라인 스크러버, 프레임 스텝

## 기술 스택

| 영역 | 스택 |
| --- | --- |
| 백엔드 | Python 3.13, FastAPI, pandas, numpy, SQLite, httpx |
| 프론트엔드 | React 18, TypeScript, Vite, Tailwind CSS, D3 (SVG) |
| 인프라 | Docker Compose (backend :8000, frontend :3000) |

## 시작하기

### 1. Docker Compose로 실행

```bash
docker compose up --build -d
```

프론트엔드: http://localhost:3000
백엔드 API: http://localhost:8000/docs

### 2. 데이터 수집(fetch)

가장 최근 대회 중 **360 데이터를 보유한 대회**를 자동 감지해 경기 데이터를 다운로드합니다.

```bash
# 최신 360 보유 대회 자동 선택
docker compose run --rm backend python -m app.cli fetch

# 특정 대회 고정
COMPETITION_ID=55 SEASON_ID=282 docker compose run --rm backend python -m app.cli fetch
```

### 3. 데이터 가공(process)

```bash
docker compose run --rm backend python -m app.cli process
# 재처리
docker compose run --rm backend python -m app.cli process --force
```

### 로컬 개발 모드

```bash
# 백엔드
cd backend
python -m venv .venv && .venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000

# 프론트엔드 (별도 터미널)
cd frontend
npm install
npm run dev   # http://localhost:3000, /api는 8000으로 프록시
```

## CLI 상세

```bash
python -m app.cli fetch --help
python -m app.cli process --help
```

- `fetch`: `competitions.json`에서 후보 대회를 스캔 → GitHub API로 `three-sixty/` 디렉토리 존재 여부 확인 → 최소 매치 수(`MIN_MATCHES`, 기본 30)를 충족하는 360 보유 최신 대회 우선 선택. 다운로드는 경기 단위 최대 3회 재시도 후 건너뜁니다.
- `process`: 경기 단위 멱등 처리(완료분 스킵, `--force`로 재처리). 원본 JSON은 `data/raw/`, 가공 결과는 `data/db.sqlite`에 저장됩니다.

## API

| 엔드포인트 | 설명 |
| --- | --- |
| `GET /api/competitions` | 처리된 대회 목록 |
| `GET /api/competitions/{id}/matches` | 대회별 경기 목록 |
| `GET /api/matches/{id}/summary` | 경기 전술 기조 요약 (팀별 지표) |
| `GET /api/matches/{id}/highlights` | 자동 추출된 하이라이트 목록 |
| `GET /api/highlights/{id}/frames` | 하이라이트 재생 프레임 (선수 위치·속도·예측 앵커) |

## 데이터 구조 요약

- 좌표계: 120×80 (x: 0~120, y: 0~80), 골은 x=0/x=120
- 이벤트: `type`(pass, shot, carry, pressure, ball_recovery 등), `possession`(포제션 그룹), `minute/second`, `shot.statsbomb_xg`, `play_pattern`
- 360 프리즈프레임(`three-sixty/`): 일부 이벤트에 전 선수 위치 포함 — 경기별 `has_360`으로 애니메이션 충실도가 달라집니다

## 테스트

```bash
# 백엔드 (오프라인, 합성 픽스처 사용)
cd backend && python -m pytest

# 프론트엔드
cd frontend && npm test
```

## 출처 및 라이선스

- 데이터: [StatsBomb Open Data](https://github.com/statsbomb/open-data) — [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) 라이선스로 제공되며, 본 프로젝트에서 데이터를 사용할 때는 위 출처를 표시해야 합니다.
- 본 프로젝트는 StatsBomb의 공식 제품이 아니며 StatsBomb와 제휴 관계가 없습니다.

## 프로젝트 구조

```
backend/    FastAPI 백엔드 (CLI 수집/가공, 분석 엔진, API)
frontend/   React + Vite 프론트엔드 (바둑판 렌더링, 하이라이트 재생)
data/       원본 JSON 캐시(data/raw) + SQLite(data/db.sqlite) — git 미추적
```

## 로드맵 (v2)

- 전체 경기 연속 재생, 팀 간 비교 분석, 상황 기반 기대 위치(ML), 다중 대회 동시 처리