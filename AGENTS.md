# 프로젝트 전용 에이전트 개발 규칙 (Project Agent Rules)

본 문서는 이 프로젝트에서 작업하는 모든 AI 에이전트가 반드시 준수해야 하는 최상위 라이프사이클 및 개발 규칙입니다.

---

## 1. 이모지(Emoji) 사용 절대 금지
- 사용자 응답, 코드, 주석, 커밋 메시지, PR 본문, 이슈 내용, 마크다운 문서 등 **모든 출력물에서 이모지 사용을 엄격히 금지**합니다.

---

## 2. GitHub 이슈 기반 브랜치 & PR 워크플로우
모든 작업은 반드시 다음 단계를 거쳐 진행합니다.

1. **이슈 우선 생성**:
   - 개발/수정 작업 시작 전 반드시 GitHub CLI로 이슈를 먼저 생성합니다.
   - 예시: `gh issue create --title "[Phase 1] 기반 레이어 구축" --label "phase:1-base,type:feat" --body "..."`
2. **이슈 연동 브랜치 분기**:
   - 이슈 번호를 포함한 브랜치를 생성하여 작업합니다.
   - 형식: `feat/#<이슈번호>-<기능명>` 또는 `fix/#<이슈번호>-<버그명>`
   - 예시: `git checkout -b feat/#1-base-layer`
3. **단위 작업 커밋**:
   - 기능 단위로 쪼개어 최소 작업 단위(Atomic Commit)로 커밋합니다.
4. **Pull Request 생성 및 이슈 연동**:
   - 작업 완료 후 `gh pr create`로 PR을 생성합니다.
   - PR 본문에 반드시 `Closes #<이슈번호>`를 명시하여 머지 시 이슈가 자동 클로즈되도록 합니다.
5. **CI 통과 확인 및 머지**:
   - GitHub Actions CI (Ruff + Pytest) 통과를 확인한 후 `main` 브랜치에 머지합니다.

---

## 3. 커밋 메시지 컨벤션
- **형식**: `<type>(<scope>): <한글 요약>` 또는 `<type>: <한글 요약>`
  - Type: `feat`, `fix`, `refactor`, `docs`, `test`, `style`, `perf`, `ci`, `chore`
  - Scope: 대상 모듈명 (선택 사항)
  - Subject: 마침표 없는 명확한 한글 요약
  - 예시: `feat(downloader): StatsBomb 360 대회 자동 감지 구현`
- **단일 라인 커밋 기본**: 특별한 배경 설명이 필요한 경우가 아니면 간결한 한 줄 커밋을 원칙으로 합니다.

---

## 4. 문서 관리 규칙
- 모든 설계, 스펙 가이드, 진행 현황 문서는 프로젝트 루트가 아닌 **`docs/` 디렉터리 내부**에서 관리합니다.
  - 명세서: `docs/IMPLEMENTATION_PLAN_V3.md`
  - 진행 현황: `docs/PROGRESS.md`
  - 스펙 예시: `docs/statsbomb_spec_examples/`

---

## 5. 도메인 및 코드 품질 가이드
- **StatsBomb 좌표계**: 모든 이벤트는 $x=0 \to 120$ 방향 고정 (좌표 반전 금지).
- **경기 시간**: `duration_min`은 실제 누적 분/초 기반 산출 (`(period - 1) * 3600` 오프셋 가산 금지).
- **코드 검사**: 백엔드 코드는 `ruff check backend/` 및 `pytest`를 상시 통과해야 합니다.
