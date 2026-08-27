# StatsBomb 기반 축구 전술 분석 시스템 — 통합 구현 명세서 (v3.2)
(UEFA 6대 서브 국면 동적 포메이션 모핑 및 학계 연구 기반 5대 전술 플레이북 전면 반영본)

---

## 📋 목차
1. [프로젝트 비전 및 핵심 철학](#1-프로젝트-비전-및-핵심-철학)
2. [StatsBomb 도메인 스펙 및 정합성 원칙](#2-statsbomb-도메인-스펙-및-정합성-원칙)
3. [UEFA 6대 서브 국면 포메이션 동적 모핑 엔진](#3-uefa-6대-서브-국면-포메이션-동적-모핑-엔진)
4. [학계 연구 기반 5대 시그니처 전술 플레이북](#4-학계-연구-기반-5대-시그니처-전술-플레이북)
5. [360 시야각 & 패스 차단선 레이캐스팅 파이프라인](#5-360-시야각--패스-차단선-레이캐스팅-파이프라인)
6. [REST API 엔드포인트 명세](#6-rest-api-엔드포인트-명세)
7. [프론트엔드 React 18 + D3 동적 바둑판 시각화](#7-프론트엔드-react-18--d3-동적-바둑판-시각화)
8. [단계별 실행 체크리스트 (Implementation Runbook)](#8-단계별-실행-체크리스트-implementation-runbook)

---

# 1. 프로젝트 비전 및 핵심 철학

## 1.1 개요
본 프로젝트는 StatsBomb Open Data(이벤트 및 360 프리즈프레임)를 활용하여 단순한 경기 전체 정적 통계 대시보드를 탈피하고, **UEFA 코칭 라이선스 표준의 6대 서브 국면 대형 변화**와 **스포츠 데이터 과학 학계(MIT Sloan / StatsBomb Conference) 기반의 5대 전술 플레이북**을 인터랙티브 D3 SVG 피치 위에서 역동적으로 구현하는 현대적 전술 분석 웹 애플리케이션입니다.

## 1.2 핵심 기능 4대 축
1. **[최우선] UEFA 6대 서브 국면 포메이션 동적 모핑 (Tactical Shape Shifting)**:
   - 볼 소유 3단계: [후방 빌드업 (3-2)] ↔ [중원 전개 (3-2-4-1)] ↔ [파이널서드 공격 (2-3-5)]
   - 볼 미소유 3단계: [전방 압박 블록] ↔ [미들 4-4-2 블록] ↔ [로우 5-4-1 밀집 블록]
   - 탭 전환 시 11명의 선수 토큰이 0.5초 D3 부드러운 애니메이션으로 대형을 스르륵 변경.
2. **학계 연구 기반 5대 시그니처 전술 플레이북 (Playbook Sequence Drawing)**:
   - 과부하 컷백, 포켓 3자 침투, 하프스페이스 언더래핑, 딥 라인브레이킹, 하이프레스 속공 자동 추출 및 화살표 드로잉.
3. **압박 트랩 & 수비 라인 높이 분석 (Pressing Traps & Line Height)**:
   - 터치라인에 상대를 가두어 볼을 탈취한 구역 및 잔류 수비(Rest Defense) 구조 분석.
4. **360 열린 패스길 & 차단선 분석 (Open vs Blocked Passing Lanes)**:
   - 하이라이트 360 스냅샷에서 열린 패스길(녹색 실선)과 상대 수비 차단선(적색 점선) 레이캐스팅 렌더링.

---

# 2. StatsBomb 도메인 스펙 및 정합성 원칙

## 2.1 단일 정규화 좌표계 ($x=0 	o 120$)
* **피치 규격**: $120.0\text{m} \times 80.0\text{m}$ (x: 0~120, y: 0~80)
* **공격 방향 고정**: 모든 팀/이벤트는 공을 소유한 팀 기준 항상 왼쪽($x=0$)에서 오른쪽($x=120$)으로 공격하도록 사전 정규화되어 있습니다.
  - 수비 서드 (Defensive Third): $0.0 \le x < 40.0\text{m}$
  - 미들 서드 (Middle Third): $40.0 \le x < 75.0\text{m}$
  - 파이널 서드 (Final Third): $75.0 \le x \le 120.0\text{m}$
  - 페널티 박스 (Penalty Area): $x \ge 102.0\text{m}, y: 18.0 \sim 62.0\text{m}$

## 2.2 360 프리즈프레임 스키마와 매핑 원칙
* `three-sixty/{match_id}.json`은 `event_uuid`로 `events.json`의 `id`와 1:1 매핑.
* 익명 선수 객체: `{ teammate: bool, actor: bool, keeper: bool, location: [x, y] }`
* 매핑 및 렌더링 전략:
  - `actor: true` -> 이벤트 주체 선수(`player_id`, 이름, 등번호 매칭)
  - `keeper: true` -> 라인업 GK 매칭
  - `teammate: true/false` -> 아군/상대팀 색상으로 바둑판에 배치
  - `visible_area` -> 카메라 시야 다각형 반투명 오버레이 렌더링
  - 카메라 밖 미관측 선수 -> 해당 서브 국면의 앵커 좌표 기반 가상 고스트 토큰 자동 생성 (토글)

---

# 3. UEFA 6대 서브 국면 포메이션 동적 모핑 엔진

`app/analysis/formation.py` 모듈에서 볼 소유권 및 공의 위치, 전술적 상황을 결합하여 경기를 **6대 서브 국면**으로 정밀 분리 집계합니다.

```
┌────────────────────────────────────────────────────────────────────────┐
│                   [UEFA 6대 서브 국면 포메이션 모델]                    │
├───────────────────────────────────┬────────────────────────────────────┤
│   [A. 볼 소유 국면 (In-Possession)] │ [B. 볼 미소유 국면 (Out-of-Possession)]│
├───────────────────────────────────┼────────────────────────────────────┤
│ 1. 후방 빌드업 (Build-up, x < 40m) │ 4. 전방 압박 블록 (High Press, x >= 65m)│
│ 2. 중원 전개 (Progression, 40~75m)│ 5. 미들 블록 (Mid-Block, 40 <= x < 65m) │
│ 3. 기회 창출 (Final Third, x >= 75m)│ 6. 로우 블록 (Low-Block, x < 40m)     │
└───────────────────────────────────┴────────────────────────────────────┘
```

### 1) 볼 소유 3단계 서브 국면
* **① 후방 빌드업 (Build-up Phase)**:
  - 조건: `possession_team == team_id` and 이벤트 $x < 40.0\text{m}$
  - 분석: 골키퍼/센터백/3선 미드필더의 1차 빌드업 대형 (예: 3-2 빌드업 대형, 센터백 벌림 거리)
* **② 중원 전개 (Progression Phase)**:
  - 조건: `possession_team == team_id` and 이벤트 $40.0 \le x < 75.0\text{m}$
  - 분석: 미들 서드 볼 순환 및 전진 대형 (예: 3-2-4-1 대형, 풀백 인버티드 안쪽 전진, 메짤라 하프스페이스 위치)
* **③ 기회 창출 (Chance Creation / Final Third)**:
  - 조건: `possession_team == team_id` and 이벤트 $x \ge 75.0\text{m}$
  - 분석: 파이널 서드 박스 타격 대형 (예: 2-3-5 / 3-1-6 대형, 박스 침투 5~6인 배치, 최후방 2~3인 잔류 수비 Rest Defense)

### 2) 볼 미소유 3단계 수비 블록
* **④ 전방 압박 블록 (High Pressing Block)**:
  - 조건: `possession_team != team_id` and 수비 액션 위치 $x \ge 65.0\text{m}$
  - 분석: 상대 진영에서의 압박 라인 높이, 대인 압박 대형, 터치라인 유도 형태
* **⑤ 미들 블록 (Mid-Block Defense)**:
  - 조건: `possession_team != team_id` and 수비 액션 위치 $40.0 \le x < 65.0\text{m}$
  - 분석: 중원 콤팩트 4-4-2 / 5-3-2 두 줄 수비, 미드필드-수비 라인 간격($\text{Length}$) 및 좌우 간격($\text{Width}$)
* **⑥ 로우 블록 (Low-Block Defense)**:
  - 조건: `possession_team != team_id` and 수비 액션 위치 $x < 40.0\text{m}$
  - 분석: 자기 진영 페널티 박스 보호 5-4-1 밀집 수비, 박스 안 수적 우위

### 3) 산출 지표 (각 국면 공통)
* 선수 11명의 평균 좌표 `(x, y)` 및 포지션 앵커 좌표
* `line_height` (최후방 수비 라인 평균 $x$ 좌표)
* `compactness_length` (최전방~최후방 간격), `compactness_width` (좌우 폭)
* `formation_label` (예: "3-2-4-1", "2-3-5", "4-4-2", "5-4-1")

---

# 4. 학계 연구 기반 5대 시그니처 전술 플레이북

`app/analysis/playbook.py` 모듈은 연속된 패스/캐리/슈팅 시퀀스를 탐색하여, 스포츠 데이터 분석 학계(MIT Sloan / StatsBomb) 연구 기준에 부합하는 **5대 시그니처 공격 전개 패턴**을 자동 추출합니다.

### 1) 측면 과부하 & 컷백 (Side Overload & Cutback)
* **정의**: 터치라인 부근($y \le 22$ 또는 $y \ge 58$, $x \ge 88$)에서 수적 우위를 만든 후 박스 안 중앙($28 \le y \le 52$, $x \ge 85$)으로 꺾어주는 컷백 패스 및 슈팅.

### 2) 포켓(Zone 14) 3자 연계 침투 (Pocket Play & Third-man Run)
* **정의**: 상대 수비-미드필더 사이 포켓(Zone 14, $x: 75 \sim 95$, $y: 28 \sim 52$)에 위치한 2선 리시버에게 1차 패스 투입 후, $2.0$초 이내에 쇄도하는 3자 공격수에게 원터치 스루패스 연결.

### 3) 하프스페이스 언더래핑 & 얼리크로스 (Half-space Underlap & Early Cross)
* **정의**: 윙어가 터치라인을 벌리고 풀백/메짤라가 하프스페이스($y: 18 \sim 30$ 또는 $50 \sim 62$, $x: 65 \sim 88$)로 언더래핑 침투하여 수비 배후로 올리는 대각선 얼리 크로스.

### 4) 후방 딥 라인브레이킹 종패스 (Deep Line-breaking Penetrative Pass)
* **정의**: 최후방 센터백/수비형미드필더($x \le 55$)에서 중원을 건너뛰고 상대 수비 라인 사이 2선 공격수($x \ge 80$)에게 $\Delta x \ge 30\text{m}$ 직선 관통 종패스.

### 5) 전방 압박 탈취 즉시 속공 슛 (High-turnover Direct Strike)
* **정의**: 상대 진영($x \ge 75$)에서 `Ball Recovery` 또는 `Interception` 후 $5.0$초 및 3터치 이내에 즉시 `Shot`으로 연결.

---

# 5. 360 시야각 & 패스 차단선 레이캐스팅 파이프라인

`app/frames.py` 모듈에서 하이라이트 360 스냅샷의 패스 선택지를 2차원 기하 레이캐스팅으로 분석합니다:

1. **열린 패스길 (Open Passing Lane, 녹색 실선)**:
   - 공을 소유한 액터($P_0$)와 동료 선수($P_i$) 사이 선분에서 상대 수비수와의 수직 거리가 $2.5\text{m}$ 이상 확보된 안전한 패스 경로.
2. **차단된 패스길 (Blocked Passing Lane, 적색 점선)**:
   - 선분 반경 $2.5\text{m}$ 내에 상대 수비수가 위치하여 패스 차단 위험이 높은 경로.
3. **선택된 패스 (Selected Pass, 황금 굵은 실선)**:
   - 선수가 실제로 선택하여 실행한 패스 궤적.

---

# 6. REST API 엔드포인트 명세

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` | `/api/competitions` | 대회 목록 (`match_available_360` 포함) |
| `GET` | `/api/competitions/{comp_id}/matches?season_id={season_id}` | 매치 목록 및 360 가용성 |
| `GET` | `/api/matches/{match_id}/summary` | UEFA 6대 서브 국면 포메이션, 5대 플레이북 TOP 3/5, 압박 트랩 맵, 12x8 점유율 |
| `GET` | `/api/matches/{match_id}/highlights` | 골 및 $xG \ge 0.25$ 하이라이트 클립 목록 |
| `GET` | `/api/highlights/{highlight_id}/frames` | 360 프레임, 시야각 다각형, 열린/차단된 패스길 레이캐스팅 데이터 |

---

# 7. 프론트엔드 React 18 + D3 동적 바둑판 시각화

### 1) `TacticalBoard.tsx`
* **UEFA 6대 국면 D3 모핑 애니메이션**:
  - `[후방 빌드업] | [중원 전개] | [파이널서드 공격] | [전방 압박] | [미들 블록] | [로우 블록]` 탭 클릭 시 D3 `transition().duration(500)`으로 11개 토큰이 부드럽게 대형 변경.
* **플레이북 시퀀스 드로잉**:
  - 선택된 플레이북 패턴의 패스/캐리 화살표 애니메이션.
* **360 하이라이트 레이어**:
  - 카메라 시야 다각형 (`visible_area`) 반투명 오버레이 + 열린 패스길(녹색)/차단선(적색) 렌더링.
* **22명 포메이션 앵커 고스트 토글**:
  - 카메라 밖 미관측 선수를 현재 선택된 서브 국면의 앵커 위치에 고스트 토큰으로 배치.

### 2) `MatchView.tsx` & `HighlightView.tsx`
* `MatchView`: 6대 국면 전환 바 + 국면별 콤팩트니스/라인높이 지표 카드 + 5대 플레이북 카드 + 압박 트랩 맵.
* `HighlightView`: 인터랙티브 재생기 + 패스길 가시화 토글.

---

# 8. 단계별 실행 체크리스트 (Implementation Runbook)

### Phase 1. 기반 레이어 (Config, Downloader, Storage)
- [ ] `config.py`: 6대 국면 피치 경계($x=40, 65, 75, 102$) 및 임계값 상수
- [ ] `downloader.py`: `match_available_360` 감지 & `data/raw/` 로컬 디스크 캐싱
- [ ] `storage.py`: 6대 서브 국면 및 5대 플레이북 스키마 반영 SQLite CRUD

### Phase 2. 전술 분석 엔진 고도화 (`backend/app/analysis/`)
- [ ] `common.py`: 좌표 정규화 및 헬퍼 유틸
- [ ] `formation.py`: UEFA 6대 서브 국면별 선수 평균 위치 및 라인높이/콤팩트니스 산출
- [ ] `playbook.py`: 5대 시그니처 공격 패턴(과부하 컷백, 포켓 3자, 하프스페이스 언더랩, 딥 라인브레이킹, 하이프레스 속공) 자동 추출
- [ ] `pressure.py`: 압박 트랩 핫스팟 및 상대 진영 PPDA
- [ ] `passes.py`, `zones.py`, `transitions.py`

### Phase 3. 하이라이트 & 360 패스길 레이캐스팅 파이프라인
- [ ] `highlights.py`: 골/고xG 클립 윈도우 추출
- [ ] `frames.py`: 360 시야각 + 열린/차단된 패스길 레이캐스팅 + 외삽
- [ ] `processing.py` & `cli.py`: 종합 분석 파이프라인 및 CLI
- [ ] `main.py`: FastAPI REST API 5종

### Phase 4. 백엔드 테스트 구축
- [ ] `tests/test_analysis.py`: 6대 국면 포메이션, 5대 플레이북, 패스길 단위 테스트 (`uv run pytest`)

### Phase 5. React 18 + D3 동적 바둑판 프론트엔드 개편
- [ ] `TacticalBoard.tsx`: 6대 국면 D3 모핑 애니메이션 + 플레이북 화살표 + 360 패스길
- [ ] `MatchView.tsx`: 6대 국면 컨트롤러 + 플레이북 카드
- [ ] `HighlightView.tsx`: 하이라이트 플레이어

### Phase 6. 종합 통합 검증
- [ ] 실제 360 경기 데이터 E2E 검증
