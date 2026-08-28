"""프로젝트 전역 상수 및 환경 설정 모듈."""

from pathlib import Path

# 피치 규격 (StatsBomb 좌표계: 길이 120m, 너비 80m 고정)
PITCH_LENGTH: float = 120.0
PITCH_WIDTH: float = 80.0

# 3분할 진영 X축 경계값 및 국면 전환 기준선 (단위: 미터)
# StatsBomb은 팀 공격 방향과 무관하게 항상 x=0(자진영 골라인) -> x=120(상대진영 골라인)으로 기록됨
DEFENSIVE_THIRD_X: float = 40.0
HALF_PITCH_X: float = 60.0  # 빌드업(x < 60.0)과 공격(x >= 60.0) 국면 분할 기준선
MIDDLE_THIRD_X: float = 80.0
ATTACKING_THIRD_X: float = 80.0  # 공격 3분의 1 진영(파이널 서드) 진입 기준선 (x >= 80.0)

# UEFA 6대 서브 국면 X축 경계값 (단위: 미터)
# 1. 볼 소유 국면 (In-Possession)
SUBPHASE_BUILDUP_MAX_X: float = 40.0  # 후방 빌드업 (x < 40.0)
SUBPHASE_PROGRESSION_MIN_X: float = 40.0  # 중원 전개 (40.0 <= x < 75.0)
SUBPHASE_PROGRESSION_MAX_X: float = 75.0
SUBPHASE_FINAL_THIRD_MIN_X: float = 75.0  # 기회 창출 / 파이널서드 (x >= 75.0)

# 2. 볼 미소유 국면 (Out-of-Possession / 수비 블록)
SUBPHASE_HIGH_PRESS_MIN_X: float = 65.0  # 전방 압박 블록 (수비 액션 x >= 65.0)
SUBPHASE_MID_BLOCK_MIN_X: float = 40.0  # 미들 블록 (수비 액션 40.0 <= x < 65.0)
SUBPHASE_MID_BLOCK_MAX_X: float = 65.0
SUBPHASE_LOW_BLOCK_MAX_X: float = 40.0  # 로우 블록 (수비 액션 x < 40.0)

# 페널티 박스 영역 좌표
BOX_X_MIN: float = 102.0
BOX_Y_MIN: float = 18.0
BOX_Y_MAX: float = 62.0

# 5대 시그니처 전술 플레이북 추출 기준 상수
# 1) 측면 과부하 & 컷백
CUTBACK_FLANK_X_MIN: float = 88.0
CUTBACK_FLANK_Y_TOP: float = 22.0
CUTBACK_FLANK_Y_BOTTOM: float = 58.0
CUTBACK_TARGET_X_MIN: float = 85.0
CUTBACK_TARGET_Y_MIN: float = 28.0
CUTBACK_TARGET_Y_MAX: float = 52.0

# 2) 포켓(Zone 14) 3자 연계 침투
POCKET_X_MIN: float = 75.0
POCKET_X_MAX: float = 95.0
POCKET_Y_MIN: float = 28.0
POCKET_Y_MAX: float = 52.0
THIRD_MAN_MAX_INTERVAL_SEC: float = 2.0

# 3) 하프스페이스 언더래핑 & 얼리크로스
HALFSPACE_X_MIN: float = 65.0
HALFSPACE_X_MAX: float = 88.0
HALFSPACE_Y_LEFT_MIN: float = 18.0
HALFSPACE_Y_LEFT_MAX: float = 30.0
HALFSPACE_Y_RIGHT_MIN: float = 50.0
HALFSPACE_Y_RIGHT_MAX: float = 62.0

# 4) 후방 딥 라인브레이킹 종패스
DEEP_LINEBREAK_START_MAX_X: float = 55.0
DEEP_LINEBREAK_END_MIN_X: float = 80.0
DEEP_LINEBREAK_MIN_DX: float = 30.0

# 5) 전방 압박 탈취 즉시 속공 슛
HIGHTURNOVER_RECOVERY_MIN_X: float = 75.0
HIGHTURNOVER_MAX_TIME_SEC: float = 5.0
HIGHTURNOVER_MAX_TOUCHES: int = 3

# 360 패스길 레이캐스팅 및 전술 판정 상수
PASS_LANE_BLOCK_RADIUS: float = 2.5  # 상대 수비수에 의한 패스길 차단 판정 반경 (미터)
PPDA_OPPONENT_HALF_X: float = 40.0  # PPDA 계산 시 상대 진영 수비 액션 X축 기준선 (x >= 40.0)
PRESSURE_TRAP_TIME_WINDOW_SEC: float = 3.0  # 압박 트랩 판정 시간 윈도우 (초)
PRESSURE_TRAP_MIN_PLAYERS: int = 2  # 압박 트랩 동시 참여 최소 수비수 수
TIMELINE_INTERVAL_MINUTES: int = 15  # 타임라인 전술 슬라이스 기본 구간 (분)

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
