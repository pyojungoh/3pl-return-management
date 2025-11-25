"""환경 변수 확인 스크립트"""
import os
from dotenv import load_dotenv

load_dotenv()

print("=" * 50)
print("환경 변수 확인")
print("=" * 50)
print()

# C/S 알림용
cs_bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
cs_chat_id = os.getenv('TELEGRAM_CHAT_ID')

print("[C/S 알림용]")
print(f"  TELEGRAM_BOT_TOKEN: {'설정됨' if cs_bot_token else '없음'}")
print(f"  TELEGRAM_CHAT_ID: {'설정됨' if cs_chat_id else '없음'}")
print()

# 스케쥴 알림용
schedule_bot_token = os.getenv('TELEGRAM_SCHEDULE_BOT_TOKEN')
schedule_chat_id = os.getenv('TELEGRAM_SCHEDULE_CHAT_ID')

print("[스케쥴 알림용]")
print(f"  TELEGRAM_SCHEDULE_BOT_TOKEN: {'설정됨' if schedule_bot_token else '없음'}")
if schedule_bot_token:
    print(f"    값: {schedule_bot_token[:20]}...")
print(f"  TELEGRAM_SCHEDULE_CHAT_ID: {'설정됨' if schedule_chat_id else '없음'}")
if schedule_chat_id:
    print(f"    값: {schedule_chat_id}")
print()

if not schedule_bot_token or not schedule_chat_id:
    print("[경고] 스케쥴 알림용 환경 변수가 설정되지 않았습니다!")
    print()
    print(".env 파일에 다음을 추가하세요:")
    print("TELEGRAM_SCHEDULE_BOT_TOKEN=8518398236:AAEoGt4D_hwDa26cghbd3n4Lxcyra4xzgrg")
    print("TELEGRAM_SCHEDULE_CHAT_ID=-5004696157")
else:
    print("[성공] 모든 환경 변수가 설정되어 있습니다!")

print()
print("=" * 50)


