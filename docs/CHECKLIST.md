# 프로젝트 Phase별 실행 런북 (Execution Checklist)

본 문서는 UEFA 6대 서브 국면 및 5대 전술 플레이북 시스템 구현을 위한 표준 실행 런북입니다.

---

## 공통 라이프사이클 규칙
1. 작업 전 이슈 생성: `gh issue create --title "[Phase X] 기능명" --label "phase:X,type:feat"`
2. 브랜치 분기: `git checkout -b feat/#<이슈번호>-<기능명>`
3. 최소 단위 커밋 (이모지 절대 금지): `<type>(<scope>): <한글 요약>`
4. PR 생성 및 이슈 연동: `gh pr create --title "[Phase X] 기능명" --body "Closes #<이슈번호>"`
5. CI (Ruff + Pytest) 통과 확인 후 main 머지

---

## Phase 1. 기반 레이어 구축 (Config, Downloader, Storage)
- [ ] 이슈: `gh issue create --title "[Phase 1] 기반 레이어 구축 (config, downloader, storage)" --label "phase:1-base,type:feat"`
- [ ] 브랜치: `git checkout -b feat/#1-base-layer`
- [ ] 구현: `config.py`, `downloader.py` (캐시/감지), `storage.py` (6대 국면/플레이북 스키마)
- [ ] 검증: `uv run ruff check backend/`
- [ ] PR: `gh pr create --title "[Phase 1] 기반 레이어 구축" --body "Closes #1"`

---

## Phase 2. UEFA 6대 국면 포메이션 & 5대 플레이북 분석 엔진 (Analysis Engine)
- [ ] 이슈: `gh issue create --title "[Phase 2] UEFA 6대 국면 포메이션 및 5대 플레이북 분석 엔진 구축" --label "phase:2-analysis,type:feat"`
- [ ] 브랜치: `git checkout -b feat/#2-analysis-engine`
- [ ] 구현: 
  - `formation.py` (볼소유 3단계: 빌드업/전개/기회창출 + 볼미소유 3단계: 전방압박/미들블록/로우블록)
  - `playbook.py` (과부하컷백, 포켓3자, 하프스페이스언더랩, 딥라인브레이킹, 하이프레스속공)
  - `pressure.py` (압박 트랩 핫스팟 & 수비 라인)
  - `passes.py`, `zones.py`, `transitions.py`
- [ ] 검증: `uv run ruff check backend/`
- [ ] PR: `gh pr create --title "[Phase 2] 전술 분석 엔진 구축" --body "Closes #2"`

---

## Phase 3. 하이라이트 & 360 패스길 레이캐스팅 프레임 빌더 및 API
- [ ] 이슈: `gh issue create --title "[Phase 3] 하이라이트 추출, 360 패스길 레이캐스팅 및 FastAPI 연동" --label "phase:3-pipeline,type:feat"`
- [ ] 브랜치: `git checkout -b feat/#3-pipeline-and-api`
- [ ] 구현: `highlights.py`, `frames.py` (열린/차단 패스길 기하 레이캐스팅), `processing.py`, `cli.py`, `main.py`
- [ ] 검증: `uv run ruff check backend/`
- [ ] PR: `gh pr create --title "[Phase 3] 하이라이트 및 API 구축" --body "Closes #3"`

---

## Phase 4. 백엔드 테스트 구축
- [ ] 이슈: `gh issue create --title "[Phase 4] 백엔드 단위/통합 테스트 구축" --label "phase:4-tests,type:test"`
- [ ] 브랜치: `git checkout -b feat/#4-backend-tests`
- [ ] 구현: `tests/test_analysis.py`, `tests/test_highlights.py`, `tests/test_api.py`
- [ ] 검증: `uv run pytest backend/tests/ -v`
- [ ] PR: `gh pr create --title "[Phase 4] 백엔드 테스트 구축" --body "Closes #4"`

---

## Phase 5. React 18 + D3 동적 바둑판 프론트엔드 개편
- [ ] 이슈: `gh issue create --title "[Phase 5] React 18 + D3 6대 국면 모핑 바둑판 프론트엔드 구축" --label "phase:5-frontend,type:feat"`
- [ ] 브랜치: `git checkout -b feat/#5-frontend-board`
- [ ] 구현:
  - `TacticalBoard.tsx` (6대 국면 D3 모핑 애니메이션 + 5대 플레이북 화살표 + 360 패스길)
  - `MatchView.tsx` (6대 국면 전환 탭바 + 플레이북 카드 + 압박 트랩)
  - `HighlightView.tsx` (하이라이트 플레이어)
- [ ] 검증: `cd frontend; npm run test; npm run build`
- [ ] PR: `gh pr create --title "[Phase 5] 프론트엔드 동적 바둑판 구축" --body "Closes #5"`

---

## Phase 6. 종합 통합 검증 및 배포
- [ ] 이슈: `gh issue create --title "[Phase 6] 종합 통합 검증 및 E2E 테스트" --label "phase:6-deploy,type:chore"`
- [ ] 브랜치: `git checkout -b feat/#6-integration-and-deploy`
- [ ] 실행: `uv run python -m app.cli fetch && uv run python -m app.cli process --force`
- [ ] 검증: Docker Compose 및 UI 6대 국면 모핑/플레이북 E2E 검증
- [ ] PR: `gh pr create --title "[Phase 6] 종합 검증 완료" --body "Closes #6"`
