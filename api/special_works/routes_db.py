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
            
            conn.commit()
            return jsonify({
                'success': True,
                'message': '작업이 등록되었습니다.',
                'id': work_id
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
        
        try:
            if USE_POSTGRESQL:
                cursor.execute('DELETE FROM special_works WHERE id = %s', (work_id,))
            else:
                cursor.execute('DELETE FROM special_works WHERE id = ?', (work_id,))
            
            conn.commit()
            
            if cursor.rowcount > 0:
                return jsonify({
                    'success': True,
                    'message': '작업이 삭제되었습니다.'
                })
            else:
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
