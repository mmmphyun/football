# 진행 체크포인트 (2026-08-18)

작업을 재개할 때 이 문서와 아래 "다음 단계"부터 이어가면 됩니다.

## 완료 (1단계: 스캐폴딩 ✅)

- 루트: `docker-compose.yml`, `README.md`, `.gitignore`, `.env.example`
- 백엔드 기본: `backend/Dockerfile`, `pyproject.toml`, `requirements.txt`, `app/config.py`(설정/상수), `app/storage.py`(SQLite 스키마·CRUD), `app/downloader.py`(StatsBomb GitHub 다운로드 + three-sixty 인덱스)
- 분석 엔진(작성 완료, 미검증): `app/analysis/common.py`, `formation.py`, `zones.py`, `passes.py`, `movement.py`, `pressure.py`, `buildup.py`, `transitions.py`, `predict.py`

## 남은 작업

### 2단계: 백엔드 마저 (다음 순서)
- [ ] `app/highlights.py` — 골/페널티/xG≥0.25 추출 + 포제션 기반 클립 윈도우
- [ ] `app/frames.py` — 하이라이트 재생 프레임(360 위치·속도·앵커, 비360 폴백)
- [ ] `app/processing.py` — `analyze_match()` 파이프라인 조립 (요약+하이라이트+프레임 저장)
- [ ] `app/cli.py` — `fetch`/`process` 서브커맨드 (360 우선 대회 자동 감지, 멱등 처리, `--force`)
- [ ] `app/main.py` — FastAPI 앱 + CORS + API 5종

### 3단계: 테스트
- [ ] `backend/tests/` — 합성 픽스처(events/lineups/three-sixty) + 윈도우·점유·패스·외삽·API 테스트

### 4단계: 프론트엔드
- [ ] Vite + React + TS + Tailwind + D3 스캐폴드, `src/lib/pitch.ts`(좌표 변환)·`predict.ts`·`interpolate.ts`
- [ ] `TacticalBoard.tsx`(바둑판 보드), `MatchView.tsx`(전술 기조), `HighlightView.tsx`(재생기+고스트), `App.tsx`
- [ ] 프론트 테스트(Vitest)

### 5단계: 검증
- [ ] 의존성 설치(pip/npm), pytest/vitest 통과
- [ ] 실제 데이터 fetch → process → API/UI 확인 (네트워크 승인 필요)

## 핵심 결정 (재개 시 참고)

- 대회 선택: three-sixty 디렉토리(GitHub API) 보유 + `MIN_MATCHES`(기본 30) 충족 최신 대회 우선, `COMPETITION_ID`/`SEASON_ID` 오버라이드
- 클립 윈도우: 포제션 첫 이벤트(골 30초/슈팅 15초 상한) ~ 이벤트 후 다음 이벤트(최대 4초)
- 예측: 상수속도 외삽(최대속도 8m/s 클램프 → 경계 클램프 → 앵커 당김 0.15/s), 360 전용, 프론트가 고스트 렌더
- 그리드 기본 12×8 (8×8/16×12 토글), 프레임 보간은 프론트 담당

## 참고 사항

- Windows에서 `apply_patch` 배치 래퍼가 멀티라인 인자를 깨뜨려 사용 불가 → 파일 작성은 PowerShell `[System.IO.File]::WriteAllText` 사용
- 데이터 출처: statsbomb/open-data (CC BY 4.0, README에 고지 완료)