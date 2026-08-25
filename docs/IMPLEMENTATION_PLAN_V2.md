# StatsBomb 기반 축구 전술 분석 웹 서비스 — 통합 구현 명세서
(구현 계획 v2 + 코드베이스 감사 및 개선안)

---

## 📋 목차
1. [Part 1. 원본 구현 계획 (v2, 리뷰 반영)](#part-1-원본-구현-계획-v2-리뷰-반영)
2. [Part 2. 코드베이스 감사 결과 및 핵심 개선안](#part-2-코드베이스-감사-결과-및-핵심-개선안)
3. [Part 3. 아키텍처 및 상세 기술 스펙](#part-3-아키텍처-및-상세-기술-스펙)
4. [Part 4. 단계별 실행 체크리스트 (Implementation Checklist)](#part-4-단계별-실행-체크리스트-implementation-checklist)

---

# Part 1. 원본 구현 계획 (v2, 리뷰 반영)

## 1. 요약
StatsBomb Open Data를 수집·가공해 **(1) 경기별 팀 전술 기조 요약**과 **(2) 하이라이트 장면의 선수 움직임을 바둑판(그리드) 형태로 렌더링**하는 인터랙티브 웹 서비스를 구축한다.
초기 범위는 **대회 1개(360 데이터 우선 자동 감지)**, 분석은 **통계·규칙 기반**, 움직임 "예측"은 **묘사 + 단기 외삽(360 전용)**, 배포는 **Docker Compose**로 한다.

## 2. 기반 지식 요약
- **StatsBomb Open Data** (GitHub statsbomb/open-data, **CC BY 4.0 — 출처 표시 의무**):
  - `competitions.json`
  - `matches/{competition_id}/{season_id}.json`
  - `events/{match_id}.json`
  - `lineups/{match_id}.json`
  - `three-sixty/{match_id}.json` (일부 대회 한정)
- **좌표계**: 피치 120×80 (x: 0~120, y: 0~80), 골은 x=0/120. 이벤트는 `x,y`, `possession`(포제션 그룹 id), `minute/second`, `type`, `shot_statsbomb_xg`, `play_pattern`(페널티는 play_pattern=penalty인 슈팅) 필드를 가짐.
- **360 프리즈프레임**: 일부 이벤트 타입(패스·캐리·슈팅 등)에만 존재하며 이벤트 시점의 전 선수 위치를 제공. 없는 이벤트/대회는 공 궤적 + 참여 선수만으로 폴백.
- **스택**: Python (FastAPI + pandas/numpy) 백엔드, React (Vite + TypeScript + Tailwind + D3 SVG) 프론트, SQLite (가공 결과) + 디스크 캐시 (원본 JSON), Docker Compose (backend :8000, frontend :3000). Docker 이미지는 `python:3.13-slim`, 렌더링용 matplotlib는 미사용.

## 3. 구현 상세
### 데이터 파이프라인 (CLI)
- `fetch` 명령: `competitions.json`에서 시즌 시작일 역순으로 후보 대회를 스캔하되 **GitHub API로 `three-sixty/` 디렉토리 존재 여부를 확인**해, **최소 매치 수(≥30, 환경변수 조정 가능)를 충족하는 360 보유 최신 대회를 우선 선택**하고 없으면 최신 대회로 폴백. `COMPETITION_ID`/`SEASON_ID`로 고정 오버라이드 가능.
- 다운로드는 경기 단위로 수행, 실패 시 **최대 3회 재시도(지수 백오프) 후 건너뛰고** 마지막에 성공/실패 요약 출력. 원본 JSON은 `data/raw/`에 캐시.
- `process` 명령: 경기별 **멱등 처리**(완료 상태 저장, 재실행 시 완료분 스킵, `--force`로 재처리). 분석 지표는 `data/db.sqlite`에 저장하고 경기별 `has_360`을 기록.

### 분석 엔진 (경기 전술 기조)
- **포메이션**: 팀별 선수 평균 위치를 소유/비소유 상태로 나눠 산출 (360 프레임 기준, 폴백은 이벤트 참여 위치).
- **구역 점유율**: 기본 **12×8 그리드(10m 셀)** 로 팀별·소유 상태별 셀 점유율 계산 (8×8, 16×12 토글 지원).
- **패스 네트워크**: 선수 노드 + 완료 패스 엣지(두께=횟수, 방향 표시), 상위 15개 엣지 + 전진 진행도(Δx).
- **이동 벡터**: 360 프레임 기준 선수별 속도·방향, 스프린트(>5.5m/s) 횟수, 팀 평균 이동 벡터.
- **확장 지표**: 빌드업 방향(패스/캐리 진행 방향·3분할 진입), 압박 지수(분당 프레셔 수 + PPDA), 전환 속도(공 회수 → 8초 내 슈팅/최종 3분할 진입 횟수·평균 소요 시간).

### 하이라이트 자동 추출 + 프레임
- **대상**: 골(슈팅·페널티·자책골) + **xG ≥ 0.25** 슈팅.
- **윈도우(이벤트 기준)**: 시작 = 하이라이트 이벤트가 속한 **포제션의 첫 이벤트**(상한: 골 30초 전, 슈팅 15초 전), 끝 = **이벤트 이후 다음 이벤트(최대 4초 후)**. 경기 시작/종료로 클램프. 골 직후는 킥오프까지 이벤트가 없어 추가 프레임이 거의 없음을 정상 동작으로 간주.
- **프레임 빌더**: 윈도우 내 각 이벤트를 1프레임으로 생성. 360이면 **프리즈프레임이 있는 이벤트**에 전 선수 위치 + 속도, 없으면 공 궤적 + 참여 선수만. 서버는 원본 프레임만 제공하고, **부드러운 재생을 위한 선형 보간은 프론트에서 수행**.

### 움직임 예측 (단기 외삽, 360 전용)
- 프리즈프레임 위치 시퀀스로 선수별 속도를 계산(잡음 방지 스무딩) 후, 상수속도 모델로 **+2초까지 예상 위치** 산출: 최대속도(관측 최대값, 8m/s 상한) 클램프 → 피치 경계 클램프 → 선수 경기 평균 위치 방향 0.15/s 가중 당김. 결정적·설명 가능.
- 프레임 API에 속도·최대속도만 저장하고 프론트가 외삽해 **고스트 토큰(점선)** 표시. **비360 하이라이트는 고스트 미표시**(참여 선수 이동만 재생).

### 프론트엔드/렌더링 (바둑판)
- 경기 선택 → **전술 기조 뷰**: 지표 카드(포메이션, 점유율, 패스 네트워크, 이동 벡터, 빌드업, 압박, 전환) + 바둑판 보드.
- **하이라이트 뷰**: 장면 목록(팀·유형·분·xG) → 재생기(재생/일시정지, 속도 0.5×/1×/2×, 프레임 스텝, 타임라인 스크러버) + 보드 애니메이션. **하이라이트 0건 경기는 빈 상태 UI** 표시.
- **보드(TacticalBoard)**: D3 SVG, 120×80 → 105×68 표준 피치 스케일, 그리드 셀 = 점유 강도 히트 오버레이(체커보드 틴트), 선수 토큰(번호·팀색), 이동 방향 화살표, 고스트 예상 토큰. 토글: 소유 상태, 그리드 크기, 히트/벡터 표시.

### 인프라/운영
- Docker Compose: `backend`(uvicorn, 8000), `frontend`(nginx 정적 서빙, 3000), `data/` 볼륨 공유. 수집/가공은 `docker compose run --rm backend python -m app.cli fetch|process`로 실행.
- 개발 모드에서 프론트(3000) ↔ 백엔드(8000) 호출을 위한 **CORS 미들웨어**(localhost:3000 허용) 설정.
- **README에 StatsBomb Open Data 출처 및 CC BY 4.0 라이선스 고지** 필수 포함.

## 4. API 계약
- `GET /api/competitions` → 처리된 대회 목록 (대회명, 시즌, 매치 수, `has_360`)
- `GET /api/competitions/{id}/matches` → 매치 목록 (홈/어웨이, 스코어, 날짜, `has_360`, 처리 상태)
- `GET /api/matches/{id}/summary` → 팀별 {formation(소유/비소유 평균 위치), zones(그리드 점유), pass_network(노드·엣지), movement(선수별 속도·스프린트·벡터), buildup, pressure(index·ppda), transitions}
- `GET /api/matches/{id}/highlights` → {id, team, type, minute, xg, window{start_event, end_event}}
- `GET /api/highlights/{id}/frames` → {players[{id,number,name,team}], frames[{event_index, t, ball, players[{id,x,y,vx,vy,max_speed}]}], grid_config}

## 5. 테스트 계획
- **백엔드 (pytest, 오프라인)**: 실 매치 1개를 축소해 `backend/tests/fixtures/`에 커밋 → 클립 윈도우(포제션 경계·상한·이벤트 기준 종료), 그리드 점유 계산, 패스 네트워크 집계, 외삽(경계·최대속도 클램프), API 라우트 스모크 테스트.
- **프론트 (Vitest)**: 120×80 → 그리드 좌표 변환, 프레임 간 선형 보간, 토큰 레이아웃, 컴포넌트 렌더 스모크.
- **통합 검증**: `docker compose up` → `fetch`/`process` 실행 → UI에서 매치·하이라이트 목록 비어 있지 않은지, 하이라이트 재생 시 프레임 진행 및 고스트 표시(360 경기)를 수동 확인.

## 6. 가정 사항
- UI 언어는 **한국어**, 축구 용어는 영어 병기. 인증·사용자 계정 없음 (로컬/데모용).
- 자동 선택된 대회의 360 보유 여부에 따라 애니메이션 충실도가 달라지며, 이는 정상 동작으로 간주.
- 전체 경기 연속 재생, 팀 간 비교 분석, ML 기반 예측은 v2 범위로 남긴다.
- `fetch` 재실행 시 원본이 갱신되면 `--force`로 재처리 가능.

---

# Part 2. 코드베이스 감사 결과 및 핵심 개선안

초기 작성된 코드(`backend/app/analysis/` 등)에서 발견된 주요 도메인/스키마 불일치와 이에 대한 구체적인 개선 가이드입니다.

### 2.1 StatsBomb 360 Open Data 스키마 정합성 (Critical)
* **문제점**:
  - `formation.py`, `zones.py`, `movement.py`는 `ev.get("freeze_frame")`과 `p.get("player", {}).get("id")`를 조회하고 있음.
  - 하지만 StatsBomb 오픈데이터에서 360 파일은 `three-sixty/{match_id}.json`으로 완전히 분리되어 있으며, freeze_frame 내 선수는 **`player_id`가 없는 익명 데이터**(`{"teammate": bool, "actor": bool, "keeper": bool, "location": [x, y]}`)임.
  - 현재 코드는 `pid is None` 조건에 걸려 360 데이터가 전량 누락됨.
* **개선안**:
  1. `events`와 `three-sixty`를 로드할 때 `event["id"] == frame["event_uuid"]` 기준으로 인덱싱하여 매핑.
  2. `zones.py`: 선수 ID 없이 `teammate` 플래그와 해당 이벤트의 팀 ID로 아군/상대팀을 판별해 그리드 카운트에 직접 가산.
  3. `formation.py`: 360 익명 프레임은 팀 전체 무게중심/구역 점유에 활용하고, 선수별 개별 포메이션 위치는 ID가 식별되는 이벤트 참여 위치(Pass/Carry/Tackle/Shot 등)를 기본 축으로 삼아 계산.
  4. `movement.py`: 전체 경기 360 스냅샷 속도 추적은 잡음이 심하므로, **하이라이트 클립 윈도우 내 연속 이벤트 프레임**에서의 속도 추정 및 이벤트 액터(`actor`) 중심 속도/스프린트로 정밀화.

### 2.2 좌표계 정규화 및 `attack_direction` 제거
* **문제점**:
  - `common.py`, `buildup.py`, `transitions.py`에서 샷 위치로 공격 방향(-1 또는 1)을 판별하여 좌표를 곱하고 있음.
  - StatsBomb 이벤트 좌표는 **이미 모든 팀에 대해 x=0 → x=120 (왼쪽에서 오른쪽 공격)으로 정규화**되어 있음.
* **개선안**:
  - 불필요한 `attack_direction` 로직을 제거하고 통일된 x 좌표계(0: 수비골대 ~ 120: 상대골대)로 단일화.
  - 전진 패스/캐리: `end[0] - start[0] >= 임계값`.
  - 3분할 진영: 수비 서드 (`x < 40`), 미들 서드 (`40 <= x < 80`), 공격/파이널 서드 (`x >= 80`).

### 2.3 PPDA 및 경기 시간 산출 보정
* **문제점**:
  - `common.event_time()`의 `(period - 1) * 3600` 오프셋으로 인해 90분 경기의 `duration_min`이 150분으로 계산되어 분당 압박 수가 과소평가됨.
  - PPDA가 전 피치(0~120) 전체 패스/수비액션 비율로 계산되어 전방 압박 강도의 의미가 퇴색됨.
* **개선안**:
  - `duration_min`: 이벤트의 실제 `minute` 최댓값 또는 period별 순수 플레이 타임 합산으로 계산 (약 90~100분).
  - PPDA: **수비팀 기준 상대 진영(StatsBomb 좌표계 `x >= 40`)**에서 발생한 상대 패스 수와 우리 팀의 수비 액션(Pressure, Tackle, Interception, Block, Clearance) 수만 필터링하여 계산.
    $$\text{PPDA} = \frac{\text{Opponent Passes in } x \ge 40}{\text{Defensive Actions in } x \ge 40}$$

### 2.4 포제션 시작 위치(Thirds) 판정 보정
* **문제점**:
  - `buildup.py`에서 `team == team_id` 필터링 상태에서 `seen_possessions`를 기록하여 상대 포제션 중 수비액션이 우리 팀의 포제션 시작으로 오분류됨.
* **개선안**:
  - `ev.get("possession_team", {}).get("id") == team_id`인 이벤트 그룹에 대해서만 포제션의 첫 번째 이벤트 위치(`location`)를 추출하여 수비/미들/파이널 서드 시작 횟수를 집계.

### 2.5 다운로더 및 스토리지 보완
* **문제점**:
  - GitHub Contents API(`downloader.py`) 비인증 호출 시 60회/시간 Rate Limit에 걸려 360 인덱싱이 실패할 수 있음.
  - `storage.py`의 `upsert_competition`에 `match_count` 누락, `list_matches`에 `season_id` 필터 누락.
* **개선안**:
  - `downloader.py`: Contents API 에러 시 graceful fallback 및 로컬 디스크 캐시(`data/raw/`) 우선 조회.
  - `storage.py`: 스키마 바인딩 수정 및 인덱스 보강.

---

# Part 3. 아키텍처 및 상세 기술 스펙

```
┌─────────────────────────────────────────────────────────────┐
│                    Frontend (React 18 + Vite)               │
│  - TacticalBoard (D3 SVG 120x80 Grid / Tokens / Ghosts)    │
│  - MatchView (Tactical Summary: Formation, Zones, Passes)   │
│  - HighlightView (Player Controller + Ghost Extrapolation)  │
└──────────────────────────────┬──────────────────────────────┘
                               │ HTTP (:3000 -> :8000/api)
┌──────────────────────────────▼──────────────────────────────┐
│                    Backend (FastAPI)                        │
│  - main.py: CORS, REST API 5 Routes                         │
│  - highlights.py & frames.py: Clip Window & Frame Builder   │
│  - analysis/*.py: 8 Tactical Engine Modules                 │
│  - storage.py: SQLite (data/db.sqlite)                      │
│  - downloader.py: GitHub StatsBomb Open Data Fetcher        │
│  - cli.py: `fetch` & `process` CLI Commands                 │
└──────────────────────────────┬──────────────────────────────┘
                               │ File System
┌──────────────────────────────▼──────────────────────────────┐
│                    Data Storage Layer                       │
│  - data/raw/{competitions,matches,events,lineups,360}.json   │
│  - data/db.sqlite (Processed Summaries & Frames)             │
└─────────────────────────────────────────────────────────────┘
```

## 3.1 백엔드 모듈 상세 역할
- `app/config.py`: 피치 상수, 윈도우 임계값, 경로 설정.
- `app/downloader.py`: StatsBomb GitHub 원본 데이터 다운로드 및 `data/raw/` 캐시 관리.
- `app/storage.py`: SQLite 테이블 생성 및 멱등 CRUD 처리.
- `app/analysis/`:
  - `common.py`: 공통 헬퍼, 정규화 좌표 유틸리티, 라인업 매핑.
  - `formation.py`: 소유/비소유 상태별 선수 평균 위치.
  - `zones.py`: 12×8 (8×8, 16×12) 그리드 셀 점유 강도.
  - `passes.py`: 패스 네트워크 노드/엣지 및 전진 진행도.
  - `movement.py`: 선수/팀 이동 벡터, 스프린트, 속도 통계.
  - `pressure.py`: 상대 진영(x ≥ 40) PPDA 및 분당 압박 강도.
  - `buildup.py`: 전진 패스/캐리 및 포제션 시작 구역(3분할).
  - `transitions.py`: 공 회수 후 8초 내 슈팅/파이널 서드 진입 트랜지션.
  - `predict.py`: 상수속도 + 앵커 당김 + 경계 클램프 단기 외삽 (+2초).
- `app/highlights.py`: 골, 페널티, xG ≥ 0.25 슈팅 기반 포제션 윈도우 클리핑.
- `app/frames.py`: 하이라이트 재생용 프레임 및 선수 속도/앵커 데이터 빌더.
- `app/processing.py`: 원본 JSON 파싱 → 요약 지표 + 하이라이트 + 프레임 종합 처리 파이프라인.
- `app/cli.py`: `fetch` (360 우선 대회 다운로드), `process` (배치 처리) CLI 진입점.
- `app/main.py`: FastAPI 웹 서버 및 CORS 미들웨어.

## 3.2 핵심 알고리즘 및 상수 규격

### 1) 하이라이트 포제션 윈도우 클리핑
```python
# 골: 해당 포제션 시작 이벤트부터 (상한: 골 발생 30초 전)
# 슈팅: 해당 포제션 시작 이벤트부터 (상한: 슈팅 발생 15초 전)
# 종료: 이벤트 발생 후 다음 이벤트 (상한: 4초 후)
GOAL_CAP_SECONDS = 30
SHOT_CAP_SECONDS = 15
AFTER_EVENT_SECONDS = 4
HIGHLIGHT_XG_THRESHOLD = 0.25
```

### 2) 움직임 예측 단기 외삽 (Predict Extrapolation)
```python
def extrapolate(pos, vel, max_speed, anchor, t_sec=2.0, pull=0.15):
    # 1. 속도 클램프 (최대 8.0 m/s)
    speed = math.hypot(vel[0], vel[1])
    if speed > max_speed and speed > 0:
        vel = (vel[0] * max_speed / speed, vel[1] * max_speed / speed)
    # 2. 선형 외삽
    pred_x = pos[0] + vel[0] * t_sec
    pred_y = pos[1] + vel[1] * t_sec
    # 3. 경기 평균 위치(Anchor)로의 인력 반영
    if anchor is not None:
        weight = min(1.0, pull * t_sec)
        pred_x += (anchor[0] - pred_x) * weight
        pred_y += (anchor[1] - pred_y) * weight
    # 4. 피치 경계 클램프 (0~120, 0~80)
    pred_x = max(0.0, min(120.0, pred_x))
    pred_y = max(0.0, min(80.0, pred_y))
    return (round(pred_x, 2), round(pred_y, 2))
```

---

# Part 4. 단계별 실행 체크리스트 (Implementation Checklist)

### 📌 Step 1: 분석 엔진 리팩토링 및 결함 수정
- [ ] `backend/app/analysis/common.py`: 불필요한 `attack_direction` 제거, `event_time` 경기 시간 계산 보조 함수 정비.
- [ ] `backend/app/analysis/formation.py`: 360 익명 프레임 처리 및 이벤트 참여 위치 기반 포메이션 평균 산출.
- [ ] `backend/app/analysis/zones.py`: `three_sixty` 프레임 매핑 시 선수 ID 대신 팀 소속(`teammate`) 기준으로 셀 점유율 가산.
- [ ] `backend/app/analysis/pressure.py`: 상대 진영(x ≥ 40) 기준 PPDA 산출 및 정상 경기 시간 기준 `pressures_per_min` 계산.
- [ ] `backend/app/analysis/buildup.py`: `possession_team` 기준 3분할 시작 지점 계산 및 전진 기준 단순화.
- [ ] `backend/app/analysis/movement.py`: 스냅샷 노이즈 방지 및 유효 dt 기반 속도/스프린트 통계.

### 📌 Step 2: 스토리지, 다운로더, 파이프라인 완성
- [ ] `backend/app/storage.py`: `match_count`, `season_id` 쿼리 수정 및 하이라이트/프레임 멱등 저장 로직 점검.
- [ ] `backend/app/downloader.py`: `fetch_three_sixty_index` Rate Limit 대응 및 `data/raw/` 캐시 읽기/쓰기 구현.
- [ ] `backend/app/highlights.py`: 골/페널티/xG≥0.25 추출 + 포제션 기반 클립 윈도우 빌더 구현.
- [ ] `backend/app/frames.py`: 하이라이트 재생용 360 위치/속도/앵커 프레임 생성기 구현.
- [ ] `backend/app/processing.py`: 경기 단위 전체 분석 및 DB 적재 파이프라인 조립.
- [ ] `backend/app/cli.py`: `fetch`, `process` CLI 명령어 구현.
- [ ] `backend/app/main.py`: FastAPI 웹 서버 및 REST 엔드포인트 5종 구현.

### 📌 Step 3: 백엔드 테스트 구축
- [ ] `backend/tests/fixtures/`: 테스트용 미니 픽스처 작성 (`events.json`, `lineups.json`, `three-sixty.json`, `matches.json`).
- [ ] `backend/tests/test_analysis.py`: 전술 지표(포메이션, 점유율, PPDA, 패스네트워크) 계산 단위 테스트.
- [ ] `backend/tests/test_highlights.py`: 하이라이트 윈도우 클리핑 및 프레임 빌더 테스트.
- [ ] `backend/tests/test_predict.py`: 외삽 속도/피치 경계 클램프 및 앵커 당김 테스트.
- [ ] `backend/tests/test_api.py`: FastAPI 엔드포인트 스모크 테스트.

### 📌 Step 4: 프론트엔드 풀스택 구축 (`frontend/`)
- [ ] React 18 + Vite + TypeScript + Tailwind CSS 스캐폴딩.
- [ ] `frontend/Dockerfile` & `nginx.conf` (:3000 서빙, :8000 API 프록시).
- [ ] `src/lib/pitch.ts`: StatsBomb 120×80 ↔ SVG 피치 뷰포트 변환 유틸.
- [ ] `src/lib/predict.ts` & `src/lib/interpolate.ts`: 프론트엔드 외삽 고스트 및 선형 보간 엔진.
- [ ] `src/components/TacticalBoard.tsx`: D3 SVG 바둑판 피치 (그리드 히트맵, 패스선, 선수 토큰, 고스트 토큰).
- [ ] `src/components/MatchView.tsx`: 전술 기조 요약 카드 및 보드 연동 뷰.
- [ ] `src/components/HighlightView.tsx`: 하이라이트 목록, 인터랙티브 플레이어(재생/일시정지/속도/스크러버), 빈 상태 UI.
- [ ] `src/App.tsx`: 대회/경기 선택 네비게이션 및 뷰 탭 전환.
- [ ] Vitest 단위 테스트 (`pitch.test.ts`, `predict.test.ts`).

### 📌 Step 5: 통합 검증 및 운영 배포
- [ ] `docker compose up --build -d` 컨테이너 빌드 및 정상 기동 확인.
- [ ] `docker compose run --rm backend python -m app.cli fetch` 및 `process` 실행 검증.
- [ ] 웹 UI(http://localhost:3000)에서 경기 요약 및 하이라이트 바둑판 재생 검증.
- [ ] README 및 UI 내 StatsBomb Open Data (CC BY 4.0) 출처 표기 확인.
