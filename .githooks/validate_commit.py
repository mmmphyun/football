import sys
import re

commit_msg_filepath = sys.argv[1]

with open(commit_msg_filepath, "r", encoding="utf-8") as f:
    lines = [line.strip() for line in f.readlines() if not line.strip().startswith("#")]

if not lines:
    print("[ERROR] 커밋 메시지가 비어 있습니다.", file=sys.stderr)
    sys.exit(1)

full_text = "\n".join(lines)
title = lines[0]

def has_emoji(text: str) -> bool:
    for ch in text:
        code = ord(ch)
        if (
            0x1F600 <= code <= 0x1F64F or  # Emoticons
            0x1F300 <= code <= 0x1F5FF or  # Misc Symbols & Pictographs
            0x1F680 <= code <= 0x1F6FF or  # Transport & Map
            0x1F700 <= code <= 0x1F77F or  # Alchemical
            0x1F780 <= code <= 0x1F7FF or  # Geometric Shapes Ext
            0x1F800 <= code <= 0x1F8FF or  # Supplemental Arrows-C
            0x1F900 <= code <= 0x1F9FF or  # Supplemental Symbols & Pictographs
            0x1FA00 <= code <= 0x1FA6F or  # Chess Symbols
            0x1FA70 <= code <= 0x1FAFF or  # Symbols & Pictographs Ext-A
            0x2600 <= code <= 0x26FF or    # Misc symbols (stars, weather, etc.)
            0x2700 <= code <= 0x27BF       # Dingbats (checkmarks, crosses)
        ):
            return True
    return False

if has_emoji(full_text):
    print("[ERROR] 커밋 메시지에 이모지를 사용할 수 없습니다. (프로젝트 규칙 위반)", file=sys.stderr)
    sys.exit(1)

pattern = r"^(feat|fix|refactor|docs|test|style|perf|ci|chore)(\([a-zA-Z0-9_-]+\))?:\s+.+$"
if not re.match(pattern, title):
    print("[ERROR] 커밋 메시지 형식이 올바르지 않습니다.", file=sys.stderr)
    print("  올바른 형식 예시: feat(downloader): StatsBomb 360 대회 자동 감지 구현", file=sys.stderr)
    print("  지원 타입: feat, fix, refactor, docs, test, style, perf, ci, chore", file=sys.stderr)
    sys.exit(1)

sys.exit(0)
