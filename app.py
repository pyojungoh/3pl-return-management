"""
3PL 반품 관리 및 화주사 관리 시스템 서버
버전: v4.0 (PostgreSQL/Neon 데이터베이스 기반)
"""
from flask import Flask, render_template, send_from_directory, send_file, request, jsonify
from flask_cors import CORS
import os
from dotenv import load_dotenv

# 환경 변수 로드 (.env 파일) - 에러 발생 시 무시 (코드에 직접 설정된 값 사용)
# Flask의 자동 dotenv 로드도 비활성화하기 위해 환경 변수 설정
os.environ['FLASK_SKIP_DOTENV'] = '1'

# Flask의 자동 dotenv 로드 완전히 비활성화
import flask.cli
_original_load_dotenv = flask.cli.load_dotenv
def _noop_load_dotenv():
    """dotenv 로드를 비활성화하는 빈 함수"""
    pass
flask.cli.load_dotenv = _noop_load_dotenv

try:
    load_dotenv()
except Exception as e:
    print(f"[경고] .env 파일 로드 중 오류 발생 (무시하고 계속 진행): {e}")
    print("   환경 변수는 Vercel 설정 또는 .env 파일에서 로드됩니다.")

# Flask 앱 생성
app = Flask(__name__, 
            static_folder='static',
            template_folder='templates')
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'your-secret-key-change-this-in-production')
app.config['JSON_AS_ASCII'] = False  # 한글 지원

# CORS 설정 (모든 도메인 허용)
CORS(app, resources={r"/api/*": {"origins": "*"}})

# 데이터베이스 초기화
from api.database.models import init_db, get_company_by_username, create_company, fix_missing_return_ids

# NOTE:
# - Vercel(Serverless)에서는 import 시점에 예외가 발생하면 함수 자체가 크래시하여 사이트 접속이 불가해집니다.
# - DB(Neon) 과금/쿼터/네트워크 이슈 등으로 연결이 실패하더라도, 최소한 HTML은 서빙되도록 부팅을 계속합니다.
# - init_db()는 lazy loading으로 변경하여 첫 요청 시에만 실행되도록 합니다 (타임아웃 방지).
DB_READY = False
_db_initialized = False

def ensure_db_ready():
    """DB가 준비되었는지 확인하고, 필요시 초기화 (lazy loading)"""
    global DB_READY, _db_initialized
    
    if _db_initialized:
        return DB_READY
    
    _db_initialized = True
    DB_READY = True
    
    try:
        init_db()
        print("[성공] DB 초기화 완료")
    except Exception as e:
        DB_READY = False
        print(f"[오류] DB 초기화 실패 (부팅은 계속 진행): {e}")
        import traceback
        traceback.print_exc()
    
    # 기존 반품 데이터에 ID가 없는 경우 ID 생성
    if DB_READY:
        try:
            fix_missing_return_ids()
        except Exception as e:
            print(f"[경고] 반품 ID 생성 중 오류 발생 (무시하고 계속 진행): {e}")
    
    # 초기 관리자 계정 자동 생성 (없는 경우에만)
    if DB_READY:
        try:
            admin_user = get_company_by_username('admin')
            if not admin_user:
                print("[정보] 초기 관리자 계정이 없습니다. 생성 중...")
                create_company(
                    company_name='관리자',
                    username='admin',
                    password='admin123',  # [주의] 배포 후 비밀번호 변경 권장
                    role='관리자'
                )
                print("[성공] 초기 관리자 계정이 생성되었습니다.")
                print("   아이디: admin")
                print("   비밀번호: admin123")
                print("   [주의] 보안을 위해 배포 후 비밀번호를 변경하세요!")
            else:
                print("[성공] 관리자 계정이 이미 존재합니다.")
        except Exception as e:
            print(f"[경고] 초기 관리자 계정 생성 중 오류 (무시 가능): {e}")
    
    return DB_READY

# 기존 반품 데이터에 ID가 없는 경우 ID 생성
if DB_READY:
    try:
        fix_missing_return_ids()
    except Exception as e:
        print(f"[경고] 반품 ID 생성 중 오류 발생 (무시하고 계속 진행): {e}")

# 초기 관리자 계정 자동 생성 (없는 경우에만)
if DB_READY:
    try:
        admin_user = get_company_by_username('admin')
        if not admin_user:
            print("[정보] 초기 관리자 계정이 없습니다. 생성 중...")
            create_company(
                company_name='관리자',
                username='admin',
                password='admin123',  # [주의] 배포 후 비밀번호 변경 권장
                role='관리자'
            )
            print("[성공] 초기 관리자 계정이 생성되었습니다.")
            print("   아이디: admin")
            print("   비밀번호: admin123")
            print("   [주의] 보안을 위해 배포 후 비밀번호를 변경하세요!")
        else:
            print("[성공] 관리자 계정이 이미 존재합니다.")
    except Exception as e:
        print(f"[경고] 초기 관리자 계정 생성 중 오류 (무시 가능): {e}")

# API 블루프린트 등록 (데이터베이스 기반)
from api.auth.routes_db import auth_bp
from api.returns.routes_db import returns_bp
from api.return_sheets.routes_db import return_sheets_bp
from api.uploads.routes import uploads_bp
from api.admin.routes import admin_bp
from api.schedules.routes_db import schedules_bp
from api.board.routes_db import board_bp
from api.popups.routes_db import popups_bp
from api.header_banners.routes_db import header_banners_bp
from api.cs.routes_db import cs_bp
from api.cs.scheduler import start_cs_notification_scheduler
from api.special_works.routes_db import special_works_bp
from api.schedule_notifications.scheduler import start_schedule_notification_scheduler
from api.schedule_notifications.routes import schedule_notifications_bp
from api.pallets.routes import pallets_bp

app.register_blueprint(auth_bp)
app.register_blueprint(returns_bp)
app.register_blueprint(return_sheets_bp)
app.register_blueprint(uploads_bp)
app.register_blueprint(admin_bp)
app.register_blueprint(schedules_bp)
app.register_blueprint(board_bp)
app.register_blueprint(popups_bp)
app.register_blueprint(header_banners_bp)
print("[앱 시작] 헤더 배너 Blueprint 등록 완료")
app.register_blueprint(cs_bp)
app.register_blueprint(special_works_bp)
app.register_blueprint(schedule_notifications_bp)
app.register_blueprint(pallets_bp)
print("[앱 시작] 파레트 보관료 관리 시스템 Blueprint 등록 완료")

# C/S 알림 스케줄러 시작
print("[정보] [앱 시작] C/S 알림 스케줄러 시작 시도...")
print("[정보] [앱 시작] 배포 시간: 2025-11-17 15:30") # Force Vercel deployment trigger
try:
    # DB가 준비되지 않은 경우(예: Neon 쿼터 초과), 서버리스 부팅 안정성을 위해 스케줄러는 시작하지 않습니다.
    if DB_READY:
        start_cs_notification_scheduler()
        print("[성공] [앱 시작] C/S 알림 스케줄러 시작 완료")
    else:
        print("[경고] [앱 시작] DB 미가용 상태로 스케줄러 시작 스킵")
except Exception as e:
    print(f"[오류] [앱 시작] C/S 알림 스케줄러 시작 중 오류: {e}")
    import traceback
    traceback.print_exc()

# 스케쥴 알림 스케줄러 시작
print("[정보] [앱 시작] 스케쥴 알림 스케줄러 시작 시도...")
try:
    if DB_READY:
        start_schedule_notification_scheduler()
        print("[성공] [앱 시작] 스케쥴 알림 스케줄러 시작 완료")
    else:
        print("[경고] [앱 시작] DB 미가용 상태로 스케줄러 시작 스킵")
except Exception as e:
    print(f"[오류] [앱 시작] 스케쥴 알림 스케줄러 시작 중 오류: {e}")
    import traceback
    traceback.print_exc()


@app.route('/api/health', methods=['GET'])
def health():
    """헬스체크 (서버리스 부팅/DB 상태 확인용)"""
    return jsonify({
        'success': True,
        'db_ready': DB_READY
    })


# 메인 페이지 라우트 (화주사 대시보드)
@app.route('/')
def index():
    """화주사 대시보드 (로그인 포함)"""
    try:
        # DB 초기화는 백그라운드에서 처리 (타임아웃 방지)
        # 첫 요청 시에만 초기화 시도
        if not _db_initialized:
            try:
                ensure_db_ready()
            except Exception:
                pass  # DB 초기화 실패해도 HTML은 서빙
        
        # dashboard_server.html 파일 사용
        return send_file('dashboard_server.html')
    except FileNotFoundError:
        return '<h1>대시보드 파일을 찾을 수 없습니다.</h1><p>dashboard_server.html 파일이 필요합니다.</p>', 404
    except Exception as e:
        return f'<h1>오류 발생</h1><p>{str(e)}</p>', 500


@app.route('/special_works.html')
def special_works():
    """특수작업 관리 페이지"""
    try:
        # special_works.html 파일 직접 제공
        return send_file('special_works.html')
    except FileNotFoundError:
        return '<h1>특수작업 페이지 파일을 찾을 수 없습니다.</h1><p>special_works.html 파일이 필요합니다.</p>', 404
    except Exception as e:
        return f'<h1>오류 발생</h1><p>{str(e)}</p>', 500


@app.route('/pallets.html')
def pallets():
    """파레트 보관료 관리 페이지"""
    try:
        # pallets.html 파일 직접 제공
        return send_file('pallets.html')
    except FileNotFoundError:
        return '<h1>파레트 관리 페이지 파일을 찾을 수 없습니다.</h1><p>pallets.html 파일이 필요합니다.</p>', 404
    except Exception as e:
        return f'<h1>오류 발생</h1><p>{str(e)}</p>', 500


@app.route('/dashboard')
def dashboard():
    """대시보드 페이지"""
    return index()


@app.route('/qrmobile')
def qrmobile():
    """모바일 QR 코드 사진 입력 페이지"""
    try:
        # index.html 파일 직접 제공
        return send_file('index.html')
    except FileNotFoundError:
        return '<h1>모바일 페이지 파일을 찾을 수 없습니다.</h1><p>index.html 파일이 필요합니다.</p>', 404
    except Exception as e:
        return f'<h1>오류 발생</h1><p>{str(e)}</p>', 500

@app.route('/index.html')
def index_html():
    """모바일 페이지 (index.html 직접 접근)"""
    return qrmobile()

@app.route('/admin')
def admin():
    """관리자 페이지 (모바일 QR 코드 사진 입력 페이지) - 레거시 경로"""
    return qrmobile()

@app.route('/qr-photo')
def qr_photo():
    """QR 자동 스캔 및 사진 촬영 페이지 (모듈화)"""
    try:
        # qr_photo_return.html 파일 직접 제공
        return send_file('qr_photo_return.html')
    except FileNotFoundError:
        return '<h1>QR 사진 페이지 파일을 찾을 수 없습니다.</h1><p>qr_photo_return.html 파일이 필요합니다.</p>', 404
    except Exception as e:
        return f'<h1>오류 발생</h1><p>{str(e)}</p>', 500


# 정적 파일 제공
@app.route('/static/<path:filename>')
def serve_static(filename):
    """정적 파일 제공"""
    static_dir = os.path.join(os.path.dirname(__file__), 'static')
    if os.path.exists(static_dir):
        return send_from_directory('static', filename)
    return {'error': '파일을 찾을 수 없습니다.'}, 404


# 에러 핸들러
@app.errorhandler(404)
def not_found(error):
    print(f"[오류] 404 에러 발생: {request.url}")
    print(f"   요청 경로: {request.path}")
    print(f"   요청 메서드: {request.method}")
    # API 요청인 경우 더 자세한 정보 제공
    if request.path.startswith('/api/'):
        return jsonify({
            'error': 'API 엔드포인트를 찾을 수 없습니다.',
            'path': request.path,
            'method': request.method
        }), 404
    return {'error': '페이지를 찾을 수 없습니다.'}, 404


@app.errorhandler(500)
def internal_error(error):
    return {'error': '서버 오류가 발생했습니다.'}, 500


if __name__ == '__main__':
    # 개발 서버 실행
    # Flask의 자동 dotenv 로드는 이미 위에서 비활성화됨
    port = int(os.environ.get('PORT', 5000))
    app.run(
        host='0.0.0.0',
        port=port,
        debug=True
    )

