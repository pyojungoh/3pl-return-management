"""
스케쥴 전용 텔레그램 알림 모듈
"""
import os
import requests


def send_schedule_notification(message: str) -> bool:
    """
    스케쥴 전용 텔레그램 알림 전송
    
    Args:
        message: 전송할 메시지 (HTML 형식 지원)
    
    Returns:
        bool: 전송 성공 여부
    """
    print("🔍 [스케쥴 텔레그램] 알림 전송 함수 호출됨")
    # 스케쥴 전용 봇 토큰만 사용 (C/S 알림 봇과 완전히 분리)
    bot_token = os.environ.get('TELEGRAM_SCHEDULE_BOT_TOKEN')
    chat_id = os.environ.get('TELEGRAM_SCHEDULE_CHAT_ID')  # 스케쥴 전용 채팅방
    
    print(f"🔑 [스케쥴 텔레그램] 환경변수 확인:")
    print(f"   - TELEGRAM_SCHEDULE_BOT_TOKEN: {'설정됨' if bot_token else '없음'} ({bot_token[:10] + '...' if bot_token and len(bot_token) > 10 else 'N/A'})")
    print(f"   - TELEGRAM_SCHEDULE_CHAT_ID: {'설정됨' if chat_id else '없음'} ({chat_id})")
    
    if not bot_token or not chat_id:
        print("⚠️ 스케쥴 텔레그램 설정이 없습니다. (TELEGRAM_SCHEDULE_BOT_TOKEN, TELEGRAM_SCHEDULE_CHAT_ID)")
        print("   스케쥴 알림은 C/S 알림과 별도의 봇과 채팅방을 사용해야 합니다.")
        return False
    
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    
    data = {
        "chat_id": chat_id,
        "text": message,
        "parse_mode": "HTML"
    }
    
    try:
        response = requests.post(url, json=data, timeout=10)
        
        if response.status_code == 200:
            result = response.json()
            if result.get('ok'):
                try:
                    print("✅ 스케쥴 텔레그램 알림 전송 성공")
                except UnicodeEncodeError:
                    print("[SUCCESS] 스케쥴 텔레그램 알림 전송 성공")
                return True
            else:
                try:
                    print(f"❌ 스케쥴 텔레그램 알림 전송 실패: {result.get('description', '알 수 없는 오류')}")
                except UnicodeEncodeError:
                    print(f"[FAIL] 스케쥴 텔레그램 알림 전송 실패: {result.get('description', '알 수 없는 오류')}")
                return False
        else:
            try:
                print(f"❌ 스케쥴 텔레그램 API 오류: HTTP {response.status_code}")
                print(f"   응답: {response.text}")
            except UnicodeEncodeError:
                print(f"[ERROR] 스케쥴 텔레그램 API 오류: HTTP {response.status_code}")
                print(f"   응답: {response.text}")
            return False
            
    except requests.exceptions.Timeout:
        try:
            print("❌ 스케쥴 텔레그램 알림 전송 타임아웃")
        except UnicodeEncodeError:
            print("[ERROR] 스케쥴 텔레그램 알림 전송 타임아웃")
        return False
    except requests.exceptions.RequestException as e:
        try:
            print(f"❌ 스케쥴 텔레그램 알림 전송 오류: {e}")
        except UnicodeEncodeError:
            print(f"[ERROR] 스케쥴 텔레그램 알림 전송 오류: {e}")
        return False
    except Exception as e:
        try:
            print(f"❌ 스케쥴 텔레그램 알림 전송 예외: {e}")
        except UnicodeEncodeError:
            print(f"[ERROR] 스케쥴 텔레그램 알림 전송 예외: {e}")
        import traceback
        traceback.print_exc()
        return False

