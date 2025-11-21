"""
스케쥴 알림 스케줄러
- 등록 알림: 스케쥴 등록 시 즉시 (routes_db.py에서 처리)
- 시작일 전 알림: 시작일 - 1일, 오전 9시 (KST)
- 시작일 알림: 시작일, 오전 9시 (KST)
- 종료일 알림: 종료일, 오전 9시 (KST) - 단, 시작일 != 종료일인 경우만
"""
import threading
import time
from datetime import datetime, timezone, timedelta
from api.database.models import get_db_connection, USE_POSTGRESQL
from api.schedule_notifications.telegram import send_schedule_notification


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
                '%Y-%m-%d',  # 날짜만 있는 경우
            ]
            
            for fmt in formats:
                try:
                    dt = datetime.strptime(datetime_str.split(' ')[0], fmt)
                    break
                except ValueError:
                    continue
            
            if dt is None:
                return datetime_str.split('.')[0] if '.' in datetime_str else datetime_str
        
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=kst)
        else:
            dt = dt.astimezone(kst)
        
        return dt.strftime('%Y-%m-%d')
    except Exception as e:
        print(f"[경고] 시간 변환 오류: {e}, 원본: {value}")
        value_str = str(value)
        return value_str.split('.')[0] if '.' in value_str else value_str


# 마지막 알림 시간 추적 (중복 알림 방지)
last_notification_times = {}


def get_schedules_for_notification(notification_type: str) -> list:
    """
    알림 대상 스케쥴 조회
    
    Args:
        notification_type: 'before_start', 'start', 'end'
    
    Returns:
        List[Dict]: 알림 대상 스케쥴 리스트
    """
    kst = timezone(timedelta(hours=9))
    current_time = datetime.now(kst)
    today = current_time.date()
    tomorrow = today + timedelta(days=1)
    
    conn = get_db_connection()
    schedules = []
    
    try:
        if USE_POSTGRESQL:
            from psycopg2.extras import RealDictCursor
            cursor = conn.cursor(cursor_factory=RealDictCursor)
        else:
            import sqlite3
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
        
        if notification_type == 'before_start':
            # 시작일 전 알림: 내일이 시작일인 스케쥴
            query = '''
                SELECT id, company_name, title, start_date, end_date, 
                       event_description, request_note, schedule_type,
                       notification_sent_before_start
                FROM schedules 
                WHERE start_date = %s
                  AND (notification_sent_before_start IS NULL OR notification_sent_before_start = FALSE)
            ''' if USE_POSTGRESQL else '''
                SELECT id, company_name, title, start_date, end_date, 
                       event_description, request_note, schedule_type,
                       notification_sent_before_start
                FROM schedules 
                WHERE start_date = ?
                  AND (notification_sent_before_start IS NULL OR notification_sent_before_start = 0)
            '''
            target_date = tomorrow
        elif notification_type == 'start':
            # 시작일 알림: 오늘이 시작일인 스케쥴
            query = '''
                SELECT id, company_name, title, start_date, end_date, 
                       event_description, request_note, schedule_type,
                       notification_sent_start
                FROM schedules 
                WHERE start_date = %s
                  AND (notification_sent_start IS NULL OR notification_sent_start = FALSE)
            ''' if USE_POSTGRESQL else '''
                SELECT id, company_name, title, start_date, end_date, 
                       event_description, request_note, schedule_type,
                       notification_sent_start
                FROM schedules 
                WHERE start_date = ?
                  AND (notification_sent_start IS NULL OR notification_sent_start = 0)
            '''
            target_date = today
        elif notification_type == 'end':
            # 종료일 알림: 오늘이 종료일이고, 시작일 != 종료일인 스케쥴
            query = '''
                SELECT id, company_name, title, start_date, end_date, 
                       event_description, request_note, schedule_type,
                       notification_sent_end
                FROM schedules 
                WHERE end_date = %s
                  AND start_date != end_date
                  AND (notification_sent_end IS NULL OR notification_sent_end = FALSE)
            ''' if USE_POSTGRESQL else '''
                SELECT id, company_name, title, start_date, end_date, 
                       event_description, request_note, schedule_type,
                       notification_sent_end
                FROM schedules 
                WHERE end_date = ?
                  AND start_date != end_date
                  AND (notification_sent_end IS NULL OR notification_sent_end = 0)
            '''
            target_date = today
        else:
            return []
        
        date_str = target_date.strftime('%Y-%m-%d')
        cursor.execute(query, (date_str,))
        
        if USE_POSTGRESQL:
            rows = cursor.fetchall()
            schedules = [dict(row) for row in rows]
        else:
            rows = cursor.fetchall()
            schedules = []
            for row in rows:
                if hasattr(row, 'keys'):
                    schedules.append(dict(row))
                else:
                    schedules.append({
                        'id': row[0],
                        'company_name': row[1],
                        'title': row[2],
                        'start_date': row[3],
                        'end_date': row[4],
                        'event_description': row[5],
                        'request_note': row[6],
                        'schedule_type': row[7],
                        f'notification_sent_{notification_type}': row[8] if len(row) > 8 else None
                    })
        
        cursor.close()
        return schedules
        
    except Exception as e:
        print(f"[오류] 스케쥴 조회 오류: {e}")
        import traceback
        traceback.print_exc()
        return []
    finally:
        conn.close()


def mark_notification_sent(schedule_id: int, notification_type: str) -> bool:
    """
    알림 전송 플래그 업데이트
    
    Args:
        schedule_id: 스케쥴 ID
        notification_type: 'before_start', 'start', 'end'
    
    Returns:
        bool: 업데이트 성공 여부
    """
    conn = get_db_connection()
    
    try:
        cursor = conn.cursor()
        
        column_name = f'notification_sent_{notification_type}'
        
        if USE_POSTGRESQL:
            query = f'UPDATE schedules SET {column_name} = TRUE WHERE id = %s'
        else:
            query = f'UPDATE schedules SET {column_name} = 1 WHERE id = ?'
        
        cursor.execute(query, (schedule_id,))
        conn.commit()
        
        success = cursor.rowcount > 0
        cursor.close()
        return success
        
    except Exception as e:
        print(f"[오류] 알림 플래그 업데이트 오류: {e}")
        import traceback
        traceback.print_exc()
        if USE_POSTGRESQL:
            conn.rollback()
        return False
    finally:
        conn.close()


def send_schedule_notifications():
    """스케쥴 알림 전송 (스케줄러에서 호출)"""
    try:
        kst = timezone(timedelta(hours=9))
        current_time = datetime.now(kst)
        current_hour = current_time.hour
        current_minute = current_time.minute
        
        # 오전 9시에만 알림 전송 (9:00 ~ 9:59 사이)
        if current_hour != 9:
            return
        
        print(f"[정보] [스케쥴 스케줄러] 실행 시작: {current_time.strftime('%Y-%m-%d %H:%M:%S')}")
        
        # 1. 시작일 전 알림 (내일이 시작일)
        before_start_schedules = get_schedules_for_notification('before_start')
        print(f"[정보] [스케쥴 스케줄러] 시작일 전 알림 대상: {len(before_start_schedules)}건")
        
        for schedule in before_start_schedules:
            schedule_id = schedule.get('id')
            if not schedule_id:
                continue
            
            company_name = schedule.get('company_name', '알 수 없음')
            schedule_type = schedule.get('schedule_type', '')
            title = schedule.get('title', '')
            start_date = convert_to_kst(schedule.get('start_date', ''))
            end_date = convert_to_kst(schedule.get('end_date', ''))
            event_description = schedule.get('event_description', '')
            request_note = schedule.get('request_note', '')
            
            message = f"⏰ <b>스케쥴 시작일 하루 전 알림</b>\n\n"
            message += f"🏢 화주사: {company_name}\n"
            if schedule_type:
                message += f"📋 타입: {schedule_type}\n"
            message += f"📝 제목: {title}\n"
            message += f"📅 시작일: {start_date} (내일)\n"
            message += f"📅 종료일: {end_date}\n"
            if event_description:
                message += f"📄 내용: {event_description[:200]}{'...' if len(event_description) > 200 else ''}\n"
            if request_note:
                message += f"💬 요청사항: {request_note[:100]}{'...' if len(request_note) > 100 else ''}\n"
            
            print(f"[정보] [스케쥴 스케줄러] 시작일 전 알림 전송: 스케쥴 #{schedule_id}")
            success = send_schedule_notification(message)
            
            if success:
                mark_notification_sent(schedule_id, 'before_start')
        
        # 2. 시작일 알림 (오늘이 시작일)
        start_schedules = get_schedules_for_notification('start')
        print(f"[정보] [스케쥴 스케줄러] 시작일 알림 대상: {len(start_schedules)}건")
        
        for schedule in start_schedules:
            schedule_id = schedule.get('id')
            if not schedule_id:
                continue
            
            company_name = schedule.get('company_name', '알 수 없음')
            schedule_type = schedule.get('schedule_type', '')
            title = schedule.get('title', '')
            start_date = convert_to_kst(schedule.get('start_date', ''))
            end_date = convert_to_kst(schedule.get('end_date', ''))
            event_description = schedule.get('event_description', '')
            request_note = schedule.get('request_note', '')
            
            message = f"🚀 <b>스케쥴 시작일 알림</b>\n\n"
            message += f"🏢 화주사: {company_name}\n"
            if schedule_type:
                message += f"📋 타입: {schedule_type}\n"
            message += f"📝 제목: {title}\n"
            message += f"📅 시작일: {start_date} (오늘)\n"
            message += f"📅 종료일: {end_date}\n"
            if event_description:
                message += f"📄 내용: {event_description[:200]}{'...' if len(event_description) > 200 else ''}\n"
            if request_note:
                message += f"💬 요청사항: {request_note[:100]}{'...' if len(request_note) > 100 else ''}\n"
            
            print(f"[정보] [스케쥴 스케줄러] 시작일 알림 전송: 스케쥴 #{schedule_id}")
            success = send_schedule_notification(message)
            
            if success:
                mark_notification_sent(schedule_id, 'start')
        
        # 3. 종료일 알림 (오늘이 종료일이고, 시작일 != 종료일)
        end_schedules = get_schedules_for_notification('end')
        print(f"[정보] [스케쥴 스케줄러] 종료일 알림 대상: {len(end_schedules)}건")
        
        for schedule in end_schedules:
            schedule_id = schedule.get('id')
            if not schedule_id:
                continue
            
            company_name = schedule.get('company_name', '알 수 없음')
            schedule_type = schedule.get('schedule_type', '')
            title = schedule.get('title', '')
            start_date = convert_to_kst(schedule.get('start_date', ''))
            end_date = convert_to_kst(schedule.get('end_date', ''))
            event_description = schedule.get('event_description', '')
            request_note = schedule.get('request_note', '')
            
            message = f"🏁 <b>스케쥴 종료일 알림</b>\n\n"
            message += f"🏢 화주사: {company_name}\n"
            if schedule_type:
                message += f"📋 타입: {schedule_type}\n"
            message += f"📝 제목: {title}\n"
            message += f"📅 시작일: {start_date}\n"
            message += f"📅 종료일: {end_date} (오늘)\n"
            if event_description:
                message += f"📄 내용: {event_description[:200]}{'...' if len(event_description) > 200 else ''}\n"
            if request_note:
                message += f"💬 요청사항: {request_note[:100]}{'...' if len(request_note) > 100 else ''}\n"
            
            print(f"[정보] [스케쥴 스케줄러] 종료일 알림 전송: 스케쥴 #{schedule_id}")
            success = send_schedule_notification(message)
            
            if success:
                mark_notification_sent(schedule_id, 'end')
                
    except Exception as e:
        print(f"[오류] 스케쥴 알림 전송 오류: {e}")
        import traceback
        traceback.print_exc()


def start_schedule_notification_scheduler():
    """스케쥴 알림 스케줄러 시작 (백그라운드 스레드)"""
    import os
    is_vercel = os.environ.get('VERCEL') == '1'
    
    if is_vercel:
        print("[경고] [스케쥴 스케줄러] Vercel 환경 감지 - 백그라운드 스레드는 제한적일 수 있습니다.")
        print("   Vercel Cron Jobs를 사용하는 것을 권장합니다.")
    
    def scheduler_loop():
        print("[정보] [스케쥴 스케줄러] 루프 시작 (백그라운드 스레드)")
        loop_count = 0
        while True:
            try:
                loop_count += 1
                if loop_count % 60 == 0:  # 1시간마다 한 번씩 로그 출력
                    print(f"[정보] [스케쥴 스케줄러] 루프 실행 중... (실행 횟수: {loop_count})")
                send_schedule_notifications()
            except Exception as e:
                print(f"[오류] [스케쥴 스케줄러] 루프 오류: {e}")
                import traceback
                traceback.print_exc()
            
            # 1시간마다 실행
            time.sleep(3600)
    
    try:
        scheduler_thread = threading.Thread(target=scheduler_loop, daemon=True)
        scheduler_thread.start()
        print("[성공] [스케쥴 스케줄러] 스케쥴 알림 스케줄러가 시작되었습니다.")
        print("   - 시작일 전 알림: 시작일 - 1일, 오전 9시")
        print("   - 시작일 알림: 시작일, 오전 9시")
        print("   - 종료일 알림: 종료일, 오전 9시 (시작일 != 종료일인 경우만)")
        print(f"   - 스레드 상태: {'활성' if scheduler_thread.is_alive() else '비활성'}")
        
        # 스레드가 살아있는지 확인
        import time as time_module
        time_module.sleep(0.1)
        if not scheduler_thread.is_alive():
            print("[경고] [스케쥴 스케줄러] 경고: 스레드가 즉시 종료되었습니다. Vercel 환경에서는 작동하지 않을 수 있습니다.")
    except Exception as e:
        print(f"[오류] [스케쥴 스케줄러] 스레드 시작 오류: {e}")
        import traceback
        traceback.print_exc()

