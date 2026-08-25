# 프로젝트 진행 현황판 (2026-08-25 v3 재설계 확정)

StatsBomb Open Data 실측 스키마 교차검증을 완료하고 `IMPLEMENTATION_PLAN_V3.md`를 기준으로 작업을 실행합니다.

---

## 🎯 전체 진행 상태 요약

| 단계 | 주요 작업 내용 | 상태 |
| :--- | :--- | :---: |
| **0단계: 교차검증 및 재설계** | 실제 데이터셋 3자 교차검증, 스펙 예시 작성, v3 명세서 수립 | **완료 ✅** |
| **1단계: 기반 레이어** | `config.py`, `downloader.py` (캐시/감지), `storage.py` (CRUD) | **대기 중** |
| **2단계: 분석 엔진 리팩토링** | `common.py`, `formation.py`, `zones.py`, `passes.py`, `pressure.py`, `buildup.py`, `transitions.py`, `predict.py` | **대기 중** |
| **3단계: 하이라이트 & 파이프라인** | `highlights.py`, `frames.py`, `processing.py`, `cli.py`, `main.py` (FastAPI) | **대기 중** |
| **4단계: 백엔드 테스트** | 픽스처 작성 및 pytest 단위/통합 테스트 통과 | **대기 중** |
| **5단계: 프론트엔드 구축** | React 18 + TS + Tailwind + D3 바둑판 보드, 매치 뷰, 하이라이트 플레이어 | **대기 중** |
| **6단계: 통합 검증 & 배포** | 실제 360 경기 데이터 fetch -> process -> UI 확인, Docker Compose | **대기 중** |

---

## 📋 세부 작업 체크리스트

### 1단계: 기반 레이어
- [ ] `backend/app/config.py`: 피치/임계값 상수 정비
- [ ] `backend/app/downloader.py`: `match_available_360` 기반 감지 & `data/raw/` 디스크 캐시
- [ ] `backend/app/storage.py`: SQLite 스키마 및 CRUD 쿼리 수정

### 2단계: 분석 엔진 리팩토링
- [ ] `backend/app/analysis/common.py`: 좌표 정규화 확립 (`attack_direction` 제거), 누적 경기 시간
- [ ] `backend/app/analysis/formation.py`: 이벤트 참여 위치 기반 포메이션 평균 산출
- [ ] `backend/app/analysis/zones.py`: 360 프레임 매핑 및 12x8 그리드 점유율
- [ ] `backend/app/analysis/passes.py`: 패스 네트워크 노드/상위 엣지 집계
- [ ] `backend/app/analysis/pressure.py`: 상대 진영(x>=40) PPDA 및 분당 압박 강도
- [ ] `backend/app/analysis/buildup.py`: 3분할 시작 지점 및 전진 패스/캐리
- [ ] `backend/app/analysis/transitions.py`: 공 회수 후 8초 내 슈팅/파이널서드 진입
- [ ] `backend/app/analysis/predict.py`: +2초 단기 외삽 (최대속도/경계 클램프, 앵커 인력)

### 3단계: 하이라이트 & 파이프라인
- [ ] `backend/app/highlights.py`: 골 및 xG>=0.25 추출 + 포제션 윈도우 클리핑
- [ ] `backend/app/frames.py`: 360 위치/속도/앵커/시야각 프레임 생성
- [ ] `backend/app/processing.py`: 매치 종합 분석 및 DB 적재 파이프라인
- [ ] `backend/app/cli.py`: `fetch`, `process` CLI 명령어
- [ ] `backend/app/main.py`: FastAPI REST API 5종 및 CORS

### 4단계: 백엔드 테스트
- [ ] `backend/tests/fixtures/`: 테스트 픽스처
- [ ] `backend/tests/test_analysis.py`, `test_highlights.py`, `test_api.py`

### 5단계: 프론트엔드 구축
- [ ] Vite + React 18 + TS + Tailwind 스캐폴딩
- [ ] `src/lib/pitch.ts`, `predict.ts`, `interpolate.ts`
- [ ] `TacticalBoard.tsx` (D3 SVG 바둑판, 시야각 다각형, 토큰, 고스트, 22명 채우기 토글)
- [ ] `MatchView.tsx`, `HighlightView.tsx`, `App.tsx`

---

## 📌 핵심 도메인 결정 사항 요약
1. **좌표계**: 모든 팀 항상 x=0 -> x=120 공격 (반전 불필요).
2. **360 데이터**: `event_uuid` 매핑, 익명 선수 (`actor`=이벤트 선수, `keeper`=GK, 나머지=팀 토큰).
3. **카메라 시야각**: `visible_area` 다각형 오버레이 렌더링.
4. **22명 추론**: 기본 실측 표시 + 옵션 포메이션 앵커 고스트 채우기 토글.
