"""
특수작업 관리 API 라우트
"""
from flask import Blueprint, request, jsonify
from api.database.models import (
    get_db_connection,
    USE_POSTGRESQL
)
from datetime import datetime, date
from urllib.parse import unquote

if USE_POSTGRESQL:
    from psycopg2.extras import RealDictCursor

# Blueprint 생성
special_works_bp = Blueprint('special_works', __name__, url_prefix='/api/special-works')


def ensure_special_work_batch_tables():
    """특수작업 배치 테이블 생성"""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        if USE_POSTGRESQL:
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS special_work_batches (
                    id SERIAL PRIMARY KEY,
                    company_name TEXT NOT NULL,
                    work_date DATE NOT NULL,
                    total_amount INTEGER NOT NULL DEFAULT 0,
                    entry_count INTEGER NOT NULL DEFAULT 0,
                    photo_links TEXT,
                    memo TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS special_work_batch_items (
                    id SERIAL PRIMARY KEY,
                    batch_id INTEGER NOT NULL REFERENCES special_work_batches(id) ON DELETE CASCADE,
                    work_id INTEGER NOT NULL REFERENCES special_works(id) ON DELETE CASCADE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
        else:
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS special_work_batches (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    company_name TEXT NOT NULL,
                    work_date DATE NOT NULL,
                    total_amount INTEGER NOT NULL DEFAULT 0,
                    entry_count INTEGER NOT NULL DEFAULT 0,
                    photo_links TEXT,
                    memo TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS special_work_batch_items (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    batch_id INTEGER NOT NULL,
                    work_id INTEGER NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (batch_id) REFERENCES special_work_batches(id) ON DELETE CASCADE,
                    FOREIGN KEY (work_id) REFERENCES special_works(id) ON DELETE CASCADE
                )
            ''')
    finally:
        cursor.close()
        conn.close()


ensure_special_work_batch_tables()


def recalculate_batch_summary(cursor, batch_id):
    """배치 요약 정보 재계산"""
    if not batch_id:
        return
    if USE_POSTGRESQL:
        cursor.execute('''
            SELECT 
                COALESCE(COUNT(sw.id), 0) AS entry_count,
                COALESCE(SUM(sw.total_price), 0) AS total_amount
            FROM special_work_batch_items bi
            JOIN special_works sw ON bi.work_id = sw.id
            WHERE bi.batch_id = %s
        ''', (batch_id,))
    else:
        cursor.execute('''
            SELECT 
                COALESCE(COUNT(sw.id), 0) AS entry_count,
                COALESCE(SUM(sw.total_price), 0) AS total_amount
            FROM special_work_batch_items bi
            JOIN special_works sw ON bi.work_id = sw.id
            WHERE bi.batch_id = ?
        ''', (batch_id,))
    row = cursor.fetchone()
    if not row:
        return
    entry_count = row[0] if isinstance(row, tuple) else row['entry_count']
    total_amount = row[1] if isinstance(row, tuple) else row['total_amount']
    if entry_count == 0:
        if USE_POSTGRESQL:
            cursor.execute('DELETE FROM special_work_batches WHERE id = %s', (batch_id,))
        else:
            cursor.execute('DELETE FROM special_work_batches WHERE id = ?', (batch_id,))
        return
    if USE_POSTGRESQL:
        cursor.execute('''
            UPDATE special_work_batches
            SET entry_count = %s,
                total_amount = %s,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = %s
        ''', (entry_count, total_amount, batch_id))
    else:
        cursor.execute('''
            UPDATE special_work_batches
            SET entry_count = ?, 
                total_amount = ?, 
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        ''', (entry_count, total_amount, batch_id))


def cursor_rows_to_dicts(cursor, rows):
    columns = [col[0] for col in cursor.description]
    dict_rows = []
    for row in rows:
        if isinstance(row, dict):
            dict_rows.append(row)
        else:
            dict_rows.append({columns[i]: row[i] for i in range(len(columns))})
    return dict_rows


def get_first_value(row, default=None):
    if row is None:
        return default
    if isinstance(row, dict):
        # 반환된 dict의 첫 번째 값을 사용
        for value in row.values():
            return value
        return default
    return row[0] if len(row) > 0 else default


def format_datetime_value(value):
    if isinstance(value, datetime):
        return value.strftime('%Y-%m-%d %H:%M:%S')
    if isinstance(value, date):
        return value.strftime('%Y-%m-%d')
    return value


def get_user_context():
    """사용자 컨텍스트 가져오기 (헤더 또는 세션)"""
    # 헤더에서 사용자 정보 가져오기
    role = request.headers.get('X-User-Role', '').strip()
    username = request.headers.get('X-User-Name', '').strip()
    company_name = request.headers.get('X-Company-Name', '').strip()
    
    # URL 디코딩
    if role:
        role = unquote(role)
    if username:
        username = unquote(username)
    if company_name:
        company_name = unquote(company_name)
    
    return {
        'role': role or '화주사',
        'username': username,
        'company_name': company_name
    }


# ========== 작업 종류 관련 API ==========

@special_works_bp.route('/types', methods=['GET'])
def get_work_types():
    """작업 종류 목록 조회"""
    try:
        conn = get_db_connection()
        if USE_POSTGRESQL:
            cursor = conn.cursor(cursor_factory=RealDictCursor)
        else:
            cursor = conn.cursor()
        
        try:
            cursor.execute('''
                SELECT id, name, default_unit_price, display_order, created_at, updated_at
                FROM special_work_types
                ORDER BY display_order, name
            ''')
            rows = cursor.fetchall()
            # SQLite Row 객체는 dict()로 변환 가능, PostgreSQL RealDictCursor는 이미 dict
            result = [dict(row) for row in rows]
            
            # datetime 객체를 문자열로 변환
            for item in result:
                for key, value in item.items():
                    if isinstance(value, datetime):
                        item[key] = value.strftime('%Y-%m-%d %H:%M:%S') if value else None
            
            return jsonify({
                'success': True,
                'data': result,
                'count': len(result)
            })
        finally:
            cursor.close()
            conn.close()
    except Exception as e:
        print(f'[오류] 작업 종류 조회 오류: {e}')
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'data': [],
            'count': 0,
            'message': f'작업 종류 조회 중 오류: {str(e)}'
        }), 500


@special_works_bp.route('/types', methods=['POST'])
def create_work_type():
    """작업 종류 생성"""
    try:
        user_context = get_user_context()
        if user_context['role'] != '관리자':
            return jsonify({
                'success': False,
                'message': '관리자만 작업 종류를 생성할 수 있습니다.'
            }), 403
        
        data = request.get_json()
        name = data.get('name', '').strip()
        default_unit_price = data.get('default_unit_price', 0)
        display_order = data.get('display_order', 0)
        
        if not name:
            return jsonify({
                'success': False,
                'message': '작업 종류명은 필수입니다.'
            }), 400
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        try:
            if USE_POSTGRESQL:
                cursor.execute('''
                    INSERT INTO special_work_types (name, default_unit_price, display_order, created_at, updated_at)
                    VALUES (%s, %s, %s, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                    RETURNING id
                ''', (name, default_unit_price, display_order))
                work_type_row = cursor.fetchone()
                work_type_id = get_first_value(work_type_row)
            else:
                cursor.execute('''
                    INSERT INTO special_work_types (name, default_unit_price, display_order, created_at, updated_at)
                    VALUES (?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                ''', (name, default_unit_price, display_order))
                work_type_id = cursor.lastrowid
            
            conn.commit()
            return jsonify({
                'success': True,
                'message': '작업 종류가 생성되었습니다.',
                'id': work_type_id
            })
        except Exception as e:
            conn.rollback() if USE_POSTGRESQL else None
            print(f'[오류] 작업 종류 생성 오류: {e}')
            import traceback
            traceback.print_exc()
            return jsonify({
                'success': False,
                'message': f'작업 종류 생성 중 오류: {str(e)}'
            }), 500
        finally:
            cursor.close()
            conn.close()
    except Exception as e:
        print(f'❌ 작업 종류 생성 오류: {e}')
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'message': f'작업 종류 생성 중 오류: {str(e)}'
        }), 500


@special_works_bp.route('/types/<int:type_id>', methods=['PUT'])
def update_work_type(type_id):
    """작업 종류 수정"""
    try:
        user_context = get_user_context()
        if user_context['role'] != '관리자':
            return jsonify({
                'success': False,
                'message': '관리자만 작업 종류를 수정할 수 있습니다.'
            }), 403
        
        data = request.get_json()
        name = data.get('name')
        default_unit_price = data.get('default_unit_price')
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        try:
            updates = []
            params = []
            
            if name is not None:
                updates.append('name = %s' if USE_POSTGRESQL else 'name = ?')
                params.append(name.strip())
            
            if default_unit_price is not None:
                updates.append('default_unit_price = %s' if USE_POSTGRESQL else 'default_unit_price = ?')
                params.append(default_unit_price)
            
            if not updates:
                return jsonify({
                    'success': False,
                    'message': '수정할 데이터가 없습니다.'
                }), 400
            
            updates.append('updated_at = CURRENT_TIMESTAMP')
            params.append(type_id)
            
            if USE_POSTGRESQL:
                cursor.execute(f'''
                    UPDATE special_work_types 
                    SET {', '.join(updates)}
                    WHERE id = %s
                ''', params)
            else:
                cursor.execute(f'''
                    UPDATE special_work_types 
                    SET {', '.join(updates)}
                    WHERE id = ?
                ''', params)
            
            conn.commit()
            
            if cursor.rowcount > 0:
                return jsonify({
                    'success': True,
                    'message': '작업 종류가 수정되었습니다.'
                })
            else:
                return jsonify({
                    'success': False,
                    'message': '작업 종류를 찾을 수 없습니다.'
                }), 404
        except Exception as e:
            conn.rollback() if USE_POSTGRESQL else None
            print(f'[오류] 작업 종류 수정 오류: {e}')
            import traceback
            traceback.print_exc()
            return jsonify({
                'success': False,
                'message': f'작업 종류 수정 중 오류: {str(e)}'
            }), 500
        finally:
            cursor.close()
            conn.close()
    except Exception as e:
        print(f'[오류] 작업 종류 수정 오류: {e}')
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'message': f'작업 종류 수정 중 오류: {str(e)}'
        }), 500


@special_works_bp.route('/types/<int:type_id>', methods=['DELETE'])
def delete_work_type(type_id):
    """작업 종류 삭제"""
    try:
        user_context = get_user_context()
        if user_context['role'] != '관리자':
            return jsonify({
                'success': False,
                'message': '관리자만 작업 종류를 삭제할 수 있습니다.'
            }), 403
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        try:
            # 사용 중인 작업이 있는지 확인
            if USE_POSTGRESQL:
                cursor.execute('SELECT COUNT(*) FROM special_works WHERE work_type_id = %s', (type_id,))
            else:
                cursor.execute('SELECT COUNT(*) FROM special_works WHERE work_type_id = ?', (type_id,))
            
            count_row = cursor.fetchone()
            count = get_first_value(count_row, 0)
            if count > 0:
                return jsonify({
                    'success': False,
                    'message': f'사용 중인 작업이 {count}건 있어 삭제할 수 없습니다.'
                }), 400
            
            # 삭제
            if USE_POSTGRESQL:
                cursor.execute('DELETE FROM special_work_types WHERE id = %s', (type_id,))
            else:
                cursor.execute('DELETE FROM special_work_types WHERE id = ?', (type_id,))
            
            conn.commit()
            
            if cursor.rowcount > 0:
                return jsonify({
                    'success': True,
                    'message': '작업 종류가 삭제되었습니다.'
                })
            else:
                return jsonify({
                    'success': False,
                    'message': '작업 종류를 찾을 수 없습니다.'
                }), 404
        except Exception as e:
            conn.rollback() if USE_POSTGRESQL else None
            print(f'[오류] 작업 종류 삭제 오류: {e}')
            import traceback
            traceback.print_exc()
            return jsonify({
                'success': False,
                'message': f'작업 종류 삭제 중 오류: {str(e)}'
            }), 500
        finally:
            cursor.close()
            conn.close()
    except Exception as e:
        print(f'❌ 작업 종류 삭제 오류: {e}')
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'message': f'작업 종류 삭제 중 오류: {str(e)}'
        }), 500


# ========== 작업 관련 API ==========

@special_works_bp.route('/works', methods=['GET'])
def get_works():
    """작업 목록 조회"""
    try:
        user_context = get_user_context()
        role = user_context['role']
        company_name = user_context['company_name']
        
        # 필터 파라미터
        start_date = request.args.get('start_date', '').strip()
        end_date = request.args.get('end_date', '').strip()
        work_type_id = request.args.get('work_type_id', '').strip()
        filter_company_name = request.args.get('company_name', '').strip()
        
        conn = get_db_connection()
        if USE_POSTGRESQL:
            cursor = conn.cursor(cursor_factory=RealDictCursor)
        else:
            cursor = conn.cursor()
        
        try:
            # 화주사는 자신의 작업만 조회
            if role != '관리자':
                if not company_name:
                    return jsonify({
                        'success': False,
                        'data': [],
                        'count': 0,
                        'message': '화주사 정보를 확인할 수 없습니다.'
                    }), 400
                filter_company_name = company_name
            
            # 쿼리 구성
            where_clauses = []
            params = []
            
            if start_date:
                where_clauses.append('sw.work_date >= %s' if USE_POSTGRESQL else 'sw.work_date >= ?')
                params.append(start_date)
            
            if end_date:
                where_clauses.append('sw.work_date <= %s' if USE_POSTGRESQL else 'sw.work_date <= ?')
                params.append(end_date)
            
            if work_type_id:
                where_clauses.append('sw.work_type_id = %s' if USE_POSTGRESQL else 'sw.work_type_id = ?')
                params.append(int(work_type_id))
            
            if filter_company_name:
                where_clauses.append('sw.company_name = %s' if USE_POSTGRESQL else 'sw.company_name = ?')
                params.append(filter_company_name)
            
            where_sql = ' AND '.join(where_clauses) if where_clauses else '1=1'
            
            # JOIN으로 작업 종류명 가져오기
            query = f'''
                SELECT 
                    sw.id,
                    sw.company_name,
                    sw.work_type_id,
                    swt.name as work_type_name,
                    sw.work_date,
                    sw.quantity,
                    sw.unit_price,
                    sw.total_price,
                    sw.photo_links,
                    sw.memo,
                    sw.created_at,
                    sw.updated_at
                FROM special_works sw
                LEFT JOIN special_work_types swt ON sw.work_type_id = swt.id
                WHERE {where_sql}
                ORDER BY sw.work_date DESC, sw.created_at DESC
            '''
            
            cursor.execute(query, params)
            rows = cursor.fetchall()
            # SQLite Row 객체는 dict()로 변환 가능, PostgreSQL RealDictCursor는 이미 dict
            result = [dict(row) for row in rows]
            
            # datetime 객체를 문자열로 변환
            for item in result:
                for key, value in item.items():
                    if isinstance(value, datetime):
                        item[key] = value.strftime('%Y-%m-%d %H:%M:%S') if value else None
                    elif isinstance(value, date):
                        item[key] = value.strftime('%Y-%m-%d') if value else None
            
            return jsonify({
                'success': True,
                'data': result,
                'count': len(result)
            })
        finally:
            cursor.close()
            conn.close()
    except Exception as e:
        print(f'[오류] 작업 목록 조회 오류: {e}')
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'data': [],
            'count': 0,
            'message': f'작업 목록 조회 중 오류: {str(e)}'
        }), 500


@special_works_bp.route('/works/<int:work_id>', methods=['GET'])
def get_work(work_id):
    """작업 상세 조회"""
    try:
        user_context = get_user_context()
        role = user_context['role']
        company_name = user_context['company_name']
        
        conn = get_db_connection()
        if USE_POSTGRESQL:
            cursor = conn.cursor(cursor_factory=RealDictCursor)
        else:
            cursor = conn.cursor()
        
        try:
            # 작업 조회
            if USE_POSTGRESQL:
                cursor.execute('''
                    SELECT 
                        sw.id,
                        sw.company_name,
                        sw.work_type_id,
                        swt.name as work_type_name,
                        sw.work_date,
                        sw.quantity,
                        sw.unit_price,
                        sw.total_price,
                        sw.photo_links,
                        sw.memo,
                        sw.created_at,
                        sw.updated_at
                    FROM special_works sw
                    LEFT JOIN special_work_types swt ON sw.work_type_id = swt.id
                    WHERE sw.id = %s
                ''', (work_id,))
            else:
                cursor.execute('''
                    SELECT 
                        sw.id,
                        sw.company_name,
                        sw.work_type_id,
                        swt.name as work_type_name,
                        sw.work_date,
                        sw.quantity,
                        sw.unit_price,
                        sw.total_price,
                        sw.photo_links,
                        sw.memo,
                        sw.created_at,
                        sw.updated_at
                    FROM special_works sw
                    LEFT JOIN special_work_types swt ON sw.work_type_id = swt.id
                    WHERE sw.id = ?
                ''', (work_id,))
            
            row = cursor.fetchone()
            if not row:
                return jsonify({
                    'success': False,
                    'data': None,
                    'message': '작업을 찾을 수 없습니다.'
                }), 404
            
            result = dict(row)
            
            # 화주사는 자신의 작업만 조회 가능
            if role != '관리자':
                if not company_name or result.get('company_name') != company_name:
                    return jsonify({
                        'success': False,
                        'data': None,
                        'message': '작업을 찾을 수 없습니다.'
                    }), 404
            
            # datetime 객체를 문자열로 변환
            for key, value in result.items():
                if isinstance(value, datetime):
                    result[key] = value.strftime('%Y-%m-%d %H:%M:%S') if value else None
                elif isinstance(value, date):
                    result[key] = value.strftime('%Y-%m-%d') if value else None
            
            return jsonify({
                'success': True,
                'data': result
            })
        finally:
            cursor.close()
            conn.close()
    except Exception as e:
        print(f'[오류] 작업 상세 조회 오류: {e}')
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'data': None,
            'message': f'작업 상세 조회 중 오류: {str(e)}'
        }), 500


@special_works_bp.route('/works/bulk', methods=['POST'])
def create_works_bulk():
    """여러 작업을 동시에 등록"""
    try:
        user_context = get_user_context()
        if user_context['role'] != '관리자':
            return jsonify({
                'success': False,
                'message': '관리자만 작업을 등록할 수 있습니다.'
            }), 403
        
        data = request.get_json() or {}
        company_name = data.get('company_name', '').strip()
        work_date = data.get('work_date', '').strip()
        entries = data.get('entries', [])
        photo_links = data.get('photo_links', '').strip()
        memo = data.get('memo', '').strip()
        existing_batch_id = data.get('batch_id')  # 기존 배치 ID (선택사항)
        
        # 배치 ID 디버깅 로그
        print(f'[SW] bulk API 호출 - 기존 배치 ID: {existing_batch_id} (타입: {type(existing_batch_id)}), company: {company_name}, date: {work_date}, entries: {len(entries) if entries else 0}')
        
        if not company_name:
            return jsonify({
                'success': False,
                'message': '화주사명은 필수입니다.'
            }), 400
        
        if not work_date:
            return jsonify({
                'success': False,
                'message': '작업 일자는 필수입니다.'
            }), 400
        
        if not entries or not isinstance(entries, list):
            return jsonify({
                'success': False,
                'message': '등록할 작업 항목이 없습니다.'
            }), 400
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        try:
            normalized_entries = []
            total_amount = 0
            
            for entry in entries:
                work_type_id = entry.get('work_type_id')
                quantity = entry.get('quantity')
                unit_price = entry.get('unit_price')
                
                if not work_type_id:
                    conn.rollback()
                    return jsonify({
                        'success': False,
                        'message': '작업 종류는 필수입니다.'
                    }), 400
                
                try:
                    quantity_value = float(quantity)
                except (TypeError, ValueError):
                    conn.rollback()
                    return jsonify({
                        'success': False,
                        'message': '수량은 숫자여야 합니다.'
                    }), 400
                
                try:
                    unit_price_value = int(round(float(unit_price)))
                except (TypeError, ValueError):
                    conn.rollback()
                    return jsonify({
                        'success': False,
                        'message': '단가는 숫자여야 합니다.'
                    }), 400
                
                if quantity_value <= 0:
                    conn.rollback()
                    return jsonify({
                        'success': False,
                        'message': '수량은 0보다 커야 합니다.'
                    }), 400
                
                if unit_price_value < 0:
                    conn.rollback()
                    return jsonify({
                        'success': False,
                        'message': '단가는 0 이상이어야 합니다.'
                    }), 400
                
                total_price_value = int(round(quantity_value * unit_price_value))
                total_amount += total_price_value
                
                normalized_entries.append({
                    'work_type_id': int(work_type_id),
                    'quantity': quantity_value,
                    'unit_price': unit_price_value,
                    'total_price': total_price_value
                })
            
            created_ids = []
            for entry in normalized_entries:
                params = (
                    company_name,
                    entry['work_type_id'],
                    work_date,
                    entry['quantity'],
                    entry['unit_price'],
                    entry['total_price'],
                    photo_links,
                    memo
                )
                
                if USE_POSTGRESQL:
                    cursor.execute('''
                        INSERT INTO special_works 
                        (company_name, work_type_id, work_date, quantity, unit_price, total_price, photo_links, memo, created_at, updated_at)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                        RETURNING id
                    ''', params)
                    new_row = cursor.fetchone()
                    created_ids.append(get_first_value(new_row))
                else:
                    cursor.execute('''
                        INSERT INTO special_works 
                        (company_name, work_type_id, work_date, quantity, unit_price, total_price, photo_links, memo, created_at, updated_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                    ''', params)
                    created_ids.append(cursor.lastrowid)
            
            batch_id = None
            entry_count = len(created_ids)
            if entry_count > 0:
                # 기존 배치 ID가 제공되면 기존 배치에 추가, 없으면 새 배치 생성
                if existing_batch_id is not None and existing_batch_id != '' and existing_batch_id != 0:
                    try:
                        batch_id = int(existing_batch_id)
                        print(f'[SW] 배치 ID 변환 성공: {batch_id} (원본: {existing_batch_id}, 타입: {type(existing_batch_id)})')
                        
                        # 기존 배치 존재 확인
                        if USE_POSTGRESQL:
                            cursor.execute('SELECT id, company_name, work_date FROM special_work_batches WHERE id = %s', (batch_id,))
                        else:
                            cursor.execute('SELECT id, company_name, work_date FROM special_work_batches WHERE id = ?', (batch_id,))
                        batch_exists = cursor.fetchone()
                        
                        if batch_exists:
                            batch_info = dict(batch_exists) if isinstance(batch_exists, dict) else {'id': batch_exists[0], 'company_name': batch_exists[1] if len(batch_exists) > 1 else None, 'work_date': batch_exists[2] if len(batch_exists) > 2 else None}
                            print(f'[SW] 기존 배치 발견: ID={batch_id}, 화주사={batch_info.get("company_name")}, 날짜={batch_info.get("work_date")}, 작업 {len(created_ids)}개 추가 시작')
                            
                            # 기존 배치에 작업 추가
                            added_count = 0
                            for idx, work_id in enumerate(created_ids, 1):
                                try:
                                    if USE_POSTGRESQL:
                                        cursor.execute('''
                                            INSERT INTO special_work_batch_items (batch_id, work_id, created_at)
                                            VALUES (%s, %s, CURRENT_TIMESTAMP)
                                        ''', (batch_id, work_id))
                                    else:
                                        cursor.execute('''
                                            INSERT INTO special_work_batch_items (batch_id, work_id, created_at)
                                            VALUES (?, ?, CURRENT_TIMESTAMP)
                                        ''', (batch_id, work_id))
                                    added_count += 1
                                    print(f'[SW] 작업 {work_id}를 배치 {batch_id}에 추가 완료 ({added_count}/{len(created_ids)})')
                                except Exception as e:
                                    print(f'[SW] 작업 {work_id} 배치 추가 오류: {e}')
                                    import traceback
                                    traceback.print_exc()
                                    raise
                            
                            print(f'[SW] 총 {added_count}개 작업을 배치 {batch_id}에 추가 완료')
                            
                            # 배치 요약 정보 재계산
                            recalculate_batch_summary(cursor, batch_id)
                            print(f'[SW] 배치 요약 정보 재계산 완료: {batch_id}')
                            
                            # 커밋 전 배치 아이템 확인
                            if USE_POSTGRESQL:
                                cursor.execute('SELECT COUNT(*) FROM special_work_batch_items WHERE batch_id = %s', (batch_id,))
                            else:
                                cursor.execute('SELECT COUNT(*) FROM special_work_batch_items WHERE batch_id = ?', (batch_id,))
                            item_row = cursor.fetchone()
                            item_count = get_first_value(item_row, 0)
                            print(f'[SW] 배치 {batch_id}의 총 작업 항목 수: {item_count}')
                            
                            # 배치 ID를 반환값에 포함 (기존 배치 사용)
                            print(f'[SW] ✅ 기존 배치 {batch_id}에 작업 추가 완료, 커밋 대기')
                        else:
                            print(f'[SW] ❌ 배치가 존재하지 않음: {batch_id}, 새 배치 생성')
                            batch_id = None
                    except (ValueError, TypeError) as e:
                        print(f'[SW] ❌ 배치 ID 변환 오류: {existing_batch_id} -> {e}, 새 배치 생성')
                        import traceback
                        traceback.print_exc()
                        batch_id = None
                else:
                    # 배치 ID가 제공되지 않았거나 유효하지 않음 - 새 배치 생성
                    print(f'[SW] 배치 ID가 제공되지 않음 (값: {existing_batch_id}, 타입: {type(existing_batch_id)}), 새 배치 생성')
                    batch_id = None
                
                # 배치 ID가 None이면 새 배치 생성
                if batch_id is None:
                    print(f'[SW] 새 배치 생성 (batch_id 없음)')
                    if USE_POSTGRESQL:
                        cursor.execute('''
                            INSERT INTO special_work_batches
                            (company_name, work_date, total_amount, entry_count, photo_links, memo, created_at, updated_at)
                            VALUES (%s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                            RETURNING id
                        ''', (company_name, work_date, total_amount, entry_count, photo_links, memo))
                        new_batch_row = cursor.fetchone()
                        batch_id = get_first_value(new_batch_row)
                    else:
                        cursor.execute('''
                            INSERT INTO special_work_batches
                            (company_name, work_date, total_amount, entry_count, photo_links, memo, created_at, updated_at)
                            VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                        ''', (company_name, work_date, total_amount, entry_count, photo_links, memo))
                        batch_id = cursor.lastrowid
                    
                    for work_id in created_ids:
                        if USE_POSTGRESQL:
                            cursor.execute('''
                                INSERT INTO special_work_batch_items (batch_id, work_id, created_at)
                                VALUES (%s, %s, CURRENT_TIMESTAMP)
                            ''', (batch_id, work_id))
                        else:
                            cursor.execute('''
                                INSERT INTO special_work_batch_items (batch_id, work_id, created_at)
                                VALUES (?, ?, CURRENT_TIMESTAMP)
                            ''', (batch_id, work_id))
            
            # 커밋 전 최종 확인
            if batch_id:
                if USE_POSTGRESQL:
                    cursor.execute('SELECT COUNT(*) FROM special_work_batch_items WHERE batch_id = %s', (batch_id,))
                else:
                    cursor.execute('SELECT COUNT(*) FROM special_work_batch_items WHERE batch_id = ?', (batch_id,))
                final_row = cursor.fetchone()
                final_count = get_first_value(final_row, 0)
                print(f'[SW] 커밋 전 최종 확인: 배치 {batch_id}의 작업 항목 수 = {final_count}')
            
            conn.commit()
            print(f'[SW] 커밋 완료: 작업 {len(created_ids)}개, 배치 ID = {batch_id}')
            
            return jsonify({
                'success': True,
                'message': f'{entry_count}개의 작업이 등록되었습니다.',
                'created_ids': created_ids,
                'total_amount': total_amount,
                'batch_id': batch_id
            })
        except Exception as e:
            conn.rollback() if USE_POSTGRESQL else None
            print(f'[오류] 다중 작업 등록 오류: {e}')
            import traceback
            traceback.print_exc()
            return jsonify({
                'success': False,
                'message': f'작업 등록 중 오류: {str(e)}'
            }), 500
        finally:
            cursor.close()
            conn.close()
    except Exception as e:
        print(f'❌ 다중 작업 등록 오류: {e}')
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'message': f'작업 등록 중 오류: {str(e)}'
        }), 500


@special_works_bp.route('/works/batches', methods=['GET'])
def get_work_batches():
    """작업 배치 목록 조회"""
    try:
        user_context = get_user_context()
        role = user_context['role']
        company_name = user_context['company_name']
        
        start_date = request.args.get('start_date', '').strip()
        end_date = request.args.get('end_date', '').strip()
        work_type_id = request.args.get('work_type_id', '').strip()
        filter_company_name = request.args.get('company_name', '').strip()
        batch_id_filter = request.args.get('batch_id', '').strip()
        
        conn = get_db_connection()
        if USE_POSTGRESQL:
            cursor = conn.cursor(cursor_factory=RealDictCursor)
        else:
            cursor = conn.cursor()
        
        try:
            if role != '관리자':
                if not company_name:
                    return jsonify({
                        'success': False,
                        'data': [],
                        'count': 0,
                        'message': '화주사 정보를 확인할 수 없습니다.'
                    }), 400
                filter_company_name = company_name
            
            work_type_filter = None
            if work_type_id:
                try:
                    work_type_filter = int(work_type_id)
                except ValueError:
                    work_type_filter = None
            
            batch_clauses = []
            batch_params = []
            orphan_clauses = []
            orphan_params = []
            
            # 배치 ID 필터 (특정 배치만 조회)
            if batch_id_filter:
                try:
                    batch_id_int = int(batch_id_filter)
                    clause = 'b.id = %s' if USE_POSTGRESQL else 'b.id = ?'
                    batch_clauses.append(clause)
                    batch_params.append(batch_id_int)
                    print(f'[SW] 배치 ID 필터 적용: {batch_id_int}')
                except ValueError:
                    pass
            
            if start_date:
                clause = 'b.work_date >= %s' if USE_POSTGRESQL else 'b.work_date >= ?'
                batch_clauses.append(clause)
                batch_params.append(start_date)
                clause_orphan = 'sw.work_date >= %s' if USE_POSTGRESQL else 'sw.work_date >= ?'
                orphan_clauses.append(clause_orphan)
                orphan_params.append(start_date)
            
            if end_date:
                clause = 'b.work_date <= %s' if USE_POSTGRESQL else 'b.work_date <= ?'
                batch_clauses.append(clause)
                batch_params.append(end_date)
                clause_orphan = 'sw.work_date <= %s' if USE_POSTGRESQL else 'sw.work_date <= ?'
                orphan_clauses.append(clause_orphan)
                orphan_params.append(end_date)
            
            if filter_company_name:
                clause = 'b.company_name = %s' if USE_POSTGRESQL else 'b.company_name = ?'
                batch_clauses.append(clause)
                batch_params.append(filter_company_name)
                clause_orphan = 'sw.company_name = %s' if USE_POSTGRESQL else 'sw.company_name = ?'
                orphan_clauses.append(clause_orphan)
                orphan_params.append(filter_company_name)
            
            # 작업 종류 필터는 배치 레벨이 아닌 작업 항목 레벨에서 적용하지 않음
            # 배치에 속한 모든 작업 항목을 가져와야 함
            # 작업 종류 필터는 프론트엔드에서 렌더링 시 적용
            
            batch_where_sql = ' AND '.join(batch_clauses) if batch_clauses else '1=1'
            orphan_where_sql = ' AND '.join(orphan_clauses) if orphan_clauses else '1=1'
            
            # 작업 종류 필터는 orphan 작업에만 적용 (배치에 속하지 않은 작업)
            if work_type_filter is not None:
                orphan_clauses.append('sw.work_type_id = %s' if USE_POSTGRESQL else 'sw.work_type_id = ?')
                orphan_params.append(work_type_filter)
                orphan_where_sql = ' AND '.join(orphan_clauses) if orphan_clauses else '1=1'
            
            # 배치 조회 전에 모든 고아 레코드 정리 (SQLite에서만 실행)
            orphan_deleted_count = 0
            if not USE_POSTGRESQL:
                print(f'[SW] (SQLite) 배치 조회 전 고아 레코드 정리 시작')
                cursor.execute('''
                    DELETE FROM special_work_batch_items
                    WHERE work_id NOT IN (SELECT id FROM special_works)
                ''')
                orphan_deleted_count = cursor.rowcount
                if orphan_deleted_count > 0:
                    print(f'[SW] (SQLite) 고아 배치 아이템 {orphan_deleted_count}개 삭제 완료')
                    conn.commit()  # 고아 레코드 삭제 커밋
            else:
                print('[SW] (PostgreSQL) 고아 레코드 정리는 배치 수정 시 처리됨 - 사전 정리 생략')
            
            batch_query = f'''
                SELECT 
                    b.id AS batch_id,
                    b.company_name AS batch_company_name,
                    b.work_date AS batch_work_date,
                    b.total_amount AS batch_total_amount,
                    b.entry_count AS batch_entry_count,
                    b.photo_links AS batch_photo_links,
                    b.memo AS batch_memo,
                    b.created_at AS batch_created_at,
                    b.updated_at AS batch_updated_at,
                    sw.id AS work_id,
                    sw.work_type_id,
                    sw.quantity,
                    sw.unit_price,
                    sw.total_price,
                    sw.photo_links AS work_photo_links,
                    sw.memo AS work_memo,
                    swt.name AS work_type_name
                FROM special_work_batches b
                INNER JOIN special_work_batch_items bi ON b.id = bi.batch_id
                INNER JOIN special_works sw ON bi.work_id = sw.id
                LEFT JOIN special_work_types swt ON sw.work_type_id = swt.id
                WHERE {batch_where_sql}
                ORDER BY b.work_date DESC, b.created_at DESC, sw.id ASC
            '''
            print(f'[SW] 배치 조회 쿼리 실행: batch_where_sql={batch_where_sql}, params={batch_params}')
            cursor.execute(batch_query, batch_params)
            batch_rows = cursor.fetchall()
            batch_dicts = cursor_rows_to_dicts(cursor, batch_rows)
            print(f'[SW] 배치 조회 결과: {len(batch_dicts)}개 행')
            
            # 배치별 실제 아이템 수 확인 (디버깅용)
            if batch_dicts:
                batch_ids_in_query = set(row.get('batch_id') for row in batch_dicts)
                print(f'[SW] 조회된 배치 ID 목록: {sorted(batch_ids_in_query)}')
                for bid in sorted(batch_ids_in_query):
                    if USE_POSTGRESQL:
                        cursor.execute('SELECT COUNT(*) FROM special_work_batch_items WHERE batch_id = %s', (bid,))
                    else:
                        cursor.execute('SELECT COUNT(*) FROM special_work_batch_items WHERE batch_id = ?', (bid,))
                    count_row = cursor.fetchone()
                    actual_item_count = get_first_value(count_row, 0)
                    query_item_count = len([r for r in batch_dicts if r.get('batch_id') == bid])
                    print(f'[SW] 배치 {bid}: DB 아이템 수={actual_item_count}, 쿼리 결과 행 수={query_item_count}')
                    if actual_item_count != query_item_count:
                        print(f'[SW] ⚠️ 배치 {bid} 불일치 감지! DB에는 {actual_item_count}개, 쿼리 결과는 {query_item_count}개')
                        # 누락된 작업 ID 확인
                        if USE_POSTGRESQL:
                            cursor.execute('''
                                SELECT bi.work_id 
                                FROM special_work_batch_items bi
                                LEFT JOIN special_works sw ON bi.work_id = sw.id
                                WHERE bi.batch_id = %s AND sw.id IS NULL
                            ''', (bid,))
                        else:
                            cursor.execute('''
                                SELECT bi.work_id 
                                FROM special_work_batch_items bi
                                LEFT JOIN special_works sw ON bi.work_id = sw.id
                                WHERE bi.batch_id = ? AND sw.id IS NULL
                            ''', (bid,))
                        orphan_items = cursor.fetchall()
                        if orphan_items:
                            orphan_work_ids = [row[0] if not isinstance(row, dict) else row['work_id'] for row in orphan_items]
                            print(f'[SW] 배치 {bid}의 누락된 작업 ID (special_works에 없음): {orphan_work_ids}')
                        # 존재하는 작업 ID 확인
                        if USE_POSTGRESQL:
                            cursor.execute('''
                                SELECT bi.work_id 
                                FROM special_work_batch_items bi
                                INNER JOIN special_works sw ON bi.work_id = sw.id
                                WHERE bi.batch_id = %s
                            ''', (bid,))
                        else:
                            cursor.execute('''
                                SELECT bi.work_id 
                                FROM special_work_batch_items bi
                                INNER JOIN special_works sw ON bi.work_id = sw.id
                                WHERE bi.batch_id = ?
                            ''', (bid,))
                        existing_work_ids = cursor.fetchall()
                        existing_ids = [row[0] if not isinstance(row, dict) else row['work_id'] for row in existing_work_ids]
                        query_work_ids = [r.get('work_id') for r in batch_dicts if r.get('batch_id') == bid]
                        missing_in_query = set(existing_ids) - set(query_work_ids)
                        if missing_in_query:
                            print(f'[SW] 배치 {bid}의 쿼리 결과에서 누락된 작업 ID: {missing_in_query}')
            
            batch_map = {}
            for row in batch_dicts:
                batch_id = row.get('batch_id')
                work_id = row.get('work_id')
                work_type_name = row.get('work_type_name')
                print(f'[SW] 배치 행: batch_id={batch_id}, work_id={work_id}, work_type={work_type_name}, total_price={row.get("total_price")}')
                if batch_id not in batch_map:
                    batch_map[batch_id] = {
                        'batch_id': batch_id,
                        'company_name': row.get('batch_company_name'),
                        'work_date': row.get('batch_work_date'),
                        'total_amount': row.get('batch_total_amount') or 0,  # 초기값은 저장된 값 사용
                        'entry_count': row.get('batch_entry_count') or 0,  # 초기값은 저장된 값 사용
                        'photo_links': row.get('batch_photo_links'),
                        'memo': row.get('batch_memo'),
                        'created_at': row.get('batch_created_at'),
                        'updated_at': row.get('batch_updated_at'),
                        'entries': [],
                        'is_legacy': False
                    }
                    print(f'[SW] 배치 {batch_id} 초기화: 저장된 entry_count={batch_map[batch_id]["entry_count"]}, 저장된 total_amount={batch_map[batch_id]["total_amount"]}')
                entry = {
                    'work_id': work_id,
                    'work_type_id': row.get('work_type_id'),
                    'work_type_name': work_type_name or '',
                    'quantity': row.get('quantity'),
                    'unit_price': row.get('unit_price'),
                    'total_price': row.get('total_price'),
                    'memo': row.get('work_memo'),
                    'photo_links': row.get('work_photo_links')
                }
                batch_map[batch_id]['entries'].append(entry)
                print(f'[SW] 배치 {batch_id}에 작업 {work_id} 추가됨: 현재 항목 수={len(batch_map[batch_id]["entries"])}, 현재 총액={sum(int(e.get("total_price") or 0) for e in batch_map[batch_id]["entries"])}')
            
            # 배치 요약 정보를 실제 항목 기준으로 재계산
            for batch_id, batch_data in batch_map.items():
                # 실제 항목들의 총액과 개수 계산
                actual_entry_count = len(batch_data['entries'])
                actual_total_amount = sum(int(entry.get('total_price') or 0) for entry in batch_data['entries'])
                
                # 배치 테이블의 요약 정보와 실제 항목 정보가 다르면 업데이트
                stored_entry_count = batch_data.get('entry_count', 0)
                stored_total_amount = batch_data.get('total_amount', 0)
                
                print(f'[SW] 배치 {batch_id} 요약 정보 비교: 저장된(entry_count={stored_entry_count}, total_amount={stored_total_amount}) vs 실제(entry_count={actual_entry_count}, total_amount={actual_total_amount})')
                
                if actual_entry_count != stored_entry_count or actual_total_amount != stored_total_amount:
                    print(f'[SW] ⚠️ 배치 {batch_id} 요약 정보 불일치 감지! 저장된 값 업데이트 중...')
                    # 실제 항목 기준으로 업데이트
                    batch_data['entry_count'] = actual_entry_count
                    batch_data['total_amount'] = actual_total_amount
                    
                    # 배치 테이블의 요약 정보도 업데이트 (다음 조회를 위해)
                    if USE_POSTGRESQL:
                        cursor.execute('''
                            UPDATE special_work_batches
                            SET entry_count = %s,
                                total_amount = %s,
                                updated_at = CURRENT_TIMESTAMP
                            WHERE id = %s
                        ''', (actual_entry_count, actual_total_amount, batch_id))
                    else:
                        cursor.execute('''
                            UPDATE special_work_batches
                            SET entry_count = ?,
                                total_amount = ?,
                                updated_at = CURRENT_TIMESTAMP
                            WHERE id = ?
                        ''', (actual_entry_count, actual_total_amount, batch_id))
                    print(f'[SW] ✅ 배치 {batch_id} 요약 정보 업데이트 완료: entry_count={actual_entry_count}, total_amount={actual_total_amount}')
                else:
                    print(f'[SW] ✓ 배치 {batch_id} 요약 정보 일치')
            
            # 변경사항이 있으면 커밋
            updated_batches = [bid for bid, data in batch_map.items() 
                              if len(data['entries']) != data.get('entry_count', 0) 
                              or sum(int(e.get('total_price') or 0) for e in data['entries']) != data.get('total_amount', 0)]
            if updated_batches:
                try:
                    conn.commit()
                    print(f'[SW] 배치 요약 정보 업데이트 커밋 완료: {len(updated_batches)}개 배치 업데이트됨')
                except Exception as e:
                    print(f'[SW] ⚠️ 배치 요약 정보 업데이트 커밋 실패: {e}')
                    conn.rollback() if USE_POSTGRESQL else None
            else:
                print(f'[SW] 배치 요약 정보 업데이트 불필요 (모든 배치 일치)')
            
            orphan_batches = []
            orphan_query = f'''
                SELECT
                    sw.id AS work_id,
                    sw.company_name,
                    sw.work_date,
                    sw.quantity,
                    sw.unit_price,
                    sw.total_price,
                    sw.photo_links,
                    sw.memo,
                    sw.created_at,
                    sw.updated_at,
                    sw.work_type_id,
                    swt.name AS work_type_name
                FROM special_works sw
                LEFT JOIN special_work_batch_items bi ON sw.id = bi.work_id
                LEFT JOIN special_work_types swt ON sw.work_type_id = swt.id
                WHERE bi.id IS NULL AND {orphan_where_sql}
                ORDER BY sw.work_date DESC, sw.created_at DESC
            '''
            cursor.execute(orphan_query, orphan_params)
            orphan_rows = cursor.fetchall()
            orphan_dicts = cursor_rows_to_dicts(cursor, orphan_rows)
            
            for row in orphan_dicts:
                orphan_batches.append({
                    'batch_id': None,
                    'company_name': row.get('company_name'),
                    'work_date': row.get('work_date'),
                    'total_amount': row.get('total_price') or 0,
                    'entry_count': 1,
                    'photo_links': row.get('photo_links'),
                    'memo': row.get('memo'),
                    'created_at': row.get('created_at'),
                    'updated_at': row.get('updated_at'),
                    'entries': [{
                        'work_id': row.get('work_id'),
                        'work_type_id': row.get('work_type_id'),
                        'work_type_name': row.get('work_type_name') or '',
                        'quantity': row.get('quantity'),
                        'unit_price': row.get('unit_price'),
                        'total_price': row.get('total_price'),
                        'memo': row.get('memo'),
                        'photo_links': row.get('photo_links')
                    }],
                    'is_legacy': True
                })
            
            combined_batches = list(batch_map.values()) + orphan_batches
            combined_batches.sort(
                key=lambda item: (
                    format_datetime_value(item.get('work_date')) or '',
                    format_datetime_value(item.get('created_at')) or ''
                ),
                reverse=True
            )
            
            for batch in combined_batches:
                batch['work_date'] = format_datetime_value(batch.get('work_date'))
                batch['created_at'] = format_datetime_value(batch.get('created_at'))
                batch['updated_at'] = format_datetime_value(batch.get('updated_at'))
                for entry in batch.get('entries', []):
                    entry['quantity'] = float(entry['quantity']) if entry.get('quantity') is not None else 0
                    entry['unit_price'] = int(entry['unit_price']) if entry.get('unit_price') is not None else 0
                    entry['total_price'] = int(entry['total_price']) if entry.get('total_price') is not None else 0
            
            return jsonify({
                'success': True,
                'data': combined_batches,
                'count': len(combined_batches)
            })
        finally:
            cursor.close()
            conn.close()
    except Exception as e:
        print(f'[오류] 작업 배치 조회 오류: {e}')
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'data': [],
            'count': 0,
            'message': f'작업 배치 조회 중 오류: {str(e)}'
        }), 500


@special_works_bp.route('/works/batches/<int:batch_id>', methods=['DELETE'])
def delete_work_batch(batch_id):
    """작업 배치 삭제"""
    try:
        user_context = get_user_context()
        if user_context['role'] != '관리자':
            return jsonify({
                'success': False,
                'message': '관리자만 작업을 삭제할 수 있습니다.'
            }), 403
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        try:
            if USE_POSTGRESQL:
                cursor.execute('SELECT work_id FROM special_work_batch_items WHERE batch_id = %s', (batch_id,))
            else:
                cursor.execute('SELECT work_id FROM special_work_batch_items WHERE batch_id = ?', (batch_id,))
            rows = cursor.fetchall()
            work_ids = [row[0] if not isinstance(row, dict) else row['work_id'] for row in rows]
            
            if not work_ids:
                return jsonify({
                    'success': False,
                    'message': '배치를 찾을 수 없습니다.'
                }), 404
            
            for work_id in work_ids:
                if USE_POSTGRESQL:
                    cursor.execute('DELETE FROM special_works WHERE id = %s', (work_id,))
                else:
                    cursor.execute('DELETE FROM special_works WHERE id = ?', (work_id,))
            
            if USE_POSTGRESQL:
                cursor.execute('DELETE FROM special_work_batches WHERE id = %s', (batch_id,))
            else:
                cursor.execute('DELETE FROM special_work_batches WHERE id = ?', (batch_id,))
            
            conn.commit()
            return jsonify({
                'success': True,
                'message': '작업 배치가 삭제되었습니다.'
            })
        except Exception as e:
            conn.rollback() if USE_POSTGRESQL else None
            print(f'[오류] 작업 배치 삭제 오류: {e}')
            import traceback
            traceback.print_exc()
            return jsonify({
                'success': False,
                'message': f'작업 배치 삭제 중 오류: {str(e)}'
            }), 500
        finally:
            cursor.close()
            conn.close()
    except Exception as e:
        print(f'❌ 작업 배치 삭제 오류: {e}')
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'message': f'작업 배치 삭제 중 오류: {str(e)}'
        }), 500


@special_works_bp.route('/works', methods=['POST'])
def create_work():
    """작업 등록"""
    try:
        user_context = get_user_context()
        if user_context['role'] != '관리자':
            return jsonify({
                'success': False,
                'message': '관리자만 작업을 등록할 수 있습니다.'
            }), 403
        
        data = request.get_json()
        company_name = data.get('company_name', '').strip()
        work_type_id = data.get('work_type_id')
        work_date = data.get('work_date', '').strip()
        quantity = data.get('quantity')
        unit_price = data.get('unit_price')
        photo_links = data.get('photo_links', '').strip()
        memo = data.get('memo', '').strip()
        
        # 유효성 검사
        if not company_name:
            return jsonify({
                'success': False,
                'message': '화주사명은 필수입니다.'
            }), 400
        
        if not work_type_id:
            return jsonify({
                'success': False,
                'message': '작업 종류는 필수입니다.'
            }), 400
        
        if not work_date:
            return jsonify({
                'success': False,
                'message': '작업 일자는 필수입니다.'
            }), 400
        
        if quantity is None or quantity <= 0:
            return jsonify({
                'success': False,
                'message': '수량은 0보다 큰 값이어야 합니다.'
            }), 400
        
        if unit_price is None or unit_price < 0:
            return jsonify({
                'success': False,
                'message': '단가는 0 이상이어야 합니다.'
            }), 400
        
        total_price = quantity * unit_price
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        try:
            if USE_POSTGRESQL:
                cursor.execute('''
                    INSERT INTO special_works 
                    (company_name, work_type_id, work_date, quantity, unit_price, total_price, photo_links, memo, created_at, updated_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                    RETURNING id
                ''', (company_name, work_type_id, work_date, quantity, unit_price, total_price, photo_links, memo))
                work_row = cursor.fetchone()
                work_id = get_first_value(work_row)
            else:
                cursor.execute('''
                    INSERT INTO special_works 
                    (company_name, work_type_id, work_date, quantity, unit_price, total_price, photo_links, memo, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                ''', (company_name, work_type_id, work_date, quantity, unit_price, total_price, photo_links, memo))
                work_id = cursor.lastrowid
            
            batch_id = None
            if USE_POSTGRESQL:
                cursor.execute('''
                    INSERT INTO special_work_batches
                    (company_name, work_date, total_amount, entry_count, photo_links, memo, created_at, updated_at)
                    VALUES (%s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                    RETURNING id
                ''', (company_name, work_date, total_price, 1, photo_links, memo))
                batch_row = cursor.fetchone()
                batch_id = get_first_value(batch_row)
                cursor.execute('''
                    INSERT INTO special_work_batch_items (batch_id, work_id, created_at)
                    VALUES (%s, %s, CURRENT_TIMESTAMP)
                ''', (batch_id, work_id))
            else:
                cursor.execute('''
                    INSERT INTO special_work_batches
                    (company_name, work_date, total_amount, entry_count, photo_links, memo, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                ''', (company_name, work_date, total_price, 1, photo_links, memo))
                batch_id = cursor.lastrowid
                cursor.execute('''
                    INSERT INTO special_work_batch_items (batch_id, work_id, created_at)
                    VALUES (?, ?, CURRENT_TIMESTAMP)
                ''', (batch_id, work_id))
            
            conn.commit()
            return jsonify({
                'success': True,
                'message': '작업이 등록되었습니다.',
                'id': work_id,
                'batch_id': batch_id
            })
        except Exception as e:
            conn.rollback() if USE_POSTGRESQL else None
            print(f'[오류] 작업 등록 오류: {e}')
            import traceback
            traceback.print_exc()
            return jsonify({
                'success': False,
                'message': f'작업 등록 중 오류: {str(e)}'
            }), 500
        finally:
            cursor.close()
            conn.close()
    except Exception as e:
        print(f'❌ 작업 등록 오류: {e}')
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'message': f'작업 등록 중 오류: {str(e)}'
        }), 500


@special_works_bp.route('/works/<int:work_id>', methods=['PUT'])
def update_work(work_id):
    """작업 수정"""
    try:
        user_context = get_user_context()
        if user_context['role'] != '관리자':
            return jsonify({
                'success': False,
                'message': '관리자만 작업을 수정할 수 있습니다.'
            }), 403
        
        data = request.get_json()
        company_name = data.get('company_name')
        work_type_id = data.get('work_type_id')
        work_date = data.get('work_date')
        quantity = data.get('quantity')
        unit_price = data.get('unit_price')
        photo_links = data.get('photo_links')
        memo = data.get('memo')
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        if USE_POSTGRESQL:
            cursor.execute('SELECT batch_id FROM special_work_batch_items WHERE work_id = %s', (work_id,))
        else:
            cursor.execute('SELECT batch_id FROM special_work_batch_items WHERE work_id = ?', (work_id,))
        batch_row = cursor.fetchone()
        batch_id = batch_row[0] if batch_row else None
        
        try:
            updates = []
            params = []
            
            if company_name is not None:
                updates.append('company_name = %s' if USE_POSTGRESQL else 'company_name = ?')
                params.append(company_name.strip())
            
            if work_type_id is not None:
                updates.append('work_type_id = %s' if USE_POSTGRESQL else 'work_type_id = ?')
                params.append(int(work_type_id))
            
            if work_date is not None:
                updates.append('work_date = %s' if USE_POSTGRESQL else 'work_date = ?')
                params.append(work_date.strip())
            
            if quantity is not None:
                updates.append('quantity = %s' if USE_POSTGRESQL else 'quantity = ?')
                params.append(float(quantity))
            
            if unit_price is not None:
                updates.append('unit_price = %s' if USE_POSTGRESQL else 'unit_price = ?')
                params.append(int(unit_price))
            
            if photo_links is not None:
                updates.append('photo_links = %s' if USE_POSTGRESQL else 'photo_links = ?')
                params.append(photo_links.strip())
            
            if memo is not None:
                updates.append('memo = %s' if USE_POSTGRESQL else 'memo = ?')
                params.append(memo.strip())
            
            if not updates:
                return jsonify({
                    'success': False,
                    'message': '수정할 데이터가 없습니다.'
                }), 400
            
            # quantity와 unit_price가 모두 있으면 total_price 계산
            if quantity is not None and unit_price is not None:
                total_price = float(quantity) * int(unit_price)
                updates.append('total_price = %s' if USE_POSTGRESQL else 'total_price = ?')
                params.append(int(total_price))
            elif quantity is not None or unit_price is not None:
                # 하나만 변경된 경우 기존 값으로 계산
                if USE_POSTGRESQL:
                    cursor.execute('SELECT quantity, unit_price FROM special_works WHERE id = %s', (work_id,))
                else:
                    cursor.execute('SELECT quantity, unit_price FROM special_works WHERE id = ?', (work_id,))
                existing = cursor.fetchone()
                if existing:
                    existing_quantity = float(quantity) if quantity is not None else existing[0]
                    existing_unit_price = int(unit_price) if unit_price is not None else existing[1]
                    total_price = existing_quantity * existing_unit_price
                    updates.append('total_price = %s' if USE_POSTGRESQL else 'total_price = ?')
                    params.append(int(total_price))
            
            updates.append('updated_at = CURRENT_TIMESTAMP')
            params.append(work_id)
            
            if USE_POSTGRESQL:
                cursor.execute(f'''
                    UPDATE special_works 
                    SET {', '.join(updates)}
                    WHERE id = %s
                ''', params)
            else:
                cursor.execute(f'''
                    UPDATE special_works 
                    SET {', '.join(updates)}
                    WHERE id = ?
                ''', params)
            
            if batch_id:
                recalculate_batch_summary(cursor, batch_id)
                
                # 배치의 기본 정보(화주사, 작업 일자)도 함께 업데이트
                batch_updates = []
                batch_params = []
                if company_name is not None:
                    batch_updates.append('company_name = %s' if USE_POSTGRESQL else 'company_name = ?')
                    batch_params.append(company_name.strip())
                if work_date is not None:
                    batch_updates.append('work_date = %s' if USE_POSTGRESQL else 'work_date = ?')
                    batch_params.append(work_date.strip())
                
                if batch_updates:
                    batch_updates.append('updated_at = CURRENT_TIMESTAMP')
                    batch_params.append(batch_id)
                    if USE_POSTGRESQL:
                        cursor.execute(f'''
                            UPDATE special_work_batches
                            SET {', '.join(batch_updates)}
                            WHERE id = %s
                        ''', batch_params)
                    else:
                        cursor.execute(f'''
                            UPDATE special_work_batches
                            SET {', '.join(batch_updates)}
                            WHERE id = ?
                        ''', batch_params)
            
            conn.commit()
            
            if cursor.rowcount > 0:
                return jsonify({
                    'success': True,
                    'message': '작업이 수정되었습니다.'
                })
            else:
                return jsonify({
                    'success': False,
                    'message': '작업을 찾을 수 없습니다.'
                }), 404
        except Exception as e:
            conn.rollback() if USE_POSTGRESQL else None
            print(f'[오류] 작업 수정 오류: {e}')
            import traceback
            traceback.print_exc()
            return jsonify({
                'success': False,
                'message': f'작업 수정 중 오류: {str(e)}'
            }), 500
        finally:
            cursor.close()
            conn.close()
    except Exception as e:
        print(f'❌ 작업 수정 오류: {e}')
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'message': f'작업 수정 중 오류: {str(e)}'
        }), 500


@special_works_bp.route('/works/<int:work_id>', methods=['DELETE'])
def delete_work(work_id):
    """작업 삭제"""
    try:
        user_context = get_user_context()
        if user_context['role'] != '관리자':
            return jsonify({
                'success': False,
                'message': '관리자만 작업을 삭제할 수 있습니다.'
            }), 403
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        if USE_POSTGRESQL:
            cursor.execute('SELECT batch_id FROM special_work_batch_items WHERE work_id = %s', (work_id,))
        else:
            cursor.execute('SELECT batch_id FROM special_work_batch_items WHERE work_id = ?', (work_id,))
        batch_row = cursor.fetchone()
        batch_id = batch_row[0] if batch_row else None
        
        try:
            # 먼저 배치 아이템에서 삭제 (외래 키 제약 조건 때문에)
            if USE_POSTGRESQL:
                cursor.execute('DELETE FROM special_work_batch_items WHERE work_id = %s', (work_id,))
            else:
                cursor.execute('DELETE FROM special_work_batch_items WHERE work_id = ?', (work_id,))
            batch_item_deleted = cursor.rowcount
            print(f'[SW] 작업 {work_id} 삭제: 배치 아이템 {batch_item_deleted}개 삭제됨')
            
            # 그 다음 작업 삭제
            if USE_POSTGRESQL:
                cursor.execute('DELETE FROM special_works WHERE id = %s', (work_id,))
            else:
                cursor.execute('DELETE FROM special_works WHERE id = ?', (work_id,))
            work_deleted = cursor.rowcount
            print(f'[SW] 작업 {work_id} 삭제: 작업 {work_deleted}개 삭제됨')
            
            if work_deleted > 0:
                if batch_id:
                    recalculate_batch_summary(cursor, batch_id)
                    print(f'[SW] 작업 {work_id} 삭제: 배치 {batch_id} 요약 정보 재계산 완료')
                conn.commit()
                print(f'[SW] 작업 {work_id} 삭제 완료 및 커밋')
                return jsonify({
                    'success': True,
                    'message': '작업이 삭제되었습니다.'
                })
            else:
                conn.commit()
                print(f'[SW] 작업 {work_id} 삭제 실패: 작업을 찾을 수 없음')
                return jsonify({
                    'success': False,
                    'message': '작업을 찾을 수 없습니다.'
                }), 404
        except Exception as e:
            conn.rollback() if USE_POSTGRESQL else None
            print(f'[오류] 작업 삭제 오류: {e}')
            import traceback
            traceback.print_exc()
            return jsonify({
                'success': False,
                'message': f'작업 삭제 중 오류: {str(e)}'
            }), 500
        finally:
            cursor.close()
            conn.close()
    except Exception as e:
        print(f'❌ 작업 삭제 오류: {e}')
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'message': f'작업 삭제 중 오류: {str(e)}'
        }), 500
