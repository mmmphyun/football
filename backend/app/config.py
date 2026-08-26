"""프로젝트 전역 상수 및 환경 설정 모듈."""

from pathlib import Path

# 피치 규격 (StatsBomb 좌표계: 길이 120m, 너비 80m 고정)
PITCH_LENGTH: float = 120.0
PITCH_WIDTH: float = 80.0

# 3분할 진영 X축 경계값 (단위: 미터)
# StatsBomb은 팀 공격 방향과 무관하게 항상 x=0(자진영 골라인) -> x=120(상대진영 골라인)으로 기록됨
DEFENSIVE_THIRD_X: float = 40.0
MIDDLE_THIRD_X: float = 80.0
ATTACKING_THIRD_X: float = 120.0

# 바둑판 피치 12x8 그리드 분할 (셀 크기 10m x 10m)
ZONES_X: int = 12
ZONES_Y: int = 8
ZONE_CELL_WIDTH: float = PITCH_LENGTH / ZONES_X  # 10.0m
ZONE_CELL_HEIGHT: float = PITCH_WIDTH / ZONES_Y  # 10.0m

# 하이라이트 클립 추출 임계값 및 시간 윈도우 (단위: 초)
MIN_HIGHLIGHT_XG: float = 0.25
PRE_WINDOW_SEC: float = 15.0
POST_WINDOW_SEC: float = 4.0
MAX_POSSESSION_WINDOW_SEC: float = 30.0

# 단기 외삽(+2초) 예측 엔진 상수
EXTRAPOLATION_TIME: float = 2.0
EXTRAPOLATION_MAX_SPEED: float = 8.0  # 축구 선수의 현실적인 최대 스프린트 속도 상한 (m/s)
EXTRAPOLATION_DECAY: float = 0.15  # 초당 속도 감쇠율 (선형 외삽의 오차 완화)

# StatsBomb Open Data 다운로더 설정
STATSBOMB_RAW_BASE_URL: str = "https://raw.githubusercontent.com/statsbomb/open-data/master/data"
MIN_MATCHES_360_FILTER: int = 30  # 유의미한 분석을 위한 최소 경기 수 기준

# 파일 시스템 경로
# 프로젝트 루트를 기준으로 data/ 디렉터리 위치 산출
BASE_DIR: Path = Path(__file__).resolve().parent.parent.parent
DATA_DIR: Path = BASE_DIR / "data"
RAW_DATA_DIR: Path = DATA_DIR / "raw"
DB_PATH: Path = DATA_DIR / "db.sqlite"
