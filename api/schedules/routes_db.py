"""
판매 스케쥴 관리 API 라우트
"""
from flask import Blueprint, request, jsonify
from datetime import datetime, timedelta, timezone
from api.database.models import (
    create_schedule,
    get_schedules_by_company,
    get_all_schedules,
    get_schedules_by_date_range,
    get_schedule_by_id,
    update_schedule,
    delete_schedule,
    get_all_companies,
    create_schedule_type,
    get_all_schedule_types,
    delete_schedule_type
)
from api.schedule_notifications.telegram import send_schedule_notification
from api.database.models import get_db_connection, USE_POSTGRESQL
from urllib.parse import unquote

if USE_POSTGRESQL:
    from psycopg2.extras import RealDictCursor

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
        company_name = data.get('company_name', '').strip()
        if not company_name or not data.get('title') or not data.get('start_date') or not data.get('end_date'):
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
        
        # "모든 화주사" 선택 시 모든 화주사에게 스케줄 생성 (company_name은 "제이제이"로 저장)
        if company_name == '모든 화주사' or company_name == 'ALL':
            companies = get_all_companies(include_inactive=False)
            # 관리자 계정 제외
            companies = [c for c in companies if c.get('role') != '관리자']
            
            if not companies:
                return jsonify({
                    'success': False,
                    'message': '등록된 화주사가 없습니다.'
                }), 400
            
            created_count = 0
            failed_count = 0
            schedule_ids = []
            
            # 사용자가 선택한 schedule_type을 유지
            user_schedule_type = data.get('schedule_type', '').strip()
            if not user_schedule_type:
                user_schedule_type = '모든화주사'
            
            # 모든 화주사에게 스케줄 생성 (각 화주사의 실제 company_name으로 저장)
            for company in companies:
                company_data = data.copy()
                company_data['company_name'] = company.get('company_name')  # 각 화주사의 실제 이름으로 저장
                # schedule_type 앞에 "모든화주사-" 접두사 추가하여 "모든화주사" 타입임을 표시
                # 예: "모든화주사-입고", "모든화주사-출고" 등
                if user_schedule_type != '모든화주사':
                    company_data['schedule_type'] = f'모든화주사-{user_schedule_type}'
                else:
                    company_data['schedule_type'] = '모든화주사'
                schedule_id = create_schedule(company_data)
                if schedule_id:
                    created_count += 1
                    schedule_ids.append(schedule_id)
                else:
                    failed_count += 1
            
            if created_count > 0:
                # "모든 화주사" 스케쥴 등록 알림 (첫 번째 스케쥴 정보 사용)
                if schedule_ids:
                    try:
                        first_schedule = get_schedule_by_id(schedule_ids[0])
                        if first_schedule:
                            kst = timezone(timedelta(hours=9))
                            current_time_kst = datetime.now(kst).strftime('%Y-%m-%d %H:%M:%S')
                            
                            schedule_type = first_schedule.get('schedule_type', '')
                            if schedule_type.startswith('모든화주사-'):
                                schedule_type = schedule_type.replace('모든화주사-', '')
                            
                            message = f"📅 <b>새로운 스케쥴 등록 (모든 화주사)</b>\n\n"
                            message += f"🏢 화주사: 모든 화주사 ({created_count}개)\n"
                            if schedule_type:
                                message += f"📋 타입: {schedule_type}\n"
                            message += f"📝 제목: {first_schedule.get('title', '')}\n"
                            message += f"📅 기간: {first_schedule.get('start_date', '')} ~ {first_schedule.get('end_date', '')}\n"
                            if first_schedule.get('event_description'):
                                message += f"📄 내용: {first_schedule.get('event_description', '')[:200]}{'...' if len(first_schedule.get('event_description', '')) > 200 else ''}\n"
                            if first_schedule.get('request_note'):
                                message += f"💬 요청사항: {first_schedule.get('request_note', '')[:100]}{'...' if len(first_schedule.get('request_note', '')) > 100 else ''}\n"
                            message += f"\n등록 시간: {current_time_kst}"
                            
                            print(f"📝 [스케쥴 등록] 텔레그램 메시지 전송 시도")
                            send_schedule_notification(message)
                    except Exception as e:
                        print(f"⚠️ [스케쥴 등록] 텔레그램 알림 전송 중 오류 (무시): {e}")
                
                return jsonify({
                    'success': True,
                    'message': f'{created_count}개 화주사에게 스케쥴이 등록되었습니다.',
                    'count': created_count,
                    'failed': failed_count,
                    'ids': schedule_ids
                })
            else:
                return jsonify({
                    'success': False,
                    'message': '스케쥴 등록에 실패했습니다.'
                }), 500
        else:
            # 단일 화주사 스케줄 생성
            schedule_id = create_schedule(data)
            if schedule_id:
                # 스케쥴 등록 즉시 알림 전송
                try:
                    schedule = get_schedule_by_id(schedule_id)
                    if schedule:
                        kst = timezone(timedelta(hours=9))
                        current_time_kst = datetime.now(kst).strftime('%Y-%m-%d %H:%M:%S')
                        
                        company_name = schedule.get('company_name', '알 수 없음')
                        schedule_type = schedule.get('schedule_type', '')
                        title = schedule.get('title', '')
                        start_date = schedule.get('start_date', '')
                        end_date = schedule.get('end_date', '')
                        event_description = schedule.get('event_description', '')
                        request_note = schedule.get('request_note', '')
                        
                        message = f"📅 <b>새로운 스케쥴 등록</b>\n\n"
                        message += f"🏢 화주사: {company_name}\n"
                        if schedule_type:
                            message += f"📋 타입: {schedule_type}\n"
                        message += f"📝 제목: {title}\n"
                        message += f"📅 기간: {start_date} ~ {end_date}\n"
                        if event_description:
                            message += f"📄 내용: {event_description[:200]}{'...' if len(event_description) > 200 else ''}\n"
                        if request_note:
                            message += f"💬 요청사항: {request_note[:100]}{'...' if len(request_note) > 100 else ''}\n"
                        message += f"\n등록 시간: {current_time_kst}"
                        
                        print(f"📝 [스케쥴 등록] 텔레그램 메시지 전송 시도")
                        send_schedule_notification(message)
                        
                        # 알림 전송 플래그 업데이트
                        try:
                            conn = get_db_connection()
                            cursor = conn.cursor()
                            if USE_POSTGRESQL:
                                cursor.execute('UPDATE schedules SET notification_sent_registered = TRUE WHERE id = %s', (schedule_id,))
                            else:
                                cursor.execute('UPDATE schedules SET notification_sent_registered = 1 WHERE id = ?', (schedule_id,))
                            conn.commit()
                            cursor.close()
                            conn.close()
                        except Exception as e:
                            print(f"⚠️ [스케쥴 등록] 알림 플래그 업데이트 중 오류 (무시): {e}")
                except Exception as e:
                    print(f"⚠️ [스케쥴 등록] 텔레그램 알림 전송 중 오류 (무시): {e}")
                
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
    
    Query Parameters:
        - role: 권한 ("관리자" 또는 "화주사")
        - company: 화주사명 (화주사 모드일 때 필수)
    """
    try:
        # 권한과 화주사명 확인
        role = request.args.get('role', '관리자').strip()
        company_name = request.args.get('company', '').strip()
        
        print(f'🔍 삭제 요청: schedule_id={schedule_id}, role={role}, company={company_name}')
        
        # 화주사 모드인 경우 company_name 필수
        if role != '관리자' and not company_name:
            return jsonify({
                'success': False,
                'message': '화주사명이 필요합니다.'
            }), 400
        
        success = delete_schedule(schedule_id, role=role, company_name=company_name)
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


# ========== 스케줄 타입 관리 API ==========

@schedules_bp.route('/types', methods=['GET'])
def get_schedule_types():
    """스케줄 타입 목록 조회"""
    try:
        types = get_all_schedule_types()
        return jsonify({
            'success': True,
            'data': types,
            'count': len(types)
        })
    except Exception as e:
        print(f'❌ 스케줄 타입 조회 오류: {e}')
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'data': [],
            'count': 0,
            'message': f'스케줄 타입 조회 중 오류: {str(e)}'
        }), 500


@schedules_bp.route('/types', methods=['POST'])
def create_schedule_type_route():
    """스케줄 타입 생성"""
    try:
        data = request.get_json()
        print(f'📝 [스케줄 타입 생성 요청] 받은 데이터: {data}')
        
        if not data:
            print('❌ [스케줄 타입 생성] 요청 데이터가 없습니다.')
            return jsonify({
                'success': False,
                'message': '요청 데이터가 없습니다.'
            }), 400
        
        name = data.get('name', '').strip()
        display_order = data.get('display_order', 0)
        
        print(f'📝 [스케줄 타입 생성] 타입명: "{name}", display_order: {display_order}')
        
        if not name:
            print('❌ [스케줄 타입 생성] 타입명이 비어있습니다.')
            return jsonify({
                'success': False,
                'message': '스케줄 타입명은 필수입니다.'
            }), 400
        
        # 중복 체크를 먼저 수행 (명확한 에러 메시지를 위해)
        from api.database.models import get_all_schedule_types
        existing_types = get_all_schedule_types()
        normalized_input = name.strip().lower()
        
        print(f'📝 [스케줄 타입 생성] 기존 타입 개수: {len(existing_types)}')
        print(f'📝 [스케줄 타입 생성] 기존 타입 목록: {[t.get("name") for t in existing_types]}')
        print(f'📝 [스케줄 타입 생성] 입력 타입 (정규화): "{normalized_input}"')
        
        for existing_type in existing_types:
            existing_name = existing_type.get('name', '').strip().lower()
            print(f'📝 [스케줄 타입 생성] 비교: "{normalized_input}" vs "{existing_name}"')
            if existing_name == normalized_input:
                print(f'❌ [스케줄 타입 생성] 중복 발견: "{name}" == "{existing_type.get("name")}"')
                return jsonify({
                    'success': False,
                    'message': f'이미 존재하는 스케줄 타입입니다: "{name}"'
                }), 400
        
        print(f'✅ [스케줄 타입 생성] 중복 없음, 생성 시도: "{name}"')
        
        # create_schedule_type 함수 내부에서도 중복 체크를 수행하지만, 여기서 먼저 체크
        type_id, error_message = create_schedule_type(name, display_order)
        print(f'📝 [스케줄 타입 생성] create_schedule_type 결과: id={type_id}, error={error_message}')
        
        if type_id:
            print(f'✅ [스케줄 타입 생성] 성공: id={type_id}, name="{name}"')
            return jsonify({
                'success': True,
                'message': '스케줄 타입이 생성되었습니다.',
                'id': type_id
            })
        else:
            # create_schedule_type이 실패한 경우 (중복 체크는 이미 했으므로 다른 오류)
            error_detail = error_message or '알 수 없는 오류'
            print(f'❌ [스케줄 타입 생성] 실패: type_id={type_id}, name="{name}"')
            return jsonify({
                'success': False,
                'message': f'스케줄 타입 생성에 실패했습니다. (타입명: "{name}", 오류: {error_detail})'
            }), 400
    except Exception as e:
        print(f'❌ 스케줄 타입 생성 오류: {e}')
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'message': f'스케줄 타입 생성 중 오류: {str(e)}'
        }), 500


@schedules_bp.route('/types/<int:type_id>', methods=['DELETE'])
def delete_schedule_type_route(type_id):
    """스케줄 타입 삭제"""
    try:
        success = delete_schedule_type(type_id)
        if success:
            return jsonify({
                'success': True,
                'message': '스케줄 타입이 삭제되었습니다.'
            })
        else:
            return jsonify({
                'success': False,
                'message': '스케줄 타입 삭제에 실패했습니다.'
            }), 404
    except Exception as e:
        print(f'❌ 스케줄 타입 삭제 오류: {e}')
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'message': f'스케줄 타입 삭제 중 오류: {str(e)}'
        }), 500


# ========== 스케줄 메모 관리 API (관리자 전용) ==========

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


@schedules_bp.route('/admin-memo', methods=['GET'])
def get_schedule_memos():
    """스케줄 메모 목록 조회 API (관리자 전용)"""
    try:
        user_context = get_user_context()
        role = user_context['role']
        
        # 관리자만 접근 가능
        if role != '관리자':
            return jsonify({
                'success': False,
                'data': [],
                'message': '관리자만 접근할 수 있습니다.'
            }), 403
        
        conn = get_db_connection()
        if USE_POSTGRESQL:
            cursor = conn.cursor(cursor_factory=RealDictCursor)
        else:
            cursor = conn.cursor()
        
        try:
            # 메모판: 처리완료 제외 (대기만 표시), 최신순
            if USE_POSTGRESQL:
                cursor.execute('''
                    SELECT id, title, company_name, content, status, updated_by, updated_at, created_at
                    FROM schedule_memos
                    WHERE COALESCE(status, '대기') != '처리완료'
                    ORDER BY updated_at DESC
                ''')
            else:
                cursor.execute('''
                    SELECT id, title, company_name, content, status, updated_by, updated_at, created_at
                    FROM schedule_memos
                    WHERE COALESCE(status, '대기') != '처리완료'
                    ORDER BY updated_at DESC
                ''')
            
            rows = cursor.fetchall()
            
            memos = []
            for row in rows:
                if USE_POSTGRESQL:
                    memo = dict(row)
                else:
                    # SQLite의 경우 - Row 객체는 dict처럼 사용 가능
                    if hasattr(row, 'keys'):
                        # Row 객체인 경우
                        memo = dict(row)
                    elif cursor.description:
                        # description이 있는 경우
                        memo = dict(zip([col[0] for col in cursor.description], row))
                    else:
                        # 수동 변환
                        memo = {
                            'id': row[0] if len(row) > 0 else None,
                            'title': row[1] if len(row) > 1 else '',
                            'company_name': row[2] if len(row) > 2 else None,
                            'content': row[3] if len(row) > 3 else '',
                            'status': row[4] if len(row) > 4 else '대기',
                            'updated_by': row[5] if len(row) > 5 else None,
                            'updated_at': row[6] if len(row) > 6 else None,
                            'created_at': row[7] if len(row) > 7 else None
                        }
                # datetime 객체를 문자열로 변환
                for key, value in memo.items():
                    if isinstance(value, datetime):
                        memo[key] = value.strftime('%Y-%m-%d %H:%M:%S') if value else None
                if 'status' not in memo or memo.get('status') is None:
                    memo['status'] = '대기'
                memos.append(memo)
            
            return jsonify({
                'success': True,
                'data': memos,
                'count': len(memos),
                'message': f'{len(memos)}개의 메모를 조회했습니다.'
            })
        finally:
            cursor.close()
            conn.close()
            
    except Exception as e:
        print(f'❌ 스케줄 메모 조회 오류: {e}')
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'data': [],
            'message': f'메모 조회 중 오류: {str(e)}'
        }), 500


@schedules_bp.route('/admin-memo/<int:memo_id>', methods=['GET'])
def get_schedule_memo_detail(memo_id):
    """스케줄 메모 상세 조회 API (관리자 전용)"""
    try:
        user_context = get_user_context()
        role = user_context['role']
        
        # 관리자만 접근 가능
        if role != '관리자':
            return jsonify({
                'success': False,
                'data': None,
                'message': '관리자만 접근할 수 있습니다.'
            }), 403
        
        conn = get_db_connection()
        if USE_POSTGRESQL:
            cursor = conn.cursor(cursor_factory=RealDictCursor)
        else:
            cursor = conn.cursor()
        
        try:
            if USE_POSTGRESQL:
                cursor.execute('''
                    SELECT id, title, company_name, content, status, updated_by, updated_at, created_at
                    FROM schedule_memos
                    WHERE id = %s
                ''', (memo_id,))
            else:
                cursor.execute('''
                    SELECT id, title, company_name, content, status, updated_by, updated_at, created_at
                    FROM schedule_memos
                    WHERE id = ?
                ''', (memo_id,))
            
            row = cursor.fetchone()
            
            if row:
                if USE_POSTGRESQL:
                    memo = dict(row)
                else:
                    if hasattr(row, 'keys'):
                        memo = dict(row)
                    elif cursor.description:
                        memo = dict(zip([col[0] for col in cursor.description], row))
                    else:
                        memo = {
                            'id': row[0] if len(row) > 0 else None,
                            'title': row[1] if len(row) > 1 else '',
                            'company_name': row[2] if len(row) > 2 else None,
                            'content': row[3] if len(row) > 3 else '',
                            'status': row[4] if len(row) > 4 else '대기',
                            'updated_by': row[5] if len(row) > 5 else None,
                            'updated_at': row[6] if len(row) > 6 else None,
                            'created_at': row[7] if len(row) > 7 else None
                        }
                if memo.get('status') is None:
                    memo['status'] = '대기'
                for key, value in memo.items():
                    if isinstance(value, datetime):
                        memo[key] = value.strftime('%Y-%m-%d %H:%M:%S') if value else None
                
                return jsonify({
                    'success': True,
                    'data': memo,
                    'message': '메모를 조회했습니다.'
                })
            else:
                return jsonify({
                    'success': False,
                    'data': None,
                    'message': '메모를 찾을 수 없습니다.'
                }), 404
        finally:
            cursor.close()
            conn.close()
            
    except Exception as e:
        print(f'❌ 스케줄 메모 상세 조회 오류: {e}')
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'data': None,
            'message': f'메모 조회 중 오류: {str(e)}'
        }), 500


@schedules_bp.route('/admin-memo', methods=['POST'])
def create_schedule_memo():
    """스케줄 메모 생성 API (관리자 전용)"""
    try:
        user_context = get_user_context()
        role = user_context['role']
        username = user_context['username']
        
        # 관리자만 접근 가능
        if role != '관리자':
            return jsonify({
                'success': False,
                'message': '관리자만 접근할 수 있습니다.'
            }), 403
        
        data = request.get_json()
        if not data:
            return jsonify({
                'success': False,
                'message': '요청 데이터가 없습니다.'
            }), 400
        
        title = data.get('title', '').strip()
        company_name = data.get('company_name', '').strip()
        content = data.get('content', '').strip()
        
        if not title or not content:
            return jsonify({
                'success': False,
                'message': '제목과 내용은 필수입니다.'
            }), 400
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        try:
            if USE_POSTGRESQL:
                cursor.execute('''
                    INSERT INTO schedule_memos (title, company_name, content, status, updated_by, created_at, updated_at)
                    VALUES (%s, %s, %s, '대기', %s, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                    RETURNING id
                ''', (title, company_name if company_name else None, content, username))
                memo_id = cursor.fetchone()[0]
            else:
                cursor.execute('''
                    INSERT INTO schedule_memos (title, company_name, content, status, updated_by, created_at, updated_at)
                    VALUES (?, ?, ?, '대기', ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                ''', (title, company_name if company_name else None, content, username))
                memo_id = cursor.lastrowid
            
            if USE_POSTGRESQL:
                cursor.execute('''
                    INSERT INTO schedule_memo_logs (memo_id, action, to_status, created_by)
                    VALUES (%s, 'created', '대기', %s)
                ''', (memo_id, username))
            else:
                cursor.execute('''
                    INSERT INTO schedule_memo_logs (memo_id, action, to_status, created_by)
                    VALUES (?, 'created', '대기', ?)
                ''', (memo_id, username))
            
            conn.commit()
            
            return jsonify({
                'success': True,
                'id': memo_id,
                'message': '메모가 생성되었습니다.'
            })
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            cursor.close()
            conn.close()
            
    except Exception as e:
        print(f'❌ 스케줄 메모 생성 오류: {e}')
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'message': f'메모 생성 중 오류: {str(e)}'
        }), 500


@schedules_bp.route('/admin-memo/<int:memo_id>', methods=['PUT'])
def update_schedule_memo(memo_id):
    """스케줄 메모 수정 API (관리자 전용)"""
    try:
        user_context = get_user_context()
        role = user_context['role']
        username = user_context['username']
        
        # 관리자만 접근 가능
        if role != '관리자':
            return jsonify({
                'success': False,
                'message': '관리자만 접근할 수 있습니다.'
            }), 403
        
        data = request.get_json()
        if not data:
            return jsonify({
                'success': False,
                'message': '요청 데이터가 없습니다.'
            }), 400
        
        title = data.get('title', '').strip()
        company_name = data.get('company_name', '').strip()
        content = data.get('content', '').strip()
        
        if not title or not content:
            return jsonify({
                'success': False,
                'message': '제목과 내용은 필수입니다.'
            }), 400
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        try:
            if USE_POSTGRESQL:
                cursor.execute('''
                    UPDATE schedule_memos
                    SET title = %s, company_name = %s, content = %s, updated_by = %s, updated_at = CURRENT_TIMESTAMP
                    WHERE id = %s
                ''', (title, company_name if company_name else None, content, username, memo_id))
            else:
                cursor.execute('''
                    UPDATE schedule_memos
                    SET title = ?, company_name = ?, content = ?, updated_by = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                ''', (title, company_name if company_name else None, content, username, memo_id))
            
            if cursor.rowcount == 0:
                return jsonify({
                    'success': False,
                    'message': '메모를 찾을 수 없습니다.'
                }), 404
            
            if USE_POSTGRESQL:
                cursor.execute('''
                    INSERT INTO schedule_memo_logs (memo_id, action, created_by)
                    VALUES (%s, 'updated', %s)
                ''', (memo_id, username))
            else:
                cursor.execute('''
                    INSERT INTO schedule_memo_logs (memo_id, action, created_by)
                    VALUES (?, 'updated', ?)
                ''', (memo_id, username))
            
            conn.commit()
            
            return jsonify({
                'success': True,
                'message': '메모가 수정되었습니다.'
            })
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            cursor.close()
            conn.close()
            
    except Exception as e:
        print(f'❌ 스케줄 메모 수정 오류: {e}')
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'message': f'메모 수정 중 오류: {str(e)}'
        }), 500


@schedules_bp.route('/admin-memo/<int:memo_id>/status', methods=['PATCH', 'PUT'])
def update_schedule_memo_status(memo_id):
    """스케줄 메모 진행상황 변경 API (관리자 전용)"""
    try:
        user_context = get_user_context()
        role = user_context['role']
        username = user_context['username']
        if role != '관리자':
            return jsonify({'success': False, 'message': '관리자만 접근할 수 있습니다.'}), 403
        
        data = request.get_json() or {}
        new_status = (data.get('status') or '').strip()
        if new_status not in ('대기', '처리완료'):
            return jsonify({'success': False, 'message': '진행상황은 대기, 처리완료 중 하나여야 합니다.'}), 400
        
        conn = get_db_connection()
        try:
            if USE_POSTGRESQL:
                cur = conn.cursor(cursor_factory=RealDictCursor)
                cur.execute('SELECT id, status FROM schedule_memos WHERE id = %s', (memo_id,))
            else:
                cur = conn.cursor()
                cur.execute('SELECT id, status FROM schedule_memos WHERE id = ?', (memo_id,))
            row = cur.fetchone()
            if not row:
                return jsonify({'success': False, 'message': '메모를 찾을 수 없습니다.'}), 404
            
            old_status = (row['status'] if USE_POSTGRESQL else row[1]) or '대기'
            if old_status == new_status:
                return jsonify({'success': True, 'message': '동일한 진행상황입니다.', 'status': new_status})
            
            if USE_POSTGRESQL:
                cur.execute(
                    "UPDATE schedule_memos SET status = %s, updated_by = %s, updated_at = CURRENT_TIMESTAMP WHERE id = %s",
                    (new_status, username, memo_id)
                )
                cur.execute(
                    "INSERT INTO schedule_memo_logs (memo_id, action, from_status, to_status, created_by) VALUES (%s, 'status_change', %s, %s, %s)",
                    (memo_id, old_status, new_status, username)
                )
            else:
                cur.execute(
                    "UPDATE schedule_memos SET status = ?, updated_by = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                    (new_status, username, memo_id)
                )
                cur.execute(
                    "INSERT INTO schedule_memo_logs (memo_id, action, from_status, to_status, created_by) VALUES (?, 'status_change', ?, ?, ?)",
                    (memo_id, old_status, new_status, username)
                )
            conn.commit()
            return jsonify({'success': True, 'message': '진행상황이 변경되었습니다.', 'status': new_status})
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            conn.close()
    except Exception as e:
        print(f'❌ 스케줄 메모 진행상황 변경 오류: {e}')
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'message': str(e)}), 500


@schedules_bp.route('/admin-memo-logs', methods=['GET'])
def get_schedule_memo_logs():
    """스케줄 메모 기록장 조회 API (관리자 전용). 메모당 1행, 현재 진행상황만 반환."""
    try:
        user_context = get_user_context()
        if user_context['role'] != '관리자':
            return jsonify({'success': False, 'data': [], 'message': '관리자만 접근할 수 있습니다.'}), 403
        
        limit = max(1, min(100, request.args.get('limit', type=int) or 50))
        
        conn = get_db_connection()
        try:
            if USE_POSTGRESQL:
                cur = conn.cursor(cursor_factory=RealDictCursor)
                cur.execute('''
                    SELECT id, title, company_name, content, status, updated_at, updated_by, created_at
                    FROM schedule_memos
                    ORDER BY COALESCE(updated_at, created_at) DESC
                    LIMIT %s
                ''', (limit,))
                rows = cur.fetchall()
                items = [dict(r) for r in rows]
            else:
                cur = conn.cursor()
                cur.execute('''
                    SELECT id, title, company_name, content, status, updated_at, updated_by, created_at
                    FROM schedule_memos
                    ORDER BY COALESCE(updated_at, created_at) DESC
                    LIMIT ?
                ''', (limit,))
                rows = cur.fetchall()
                desc = [c[0] for c in cur.description] if cur.description else []
                items = [dict(zip(desc, r)) for r in rows]
            
            for it in items:
                ts = it.get('updated_at') or it.get('created_at')
                if isinstance(ts, datetime):
                    it['display_at'] = ts.strftime('%Y-%m-%d %H:%M')
                elif ts:
                    it['display_at'] = str(ts).replace('T', ' ')[:16]
                else:
                    it['display_at'] = '-'
            
            return jsonify({'success': True, 'data': items, 'count': len(items)})
        finally:
            conn.close()
    except Exception as e:
        print(f'❌ 스케줄 메모 기록장 조회 오류: {e}')
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'data': [], 'message': str(e)}), 500


@schedules_bp.route('/admin-memo/<int:memo_id>', methods=['DELETE'])
def delete_schedule_memo(memo_id):
    """스케줄 메모 삭제 API (관리자 전용)"""
    try:
        user_context = get_user_context()
        role = user_context['role']
        
        # 관리자만 접근 가능
        if role != '관리자':
            return jsonify({
                'success': False,
                'message': '관리자만 접근할 수 있습니다.'
            }), 403
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        try:
            if USE_POSTGRESQL:
                cursor.execute('DELETE FROM schedule_memos WHERE id = %s', (memo_id,))
            else:
                cursor.execute('DELETE FROM schedule_memos WHERE id = ?', (memo_id,))
            
            if cursor.rowcount == 0:
                return jsonify({
                    'success': False,
                    'message': '메모를 찾을 수 없습니다.'
                }), 404
            
            conn.commit()
            
            return jsonify({
                'success': True,
                'message': '메모가 삭제되었습니다.'
            })
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            cursor.close()
            conn.close()
            
    except Exception as e:
        print(f'❌ 스케줄 메모 삭제 오류: {e}')
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'message': f'메모 삭제 중 오류: {str(e)}'
        }), 500

