"""
텔레그램 채팅방 ID 찾기 스크립트
"""
import requests
import sys
import io

# Windows 콘솔 인코딩 설정
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

BOT_TOKEN = "8518398236:AAEoGt4D_hwDa26cghbd3n4Lxcyra4xzgrg"

print("=" * 50)
print("텔레그램 채팅방 ID 찾기")
print("=" * 50)
print()

# getUpdates 호출
url = f"https://api.telegram.org/bot{BOT_TOKEN}/getUpdates"
print(f"API 호출 중: {url}")
print()

try:
    response = requests.get(url)
    data = response.json()
    
    if data.get('ok'):
        results = data.get('result', [])
        if results:
            print(f"[성공] {len(results)}개의 업데이트를 찾았습니다.\n")
            print("발견된 채팅방:")
            print("-" * 50)
            
            chat_ids = set()
            for update in results:
                if 'message' in update:
                    chat = update['message'].get('chat', {})
                    chat_id = chat.get('id')
                    chat_type = chat.get('type')
                    chat_title = chat.get('title') or chat.get('first_name') or chat.get('username') or '알 수 없음'
                    
                    if chat_id:
                        chat_ids.add((chat_id, chat_type, chat_title))
            
            for chat_id, chat_type, chat_title in chat_ids:
                print(f"  채팅방 ID: {chat_id}")
                print(f"  타입: {chat_type}")
                print(f"  이름: {chat_title}")
                print()
            
            print("-" * 50)
            print("\n[사용할 채팅방 ID]")
            if chat_ids:
                # 그룹 채팅이 있으면 그룹 우선, 없으면 첫 번째
                group_chats = [c for c in chat_ids if c[1] in ['group', 'supergroup']]
                if group_chats:
                    print(f"  {group_chats[0][0]}")
                    print(f"\n이 ID를 Vercel 환경 변수 TELEGRAM_SCHEDULE_CHAT_ID에 등록하세요!")
                else:
                    print(f"  {list(chat_ids)[0][0]}")
                    print(f"\n이 ID를 Vercel 환경 변수 TELEGRAM_SCHEDULE_CHAT_ID에 등록하세요!")
        else:
            print("[경고] 아직 메시지가 없습니다.")
            print()
            print("다음 단계를 따라주세요:")
            print("1. 텔레그램 앱에서 새 그룹을 생성하세요")
            print("2. 그룹에 봇을 추가하세요")
            print("3. 그룹 채팅에서 봇에게 메시지를 보내세요 (예: '테스트', '/start')")
            print("4. 그 다음 이 스크립트를 다시 실행하세요")
            print()
            print("또는 브라우저에서 다음 URL을 열어보세요:")
            print(f"   {url}")
    else:
        print(f"[오류] {data.get('description', '알 수 없는 오류')}")
        if 'error_code' in data:
            print(f"   에러 코드: {data.get('error_code')}")
            
except requests.exceptions.RequestException as e:
    print(f"[오류] 네트워크 오류: {e}")
except Exception as e:
    print(f"[오류] 오류 발생: {e}")
    import traceback
    traceback.print_exc()

print()
print("=" * 50)

