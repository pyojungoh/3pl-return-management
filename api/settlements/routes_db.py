"""
정산 관리 API 라우트
"""
from flask import Blueprint, request, jsonify, Response
from api.database.models import (
    get_db_connection,
    USE_POSTGRESQL,
    normalize_company_name,
    get_company_search_keywords
)
from datetime import datetime, date
from urllib.parse import unquote
import os
import uuid
import base64 as base64_lib

if USE_POSTGRESQL:
    from psycopg2.extras import RealDictCursor

# Blueprint 생성
settlements_bp = Blueprint('settlements', __name__, url_prefix='/api/settlements')


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


# ========== 정산 목록 조회 ==========

@settlements_bp.route('/list', methods=['GET'])
def get_settlements_list():
    """정산 목록 조회"""
    try:
        user_context = get_user_context()
        role = user_context['role']
        company_name = user_context['company_name']
        
        # 필터 파라미터
        settlement_year_month = request.args.get('settlement_year_month', '').strip()
        filter_company_name = request.args.get('company_name', '').strip()
        
        conn = get_db_connection()
        if USE_POSTGRESQL:
            cursor = conn.cursor(cursor_factory=RealDictCursor)
        else:
            cursor = conn.cursor()
        
        try:
            # 화주사는 자신의 정산만 조회
            if role != '관리자':
                if not company_name:
                    return jsonify({
                        'success': False,
                        'data': [],
                        'count': 0,
                        'message': '화주사 정보를 확인할 수 없습니다.'
                    }), 400
                filter_company_name = company_name
            
            # 필터 파라미터 - status
            filter_status = request.args.get('status', '').strip()
            
            # 쿼리 구성
            where_clauses = []
            params = []
            
            if settlement_year_month:
                where_clauses.append('s.settlement_year_month = %s' if USE_POSTGRESQL else 's.settlement_year_month = ?')
                params.append(settlement_year_month)
            
            if filter_company_name:
                where_clauses.append('s.company_name = %s' if USE_POSTGRESQL else 's.company_name = ?')
                params.append(filter_company_name)
            
            if filter_status:
                # '전달' 상태 필터인 경우, '전달' 이상의 상태 (전달, 정산확인, 입금완료) 모두 조회
                if filter_status == '전달':
                    where_clauses.append('s.status IN (%s, %s, %s)' if USE_POSTGRESQL else 's.status IN (?, ?, ?)')
                    params.extend(['전달', '정산확인', '입금완료'])
                else:
                    where_clauses.append('s.status = %s' if USE_POSTGRESQL else 's.status = ?')
                    params.append(filter_status)
            
            where_sql = ' AND '.join(where_clauses) if where_clauses else '1=1'
            
            query = f'''
                SELECT 
                    s.id,
                    s.company_name,
                    s.settlement_year_month,
                    s.work_fee,
                    s.work_fee_file_url,
                    s.inout_fee,
                    s.inout_fee_file_url,
                    s.shipping_fee,
                    s.shipping_fee_file_url,
                    s.storage_fee,
                    s.special_work_fee,
                    s.error_deduction,
                    s.collect_on_delivery_fee,
                    s.total_amount,
                    s.status,
                    s.tax_invoice_file_url,
                    s.memo,
                    s.created_at,
                    s.updated_at
                FROM settlements s
                WHERE {where_sql}
                ORDER BY s.settlement_year_month DESC, s.company_name
            '''
            
            cursor.execute(query, params)
            rows = cursor.fetchall()
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
        print(f'[오류] 정산 목록 조회 오류: {e}')
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'data': [],
            'count': 0,
            'message': f'정산 목록 조회 중 오류: {str(e)}'
        }), 500


# ========== 정산 상세 조회 ==========

@settlements_bp.route('/<int:settlement_id>', methods=['GET'])
def get_settlement_detail(settlement_id):
    """정산 상세 조회"""
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
            # 정산 정보 조회
            if USE_POSTGRESQL:
                cursor.execute('SELECT * FROM settlements WHERE id = %s', (settlement_id,))
            else:
                cursor.execute('SELECT * FROM settlements WHERE id = ?', (settlement_id,))
            
            row = cursor.fetchone()
            if not row:
                return jsonify({
                    'success': False,
                    'message': '정산을 찾을 수 없습니다.'
                }), 404
            
            settlement = dict(row)
            
            # 화주사는 자신의 정산만 조회 가능
            if role != '관리자':
                if settlement.get('company_name') != company_name:
                    return jsonify({
                        'success': False,
                        'message': '권한이 없습니다.'
                    }), 403
            
            # 첨부파일 조회
            if USE_POSTGRESQL:
                cursor.execute('SELECT * FROM settlement_files WHERE settlement_id = %s ORDER BY uploaded_at DESC', (settlement_id,))
            else:
                cursor.execute('SELECT * FROM settlement_files WHERE settlement_id = ? ORDER BY uploaded_at DESC', (settlement_id,))
            
            files = cursor.fetchall()
            settlement['files'] = [dict(f) for f in files]
            
            # datetime 객체를 문자열로 변환
            for key, value in settlement.items():
                if isinstance(value, datetime):
                    settlement[key] = value.strftime('%Y-%m-%d %H:%M:%S') if value else None
                elif isinstance(value, date):
                    settlement[key] = value.strftime('%Y-%m-%d') if value else None
            
            for file in settlement['files']:
                for key, value in file.items():
                    if isinstance(value, datetime):
                        file[key] = value.strftime('%Y-%m-%d %H:%M:%S') if value else None
            
            return jsonify({
                'success': True,
                'data': settlement
            })
        finally:
            cursor.close()
            conn.close()
    except Exception as e:
        print(f'[오류] 정산 상세 조회 오류: {e}')
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'message': f'정산 상세 조회 중 오류: {str(e)}'
        }), 500


# ========== 정산 생성/수정 ==========

@settlements_bp.route('/', methods=['POST'])
def create_settlement():
    """정산 생성"""
    try:
        user_context = get_user_context()
        role = user_context['role']
        company_name = user_context['company_name']
        
        # 관리자만 정산 생성 가능
        if role != '관리자':
            return jsonify({
                'success': False,
                'message': '관리자만 정산을 생성할 수 있습니다.'
            }), 403
        
        data = request.get_json()
        settlement_company_name = data.get('company_name', '').strip()
        settlement_year_month = data.get('settlement_year_month', '').strip()
        
        if not settlement_company_name or not settlement_year_month:
            return jsonify({
                'success': False,
                'message': '화주사명과 정산년월은 필수입니다.'
            }), 400
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        try:
            # 중복 체크 - 기존 정산이 있으면 UPDATE, 없으면 INSERT
            if USE_POSTGRESQL:
                cursor.execute('SELECT id FROM settlements WHERE company_name = %s AND settlement_year_month = %s', 
                             (settlement_company_name, settlement_year_month))
            else:
                cursor.execute('SELECT id FROM settlements WHERE company_name = ? AND settlement_year_month = ?', 
                             (settlement_company_name, settlement_year_month))
            
            existing = cursor.fetchone()
            
            if existing:
                # 기존 정산이 있으면 UPDATE (임시 정산 업데이트)
                settlement_id = existing[0]
                if USE_POSTGRESQL:
                    cursor.execute('''
                        UPDATE settlements SET
                            work_fee = %s, inout_fee = %s, 
                            shipping_fee = %s, storage_fee = %s,
                            special_work_fee = %s, error_deduction = %s,
                            collect_on_delivery_fee = %s,
                            total_amount = %s, status = %s, memo = %s,
                            updated_at = CURRENT_TIMESTAMP
                        WHERE id = %s
                    ''', (
                        data.get('work_fee', 0), data.get('inout_fee', 0),
                        data.get('shipping_fee', 0), data.get('storage_fee', 0),
                        data.get('special_work_fee', 0), data.get('error_deduction', 0),
                        data.get('collect_on_delivery_fee', 0),
                        data.get('total_amount', 0), data.get('status', '대기'),
                        data.get('memo', ''), settlement_id
                    ))
                else:
                    cursor.execute('''
                        UPDATE settlements SET
                            work_fee = ?, inout_fee = ?, 
                            shipping_fee = ?, storage_fee = ?,
                            special_work_fee = ?, error_deduction = ?,
                            collect_on_delivery_fee = ?,
                            total_amount = ?, status = ?, memo = ?,
                            updated_at = CURRENT_TIMESTAMP
                        WHERE id = ?
                    ''', (
                        data.get('work_fee', 0), data.get('inout_fee', 0),
                        data.get('shipping_fee', 0), data.get('storage_fee', 0),
                        data.get('special_work_fee', 0), data.get('error_deduction', 0),
                        data.get('collect_on_delivery_fee', 0),
                        data.get('total_amount', 0), data.get('status', '대기'),
                        data.get('memo', ''), settlement_id
                    ))
            else:
                # 정산 생성
                if USE_POSTGRESQL:
                    cursor.execute('''
                        INSERT INTO settlements (
                            company_name, settlement_year_month, work_fee, inout_fee, 
                            shipping_fee, storage_fee, special_work_fee, error_deduction,
                            collect_on_delivery_fee, total_amount, status, memo, created_at, updated_at
                        )
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                        RETURNING id
                    ''', (
                        settlement_company_name, settlement_year_month,
                        data.get('work_fee', 0), data.get('inout_fee', 0),
                        data.get('shipping_fee', 0), data.get('storage_fee', 0),
                        data.get('special_work_fee', 0), data.get('error_deduction', 0),
                        data.get('collect_on_delivery_fee', 0),
                        data.get('total_amount', 0), data.get('status', '대기'),
                        data.get('memo', '')
                    ))
                    settlement_id = cursor.fetchone()[0]
                else:
                    cursor.execute('''
                        INSERT INTO settlements (
                            company_name, settlement_year_month, work_fee, inout_fee, 
                            shipping_fee, storage_fee, special_work_fee, error_deduction,
                            collect_on_delivery_fee, total_amount, status, memo, created_at, updated_at
                        )
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                    ''', (
                        settlement_company_name, settlement_year_month,
                        data.get('work_fee', 0), data.get('inout_fee', 0),
                        data.get('shipping_fee', 0), data.get('storage_fee', 0),
                        data.get('special_work_fee', 0), data.get('error_deduction', 0),
                        data.get('collect_on_delivery_fee', 0),
                        data.get('total_amount', 0), data.get('status', '대기'),
                        data.get('memo', '')
                    ))
                    settlement_id = cursor.lastrowid
            
            conn.commit()
            return jsonify({
                'success': True,
                'message': '정산이 생성되었습니다.',
                'id': settlement_id
            })
        except Exception as e:
            conn.rollback() if USE_POSTGRESQL else None
            print(f'[오류] 정산 생성 오류: {e}')
            import traceback
            traceback.print_exc()
            return jsonify({
                'success': False,
                'message': f'정산 생성 중 오류: {str(e)}'
            }), 500
        finally:
            cursor.close()
            conn.close()
    except Exception as e:
        print(f'❌ 정산 생성 오류: {e}')
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'message': f'정산 생성 중 오류: {str(e)}'
        }), 500


@settlements_bp.route('/<int:settlement_id>', methods=['PUT'])
def update_settlement(settlement_id):
    """정산 수정"""
    try:
        user_context = get_user_context()
        role = user_context['role']
        
        # 관리자만 정산 수정 가능
        if role != '관리자':
            return jsonify({
                'success': False,
                'message': '관리자만 정산을 수정할 수 있습니다.'
            }), 403
        
        data = request.get_json()
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        try:
            # 업데이트할 필드 구성
            updates = []
            params = []
            
            if 'work_fee' in data:
                updates.append('work_fee = %s' if USE_POSTGRESQL else 'work_fee = ?')
                params.append(data['work_fee'])
            
            if 'work_fee_file_url' in data:
                updates.append('work_fee_file_url = %s' if USE_POSTGRESQL else 'work_fee_file_url = ?')
                params.append(data['work_fee_file_url'])
            
            if 'inout_fee' in data:
                updates.append('inout_fee = %s' if USE_POSTGRESQL else 'inout_fee = ?')
                params.append(data['inout_fee'])
            
            if 'inout_fee_file_url' in data:
                updates.append('inout_fee_file_url = %s' if USE_POSTGRESQL else 'inout_fee_file_url = ?')
                params.append(data['inout_fee_file_url'])
            
            if 'shipping_fee' in data:
                updates.append('shipping_fee = %s' if USE_POSTGRESQL else 'shipping_fee = ?')
                params.append(data['shipping_fee'])
            
            if 'shipping_fee_file_url' in data:
                updates.append('shipping_fee_file_url = %s' if USE_POSTGRESQL else 'shipping_fee_file_url = ?')
                params.append(data['shipping_fee_file_url'])
            
            if 'collect_on_delivery_fee' in data:
                updates.append('collect_on_delivery_fee = %s' if USE_POSTGRESQL else 'collect_on_delivery_fee = ?')
                params.append(data['collect_on_delivery_fee'])
            
            if 'storage_fee' in data:
                updates.append('storage_fee = %s' if USE_POSTGRESQL else 'storage_fee = ?')
                params.append(data['storage_fee'])
            
            if 'special_work_fee' in data:
                updates.append('special_work_fee = %s' if USE_POSTGRESQL else 'special_work_fee = ?')
                params.append(data['special_work_fee'])
            
            if 'error_deduction' in data:
                updates.append('error_deduction = %s' if USE_POSTGRESQL else 'error_deduction = ?')
                params.append(data['error_deduction'])
            
            if 'total_amount' in data:
                updates.append('total_amount = %s' if USE_POSTGRESQL else 'total_amount = ?')
                params.append(data['total_amount'])
            
            if 'status' in data:
                updates.append('status = %s' if USE_POSTGRESQL else 'status = ?')
                params.append(data['status'])
            
            if 'memo' in data:
                updates.append('memo = %s' if USE_POSTGRESQL else 'memo = ?')
                params.append(data['memo'])
            
            if not updates:
                return jsonify({
                    'success': False,
                    'message': '수정할 데이터가 없습니다.'
                }), 400
            
            updates.append('updated_at = CURRENT_TIMESTAMP')
            params.append(settlement_id)
            
            if USE_POSTGRESQL:
                cursor.execute(f'''
                    UPDATE settlements 
                    SET {', '.join(updates)}
                    WHERE id = %s
                ''', params)
            else:
                cursor.execute(f'''
                    UPDATE settlements 
                    SET {', '.join(updates)}
                    WHERE id = ?
                ''', params)
            
            conn.commit()
            
            if cursor.rowcount > 0:
                return jsonify({
                    'success': True,
                    'message': '정산이 수정되었습니다.'
                })
            else:
                return jsonify({
                    'success': False,
                    'message': '정산을 찾을 수 없습니다.'
                }), 404
        except Exception as e:
            conn.rollback() if USE_POSTGRESQL else None
            print(f'[오류] 정산 수정 오류: {e}')
            import traceback
            traceback.print_exc()
            return jsonify({
                'success': False,
                'message': f'정산 수정 중 오류: {str(e)}'
            }), 500
        finally:
            cursor.close()
            conn.close()
    except Exception as e:
        print(f'❌ 정산 수정 오류: {e}')
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'message': f'정산 수정 중 오류: {str(e)}'
        }), 500


# ========== 정산 삭제 ==========

@settlements_bp.route('/<int:settlement_id>', methods=['DELETE'])
def delete_settlement(settlement_id):
    """정산 삭제"""
    try:
        user_context = get_user_context()
        role = user_context['role']
        
        # 관리자만 정산 삭제 가능
        if role != '관리자':
            return jsonify({
                'success': False,
                'message': '관리자만 정산을 삭제할 수 있습니다.'
            }), 403
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        try:
            if USE_POSTGRESQL:
                cursor.execute('DELETE FROM settlements WHERE id = %s', (settlement_id,))
            else:
                cursor.execute('DELETE FROM settlements WHERE id = ?', (settlement_id,))
            
            conn.commit()
            
            if cursor.rowcount > 0:
                return jsonify({
                    'success': True,
                    'message': '정산이 삭제되었습니다.'
                })
            else:
                return jsonify({
                    'success': False,
                    'message': '정산을 찾을 수 없습니다.'
                }), 404
        except Exception as e:
            conn.rollback() if USE_POSTGRESQL else None
            print(f'[오류] 정산 삭제 오류: {e}')
            import traceback
            traceback.print_exc()
            return jsonify({
                'success': False,
                'message': f'정산 삭제 중 오류: {str(e)}'
            }), 500
        finally:
            cursor.close()
            conn.close()
    except Exception as e:
        print(f'❌ 정산 삭제 오류: {e}')
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'message': f'정산 삭제 중 오류: {str(e)}'
        }), 500


# ========== 데이터 소스 조회 (파레트, 특수작업, 반품관리) ==========

@settlements_bp.route('/data-sources', methods=['GET'])
def get_data_sources():
    """정산에 필요한 데이터 소스 조회 (파레트 보관료, 특수작업, 오배송/누락 차감)"""
    try:
        user_context = get_user_context()
        role = user_context['role']
        company_name = user_context['company_name']
        
        settlement_year_month = request.args.get('settlement_year_month', '').strip()
        filter_company_name = request.args.get('company_name', '').strip()
        
        if not settlement_year_month:
            return jsonify({
                'success': False,
                'message': '정산년월이 필요합니다.'
            }), 400
        
        # 화주사는 자신의 데이터만 조회
        if role != '관리자':
            if not company_name:
                return jsonify({
                    'success': False,
                    'message': '화주사 정보를 확인할 수 없습니다.'
                }), 400
            filter_company_name = company_name
        elif not filter_company_name:
            # 관리자인 경우 company_name 파라미터가 필수
            return jsonify({
                'success': False,
                'message': '화주사명이 필요합니다.'
            }), 400
        
        result = {
            'storage_fee': 0,  # 파레트 보관료
            'special_work_fee': 0,  # 특수작업 비용
            'error_wrong_delivery_count': 0,  # 오배송 건수
            'error_missing_count': 0,  # 누락 건수
            'error_details': [],  # 오배송/누락 상세
            'collect_on_delivery_fee': 0  # 착불 택배비
        }
        
        # 1. 파레트 보관료 조회
        try:
            from api.pallets.models import get_settlements
            pallet_settlements = get_settlements(
                company_name=filter_company_name,
                settlement_month=settlement_year_month,
                role=role
            )
            if pallet_settlements:
                filter_normalized = normalize_company_name(filter_company_name)
                for settlement in pallet_settlements:
                    if normalize_company_name(settlement.get('company_name', '') or '') == filter_normalized:
                        result['storage_fee'] = settlement.get('total_fee', 0)
                        break
        except Exception as e:
            print(f'[경고] 파레트 보관료 조회 오류: {e}')
        
        # 2. 특수작업 비용 조회
        try:
            if not filter_company_name:
                print('[경고] 특수작업 비용 조회: 화주사명이 없어서 조회하지 않음')
            else:
                conn = get_db_connection()
                if USE_POSTGRESQL:
                    cursor = conn.cursor(cursor_factory=RealDictCursor)
                else:
                    cursor = conn.cursor()
                
                try:
                    # 정산년월을 날짜 범위로 변환 (특수작업 메뉴와 동일한 방식: 해당 월의 마지막 날까지)
                    try:
                        year, month = map(int, settlement_year_month.split('-'))
                        start_date = f'{year}-{month:02d}-01'
                        # 해당 월의 마지막 날 계산 (특수작업 메뉴와 동일한 방식)
                        # JavaScript의 new Date(year, month, 0).getDate()와 동일
                        from datetime import date
                        if month == 12:
                            # 12월인 경우: date(다음해, 1, 0).day = 올해 12월 마지막 날
                            last_day = date(year + 1, 1, 0).day
                        else:
                            # 다른 월: date(올해, 다음월, 0).day = 이번 달 마지막 날
                            last_day = date(year, month + 1, 0).day
                        end_date = f'{year}-{month:02d}-{last_day:02d}'
                        print(f'[디버깅] 날짜 범위 계산: {settlement_year_month} -> {start_date} ~ {end_date}')
                    except (ValueError, AttributeError) as e:
                        print(f'[경고] 정산년월 파싱 오류: {settlement_year_month}, {e}')
                        start_date = None
                        end_date = None
                    
                    if start_date and end_date:
                        # 디버깅: 조회 전 실제 데이터 확인
                        if USE_POSTGRESQL:
                            cursor.execute('''
                                SELECT company_name, work_date, total_price
                                FROM special_works
                                WHERE company_name = %s 
                                AND work_date >= %s 
                                AND work_date <= %s
                                LIMIT 5
                            ''', (filter_company_name, start_date, end_date))
                        else:
                            cursor.execute('''
                                SELECT company_name, work_date, total_price
                                FROM special_works
                                WHERE company_name = ? 
                                AND work_date >= ? 
                                AND work_date <= ?
                                LIMIT 5
                            ''', (filter_company_name, start_date, end_date))
                        debug_rows = cursor.fetchall()
                        print(f'[디버깅] 특수작업 조회 조건: company_name={filter_company_name}, start_date={start_date}, end_date={end_date}')
                        print(f'[디버깅] 조회된 데이터 개수: {len(debug_rows)}')
                        for debug_row in debug_rows:
                            debug_data = dict(debug_row) if isinstance(debug_row, dict) else {
                                'company_name': debug_row[0],
                                'work_date': debug_row[1],
                                'total_price': debug_row[2]
                            }
                            print(f'[디버깅] 발견된 데이터: {debug_data}')
                        
                        # 화주사명으로 조회 (정확한 매칭)
                        if USE_POSTGRESQL:
                            cursor.execute('''
                                SELECT COALESCE(SUM(total_price), 0) as total
                                FROM special_works
                                WHERE company_name = %s
                                AND work_date >= %s 
                                AND work_date <= %s
                            ''', (filter_company_name, start_date, end_date))
                        else:
                            # SQLite는 기본적으로 대소문자 구분 안 함 (TEXT 컬럼)
                            cursor.execute('''
                                SELECT COALESCE(SUM(total_price), 0) as total
                                FROM special_works
                                WHERE company_name = ?
                                AND work_date >= ? 
                                AND work_date <= ?
                            ''', (filter_company_name, start_date, end_date))
                        
                        row = cursor.fetchone()
                        if row:
                            total = row[0] if isinstance(row, dict) else row[0]
                            result['special_work_fee'] = int(total or 0)
                            print(f'[정보] 특수작업 비용 조회 성공: {filter_company_name}, {settlement_year_month}, {result["special_work_fee"]}원')
                        else:
                            result['special_work_fee'] = 0
                            print(f'[정보] 특수작업 비용 조회 결과 없음: {filter_company_name}, {settlement_year_month}')
                finally:
                    cursor.close()
                    conn.close()
        except Exception as e:
            print(f'[경고] 특수작업 비용 조회 오류: {e}')
            import traceback
            traceback.print_exc()
            # 에러가 발생해도 기본값 0으로 계속 진행
            result['special_work_fee'] = 0
        
        # 3. 오배송/누락 차감 조회 (C/S 메뉴 - customer_service 테이블)
        # C/S 메뉴의 해당 월 데이터와 일치시켜 조회 (월 형식: 2025년01월, 2025년1월)
        try:
            conn = get_db_connection()
            if USE_POSTGRESQL:
                cursor = conn.cursor(cursor_factory=RealDictCursor)
            else:
                cursor = conn.cursor()
            
            try:
                # 정산년월(2025-01) → C/S 월 형식 변환 ("2025년1월", "2025년01월")
                year, month = map(int, settlement_year_month.split('-'))
                month_variants = list(dict.fromkeys([f'{year}년{month}월', f'{year}년{month:02d}월']))
                
                # 화주사명 매칭용 키워드 (대소문자·띄어쓰기 무시)
                try:
                    company_keywords = get_company_search_keywords(filter_company_name)
                    if not company_keywords:
                        company_keywords = [normalize_company_name(filter_company_name)]
                except Exception:
                    company_keywords = [normalize_company_name(filter_company_name)]
                
                # C/S 테이블에서 해당 월의 오배송/누락 조회 (월만 필터, 화주사는 Python에서 매칭)
                if USE_POSTGRESQL:
                    placeholders = ','.join(['%s'] * len(month_variants))
                    cursor.execute(f'''
                        SELECT management_number, customer_name, issue_type, company_name
                        FROM customer_service
                        WHERE month IN ({placeholders})
                        AND (issue_type = '오배송' OR issue_type = '누락')
                    ''', tuple(month_variants))
                else:
                    placeholders = ','.join(['?'] * len(month_variants))
                    cursor.execute(f'''
                        SELECT management_number, customer_name, issue_type, company_name
                        FROM customer_service
                        WHERE month IN ({placeholders})
                        AND (issue_type = '오배송' OR issue_type = '누락')
                    ''', tuple(month_variants))
                
                rows = cursor.fetchall()
                # SQLite는 tuple 반환 → dict 변환
                if USE_POSTGRESQL:
                    row_list = [dict(r) for r in rows]
                else:
                    col_names = [col[0] for col in cursor.description]
                    row_list = [dict(zip(col_names, r)) for r in rows]
                
                wrong_delivery_count = 0
                missing_count = 0
                error_details = []
                
                for row in row_list:
                    cs_company = (row.get('company_name') or '').strip()
                    cs_company_norm = normalize_company_name(cs_company)
                    # 화주사 매칭 (대소문자·띄어쓰기 무시)
                    if cs_company_norm not in company_keywords:
                        continue
                    
                    issue_type = row.get('issue_type', '')
                    if issue_type == '오배송':
                        wrong_delivery_count += 1
                    elif issue_type == '누락':
                        missing_count += 1
                    
                    error_details.append({
                        'tracking_number': row.get('management_number', '') or '',
                        'customer_name': row.get('customer_name', '') or '',
                        'return_type': issue_type
                    })
                
                result['error_wrong_delivery_count'] = wrong_delivery_count
                result['error_missing_count'] = missing_count
                result['error_details'] = error_details
            finally:
                cursor.close()
                conn.close()
        except Exception as e:
            print(f'[경고] 오배송/누락 차감 조회 오류: {e}')
            import traceback
            traceback.print_exc()
        
        # 4. 착불 택배비 집계 (반품관리)
        try:
            conn = get_db_connection()
            if USE_POSTGRESQL:
                cursor = conn.cursor(cursor_factory=RealDictCursor)
            else:
                cursor = conn.cursor()
            
            try:
                # 정산년월 → 월 형식. 반품 DB는 "2025년1월" 또는 "2025년01월" 둘 다 있을 수 있음.
                year, month = map(int, settlement_year_month.split('-'))
                month_variants = list(dict.fromkeys([f'{year}년{month}월', f'{year}년{month:02d}월']))
                
                if USE_POSTGRESQL:
                    placeholders = ','.join(['%s'] * len(month_variants))
                    cursor.execute(f'''
                        SELECT shipping_fee
                        FROM returns
                        WHERE company_name = %s 
                        AND month IN ({placeholders})
                        AND shipping_fee IS NOT NULL
                        AND shipping_fee != ''
                    ''', (filter_company_name, *month_variants))
                else:
                    placeholders = ','.join(['?'] * len(month_variants))
                    cursor.execute(f'''
                        SELECT shipping_fee
                        FROM returns
                        WHERE company_name = ? 
                        AND month IN ({placeholders})
                        AND shipping_fee IS NOT NULL
                        AND shipping_fee != ''
                    ''', (filter_company_name, *month_variants))
                
                rows = cursor.fetchall()
                total_collect_fee = 0
                
                for row in rows:
                    shipping_fee = row.get('shipping_fee', '') if isinstance(row, dict) else row[0]
                    if not shipping_fee:
                        continue
                    shipping_fee_str = str(shipping_fee).strip()
                    # "착불"로 시작하는 경우만 처리
                    if shipping_fee_str.startswith('착불'):
                        # "착불 5000" 형식에서 금액 추출
                        import re
                        match = re.match(r'착불\s*([\d,]+)', shipping_fee_str)
                        if match:
                            amount_str = match.group(1).replace(',', '')
                            try:
                                amount = int(amount_str)
                                total_collect_fee += amount
                            except ValueError:
                                pass
                
                result['collect_on_delivery_fee'] = total_collect_fee
                print(f'[정보] 착불 택배비 집계: {filter_company_name}, {settlement_year_month}, {total_collect_fee}원')
            finally:
                cursor.close()
                conn.close()
        except Exception as e:
            print(f'[경고] 착불 택배비 집계 오류: {e}')
            import traceback
            traceback.print_exc()
            # 에러가 발생해도 기본값 0으로 계속 진행
            result['collect_on_delivery_fee'] = 0
        
        return jsonify({
            'success': True,
            'data': result
        })
    except Exception as e:
        print(f'[오류] 데이터 소스 조회 오류: {e}')
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'message': f'데이터 소스 조회 중 오류: {str(e)}'
        }), 500


# ========== 파일 업로드 ==========

@settlements_bp.route('/upload-file', methods=['POST'])
def upload_settlement_file():
    """정산 파일 업로드 (이지어드민, 택배사 파일 등) - Google Drive
    
    지원하는 요청 형식:
    1. FormData (권장): multipart/form-data
       - settlement_id: int
       - file_type: str ('work_fee', 'inout_fee', 'shipping_fee')
       - file: File (파일 객체)
    
    2. JSON (호환성): application/json
       - settlement_id: int
       - file_type: str
       - file_name: str
       - file_data: str (base64 인코딩된 파일 데이터)
    """
    try:
        user_context = get_user_context()
        role = user_context['role']
        
        # 관리자만 파일 업로드 가능
        if role != '관리자':
            return jsonify({
                'success': False,
                'message': '관리자만 파일을 업로드할 수 있습니다.'
            }), 403
        
        # FormData 방식인지 JSON 방식인지 확인
        if 'file' in request.files:
            # FormData 방식 (권장)
            file = request.files['file']
            settlement_id = request.form.get('settlement_id')
            file_type = request.form.get('file_type', '').strip()
            
            if not settlement_id or not file_type or not file.filename:
                return jsonify({
                    'success': False,
                    'message': '필수 데이터가 누락되었습니다. (settlement_id, file_type, file 필요)'
                }), 400
            
            settlement_id = int(settlement_id)
            file_name = file.filename
            file_data = file.read()
            
        else:
            # JSON 방식 (호환성)
            data = request.get_json()
            settlement_id = data.get('settlement_id')
            file_type = data.get('file_type', '').strip()
            file_name = data.get('file_name', '').strip()
            base64_data = data.get('file_data', '')
            
            if not settlement_id or not file_type or not file_name or not base64_data:
                return jsonify({
                    'success': False,
                    'message': '필수 데이터가 누락되었습니다.'
                }), 400
            
            # Base64 디코딩
            try:
                from api.uploads.oauth_drive import upload_settlement_excel_to_drive
                import base64 as base64_lib
                
                # Base64 데이터에서 실제 데이터 추출
                if ',' in base64_data:
                    base64_data = base64_data.split(',')[1]
                
                file_data = base64_lib.b64decode(base64_data)
            except Exception as e:
                return jsonify({
                    'success': False,
                    'message': f'파일 데이터 디코딩 실패: {str(e)}'
                }), 400
        
        # 정산 정보 조회 (company_name, settlement_year_month 가져오기)
        conn = get_db_connection()
        if USE_POSTGRESQL:
            cursor = conn.cursor(cursor_factory=RealDictCursor)
        else:
            cursor = conn.cursor()
        
        try:
            if USE_POSTGRESQL:
                cursor.execute('SELECT company_name, settlement_year_month FROM settlements WHERE id = %s', (settlement_id,))
            else:
                cursor.execute('SELECT company_name, settlement_year_month FROM settlements WHERE id = ?', (settlement_id,))
            
            row = cursor.fetchone()
            if not row:
                return jsonify({
                    'success': False,
                    'message': '정산을 찾을 수 없습니다.'
                }), 404
            
            settlement = dict(row)
            company_name = settlement.get('company_name', '')
            settlement_year_month = settlement.get('settlement_year_month', '')
            
            if not company_name or not settlement_year_month:
                return jsonify({
                    'success': False,
                    'message': '정산 정보가 불완전합니다. (화주사명 또는 정산년월 없음)'
                }), 400
        finally:
            cursor.close()
            conn.close()
        
        # Google Drive 업로드
        try:
            from api.uploads.oauth_drive import upload_settlement_excel_to_drive
            
            # Google Drive에 업로드
            result = upload_settlement_excel_to_drive(
                file_data=file_data,
                filename=file_name,
                company_name=company_name,
                settlement_year_month=settlement_year_month
            )
            
            if not result.get('success'):
                return jsonify({
                    'success': False,
                    'message': result.get('message', '파일 업로드 실패')
                }), 500
            
            file_url = result.get('web_view_link', result.get('file_url', ''))
            
            if not file_url:
                return jsonify({
                    'success': False,
                    'message': '파일 업로드는 성공했지만 파일 URL을 가져올 수 없습니다.'
                }), 500
            
            # 파일 정보 DB 저장
            conn = get_db_connection()
            cursor = conn.cursor()
            
            try:
                # 파일 크기 계산
                file_size = len(file_data)
                
                if USE_POSTGRESQL:
                    cursor.execute('''
                        INSERT INTO settlement_files (
                            settlement_id, file_type, file_name, file_url, file_size, uploaded_at
                        )
                        VALUES (%s, %s, %s, %s, %s, CURRENT_TIMESTAMP)
                        RETURNING id
                    ''', (settlement_id, file_type, file_name, file_url, file_size))
                    file_id = cursor.fetchone()[0]
                else:
                    cursor.execute('''
                        INSERT INTO settlement_files (
                            settlement_id, file_type, file_name, file_url, file_size, uploaded_at
                        )
                        VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                    ''', (settlement_id, file_type, file_name, file_url, file_size))
                    file_id = cursor.lastrowid
                
                # 정산 테이블에 파일 URL 업데이트 (file_type에 따라)
                if file_type == 'work_fee':
                    if USE_POSTGRESQL:
                        cursor.execute('UPDATE settlements SET work_fee_file_url = %s WHERE id = %s', (file_url, settlement_id))
                    else:
                        cursor.execute('UPDATE settlements SET work_fee_file_url = ? WHERE id = ?', (file_url, settlement_id))
                elif file_type == 'inout_fee':
                    if USE_POSTGRESQL:
                        cursor.execute('UPDATE settlements SET inout_fee_file_url = %s WHERE id = %s', (file_url, settlement_id))
                    else:
                        cursor.execute('UPDATE settlements SET inout_fee_file_url = ? WHERE id = ?', (file_url, settlement_id))
                elif file_type == 'shipping_fee':
                    if USE_POSTGRESQL:
                        cursor.execute('UPDATE settlements SET shipping_fee_file_url = %s WHERE id = %s', (file_url, settlement_id))
                    else:
                        cursor.execute('UPDATE settlements SET shipping_fee_file_url = ? WHERE id = ?', (file_url, settlement_id))
                
                conn.commit()
                
                return jsonify({
                    'success': True,
                    'message': '파일이 업로드되었습니다.',
                    'file_id': file_id,
                    'file_url': file_url
                })
            except Exception as e:
                conn.rollback() if USE_POSTGRESQL else None
                print(f'[오류] 파일 정보 저장 오류: {e}')
                import traceback
                traceback.print_exc()
                return jsonify({
                    'success': False,
                    'message': f'파일 정보 저장 중 오류: {str(e)}'
                }), 500
            finally:
                cursor.close()
                conn.close()
        except Exception as e:
            print(f'[오류] 파일 업로드 오류: {e}')
            import traceback
            traceback.print_exc()
            return jsonify({
                'success': False,
                'message': f'파일 업로드 중 오류: {str(e)}'
            }), 500
    except Exception as e:
        print(f'❌ 파일 업로드 오류: {e}')
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'message': f'파일 업로드 중 오류: {str(e)}'
        }), 500


# ========== 청크 업로드 (큰 파일용) ==========

@settlements_bp.route('/upload-file-start', methods=['POST'])
def upload_settlement_file_start():
    """정산 파일 청크 업로드 시작 API (테스트 파일과 동일한 방식)"""
    try:
        user_context = get_user_context()
        role = user_context['role']
        
        # 관리자만 파일 업로드 가능
        if role != '관리자':
            return jsonify({
                'success': False,
                'message': '관리자만 파일을 업로드할 수 있습니다.'
            }), 403
        
        data = request.get_json()
        settlement_id = data.get('settlement_id')
        file_type = data.get('file_type', '').strip()
        filename = data.get('filename')
        file_size = data.get('file_size')
        total_chunks = data.get('total_chunks')
        
        if not settlement_id or not file_type or not filename or not file_size or not total_chunks:
            return jsonify({
                'success': False,
                'message': '필수 파라미터가 없습니다.'
            }), 400
        
        # 정산 정보 조회 (company_name, settlement_year_month 가져오기)
        conn = get_db_connection()
        if USE_POSTGRESQL:
            cursor = conn.cursor(cursor_factory=RealDictCursor)
        else:
            cursor = conn.cursor()
        
        try:
            if USE_POSTGRESQL:
                cursor.execute('SELECT company_name, settlement_year_month FROM settlements WHERE id = %s', (settlement_id,))
            else:
                cursor.execute('SELECT company_name, settlement_year_month FROM settlements WHERE id = ?', (settlement_id,))
            
            row = cursor.fetchone()
            if not row:
                return jsonify({
                    'success': False,
                    'message': '정산을 찾을 수 없습니다.'
                }), 404
            
            settlement = dict(row)
            company_name = settlement.get('company_name', '')
            settlement_year_month = settlement.get('settlement_year_month', '')
            
            if not company_name or not settlement_year_month:
                return jsonify({
                    'success': False,
                    'message': '정산 정보가 불완전합니다. (화주사명 또는 정산년월 없음)'
                }), 400
        finally:
            cursor.close()
            conn.close()
        
        # 업로드 세션 생성 (테스트 파일과 동일한 방식)
        upload_id = str(uuid.uuid4())
        
        # 세션 저장 (임시로 전역 변수 사용, 실제로는 DB나 Redis 사용)
        if not hasattr(upload_settlement_file_start, 'upload_sessions'):
            upload_settlement_file_start.upload_sessions = {}
        
        upload_settlement_file_start.upload_sessions[upload_id] = {
            'settlement_id': settlement_id,
            'file_type': file_type,
            'filename': filename,
            'file_size': file_size,
            'total_chunks': total_chunks,
            'company_name': company_name,
            'settlement_year_month': settlement_year_month,
            'chunks': {},
            'created_at': datetime.now()
        }
        
        print(f"[정보] 정산 파일 업로드 세션 시작: {upload_id}, 파일: {filename}, 크기: {file_size} bytes, 청크: {total_chunks}")
        
        return jsonify({
            'success': True,
            'upload_id': upload_id,
            'message': '업로드 세션이 생성되었습니다.'
        })
        
    except Exception as e:
        print(f'[오류] 업로드 시작 오류: {e}')
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'message': f'업로드 시작 중 오류: {str(e)}'
        }), 500


@settlements_bp.route('/upload-file-chunk', methods=['POST'])
def upload_settlement_file_chunk():
    """정산 파일 청크 업로드 API (테스트 파일과 동일한 방식)"""
    try:
        data = request.get_json()
        upload_id = data.get('upload_id')
        chunk_index = data.get('chunk_index')
        chunk_data = data.get('chunk_data')
        is_last_chunk = data.get('is_last_chunk', False)
        
        if not upload_id or chunk_index is None or not chunk_data:
            return jsonify({
                'success': False,
                'message': '필수 파라미터가 없습니다.'
            }), 400
        
        # 세션 확인
        if not hasattr(upload_settlement_file_start, 'upload_sessions'):
            return jsonify({
                'success': False,
                'message': '업로드 세션을 찾을 수 없습니다.'
            }), 404
        
        session = upload_settlement_file_start.upload_sessions.get(upload_id)
        if not session:
            return jsonify({
                'success': False,
                'message': '업로드 세션이 만료되었거나 존재하지 않습니다.'
            }), 404
        
        # 청크 저장
        session['chunks'][chunk_index] = chunk_data
        
        print(f"[정보] 정산 파일 청크 수신: {upload_id}, 청크 {chunk_index + 1}/{session['total_chunks']}")
        
        return jsonify({
            'success': True,
            'message': f'청크 {chunk_index + 1} 수신 완료'
        })
        
    except Exception as e:
        print(f'[오류] 청크 업로드 오류: {e}')
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'message': f'청크 업로드 중 오류: {str(e)}'
        }), 500


@settlements_bp.route('/upload-file-complete', methods=['POST'])
def upload_settlement_file_complete():
    """정산 파일 청크 업로드 완료 API (테스트 파일과 동일한 방식)"""
    try:
        user_context = get_user_context()
        role = user_context['role']
        
        # 관리자만 파일 업로드 가능
        if role != '관리자':
            return jsonify({
                'success': False,
                'message': '관리자만 파일을 업로드할 수 있습니다.'
            }), 403
        
        data = request.get_json()
        upload_id = data.get('upload_id')
        
        if not upload_id:
            return jsonify({
                'success': False,
                'message': '업로드 ID가 없습니다.'
            }), 400
        
        # 세션 확인
        if not hasattr(upload_settlement_file_start, 'upload_sessions'):
            return jsonify({
                'success': False,
                'message': '업로드 세션을 찾을 수 없습니다.'
            }), 404
        
        session = upload_settlement_file_start.upload_sessions.get(upload_id)
        if not session:
            return jsonify({
                'success': False,
                'message': '업로드 세션이 만료되었거나 존재하지 않습니다.'
            }), 404
        
        # 모든 청크 확인
        total_chunks = session['total_chunks']
        chunks = session['chunks']
        
        if len(chunks) != total_chunks:
            return jsonify({
                'success': False,
                'message': f'모든 청크를 받지 못했습니다. ({len(chunks)}/{total_chunks})'
            }), 400
        
        # 청크 조립
        print(f"[정보] 정산 파일 청크 조립 시작: {upload_id}, 총 {total_chunks}개 청크")
        chunks_list = [chunks[i] for i in range(total_chunks)]
        base64_data = ''.join(chunks_list)
        
        # Base64 디코딩
        file_data = base64_lib.b64decode(base64_data)
        
        print(f"[정보] 정산 파일 조립 완료: {len(file_data)} bytes")
        
        # Google Drive에 업로드
        try:
            from api.uploads.oauth_drive import upload_settlement_excel_to_drive
            
            settlement_id = session['settlement_id']
            file_type = session['file_type']
            filename = session['filename']
            company_name = session['company_name']
            settlement_year_month = session['settlement_year_month']
            
            result = upload_settlement_excel_to_drive(
                file_data=file_data,
                filename=filename,
                company_name=company_name,
                settlement_year_month=settlement_year_month
            )
            
            # 세션 삭제
            del upload_settlement_file_start.upload_sessions[upload_id]
            
            if not result.get('success'):
                return jsonify({
                    'success': False,
                    'message': result.get('message', '파일 업로드 실패')
                }), 500
            
            file_url = result.get('web_view_link', result.get('file_url', ''))
            
            if not file_url:
                return jsonify({
                    'success': False,
                    'message': '파일 업로드는 성공했지만 파일 URL을 가져올 수 없습니다.'
                }), 500
            
            # 파일 정보 DB 저장
            conn = get_db_connection()
            cursor = conn.cursor()
            
            try:
                file_size = len(file_data)
                
                if USE_POSTGRESQL:
                    cursor.execute('''
                        INSERT INTO settlement_files (
                            settlement_id, file_type, file_name, file_url, file_size, uploaded_at
                        )
                        VALUES (%s, %s, %s, %s, %s, CURRENT_TIMESTAMP)
                        RETURNING id
                    ''', (settlement_id, file_type, filename, file_url, file_size))
                    file_id = cursor.fetchone()[0]
                else:
                    cursor.execute('''
                        INSERT INTO settlement_files (
                            settlement_id, file_type, file_name, file_url, file_size, uploaded_at
                        )
                        VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                    ''', (settlement_id, file_type, filename, file_url, file_size))
                    file_id = cursor.lastrowid
                
                # 정산 테이블에 파일 URL 업데이트 (file_type에 따라)
                if file_type == 'work_fee':
                    if USE_POSTGRESQL:
                        cursor.execute('UPDATE settlements SET work_fee_file_url = %s WHERE id = %s', (file_url, settlement_id))
                    else:
                        cursor.execute('UPDATE settlements SET work_fee_file_url = ? WHERE id = ?', (file_url, settlement_id))
                elif file_type == 'inout_fee':
                    if USE_POSTGRESQL:
                        cursor.execute('UPDATE settlements SET inout_fee_file_url = %s WHERE id = %s', (file_url, settlement_id))
                    else:
                        cursor.execute('UPDATE settlements SET inout_fee_file_url = ? WHERE id = ?', (file_url, settlement_id))
                elif file_type == 'shipping_fee':
                    if USE_POSTGRESQL:
                        cursor.execute('UPDATE settlements SET shipping_fee_file_url = %s WHERE id = %s', (file_url, settlement_id))
                    else:
                        cursor.execute('UPDATE settlements SET shipping_fee_file_url = ? WHERE id = ?', (file_url, settlement_id))
                
                conn.commit()
                
                return jsonify({
                    'success': True,
                    'file_id': file_id,
                    'file_url': file_url,
                    'message': '파일 업로드 성공'
                })
            except Exception as e:
                conn.rollback() if USE_POSTGRESQL else None
                print(f'[오류] 파일 정보 저장 오류: {e}')
                import traceback
                traceback.print_exc()
                return jsonify({
                    'success': False,
                    'message': f'파일 정보 저장 중 오류: {str(e)}'
                }), 500
            finally:
                cursor.close()
                conn.close()
                
        except ImportError as import_error:
            print(f"[오류] 구글 드라이브 모듈 import 실패: {import_error}")
            return jsonify({
                'success': False,
                'message': f'구글 드라이브 모듈을 찾을 수 없습니다: {str(import_error)}'
            }), 500
        except Exception as upload_error:
            print(f"[오류] 구글 드라이브 업로드 오류: {upload_error}")
            import traceback
            traceback.print_exc()
            return jsonify({
                'success': False,
                'message': f'파일 업로드 중 오류가 발생했습니다: {str(upload_error)}'
            }), 500
        
    except Exception as e:
        print(f'[오류] 업로드 완료 처리 오류: {e}')
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'message': f'업로드 완료 처리 중 오류: {str(e)}'
        }), 500


# ========== 파일 삭제 ==========

@settlements_bp.route('/<int:settlement_id>/delete-file', methods=['POST'])
def delete_settlement_file(settlement_id):
    """정산 파일 삭제"""
    try:
        user_context = get_user_context()
        role = user_context['role']
        
        # 관리자만 파일 삭제 가능
        if role != '관리자':
            return jsonify({
                'success': False,
                'message': '관리자만 파일을 삭제할 수 있습니다.'
            }), 403
        
        data = request.get_json()
        file_type = data.get('file_type', '').strip()
        
        if not file_type:
            return jsonify({
                'success': False,
                'message': '파일 타입이 필요합니다.'
            }), 400
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        try:
            # 정산 테이블에서 파일 URL 제거 (file_type에 따라)
            if file_type == 'work_fee':
                if USE_POSTGRESQL:
                    cursor.execute('UPDATE settlements SET work_fee_file_url = NULL WHERE id = %s', (settlement_id,))
                else:
                    cursor.execute('UPDATE settlements SET work_fee_file_url = NULL WHERE id = ?', (settlement_id,))
            elif file_type == 'inout_fee':
                if USE_POSTGRESQL:
                    cursor.execute('UPDATE settlements SET inout_fee_file_url = NULL WHERE id = %s', (settlement_id,))
                else:
                    cursor.execute('UPDATE settlements SET inout_fee_file_url = NULL WHERE id = ?', (settlement_id,))
            elif file_type == 'shipping_fee':
                if USE_POSTGRESQL:
                    cursor.execute('UPDATE settlements SET shipping_fee_file_url = NULL WHERE id = %s', (settlement_id,))
                else:
                    cursor.execute('UPDATE settlements SET shipping_fee_file_url = NULL WHERE id = ?', (settlement_id,))
            
            # settlement_files 테이블에서도 삭제
            if USE_POSTGRESQL:
                cursor.execute('DELETE FROM settlement_files WHERE settlement_id = %s AND file_type = %s', (settlement_id, file_type))
            else:
                cursor.execute('DELETE FROM settlement_files WHERE settlement_id = ? AND file_type = ?', (settlement_id, file_type))
            
            conn.commit()
            
            return jsonify({
                'success': True,
                'message': '파일이 삭제되었습니다.'
            })
        except Exception as e:
            conn.rollback() if USE_POSTGRESQL else None
            print(f'[오류] 파일 삭제 오류: {e}')
            import traceback
            traceback.print_exc()
            return jsonify({
                'success': False,
                'message': f'파일 삭제 중 오류: {str(e)}'
            }), 500
        finally:
            cursor.close()
            conn.close()
    except Exception as e:
        print(f'[오류] 파일 삭제 오류: {e}')
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'message': f'파일 삭제 중 오류: {str(e)}'
        }), 500


# ========== 세금계산서 삭제 ==========

@settlements_bp.route('/<int:settlement_id>/delete-tax-invoice', methods=['POST'])
def delete_tax_invoice(settlement_id):
    """세금계산서 삭제 (관리자용)"""
    try:
        user_context = get_user_context()
        role = user_context['role']
        
        # 관리자만 세금계산서 삭제 가능
        if role != '관리자':
            return jsonify({
                'success': False,
                'message': '관리자만 세금계산서를 삭제할 수 있습니다.'
            }), 403
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        try:
            # 세금계산서 URL을 NULL로 업데이트
            if USE_POSTGRESQL:
                cursor.execute('UPDATE settlements SET tax_invoice_file_url = NULL, updated_at = CURRENT_TIMESTAMP WHERE id = %s', (settlement_id,))
            else:
                cursor.execute('UPDATE settlements SET tax_invoice_file_url = NULL, updated_at = CURRENT_TIMESTAMP WHERE id = ?', (settlement_id,))
            
            conn.commit()
            
            if cursor.rowcount > 0:
                return jsonify({
                    'success': True,
                    'message': '세금계산서가 삭제되었습니다.'
                })
            else:
                return jsonify({
                    'success': False,
                    'message': '정산을 찾을 수 없습니다.'
                }), 404
        except Exception as e:
            conn.rollback() if USE_POSTGRESQL else None
            print(f'[오류] 세금계산서 삭제 오류: {e}')
            import traceback
            traceback.print_exc()
            return jsonify({
                'success': False,
                'message': f'세금계산서 삭제 중 오류: {str(e)}'
            }), 500
        finally:
            cursor.close()
            conn.close()
    except Exception as e:
        print(f'[오류] 세금계산서 삭제 오류: {e}')
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'message': f'세금계산서 삭제 중 오류: {str(e)}'
        }), 500


# ========== 일괄 상태 변경 ==========

@settlements_bp.route('/bulk-update-status', methods=['POST'])
def bulk_update_settlement_status():
    """정산년월별 일괄 상태 변경"""
    try:
        user_context = get_user_context()
        role = user_context['role']
        
        # 관리자만 일괄 상태 변경 가능
        if role != '관리자':
            return jsonify({
                'success': False,
                'message': '관리자만 일괄 상태 변경이 가능합니다.'
            }), 403
        
        settlement_year_month = request.args.get('settlement_year_month', '').strip()
        status = request.args.get('status', '').strip()
        
        if not settlement_year_month or not status:
            return jsonify({
                'success': False,
                'message': '정산년월과 상태는 필수입니다.'
            }), 400
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        try:
            # 해당 정산년월의 모든 정산 상태 변경
            # 단, 이미 '정산확인' 이상 상태인 정산은 변경하지 않음 (화주사가 확인한 정산 보호)
            if USE_POSTGRESQL:
                cursor.execute('''
                    UPDATE settlements 
                    SET status = %s, updated_at = CURRENT_TIMESTAMP
                    WHERE settlement_year_month = %s
                    AND status NOT IN ('정산확인', '입금완료')
                ''', (status, settlement_year_month))
            else:
                cursor.execute('''
                    UPDATE settlements 
                    SET status = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE settlement_year_month = ?
                    AND status NOT IN ('정산확인', '입금완료')
                ''', (status, settlement_year_month))
            
            updated_count = cursor.rowcount
            conn.commit()
            print(f'[일괄상태변경] 정산년월={settlement_year_month}, 상태={status}, 변경된개수={updated_count}')
            
            return jsonify({
                'success': True,
                'message': f'{updated_count}개의 정산이 {status} 상태로 변경되었습니다.',
                'updated_count': updated_count
            })
        except Exception as e:
            conn.rollback() if USE_POSTGRESQL else None
            print(f'[오류] 일괄 상태 변경 오류: {e}')
            import traceback
            traceback.print_exc()
            return jsonify({
                'success': False,
                'message': f'일괄 상태 변경 중 오류: {str(e)}'
            }), 500
        finally:
            cursor.close()
            conn.close()
    except Exception as e:
        print(f'[오류] 일괄 상태 변경 오류: {e}')
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'message': f'일괄 상태 변경 중 오류: {str(e)}'
        }), 500


# ========== 세금계산서 업로드 (화주사용) ==========

@settlements_bp.route('/<int:settlement_id>/upload-tax-invoice', methods=['POST'])
def upload_tax_invoice(settlement_id):
    """세금계산서 업로드 (관리자용)"""
    try:
        user_context = get_user_context()
        role = user_context['role']
        
        # 관리자만 세금계산서 업로드 가능
        if role != '관리자':
            return jsonify({
                'success': False,
                'message': '관리자만 세금계산서를 업로드할 수 있습니다.'
            }), 403
        
        # 정산 정보 조회
        conn = get_db_connection()
        if USE_POSTGRESQL:
            cursor = conn.cursor(cursor_factory=RealDictCursor)
        else:
            cursor = conn.cursor()
        
        try:
            if USE_POSTGRESQL:
                cursor.execute('SELECT company_name, settlement_year_month FROM settlements WHERE id = %s', (settlement_id,))
            else:
                cursor.execute('SELECT company_name, settlement_year_month FROM settlements WHERE id = ?', (settlement_id,))
            
            row = cursor.fetchone()
            if not row:
                return jsonify({
                    'success': False,
                    'message': '정산을 찾을 수 없습니다.'
                }), 404
            
            settlement = dict(row)
            settlement_company_name = settlement.get('company_name', '')
            settlement_year_month = settlement.get('settlement_year_month', '')
        finally:
            cursor.close()
            conn.close()
        
        # 파일 업로드 처리 (FormData 방식)
        if 'file' not in request.files:
            return jsonify({
                'success': False,
                'message': '파일이 없습니다.'
            }), 400
        
        file = request.files['file']
        if not file.filename:
            return jsonify({
                'success': False,
                'message': '파일명이 없습니다.'
            }), 400
        
        file_data = file.read()
        file_name = file.filename
        
        # Google Drive 업로드
        try:
            from api.uploads.oauth_drive import upload_settlement_excel_to_drive
            
            result = upload_settlement_excel_to_drive(
                file_data=file_data,
                filename=f'세금계산서_{file_name}',
                company_name=settlement_company_name,
                settlement_year_month=settlement_year_month
            )
            
            if not result.get('success'):
                return jsonify({
                    'success': False,
                    'message': result.get('message', '파일 업로드 실패')
                }), 500
            
            file_url = result.get('web_view_link', result.get('file_url', ''))
            
            if not file_url:
                return jsonify({
                    'success': False,
                    'message': '파일 업로드는 성공했지만 파일 URL을 가져올 수 없습니다.'
                }), 500
            
            # DB 업데이트
            conn = get_db_connection()
            cursor = conn.cursor()
            
            try:
                if USE_POSTGRESQL:
                    cursor.execute('UPDATE settlements SET tax_invoice_file_url = %s, updated_at = CURRENT_TIMESTAMP WHERE id = %s', (file_url, settlement_id))
                else:
                    cursor.execute('UPDATE settlements SET tax_invoice_file_url = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?', (file_url, settlement_id))
                
                conn.commit()
                
                return jsonify({
                    'success': True,
                    'message': '세금계산서가 업로드되었습니다.',
                    'file_url': file_url
                })
            except Exception as e:
                conn.rollback() if USE_POSTGRESQL else None
                print(f'[오류] 세금계산서 정보 저장 오류: {e}')
                import traceback
                traceback.print_exc()
                return jsonify({
                    'success': False,
                    'message': f'세금계산서 정보 저장 중 오류: {str(e)}'
                }), 500
            finally:
                cursor.close()
                conn.close()
        except Exception as e:
            print(f'[오류] 세금계산서 업로드 오류: {e}')
            import traceback
            traceback.print_exc()
            return jsonify({
                'success': False,
                'message': f'세금계산서 업로드 중 오류: {str(e)}'
            }), 500
    except Exception as e:
        print(f'[오류] 세금계산서 업로드 오류: {e}')
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'message': f'세금계산서 업로드 중 오류: {str(e)}'
        }), 500


# ========== 상태 변경 (정산 확정, 입금완료) ==========

@settlements_bp.route('/<int:settlement_id>/update-status', methods=['POST'])
def update_settlement_status(settlement_id):
    """정산 상태 변경 (정산 확정, 입금완료)"""
    try:
        user_context = get_user_context()
        role = user_context['role']
        company_name = user_context['company_name']
        
        data = request.get_json()
        new_status = data.get('status', '').strip()
        
        if not new_status:
            return jsonify({
                'success': False,
                'message': '상태값이 필요합니다.'
            }), 400
        
        # 유효한 상태값 확인
        valid_statuses = ['대기', '전달', '정산확인', '입금완료']
        if new_status not in valid_statuses:
            return jsonify({
                'success': False,
                'message': f'유효하지 않은 상태값입니다. 가능한 값: {", ".join(valid_statuses)}'
            }), 400
        
        # 정산 정보 조회
        conn = get_db_connection()
        if USE_POSTGRESQL:
            cursor = conn.cursor(cursor_factory=RealDictCursor)
        else:
            cursor = conn.cursor()
        
        try:
            if USE_POSTGRESQL:
                cursor.execute('SELECT company_name, status FROM settlements WHERE id = %s', (settlement_id,))
            else:
                cursor.execute('SELECT company_name, status FROM settlements WHERE id = ?', (settlement_id,))
            
            row = cursor.fetchone()
            if not row:
                return jsonify({
                    'success': False,
                    'message': '정산을 찾을 수 없습니다.'
                }), 404
            
            settlement = dict(row) if USE_POSTGRESQL else dict(zip([desc[0] for desc in cursor.description], row))
            settlement_company_name = settlement.get('company_name', '')
            current_status = settlement.get('status', '')
            
            print(f'[정산상태변경] role={role}, company_name={company_name}, settlement_company_name={settlement_company_name}, current_status={current_status}, new_status={new_status}')
            
            # 권한 확인
            if role == '관리자':
                # 관리자는 모든 상태 변경 가능
                pass
            elif new_status == '정산확인':
                # 화주사는 자신의 정산만 '정산확인' 상태로 변경 가능
                if not company_name:
                    print(f'[정산상태변경] 화주사 정보 없음')
                    return jsonify({
                        'success': False,
                        'message': '화주사 정보를 확인할 수 없습니다.'
                    }), 400
                
                if settlement_company_name != company_name:
                    print(f'[정산상태변경] 화주사 불일치: {company_name} != {settlement_company_name}')
                    return jsonify({
                        'success': False,
                        'message': '자신의 정산만 확인할 수 있습니다.'
                    }), 403
                
                # 화주사는 '전달' 상태에서만 '정산확인'으로 변경 가능
                if current_status != '전달':
                    print(f'[정산상태변경] 상태 불일치: {current_status} != 전달')
                    return jsonify({
                        'success': False,
                        'message': '전달 상태인 정산만 확인할 수 있습니다.'
                    }), 400
            else:
                # 화주사는 정산확인 외의 상태 변경 불가 (관리자가 아닌 경우)
                if role != '관리자':
                    print(f'[정산상태변경] 권한 없음: role={role}, new_status={new_status}')
                    return jsonify({
                        'success': False,
                        'message': '권한이 없습니다.'
                    }), 403
            
            # 상태 업데이트
            if USE_POSTGRESQL:
                cursor.execute('UPDATE settlements SET status = %s, updated_at = CURRENT_TIMESTAMP WHERE id = %s', (new_status, settlement_id))
            else:
                cursor.execute('UPDATE settlements SET status = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?', (new_status, settlement_id))
            
            updated_rows = cursor.rowcount
            print(f'[정산상태변경] UPDATE 실행, rowcount={updated_rows}, settlement_id={settlement_id}, new_status={new_status}')
            
            conn.commit()
            print(f'[정산상태변경] COMMIT 완료, settlement_id={settlement_id}, new_status={new_status}')
            
            if updated_rows > 0:
                return jsonify({
                    'success': True,
                    'message': f'정산 상태가 {new_status}로 변경되었습니다.'
                })
            else:
                print(f'[정산상태변경] 업데이트 실패, rowcount=0, settlement_id={settlement_id}')
                return jsonify({
                    'success': False,
                    'message': '정산을 찾을 수 없습니다.'
                }), 404
        except Exception as e:
            conn.rollback() if USE_POSTGRESQL else None
            print(f'[오류] 정산 상태 변경 오류: {e}')
            import traceback
            traceback.print_exc()
            return jsonify({
                'success': False,
                'message': f'정산 상태 변경 중 오류: {str(e)}'
            }), 500
        finally:
            cursor.close()
            conn.close()
    except Exception as e:
        print(f'[오류] 정산 상태 변경 오류: {e}')
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'message': f'정산 상태 변경 중 오류: {str(e)}'
        }), 500


# ========== 명세서 생성 ==========

@settlements_bp.route('/<int:settlement_id>/statement', methods=['GET'])
def generate_settlement_statement(settlement_id):
    """정산 명세서 생성 (엑셀)"""
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
            # 정산 정보 조회
            if USE_POSTGRESQL:
                cursor.execute('SELECT * FROM settlements WHERE id = %s', (settlement_id,))
            else:
                cursor.execute('SELECT * FROM settlements WHERE id = ?', (settlement_id,))
            
            row = cursor.fetchone()
            if not row:
                return jsonify({
                    'success': False,
                    'message': '정산을 찾을 수 없습니다.'
                }), 404
            
            settlement = dict(row) if USE_POSTGRESQL else dict(zip([desc[0] for desc in cursor.description], row))
            
            # 화주사는 자신의 정산만 조회 가능
            if role != '관리자':
                if settlement.get('company_name') != company_name:
                    return jsonify({
                        'success': False,
                        'message': '권한이 없습니다.'
                    }), 403
            
            # datetime 객체를 문자열로 변환
            for key, value in settlement.items():
                if isinstance(value, datetime):
                    settlement[key] = value.strftime('%Y-%m-%d %H:%M:%S') if value else None
                elif isinstance(value, date):
                    settlement[key] = value.strftime('%Y-%m-%d') if value else None
            
            # 명세서 생성
            from api.settlements.statement_generator import create_settlement_statement
            excel_file = create_settlement_statement(settlement)
            
            # 파일명 생성
            year_month = settlement.get('settlement_year_month', '').replace('-', '')
            company = settlement.get('company_name', '정산')
            filename = f'정산명세서_{company}_{year_month}.xlsx'
            
            return Response(
                excel_file.read(),
                mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                headers={
                    'Content-Disposition': f'attachment; filename="{filename}"',
                    'Content-Type': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
                }
            )
        finally:
            cursor.close()
            conn.close()
    except Exception as e:
        print(f'[오류] 명세서 생성 오류: {e}')
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'message': f'명세서 생성 중 오류: {str(e)}'
        }), 500

