"""
스케쥴 알림 테스트 및 관리 API
"""
import os
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


@schedule_notifications_bp.route('/check-notifications', methods=['GET', 'POST'])
def check_notifications():
    """스케쥴 알림 체크 (Vercel Cron Jobs용)"""
    try:
        # Vercel Cron Jobs에서 호출하는 엔드포인트
        # 헤더에서 cron secret 확인 (선택사항, 보안 강화용)
        cron_secret = request.headers.get('Authorization')
        expected_secret = os.environ.get('CRON_SECRET')
        
        # CRON_SECRET이 설정되어 있으면 검증
        if expected_secret and cron_secret != f'Bearer {expected_secret}':
            print("⚠️ [스케쥴 Cron] 인증 실패: CRON_SECRET 불일치")
            return jsonify({
                'success': False,
                'message': 'Unauthorized'
            }), 401
        
        print("🔄 [스케쥴 Cron] 스케쥴 알림 체크 시작 (Vercel Cron Jobs)")
        
        # 스케줄러 함수 직접 호출
        from api.schedule_notifications.scheduler import send_schedule_notifications
        send_schedule_notifications()
        
        return jsonify({
            'success': True,
            'message': '스케쥴 알림 체크 완료'
        })
        
    except Exception as e:
        print(f'❌ 스케쥴 알림 체크 오류: {e}')
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'message': f'스케쥴 알림 체크 중 오류: {str(e)}'
        }), 500

