# 프로젝트 Phase별 실행 체크리스트 (Execution Checklist & Runbook)

본 문서는 새 세션에서 각 Phase 작업을 시작할 때 에이전트와 개발자가 따라야 하는 표준 실행 절차 및 검증 체크리스트입니다.

---

## 작업 라이프사이클 공통 규칙
1. 작업 시작 전 반드시 GitHub 이슈를 먼저 생성합니다 (`gh issue create`).
2. 이슈 번호를 포함한 브랜치를 생성합니다 (`git checkout -b feat/#<이슈번호>-<기능명>`).
3. 최소 작업 단위(Atomic Commit)로 커밋합니다 (`<type>(<scope>): <한글 요약>`).
4. PR 생성 시 `Closes #<이슈번호>`를 본문에 명시합니다 (`gh pr create`).
5. GitHub Actions CI (Ruff + Pytest) 통과를 확인한 후 `main` 브랜치에 머지합니다.

---

## Phase 1. 기반 레이어 구축 (Config, Downloader, Storage)

### 1) 이슈 및 브랜치
```powershell
gh issue create --title "[Phase 1] 기반 레이어 구축 (config, downloader, storage)" --label "phase:1-base,type:feat" --body "기반 설정, StatsBomb 360 다운로더 및 디스크 캐시, SQLite 스토리지 레이어를 구축합니다."
git checkout -b feat/#1-base-layer
```

### 2) 개발 대상 파일
- [ ] `backend/app/config.py`: 피치 규격(120x80), 3분할 경계, 하이라이트 임계값, 외삽 상수
- [ ] `backend/app/downloader.py`: `competitions.json`의 `match_available_360` 기반 감지 & `data/raw/` 디스크 캐싱
- [ ] `backend/app/storage.py`: SQLite 스키마(competitions, matches, summaries, highlights, frames) 및 CRUD

### 3) 로컬 검증
```powershell
uv run ruff check backend/
uv run ruff format --check backend/
```

### 4) PR 및 머지
```powershell
gh pr create --title "[Phase 1] 기반 레이어 구축" --body "Closes #1"
# CI 통과 확인 후 main 머지
```

---

## Phase 2. 분석 엔진 8종 리팩토링 (Analysis Engine)

### 1) 이슈 및 브랜치
```powershell
gh issue create --title "[Phase 2] 8종 전술 분석 엔진 리팩토링" --label "phase:2-analysis,type:feat" --body "StatsBomb 실측 스키마 및 정규화 좌표계 기반 8종 전술 분석 모듈을 구현합니다."
git checkout -b feat/#2-analysis-engine
```

### 2) 개발 대상 파일
- [ ] `backend/app/analysis/common.py`: 좌표 정규화 유틸, 정상 경기 시간, 라인업 매핑
- [ ] `backend/app/analysis/formation.py`: 이벤트 참여 위치 기반 포메이션 평균 산출
- [ ] `backend/app/analysis/zones.py`: 360 프레임 매핑 및 12x8 그리드 점유율 집계
- [ ] `backend/app/analysis/passes.py`: 패스 네트워크 노드/상위 엣지(15개) 및 전진 진행도
- [ ] `backend/app/analysis/pressure.py`: 상대 진영(x >= 40) PPDA 및 분당 압박 강도
- [ ] `backend/app/analysis/buildup.py`: 3분할 시작 지점 및 전진 패스/캐리 집계
- [ ] `backend/app/analysis/transitions.py`: 공 회수 후 8초 이내 전환 속도 집계
- [ ] `backend/app/analysis/predict.py`: +2초 단기 외삽 엔진 (최대속도/경계 클램프, 앵커 인력)

### 3) 로컬 검증
```powershell
uv run ruff check backend/
```

### 4) PR 및 머지
```powershell
gh pr create --title "[Phase 2] 8종 전술 분석 엔진 리팩토링" --body "Closes #2"
```

---

## Phase 3. 하이라이트 & 프레임 파이프라인

### 1) 이슈 및 브랜치
```powershell
gh issue create --title "[Phase 3] 하이라이트 추출, 프레임 빌더 및 FastAPI 연동" --label "phase:3-pipeline,type:feat" --body "골/고xG 클립 윈도우 추출, 360 프레임 시퀀스 빌더, CLI 및 FastAPI 엔드포인트를 구현합니다."
git checkout -b feat/#3-pipeline-and-api
```

### 2) 개발 대상 파일
- [x] `backend/app/highlights.py`: 골 및 xG >= 0.25 슈팅 추출 + 포제션 윈도우 클리핑
- [x] `backend/app/frames.py`: 360 위치/속도/앵커/시야각 프레임 생성
- [x] `backend/app/processing.py`: 매치 종합 분석 및 DB 적재 파이프라인
- [x] `backend/app/cli.py`: fetch, process CLI 서브커맨드
- [x] `backend/app/main.py`: FastAPI 앱, CORS 미들웨어, REST API 5종

### 3) 로컬 검증
```powershell
uv run ruff check backend/
```

### 4) PR 및 머지
```powershell
gh pr create --title "[Phase 3] 하이라이트 추출 및 FastAPI 연동" --body "Closes #3"
```

---

## Phase 4. 백엔드 테스트 구축 (Testing)

### 1) 이슈 및 브랜치
```powershell
gh issue create --title "[Phase 4] 백엔드 단위 및 통합 테스트 구축" --label "phase:4-tests,type:test" --body "실제 축소 픽스처 기반 분석 엔진, 하이라이트, API 단위/통합 테스트를 작성합니다."
git checkout -b feat/#4-backend-tests
```

### 2) 개발 대상 파일
- [x] `backend/tests/fixtures/`: competitions, matches, events, lineups, three-sixty 축소 픽스처
- [x] `backend/tests/test_analysis.py`: 8종 분석 지표 단위 테스트
- [x] `backend/tests/test_highlights.py`: 윈도우 클리핑 및 프레임 빌더 테스트
- [x] `backend/tests/test_storage_pipeline.py`: 스토리지 CRUD 및 데이터 처리 파이프라인 테스트
- [x] `backend/tests/test_api.py`: FastAPI 엔드포인트 스모크 테스트

### 3) 로컬 검증
```powershell
uv run pytest backend/tests/ -v
uv run ruff check backend/
```

### 4) PR 및 머지
```powershell
gh pr create --title "[Phase 4] 백엔드 단위 및 통합 테스트 구축" --body "Closes #4"
```

---

## Phase 5. 프론트엔드 구축 (React + Vite + D3)

### 1) 이슈 및 브랜치
```powershell
gh issue create --title "[Phase 5] React 18 + D3 바둑판 프론트엔드 구축" --label "phase:5-frontend,type:feat" --body "TacticalBoard D3 SVG 바둑판 피치, 매치 전술 기조 뷰, 하이라이트 인터랙티브 플레이어를 구현합니다."
git checkout -b feat/#5-frontend-board
```

### 2) 개발 대상 파일
- [ ] `frontend/` 스캐폴딩: Vite + React 18 + TS + Tailwind CSS
- [ ] `frontend/src/lib/pitch.ts`, `predict.ts`, `interpolate.ts`: 좌표 변환, 외삽, 보간 엔진
- [ ] `frontend/src/components/TacticalBoard.tsx`: D3 SVG 바둑판, 히트맵, 토큰, 고스트, 시야각 오버레이, 22명 추론 토글
- [ ] `frontend/src/components/MatchView.tsx`: 8종 전술 기조 요약 카드 & 인터랙티브 바둑판
- [ ] `frontend/src/components/HighlightView.tsx`: 하이라이트 플레이어, 컨트롤러, 빈 상태 UI
- [ ] `frontend/src/App.tsx`: 대회/경기 선택 네비게이션 및 뷰 탭 전환

### 3) 로컬 검증
```powershell
cd frontend
npm run test
npm run build
```

### 4) PR 및 머지
```powershell
gh pr create --title "[Phase 5] React 18 + D3 바둑판 프론트엔드 구축" --body "Closes #5"
```

---

## Phase 6. 통합 검증 및 도커 배포 (Integration & Deploy)

### 1) 이슈 및 브랜치
```powershell
gh issue create --title "[Phase 6] 종합 통합 검증 및 Docker Compose 실행" --label "phase:6-deploy,type:chore" --body "실제 StatsBomb 데이터 다운로드/가공 및 Docker Compose 기반 E2E 동작을 검증합니다."
git checkout -b feat/#6-integration-and-deploy
```

### 2) 개발 대상 파일
- [ ] `docker-compose.yml`, `backend/Dockerfile`, `frontend/Dockerfile`, `frontend/nginx.conf`
- [ ] `docs/PROGRESS.md` 최종 완료 처리

### 3) 검증 절차
```powershell
uv run python -m app.cli fetch
uv run python -m app.cli process --force
docker compose up --build
```

### 4) PR 및 머지
```powershell
gh pr create --title "[Phase 6] 종합 통합 검증 및 배포 준비 완료" --body "Closes #6"
```
