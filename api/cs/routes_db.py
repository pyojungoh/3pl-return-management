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
from urllib.parse import quote

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


def create_cs_request(company_name: str, username: str, date: str, month: str, issue_type: str, content: str, management_number: str = None) -> int:
    """C/S 접수 생성"""
    conn = get_db_connection()
    
    if USE_POSTGRESQL:
        cursor = conn.cursor()
        try:
            cursor.execute('''
                INSERT INTO customer_service (company_name, username, date, month, issue_type, content, management_number, status)
                VALUES (%s, %s, %s, %s, %s, %s, %s, '접수')
                RETURNING id
            ''', (company_name, username, date, month, issue_type, content, management_number))
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
                INSERT INTO customer_service (company_name, username, date, month, issue_type, content, management_number, status)
                VALUES (?, ?, ?, ?, ?, ?, ?, '접수')
            ''', (company_name, username, date, month, issue_type, content, management_number))
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
                if month:
                    cursor.execute('''
                        SELECT id, company_name, username, date, month, issue_type, content, 
                               management_number, generated_management_number, status, 
                               admin_message, processor, processed_at, created_at, updated_at
                        FROM customer_service
                        WHERE month = ?
                        ORDER BY created_at DESC
                    ''', (month,))
                else:
                    cursor.execute('''
                        SELECT id, company_name, username, date, month, issue_type, content, 
                               management_number, generated_management_number, status, 
                               admin_message, processor, processed_at, created_at, updated_at
                        FROM customer_service
                        ORDER BY created_at DESC
                    ''')
            else:
                if month:
                    cursor.execute('''
                        SELECT id, company_name, username, date, month, issue_type, content, 
                               management_number, generated_management_number, status, 
                               admin_message, processor, processed_at, created_at, updated_at
                        FROM customer_service
                        WHERE company_name = ? AND month = ?
                        ORDER BY created_at DESC
                    ''', (company_name, month))
                else:
                    cursor.execute('''
                        SELECT id, company_name, username, date, month, issue_type, content, 
                               management_number, generated_management_number, status, 
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
    
    processed_at = datetime.now() if status in ['처리완료', '처리불가'] else None
    
    if USE_POSTGRESQL:
        cursor = conn.cursor()
        try:
            if admin_message and processor:
                cursor.execute('''
                    UPDATE customer_service
                    SET status = %s, admin_message = %s, processor = %s, processed_at = %s, updated_at = CURRENT_TIMESTAMP
                    WHERE id = %s
                ''', (status, admin_message, processor, processed_at, cs_id))
            elif admin_message:
                cursor.execute('''
                    UPDATE customer_service
                    SET status = %s, admin_message = %s, processed_at = %s, updated_at = CURRENT_TIMESTAMP
                    WHERE id = %s
                ''', (status, admin_message, processed_at, cs_id))
            elif processor:
                cursor.execute('''
                    UPDATE customer_service
                    SET status = %s, processor = %s, processed_at = %s, updated_at = CURRENT_TIMESTAMP
                    WHERE id = %s
                ''', (status, processor, processed_at, cs_id))
            else:
                cursor.execute('''
                    UPDATE customer_service
                    SET status = %s, processed_at = %s, updated_at = CURRENT_TIMESTAMP
                    WHERE id = %s
                ''', (status, processed_at, cs_id))
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
            if admin_message and processor:
                cursor.execute('''
                    UPDATE customer_service
                    SET status = ?, admin_message = ?, processor = ?, processed_at = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                ''', (status, admin_message, processor, processed_at, cs_id))
            elif admin_message:
                cursor.execute('''
                    UPDATE customer_service
                    SET status = ?, admin_message = ?, processed_at = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                ''', (status, admin_message, processed_at, cs_id))
            elif processor:
                cursor.execute('''
                    UPDATE customer_service
                    SET status = ?, processor = ?, processed_at = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                ''', (status, processor, processed_at, cs_id))
            else:
                cursor.execute('''
                    UPDATE customer_service
                    SET status = ?, processed_at = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                ''', (status, processed_at, cs_id))
            conn.commit()
            return cursor.rowcount > 0
        except Exception as e:
            print(f"❌ C/S 상태 업데이트 오류: {e}")
            return False
        finally:
            conn.close()


def update_generated_management_number(cs_id: int, generated_management_number: str) -> bool:
    """C/S 접수 생성된 관리번호 업데이트 (관리자용)"""
    conn = get_db_connection()
    
    if USE_POSTGRESQL:
        cursor = conn.cursor()
        try:
            cursor.execute('''
                UPDATE customer_service
                SET generated_management_number = %s, updated_at = CURRENT_TIMESTAMP
                WHERE id = %s
            ''', (generated_management_number, cs_id))
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
                SET generated_management_number = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            ''', (generated_management_number, cs_id))
            conn.commit()
            return cursor.rowcount > 0
        except Exception as e:
            print(f"❌ C/S 생성된 관리번호 업데이트 오류: {e}")
            return False
        finally:
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
                       management_number, generated_management_number, status, 
                       admin_message, processor, processed_at, created_at, updated_at
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
                           management_number, generated_management_number, status, 
                           admin_message, processor, processed_at, created_at, updated_at
                    FROM customer_service
                    WHERE status = '접수' AND issue_type = ?
                    ORDER BY created_at DESC
                ''', (issue_type,))
            else:
                cursor.execute('''
                    SELECT id, company_name, username, date, month, issue_type, content, 
                           management_number, generated_management_number, status, 
                           admin_message, processor, processed_at, created_at, updated_at
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


@cs_bp.route('/', methods=['POST'])
def create_cs():
    """C/S 접수 생성 (화주사용)"""
    try:
        data = request.get_json()
        company_name = data.get('company_name', '').strip()
        username = data.get('username', '').strip()
        date = data.get('date', '').strip()
        issue_type = data.get('issue_type', '').strip()
        content = data.get('content', '').strip()
        management_number = data.get('management_number', '').strip() if data.get('management_number') else None
        
        if not company_name or not username or not date or not issue_type or not content or not management_number:
            return jsonify({
                'success': False,
                'message': '모든 필수 필드를 입력해주세요.'
            }), 400
        
        # 날짜에서 년월 추출 (YYYY-MM-DD 형식에서)
        try:
            date_obj = datetime.strptime(date, '%Y-%m-%d')
            month = f"{date_obj.year}년{date_obj.month}월"
        except:
            # 이미 년월 형식인 경우
            month = date if '년' in date and '월' in date else f"{datetime.now().year}년{datetime.now().month}월"
        
        # C/S 접수 생성
        cs_id = create_cs_request(company_name, username, date, month, issue_type, content, management_number)
        
        if cs_id:
            # 텔레그램 알림 전송
            # 현재 시간을 KST로 변환
            kst = timezone(timedelta(hours=9))
            current_time_kst = datetime.now(kst).strftime('%Y-%m-%d %H:%M:%S')
            
            message = f"📝 <b>새로운 C/S 접수</b>\n\n"
            message += f"화주사: {company_name}\n"
            message += f"유형: {issue_type}\n"
            message += f"내용: {content[:200]}{'...' if len(content) > 200 else ''}\n"
            message += f"접수일: {current_time_kst}"
            
            send_telegram_notification(message)
            
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
        company_name = request.args.get('company', '').strip()
        role = request.args.get('role', '화주사').strip()
        month = request.args.get('month', '').strip()
        
        cs_list = get_cs_requests(
            company_name if role != '관리자' else None, 
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
    """C/S 접수가 있는 월 목록 조회"""
    try:
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
                return jsonify({
                    'success': True,
                    'months': months
                })
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
                return jsonify({
                    'success': True,
                    'months': months
                })
            finally:
                conn.close()
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
    """C/S 접수 상태 업데이트 (관리자용 - 처리완료/처리불가)"""
    try:
        data = request.get_json()
        status = data.get('status', '').strip()
        admin_message = data.get('admin_message', '').strip() if data.get('admin_message') else None
        processor = data.get('processor', '').strip() if data.get('processor') else None
        
        if not status or status not in ['처리완료', '처리불가']:
            return jsonify({
                'success': False,
                'message': '상태는 처리완료 또는 처리불가여야 합니다.'
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


@cs_bp.route('/export', methods=['GET'])
def export_cs():
    """C/S 접수 엑셀 다운로드"""
    try:
        company_name = request.args.get('company', '').strip()
        role = request.args.get('role', '화주사').strip()
        month = request.args.get('month', '').strip()
        
        cs_list = get_cs_requests(
            company_name if role != '관리자' else None,
            role,
            month if month else None
        )
        
        # 메모리 내 CSV 생성
        output = io.StringIO()
        writer = csv.writer(output)
        
        # 한글 헤더
        writer.writerow(['날짜', '관리번호', '생성된 관리번호', '화주사명', 'C/S 종류', 'C/S 내용', '처리여부', '처리자', '관리자 메시지', '접수일시'])
        
        for cs in cs_list:
            date = cs.get('date', '')
            management_number = cs.get('management_number', '') or ''
            generated_management_number = cs.get('generated_management_number', '') or ''
            company = cs.get('company_name', '')
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
