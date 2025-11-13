"""
텔레그램 알림 모듈
"""
import os
import requests


def send_telegram_notification(message: str) -> bool:
    """
    텔레그램 알림 전송
    
    Args:
        message: 전송할 메시지 (HTML 형식 지원)
    
    Returns:
        bool: 전송 성공 여부
    """
    bot_token = os.environ.get('TELEGRAM_BOT_TOKEN')
    chat_id = os.environ.get('TELEGRAM_CHAT_ID')
    
    if not bot_token or not chat_id:
        print("⚠️ 텔레그램 설정이 없습니다. (TELEGRAM_BOT_TOKEN 또는 TELEGRAM_CHAT_ID)")
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
                    print("✅ 텔레그램 알림 전송 성공")
                except UnicodeEncodeError:
                    print("[SUCCESS] 텔레그램 알림 전송 성공")
                return True
            else:
                try:
                    print(f"❌ 텔레그램 알림 전송 실패: {result.get('description', '알 수 없는 오류')}")
                except UnicodeEncodeError:
                    print(f"[FAIL] 텔레그램 알림 전송 실패: {result.get('description', '알 수 없는 오류')}")
                return False
        else:
            try:
                print(f"❌ 텔레그램 API 오류: HTTP {response.status_code}")
                print(f"   응답: {response.text}")
            except UnicodeEncodeError:
                print(f"[ERROR] 텔레그램 API 오류: HTTP {response.status_code}")
                print(f"   응답: {response.text}")
            return False
            
    except requests.exceptions.Timeout:
        try:
            print("❌ 텔레그램 알림 전송 타임아웃")
        except UnicodeEncodeError:
            print("[ERROR] 텔레그램 알림 전송 타임아웃")
        return False
    except requests.exceptions.RequestException as e:
        try:
            print(f"❌ 텔레그램 알림 전송 오류: {e}")
        except UnicodeEncodeError:
            print(f"[ERROR] 텔레그램 알림 전송 오류: {e}")
        return False
    except Exception as e:
        try:
            print(f"❌ 텔레그램 알림 전송 예외: {e}")
        except UnicodeEncodeError:
            print(f"[ERROR] 텔레그램 알림 전송 예외: {e}")
        import traceback
        traceback.print_exc()
        return False

