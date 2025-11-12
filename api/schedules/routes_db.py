"""
판매 스케쥴 관리 API 라우트
"""
from flask import Blueprint, request, jsonify
from datetime import datetime, timedelta
from api.database.models import (
    create_schedule,
    get_schedules_by_company,
    get_all_schedules,
    get_schedules_by_date_range,
    get_schedule_by_id,
    update_schedule,
    delete_schedule
)

# Blueprint 생성
schedules_bp = Blueprint('schedules', __name__, url_prefix='/api/schedules')


@schedules_bp.route('/list', methods=['GET'])
def get_schedules_list():
    """
    스케쥴 목록 조회 API
    
    Query Parameters:
        - company: 화주사명 (화주사 모드일 때 필수)
        - role: 권한 ("관리자" 또는 "화주사")
    
    Returns:
        {
            "success": bool,
            "data": List[Dict],
            "count": int,
            "message": str
        }
    """
    try:
        company = request.args.get('company', '').strip()
        role = request.args.get('role', '화주사').strip()
        
        # 화주사인 경우 자신의 스케쥴만 조회
        if role != '관리자':
            if not company:
                return jsonify({
                    'success': False,
                    'data': [],
                    'count': 0,
                    'message': '화주사명이 필요합니다.'
                }), 400
            schedules = get_schedules_by_company(company)
        else:
            # 관리자는 전체 스케쥴 조회
            schedules = get_all_schedules()
        
        return jsonify({
            'success': True,
            'data': schedules,
            'count': len(schedules),
            'message': f'{len(schedules)}개의 스케쥴을 찾았습니다.'
        })
    except Exception as e:
        print(f'❌ 스케쥴 목록 조회 오류: {e}')
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'data': [],
            'count': 0,
            'message': f'스케쥴 목록 조회 중 오류: {str(e)}'
        }), 500


@schedules_bp.route('/calendar', methods=['GET'])
def get_calendar_schedules():
    """
    달력용 스케쥴 조회 API (관리자용)
    
    Query Parameters:
        - startDate: 시작 날짜 (YYYY-MM-DD)
        - endDate: 종료 날짜 (YYYY-MM-DD)
        - month: 월 (예: "2025-11") - 선택사항, 없으면 현재 월
    
    Returns:
        {
            "success": bool,
            "data": List[Dict],
            "message": str
        }
    """
    try:
        start_date = request.args.get('startDate', '').strip()
        end_date = request.args.get('endDate', '').strip()
        month = request.args.get('month', '').strip()
        
        # 월이 제공된 경우 해당 월의 시작일과 종료일 계산
        if month and not start_date and not end_date:
            try:
                year, month_num = month.split('-')
                year = int(year)
                month_num = int(month_num)
                # 해당 월의 첫날과 마지막날
                start_date = f"{year}-{month_num:02d}-01"
                if month_num == 12:
                    end_date = f"{year + 1}-01-01"
                else:
                    end_date = f"{year}-{month_num + 1:02d}-01"
            except:
                # 파싱 실패 시 현재 월 사용
                today = datetime.now()
                start_date = today.replace(day=1).strftime('%Y-%m-%d')
                if today.month == 12:
                    end_date = today.replace(year=today.year + 1, month=1, day=1).strftime('%Y-%m-%d')
                else:
                    end_date = today.replace(month=today.month + 1, day=1).strftime('%Y-%m-%d')
        
        # 날짜가 없으면 현재 월 사용
        if not start_date or not end_date:
            today = datetime.now()
            start_date = today.replace(day=1).strftime('%Y-%m-%d')
            if today.month == 12:
                end_date = today.replace(year=today.year + 1, month=1, day=1).strftime('%Y-%m-%d')
            else:
                end_date = today.replace(month=today.month + 1, day=1).strftime('%Y-%m-%d')
        
        schedules = get_schedules_by_date_range(start_date, end_date)
        
        return jsonify({
            'success': True,
            'data': schedules,
            'count': len(schedules),
            'startDate': start_date,
            'endDate': end_date,
            'message': f'{len(schedules)}개의 스케쥴을 찾았습니다.'
        })
    except Exception as e:
        print(f'❌ 달력 스케쥴 조회 오류: {e}')
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'data': [],
            'count': 0,
            'message': f'달력 스케쥴 조회 중 오류: {str(e)}'
        }), 500


@schedules_bp.route('/create', methods=['POST'])
def create_schedule_route():
    """
    스케쥴 생성 API
    
    Request Body:
        {
            "company_name": str,
            "title": str,
            "start_date": str (YYYY-MM-DD),
            "end_date": str (YYYY-MM-DD),
            "event_description": str,
            "request_note": str (선택사항)
        }
    """
    try:
        data = request.get_json()
        
        # 필수 필드 확인
        if not data.get('company_name') or not data.get('title') or not data.get('start_date') or not data.get('end_date'):
            return jsonify({
                'success': False,
                'message': '화주사명, 제목, 시작일, 종료일은 필수입니다.'
            }), 400
        
        # 날짜 유효성 검사
        try:
            start_date = datetime.strptime(data.get('start_date'), '%Y-%m-%d')
            end_date = datetime.strptime(data.get('end_date'), '%Y-%m-%d')
            if end_date < start_date:
                return jsonify({
                    'success': False,
                    'message': '종료일은 시작일보다 늦어야 합니다.'
                }), 400
        except ValueError:
            return jsonify({
                'success': False,
                'message': '날짜 형식이 올바르지 않습니다. (YYYY-MM-DD 형식)'
            }), 400
        
        schedule_id = create_schedule(data)
        if schedule_id:
            return jsonify({
                'success': True,
                'message': '스케쥴이 등록되었습니다.',
                'id': schedule_id
            })
        else:
            return jsonify({
                'success': False,
                'message': '스케쥴 등록에 실패했습니다.'
            }), 500
        
    except Exception as e:
        print(f'❌ 스케쥴 등록 오류: {e}')
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'message': f'스케쥴 등록 중 오류: {str(e)}'
        }), 500


@schedules_bp.route('/update/<int:schedule_id>', methods=['PUT'])
def update_schedule_route(schedule_id):
    """
    스케쥴 수정 API
    """
    try:
        data = request.get_json()
        
        # 날짜 유효성 검사
        if data.get('start_date') and data.get('end_date'):
            try:
                start_date = datetime.strptime(data.get('start_date'), '%Y-%m-%d')
                end_date = datetime.strptime(data.get('end_date'), '%Y-%m-%d')
                if end_date < start_date:
                    return jsonify({
                        'success': False,
                        'message': '종료일은 시작일보다 늦어야 합니다.'
                    }), 400
            except ValueError:
                return jsonify({
                    'success': False,
                    'message': '날짜 형식이 올바르지 않습니다. (YYYY-MM-DD 형식)'
                }), 400
        
        success = update_schedule(schedule_id, data)
        if success:
            return jsonify({
                'success': True,
                'message': '스케쥴이 수정되었습니다.'
            })
        else:
            return jsonify({
                'success': False,
                'message': '스케쥴 수정에 실패했습니다.'
            }), 500
        
    except Exception as e:
        print(f'❌ 스케쥴 수정 오류: {e}')
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'message': f'스케쥴 수정 중 오류: {str(e)}'
        }), 500


@schedules_bp.route('/delete/<int:schedule_id>', methods=['DELETE'])
def delete_schedule_route(schedule_id):
    """
    스케쥴 삭제 API
    """
    try:
        success = delete_schedule(schedule_id)
        if success:
            return jsonify({
                'success': True,
                'message': '스케쥴이 삭제되었습니다.'
            })
        else:
            return jsonify({
                'success': False,
                'message': '스케쥴 삭제에 실패했습니다.'
            }), 500
        
    except Exception as e:
        print(f'❌ 스케쥴 삭제 오류: {e}')
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'message': f'스케쥴 삭제 중 오류: {str(e)}'
        }), 500


@schedules_bp.route('/<int:schedule_id>', methods=['GET'])
def get_schedule_detail(schedule_id):
    """
    스케쥴 상세 조회 API
    """
    try:
        schedule = get_schedule_by_id(schedule_id)
        if schedule:
            return jsonify({
                'success': True,
                'data': schedule,
                'message': '스케쥴을 찾았습니다.'
            })
        else:
            return jsonify({
                'success': False,
                'data': None,
                'message': '스케쥴을 찾을 수 없습니다.'
            }), 404
        
    except Exception as e:
        print(f'❌ 스케쥴 조회 오류: {e}')
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'data': None,
            'message': f'스케쥴 조회 중 오류: {str(e)}'
        }), 500

