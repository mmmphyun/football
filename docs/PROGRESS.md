# 개발 진행 현황 (2026-08-26 v3 기준)

StatsBomb Open Data 기반 전술 분석 시스템 `IMPLEMENTATION_PLAN_V3.md` 진행 상황입니다.

---

## 단계별 진행 요약

| Phase | 주요 작업 내용 | 상태 |
| :--- | :--- | :---: |
| **Phase 0: 설계 및 정비** | 기존 3개 리포지토리 통합 분석, v3 명세서 및 런북 작성 | **완료** |
| **Phase 1: 기반 레이어** | `config.py`, `downloader.py` (다운로더/캐시), `storage.py` (CRUD) | **완료** |
| **Phase 2: 분석 엔진 리팩토링** | `common.py`, `formation.py`, `zones.py`, `passes.py`, `pressure.py`, `buildup.py`, `transitions.py`, `predict.py` | **완료** |
| **Phase 3: 하이라이트 & 파이프라인** | `highlights.py`, `frames.py`, `processing.py`, `cli.py`, `main.py` (FastAPI) | **완료** |
| **Phase 4: 백엔드 테스트** | 실제 축소 픽스처 기반 pytest 단위/통합 테스트 | **완료** |
| **Phase 5: 프론트엔드 구축** | React 18 + TS + Tailwind + D3 바둑판 피치, 전술 뷰, 하이라이트 플레이어 | **완료** |
| **Phase 6: 통합 검증 & 배포** | 실제 360 경기 데이터 fetch -> process -> UI 확인, Docker Compose | **완료** |

---

## 세부 구현 체크리스트

### Phase 1: 기반 레이어
- [x] `backend/app/config.py`: 피치 규격/상수/경로 설정
- [x] `backend/app/downloader.py`: `match_available_360` 감지 & `data/raw/` 캐싱
- [x] `backend/app/storage.py`: SQLite 스키마 및 CRUD 함수

### Phase 2: 분석 엔진 리팩토링
- [x] `backend/app/analysis/common.py`: 좌표계 불변(`attack_direction` 반전 금지), 시간 계산
- [x] `backend/app/analysis/formation.py`: 이벤트 기반 선수별 평균 좌표 및 포메이션 산출
- [x] `backend/app/analysis/zones.py`: 360 프레임 기반 12x8 존 점유율
- [x] `backend/app/analysis/passes.py`: 패스 네트워크 노드/상위 엣지 및 전진성
- [x] `backend/app/analysis/pressure.py`: 상대 진영(x>=40) PPDA 및 압박 강도
- [x] `backend/app/analysis/buildup.py`: 3분할 진영별 빌드업 시작점/전진 패스
- [x] `backend/app/analysis/transitions.py`: 턴오버 후 8초 이내 속공/지공 전환
- [x] `backend/app/analysis/predict.py`: +2초 단기 외삽(최대속도/경계 클램프, 앵커 인력)

### Phase 3: 하이라이트 & 파이프라인
- [x] `backend/app/highlights.py`: 골 및 xG>=0.25 슈팅 + 포제션 윈도우 클립
- [x] `backend/app/frames.py`: 360 위치/속도/앵커/시야각 프레임 생성
- [x] `backend/app/processing.py`: 매치 종합 분석 및 DB 적재 파이프라인
- [x] `backend/app/cli.py`: `fetch`, `process` CLI 명령어
- [x] `backend/app/main.py`: FastAPI REST API 5개 라우트 및 CORS

### Phase 4: 백엔드 테스트
- [x] `backend/tests/fixtures/`: 실제 축소 데이터 픽스처
- [x] `backend/tests/test_analysis.py`, `test_highlights.py`, `test_storage_pipeline.py`, `test_api.py`

### Phase 5: 프론트엔드 구축
- [x] Vite + React 18 + TS + Tailwind 기본 스캐폴딩
- [x] `src/lib/pitch.ts`, `predict.ts`, `interpolate.ts`
- [x] `TacticalBoard.tsx` (D3 SVG 바둑판 피치, 히트맵, 토큰, 고스트, 22명 추론)
- [x] `MatchView.tsx`, `HighlightView.tsx`, `App.tsx`

### Phase 6: 통합 검증 & 배포
- [x] `frontend/Dockerfile`, `frontend/nginx.conf` Nginx 리버스 프록시 및 정적 서빙 구성
- [x] `backend/Dockerfile`, `docker-compose.yml` 컨테이너 배포 명세 구성
- [x] 실제 StatsBomb 360 데이터 다운로드(`fetch`) 및 분석 적재(`process`) CLI 파이프라인 검증
- [x] 백엔드 및 프론트엔드 전체 단위/통합 테스트 및 프로덕션 빌드 통과

---

## 핵심 도메인 규칙 및 제약사항
1. **좌표계 불변**: 모든 이벤트는 항상 x=0 -> x=120 방향 고정 (좌표 반전 금지).
2. **360 데이터 매핑**: `event_uuid` 기반 매핑, 선수 식별 불가(`actor`=이벤트 수행자, `keeper`=GK, 나머지는 팀원/상대).
3. **시야각 폴리곤**: `visible_area` 내에서만 점유율 계산.
4. **22명 추론**: 미식별 선수는 포메이션 앵커 + 평균 위치 기반 가상 배치.
