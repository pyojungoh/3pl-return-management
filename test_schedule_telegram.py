"""
스케쥴 텔레그램 알림 테스트 스크립트
"""
import requests
import os

BOT_TOKEN = "8518398236:AAEoGt4D_hwDa26cghbd3n4Lxcyra4xzgrg"
CHAT_ID = "-5004696157"  # 찾은 채팅방 ID

print("=" * 50)
print("스케쥴 텔레그램 알림 테스트")
print("=" * 50)
print()

message = """📅 <b>새로운 스케쥴 등록</b>

🏢 화주사: 테스트 화주사
📋 타입: 출고
📝 제목: 테스트 스케쥴
📅 기간: 2025-01-15 ~ 2025-01-20
📄 내용: 이것은 테스트 메시지입니다.

등록 시간: 2025-01-14 09:00:00"""

url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"

data = {
    "chat_id": CHAT_ID,
    "text": message,
    "parse_mode": "HTML"
}

print(f"봇 토큰: {BOT_TOKEN[:20]}...")
print(f"채팅방 ID: {CHAT_ID}")
print()
print("메시지 전송 중...")
print()

try:
    response = requests.post(url, json=data, timeout=10)
    
    if response.status_code == 200:
        result = response.json()
        if result.get('ok'):
            print("[성공] 텔레그램 메시지가 전송되었습니다!")
            print("텔레그램 그룹 'jjay 스케줄'을 확인해보세요.")
        else:
            print(f"[실패] {result.get('description', '알 수 없는 오류')}")
    else:
        print(f"[오류] HTTP {response.status_code}")
        print(f"응답: {response.text}")
        
except Exception as e:
    print(f"[오류] {e}")

print()
print("=" * 50)


