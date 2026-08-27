# 프로젝트 Phase별 실행 런북 (Execution Checklist)

본 문서는 새 세션에서 Phase별 작업을 진행할 때 에이전트와 개발자가 준수하는 표준 실행 체크리스트입니다.

---

## 공통 라이프사이클 규칙
1. 작업 전 이슈 생성: `gh issue create --title "[Phase X] 기능명" --label "phase:X,type:feat"`
2. 브랜치 분기: `git checkout -b feat/#<이슈번호>-<기능명>`
3. 최소 단위 커밋 (이모지 절대 금지): `<type>(<scope>): <한글 요약>`
4. PR 생성 및 이슈 연동: `gh pr create --title "[Phase X] 기능명" --body "Closes #<이슈번호>"`
5. CI (Ruff + Pytest) 통과 확인 후 main 머지

---

## Phase 1. 기반 레이어 구축 (Config, Downloader, Storage)
- [x] 이슈: `gh issue create --title "[Phase 1] 기반 레이어 구축 (config, downloader, storage)" --label "phase:1-base,type:feat"` (#38)
- [x] 브랜치: `git checkout -b feat/#38-base-layer`
- [x] 구현: `config.py`, `downloader.py` (캐시/감지), `storage.py` (3대 국면 스키마)
- [x] 검증: `uv run ruff check backend/` && `uv run pytest backend/`
- [x] PR: `gh pr create --title "[Phase 1] 기반 레이어 구축" --body "Closes #38"` (PR #39 Merged)

---

## Phase 2. 5대 인터랙티브 전술 분석 엔진 구축 (Analysis Engine)
- [x] 이슈: `gh issue create --title "[Phase 2] 3대 국면 포메이션 및 플레이북 분석 엔진 구축" --label "phase:2-analysis,type:feat"` (#41)
- [x] 브랜치: `git checkout -b feat/#41-analysis-engine`
- [x] 구현: 
  - `formation.py` (수비/빌드업/공격 3대 국면 대형 및 라인 높이/너비/길이)
  - `playbook.py` (시그니처 공격 패턴 TOP 3 시퀀스 추출)
  - `pressure.py` (압박 트랩 핫스팟 & 수비 라인)
  - `timeline.py` (시간대별 전술 슬라이스)
  - `passes.py`, `zones.py`, `transitions.py`
- [x] 검증: `uv run ruff check backend/` && `uv run pytest backend/`
- [x] PR: `gh pr create --title "[Phase 2] 전술 분석 엔진 구축" --body "Closes #41"` (PR #42 Merged)

---

## Phase 3. 하이라이트 & 360 패스길 프레임 빌더 및 API
- [x] 이슈: `gh issue create --title "[Phase 3] 하이라이트 추출, 360 패스길 빌더 및 FastAPI 연동" --label "phase:3-pipeline,type:feat"` (#43)
- [x] 브랜치: `git checkout -b feat/#43-pipeline-and-api`
- [x] 구현: `highlights.py`, `frames.py` (열린/차단된 패스길 레이캐스팅), `processing.py`, `cli.py`, `main.py`
- [x] 검증: `uv run ruff check backend/` && `uv run pytest backend/`
- [x] PR: `gh pr create --title "[Phase 3] 하이라이트 및 API 구축" --body "Closes #43"` (PR #44 Merged)

---

## Phase 4. 백엔드 테스트 구축
- [x] 이슈: `gh issue create --title "[Phase 4] 백엔드 단위/통합 테스트 구축" --label "phase:4-tests,type:test"` (#45)
- [x] 브랜치: `git checkout -b feat/#45-backend-tests`
- [x] 구현: `tests/fixtures/`, `tests/test_analysis.py`, `tests/test_highlights.py`, `tests/test_api.py`, `tests/test_storage_pipeline.py`
- [x] 검증: `uv run pytest backend/tests/ -v` && `uv run ruff check backend/`
- [x] PR: `gh pr create --title "[Phase 4] 백엔드 테스트 구축" --body "Closes #45"` (PR #46 Merged)

---

## Phase 5. React 18 + D3 동적 바둑판 프론트엔드 개편
- [x] 이슈: `gh issue create --title "[Phase 5] React 18 + D3 국면 모핑 바둑판 프론트엔드 구축" --label "phase:5-frontend,type:feat"` (#47)
- [x] 브랜치: `git checkout -b feat/#47-frontend-board`
- [x] 구현:
  - `TacticalBoard.tsx` (3대 국면 D3 모핑 애니메이션 + 플레이북 화살표 + 360 패스길)
  - `MatchView.tsx` (국면 전환 바 + 플레이북 카드 + 압박 트랩)
  - `HighlightView.tsx` (하이라이트 플레이어)
- [x] 검증: `cd frontend; npm run test; npm run build`
- [x] PR: `gh pr create --title "[Phase 5] 프론트엔드 동적 바둑판 구축" --body "Closes #47"` (PR #48 Merged)

---

## Phase 6. 종합 통합 검증 및 E2E 테스트
- [x] 이슈: `gh issue create --title "[Phase 6] 종합 통합 검증 및 E2E 테스트" --label "phase:6-deploy,type:chore"` (#49)
- [x] 브랜치: `git checkout -b feat/#49-integration-and-deploy`
- [x] 실행: `uv run python -m app.cli fetch && uv run python -m app.cli process --force`
- [x] 검증: 백엔드/프론트엔드 단위 및 E2E 빌드/테스트 전수 통과
- [ ] PR: `gh pr create --title "[Phase 6] 종합 검증 완료" --body "Closes #49"`
