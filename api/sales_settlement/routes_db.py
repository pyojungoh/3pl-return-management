"""
매출정산 API 라우트 (jjay 최고관리자 전용)
- 월별/연별 정산 요약
- 기존 settlements API 재사용 (목록, 상세, 상태변경)
"""
from flask import Blueprint, request, jsonify
from api.database.models import get_db_connection, USE_POSTGRESQL, ensure_settlement_return_fee_column
from api.sales_settlement.analytics_db import build_settlement_analytics
from datetime import datetime, date
from urllib.parse import unquote

if USE_POSTGRESQL:
    from psycopg2.extras import RealDictCursor

sales_settlement_bp = Blueprint('sales_settlement', __name__, url_prefix='/api/sales_settlement')

# jjay만 접근 가능
JJAY_USERNAME = 'jjay'


def _settlement_statement_ready(item: dict) -> bool:
    """정산 명세서(엑셀) 생성에 쓸 금액·첨부가 갖춰졌는지 여부 (전달 건 표시·정렬용)."""
    for key in (
        'work_fee_file_url',
        'inout_fee_file_url',
        'shipping_fee_file_url',
        'tax_invoice_file_url',
    ):
        v = item.get(key)
        if v and str(v).strip():
            return True
    try:
        fc = int(item.get('settlement_file_count') or 0)
    except (TypeError, ValueError):
        fc = 0
    if fc > 0:
        return True
    line = (
        int(item.get('work_fee') or 0)
        + int(item.get('inout_fee') or 0)
        + int(item.get('shipping_fee') or 0)
        + int(item.get('collect_on_delivery_fee') or 0)
        + int(item.get('return_fee') or 0)
        + int(item.get('storage_fee') or 0)
        + int(item.get('special_work_fee') or 0)
        - int(item.get('error_deduction') or 0)
    )
    if line != 0:
        return True
    if int(item.get('total_amount') or 0) != 0:
        return True
    return False


def get_user_context():
    """사용자 컨텍스트 가져오기"""
    role = request.headers.get('X-User-Role', '').strip()
    username = request.headers.get('X-User-Name', '').strip()
    company_name = request.headers.get('X-Company-Name', '').strip()
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


def _check_jjay():
    """jjay 권한 확인, 실패 시 (None, response) 반환"""
    ctx = get_user_context()
    if ctx['username'].strip().lower() != JJAY_USERNAME or ctx['role'] != '관리자':
        return None, (jsonify({'success': False, 'message': '접근 권한이 없습니다. (jjay 전용)'}), 403)
    return ctx, None


@sales_settlement_bp.route('/check-access', methods=['GET'])
def check_access():
    """jjay 접근 권한 확인 (프론트엔드 탭 표시용)"""
    ctx = get_user_context()
    has_access = ctx['username'].strip().lower() == JJAY_USERNAME and ctx['role'] == '관리자'
    return jsonify({
        'success': True,
        'has_access': has_access
    })


@sales_settlement_bp.route('/summary', methods=['GET'])
def get_summary():
    """
    월별/연별 정산 요약
    - year_month: 2025-01 (월별) 또는 비워두면 전체
    - year: 2025 (연별 - 해당 연도 전체)
    """
    ctx, err = _check_jjay()
    if err:
        return err[0], err[1]
    try:
        year_month = request.args.get('year_month', '').strip()
        year = request.args.get('year', '').strip()
        if year_month and year and len(year_month) >= 7 and not year_month.startswith(f'{year}-'):
            year = ''

        conn = get_db_connection()
        ensure_settlement_return_fee_column(conn)
        if USE_POSTGRESQL:
            cursor = conn.cursor(cursor_factory=RealDictCursor)
        else:
            cursor = conn.cursor()

        try:
            where_clauses = []
            params = []

            if year_month:
                where_clauses.append('settlement_year_month = %s' if USE_POSTGRESQL else 'settlement_year_month = ?')
                params.append(year_month)
            if year:
                where_clauses.append('settlement_year_month LIKE %s' if USE_POSTGRESQL else 'settlement_year_month LIKE ?')
                params.append(f'{year}-%')

            where_sql = ' AND '.join(where_clauses) if where_clauses else '1=1'

            query = f'''
                SELECT 
                    s.id,
                    s.settlement_year_month,
                    s.company_name,
                    s.total_amount,
                    s.status,
                    s.work_fee, s.inout_fee, s.shipping_fee, s.storage_fee,
                    s.special_work_fee, s.error_deduction, s.collect_on_delivery_fee, s.return_fee,
                    s.work_fee_file_url,
                    s.inout_fee_file_url,
                    s.shipping_fee_file_url,
                    s.tax_invoice_file_url,
                    (SELECT COUNT(*) FROM settlement_files f WHERE f.settlement_id = s.id) AS settlement_file_count
                FROM settlements s
                WHERE {where_sql.replace("settlement_year_month", "s.settlement_year_month")}
                ORDER BY s.settlement_year_month DESC, s.company_name
            '''
            cursor.execute(query, params)
            rows = cursor.fetchall()
            result = [dict(row) for row in rows]

            for item in result:
                item['statement_ready'] = _settlement_statement_ready(item)
                for k in (
                    'work_fee_file_url',
                    'inout_fee_file_url',
                    'shipping_fee_file_url',
                    'tax_invoice_file_url',
                    'settlement_file_count',
                ):
                    item.pop(k, None)

            def _ss_sort_key(row):
                st = (row.get('status') or '대기').strip()
                name = (row.get('company_name') or '').strip()
                sr = bool(row.get('statement_ready'))
                if st in ('정산확인', '입금완료'):
                    return (0, 0, name)
                if st == '전달' and sr:
                    return (0, 1, name)
                if st == '대기':
                    return (1, 0, name)
                if st == '전달':
                    return (1, 1, name)
                return (2, 0, name)

            result.sort(key=_ss_sort_key)

            # 집계
            total_sales = 0
            by_company = {}
            by_status = {'대기': 0, '전달': 0, '정산확인': 0, '입금완료': 0}
            by_month = {}

            for item in result:
                amt = item.get('total_amount') or 0
                total_sales += amt
                company = item.get('company_name') or ''
                status = item.get('status') or '대기'
                ym = item.get('settlement_year_month') or ''

                if company:
                    by_company[company] = by_company.get(company, 0) + amt
                if status in by_status:
                    by_status[status] += 1
                if ym:
                    by_month[ym] = by_month.get(ym, 0) + amt

            # datetime 변환
            for item in result:
                for k, v in item.items():
                    if isinstance(v, datetime):
                        item[k] = v.strftime('%Y-%m-%d %H:%M:%S') if v else None
                    elif isinstance(v, date):
                        item[k] = v.strftime('%Y-%m-%d') if v else None

            return jsonify({
                'success': True,
                'data': {
                    'total_sales': total_sales,
                    'by_company': by_company,
                    'by_status': by_status,
                    'by_month': by_month,
                    'items': result,
                    'count': len(result)
                }
            })
        finally:
            cursor.close()
            conn.close()
    except Exception as e:
        print(f'[매출정산] 요약 조회 오류: {e}')
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


@sales_settlement_bp.route('/analytics', methods=['GET'])
def get_analytics():
    """
    연별 매출 통계 (월별·연별 시계열, 화주사 순위, KPI)
    Query: months_back (기본 24), year_from, year_to (연도 필터, 선택)
    """
    ctx, err = _check_jjay()
    if err:
        return err[0], err[1]
    try:
        months_back = int(request.args.get('months_back', 24))
        if months_back < 1:
            months_back = 24
        if months_back > 120:
            months_back = 120
        year_from = request.args.get('year_from', '').strip() or None
        year_to = request.args.get('year_to', '').strip() or None

        conn = get_db_connection()
        ensure_settlement_return_fee_column(conn)
        if USE_POSTGRESQL:
            cursor = conn.cursor(cursor_factory=RealDictCursor)
        else:
            cursor = conn.cursor()

        try:
            if USE_POSTGRESQL:
                cursor.execute('''
                    SELECT settlement_year_month, company_name, total_amount, status
                    FROM settlements
                    WHERE settlement_year_month IS NOT NULL AND TRIM(settlement_year_month) <> ''
                ''')
            else:
                cursor.execute('''
                    SELECT settlement_year_month, company_name, total_amount, status
                    FROM settlements
                    WHERE settlement_year_month IS NOT NULL AND settlement_year_month != ''
                ''')
            rows = cursor.fetchall()
            if USE_POSTGRESQL:
                list_rows = [dict(r) for r in rows]
            else:
                cols = [d[0] for d in cursor.description]
                list_rows = [dict(zip(cols, r)) for r in rows]
        finally:
            cursor.close()
            conn.close()

        payload = build_settlement_analytics(
            list_rows,
            months_back=months_back,
            year_from=year_from,
            year_to=year_to,
        )
        return jsonify({'success': True, 'data': payload})
    except Exception as e:
        print(f'[매출정산] analytics 오류: {e}')
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'message': str(e)}), 500


@sales_settlement_bp.route('/available-months', methods=['GET'])
def get_available_months():
    """정산 데이터가 있는 년월 목록"""
    ctx, err = _check_jjay()
    if err:
        return err[0], err[1]
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            if USE_POSTGRESQL:
                cursor.execute('''
                    SELECT DISTINCT settlement_year_month
                    FROM settlements
                    ORDER BY settlement_year_month DESC
                ''')
            else:
                cursor.execute('''
                    SELECT DISTINCT settlement_year_month
                    FROM settlements
                    ORDER BY settlement_year_month DESC
                ''')
            rows = cursor.fetchall()
            months = [r[0] for r in rows if r[0]]
            return jsonify({'success': True, 'data': months})
        finally:
            cursor.close()
            conn.close()
    except Exception as e:
        print(f'[매출정산] 년월 목록 오류: {e}')
        return jsonify({'success': False, 'message': str(e)}), 500
