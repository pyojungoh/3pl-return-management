"""
C/S 접수 관리 API 라우트
"""
from flask import Blueprint, request, jsonify, Response
from api.database.models import (
    get_db_connection,
    USE_POSTGRESQL
)
from datetime import datetime, timezone, timedelta
import csv
import io
import os
from urllib.parse import quote

# 한국 시간대 (KST = UTC+9)
KST = timezone(timedelta(hours=9))

def get_kst_now():
    """현재 한국 시간 반환"""
    return datetime.now(KST)

# 텔레그램 알림 모듈 (선택적 import - 없어도 작동)
try:
    from api.notifications.telegram import send_telegram_notification
except ImportError:
    def send_telegram_notification(message: str) -> bool:
        print(f"⚠️ 텔레그램 알림 모듈을 찾을 수 없습니다. 메시지: {message}")
        return False

# Blueprint 생성
cs_bp = Blueprint('cs', __name__, url_prefix='/api/cs')

if USE_POSTGRESQL:
    from psycopg2.extras import RealDictCursor


def create_cs_request(company_name: str, username: str, date: str, month: str, issue_type: str, content: str, management_number: str = None, customer_name: str = None) -> int:
    """C/S 접수 생성"""
    conn = get_db_connection()
    
    # 한국 시간으로 현재 시간 저장
    kst_now = get_kst_now()
    
    if USE_POSTGRESQL:
        cursor = conn.cursor()
        try:
            cursor.execute('''
                INSERT INTO customer_service (company_name, username, date, month, issue_type, content, management_number, customer_name, status, created_at, updated_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, '접수', %s, %s)
                RETURNING id
            ''', (company_name, username, date, month, issue_type, content, management_number, customer_name, kst_now, kst_now))
            cs_id = cursor.fetchone()[0]
            conn.commit()
            print(f"✅ C/S 접수 생성 성공: ID {cs_id}, 화주사: {company_name}, 유형: {issue_type}")
            return cs_id
        except Exception as e:
            print(f"❌ C/S 접수 생성 오류: {e}")
            conn.rollback()
            return None
        finally:
            cursor.close()
            conn.close()
    else:
        cursor = conn.cursor()
        try:
            cursor.execute('''
                INSERT INTO customer_service (company_name, username, date, month, issue_type, content, management_number, customer_name, status, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, '접수', ?, ?)
            ''', (company_name, username, date, month, issue_type, content, management_number, customer_name, kst_now, kst_now))
            cs_id = cursor.lastrowid
            conn.commit()
            print(f"✅ C/S 접수 생성 성공: ID {cs_id}, 화주사: {company_name}, 유형: {issue_type}")
            return cs_id
        except Exception as e:
            print(f"❌ C/S 접수 생성 오류: {e}")
            return None
        finally:
            conn.close()


def get_cs_requests(company_name: str = None, role: str = '화주사', month: str = None) -> list:
    """C/S 접수 목록 조회"""
    conn = get_db_connection()
    
    if USE_POSTGRESQL:
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        try:
            if role == '관리자':
                if company_name:
                    # 관리자 모드에서 특정 화주사 필터링
                    if month:
                        cursor.execute('''
                            SELECT * FROM customer_service
                            WHERE company_name = %s AND month = %s
                            ORDER BY created_at DESC
                        ''', (company_name, month))
                    else:
                        cursor.execute('''
                            SELECT * FROM customer_service
                            WHERE company_name = %s
                            ORDER BY created_at DESC
                        ''', (company_name,))
                else:
                    # 관리자 모드에서 전체 조회
                    if month:
                        cursor.execute('''
                            SELECT * FROM customer_service
                            WHERE month = %s
                            ORDER BY created_at DESC
                        ''', (month,))
                    else:
                        cursor.execute('''
                            SELECT * FROM customer_service
                            ORDER BY created_at DESC
                        ''')
            else:
                if month:
                    cursor.execute('''
                        SELECT * FROM customer_service
                        WHERE company_name = %s AND month = %s
                        ORDER BY created_at DESC
                    ''', (company_name, month))
                else:
                    cursor.execute('''
                        SELECT * FROM customer_service
                        WHERE company_name = %s
                        ORDER BY created_at DESC
                    ''', (company_name,))
            
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
        finally:
            cursor.close()
            conn.close()
    else:
        import sqlite3
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        try:
            if role == '관리자':
                if company_name:
                    # 관리자 모드에서 특정 화주사 필터링
                    if month:
                        cursor.execute('''
                            SELECT id, company_name, username, date, month, issue_type, content, 
                                   management_number, generated_management_number, customer_name, status, 
                                   admin_message, processor, processed_at, created_at, updated_at
                            FROM customer_service
                            WHERE company_name = ? AND month = ?
                            ORDER BY created_at DESC
                        ''', (company_name, month))
                    else:
                        cursor.execute('''
                            SELECT id, company_name, username, date, month, issue_type, content, 
                                   management_number, generated_management_number, customer_name, status, 
                                   admin_message, processor, processed_at, created_at, updated_at
                            FROM customer_service
                            WHERE company_name = ?
                            ORDER BY created_at DESC
                        ''', (company_name,))
                else:
                    # 관리자 모드에서 전체 조회
                    if month:
                        cursor.execute('''
                            SELECT id, company_name, username, date, month, issue_type, content, 
                                   management_number, generated_management_number, customer_name, status, 
                                   admin_message, processor, processed_at, created_at, updated_at
                            FROM customer_service
                            WHERE month = ?
                            ORDER BY created_at DESC
                        ''', (month,))
                    else:
                        cursor.execute('''
                            SELECT id, company_name, username, date, month, issue_type, content, 
                                   management_number, generated_management_number, customer_name, status, 
                                   admin_message, processor, processed_at, created_at, updated_at
                            FROM customer_service
                            ORDER BY created_at DESC
                        ''')
            else:
                if month:
                    cursor.execute('''
                        SELECT id, company_name, username, date, month, issue_type, content, 
                               management_number, generated_management_number, customer_name, status, 
                               admin_message, processor, processed_at, created_at, updated_at
                        FROM customer_service
                        WHERE company_name = ? AND month = ?
                        ORDER BY created_at DESC
                    ''', (company_name, month))
                else:
                    cursor.execute('''
                        SELECT id, company_name, username, date, month, issue_type, content, 
                               management_number, generated_management_number, customer_name, status, 
                               admin_message, processor, processed_at, created_at, updated_at
                        FROM customer_service
                        WHERE company_name = ?
                        ORDER BY created_at DESC
                    ''', (company_name,))
            
            rows = cursor.fetchall()
            result = []
            for row in rows:
                result.append({
                    'id': row['id'],
                    'company_name': row['company_name'] or '',
                    'username': row['username'] or '',
                    'date': row['date'] or '',
                    'month': row['month'] or '',
                    'issue_type': row['issue_type'] or '',
                    'content': row['content'] or '',
                    'management_number': row['management_number'] or '',
                    'generated_management_number': row['generated_management_number'] or '',
                    'customer_name': row.get('customer_name') or '',
                    'status': row['status'] or '접수',
                    'admin_message': row['admin_message'] or '',
                    'processor': row['processor'] or '',
                    'processed_at': str(row['processed_at']) if row['processed_at'] else '',
                    'created_at': str(row['created_at']) if row['created_at'] else '',
                    'updated_at': str(row['updated_at']) if row['updated_at'] else ''
                })
            return result
        finally:
            conn.close()


def update_cs_status(cs_id: int, status: str, admin_message: str = None, processor: str = None) -> bool:
    """C/S 접수 상태 업데이트 (관리자용)"""
    conn = get_db_connection()
    
    # 한국 시간으로 처리 시간 저장
    processed_at = get_kst_now() if status in ['처리완료', '처리불가'] else None
    updated_at = get_kst_now()
    
    if USE_POSTGRESQL:
        cursor = conn.cursor()
        try:
            if status == '접수':
                cursor.execute('''
                    UPDATE customer_service
                    SET status = %s, admin_message = %s, processor = NULL, processed_at = NULL, updated_at = %s
                    WHERE id = %s
                ''', (status, admin_message, updated_at, cs_id))
                conn.commit()
                return cursor.rowcount > 0
            if admin_message and processor:
                cursor.execute('''
                    UPDATE customer_service
                    SET status = %s, admin_message = %s, processor = %s, processed_at = %s, updated_at = %s
                    WHERE id = %s
                ''', (status, admin_message, processor, processed_at, updated_at, cs_id))
            elif admin_message:
                cursor.execute('''
                    UPDATE customer_service
                    SET status = %s, admin_message = %s, processed_at = %s, updated_at = %s
                    WHERE id = %s
                ''', (status, admin_message, processed_at, updated_at, cs_id))
            elif processor:
                cursor.execute('''
                    UPDATE customer_service
                    SET status = %s, processor = %s, processed_at = %s, updated_at = %s
                    WHERE id = %s
                ''', (status, processor, processed_at, updated_at, cs_id))
            else:
                cursor.execute('''
                    UPDATE customer_service
                    SET status = %s, processed_at = %s, updated_at = %s
                    WHERE id = %s
                ''', (status, processed_at, updated_at, cs_id))
            conn.commit()
            return cursor.rowcount > 0
        except Exception as e:
            print(f"❌ C/S 상태 업데이트 오류: {e}")
            conn.rollback()
            return False
        finally:
            cursor.close()
            conn.close()
    else:
        cursor = conn.cursor()
        try:
            if status == '접수':
                cursor.execute('''
                    UPDATE customer_service
                    SET status = ?, admin_message = ?, processor = NULL, processed_at = NULL, updated_at = ?
                    WHERE id = ?
                ''', (status, admin_message, updated_at, cs_id))
                conn.commit()
                return cursor.rowcount > 0
            if admin_message and processor:
                cursor.execute('''
                    UPDATE customer_service
                    SET status = ?, admin_message = ?, processor = ?, processed_at = ?, updated_at = ?
                    WHERE id = ?
                ''', (status, admin_message, processor, processed_at, updated_at, cs_id))
            elif admin_message:
                cursor.execute('''
                    UPDATE customer_service
                    SET status = ?, admin_message = ?, processed_at = ?, updated_at = ?
                    WHERE id = ?
                ''', (status, admin_message, processed_at, updated_at, cs_id))
            elif processor:
                cursor.execute('''
                    UPDATE customer_service
                    SET status = ?, processor = ?, processed_at = ?, updated_at = ?
                    WHERE id = ?
                ''', (status, processor, processed_at, updated_at, cs_id))
            else:
                cursor.execute('''
                    UPDATE customer_service
                    SET status = ?, processed_at = ?, updated_at = ?
                    WHERE id = ?
                ''', (status, processed_at, updated_at, cs_id))
            conn.commit()
            return cursor.rowcount > 0
        except Exception as e:
            print(f"❌ C/S 상태 업데이트 오류: {e}")
            return False
        finally:
            conn.close()


def delete_cs_request(cs_id: int) -> bool:
    """C/S 접수 삭제 (관리자용)"""
    conn = get_db_connection()
    
    if USE_POSTGRESQL:
        cursor = conn.cursor()
        try:
            cursor.execute('DELETE FROM customer_service WHERE id = %s', (cs_id,))
            conn.commit()
            return cursor.rowcount > 0
        except Exception as e:
            print(f"❌ C/S 삭제 오류: {e}")
            conn.rollback()
            return False
        finally:
            cursor.close()
            conn.close()
    else:
        cursor = conn.cursor()
        try:
            cursor.execute('DELETE FROM customer_service WHERE id = ?', (cs_id,))
            conn.commit()
            return cursor.rowcount > 0
        except Exception as e:
            print(f"❌ C/S 삭제 오류: {e}")
            return False
        finally:
            conn.close()

def update_generated_management_number(cs_id: int, generated_management_number: str) -> bool:
    """C/S 접수 생성된 관리번호 업데이트 (관리자용)"""
    conn = get_db_connection()
    
    # 한국 시간으로 업데이트 시간 저장
    updated_at = get_kst_now()
    
    if USE_POSTGRESQL:
        cursor = conn.cursor()
        try:
            cursor.execute('''
                UPDATE customer_service
                SET generated_management_number = %s, updated_at = %s
                WHERE id = %s
            ''', (generated_management_number, updated_at, cs_id))
            conn.commit()
            return cursor.rowcount > 0
        except Exception as e:
            print(f"❌ C/S 생성된 관리번호 업데이트 오류: {e}")
            conn.rollback()
            return False
        finally:
            cursor.close()
            conn.close()
    else:
        cursor = conn.cursor()
        try:
            cursor.execute('''
                UPDATE customer_service
                SET generated_management_number = ?, updated_at = ?
                WHERE id = ?
            ''', (generated_management_number, updated_at, cs_id))
            conn.commit()
            return cursor.rowcount > 0
        except Exception as e:
            print(f"❌ C/S 생성된 관리번호 업데이트 오류: {e}")
            return False
        finally:
            conn.close()


def update_customer_name(cs_id: int, customer_name: str) -> bool:
    """C/S 접수 고객명 업데이트 (관리자용)"""
    conn = get_db_connection()
    
    # 한국 시간으로 업데이트 시간 저장
    updated_at = get_kst_now()
    
    if USE_POSTGRESQL:
        cursor = conn.cursor()
        try:
            cursor.execute('''
                UPDATE customer_service
                SET customer_name = %s, updated_at = %s
                WHERE id = %s
            ''', (customer_name, updated_at, cs_id))
            conn.commit()
            return cursor.rowcount > 0
        except Exception as e:
            print(f"❌ C/S 고객명 업데이트 오류: {e}")
            conn.rollback()
            return False
        finally:
            cursor.close()
            conn.close()
    else:
        cursor = conn.cursor()
        try:
            cursor.execute('''
                UPDATE customer_service
                SET customer_name = ?, updated_at = ?
                WHERE id = ?
            ''', (customer_name, updated_at, cs_id))
            conn.commit()
            return cursor.rowcount > 0
        except Exception as e:
            print(f"❌ C/S 고객명 업데이트 오류: {e}")
            return False
        finally:
            conn.close()


def fetch_cs_issue_type_for_request(cs_id: int):
    """접수 건이 있으면 issue_type(빈 문자열 가능), 없으면 None."""
    conn = get_db_connection()
    if USE_POSTGRESQL:
        cursor = conn.cursor()
        try:
            cursor.execute('SELECT issue_type FROM customer_service WHERE id = %s', (cs_id,))
            row = cursor.fetchone()
            if not row:
                return None
            return (row[0] or '').strip()
        finally:
            cursor.close()
            conn.close()
    else:
        cursor = conn.cursor()
        try:
            cursor.execute('SELECT issue_type FROM customer_service WHERE id = ?', (cs_id,))
            row = cursor.fetchone()
            if not row:
                return None
            return (row[0] or '').strip()
        finally:
            conn.close()


def update_cs_request_issue_type(cs_id: int, issue_type: str) -> bool:
    """C/S 접수 건의 종류(issue_type) 변경 (관리자용)"""
    issue_type = (issue_type or '').strip()
    if not issue_type or len(issue_type) > 200:
        return False
    updated_at = get_kst_now()
    conn = get_db_connection()
    if USE_POSTGRESQL:
        cursor = conn.cursor()
        try:
            cursor.execute('''
                UPDATE customer_service
                SET issue_type = %s, updated_at = %s
                WHERE id = %s
            ''', (issue_type, updated_at, cs_id))
            conn.commit()
            return cursor.rowcount > 0
        except Exception as e:
            print(f"❌ C/S 종류 업데이트 오류: {e}")
            conn.rollback()
            return False
        finally:
            cursor.close()
            conn.close()
    else:
        cursor = conn.cursor()
        try:
            cursor.execute('''
                UPDATE customer_service
                SET issue_type = ?, updated_at = ?
                WHERE id = ?
            ''', (issue_type, updated_at, cs_id))
            conn.commit()
            return cursor.rowcount > 0
        except Exception as e:
            print(f"❌ C/S 종류 업데이트 오류: {e}")
            return False
        finally:
            conn.close()


def update_cs_last_notification(cs_id: int, notification_time: datetime = None) -> bool:
    """C/S 마지막 알림 시간 업데이트 (반복 알림용, Vercel 서버리스에서 DB에 저장)
    PostgreSQL: DB의 NOW() 사용 (타임존 변환 문제 완전 회피)
    SQLite: Python datetime 전달
    """
    conn = get_db_connection()
    cursor = None
    try:
        cursor = conn.cursor()
        if USE_POSTGRESQL:
            # DB 서버 시간(UTC) 사용 - Python/psycopg2 타임존 변환 회피
            cursor.execute("SET LOCAL timezone = 'UTC'")
            cursor.execute('''
                UPDATE customer_service SET last_notification_at = NOW() WHERE id = %s
            ''', (cs_id,))
        else:
            # SQLite: Python datetime 필요
            ts = notification_time if notification_time is not None else datetime.now(timezone.utc)
            cursor.execute('''
                UPDATE customer_service SET last_notification_at = ? WHERE id = ?
            ''', (ts, cs_id))
        conn.commit()
        return True
    except Exception as e:
        print(f"❌ C/S last_notification_at 업데이트 오류: {e}")
        if USE_POSTGRESQL:
            conn.rollback()
        return False
    finally:
        if cursor:
            cursor.close()
        conn.close()


def get_pending_cs_requests() -> list:
    """미처리 C/S 접수 목록 조회 (알림용)"""
    conn = get_db_connection()
    
    if USE_POSTGRESQL:
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        try:
            cursor.execute('''
                SELECT * FROM customer_service
                WHERE status = '접수'
                ORDER BY created_at DESC
            ''')
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
        finally:
            cursor.close()
            conn.close()
    else:
        import sqlite3
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        try:
            cursor.execute('''
                SELECT id, company_name, username, date, month, issue_type, content, 
                       management_number, generated_management_number, customer_name, status, 
                       admin_message, processor, processed_at, created_at, updated_at, last_notification_at
                FROM customer_service
                WHERE status = '접수'
                ORDER BY created_at DESC
            ''')
            rows = cursor.fetchall()
            result = []
            for row in rows:
                result.append({
                    'id': row['id'],
                    'company_name': row['company_name'] or '',
                    'username': row['username'] or '',
                    'date': row['date'] or '',
                    'month': row['month'] or '',
                    'issue_type': row['issue_type'] or '',
                    'content': row['content'] or '',
                    'management_number': row['management_number'] or '',
                    'generated_management_number': row['generated_management_number'] or '',
                    'customer_name': row.get('customer_name') or '',
                    'status': row['status'] or '접수',
                    'admin_message': row['admin_message'] or '',
                    'processor': row['processor'] or '',
                    'processed_at': str(row['processed_at']) if row['processed_at'] else '',
                    'created_at': str(row['created_at']) if row['created_at'] else '',
                    'updated_at': str(row['updated_at']) if row['updated_at'] else '',
                    'last_notification_at': str(row['last_notification_at']) if row.get('last_notification_at') else None
                })
            return result
        finally:
            conn.close()


def get_pending_cs_requests_by_issue_type(issue_type: str = None) -> list:
    """미처리 C/S 접수 목록 조회 (알림용) - 특정 유형 필터링"""
    conn = get_db_connection()
    
    if USE_POSTGRESQL:
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        try:
            if issue_type:
                cursor.execute('''
                    SELECT * FROM customer_service
                    WHERE status = '접수' AND issue_type = %s
                    ORDER BY created_at DESC
                ''', (issue_type,))
            else:
                cursor.execute('''
                    SELECT * FROM customer_service
                    WHERE status = '접수'
                    ORDER BY created_at DESC
                ''')
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
        finally:
            cursor.close()
            conn.close()
    else:
        import sqlite3
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        try:
            if issue_type:
                cursor.execute('''
                    SELECT id, company_name, username, date, month, issue_type, content, 
                           management_number, generated_management_number, customer_name, status, 
                           admin_message, processor, processed_at, created_at, updated_at, last_notification_at
                    FROM customer_service
                    WHERE status = '접수' AND issue_type = ?
                    ORDER BY created_at DESC
                ''', (issue_type,))
            else:
                cursor.execute('''
                    SELECT id, company_name, username, date, month, issue_type, content, 
                           management_number, generated_management_number, customer_name, status, 
                           admin_message, processor, processed_at, created_at, updated_at, last_notification_at
                    FROM customer_service
                    WHERE status = '접수'
                    ORDER BY created_at DESC
                ''')
            rows = cursor.fetchall()
            result = []
            for row in rows:
                result.append({
                    'id': row['id'],
                    'company_name': row['company_name'] or '',
                    'username': row['username'] or '',
                    'date': row['date'] or '',
                    'month': row['month'] or '',
                    'issue_type': row['issue_type'] or '',
                    'content': row['content'] or '',
                    'management_number': row['management_number'] or '',
                    'generated_management_number': row['generated_management_number'] or '',
                    'customer_name': row.get('customer_name') or '',
                    'status': row['status'] or '접수',
                    'admin_message': row['admin_message'] or '',
                    'processor': row['processor'] or '',
                    'processed_at': str(row['processed_at']) if row['processed_at'] else '',
                    'created_at': str(row['created_at']) if row['created_at'] else '',
                    'updated_at': str(row['updated_at']) if row['updated_at'] else '',
                    'last_notification_at': str(row['last_notification_at']) if row.get('last_notification_at') else None
                })
            return result
        finally:
            conn.close()


@cs_bp.route('/', methods=['POST'])
def create_cs():
    """C/S 접수 생성 (화주사용)"""
    try:
        data = request.get_json()
        company_name = data.get('company_name', '').strip()
        username = data.get('username', '').strip()
        issue_type = data.get('issue_type', '').strip()
        content = data.get('content', '').strip()
        management_number = data.get('management_number', '').strip() if data.get('management_number') else None
        customer_name = data.get('customer_name', '').strip() if data.get('customer_name') else None
        
        if not company_name or not username or not issue_type or not content or not management_number:
            return jsonify({
                'success': False,
                'message': '모든 필수 필드를 입력해주세요.'
            }), 400
        
        # 접수 등록 날짜를 현재 날짜로 설정 (한국 시간)
        kst_now = get_kst_now()
        date = kst_now.strftime('%Y-%m-%d')
        # 월을 2자리 형식으로 (01월, 02월, ...)
        month = f"{kst_now.year}년{kst_now.month:02d}월"
        
        # C/S 접수 생성
        cs_id = create_cs_request(company_name, username, date, month, issue_type, content, management_number, customer_name)
        
        if cs_id:
            # 텔레그램 알림 전송
            print(f"📤 [C/S 등록] 텔레그램 알림 전송 시작: C/S #{cs_id}")
            # 현재 시간을 KST로 변환
            kst = timezone(timedelta(hours=9))
            current_time_kst = datetime.now(kst).strftime('%Y-%m-%d %H:%M:%S')
            
            message = f"📝 <b>새로운 C/S 접수</b>\n\n"
            message += f"📋 C/S 번호: #{cs_id}\n"
            if management_number:
                message += f"🔢 관리번호: {management_number}\n"
            message += f"화주사: {company_name}\n"
            message += f"유형: {issue_type}\n"
            message += f"내용: {content[:200]}{'...' if len(content) > 200 else ''}\n"
            message += f"접수일: {current_time_kst}"
            
            print(f"📝 [C/S 등록] 텔레그램 메시지: {message[:100]}...")
            result = send_telegram_notification(message)
            print(f"📬 [C/S 등록] 텔레그램 알림 전송 결과: {'성공' if result else '실패'}")
            
            # 즉시 알림 전송 시 last_notification_at 설정 (반복 알림 기준점)
            # None 전달 → PostgreSQL: NOW(), SQLite: Python UTC (타임존 일관성)
            update_cs_last_notification(cs_id, None)
            
            return jsonify({
                'success': True,
                'message': 'C/S 접수가 등록되었습니다.',
                'id': cs_id
            })
        else:
            return jsonify({
                'success': False,
                'message': 'C/S 접수 등록에 실패했습니다.'
            }), 500
            
    except Exception as e:
        print(f'❌ C/S 접수 생성 오류: {e}')
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'message': f'C/S 접수 등록 중 오류: {str(e)}'
        }), 500


@cs_bp.route('/', methods=['GET'])
def get_cs_list():
    """C/S 접수 목록 조회"""
    try:
        # DB 초기화 확인 (lazy loading)
        try:
            from app import ensure_db_ready
            ensure_db_ready()
        except Exception as db_error:
            print(f"[경고] C/S 목록 조회 시 DB 초기화 확인 중 오류 (무시하고 계속): {db_error}")
        
        company_name = request.args.get('company', '').strip()
        role = request.args.get('role', '화주사').strip()
        month = request.args.get('month', '').strip()
        
        # 관리자 모드에서도 company_name이 제공되면 필터링
        filter_company = company_name if company_name else (None if role == '관리자' else company_name)
        
        cs_list = get_cs_requests(
            filter_company,
            role,
            month if month else None
        )
        
        return jsonify({
            'success': True,
            'data': cs_list,
            'count': len(cs_list)
        })
    except Exception as e:
        print(f'❌ C/S 목록 조회 오류: {e}')
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'data': [],
            'count': 0,
            'message': f'C/S 목록 조회 중 오류: {str(e)}'
        }), 500


@cs_bp.route('/available-months', methods=['GET'])
def get_available_months():
    """C/S 접수가 있는 월 목록 조회 (현재 월 자동 포함)"""
    try:
        # DB 초기화 확인 (lazy loading)
        try:
            from app import ensure_db_ready
            ensure_db_ready()
        except Exception as db_error:
            print(f"[경고] C/S 월 목록 조회 시 DB 초기화 확인 중 오류 (무시하고 계속): {db_error}")
        
        company_name = request.args.get('company', '').strip()
        role = request.args.get('role', '화주사').strip()
        
        conn = get_db_connection()
        
        if USE_POSTGRESQL:
            cursor = conn.cursor()
            try:
                if role == '관리자':
                    cursor.execute('''
                        SELECT DISTINCT month FROM customer_service
                        ORDER BY month DESC
                    ''')
                else:
                    cursor.execute('''
                        SELECT DISTINCT month FROM customer_service
                        WHERE company_name = %s
                        ORDER BY month DESC
                    ''', (company_name,))
                
                rows = cursor.fetchall()
                months = [row[0] for row in rows if row[0]]
            finally:
                cursor.close()
                conn.close()
        else:
            cursor = conn.cursor()
            try:
                if role == '관리자':
                    cursor.execute('''
                        SELECT DISTINCT month FROM customer_service
                        ORDER BY month DESC
                    ''')
                else:
                    cursor.execute('''
                        SELECT DISTINCT month FROM customer_service
                        WHERE company_name = ?
                        ORDER BY month DESC
                    ''', (company_name,))
                
                rows = cursor.fetchall()
                months = [row[0] for row in rows if row[0]]
            finally:
                conn.close()
        
        # 현재 월 자동 추가 (01월 형식으로)
        kst_now = get_kst_now()
        current_month_str = f"{kst_now.year}년{kst_now.month:02d}월"
        if current_month_str not in months:
            months.append(current_month_str)
        
        # 다음 월도 자동 추가
        next_month = kst_now.month + 1
        next_year = kst_now.year
        if next_month > 12:
            next_month = 1
            next_year += 1
        next_month_str = f"{next_year}년{next_month:02d}월"
        if next_month_str not in months:
            months.append(next_month_str)
        
        # 정렬 (년도 내림차순, 월 내림차순)
        def parse_month(month_str):
            try:
                if '년' in month_str and '월' in month_str:
                    year_part = month_str.split('년')[0]
                    month_part = month_str.split('년')[1].split('월')[0]
                    return (int(year_part), int(month_part))
                return (0, 0)
            except:
                return (0, 0)
        
        months.sort(key=parse_month, reverse=True)
        
        return jsonify({
            'success': True,
            'months': months
        })
    except Exception as e:
        print(f'❌ C/S 월 목록 조회 오류: {e}')
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'months': [],
            'message': f'C/S 월 목록 조회 중 오류: {str(e)}'
        }), 500


@cs_bp.route('/<int:cs_id>/status', methods=['PUT'])
def update_cs_status_route(cs_id):
    """C/S 접수 상태 업데이트 (관리자용 - 접수/처리완료/처리불가)"""
    try:
        data = request.get_json()
        status = data.get('status', '').strip()
        admin_message = data.get('admin_message', '').strip() if data.get('admin_message') else None
        processor = data.get('processor', '').strip() if data.get('processor') else None
        
        if not status or status not in ['접수', '처리완료', '처리불가']:
            return jsonify({
                'success': False,
                'message': '상태는 접수, 처리완료, 처리불가 중 하나여야 합니다.'
            }), 400
        
        success = update_cs_status(cs_id, status, admin_message, processor)
        
        if success:
            return jsonify({
                'success': True,
                'message': f'C/S 접수가 {status}로 변경되었습니다.'
            })
        else:
            return jsonify({
                'success': False,
                'message': 'C/S 접수 상태 업데이트에 실패했습니다.'
            }), 500
            
    except Exception as e:
        print(f'❌ C/S 상태 업데이트 오류: {e}')
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'message': f'C/S 상태 업데이트 중 오류: {str(e)}'
        }), 500


@cs_bp.route('/<int:cs_id>/issue-type', methods=['PUT'])
def update_cs_request_issue_type_route(cs_id):
    """C/S 접수 건의 종류 변경 (관리자용)"""
    try:
        role = request.args.get('role', '').strip()
        if role != '관리자':
            return jsonify({
                'success': False,
                'message': '관리자만 C/S 종류를 변경할 수 있습니다.'
            }), 403

        data = request.get_json() or {}
        issue_type = (data.get('issue_type') or '').strip()
        if not issue_type or len(issue_type) > 200:
            return jsonify({
                'success': False,
                'message': 'C/S 종류를 선택하거나 입력해 주세요.'
            }), 400

        prev = fetch_cs_issue_type_for_request(cs_id)
        if prev is None:
            return jsonify({
                'success': False,
                'message': 'C/S 접수를 찾을 수 없습니다.'
            }), 404

        types = get_cs_issue_types()
        active_names = {
            t['name'].strip()
            for t in types
            if t.get('name') and t.get('is_active', True) is not False
        }
        if active_names and issue_type not in active_names and issue_type != prev:
            return jsonify({
                'success': False,
                'message': '활성화된 C/S 종류만 선택할 수 있습니다.'
            }), 400

        success = update_cs_request_issue_type(cs_id, issue_type)
        if success:
            return jsonify({
                'success': True,
                'message': 'C/S 종류가 변경되었습니다.'
            })
        return jsonify({
            'success': False,
            'message': 'C/S 종류 변경에 실패했습니다.'
        }), 500
    except Exception as e:
        print(f'❌ C/S 종류 변경 오류: {e}')
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'message': f'C/S 종류 변경 중 오류: {str(e)}'
        }), 500


@cs_bp.route('/<int:cs_id>', methods=['DELETE'])
def delete_cs_route(cs_id):
    """C/S 접수 삭제 (관리자용)"""
    try:
        role = request.args.get('role', '').strip()
        
        if role != '관리자':
            return jsonify({
                'success': False,
                'message': '관리자만 C/S를 삭제할 수 있습니다.'
            }), 403
        
        success = delete_cs_request(cs_id)
        
        if success:
            return jsonify({
                'success': True,
                'message': 'C/S 접수가 삭제되었습니다.'
            })
        else:
            return jsonify({
                'success': False,
                'message': 'C/S 접수를 찾을 수 없거나 삭제에 실패했습니다.'
            }), 404
    except Exception as e:
        print(f'❌ C/S 삭제 오류: {e}')
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'message': f'C/S 삭제 중 오류: {str(e)}'
        }), 500


@cs_bp.route('/<int:cs_id>/generated-management-number', methods=['PUT'])
def update_generated_management_number_route(cs_id):
    """C/S 접수 생성된 관리번호 업데이트 (관리자용)"""
    try:
        data = request.get_json()
        generated_management_number = data.get('generated_management_number', '').strip() if data.get('generated_management_number') else None
        
        success = update_generated_management_number(cs_id, generated_management_number)
        
        if success:
            return jsonify({
                'success': True,
                'message': '생성된 관리번호가 업데이트되었습니다.'
            })
        else:
            return jsonify({
                'success': False,
                'message': '생성된 관리번호 업데이트에 실패했습니다.'
            }), 500
            
    except Exception as e:
        print(f'❌ C/S 생성된 관리번호 업데이트 오류: {e}')
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'message': f'생성된 관리번호 업데이트 중 오류: {str(e)}'
        }), 500


@cs_bp.route('/<int:cs_id>/customer-name', methods=['PUT'])
def update_customer_name_route(cs_id):
    """C/S 접수 고객명 업데이트 (관리자용)"""
    try:
        data = request.get_json()
        customer_name = data.get('customer_name', '').strip() if data.get('customer_name') else None
        
        success = update_customer_name(cs_id, customer_name)
        
        if success:
            return jsonify({
                'success': True,
                'message': '고객명이 업데이트되었습니다.'
            })
        else:
            return jsonify({
                'success': False,
                'message': '고객명 업데이트에 실패했습니다.'
            }), 500
            
    except Exception as e:
        print(f'❌ C/S 고객명 업데이트 오류: {e}')
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'message': f'고객명 업데이트 중 오류: {str(e)}'
        }), 500


@cs_bp.route('/test-telegram', methods=['POST'])
def test_telegram():
    """텔레그램 알림 테스트 (관리자용)"""
    try:
        # 텔레그램 알림 전송
        message = "🧪 <b>텔레그램 알림 테스트</b>\n\n"
        message += "이 메시지가 보이면 텔레그램 연동이 정상적으로 작동합니다! ✅\n\n"
        message += f"테스트 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        
        success = send_telegram_notification(message)
        
        if success:
            return jsonify({
                'success': True,
                'message': '텔레그램 알림이 전송되었습니다. 텔레그램 앱을 확인해주세요.'
            })
        else:
            return jsonify({
                'success': False,
                'message': '텔레그램 알림 전송에 실패했습니다. 환경 변수 설정을 확인해주세요.'
            }), 500
            
    except Exception as e:
        print(f'❌ 텔레그램 테스트 오류: {e}')
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'message': f'텔레그램 테스트 중 오류: {str(e)}'
        }), 500


@cs_bp.route('/<int:cs_id>/resend-notification', methods=['POST'])
def resend_cs_notification(cs_id):
    """C/S 재요청 알림 전송 (화주사용)"""
    try:
        conn = get_db_connection()
        
        if USE_POSTGRESQL:
            cursor = conn.cursor()
            try:
                # C/S 정보 조회
                cursor.execute('''
                    SELECT id, company_name, username, date, month, issue_type, content, 
                           management_number, generated_management_number, status, created_at
                    FROM customer_service
                    WHERE id = %s
                ''', (cs_id,))
                row = cursor.fetchone()
                
                if not row:
                    return jsonify({
                        'success': False,
                        'message': 'C/S 접수를 찾을 수 없습니다.'
                    }), 404
                
                cs_data = {
                    'id': row[0],
                    'company_name': row[1],
                    'username': row[2],
                    'date': row[3],
                    'month': row[4],
                    'issue_type': row[5],
                    'content': row[6],
                    'management_number': row[7],
                    'generated_management_number': row[8],
                    'status': row[9],
                    'created_at': row[10]
                }
            finally:
                cursor.close()
                conn.close()
        else:
            import sqlite3
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            try:
                cursor.execute('''
                    SELECT id, company_name, username, date, month, issue_type, content, 
                           management_number, generated_management_number, status, created_at
                    FROM customer_service
                    WHERE id = ?
                ''', (cs_id,))
                row = cursor.fetchone()
                
                if not row:
                    return jsonify({
                        'success': False,
                        'message': 'C/S 접수를 찾을 수 없습니다.'
                    }), 404
                
                cs_data = dict(row)
            finally:
                conn.close()
        
        # 처리완료 상태면 알림 전송하지 않음
        if cs_data.get('status') == '처리완료' or cs_data.get('status') == '처리불가':
            return jsonify({
                'success': False,
                'message': '처리완료된 C/S는 재요청할 수 없습니다.'
            }), 400
        
        # 텔레그램 알림 메시지 생성
        kst_now = get_kst_now()
        message = "🔔 <b>C/S 재요청 알림</b>\n\n"
        message += f"📋 <b>C/S ID:</b> {cs_data.get('id', 'N/A')}\n"
        if cs_data.get('generated_management_number'):
            message += f"🔢 <b>관리번호:</b> {cs_data.get('generated_management_number')}\n"
        elif cs_data.get('management_number'):
            message += f"🔢 <b>관리번호:</b> {cs_data.get('management_number')}\n"
        message += f"🏢 <b>화주사:</b> {cs_data.get('company_name', 'N/A')}\n"
        message += f"📅 <b>날짜:</b> {cs_data.get('date', 'N/A')}\n"
        message += f"📦 <b>종류:</b> {cs_data.get('issue_type', 'N/A')}\n"
        message += f"📝 <b>내용:</b> {cs_data.get('content', 'N/A')}\n"
        message += f"⏰ <b>재요청 시간:</b> {kst_now.strftime('%Y-%m-%d %H:%M:%S')}\n\n"
        message += "⚠️ 화주사가 재요청을 요청했습니다. 빠른 처리 부탁드립니다."
        
        success = send_telegram_notification(message)
        
        if success:
            return jsonify({
                'success': True,
                'message': '재요청 알림이 전송되었습니다.'
            })
        else:
            return jsonify({
                'success': False,
                'message': '재요청 알림 전송에 실패했습니다.'
            }), 500
            
    except Exception as e:
        print(f'❌ C/S 재요청 알림 오류: {e}')
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'message': f'재요청 알림 전송 중 오류: {str(e)}'
        }), 500


def _check_cron_auth():
    """Cron 인증 검사. 실패 시 (False, response) 반환, 성공 시 (True, None) 반환"""
    cron_secret = request.headers.get('Authorization')
    query_secret = request.args.get('secret', '').strip()
    expected_secret = os.environ.get('CRON_SECRET')
    if expected_secret:
        header_ok = cron_secret == f'Bearer {expected_secret}'
        query_ok = query_secret == expected_secret
        if not header_ok and not query_ok:
            return False, (jsonify({'success': False, 'message': 'Unauthorized'}), 401)
    return True, None


@cs_bp.route('/check-notifications', methods=['GET', 'POST'])
def check_notifications():
    """C/S 알림 체크 (Vercel Cron Jobs용) - type 파라미터로 분기"""
    try:
        ok, err = _check_cron_auth()
        if not ok:
            return err
        notif_type = request.args.get('type', 'all').strip().lower()
        if notif_type not in ('all', 'cancellation', 'general'):
            notif_type = 'all'
        from api.cs.scheduler import send_cs_notifications
        stats = send_cs_notifications(notification_type=notif_type) or {}
        
        resp = {
            'success': True,
            'message': 'C/S 알림 체크 완료',
            'type': notif_type,
            'cancellation_count': stats.get('cancellation_count', 0),
            'general_count': stats.get('general_count', 0),
            'cancellation_sent': stats.get('cancellation_sent', 0),
            'general_sent': stats.get('general_sent', 0),
            'logs': stats.get('log_lines', []),
        }
        return jsonify(resp)
        
    except Exception as e:
        print(f'❌ C/S 알림 체크 오류: {e}')
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'message': f'C/S 알림 체크 중 오류: {str(e)}'
        }), 500


@cs_bp.route('/check-notifications-cancellation', methods=['GET', 'POST'])
def check_notifications_cancellation():
    """C/S 취소건 알림 전용 (1분용 cron) - URL 분리로 혼동 방지"""
    try:
        ok, err = _check_cron_auth()
        if not ok:
            return err
        from api.cs.scheduler import send_cs_notifications
        stats = send_cs_notifications(notification_type='cancellation') or {}
        return jsonify({
            'success': True, 'message': 'C/S 취소건 알림 체크 완료', 'type': 'cancellation',
            'cancellation_count': stats.get('cancellation_count', 0), 'cancellation_sent': stats.get('cancellation_sent', 0),
            'logs': stats.get('log_lines', []),
        })
    except Exception as e:
        print(f'❌ C/S 취소건 알림 체크 오류: {e}')
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'message': str(e)}), 500


@cs_bp.route('/check-notifications-general', methods=['GET', 'POST'])
def check_notifications_general():
    """C/S 일반건 알림 전용 (5분용 cron) - URL 분리로 혼동 방지"""
    try:
        ok, err = _check_cron_auth()
        if not ok:
            return err
        from api.cs.scheduler import send_cs_notifications
        stats = send_cs_notifications(notification_type='general') or {}
        return jsonify({
            'success': True, 'message': 'C/S 일반건 알림 체크 완료', 'type': 'general',
            'general_count': stats.get('general_count', 0), 'general_sent': stats.get('general_sent', 0),
            'logs': stats.get('log_lines', []),
        })
    except Exception as e:
        print(f'❌ C/S 일반건 알림 체크 오류: {e}')
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'message': str(e)}), 500


@cs_bp.route('/export', methods=['GET'])
def export_cs():
    """C/S 접수 엑셀 다운로드"""
    try:
        company_name = request.args.get('company', '').strip()
        role = request.args.get('role', '화주사').strip()
        month = request.args.get('month', '').strip()
        
        # 관리자 모드에서도 company_name이 제공되면 필터링
        filter_company = company_name if company_name else (None if role == '관리자' else company_name)
        
        cs_list = get_cs_requests(
            filter_company,
            role,
            month if month else None
        )
        
        # 메모리 내 CSV 생성
        output = io.StringIO()
        writer = csv.writer(output)
        
        # 한글 헤더
        writer.writerow(['날짜', '관리번호', '생성된 관리번호', '화주사명', '고객명', 'C/S 종류', 'C/S 내용', '처리여부', '처리자', '관리자 메시지', '접수일시'])
        
        for cs in cs_list:
            date = cs.get('date', '')
            management_number = cs.get('management_number', '') or ''
            generated_management_number = cs.get('generated_management_number', '') or ''
            company = cs.get('company_name', '')
            customer_name = cs.get('customer_name', '') or ''
            issue_type = cs.get('issue_type', '')
            content = cs.get('content', '')
            status = cs.get('status', '접수')
            processor = cs.get('processor', '') or ''
            admin_message = cs.get('admin_message', '') or ''
            created_at = cs.get('created_at', '')
            
            writer.writerow([
                date,
                management_number,
                generated_management_number,
                company,
                customer_name,
                issue_type,
                content,
                status,
                processor,
                admin_message,
                created_at
            ])
        
        output.seek(0)
        
        # 파일명 생성 (한글)
        filename = f"C/S접수내역_{month if month else '전체'}.csv"
        encoded_filename = quote(filename.encode('utf-8'))
        
        response = Response(
            output.getvalue().encode('utf-8-sig'),  # BOM 추가로 Excel에서 한글 깨짐 방지
            mimetype='text/csv; charset=utf-8',
            headers={
                'Content-Disposition': f'attachment; filename*=UTF-8\'\'{encoded_filename}'
            }
        )
        
        return response
        
    except Exception as e:
        print(f'❌ C/S 엑셀 다운로드 오류: {e}')
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'message': f'엑셀 다운로드 중 오류: {str(e)}'
        }), 500


# ========== C/S 종류 관리 API ==========

def get_cs_issue_types() -> list:
    """C/S 종류 목록 조회"""
    conn = get_db_connection()
    
    if USE_POSTGRESQL:
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        try:
            cursor.execute('''
                SELECT * FROM cs_issue_types
                ORDER BY display_order ASC, id ASC
            ''')
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
        finally:
            cursor.close()
            conn.close()
    else:
        import sqlite3
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        try:
            cursor.execute('''
                SELECT id, name, color, bg_color, display_order, is_active, created_at, updated_at
                FROM cs_issue_types
                ORDER BY display_order ASC, id ASC
            ''')
            rows = cursor.fetchall()
            result = []
            for row in rows:
                result.append({
                    'id': row['id'],
                    'name': row['name'],
                    'color': row['color'] or '#636e72',
                    'bg_color': row['bg_color'] or '#ecf0f1',
                    'display_order': row['display_order'] or 0,
                    'is_active': bool(row['is_active']),
                    'created_at': str(row['created_at']) if row['created_at'] else '',
                    'updated_at': str(row['updated_at']) if row['updated_at'] else ''
                })
            return result
        finally:
            conn.close()


def create_cs_issue_type(name: str, color: str = None, bg_color: str = None, display_order: int = None) -> int:
    """C/S 종류 생성"""
    conn = get_db_connection()
    
    kst_now = get_kst_now()
    color = color or '#636e72'
    bg_color = bg_color or '#ecf0f1'
    
    # display_order가 없으면 최대값 + 1
    if display_order is None:
        if USE_POSTGRESQL:
            cursor = conn.cursor()
            try:
                cursor.execute('SELECT COALESCE(MAX(display_order), 0) + 1 FROM cs_issue_types')
                display_order = cursor.fetchone()[0] or 1
            finally:
                cursor.close()
        else:
            cursor = conn.cursor()
            try:
                cursor.execute('SELECT COALESCE(MAX(display_order), 0) + 1 FROM cs_issue_types')
                row = cursor.fetchone()
                display_order = row[0] if row and row[0] else 1
            finally:
                pass
    
    if USE_POSTGRESQL:
        cursor = conn.cursor()
        try:
            cursor.execute('''
                INSERT INTO cs_issue_types (name, color, bg_color, display_order, created_at, updated_at)
                VALUES (%s, %s, %s, %s, %s, %s)
                RETURNING id
            ''', (name, color, bg_color, display_order, kst_now, kst_now))
            cs_type_id = cursor.fetchone()[0]
            conn.commit()
            print(f"✅ C/S 종류 생성 성공: ID {cs_type_id}, 이름: {name}")
            return cs_type_id
        except Exception as e:
            print(f"❌ C/S 종류 생성 오류: {e}")
            conn.rollback()
            return None
        finally:
            cursor.close()
            conn.close()
    else:
        cursor = conn.cursor()
        try:
            cursor.execute('''
                INSERT INTO cs_issue_types (name, color, bg_color, display_order, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (name, color, bg_color, display_order, kst_now, kst_now))
            cs_type_id = cursor.lastrowid
            conn.commit()
            print(f"✅ C/S 종류 생성 성공: ID {cs_type_id}, 이름: {name}")
            return cs_type_id
        except Exception as e:
            print(f"❌ C/S 종류 생성 오류: {e}")
            conn.rollback()
            return None
        finally:
            conn.close()


def update_cs_issue_type(type_id: int, name: str = None, color: str = None, bg_color: str = None, display_order: int = None, is_active: bool = None) -> bool:
    """C/S 종류 업데이트"""
    conn = get_db_connection()
    
    kst_now = get_kst_now()
    
    # 업데이트할 필드만 동적으로 구성
    updates = []
    params = []
    
    if name is not None:
        updates.append('name = %s' if USE_POSTGRESQL else 'name = ?')
        params.append(name)
    if color is not None:
        updates.append('color = %s' if USE_POSTGRESQL else 'color = ?')
        params.append(color)
    if bg_color is not None:
        updates.append('bg_color = %s' if USE_POSTGRESQL else 'bg_color = ?')
        params.append(bg_color)
    if display_order is not None:
        updates.append('display_order = %s' if USE_POSTGRESQL else 'display_order = ?')
        params.append(display_order)
    if is_active is not None:
        updates.append('is_active = %s' if USE_POSTGRESQL else 'is_active = ?')
        params.append(is_active)
    
    if not updates:
        return False
    
    updates.append('updated_at = %s' if USE_POSTGRESQL else 'updated_at = ?')
    params.append(kst_now)
    params.append(type_id)
    
    if USE_POSTGRESQL:
        cursor = conn.cursor()
        try:
            query = f'UPDATE cs_issue_types SET {", ".join(updates)} WHERE id = %s'
            cursor.execute(query, params)
            conn.commit()
            return cursor.rowcount > 0
        except Exception as e:
            print(f"❌ C/S 종류 업데이트 오류: {e}")
            conn.rollback()
            return False
        finally:
            cursor.close()
            conn.close()
    else:
        cursor = conn.cursor()
        try:
            query = f'UPDATE cs_issue_types SET {", ".join(updates)} WHERE id = ?'
            cursor.execute(query, params)
            conn.commit()
            return cursor.rowcount > 0
        except Exception as e:
            print(f"❌ C/S 종류 업데이트 오류: {e}")
            return False
        finally:
            conn.close()


def delete_cs_issue_type(type_id: int) -> bool:
    """C/S 종류 삭제"""
    conn = get_db_connection()
    
    if USE_POSTGRESQL:
        cursor = conn.cursor()
        try:
            cursor.execute('DELETE FROM cs_issue_types WHERE id = %s', (type_id,))
            conn.commit()
            return cursor.rowcount > 0
        except Exception as e:
            print(f"❌ C/S 종류 삭제 오류: {e}")
            conn.rollback()
            return False
        finally:
            cursor.close()
            conn.close()
    else:
        cursor = conn.cursor()
        try:
            cursor.execute('DELETE FROM cs_issue_types WHERE id = ?', (type_id,))
            conn.commit()
            return cursor.rowcount > 0
        except Exception as e:
            print(f"❌ C/S 종류 삭제 오류: {e}")
            return False
        finally:
            conn.close()


@cs_bp.route('/issue-types', methods=['GET'])
def get_cs_issue_types_route():
    """C/S 종류 목록 조회"""
    try:
        issue_types = get_cs_issue_types()
        return jsonify({
            'success': True,
            'data': issue_types
        })
    except Exception as e:
        print(f'❌ C/S 종류 목록 조회 오류: {e}')
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'data': [],
            'message': f'C/S 종류 목록 조회 중 오류: {str(e)}'
        }), 500


@cs_bp.route('/issue-types', methods=['POST'])
def create_cs_issue_type_route():
    """C/S 종류 생성 (관리자용)"""
    try:
        data = request.get_json()
        role = request.args.get('role', '').strip()
        
        if role != '관리자':
            return jsonify({
                'success': False,
                'message': '관리자만 C/S 종류를 생성할 수 있습니다.'
            }), 403
        
        name = data.get('name', '').strip()
        color = data.get('color', '').strip() if data.get('color') else None
        bg_color = data.get('bg_color', '').strip() if data.get('bg_color') else None
        display_order = data.get('display_order')
        
        if not name:
            return jsonify({
                'success': False,
                'message': '종류명을 입력해주세요.'
            }), 400
        
        cs_type_id = create_cs_issue_type(name, color, bg_color, display_order)
        
        if cs_type_id:
            return jsonify({
                'success': True,
                'message': 'C/S 종류가 생성되었습니다.',
                'id': cs_type_id
            })
        else:
            return jsonify({
                'success': False,
                'message': 'C/S 종류 생성에 실패했습니다. (이미 존재하는 이름일 수 있습니다)'
            }), 500
            
    except Exception as e:
        print(f'❌ C/S 종류 생성 오류: {e}')
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'message': f'C/S 종류 생성 중 오류: {str(e)}'
        }), 500


@cs_bp.route('/issue-types/<int:type_id>', methods=['PUT'])
def update_cs_issue_type_route(type_id):
    """C/S 종류 업데이트 (관리자용)"""
    try:
        data = request.get_json()
        role = request.args.get('role', '').strip()
        
        if role != '관리자':
            return jsonify({
                'success': False,
                'message': '관리자만 C/S 종류를 수정할 수 있습니다.'
            }), 403
        
        name = data.get('name', '').strip() if data.get('name') else None
        color = data.get('color', '').strip() if data.get('color') else None
        bg_color = data.get('bg_color', '').strip() if data.get('bg_color') else None
        display_order = data.get('display_order')
        is_active = data.get('is_active')
        
        success = update_cs_issue_type(type_id, name, color, bg_color, display_order, is_active)
        
        if success:
            return jsonify({
                'success': True,
                'message': 'C/S 종류가 업데이트되었습니다.'
            })
        else:
            return jsonify({
                'success': False,
                'message': 'C/S 종류 업데이트에 실패했습니다.'
            }), 500
            
    except Exception as e:
        print(f'❌ C/S 종류 업데이트 오류: {e}')
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'message': f'C/S 종류 업데이트 중 오류: {str(e)}'
        }), 500


@cs_bp.route('/issue-types/<int:type_id>', methods=['DELETE'])
def delete_cs_issue_type_route(type_id):
    """C/S 종류 삭제 (관리자용)"""
    try:
        role = request.args.get('role', '').strip()
        
        if role != '관리자':
            return jsonify({
                'success': False,
                'message': '관리자만 C/S 종류를 삭제할 수 있습니다.'
            }), 403
        
        success = delete_cs_issue_type(type_id)
        
        if success:
            return jsonify({
                'success': True,
                'message': 'C/S 종류가 삭제되었습니다.'
            })
        else:
            return jsonify({
                'success': False,
                'message': 'C/S 종류를 찾을 수 없거나 삭제에 실패했습니다.'
            }), 404
    except Exception as e:
        print(f'❌ C/S 종류 삭제 오류: {e}')
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'message': f'C/S 종류 삭제 중 오류: {str(e)}'
        }), 500
