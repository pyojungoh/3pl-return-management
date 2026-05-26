"""
Google Drive OAuth 웹 재연결 (관리자 — Vercel 환경 변수 수동 갱신 없이 DB에 토큰 저장)
"""
import json
import os
from urllib.parse import unquote, urlparse

from flask import Blueprint, jsonify, redirect, request, make_response
from google_auth_oauthlib.flow import Flow
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer

from api.uploads.oauth_drive import SCOPES, _client_credentials_from_env, get_credentials
from api.uploads.oauth_token_store import (
    get_stored_token_meta,
    load_stored_token_dict,
    save_stored_token_dict,
)

oauth_web_bp = Blueprint('oauth_web', __name__, url_prefix='/api/uploads/oauth')

_STATE_SALT = 'google-drive-oauth-web-v1'


def _serializer():
    secret = os.environ.get('SECRET_KEY', 'your-secret-key-change-this-in-production')
    return URLSafeTimedSerializer(secret, salt=_STATE_SALT)


def _is_admin_request() -> bool:
    role = unquote((request.headers.get('X-User-Role') or '')).strip()
    return role == '관리자'


def _redirect_base() -> str:
    explicit = (os.environ.get('GOOGLE_OAUTH_REDIRECT_BASE') or '').strip().rstrip('/')
    if explicit:
        return explicit
    host = (request.host_url or '').rstrip('/')
    if host.startswith('http://') and os.environ.get('VERCEL'):
        return 'https://www.jjaysolution.com'
    return host or 'https://www.jjaysolution.com'


def _callback_uri() -> str:
    """
    Google Cloud Console에 등록된 redirect URI와 100% 일치해야 함 (redirect_uri_mismatch 방지).
    우선순위: GOOGLE_OAUTH_REDIRECT_URI → credentials JSON redirect_uris(요청 host 매칭) → fallback
    """
    custom = (os.environ.get('GOOGLE_OAUTH_REDIRECT_URI') or '').strip()
    if custom:
        return custom

    try:
        raw = _load_credentials_config()
        uris = list((raw.get('web') or {}).get('redirect_uris') or [])
        host = (request.host or '').split(':')[0].lower()

        if host in ('localhost', '127.0.0.1'):
            for uri in uris:
                if 'localhost' in uri or '127.0.0.1' in uri:
                    return uri

        for uri in uris:
            parsed = urlparse(uri)
            if parsed.hostname and parsed.hostname.lower() == host:
                return uri

        if host.startswith('www.'):
            alt_host = host[4:]
        else:
            alt_host = f'www.{host}'
        for uri in uris:
            parsed = urlparse(uri)
            if parsed.hostname and parsed.hostname.lower() == alt_host:
                return uri

        for uri in uris:
            if uri.startswith('https://') and 'localhost' not in uri:
                return uri
        if uris:
            return uris[0]
    except Exception:
        pass

    return f'{_redirect_base()}/api/uploads/oauth/callback'


def _load_credentials_config():
    raw_json = os.environ.get('GOOGLE_OAUTH_CREDENTIALS_JSON')
    if not raw_json:
        raise ValueError(
            'GOOGLE_OAUTH_CREDENTIALS_JSON 환경 변수가 없습니다. '
            'Google Cloud Console OAuth 클라이언트 JSON을 Vercel에 설정하세요.'
        )
    return json.loads(raw_json)


def _build_web_client_config():
    """
    웹 OAuth Flow용 client config.
    - web 키가 있으면 그대로 사용
    - installed(데스크톱)만 있으면 web 형태로 변환 (GCP에 redirect URI 등록 필요)
    """
    raw = _load_credentials_config()
    redirect_uri = _callback_uri()

    if 'web' in raw:
        config = json.loads(json.dumps(raw))
        uris = list(config['web'].get('redirect_uris') or [])
        if redirect_uri not in uris:
            uris.append(redirect_uri)
        config['web']['redirect_uris'] = uris
        return config, redirect_uri

    if 'installed' in raw:
        ins = raw['installed']
        config = {
            'web': {
                'client_id': ins['client_id'],
                'client_secret': ins['client_secret'],
                'auth_uri': ins.get('auth_uri', 'https://accounts.google.com/o/oauth2/auth'),
                'token_uri': ins.get('token_uri', 'https://oauth2.googleapis.com/token'),
                'redirect_uris': [redirect_uri],
            }
        }
        return config, redirect_uri

    raise ValueError(
        "GOOGLE_OAUTH_CREDENTIALS_JSON에 'web' 또는 'installed' 키가 필요합니다."
    )


def _create_flow():
    config, redirect_uri = _build_web_client_config()
    flow = Flow.from_client_config(config, scopes=SCOPES, redirect_uri=redirect_uri)
    return flow


def _fetch_google_email(access_token: str) -> str:
    if not access_token:
        return ''
    try:
        import urllib.request
        req = urllib.request.Request(
            'https://www.googleapis.com/oauth2/v2/userinfo',
            headers={'Authorization': f'Bearer {access_token}'},
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode())
        return (data.get('email') or '').strip()
    except Exception:
        return ''


@oauth_web_bp.route('/status', methods=['GET'])
def oauth_status():
    """관리자: Drive OAuth 연결 상태."""
    if not _is_admin_request():
        return jsonify({'success': False, 'message': '관리자만 확인할 수 있습니다.'}), 403

    meta = get_stored_token_meta()
    stored = load_stored_token_dict()
    env_token = bool(os.environ.get('GOOGLE_OAUTH_TOKEN_JSON'))

    connected = False
    has_refresh = False
    expiry = None
    last_error = None
    google_email = (meta or {}).get('google_email') or ''

    try:
        creds = get_credentials()
        connected = bool(creds and creds.valid)
        has_refresh = bool(creds and creds.refresh_token)
        if creds and getattr(creds, 'expiry', None):
            expiry = creds.expiry.isoformat()
        if connected and not google_email and creds.token:
            google_email = _fetch_google_email(creds.token)
    except Exception as e:
        last_error = str(e)

    callback_uri = _callback_uri()
    creds_config = _load_credentials_config()
    client_type = 'web' if 'web' in creds_config else ('installed' if 'installed' in creds_config else 'unknown')

    return jsonify({
        'success': True,
        'connected': connected,
        'has_refresh_token': has_refresh,
        'expiry': expiry,
        'google_email': google_email,
        'stored_in_db': bool(stored),
        'env_token_configured': env_token,
        'db_updated_at': (meta or {}).get('updated_at'),
        'callback_uri': callback_uri,
        'oauth_client_type': client_type,
        'last_error': last_error,
        'auto_refresh_note': (
            'refresh_token이 유효하면 access token은 서버가 자동 갱신합니다. '
            'invalid_grant 시에만 아래 재연결 버튼으로 다시 로그인하면 됩니다.'
        ),
        'web_client_hint': (
            '재연결이 redirect_uri 오류로 실패하면 Google Cloud Console에서 '
            'OAuth 클라이언트 유형을 "웹 애플리케이션"으로 만들고 '
            f'승인된 리디렉션 URI에 {callback_uri} 를 추가한 뒤 '
            'GOOGLE_OAUTH_CREDENTIALS_JSON을 해당 JSON으로 교체하세요.'
        ) if client_type == 'installed' else None,
    })


@oauth_web_bp.route('/authorize-url', methods=['GET'])
def oauth_authorize_url():
    """관리자: Google 로그인 URL 반환 (프론트에서 window.location 으로 이동)."""
    if not _is_admin_request():
        return jsonify({'success': False, 'message': '관리자만 연결할 수 있습니다.'}), 403

    try:
        flow = _create_flow()
        state = _serializer().dumps({'v': 1})
        auth_url, _ = flow.authorization_url(
            access_type='offline',
            include_granted_scopes='true',
            prompt='consent',
            state=state,
        )
        return jsonify({
            'success': True,
            'url': auth_url,
            'callback_uri': _callback_uri(),
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e),
        }), 400


@oauth_web_bp.route('/callback', methods=['GET'])
def oauth_callback():
    """Google OAuth 콜백 — 토큰 DB 저장."""
    error = request.args.get('error')
    if error:
        return redirect(f'/api/uploads/oauth/done?status=error&reason={error}')

    state = request.args.get('state', '')
    code = request.args.get('code', '')
    if not code:
        return redirect('/api/uploads/oauth/done?status=error&reason=missing_code')

    try:
        _serializer().loads(state, max_age=900)
    except SignatureExpired:
        return redirect('/api/uploads/oauth/done?status=error&reason=state_expired')
    except BadSignature:
        return redirect('/api/uploads/oauth/done?status=error&reason=invalid_state')

    try:
        flow = _create_flow()
        flow.fetch_token(code=code)
        creds = flow.credentials
        if not creds or not creds.refresh_token:
            return redirect('/api/uploads/oauth/done?status=error&reason=no_refresh_token')

        oauth_credentials_json = os.environ.get('GOOGLE_OAUTH_CREDENTIALS_JSON')
        token_info = {
            'token': creds.token,
            'refresh_token': creds.refresh_token,
            'token_uri': creds.token_uri,
            'scopes': list(creds.scopes) if creds.scopes else SCOPES,
        }
        if getattr(creds, 'expiry', None):
            token_info['expiry'] = creds.expiry.isoformat()
        client_id, client_secret = _client_credentials_from_env(token_info, oauth_credentials_json)
        token_info['client_id'] = client_id
        token_info['client_secret'] = client_secret

        email = _fetch_google_email(creds.token)
        save_stored_token_dict(token_info, google_email=email or None)

        # 인스턴스 캐시 초기화
        import api.uploads.oauth_drive as od
        od._oauth_creds_cache = None
        od._last_oauth_error = None

        return redirect('/api/uploads/oauth/done?status=success')
    except Exception as e:
        print(f'[오류] OAuth callback: {e}')
        import traceback
        traceback.print_exc()
        reason = str(e)[:180].replace(' ', '+')
        return redirect(f'/api/uploads/oauth/done?status=error&reason={reason}')


@oauth_web_bp.route('/migrate-env', methods=['POST'])
def oauth_migrate_env():
    """관리자: 현재 Vercel 환경 변수 토큰을 DB로 복사 (재로그인 없이 1회 마이그레이션)."""
    if not _is_admin_request():
        return jsonify({'success': False, 'message': '관리자만 실행할 수 있습니다.'}), 403

    token_json = os.environ.get('GOOGLE_OAUTH_TOKEN_JSON')
    if not token_json:
        return jsonify({'success': False, 'message': 'GOOGLE_OAUTH_TOKEN_JSON 환경 변수가 없습니다.'}), 400

    try:
        token_info = json.loads(token_json)
        creds = get_credentials()
        if creds and creds.valid:
            from api.uploads.oauth_token_store import save_credentials_object
            email = _fetch_google_email(creds.token)
            save_credentials_object(creds, google_email=email or None)
            return jsonify({'success': True, 'message': '환경 변수 토큰을 DB에 저장했습니다.'})
        return jsonify({'success': False, 'message': '유효한 OAuth 토큰을 가져올 수 없습니다.'}), 400
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500


@oauth_web_bp.route('/done', methods=['GET'])
def oauth_done():
    """OAuth 완료 안내 페이지 (브라우저 리디렉션용)."""
    status = request.args.get('status', 'unknown')
    reason = request.args.get('reason', '')

    if status == 'success':
        title = 'Google Drive 연결 완료'
        body = '정산 파일 업로드용 OAuth 토큰이 저장되었습니다. 이제 access token은 서버가 자동으로 갱신합니다.'
        color = '#155724'
        bg = '#d4edda'
    else:
        title = 'Google Drive 연결 실패'
        body = f'오류: {reason or "알 수 없음"}. GCP redirect URI 설정을 확인하거나 관리자에게 문의하세요.'
        color = '#721c24'
        bg = '#f8d7da'

    html = f'''<!DOCTYPE html>
<html lang="ko"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{title}</title></head>
<body style="font-family:sans-serif;padding:24px;max-width:520px;margin:40px auto;">
<div style="padding:16px;background:{bg};border-radius:8px;color:{color};">
<h2 style="margin:0 0 12px;">{title}</h2>
<p style="margin:0;line-height:1.5;">{body}</p>
</div>
<p style="margin-top:20px;"><a href="/">통합 관리 시스템으로 돌아가기</a></p>
<script>if(window.opener){{window.opener.postMessage({{type:"google-oauth-done",status:"{status}"}},"*");}}</script>
</body></html>'''
    resp = make_response(html)
    resp.headers['Content-Type'] = 'text/html; charset=utf-8'
    return resp
