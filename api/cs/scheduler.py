"""
C/S 알림 스케줄러
- 일반 미처리 항목: 5분마다 알림
- 취소건: 1분마다 알림
"""
import threading
import time
from datetime import datetime, timezone, timedelta
from api.cs.routes_db import get_pending_cs_requests, get_pending_cs_requests_by_issue_type
from api.notifications.telegram import send_telegram_notification


def convert_to_kst(datetime_str: str) -> str:
    """
    시간 문자열을 한국시간(KST)으로 변환
    데이터베이스에 저장된 시간은 이미 KST이므로, timezone 정보가 없으면 KST로 가정
    """
    if not datetime_str:
        return ''
    
    try:
        # 다양한 날짜 형식 파싱 시도
        formats = [
            '%Y-%m-%d %H:%M:%S',
            '%Y-%m-%d %H:%M:%S.%f',
            '%Y-%m-%dT%H:%M:%S',
            '%Y-%m-%dT%H:%M:%S.%f',
            '%Y-%m-%dT%H:%M:%S%z',
            '%Y-%m-%dT%H:%M:%S.%f%z',
        ]
        
        dt = None
        for fmt in formats:
            try:
                dt = datetime.strptime(datetime_str, fmt)
                break
            except ValueError:
                continue
        
        if dt is None:
            return datetime_str
        
        # timezone 정보가 있으면 변환, 없으면 이미 KST로 가정
        if dt.tzinfo is None:
            # timezone 정보가 없으면 이미 KST로 저장된 것으로 가정하고 그대로 반환
            # 또는 문자열에서 마이크로초 제거
            if '.' in datetime_str:
                return datetime_str.split('.')[0]
            return datetime_str
        else:
            # timezone 정보가 있으면 KST로 변환
            kst = timezone(timedelta(hours=9))
            kst_time = dt.astimezone(kst)
            return kst_time.strftime('%Y-%m-%d %H:%M:%S')
    except Exception as e:
        print(f"⚠️ 시간 변환 오류: {e}, 원본: {datetime_str}")
        # 오류 발생 시 원본 반환 (마이크로초 제거)
        if '.' in datetime_str:
            return datetime_str.split('.')[0]
        return datetime_str

# 마지막 알림 시간 추적 (중복 알림 방지)
last_notification_times = {}

def send_cs_notifications():
    """C/S 알림 전송 (스케줄러에서 호출)"""
    try:
        # KST 시간대 사용
        kst = timezone(timedelta(hours=9))
        current_time = datetime.now(kst)
        print(f"🕐 [스케줄러] 실행 시작: {current_time.strftime('%Y-%m-%d %H:%M:%S')}")
        
        # 취소건: 1분마다 알림
        cancellation_requests = get_pending_cs_requests_by_issue_type('취소')
        print(f"📊 [스케줄러] 취소건 조회: {len(cancellation_requests)}건")
        
        for cs in cancellation_requests:
            cs_id = cs.get('id')
            if not cs_id:
                continue
            
            # 상태 확인 (처리완료/처리불가면 스킵)
            status = cs.get('status', '접수')
            if status not in ['접수']:
                continue
                
            # 마지막 알림 시간 확인 (1분 이내면 스킵)
            last_time_key = f"cancellation_{cs_id}"
            last_time = last_notification_times.get(last_time_key)
            
            if last_time:
                time_diff = (current_time - last_time).total_seconds()
                if time_diff < 60:  # 1분 미만이면 스킵
                    continue
            
            # 알림 전송
            company_name = cs.get('company_name', '알 수 없음')
            issue_type = cs.get('issue_type', '취소')
            content = cs.get('content', '')
            content_preview = content[:100] + ('...' if len(content) > 100 else '')
            
            cs_id = cs.get('id', '')
            management_number = cs.get('management_number', '') or cs.get('generated_management_number', '')
            created_at_kst = convert_to_kst(cs.get('created_at', ''))
            message = f"🚨 <b>미처리 취소건 알림 (1분)</b>\n\n"
            message += f"📋 C/S 번호: #{cs_id}\n"
            if management_number:
                message += f"🔢 관리번호: {management_number}\n"
            message += f"화주사: {company_name}\n"
            message += f"유형: {issue_type}\n"
            message += f"내용: {content_preview}\n"
            message += f"접수일: {created_at_kst}"
            
            print(f"📤 [스케줄러] 취소건 알림 전송: C/S #{cs_id}")
            send_telegram_notification(message)
            
            # 마지막 알림 시간 업데이트
            last_notification_times[last_time_key] = current_time
        
        # 일반 미처리 항목: 5분마다 알림 (취소건 제외)
        all_pending = get_pending_cs_requests()
        non_cancellation_requests = [cs for cs in all_pending if cs.get('issue_type') != '취소' and cs.get('status') == '접수']
        print(f"📊 [스케줄러] 일반 미처리 항목 조회: {len(non_cancellation_requests)}건")
        if len(non_cancellation_requests) > 0:
            print(f"   - C/S ID 목록: {[cs.get('id') for cs in non_cancellation_requests]}")
            print(f"   - 저장된 알림 시간 키: {list(last_notification_times.keys())}")
        
        for cs in non_cancellation_requests:
            cs_id = cs.get('id')
            if not cs_id:
                continue
            
            # 상태 확인 (처리완료/처리불가면 스킵)
            status = cs.get('status', '접수')
            if status not in ['접수']:
                continue
                
            # 마지막 알림 시간 확인 (5분 이내면 스킵)
            last_time_key = f"general_{cs_id}"
            last_time = last_notification_times.get(last_time_key)
            
            should_send = False
            
            if last_time:
                # 이전에 알림을 보낸 적이 있으면, 5분 이상 지났는지 확인
                time_diff = (current_time - last_time).total_seconds()
                print(f"🔍 [스케줄러] C/S #{cs_id}: 마지막 알림 시간 확인")
                print(f"   - 마지막 알림: {last_time.strftime('%Y-%m-%d %H:%M:%S') if hasattr(last_time, 'strftime') else last_time}")
                print(f"   - 현재 시간: {current_time.strftime('%Y-%m-%d %H:%M:%S')}")
                print(f"   - 경과 시간: {time_diff:.0f}초 ({time_diff/60:.1f}분)")
                
                if time_diff >= 300:  # 5분 이상 지났으면 알림 전송
                    should_send = True
                    print(f"✅ [스케줄러] C/S #{cs_id}: 5분 이상 경과, 알림 전송")
                else:
                    print(f"⏸️ [스케줄러] C/S #{cs_id}: 5분 미만 ({time_diff/60:.1f}분), 스킵 (다음 체크 대기)")
            else:
                # 첫 알림인 경우, 접수일로부터 1분 이상 지났는지 확인 (5분에서 1분으로 완화)
                created_at_str = cs.get('created_at', '')
                print(f"🔍 [스케줄러] C/S #{cs_id}: 첫 알림 체크, 접수일: {created_at_str}")
                
                if created_at_str:
                    try:
                        # created_at을 datetime으로 파싱 (KST로 가정)
                        created_at = None
                        formats = [
                            '%Y-%m-%d %H:%M:%S',
                            '%Y-%m-%d %H:%M:%S.%f',
                            '%Y-%m-%dT%H:%M:%S',
                            '%Y-%m-%dT%H:%M:%S.%f',
                        ]
                        for fmt in formats:
                            try:
                                created_at = datetime.strptime(created_at_str.split('.')[0] if '.' in created_at_str else created_at_str, fmt)
                                # KST로 가정
                                created_at = created_at.replace(tzinfo=kst)
                                break
                            except ValueError:
                                continue
                        
                        if created_at:
                            # 접수일로부터 1분 이상 지났는지 확인 (5분에서 1분으로 완화)
                            time_since_creation = (current_time - created_at).total_seconds()
                            print(f"⏱️ [스케줄러] C/S #{cs_id}: 접수일로부터 {time_since_creation:.0f}초 경과")
                            
                            if time_since_creation >= 60:  # 1분 이상 지났으면 알림 전송
                                should_send = True
                                print(f"✅ [스케줄러] C/S #{cs_id}: 1분 이상 경과, 알림 전송")
                            else:
                                print(f"⏸️ [스케줄러] C/S #{cs_id}: 1분 미만, 스킵 (다음 체크 대기)")
                        else:
                            # 파싱 실패 시에도 알림 전송 (안전장치)
                            should_send = True
                            print(f"⚠️ [스케줄러] C/S #{cs_id}: 접수일 파싱 실패, 알림 전송 (안전장치)")
                    except Exception as e:
                        print(f"⚠️ [스케줄러] 접수일 파싱 오류: {e}, C/S #{cs_id}")
                        # 오류 발생 시에도 알림 전송 (안전장치)
                        should_send = True
                else:
                    # created_at이 없으면 알림 전송 (안전장치)
                    should_send = True
                    print(f"⚠️ [스케줄러] C/S #{cs_id}: 접수일 정보 없음, 알림 전송 (안전장치)")
            
            if not should_send:
                continue
            
            # 알림 전송
            company_name = cs.get('company_name', '알 수 없음')
            issue_type = cs.get('issue_type', '알 수 없음')
            content = cs.get('content', '')
            content_preview = content[:100] + ('...' if len(content) > 100 else '')
            
            cs_id = cs.get('id', '')
            management_number = cs.get('management_number', '') or cs.get('generated_management_number', '')
            created_at_kst = convert_to_kst(cs.get('created_at', ''))
            message = f"🚨 <b>미처리 C/S 알림 (5분)</b>\n\n"
            message += f"📋 C/S 번호: #{cs_id}\n"
            if management_number:
                message += f"🔢 관리번호: {management_number}\n"
            message += f"화주사: {company_name}\n"
            message += f"유형: {issue_type}\n"
            message += f"내용: {content_preview}\n"
            message += f"접수일: {created_at_kst}"
            
            print(f"📤 [스케줄러] 일반 미처리 항목 알림 전송: C/S #{cs_id}")
            send_telegram_notification(message)
            
            # 마지막 알림 시간 업데이트
            last_notification_times[last_time_key] = current_time
            print(f"💾 [스케줄러] C/S #{cs_id}: 마지막 알림 시간 저장 완료: {current_time.strftime('%Y-%m-%d %H:%M:%S')}")
            
    except Exception as e:
        print(f"❌ C/S 알림 전송 오류: {e}")
        import traceback
        traceback.print_exc()


def start_cs_notification_scheduler():
    """C/S 알림 스케줄러 시작 (백그라운드 스레드)"""
    def scheduler_loop():
        print("🔄 [스케줄러] 루프 시작")
        loop_count = 0
        while True:
            try:
                loop_count += 1
                if loop_count % 5 == 0:  # 5분마다 한 번씩 로그 출력
                    print(f"🔄 [스케줄러] 루프 실행 중... (실행 횟수: {loop_count})")
                send_cs_notifications()
            except Exception as e:
                print(f"❌ [스케줄러] 루프 오류: {e}")
                import traceback
                traceback.print_exc()
            
            # 1분마다 실행 (취소건 체크)
            time.sleep(60)
    
    scheduler_thread = threading.Thread(target=scheduler_loop, daemon=True)
    scheduler_thread.start()
    print("✅ C/S 알림 스케줄러가 시작되었습니다.")
    print("   - 취소건: 1분마다 알림")
    print("   - 일반 항목: 첫 알림은 접수 후 1분, 이후 5분마다 알림")

