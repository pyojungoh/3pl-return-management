"""
3PL 반품 관리 및 화주사 관리 시스템 서버
버전: v2.0 (외부 서버 - 속도 개선)
"""
from flask import Flask, render_template, send_from_directory, send_file
from flask_cors import CORS
import os

# Flask 앱 생성
app = Flask(__name__, 
            static_folder='static',
            template_folder='templates')
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'your-secret-key-change-this-in-production')
app.config['JSON_AS_ASCII'] = False  # 한글 지원

# CORS 설정 (모든 도메인 허용)
CORS(app, resources={r"/api/*": {"origins": "*"}})

# API 블루프린트 등록
from api.auth.routes import auth_bp
from api.returns.routes import returns_bp
from api.return_sheets.routes import return_sheets_bp

app.register_blueprint(auth_bp)
app.register_blueprint(returns_bp)
app.register_blueprint(return_sheets_bp)


# 메인 페이지 라우트 (화주사 대시보드)
@app.route('/')
def index():
    """화주사 대시보드 (로그인 포함)"""
    try:
        return send_file('dashboard_server.html')
    except:
        # 파일이 없으면 dashboard.html 사용
        try:
            return send_file('dashboard.html')
        except:
            return '<h1>대시보드 파일을 찾을 수 없습니다.</h1>', 404


@app.route('/dashboard')
def dashboard():
    """대시보드 페이지"""
    return index()


@app.route('/admin')
def admin():
    """관리자 페이지"""
    return render_template('index.html')


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
    return {'error': '페이지를 찾을 수 없습니다.'}, 404


@app.errorhandler(500)
def internal_error(error):
    return {'error': '서버 오류가 발생했습니다.'}, 500


if __name__ == '__main__':
    # 개발 서버 실행
    port = int(os.environ.get('PORT', 5000))
    app.run(
        host='0.0.0.0',
        port=port,
        debug=True
    )



