# StatsBomb 기반 축구 전술 분석 및 인터랙티브 바둑판 웹 서비스 — 통합 구현 명세서 (v3.1)
(국면별 동적 포메이션 전환, 전술 플레이북, 압박 트랩, 360 패스길 분석 전면 반영본)

---

## 📋 목차
1. [프로젝트 비전 & 핵심 아키텍처](#1-프로젝트-비전--핵심-아키텍처)
2. [StatsBomb 도메인 규격 & 정합성 원칙](#2-statsbomb-도메인-규격--정합성-원칙)
3. [5대 인터랙티브 전술 분석 엔진 정밀 스펙](#3-5대-인터랙티브-전술-분석-엔진-정밀-스펙)
4. [하이라이트 & 360 프레임 파이프라인](#4-하이라이트--360-프레임-파이프라인)
5. [REST API 계약 (Backend Endpoints)](#5-rest-api-계약-backend-endpoints)
6. [프론트엔드 인터랙티브 바둑판 시각화 (TacticalBoard & UI)](#6-프론트엔드-인터랙티브-바둑판-시각화-tacticalboard--ui)
7. [단계별 실행 체크리스트 (Implementation Checklist)](#7-단계별-실행-체크리스트-implementation-checklist)

---

# 1. 프로젝트 비전 & 핵심 아키텍처

## 1.1 개요
StatsBomb Open Data(이벤트 및 360 프리즈프레임)를 가공하여 단순한 정적 통계 대시보드를 탈피하고:
1. **[최우선] 3대 국면(수비 ↔ 빌드업 ↔ 공격) 포메이션 동적 모핑 (Tactical Shape Shifting)**
2. **시그니처 전술 전개 패턴 TOP 3 플레이북 (Tactical Playbook Animation)**
3. **압박 트랩 핫스팟 & 수비 라인 높이 분석 (Pressing Trap & Defensive Line)**
4. **시간대별 전술 변화 타임라인 스크러버 (Tactical Shifts Timeline)**
5. **360 시야각 기반 열린 패스길 / 차단선 렌더링 (Open vs Blocked Passing Lanes)**
을 인터랙티브 D3 SVG 바둑판 피치 위에서 역동적으로 구현하는 현대적 축구 전술 분석 웹 애플리케이션을 구축합니다.

## 1.2 전체 아키텍처
```
┌─────────────────────────────────────────────────────────────┐
│                 Frontend (React 18 + TypeScript + Vite)      │
│  - TacticalBoard.tsx: D3 SVG 120x80 / 3대 국면 모핑 트랜지션 │
│    시야각 다각형 / 패턴 화살표 / 열린 패스길 / 22명 앵커 토글 │
│  - MatchView.tsx: 국면 탭, 플레이북 카드, 압박/라인 분석 UI │
│  - HighlightView.tsx: 하이라이트 플레이어, 차단선, 타임라인  │
└──────────────────────────────┬──────────────────────────────┘
                               │ HTTP (:3000 -> :8000/api)
┌──────────────────────────────▼──────────────────────────────┐
│                 Backend (FastAPI / Python 3.13+)            │
│  - main.py: CORS, REST API 5 Routes                         │
│  - highlights.py & frames.py: 클립 윈도우 & 360 패스길 빌더  │
│  - analysis/:                                               │
│    * formation.py: 3대 국면(수비/빌드업/공격)별 대형 산출    │
│    * playbook.py: 시그니처 전개 패턴 TOP 3 시퀀스 추출      │
│    * pressure.py: 압박 트랩 핫스팟 & 수비 라인 높이 산출     │
│    * timeline.py: 시간대별 포메이션 및 전술 변화 슬라이스   │
│    * zones.py, passes.py, buildup.py, transitions.py        │
│  - storage.py: SQLite (data/db.sqlite) CRUD                 │
│  - downloader.py: GitHub Raw 다운로드 & data/raw/ 로컬 캐시  │
│  - cli.py: `fetch` & `process` CLI 진입점                   │
└──────────────────────────────┬──────────────────────────────┘
```

---

# 2. StatsBomb 도메인 규격 & 정합성 원칙

## 2.1 단일 정규화 좌표계 ($x=0 	o 120$)
* **피치 규격**: $120.0\text{m} \times 80.0\text{m}$ (x: 0~120, y: 0~80)
* **공격 방향 고정**: 모든 팀/이벤트는 공을 쥔 팀 기준 항상 왼쪽($x=0$)에서 오른쪽($x=120$)으로 공격하도록 정규화되어 있음. (좌표 반전 로직 배제)
  - 수비 서드 (Defensive Third): $0.0 \le x < 40.0$
  - 미들 서드 (Middle Third): $40.0 \le x < 80.0$
  - 파이널 서드 (Final Third): $80.0 \le x \le 120.0$

## 2.2 360 프리즈프레임 스키마와 익명성 처리
* `three-sixty/{match_id}.json`은 `event_uuid`로 `events.json`의 `id`와 1:1 매핑.
* `freeze_frame` 선수 객체: `{ "teammate": bool, "actor": bool, "keeper": bool, "location": [x, y] }`
* 매핑 원칙:
  - `actor: true` -> 이벤트 주체 선수(`player_id`, 이름, 등번호 매칭)
  - `keeper: true` -> 라인업 GK 매칭
  - `teammate: true/false` -> 아군/상대팀 색상으로 바둑판에 배치
  - `visible_area` -> 카메라 시야각 반투명 다각형 렌더링
  - 카메라 밖 미관측 선수 -> 해당 국면 앵커 좌표 기반 가상 고스트 토큰 자동 생성 (토글)

---

# 3. 5대 인터랙티브 전술 분석 엔진 정밀 스펙

### 1) [최우선] 3대 국면(Phase) 동적 포메이션 엔진 (`app/analysis/formation.py`)
이벤트를 볼 소유권 및 공의 피치 위치에 따라 3대 국면으로 엄격히 분류하여 각 선수별 평균 $(x, y)$ 및 진형 너비/길이(Compactness)를 산출합니다.

* **수비 국면 (Defensive Shape)**:
  - 조건: 상대팀 볼 소유 (`possession_team != team_id`) 또는 우리 진영 수비 액션
  - 산출 지표: 수비 블록 형태(예: 4-4-2 두 줄 수비), 수비 라인 평균 높이($\text{Line Height}$), 선수 간격 너비($\text{Width}$)/길이($\text{Length}$)
* **빌드업 국면 (Buildup Shape)**:
  - 조건: 우리 팀 볼 소유 (`possession_team == team_id`) 중 **자기 진영($x < 60.0$)**에서 발생한 패스/캐리/터치 이벤트
  - 산출 지표: 후방 빌드업 대형(예: 3-2 빌드업 대형, 풀백 인버티드 전진 여부, 센터백 벌림 거리)
* **공격 국면 (Attacking Shape)**:
  - 조건: 우리 팀 볼 소유 (`possession_team == team_id`) 중 **상대 진영($x \ge 60.0$)**에서 발생한 공격 전개 이벤트
  - 산출 지표: 파이널 서드 박스 타격 대형(예: 2-3-5, 3-2-5), 최전방 공격 가담 인원 수, 하프스페이스 점유 선수
* **응답 데이터 구조**:
  ```json
  {
    "defensive": { "formation": "4-4-2", "line_height": 32.5, "width": 42.0, "length": 22.0, "players": [...] },
    "buildup": { "formation": "3-2-4-1", "line_height": 45.0, "width": 55.0, "length": 34.0, "players": [...] },
    "attacking": { "formation": "2-3-5", "line_height": 72.0, "width": 62.0, "length": 38.0, "players": [...] }
  }
  ```

### 2) 시그니처 공격 패턴 TOP 3 플레이북 (`app/analysis/playbook.py`)
연속된 패스/캐리 시퀀스를 분석하여 경기 중 가장 유의미하고 반복된 공격 전개 패턴 3종을 추출합니다.
* **패턴 분류 기준**:
  - 측면 오버래핑 & 컷백 패턴 (Side Overload & Cutback)
  - 인버티드 풀백 중앙 전환 패턴 (Inverted Switch)
  - 중앙 침투 다이렉트 스루패스 패턴 (Central Penetration)
* **산출 데이터**: 패턴 이름, 발생 횟수, 총 창출 xG, 시퀀스 내 이벤트 좌표 목록 ($start \to end$ 화살표 렌더링용).

### 3) 압박 트랩 & 수비 라인 높이 (`app/analysis/pressure.py`)
* **압박 트랩 핫스팟 (Pressing Trap Zones)**:
  - 상대 볼 소유자를 3초 이내에 2명 이상의 선수가 동시에 압박하여 볼을 탈취한 구역 (좌우 측면 터치라인 트랩 등).
* **수비 라인 높이 추이**: 경기 시간대별 최후방 수비수들의 $x$ 좌표 평균 변화.
* **PPDA (상대 진영 $x \ge 40$)**: $\text{PPDA} = \frac{\text{Opponent Passes in } x \ge 40}{\text{Defensive Actions in } x \ge 40}$.

### 4) 시간대별 전술 변화 타임라인 (`app/analysis/timeline.py`)
* 경기를 15분 단위 구간(0~15, 15~30, 30~45, 45~60, 60~75, 75~90+) 또는 주요 전술 변경(Tactical Shift/골) 기점으로 분할.
* 각 구간별 실시간 포메이션, 수비 라인 높이, 점유율 슬라이스 제공.

### 5) 360 열린 패스길 & 차단선 분석 (`app/analysis/passes.py` & `frames.py`)
* 360 스냅샷에서 공을 잡은 선수와 동료 선수 사이의 직선 경로상에 상대 수비수 존재 여부를 레이캐스팅(Ray-casting)으로 계산:
  - **열린 패스길 (Open Lane, 녹색)**: 상대 수비수가 반경 $2.5\text{m}$ 내에 없는 안전한 패스 경로
  - **차단된 패스길 (Blocked Lane, 붉은 점선)**: 상대 수비수가 차단각에 위치한 위험 경로
  - **선택된 패스 (Selected Pass, 황금 실선)**: 실제 선수가 패스한 궤적

---

# 4. 하이라이트 & 360 프레임 파이프라인

## 4.1 클립 윈도우 추출 (`app/highlights.py`)
* 골(슈팅/페널티/자책골) 및 $xG \ge 0.25$ 슈팅 추출.
* 포제션 시작 이벤트(골 30초, 슛 15초 상한) ~ 이벤트 후 4초까지 클리핑.

## 4.2 프레임 빌더 (`app/frames.py`)
* 프레임별 데이터: `timestamp`, `ball_location`, `visible_area`, `players` (실측 좌표, 속도 $v_x, v_y$, $+2$초 외삽 예측 좌표, 국면 앵커 좌표), `passing_lanes` (열린/차단된 패스길 목록).

---

# 5. REST API 계약 (Backend Endpoints)

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` | `/api/competitions` | 처리된 대회 목록 (`match_available_360` 포함) |
| `GET` | `/api/competitions/{comp_id}/matches?season_id={season_id}` | 매치 목록 및 360 가용성 |
| `GET` | `/api/matches/{match_id}/summary` | 3대 국면 포메이션(수비/빌드업/공격), 플레이북 TOP 3, 압박 트랩, 12x8 점유율, 타임라인 |
| `GET` | `/api/matches/{match_id}/highlights` | 하이라이트 클립 목록 (`id`, `type`, `minute`, `xg`, `window`) |
| `GET` | `/api/highlights/{highlight_id}/frames` | 360 프레임, 시야각 다각형, 열린/차단된 패스길, 외삽 고스트 |

---

# 6. 프론트엔드 인터랙티브 바둑판 시각화 (TacticalBoard & UI)

## 6.1 `TacticalBoard.tsx` 핵심 구현
1. **3대 국면 모핑 애니메이션**:
   - `[수비 대형] | [빌드업 대형] | [공격 대형]` 토글 클릭 시 D3 `transition().duration(500)`으로 11명의 선수 토큰이 부드럽게 대형을 변경.
2. **플레이북 패턴 애니메이션**:
   - 플레이북 카드 호버/클릭 시 전술 전개 패스/침투 화살표가 피치 위에 순차적으로 드로잉 애니메이션.
3. **360 하이라이트 뷰**:
   - 카메라 시야 다각형(`visible_area`) 반투명 오버레이 + 녹색(열린 길) / 적색(차단선) 패스 옵션 렌더링.
4. **22명 포메이션 앵커 추론 토글**:
   - 카메라 밖 미관측 선수를 현재 선택된 국면(수비/빌드업/공격)의 앵커 위치에 반투명 고스트 토큰으로 자동 배치.

## 6.2 `MatchView.tsx` & `HighlightView.tsx`
* `MatchView`: 상단 국면 전환 바둑판 피치 + 국면별 콤팩트니스 지표 카드 + TOP 3 플레이북 카드 + 압박 트랩 맵.
* `HighlightView`: 인터랙티브 재생기 (재생/일시정지/0.5x~2x/스크러버/패스길 토글).

---

# 7. 단계별 실행 체크리스트 (Implementation Checklist)

### Phase 1. 기반 레이어 구축 (`config`, `downloader`, `storage`)
- [ ] `config.py`: 피치/국면 경계($x=40, 60, 80$)/임계값 상수 정비
- [ ] `downloader.py`: `match_available_360` 감지 & `data/raw/` 디스크 캐싱
- [ ] `storage.py`: 3대 국면 및 플레이북 스키마 반영 SQLite CRUD

### Phase 2. 5대 인터랙티브 전술 분석 엔진 구축 (`backend/app/analysis/`)
- [ ] `common.py`: 좌표 유틸리티 확립 및 정규화
- [ ] `formation.py`: 3대 국면(수비/빌드업/공격) 분리 집계 및 라인 높이/너비/길이 산출
- [ ] `playbook.py`: 시그니처 공격 전개 패턴 TOP 3 시퀀스 자동 추출
- [ ] `pressure.py`: 압박 트랩 핫스팟 및 상대 진영 PPDA 산출
- [ ] `timeline.py`: 시간대별(15분 단위) 전술 변화 슬라이스
- [ ] `passes.py` & `zones.py`: 패스 네트워크 및 12x8 그리드 점유율

### Phase 3. 하이라이트, 360 패스길 프레임 빌더 & FastAPI
- [ ] `highlights.py`: 골/고xG 클립 윈도우 추출
- [ ] `frames.py`: 360 위치/시야각 + 열린/차단된 패스길 레이캐스팅 + 외삽
- [ ] `processing.py` & `cli.py`: 종합 분석 파이프라인 및 CLI
- [ ] `main.py`: FastAPI REST API 5종 엔드포인트

### Phase 4. 백엔드 테스트 구축
- [ ] `tests/fixtures/`: 실측 축소 픽스처
- [ ] `tests/`: 3대 국면 포메이션, 플레이북, 패스길, API 단위/통합 테스트 (`uv run pytest`)

### Phase 5. 프론트엔드 React 18 + D3 바둑판 전면 개편
- [ ] `TacticalBoard.tsx`: 3대 국면 D3 모핑 애니메이션 + 시야각 + 패스길 + 22명 고스트
- [ ] `MatchView.tsx`: 국면 전환 컨트롤러 + 플레이북 카드 + 압박 트랩
- [ ] `HighlightView.tsx`: 하이라이트 플레이어 및 패스길 토글

### Phase 6. 통합 검증 및 E2E 테스트
- [ ] 실제 360 경기 fetch -> process -> UI 대형 모핑 및 하이라이트 E2E 검증
