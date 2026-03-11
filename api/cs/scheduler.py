"""
C/S 알림 스케줄러
- 일반 미처리 항목: 5분마다 알림
- 취소건: 1분마다 알림
- Vercel 서버리스: last_notification_at을 DB에 저장 (메모리는 요청마다 초기화됨)
"""
import threading
import time
from datetime import datetime, timezone, timedelta
from api.cs.routes_db import (
    get_pending_cs_requests,
    get_pending_cs_requests_by_issue_type,
    update_cs_last_notification,
)
from api.notifications.telegram import send_telegram_notification


def parse_datetime_for_compare(value) -> datetime:
    """DB의 last_notification_at 또는 created_at을 datetime으로 파싱 (비교용)"""
    if not value:
        return None
    kst = timezone(timedelta(hours=9))
    if isinstance(value, datetime):
        if value.tzinfo is None:
            return value.replace(tzinfo=kst)
        return value.astimezone(kst)
    s = str(value).strip()
    if not s:
        return None
    # 마이크로초 제거 (예: 2025-02-27 10:30:00.123456)
    s_clean = s.split('.')[0] if '.' in s else s
    if len(s_clean) >= 19:
        try:
            dt = datetime.strptime(s_clean[:19], '%Y-%m-%d %H:%M:%S')
            return dt.replace(tzinfo=kst)
        except ValueError:
            pass
        try:
            dt = datetime.strptime(s_clean[:19], '%Y-%m-%dT%H:%M:%S')
            return dt.replace(tzinfo=kst)
        except ValueError:
            pass
    return None


def convert_to_kst(value) -> str:
    """
    시간 값을 한국시간(KST) 문자열로 변환.
    value는 문자열 또는 datetime 객체가 될 수 있음.
    """
    if not value:
        return ''
    
    kst = timezone(timedelta(hours=9))
    
    try:
        dt = None
        if isinstance(value, datetime):
            dt = value
        else:
            datetime_str = str(value)
            formats = [
                '%Y-%m-%d %H:%M:%S',
                '%Y-%m-%d %H:%M:%S.%f',
                '%Y-%m-%dT%H:%M:%S',
                '%Y-%m-%dT%H:%M:%S.%f',
                '%Y-%m-%dT%H:%M:%S%z',
                '%Y-%m-%dT%H:%M:%S.%f%z',
            ]
            
            for fmt in formats:
                try:
                    dt = datetime.strptime(datetime_str, fmt)
                    break
                except ValueError:
                    continue
            
            if dt is None:
                # 문자열 파싱 실패 시 그대로 반환 (마이크로초 제거)
                return datetime_str.split('.')[0] if '.' in datetime_str else datetime_str
        
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=kst)
        else:
            dt = dt.astimezone(kst)
        
        return dt.strftime('%Y-%m-%d %H:%M:%S')
    except Exception as e:
        print(f"[경고] 시간 변환 오류: {e}, 원본: {value}")
        value_str = str(value)
        return value_str.split('.')[0] if '.' in value_str else value_str

def send_cs_notifications():
    """C/S 알림 전송 (스케줄러에서 호출)
    Returns:
        dict: {cancellation_count, general_count, cancellation_sent, general_sent}
    """
    stats = {'cancellation_count': 0, 'general_count': 0, 'cancellation_sent': 0, 'general_sent': 0}
    try:
        # KST 시간대 사용
        kst = timezone(timedelta(hours=9))
        current_time = datetime.now(kst)
        print(f"[정보] [스케줄러] 실행 시작: {current_time.strftime('%Y-%m-%d %H:%M:%S')}")
        
        # 취소건: 1분마다 알림
        cancellation_requests = get_pending_cs_requests_by_issue_type('취소')
        stats['cancellation_count'] = len(cancellation_requests)
        print(f"[정보] [스케줄러] 취소건 조회: {len(cancellation_requests)}건")
        
        for cs in cancellation_requests:
            cs_id = cs.get('id')
            if not cs_id:
                continue
            
            # 상태 확인 (처리완료/처리불가면 스킵)
            status = cs.get('status', '접수')
            if status not in ['접수']:
                continue
                
            # 마지막 알림 시간 확인 (1분 이내면 스킵) - DB에서 조회 (Vercel 서버리스 대응)
            last_time = parse_datetime_for_compare(cs.get('last_notification_at'))
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
            
            print(f"[정보] [스케줄러] 취소건 알림 전송: C/S #{cs_id}")
            if send_telegram_notification(message):
                stats['cancellation_sent'] += 1
            
            # 마지막 알림 시간 DB 업데이트 (Vercel 서버리스에서 다음 호출 시 유지)
            update_cs_last_notification(cs_id, current_time)
        
        # 일반 미처리 항목: 5분마다 알림 (취소건 제외)
        all_pending = get_pending_cs_requests()
        non_cancellation_requests = [cs for cs in all_pending if cs.get('issue_type') != '취소' and cs.get('status') == '접수']
        stats['general_count'] = len(non_cancellation_requests)
        print(f"[정보] [스케줄러] 일반 미처리 항목 조회: {len(non_cancellation_requests)}건")
        if len(non_cancellation_requests) > 0:
            print(f"   - C/S ID 목록: {[cs.get('id') for cs in non_cancellation_requests]}")
        
        for cs in non_cancellation_requests:
            cs_id = cs.get('id')
            if not cs_id:
                continue
            
            # 상태 확인 (처리완료/처리불가면 스킵)
            status = cs.get('status', '접수')
            if status not in ['접수']:
                continue
                
            # 마지막 알림 시간 확인 (5분 이내면 스킵) - DB에서 조회 (Vercel 서버리스 대응)
            last_time = parse_datetime_for_compare(cs.get('last_notification_at'))
            
            should_send = False
            
            if last_time:
                # 이전에 알림을 보낸 적이 있으면, 5분 이상 지났는지 확인
                time_diff = (current_time - last_time).total_seconds()
                print(f"[정보] [스케줄러] C/S #{cs_id}: 마지막 알림 시간 확인")
                print(f"   - 마지막 알림: {last_time.strftime('%Y-%m-%d %H:%M:%S') if hasattr(last_time, 'strftime') else last_time}")
                print(f"   - 현재 시간: {current_time.strftime('%Y-%m-%d %H:%M:%S')}")
                print(f"   - 경과 시간: {time_diff:.0f}초 ({time_diff/60:.1f}분)")
                
                if time_diff >= 300:  # 5분 이상 지났으면 알림 전송
                    should_send = True
                    print(f"[성공] [스케줄러] C/S #{cs_id}: 5분 이상 경과, 알림 전송")
                else:
                    print(f"[정보] [스케줄러] C/S #{cs_id}: 5분 미만 ({time_diff/60:.1f}분), 스킵 (다음 체크 대기)")
            else:
                # 첫 알림인 경우, 접수일로부터 1분 이상 지났는지 확인 (5분에서 1분으로 완화)
                created_at_str = cs.get('created_at', '')
                print(f"[정보] [스케줄러] C/S #{cs_id}: 첫 알림 체크, 접수일: {created_at_str}")
                
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
                            print(f"[정보] [스케줄러] C/S #{cs_id}: 접수일로부터 {time_since_creation:.0f}초 경과")
                            
                            if time_since_creation >= 60:  # 1분 이상 지났으면 알림 전송
                                should_send = True
                                print(f"[성공] [스케줄러] C/S #{cs_id}: 1분 이상 경과, 알림 전송")
                            else:
                                print(f"[정보] [스케줄러] C/S #{cs_id}: 1분 미만, 스킵 (다음 체크 대기)")
                        else:
                            # 파싱 실패 시에도 알림 전송 (안전장치)
                            should_send = True
                            print(f"[경고] [스케줄러] C/S #{cs_id}: 접수일 파싱 실패, 알림 전송 (안전장치)")
                    except Exception as e:
                        print(f"[경고] [스케줄러] 접수일 파싱 오류: {e}, C/S #{cs_id}")
                        # 오류 발생 시에도 알림 전송 (안전장치)
                        should_send = True
                else:
                    # created_at이 없으면 알림 전송 (안전장치)
                    should_send = True
                    print(f"[경고] [스케줄러] C/S #{cs_id}: 접수일 정보 없음, 알림 전송 (안전장치)")
            
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
            
            print(f"[정보] [스케줄러] 일반 미처리 항목 알림 전송: C/S #{cs_id}")
            if send_telegram_notification(message):
                stats['general_sent'] += 1
            
            # 마지막 알림 시간 DB 업데이트 (Vercel 서버리스에서 다음 호출 시 유지)
            update_cs_last_notification(cs_id, current_time)
            print(f"[성공] [스케줄러] C/S #{cs_id}: 마지막 알림 시간 DB 저장 완료: {current_time.strftime('%Y-%m-%d %H:%M:%S')}")
        
        return stats
            
    except Exception as e:
        print(f"[오류] C/S 알림 전송 오류: {e}")
        import traceback
        traceback.print_exc()
        return stats


def start_cs_notification_scheduler():
    """C/S 알림 스케줄러 시작 (백그라운드 스레드)"""
    import os
    is_vercel = os.environ.get('VERCEL') == '1'
    
    if is_vercel:
        print("[경고] [스케줄러] Vercel 환경 감지 - 백그라운드 스레드는 제한적일 수 있습니다.")
        print("   Vercel Cron Jobs를 사용하는 것을 권장합니다: /api/cs/check-notifications")
    
    def scheduler_loop():
        print("[정보] [스케줄러] 루프 시작 (백그라운드 스레드)")
        loop_count = 0
        while True:
            try:
                loop_count += 1
                if loop_count % 5 == 0:  # 5분마다 한 번씩 로그 출력
                    print(f"[정보] [스케줄러] 루프 실행 중... (실행 횟수: {loop_count})")
                elif loop_count == 1:
                    print(f"[정보] [스케줄러] 첫 실행: {loop_count}")
                send_cs_notifications()
            except Exception as e:
                print(f"[오류] [스케줄러] 루프 오류: {e}")
                import traceback
                traceback.print_exc()
            
            # 1분마다 실행 (취소건 체크)
            time.sleep(60)
    
    try:
        scheduler_thread = threading.Thread(target=scheduler_loop, daemon=True)
        scheduler_thread.start()
        print("[성공] [스케줄러] C/S 알림 스케줄러가 시작되었습니다.")
        print("   - 취소건: 1분마다 알림")
        print("   - 일반 항목: 첫 알림은 접수 후 1분, 이후 5분마다 알림")
        print(f"   - 스레드 상태: {'활성' if scheduler_thread.is_alive() else '비활성'}")
        
        # 스레드가 살아있는지 확인
        import time as time_module
        time_module.sleep(0.1)  # 잠시 대기
        if not scheduler_thread.is_alive():
            print("[경고] [스케줄러] 경고: 스레드가 즉시 종료되었습니다. Vercel 환경에서는 작동하지 않을 수 있습니다.")
    except Exception as e:
        print(f"[오류] [스케줄러] 스레드 시작 오류: {e}")
        import traceback
        traceback.print_exc()

