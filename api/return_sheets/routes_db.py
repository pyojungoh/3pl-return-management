"""
시트 관리 API 라우트 (SQLite 데이터베이스 기반)
"""
from flask import Blueprint, jsonify
from api.database.models import get_available_months

# Blueprint 생성
return_sheets_bp = Blueprint('return_sheets', __name__, url_prefix='/api/sheets')


@return_sheets_bp.route('/months', methods=['GET'])
def get_available_months_route():
    """
    사용 가능한 월 목록 조회 API
    
    Returns:
        {
            "success": bool,
            "sheets": list,
            "message": str
        }
    """
    try:
        months = get_available_months()
        
        # 현재 월이 없으면 추가
        from datetime import datetime
        today = datetime.now()
        current_month = f"{today.year}년{today.month}월"
        
        if current_month not in months:
            months.insert(0, current_month)
        
        return jsonify({
            'success': True,
            'sheets': months,
            'message': f'{len(months)}개의 월별 데이터를 찾았습니다.'
        })
        
    except Exception as e:
        print(f"❌ 시트 목록 조회 오류: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'sheets': [],
            'message': f'시트 목록 조회 중 오류: {str(e)}'
        }), 500



