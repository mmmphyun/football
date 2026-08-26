# StatsBomb 기반 축구 전술 분석 및 인터랙티브 바둑판 시각화 시스템

StatsBomb Open Data(이벤트 및 360 프리즈프레임)를 수집·분석하여 경기별 팀 전술 기조를 요약하고, 하이라이트 장면의 선수 움직임을 인터랙티브 바둑판(D3 SVG 피치)으로 시각화하는 웹 서비스입니다.

---

## 주요 기능

1. **경기별 전술 기조 요약 (Tactical Summary)**
   - 소유/비소유 상태별 포메이션 평균 위치
   - 12x8 그리드(10m 셀) 구역 점유 강도 히트맵
   - 패스 네트워크 (상위 15개 엣지, 노드 터치 수, 팀 전진도)
   - 상대 진영(x >= 40) 기준 PPDA 및 분당 압박 강도
   - 빌드업 방향 및 포제션 시작 3분할(Defensive/Middle/Final Third) 분석
   - 공 회수 후 8초 이내 역습 전환 속도

2. **하이라이트 인터랙티브 바둑판 재생기 (Highlight Tactical Board)**
   - 골 및 높은 기대득점(xG >= 0.25) 장면 자동 추출 및 포제션 윈도우 클리핑
   - 360 실측 위치 스냅샷 및 카메라 시야 다각형(visible_area) 오버레이
   - 선수별 속도 벡터 및 +2초 단기 외삽 고스트 토큰(Ghost Vector)
   - 22명 포메이션 앵커 추론 토글 (카메라 밖 미관측 선수 가상 배치)
   - 재생/일시정지, 재생 속도 조절(0.5x, 1x, 2x), 타임라인 스크러버

---

## 기술 스택

- **Backend**: Python 3.13+, FastAPI, SQLite, uv, Pydantic, pytest, Ruff
- **Frontend**: React 18, TypeScript, Vite, Tailwind CSS, D3.js (SVG 피치 렌더링)
- **Infrastructure**: Docker, Docker Compose, GitHub Actions CI

---

## 프로젝트 문서 안내

모든 기획, 도메인 스펙 가이드, 실행 체크리스트는 `docs/` 디렉터리 내에서 관리됩니다.

- [v3 통합 구현 명세서](docs/IMPLEMENTATION_PLAN_V3.md)
- [Phase별 실행 체크리스트 (런북)](docs/CHECKLIST.md)
- [진행 현황판](docs/PROGRESS.md)
- [StatsBomb 5대 핵심 스펙 및 예시 가이드](docs/statsbomb_spec_examples/README.md)
- [에이전트 개발 규칙](AGENTS.md)

---

## 로컬 개발 환경 설정

### 1. 백엔드 설정 (uv 기반)
```powershell
# 의존성 설치
uv pip install -r backend/requirements.txt

# 린트 검사
uv run ruff check backend/

# 테스트 실행
uv run pytest backend/tests/
```

### 2. 데이터 수집 및 가공 CLI
```powershell
# 360 보유 대회 자동 감지 및 다운로드
uv run python -m app.cli fetch

# 데이터 전술 분석 및 DB 적재
uv run python -m app.cli process
```

### 3. Docker Compose 전체 실행
```powershell
docker compose up --build
```
- Frontend: `http://localhost:3000`
- Backend API: `http://localhost:8000/docs`

---

## 라이선스 및 데이터 출처 고지

- **데이터 출처**: [StatsBomb Open Data](https://github.com/statsbomb/open-data)
- **데이터 라이선스**: Creative Commons Attribution 4.0 International License (CC BY 4.0)
- 본 프로젝트는 StatsBomb Open Data를 기반으로 제작되었으며, 라이선스 가이드라인에 따라 출처를 명시합니다.
