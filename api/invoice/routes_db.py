"""
거래명세서 API 라우트 (관리자 전용)
"""
from flask import Blueprint, request, jsonify
from urllib.parse import unquote
from datetime import datetime, date

from api.database.models import get_db_connection, USE_POSTGRESQL, get_all_companies
from api.invoice.models import init_invoice_tables
from api.uploads.cloudinary_upload import upload_single_file_to_cloudinary

if USE_POSTGRESQL:
    from psycopg2.extras import RealDictCursor

invoice_bp = Blueprint('invoice', __name__, url_prefix='/api/invoice')


def _row_to_dict(row):
    """DB row를 dict로 변환 (PostgreSQL RealDictRow / SQLite Row)"""
    if row is None:
        return None
    if hasattr(row, 'keys'):
        d = dict(row)
    else:
        return None
    for k, v in d.items():
        if isinstance(v, datetime):
            d[k] = v.strftime('%Y-%m-%d %H:%M:%S') if v else None
        elif isinstance(v, date):
            d[k] = v.strftime('%Y-%m-%d') if v else None
    return d


def _get_user_role():
    """헤더에서 역할 정보 추출"""
    role = request.headers.get('X-User-Role', '').strip()
    if role:
        role = unquote(role)
    return role or ''


def _require_invoice_admin():
    """관리자 권한 확인, 실패 시 (False, response_tuple) 반환"""
    role = _get_user_role()
    if role != '관리자':
        return False, (jsonify({
            'success': False,
            'message': '거래명세서 메뉴는 관리자 전용입니다.'
        }), 403)
    return True, None


@invoice_bp.before_request
def _before_invoice_request():
    """모든 /api/invoice/* 요청 전: 테이블 초기화 + 관리자 체크 (health 제외)"""
    # 1. 테이블 초기화
    try:
        init_invoice_tables()
    except Exception as e:
        print(f"[오류] 거래명세서 테이블 초기화 실패: {e}")
        # health 엔드포인트는 실패해도 진행 (DB 미연결 환경 대비)

    # 2. health 엔드포인트는 관리자 체크 생략
    if request.path.rstrip('/').endswith('/health'):
        return None

    # 3. 그 외 모든 엔드포인트: 관리자 체크
    ok, err = _require_invoice_admin()
    if not ok:
        return err[0], err[1]
    return None


@invoice_bp.route('/health', methods=['GET'])
def health():
    """헬스체크 (테스트용, 관리자 체크 생략)"""
    return jsonify({
        'success': True,
        'message': '거래명세서 API 정상',
        'module': 'invoice'
    })


@invoice_bp.route('/products', methods=['GET'])
def get_products():
    """상품 목록 (검색, is_active 필터)"""
    try:
        search = request.args.get('search', '').strip()
        include_inactive = request.args.get('include_inactive', '0') == '1'

        conn = get_db_connection()
        if USE_POSTGRESQL:
            cursor = conn.cursor(cursor_factory=RealDictCursor)
        else:
            cursor = conn.cursor()

        try:
            if USE_POSTGRESQL:
                sql = '''
                    SELECT id, product_code, product_name, qty_per_carton,
                           purchase_price, wholesale_price, group_buy_price, retail_price,
                           expiry_days, memo, image_url, category, is_active,
                           created_at, updated_at
                    FROM invoice_products
                    WHERE 1=1
                '''
                params = []
                if not include_inactive:
                    sql += ' AND (is_active IS NULL OR is_active = TRUE)'
                if search:
                    sql += ' AND (product_code ILIKE %s OR product_name ILIKE %s OR memo ILIKE %s)'
                    p = f'%{search}%'
                    params = [p, p, p]
                sql += ' ORDER BY product_code ASC'
                cursor.execute(sql, params if params else None)
            else:
                sql = '''
                    SELECT id, product_code, product_name, qty_per_carton,
                           purchase_price, wholesale_price, group_buy_price, retail_price,
                           expiry_days, memo, image_url, category, is_active,
                           created_at, updated_at
                    FROM invoice_products
                    WHERE 1=1
                '''
                params = []
                if not include_inactive:
                    sql += ' AND (is_active IS NULL OR is_active = 1)'
                if search:
                    sql += ' AND (product_code LIKE ? OR product_name LIKE ? OR memo LIKE ?)'
                    p = f'%{search}%'
                    params = [p, p, p]
                sql += ' ORDER BY product_code ASC'
                cursor.execute(sql, params if params else None)

            rows = cursor.fetchall()
            data = [_row_to_dict(r) for r in rows]
            return jsonify({'success': True, 'data': data, 'count': len(data)})
        finally:
            cursor.close()
            conn.close()
    except Exception as e:
        print(f"[오류] 상품 목록 조회: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'message': str(e), 'data': []}), 500


@invoice_bp.route('/products/<int:product_id>', methods=['GET'])
def get_product(product_id):
    """상품 상세 조회"""
    try:
        conn = get_db_connection()
        if USE_POSTGRESQL:
            cursor = conn.cursor(cursor_factory=RealDictCursor)
        else:
            cursor = conn.cursor()
        try:
            if USE_POSTGRESQL:
                cursor.execute(
                    'SELECT * FROM invoice_products WHERE id = %s', (product_id,)
                )
            else:
                cursor.execute('SELECT * FROM invoice_products WHERE id = ?', (product_id,))
            row = cursor.fetchone()
            if not row:
                return jsonify({'success': False, 'message': '상품을 찾을 수 없습니다.'}), 404
            return jsonify({'success': True, 'data': _row_to_dict(row)})
        finally:
            cursor.close()
            conn.close()
    except Exception as e:
        print(f"[오류] 상품 상세 조회: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500


@invoice_bp.route('/products', methods=['POST'])
def create_product():
    """상품 등록"""
    try:
        data = request.get_json() or {}
        product_code = (data.get('product_code') or '').strip()
        product_name = (data.get('product_name') or '').strip()
        qty_per_carton = int(data.get('qty_per_carton', 1) or 1)
        purchase_price = int(data.get('purchase_price', 0) or 0)
        wholesale_price = int(data.get('wholesale_price', 0) or 0)
        group_buy_price = int(data.get('group_buy_price', 0) or 0)
        retail_price = int(data.get('retail_price', 0) or 0)
        expiry_days = data.get('expiry_days')
        if expiry_days is not None and expiry_days != '':
            expiry_days = int(expiry_days) if expiry_days else None
        memo = (data.get('memo') or '').strip() or None
        image_url = (data.get('image_url') or '').strip() or None
        category = (data.get('category') or '').strip() or None

        if not product_code:
            return jsonify({'success': False, 'message': '상품고유번호는 필수입니다.'}), 400
        if not product_name:
            return jsonify({'success': False, 'message': '상품명은 필수입니다.'}), 400

        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            if USE_POSTGRESQL:
                cursor.execute('''
                    INSERT INTO invoice_products
                    (product_code, product_name, qty_per_carton, purchase_price, wholesale_price,
                     group_buy_price, retail_price, expiry_days, memo, image_url, category)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    RETURNING id
                ''', (product_code, product_name, qty_per_carton, purchase_price, wholesale_price,
                      group_buy_price, retail_price, expiry_days, memo, image_url, category))
                row = cursor.fetchone()
                new_id = row[0] if row else None
            else:
                cursor.execute('''
                    INSERT INTO invoice_products
                    (product_code, product_name, qty_per_carton, purchase_price, wholesale_price,
                     group_buy_price, retail_price, expiry_days, memo, image_url, category)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (product_code, product_name, qty_per_carton, purchase_price, wholesale_price,
                      group_buy_price, retail_price, expiry_days, memo, image_url, category))
                new_id = cursor.lastrowid
            conn.commit()
            return jsonify({'success': True, 'message': '상품이 등록되었습니다.', 'id': new_id})
        except Exception as db_err:
            conn.rollback()
            err_msg = str(db_err).lower()
            if 'unique' in err_msg or 'duplicate' in err_msg or 'already exists' in err_msg:
                return jsonify({'success': False, 'message': '이미 존재하는 상품고유번호입니다.'}), 400
            raise
        finally:
            cursor.close()
            conn.close()
    except Exception as e:
        print(f"[오류] 상품 등록: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'message': str(e)}), 500


@invoice_bp.route('/products/<int:product_id>', methods=['PUT'])
def update_product(product_id):
    """상품 수정"""
    try:
        data = request.get_json() or {}
        product_code = (data.get('product_code') or '').strip()
        product_name = (data.get('product_name') or '').strip()
        qty_per_carton = int(data.get('qty_per_carton', 1) or 1)
        purchase_price = int(data.get('purchase_price', 0) or 0)
        wholesale_price = int(data.get('wholesale_price', 0) or 0)
        group_buy_price = int(data.get('group_buy_price', 0) or 0)
        retail_price = int(data.get('retail_price', 0) or 0)
        expiry_days = data.get('expiry_days')
        if expiry_days is not None and expiry_days != '':
            expiry_days = int(expiry_days) if expiry_days else None
        memo = (data.get('memo') or '').strip() or None
        image_url = data.get('image_url')
        if image_url is not None:
            image_url = (image_url or '').strip() or None
        category = (data.get('category') or '').strip() or None
        is_active = data.get('is_active')
        if is_active is not None:
            is_active = bool(is_active) if isinstance(is_active, bool) else (str(is_active) in ('1', 'true', 'True'))

        if not product_code:
            return jsonify({'success': False, 'message': '상품고유번호는 필수입니다.'}), 400
        if not product_name:
            return jsonify({'success': False, 'message': '상품명은 필수입니다.'}), 400

        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            if USE_POSTGRESQL:
                updates = [
                    'product_code=%s', 'product_name=%s', 'qty_per_carton=%s',
                    'purchase_price=%s', 'wholesale_price=%s', 'group_buy_price=%s', 'retail_price=%s',
                    'expiry_days=%s', 'memo=%s', 'category=%s', 'updated_at=CURRENT_TIMESTAMP'
                ]
                params = [product_code, product_name, qty_per_carton, purchase_price, wholesale_price,
                          group_buy_price, retail_price, expiry_days, memo, category]
                if image_url is not None:
                    updates.append('image_url=%s')
                    params.append(image_url)
                if is_active is not None:
                    updates.append('is_active=%s')
                    params.append(is_active)
                params.append(product_id)
                cursor.execute(
                    f"UPDATE invoice_products SET {', '.join(updates)} WHERE id = %s",
                    params
                )
            else:
                updates = [
                    'product_code=?', 'product_name=?', 'qty_per_carton=?',
                    'purchase_price=?', 'wholesale_price=?', 'group_buy_price=?', 'retail_price=?',
                    'expiry_days=?', 'memo=?', 'category=?', 'updated_at=CURRENT_TIMESTAMP'
                ]
                params = [product_code, product_name, qty_per_carton, purchase_price, wholesale_price,
                          group_buy_price, retail_price, expiry_days, memo, category]
                if image_url is not None:
                    updates.append('image_url=?')
                    params.append(image_url)
                if is_active is not None:
                    updates.append('is_active=?')
                    params.append(is_active)
                params.append(product_id)
                cursor.execute(
                    f"UPDATE invoice_products SET {', '.join(updates)} WHERE id = ?",
                    params
                )
            conn.commit()
            if cursor.rowcount == 0:
                return jsonify({'success': False, 'message': '상품을 찾을 수 없습니다.'}), 404
            return jsonify({'success': True, 'message': '상품이 수정되었습니다.'})
        except Exception as db_err:
            conn.rollback()
            err_msg = str(db_err).lower()
            if 'unique' in err_msg or 'duplicate' in err_msg:
                return jsonify({'success': False, 'message': '이미 존재하는 상품고유번호입니다.'}), 400
            raise
        finally:
            cursor.close()
            conn.close()
    except Exception as e:
        print(f"[오류] 상품 수정: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'message': str(e)}), 500


@invoice_bp.route('/products/<int:product_id>', methods=['DELETE'])
def delete_product(product_id):
    """상품 삭제 (is_active=false로 소프트 삭제)"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            if USE_POSTGRESQL:
                cursor.execute(
                    'UPDATE invoice_products SET is_active = FALSE, updated_at = CURRENT_TIMESTAMP WHERE id = %s',
                    (product_id,)
                )
            else:
                cursor.execute(
                    'UPDATE invoice_products SET is_active = 0, updated_at = CURRENT_TIMESTAMP WHERE id = ?',
                    (product_id,)
                )
            conn.commit()
            if cursor.rowcount == 0:
                return jsonify({'success': False, 'message': '상품을 찾을 수 없습니다.'}), 404
            return jsonify({'success': True, 'message': '상품이 비활성화되었습니다.'})
        finally:
            cursor.close()
            conn.close()
    except Exception as e:
        print(f"[오류] 상품 삭제: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500


@invoice_bp.route('/products/upload-image', methods=['POST'])
def upload_product_image():
    """상품 사진 업로드 (Cloudinary)"""
    try:
        data = request.get_json() or {}
        base64_data = data.get('base64') or data.get('image') or ''
        filename = (data.get('filename') or 'product.jpg').strip()

        if not base64_data:
            return jsonify({'success': False, 'message': '이미지 데이터가 없습니다.'}), 400

        product_code = (data.get('product_code') or 'product').strip()
        from datetime import datetime
        ts = datetime.now().strftime('%Y%m%d_%H%M%S')
        safe_name = f"{product_code}_{ts}".replace(' ', '_')[:50]
        if '.' not in filename:
            filename = f"{safe_name}.jpg"
        else:
            ext = filename.split('.')[-1]
            filename = f"{safe_name}.{ext}"

        url = upload_single_file_to_cloudinary(base64_data, filename, 'product_images')
        return jsonify({'success': True, 'url': url, 'message': '이미지가 업로드되었습니다.'})
    except Exception as e:
        print(f"[오류] 상품 이미지 업로드: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'message': str(e)}), 500


# ========== 거래처 API ==========

@invoice_bp.route('/companies', methods=['GET'])
def get_companies():
    """화주사 목록 (거래처 등록 시 선택용)"""
    try:
        companies = get_all_companies(include_inactive=False)
        data = [{'id': c.get('id'), 'company_name': c.get('company_name')} for c in (companies or []) if c.get('role') != '관리자']
        return jsonify({'success': True, 'data': data})
    except Exception as e:
        print(f"[오류] 화주사 목록: {e}")
        return jsonify({'success': False, 'message': str(e), 'data': []}), 500


@invoice_bp.route('/customers', methods=['GET'])
def get_customers():
    """거래처 목록 (company_id 필터: ''=전체, 'null'=독립만, 숫자=해당 화주사)"""
    try:
        company_filter = request.args.get('company_id', '').strip()

        conn = get_db_connection()
        if USE_POSTGRESQL:
            cursor = conn.cursor(cursor_factory=RealDictCursor)
        else:
            cursor = conn.cursor()

        try:
            if USE_POSTGRESQL:
                sql = '''
                    SELECT c.id, c.customer_name, c.contact_tel, c.address, c.business_number,
                           c.representative, c.company_id, c.memo, c.is_active, c.created_at, c.updated_at,
                           co.company_name
                    FROM invoice_customers c
                    LEFT JOIN companies co ON c.company_id = co.id
                    WHERE 1=1
                '''
                params = []
                if company_filter == 'null':
                    sql += ' AND c.company_id IS NULL'
                elif company_filter and company_filter.isdigit():
                    sql += ' AND c.company_id = %s'
                    params.append(int(company_filter))
                sql += ' AND (c.is_active IS NULL OR c.is_active = TRUE)'
                sql += ' ORDER BY c.customer_name ASC'
                cursor.execute(sql, params if params else None)
            else:
                sql = '''
                    SELECT c.id, c.customer_name, c.contact_tel, c.address, c.business_number,
                           c.representative, c.company_id, c.memo, c.is_active, c.created_at, c.updated_at,
                           co.company_name
                    FROM invoice_customers c
                    LEFT JOIN companies co ON c.company_id = co.id
                    WHERE (c.is_active IS NULL OR c.is_active = 1)
                '''
                params = []
                if company_filter == 'null':
                    sql += ' AND c.company_id IS NULL'
                elif company_filter and company_filter.isdigit():
                    sql += ' AND c.company_id = ?'
                    params.append(int(company_filter))
                sql += ' ORDER BY c.customer_name ASC'
                cursor.execute(sql, params if params else None)

            rows = cursor.fetchall()
            data = []
            for r in rows:
                d = _row_to_dict(r)
                if d:
                    d['company_name'] = d.get('company_name') if 'company_name' in d else None
                data.append(d)
            return jsonify({'success': True, 'data': data, 'count': len(data)})
        finally:
            cursor.close()
            conn.close()
    except Exception as e:
        print(f"[오류] 거래처 목록: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'message': str(e), 'data': []}), 500


@invoice_bp.route('/customers/<int:customer_id>', methods=['GET'])
def get_customer(customer_id):
    """거래처 상세 조회"""
    try:
        conn = get_db_connection()
        if USE_POSTGRESQL:
            cursor = conn.cursor(cursor_factory=RealDictCursor)
        else:
            cursor = conn.cursor()
        try:
            if USE_POSTGRESQL:
                cursor.execute('''
                    SELECT c.*, co.company_name FROM invoice_customers c
                    LEFT JOIN companies co ON c.company_id = co.id WHERE c.id = %s
                ''', (customer_id,))
            else:
                cursor.execute('''
                    SELECT c.*, co.company_name FROM invoice_customers c
                    LEFT JOIN companies co ON c.company_id = co.id WHERE c.id = ?
                ''', (customer_id,))
            row = cursor.fetchone()
            if not row:
                return jsonify({'success': False, 'message': '거래처를 찾을 수 없습니다.'}), 404
            return jsonify({'success': True, 'data': _row_to_dict(row)})
        finally:
            cursor.close()
            conn.close()
    except Exception as e:
        print(f"[오류] 거래처 상세: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500


@invoice_bp.route('/customers', methods=['POST'])
def create_customer():
    """거래처 등록"""
    try:
        data = request.get_json() or {}
        customer_name = (data.get('customer_name') or '').strip()
        contact_tel = (data.get('contact_tel') or '').strip() or None
        address = (data.get('address') or '').strip() or None
        business_number = (data.get('business_number') or '').strip() or None
        representative = (data.get('representative') or '').strip() or None
        company_id = data.get('company_id')
        if company_id is not None and company_id != '':
            company_id = int(company_id) if company_id else None
        else:
            company_id = None
        memo = (data.get('memo') or '').strip() or None

        if not customer_name:
            return jsonify({'success': False, 'message': '거래처명은 필수입니다.'}), 400

        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            if USE_POSTGRESQL:
                cursor.execute('''
                    INSERT INTO invoice_customers
                    (customer_name, contact_tel, address, business_number, representative, company_id, memo)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    RETURNING id
                ''', (customer_name, contact_tel, address, business_number, representative, company_id, memo))
                row = cursor.fetchone()
                new_id = row[0] if row else None
            else:
                cursor.execute('''
                    INSERT INTO invoice_customers
                    (customer_name, contact_tel, address, business_number, representative, company_id, memo)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (customer_name, contact_tel, address, business_number, representative, company_id, memo))
                new_id = cursor.lastrowid
            conn.commit()
            return jsonify({'success': True, 'message': '거래처가 등록되었습니다.', 'id': new_id})
        finally:
            cursor.close()
            conn.close()
    except Exception as e:
        print(f"[오류] 거래처 등록: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'message': str(e)}), 500


@invoice_bp.route('/customers/<int:customer_id>', methods=['PUT'])
def update_customer(customer_id):
    """거래처 수정"""
    try:
        data = request.get_json() or {}
        customer_name = (data.get('customer_name') or '').strip()
        contact_tel = (data.get('contact_tel') or '').strip() or None
        address = (data.get('address') or '').strip() or None
        business_number = (data.get('business_number') or '').strip() or None
        representative = (data.get('representative') or '').strip() or None
        company_id = data.get('company_id')
        if company_id is not None and company_id != '':
            company_id = int(company_id) if company_id else None
        else:
            company_id = None
        memo = (data.get('memo') or '').strip() or None

        if not customer_name:
            return jsonify({'success': False, 'message': '거래처명은 필수입니다.'}), 400

        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            if USE_POSTGRESQL:
                cursor.execute('''
                    UPDATE invoice_customers SET
                    customer_name=%s, contact_tel=%s, address=%s, business_number=%s,
                    representative=%s, company_id=%s, memo=%s, updated_at=CURRENT_TIMESTAMP
                    WHERE id=%s
                ''', (customer_name, contact_tel, address, business_number, representative, company_id, memo, customer_id))
            else:
                cursor.execute('''
                    UPDATE invoice_customers SET
                    customer_name=?, contact_tel=?, address=?, business_number=?,
                    representative=?, company_id=?, memo=?, updated_at=CURRENT_TIMESTAMP
                    WHERE id=?
                ''', (customer_name, contact_tel, address, business_number, representative, company_id, memo, customer_id))
            conn.commit()
            if cursor.rowcount == 0:
                return jsonify({'success': False, 'message': '거래처를 찾을 수 없습니다.'}), 404
            return jsonify({'success': True, 'message': '거래처가 수정되었습니다.'})
        finally:
            cursor.close()
            conn.close()
    except Exception as e:
        print(f"[오류] 거래처 수정: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500


@invoice_bp.route('/customers/<int:customer_id>', methods=['DELETE'])
def delete_customer(customer_id):
    """거래처 삭제 (is_active=false)"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            if USE_POSTGRESQL:
                cursor.execute(
                    'UPDATE invoice_customers SET is_active = FALSE, updated_at = CURRENT_TIMESTAMP WHERE id = %s',
                    (customer_id,)
                )
            else:
                cursor.execute(
                    'UPDATE invoice_customers SET is_active = 0, updated_at = CURRENT_TIMESTAMP WHERE id = ?',
                    (customer_id,)
                )
            conn.commit()
            if cursor.rowcount == 0:
                return jsonify({'success': False, 'message': '거래처를 찾을 수 없습니다.'}), 404
            return jsonify({'success': True, 'message': '거래처가 비활성화되었습니다.'})
        finally:
            cursor.close()
            conn.close()
    except Exception as e:
        print(f"[오류] 거래처 삭제: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500


# ========== 거래명세서 API ==========

def _generate_statement_no(conn, cursor):
    """명세서 번호 자동 생성: INV-{년}-{5자리}"""
    year = datetime.now().strftime('%Y')
    prefix = f'INV-{year}-'
    if USE_POSTGRESQL:
        cursor.execute(
            "SELECT statement_no FROM invoice_statements WHERE statement_no LIKE %s ORDER BY statement_no DESC LIMIT 1",
            (prefix + '%',)
        )
    else:
        cursor.execute(
            "SELECT statement_no FROM invoice_statements WHERE statement_no LIKE ? ORDER BY statement_no DESC LIMIT 1",
            (prefix + '%',)
        )
    row = cursor.fetchone()
    if row:
        last_no = row[0] if isinstance(row, (tuple, list)) else row.get('statement_no', '')
        try:
            num = int(last_no.replace(prefix, '')) + 1
        except (ValueError, TypeError):
            num = 1
    else:
        num = 1
    return f'{prefix}{num:05d}'


@invoice_bp.route('/statements', methods=['GET'])
def get_statements():
    """거래명세서 목록 (날짜, 거래처, 입금여부 필터)"""
    try:
        start_date = request.args.get('start_date', '').strip()
        end_date = request.args.get('end_date', '').strip()
        customer_id = request.args.get('customer_id', '').strip()
        is_paid = request.args.get('is_paid', '').strip()

        conn = get_db_connection()
        if USE_POSTGRESQL:
            cursor = conn.cursor(cursor_factory=RealDictCursor)
        else:
            cursor = conn.cursor()

        try:
            sql = '''
                SELECT s.id, s.statement_no, s.statement_date, s.customer_id, s.total_amount,
                       s.vat_amount, s.grand_total, s.memo, s.is_paid, s.paid_at, s.created_at,
                       c.customer_name
                FROM invoice_statements s
                JOIN invoice_customers c ON s.customer_id = c.id
                WHERE 1=1
            '''
            params = []
            if start_date:
                if USE_POSTGRESQL:
                    sql += ' AND s.statement_date >= %s'
                else:
                    sql += ' AND s.statement_date >= ?'
                params.append(start_date)
            if end_date:
                if USE_POSTGRESQL:
                    sql += ' AND s.statement_date <= %s'
                else:
                    sql += ' AND s.statement_date <= ?'
                params.append(end_date)
            if customer_id and customer_id.isdigit():
                if USE_POSTGRESQL:
                    sql += ' AND s.customer_id = %s'
                else:
                    sql += ' AND s.customer_id = ?'
                params.append(int(customer_id))
            if is_paid == '1':
                sql += ' AND (s.is_paid = TRUE OR s.is_paid = 1)'
            elif is_paid == '0':
                sql += ' AND (s.is_paid = FALSE OR s.is_paid = 0 OR s.is_paid IS NULL)'
            sql += ' ORDER BY s.statement_date DESC, s.id DESC'

            cursor.execute(sql, params if params else None)
            rows = cursor.fetchall()
            data = [_row_to_dict(r) for r in rows]
            return jsonify({'success': True, 'data': data, 'count': len(data)})
        finally:
            cursor.close()
            conn.close()
    except Exception as e:
        print(f"[오류] 명세서 목록: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'message': str(e), 'data': []}), 500


@invoice_bp.route('/statements/<int:statement_id>', methods=['GET'])
def get_statement(statement_id):
    """거래명세서 상세 (품목 포함)"""
    try:
        conn = get_db_connection()
        if USE_POSTGRESQL:
            cursor = conn.cursor(cursor_factory=RealDictCursor)
        else:
            cursor = conn.cursor()
        try:
            if USE_POSTGRESQL:
                cursor.execute('''
                    SELECT s.*, c.customer_name, c.contact_tel, c.address, c.business_number, c.representative
                    FROM invoice_statements s
                    JOIN invoice_customers c ON s.customer_id = c.id
                    WHERE s.id = %s
                ''', (statement_id,))
            else:
                cursor.execute('''
                    SELECT s.*, c.customer_name, c.contact_tel, c.address, c.business_number, c.representative
                    FROM invoice_statements s
                    JOIN invoice_customers c ON s.customer_id = c.id
                    WHERE s.id = ?
                ''', (statement_id,))
            row = cursor.fetchone()
            if not row:
                return jsonify({'success': False, 'message': '명세서를 찾을 수 없습니다.'}), 404

            stmt = _row_to_dict(row)
            if USE_POSTGRESQL:
                cursor.execute(
                    'SELECT * FROM invoice_statement_items WHERE statement_id = %s ORDER BY sort_order, id',
                    (statement_id,)
                )
            else:
                cursor.execute(
                    'SELECT * FROM invoice_statement_items WHERE statement_id = ? ORDER BY sort_order, id',
                    (statement_id,)
                )
            items = [_row_to_dict(r) for r in cursor.fetchall()]
            stmt['items'] = items
            return jsonify({'success': True, 'data': stmt})
        finally:
            cursor.close()
            conn.close()
    except Exception as e:
        print(f"[오류] 명세서 상세: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500


@invoice_bp.route('/statements/<int:statement_id>', methods=['PUT'])
def update_statement(statement_id):
    """거래명세서 수정"""
    try:
        data = request.get_json() or {}
        statement_date = (data.get('statement_date') or '').strip()
        customer_id = data.get('customer_id')
        memo = (data.get('memo') or '').strip() or None
        items = data.get('items') or []

        if not statement_date:
            return jsonify({'success': False, 'message': '거래일자를 입력하세요.'}), 400
        if not customer_id:
            return jsonify({'success': False, 'message': '거래처를 선택하세요.'}), 400
        customer_id = int(customer_id)
        if not items or len(items) == 0:
            return jsonify({'success': False, 'message': '품목을 1개 이상 추가하세요.'}), 400

        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            total_amount = 0
            for it in items:
                qty = int(it.get('qty', 0) or 0)
                unit_price = int(it.get('unit_price', 0) or 0)
                total_amount += qty * unit_price
            vat_amount = int(total_amount * 0.1)
            grand_total = total_amount + vat_amount

            if USE_POSTGRESQL:
                cursor.execute('''
                    UPDATE invoice_statements SET
                    statement_date=%s, customer_id=%s, total_amount=%s, vat_amount=%s,
                    grand_total=%s, memo=%s, updated_at=CURRENT_TIMESTAMP
                    WHERE id=%s
                ''', (statement_date, customer_id, total_amount, vat_amount, grand_total, memo, statement_id))
            else:
                cursor.execute('''
                    UPDATE invoice_statements SET
                    statement_date=?, customer_id=?, total_amount=?, vat_amount=?,
                    grand_total=?, memo=?, updated_at=CURRENT_TIMESTAMP
                    WHERE id=?
                ''', (statement_date, customer_id, total_amount, vat_amount, grand_total, memo, statement_id))
            if cursor.rowcount == 0:
                return jsonify({'success': False, 'message': '명세서를 찾을 수 없습니다.'}), 404

            if USE_POSTGRESQL:
                cursor.execute('DELETE FROM invoice_statement_items WHERE statement_id = %s', (statement_id,))
            else:
                cursor.execute('DELETE FROM invoice_statement_items WHERE statement_id = ?', (statement_id,))

            for i, it in enumerate(items):
                product_id = int(it.get('product_id', 0) or 0)
                product_name = (it.get('product_name') or '').strip() or '-'
                qty = int(it.get('qty', 0) or 0)
                unit_price = int(it.get('unit_price', 0) or 0)
                amount = qty * unit_price
                if USE_POSTGRESQL:
                    cursor.execute('''
                        INSERT INTO invoice_statement_items
                        (statement_id, product_id, product_name, qty, unit_price, amount, sort_order)
                        VALUES (%s, %s, %s, %s, %s, %s, %s)
                    ''', (statement_id, product_id, product_name, qty, unit_price, amount, i))
                else:
                    cursor.execute('''
                        INSERT INTO invoice_statement_items
                        (statement_id, product_id, product_name, qty, unit_price, amount, sort_order)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    ''', (statement_id, product_id, product_name, qty, unit_price, amount, i))

            conn.commit()
            return jsonify({'success': True, 'message': '거래명세서가 수정되었습니다.'})
        except Exception as db_err:
            conn.rollback()
            raise
        finally:
            cursor.close()
            conn.close()
    except Exception as e:
        print(f"[오류] 명세서 수정: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'message': str(e)}), 500


@invoice_bp.route('/statements', methods=['POST'])
def create_statement():
    """거래명세서 작성"""
    try:
        data = request.get_json() or {}
        statement_date = (data.get('statement_date') or '').strip()
        customer_id = data.get('customer_id')
        memo = (data.get('memo') or '').strip() or None
        items = data.get('items') or []

        if not statement_date:
            return jsonify({'success': False, 'message': '거래일자를 입력하세요.'}), 400
        if not customer_id:
            return jsonify({'success': False, 'message': '거래처를 선택하세요.'}), 400
        customer_id = int(customer_id)
        if not items or len(items) == 0:
            return jsonify({'success': False, 'message': '품목을 1개 이상 추가하세요.'}), 400

        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            statement_no = _generate_statement_no(conn, cursor)
            total_amount = 0
            for it in items:
                qty = int(it.get('qty', 0) or 0)
                unit_price = int(it.get('unit_price', 0) or 0)
                total_amount += qty * unit_price
            vat_amount = int(total_amount * 0.1)
            grand_total = total_amount + vat_amount

            if USE_POSTGRESQL:
                cursor.execute('''
                    INSERT INTO invoice_statements
                    (statement_no, statement_date, customer_id, total_amount, vat_amount, grand_total, memo)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    RETURNING id
                ''', (statement_no, statement_date, customer_id, total_amount, vat_amount, grand_total, memo))
                row = cursor.fetchone()
                stmt_id = row[0] if row else None
            else:
                cursor.execute('''
                    INSERT INTO invoice_statements
                    (statement_no, statement_date, customer_id, total_amount, vat_amount, grand_total, memo)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (statement_no, statement_date, customer_id, total_amount, vat_amount, grand_total, memo))
                stmt_id = cursor.lastrowid

            for i, it in enumerate(items):
                product_id = int(it.get('product_id', 0) or 0)
                product_name = (it.get('product_name') or '').strip() or '-'
                qty = int(it.get('qty', 0) or 0)
                unit_price = int(it.get('unit_price', 0) or 0)
                amount = qty * unit_price
                if USE_POSTGRESQL:
                    cursor.execute('''
                        INSERT INTO invoice_statement_items
                        (statement_id, product_id, product_name, qty, unit_price, amount, sort_order)
                        VALUES (%s, %s, %s, %s, %s, %s, %s)
                    ''', (stmt_id, product_id, product_name, qty, unit_price, amount, i))
                else:
                    cursor.execute('''
                        INSERT INTO invoice_statement_items
                        (statement_id, product_id, product_name, qty, unit_price, amount, sort_order)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    ''', (stmt_id, product_id, product_name, qty, unit_price, amount, i))

            conn.commit()
            return jsonify({'success': True, 'message': '거래명세서가 등록되었습니다.', 'id': stmt_id, 'statement_no': statement_no})
        except Exception as db_err:
            conn.rollback()
            raise
        finally:
            cursor.close()
            conn.close()
    except Exception as e:
        print(f"[오류] 명세서 등록: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'message': str(e)}), 500


@invoice_bp.route('/statements/<int:statement_id>/paid', methods=['PUT'])
def update_statement_paid(statement_id):
    """입금 완료 처리"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            if USE_POSTGRESQL:
                cursor.execute('''
                    UPDATE invoice_statements SET is_paid = TRUE, paid_at = CURRENT_TIMESTAMP, updated_at = CURRENT_TIMESTAMP
                    WHERE id = %s
                ''', (statement_id,))
            else:
                cursor.execute('''
                    UPDATE invoice_statements SET is_paid = 1, paid_at = CURRENT_TIMESTAMP, updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                ''', (statement_id,))
            conn.commit()
            if cursor.rowcount == 0:
                return jsonify({'success': False, 'message': '명세서를 찾을 수 없습니다.'}), 404
            return jsonify({'success': True, 'message': '입금 완료 처리되었습니다.'})
        finally:
            cursor.close()
            conn.close()
    except Exception as e:
        print(f"[오류] 입금 완료: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500


# ========== 정산 API ==========

@invoice_bp.route('/settlements/summary', methods=['GET'])
def get_settlements_summary():
    """월별/년별 정산 요약 (group=month | group=year)"""
    try:
        group_by = request.args.get('group', 'month').strip().lower()
        if group_by not in ('month', 'year'):
            group_by = 'month'

        conn = get_db_connection()
        if USE_POSTGRESQL:
            cursor = conn.cursor(cursor_factory=RealDictCursor)
        else:
            cursor = conn.cursor()

        try:
            if group_by == 'year':
                if USE_POSTGRESQL:
                    cursor.execute('''
                        SELECT TO_CHAR(s.statement_date, 'YYYY') AS period,
                               COUNT(*) AS cnt,
                               COALESCE(SUM(s.grand_total), 0)::BIGINT AS total_amount,
                               COALESCE(SUM(CASE WHEN s.is_paid = TRUE THEN s.grand_total ELSE 0 END), 0)::BIGINT AS paid_amount,
                               COALESCE(SUM(CASE WHEN s.is_paid = FALSE OR s.is_paid IS NULL THEN s.grand_total ELSE 0 END), 0)::BIGINT AS unpaid_amount
                        FROM invoice_statements s
                        GROUP BY TO_CHAR(s.statement_date, 'YYYY')
                        ORDER BY period DESC
                    ''')
                else:
                    cursor.execute('''
                        SELECT strftime('%Y', s.statement_date) AS period,
                               COUNT(*) AS cnt,
                               SUM(s.grand_total) AS total_amount,
                               SUM(CASE WHEN s.is_paid = 1 THEN s.grand_total ELSE 0 END) AS paid_amount,
                               SUM(CASE WHEN s.is_paid = 0 OR s.is_paid IS NULL THEN s.grand_total ELSE 0 END) AS unpaid_amount
                        FROM invoice_statements s
                        GROUP BY strftime('%Y', s.statement_date)
                        ORDER BY period DESC
                    ''')
            else:
                if USE_POSTGRESQL:
                    cursor.execute('''
                        SELECT TO_CHAR(s.statement_date, 'YYYY-MM') AS period,
                               COUNT(*) AS cnt,
                               COALESCE(SUM(s.grand_total), 0)::BIGINT AS total_amount,
                               COALESCE(SUM(CASE WHEN s.is_paid = TRUE THEN s.grand_total ELSE 0 END), 0)::BIGINT AS paid_amount,
                               COALESCE(SUM(CASE WHEN s.is_paid = FALSE OR s.is_paid IS NULL THEN s.grand_total ELSE 0 END), 0)::BIGINT AS unpaid_amount
                        FROM invoice_statements s
                        GROUP BY TO_CHAR(s.statement_date, 'YYYY-MM')
                        ORDER BY period DESC
                    ''')
                else:
                    cursor.execute('''
                        SELECT strftime('%Y-%m', s.statement_date) AS period,
                               COUNT(*) AS cnt,
                               SUM(s.grand_total) AS total_amount,
                               SUM(CASE WHEN s.is_paid = 1 THEN s.grand_total ELSE 0 END) AS paid_amount,
                               SUM(CASE WHEN s.is_paid = 0 OR s.is_paid IS NULL THEN s.grand_total ELSE 0 END) AS unpaid_amount
                        FROM invoice_statements s
                        GROUP BY strftime('%Y-%m', s.statement_date)
                        ORDER BY period DESC
                    ''')

            rows = cursor.fetchall()
            data = []
            for r in rows:
                d = _row_to_dict(r)
                if d:
                    d['total_amount'] = int(d.get('total_amount') or 0)
                    d['paid_amount'] = int(d.get('paid_amount') or 0)
                    d['unpaid_amount'] = int(d.get('unpaid_amount') or 0)
                    d['cnt'] = int(d.get('cnt') or 0)
                    data.append(d)
            return jsonify({'success': True, 'data': data, 'group': group_by})
        finally:
            cursor.close()
            conn.close()
    except Exception as e:
        print(f"[오류] 정산 요약: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'message': str(e), 'data': []}), 500


@invoice_bp.route('/settlements/unpaid', methods=['GET'])
def get_settlements_unpaid():
    """미정산(미입금) 명세서 목록"""
    try:
        conn = get_db_connection()
        if USE_POSTGRESQL:
            cursor = conn.cursor(cursor_factory=RealDictCursor)
        else:
            cursor = conn.cursor()
        try:
            if USE_POSTGRESQL:
                cursor.execute('''
                    SELECT s.id, s.statement_no, s.statement_date, s.customer_id, s.total_amount,
                           s.vat_amount, s.grand_total, s.memo, s.is_paid, s.paid_at,
                           c.customer_name
                    FROM invoice_statements s
                    JOIN invoice_customers c ON s.customer_id = c.id
                    WHERE s.is_paid IS NOT TRUE
                    ORDER BY s.statement_date ASC, s.id ASC
                ''')
            else:
                cursor.execute('''
                    SELECT s.id, s.statement_no, s.statement_date, s.customer_id, s.total_amount,
                           s.vat_amount, s.grand_total, s.memo, s.is_paid, s.paid_at,
                           c.customer_name
                    FROM invoice_statements s
                    JOIN invoice_customers c ON s.customer_id = c.id
                    WHERE s.is_paid = 0 OR s.is_paid IS NULL
                    ORDER BY s.statement_date ASC, s.id ASC
                ''')
            rows = cursor.fetchall()
            data = [_row_to_dict(r) for r in rows]
            return jsonify({'success': True, 'data': data, 'count': len(data)})
        finally:
            cursor.close()
            conn.close()
    except Exception as e:
        print(f"[오류] 미정산 목록: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'message': str(e), 'data': []}), 500
