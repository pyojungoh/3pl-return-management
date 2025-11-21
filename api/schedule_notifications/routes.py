"""
스케쥴 알림 테스트 및 관리 API
"""
from flask import Blueprint, request, jsonify
from datetime import datetime, timezone, timedelta
from api.schedule_notifications.telegram import send_schedule_notification

# Blueprint 생성
schedule_notifications_bp = Blueprint('schedule_notifications', __name__, url_prefix='/api/schedule-notifications')


@schedule_notifications_bp.route('/test', methods=['POST'])
def test_schedule_notification():
    """스케쥴 텔레그램 알림 테스트 (관리자용)"""
    try:
        # 텔레그램 알림 전송
        message = "🧪 <b>스케쥴 텔레그램 알림 테스트</b>\n\n"
        message += "이 메시지가 보이면 스케쥴 텔레그램 연동이 정상적으로 작동합니다! ✅\n\n"
        message += f"테스트 시간: {datetime.now(timezone(timedelta(hours=9))).strftime('%Y-%m-%d %H:%M:%S')}"
        
        success = send_schedule_notification(message)
        
        if success:
            return jsonify({
                'success': True,
                'message': '스케쥴 텔레그램 알림이 전송되었습니다. 텔레그램 앱을 확인해주세요.'
            })
        else:
            return jsonify({
                'success': False,
                'message': '스케쥴 텔레그램 알림 전송에 실패했습니다. 환경 변수 설정을 확인해주세요. (TELEGRAM_SCHEDULE_BOT_TOKEN, TELEGRAM_SCHEDULE_CHAT_ID)'
            }), 500
            
    except Exception as e:
        print(f'❌ 스케쥴 텔레그램 테스트 오류: {e}')
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'message': f'스케쥴 텔레그램 테스트 중 오류: {str(e)}'
        }), 500

