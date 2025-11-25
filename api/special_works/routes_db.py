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
                work_type_id = cursor.fetchone()[0]
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
            
            count = cursor.fetchone()[0]
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
                    created_ids.append(cursor.fetchone()[0])
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
                if USE_POSTGRESQL:
                    cursor.execute('''
                        INSERT INTO special_work_batches
                        (company_name, work_date, total_amount, entry_count, photo_links, memo, created_at, updated_at)
                        VALUES (%s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                        RETURNING id
                    ''', (company_name, work_date, total_amount, entry_count, photo_links, memo))
                    batch_id = cursor.fetchone()[0]
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
            
            conn.commit()
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
            
            if work_type_filter is not None:
                clause = 'sw.work_type_id = %s' if USE_POSTGRESQL else 'sw.work_type_id = ?'
                batch_clauses.append(clause)
                batch_params.append(work_type_filter)
                orphan_clauses.append(clause)
                orphan_params.append(work_type_filter)
            
            batch_where_sql = ' AND '.join(batch_clauses) if batch_clauses else '1=1'
            orphan_where_sql = ' AND '.join(orphan_clauses) if orphan_clauses else '1=1'
            
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
                JOIN special_work_batch_items bi ON b.id = bi.batch_id
                JOIN special_works sw ON bi.work_id = sw.id
                LEFT JOIN special_work_types swt ON sw.work_type_id = swt.id
                WHERE {batch_where_sql}
                ORDER BY b.work_date DESC, b.created_at DESC, sw.id ASC
            '''
            cursor.execute(batch_query, batch_params)
            batch_rows = cursor.fetchall()
            batch_dicts = cursor_rows_to_dicts(cursor, batch_rows)
            
            batch_map = {}
            for row in batch_dicts:
                batch_id = row.get('batch_id')
                if batch_id not in batch_map:
                    batch_map[batch_id] = {
                        'batch_id': batch_id,
                        'company_name': row.get('batch_company_name'),
                        'work_date': row.get('batch_work_date'),
                        'total_amount': row.get('batch_total_amount') or 0,
                        'entry_count': row.get('batch_entry_count') or 0,
                        'photo_links': row.get('batch_photo_links'),
                        'memo': row.get('batch_memo'),
                        'created_at': row.get('batch_created_at'),
                        'updated_at': row.get('batch_updated_at'),
                        'entries': [],
                        'is_legacy': False
                    }
                batch_map[batch_id]['entries'].append({
                    'work_id': row.get('work_id'),
                    'work_type_id': row.get('work_type_id'),
                    'work_type_name': row.get('work_type_name') or '',
                    'quantity': row.get('quantity'),
                    'unit_price': row.get('unit_price'),
                    'total_price': row.get('total_price'),
                    'memo': row.get('work_memo'),
                    'photo_links': row.get('work_photo_links')
                })
            
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
                work_id = cursor.fetchone()[0]
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
                batch_id = cursor.fetchone()[0]
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
            if USE_POSTGRESQL:
                cursor.execute('DELETE FROM special_works WHERE id = %s', (work_id,))
            else:
                cursor.execute('DELETE FROM special_works WHERE id = ?', (work_id,))
            
            conn.commit()
            
            if cursor.rowcount > 0:
                if batch_id:
                    recalculate_batch_summary(cursor, batch_id)
                conn.commit()
                return jsonify({
                    'success': True,
                    'message': '작업이 삭제되었습니다.'
                })
            else:
                conn.commit()
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
