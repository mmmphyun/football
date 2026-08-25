# StatsBomb 기반 축구 전술 분석 웹 서비스 — 통합 구현 명세서 v3
(StatsBomb Open Data 실측 스키마 및 교차검증 기반 전면 재설계본)

---

## 📋 목차
1. [프로젝트 개요 및 시스템 아키텍처](#1-프로젝트-개요-및-시스템-아키텍처)
2. [StatsBomb 도메인 규격 및 정합성 원칙](#2-statsbomb-도메인-규격-및-정합성-원칙)
3. [데이터 파이프라인 (Downloader & Storage)](#3-데이터-파이프라인-downloader--storage)
4. [분석 엔진 8종 정밀 규격 (Analysis Engine)](#4-분석-엔진-8종-정밀-규격-analysis-engine)
5. [하이라이트 & 프레임 생성 파이프라인](#5-하이라이트--프레임-생성-파이프라인)
6. [REST API 계약 (Backend Endpoints)](#6-rest-api-계약-backend-endpoints)
7. [프론트엔드 바둑판 시각화 (TacticalBoard & UI)](#7-프론트엔드-바둑판-시각화-tacticalboard--ui)
8. [단계별 실행 체크리스트 (Implementation Checklist)](#8-단계별-실행-체크리스트-implementation-checklist)

---

# 1. 프로젝트 개요 및 시스템 아키텍처

## 1.1 개요
StatsBomb Open Data(GitHub `statsbomb/open-data`, CC BY 4.0)를 수집·가공하여:
1. **경기별 팀 전술 기조 요약** (포메이션, 12×8 구역 점유율, 패스 네트워크, 압박 강도, 빌드업, 전환 속도)
2. **하이라이트 장면의 선수 움직임 바둑판(D3 SVG) 인터랙티브 재생** (360 실측 위치, 카메라 시야 다각형, 이동 속도, +2초 외삽 고스트 토큰, 22명 포메이션 앵커 추론 토글)
을 제공하는 웹 애플리케이션을 구축합니다.

## 1.2 전체 아키텍처 다이어그램
```
┌─────────────────────────────────────────────────────────────┐
│                 Frontend (React 18 + TypeScript + Vite)      │
│  - TacticalBoard.tsx (D3 SVG 120x80 / Zones / Tokens / Ghost)│
│  - MatchView.tsx (8종 전술 기조 요약 카드 & 인터랙티브 피치) │
│  - HighlightView.tsx (플레이어 컨트롤러, 시야각, 타임라인)  │
└──────────────────────────────┬──────────────────────────────┘
                               │ HTTP (:3000 -> :8000/api)
┌──────────────────────────────▼──────────────────────────────┐
│                 Backend (FastAPI / Python 3.13+)            │
│  - main.py: CORS, REST API 5 Routes                         │
│  - highlights.py & frames.py: 클립 윈도우 & 프레임 빌더      │
│  - analysis/*.py: 8종 전술 분석 엔진 모듈                   │
│  - processing.py: 매치 종합 분석 및 멱등 파이프라인          │
│  - storage.py: SQLite (data/db.sqlite) CRUD                 │
│  - downloader.py: GitHub Raw 다운로드 & data/raw/ 로컬 캐시  │
│  - cli.py: `fetch` & `process` CLI 진입점                   │
└──────────────────────────────┬──────────────────────────────┘
                               │ File System
┌──────────────────────────────▼──────────────────────────────┐
│                    Data Storage Layer                       │
│  - data/raw/{competitions,matches,events,lineups,360}.json   │
│  - data/db.sqlite (가공된 요약 지표, 하이라이트 메타, 프레임) │
└─────────────────────────────────────────────────────────────┘
```

---

# 2. StatsBomb 도메인 규격 및 정합성 원칙

## 2.1 단일 정규화 좌표계 ($x=0 	o 120$)
* **피치 규격**: 가로 $120.0\text{m} \times$ 세로 $80.0\text{m}$
* **공격 방향 고정**: StatsBomb 데이터는 홈/어웨이, 전/후반 구분 없이 **공을 쥔 팀 기준 항상 왼쪽($x=0$)에서 오른쪽($x=120$)으로 공격**하도록 전처리되어 있습니다.
* **[원칙]** 좌표에 $-1$을 곱하거나 `attack_direction`을 계산하여 좌표를 반전시키는 코드를 완전히 배제합니다.
  - 수비 서드 (Defensive Third): $0.0 \le x < 40.0$
  - 미들 서드 (Middle Third): $40.0 \le x < 80.0$
  - 파이널/공격 서드 (Final Third): $80.0 \le x \le 120.0$

## 2.2 360 프리즈프레임 스키마와 익명성 처리 원칙
* 360 파일은 `three-sixty/{match_id}.json` 별도 파일로 존재하며, `event_uuid`로 `events.json`의 `event["id"]`와 1:1 매핑됩니다.
* 360 프레임 내부 선수 객체는 `player_id`가 없는 **익명 데이터**입니다:
  ```json
  { "teammate": true, "actor": false, "keeper": false, "location": [61.0, 40.1] }
  ```
* **하이브리드 선수 식별 및 매핑 전략**:
  1. `actor: true` $\to$ 해당 이벤트의 `event["player"]["id"]`와 100% 매칭하여 이름/등번호 부여.
  2. `keeper: true` $\to$ 라인업의 해당 팀 GK와 매칭.
  3. `teammate: true/false` $\to$ 아군/상대팀 색상으로 바둑판에 배치하고 12×8 구역 점유율에 직접 가산.
  4. `visible_area` 다각형 $\to$ 카메라 시야 영역을 반투명 오버레이로 렌더링.
  5. 카메라 밖 미관측 선수 $\to$ 팀 경기 평균 위치(Anchor) 기반 가상 고스트 토큰 생성(토글 옵션).

## 2.3 경기 시간 계산 원칙
* `minute`와 `second`는 이미 1분/1초 단위 누적 경기 시간입니다.
* `(period - 1) * 3600` 오프셋 가산을 금지하고, `duration_min = max(event.minute)` 또는 실제 period별 시간 합산으로 정상 90~100분 산출.

---

# 3. 데이터 파이프라인 (Downloader & Storage)

## 3.1 `app/downloader.py`
* **360 보유 대회 자동 감지**:
  - `competitions.json`에서 `match_available_360` 필드가 `null`이 아니고 `MIN_MATCHES`($\ge 30$)를 만족하는 최신 대회를 우선 선정. (GitHub API Rate limit 의존성 제거)
  - `COMPETITION_ID`/`SEASON_ID` 환경변수 지정 시 고정 오버라이드 지원.
* **로컬 디스크 캐싱 (`data/raw/`)**:
  - 다운로드 전 `data/raw/...` 파일 존재 여부 우선 확인.
  - 파일 미존재 시 GitHub Raw에서 다운로드 후 로컬에 원본 JSON 저장.
  - 지수 백오프 기반 최대 3회 재시도.

## 3.2 `app/storage.py` (SQLite Schema)
* `competitions`: `competition_id`, `season_id`, `name`, `season_name`, `country`, `match_count`, `has_360`, `processed_at`
* `matches`: `match_id`, `competition_id`, `season_id`, `home_team`, `away_team`, `home_team_id`, `away_team_id`, `home_score`, `away_score`, `match_date`, `has_360`, `status`
* `match_summaries`: `match_id`, `summary_json`
* `highlights`: `id`, `match_id`, `team_id`, `team_name`, `type`, `minute`, `second`, `xg`, `start_event`, `end_event`, `event_index`
* `highlight_frames`: `id`, `match_id`, `frames_json`, `players_json`, `has_360`

---

# 4. 분석 엔진 8종 정밀 규격 (Analysis Engine)

### 1) `app/analysis/common.py`
* `event_time(ev)`: `minute * 60 + second` 기반 정상 누적 초 반환.
* `is_completed_pass(ev)`: `type == 'Pass'` and `pass.outcome is None` (또는 'Complete').
* `build_lineup_maps(lineups)`: 팀별/선수별 이름, 등번호, 포지션, GK 여부 매핑.
* `team_ids(events)` & `opponent_of(team_id, team_ids_list)`.

### 2) `app/analysis/formation.py`
* **소유/비소유 상태별(`possession`, `out_of_possession`) 선수 평균 위치**:
  - 각 선수가 참여한 온더볼 이벤트(Pass, Carry, Shot, Tackle, Pressure, Receipt 등)의 위치를 누적하여 선수별 평균 $(x, y)$ 산출.
  - 360 보유 시 팀 전체 무게중심 보정에 활용.

### 3) `app/analysis/zones.py`
* **12×8 바둑판 그리드 점유율 ($10\text{m} \times 10\text{m}$ 셀)**:
  - 360 프레임 보유 시: 모든 프리즈프레임 선수의 위치를 `teammate` 여부에 따라 아군/상대팀으로 분류하여 셀 카운트 가산.
  - 비-360 폴백: 이벤트 참여 위치(`location`, `pass.end_location`, `carry.end_location`)로 점유율 집계.
  - 각 셀별 점유 강도 ($0.0 \sim 1.0$) 정규화.

### 4) `app/analysis/passes.py`
* **패스 네트워크 (Pass Network)**:
  - 성공 패스 대상 Passer $\to$ Recipient 간 엣지 집계 (상위 15개).
  - 선수별 터치 수 및 평균 위치 $(x, y)$를 노드에 포함.
  - 팀 평균 전진 진행도 $\Delta x$ 산출.

### 5) `app/analysis/pressure.py`
* **압박 지수 & 상대 진영 PPDA**:
  - 정상 경기 시간(`duration_min`) 기준 분당 압박 횟수(`pressures_per_min`).
  - PPDA: 수비팀 기준 상대 진영($x \ge 40$)에서 발생한 상대 패스 수 $\div$ 우리 팀의 수비 액션(`Pressure`, `Tackle`, `Interception`, `Block`, `Clearance`) 수.
    $$\text{PPDA} = \frac{\text{Opponent Passes in } x \ge 40}{\text{Defensive Actions in } x \ge 40}$$

### 6) `app/analysis/buildup.py`
* **빌드업 방향 & 3분할 시작 지점**:
  - 전진 패스: $(end[0] - start[0]) \ge 10.0\text{m}$
  - 전진 캐리: $(end[0] - start[0]) \ge 5.0\text{m}$
  - 포제션 시작 서드: `possession_team == team_id`인 포제션의 첫 이벤트 위치를 기준으로 수비($x < 40$), 미들($40 \le x < 80$), 공격($x \ge 80$) 서드 시작 횟수 집계.

### 7) `app/analysis/transitions.py`
* **공 회수 후 역습 전환 속도**:
  - 공 회수(`Ball Recovery`, `Interception`) 이벤트 발생 시점부터 8초 이내에 슈팅 또는 파이널 서드($x \ge 80$)에 도달한 횟수 및 평균 소요 시간.

### 8) `app/analysis/predict.py`
* **움직임 단기 외삽 (+2초)**:
  - 상수속도 외삽 $\to$ 최대 속도 클램프 ($8.0\text{m/s}$) $\to$ 피치 경계 클램프 ($0 \le x \le 120, 0 \le y \le 80$) $\to$ 경기 평균 앵커 위치 인력 ($0.15/\text{s}$) 반영.

---

# 5. 하이라이트 & 프레임 생성 파이프라인

## 5.1 하이라이트 이벤트 추출 (`app/highlights.py`)
* **추출 대상**:
  1. 골 (Goal: 슈팅, 페널티 골, 자책골)
  2. 고위협 슈팅 ($xG \ge 0.25$)
* **포제션 기반 클립 윈도우 정책**:
  - **시작 이벤트**: 하이라이트 이벤트가 속한 포제션(`possession`)의 첫 번째 이벤트 (상한: 골 발생 30초 전, 슈팅 발생 15초 전).
  - **종료 이벤트**: 하이라이트 이벤트 직후 다음 이벤트 (상한: 발생 4초 후).

## 5.2 하이라이트 프레임 빌더 (`app/frames.py`)
* 윈도우 내 각 이벤트를 시간 순서대로 프레임으로 구성:
  - `event_index`, `timestamp`, `minute`, `second`, `ball_location`
  - `visible_area`: 카메라 시야 다각형 좌표 (360 경기)
  - `players`: 
    - 360 프레임 위치 기반 선수 목록 (`is_teammate`, `is_actor`, `is_keeper`, `location: [x, y]`)
    - 연속 프레임 간 변위 기반 선수 속도 $(v_x, v_y)$ 및 $+2$초 외삽 예측 좌표 $(pred_x, pred_y)$
    - 비-360 경기: 이벤트 참여 선수 위치로 폴백

---

# 6. REST API 계약 (Backend Endpoints)

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` | `/api/competitions` | 가공 완료된 대회 목록 (`competition_id`, `season_id`, `name`, `match_count`, `has_360`) |
| `GET` | `/api/competitions/{comp_id}/matches?season_id={season_id}` | 특정 대회의 매치 목록 (홈/어웨이 팀, 스코어, 일자, 360 가용성, 처리 상태) |
| `GET` | `/api/matches/{match_id}/summary` | 8종 전술 기조 요약 지표 (포메이션, 구역 점유율, 패스 네트워크, 압박/PPDA, 빌드업, 전환) |
| `GET` | `/api/matches/{match_id}/highlights` | 매치별 하이라이트 클립 목록 (`id`, `team`, `type`, `minute`, `xg`, `window`) |
| `GET` | `/api/highlights/{highlight_id}/frames` | 하이라이트 재생용 프레임 시퀀스 (실측 위치, 카메라 시야각, 외삽 고스트, 선수 메타) |

---

# 7. 프론트엔드 바둑판 시각화 (TacticalBoard & UI)

## 7.1 기술 스택
* **React 18 + TypeScript + Vite + Tailwind CSS + D3.js (SVG 피치 렌더링)**

## 7.2 주요 컴포넌트 구조
1. **`TacticalBoard.tsx`**:
   - $120 \times 80$ 피치 $\to$ SVG 뷰포트 반응형 변환.
   - 12×8 체커보드 바둑판 그리드 & 점유 강도 히트맵 레이어.
   - 카메라 시야 다각형 (`visible_area`) 반투명 오버레이.
   - 패스 네트워크 연결선 & 노드 렌더링.
   - 선수 원형 토큰 (팀 색상, 등번호, 액터 강조).
   - 움직임 예측 점선 고스트 토큰 (Ghost Vector).
   - **[토글] 22명 전체 진형 추론 모드**: 카메라 밖 미관측 선수를 포메이션 앵커 위치에 고스트로 자동 채움.
2. **`MatchView.tsx`**:
   - 경기 전술 기조 요약 뷰 (포메이션, 그리드 점유 히트맵, 패스 네트워크, PPDA 게이지, 빌드업 3분할 차트).
3. **`HighlightView.tsx`**:
   - 하이라이트 목록 선택 및 인터랙티브 플레이어.
   - 재생/일시정지, 속도 조절 ($0.5\times / 1\times / 2\times$), 타임라인 스크러버, 프레임 보간(Interpolation).

---

# 8. 단계별 실행 체크리스트 (Implementation Checklist)

### 📌 Step 1: 데이터 파이프라인 & 기반 레이어 구축
- [ ] `backend/app/config.py`: 상수 및 경로 설정 정비.
- [ ] `backend/app/downloader.py`: `competitions.json` 기반 360 대회 자동 감지 및 `data/raw/` 디스크 캐싱 구현.
- [ ] `backend/app/storage.py`: SQLite 스키마 바인딩 수정 및 멱등 CRUD 구현.

### 📌 Step 2: 분석 엔진 8종 리팩토링 & 검증
- [ ] `backend/app/analysis/common.py`: 좌표 유틸리티 확립, `attack_direction` 완전 제거, 정상 `event_time` 함수 정비.
- [ ] `backend/app/analysis/formation.py`: 이벤트 참여 위치 기반 포메이션 평균 산출.
- [ ] `backend/app/analysis/zones.py`: `three-sixty` 프레임 매핑 및 12×8 그리드 점유율 가산.
- [ ] `backend/app/analysis/passes.py`: 패스 네트워크 상위 엣지 및 노드 위치 집계.
- [ ] `backend/app/analysis/pressure.py`: 상대 진영($x \ge 40$) PPDA 및 정상 시간 기준 분당 압박 산출.
- [ ] `backend/app/analysis/buildup.py`: `possession_team` 기준 3분할 시작 구역 및 전진 집계.
- [ ] `backend/app/analysis/transitions.py`: 공 회수 후 8초 이내 전환 속도 집계.
- [ ] `backend/app/analysis/predict.py`: 속도/경계 클램프 및 앵커 인력 단기 외삽.

### 📌 Step 3: 하이라이트, 프레임 빌더 & 파이프라인
- [ ] `backend/app/highlights.py`: 골 및 $xG \ge 0.25$ 슈팅 추출 + 포제션 기반 클립 윈도우 빌더.
- [ ] `backend/app/frames.py`: 360 위치/속도/앵커/시야각 프레임 생성기 구현.
- [ ] `backend/app/processing.py`: 매치 종합 분석 및 DB 적재 파이프라인 조립.
- [ ] `backend/app/cli.py`: `fetch`, `process` CLI 명령어 구현.
- [ ] `backend/app/main.py`: FastAPI REST API 엔드포인트 5종 및 CORS 미들웨어.

### 📌 Step 4: 백엔드 단위/통합 테스트
- [ ] `backend/tests/fixtures/`: 실제 축소 픽스처 생성.
- [ ] `backend/tests/test_analysis.py`: 8종 분석 지표 단위 테스트.
- [ ] `backend/tests/test_highlights.py`: 윈도우 클리핑 및 프레임 빌더 테스트.
- [ ] `backend/tests/test_api.py`: FastAPI 엔드포인트 스모크 테스트.

### 📌 Step 5: 프론트엔드 풀스택 구현 (`frontend/`)
- [ ] React 18 + Vite + TypeScript + Tailwind CSS 스캐폴딩.
- [ ] `src/lib/pitch.ts`: $120 \times 80 \leftrightarrow$ SVG 피치 좌표 변환.
- [ ] `src/lib/interpolate.ts` & `src/lib/predict.ts`: 프론트엔드 프레임 선형 보간 및 외삽 엔진.
- [ ] `src/components/TacticalBoard.tsx`: D3 SVG 바둑판 피치, 시야각 다각형, 토큰, 고스트.
- [ ] `src/components/MatchView.tsx`: 전술 기조 요약 카드 및 인터랙티브 바둑판 보드.
- [ ] `src/components/HighlightView.tsx`: 하이라이트 플레이어, 컨트롤러, 빈 상태 UI.
- [ ] `src/App.tsx`: 대회/경기 네비게이션 및 뷰 탭 전환.

### 📌 Step 6: 종합 연동 및 최종 검증
- [ ] `fetch` & `process` 실제 데이터 다운로드 및 가공 실행.
- [ ] 프론트엔드 빌드 및 백엔드 연동 수동/자동 검증.
