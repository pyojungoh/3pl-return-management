"""
홈페이지(로그인 포털) 설정 API — 공개 조회 + 관리자 저장
"""
import json
from urllib.parse import unquote

from flask import Blueprint, request, jsonify

from api.uploads.cloudinary_upload import upload_to_cloudinary

from api.database.models import (
    get_company_by_username,
    get_homepage_portal_config_merged,
    set_homepage_portal_config,
)

homepage_bp = Blueprint('homepage', __name__, url_prefix='/api/homepage')


def _verify_admin_actor():
    """헤더 + DB로 관리자 이중 확인 (다른 모듈과 동일 패턴)."""
    raw_role = request.headers.get('X-User-Role') or ''
    role = unquote(raw_role.strip())
    raw_name = request.headers.get('X-User-Name') or ''
    username = unquote(raw_name.strip())
    if role != '관리자' or not username:
        return None
    user = get_company_by_username(username)
    if not user:
        return None
    if (user.get('role') or '').strip() != '관리자':
        return None
    return user


ALLOWED_KEYS = frozenset({
    'hero_title', 'hero_subtitle', 'notice_text', 'notice_visible',
    'login_card_title', 'logo_url', 'features',
    'footer_company', 'footer_line2', 'footer_tel',
    'cta_label', 'cta_url', 'browser_tab_title',
    'meta_description', 'footer_copyright', 'footer_seo_block',
    'quote_section_title', 'quote_section_subtitle', 'inquiry_email',
    'service_section_title', 'service_section_lead', 'service_cards',
    'banner_images', 'hero_slides', 'partner_section_title', 'partner_section_lead',
    'partner_logos', 'youtube_section_title', 'youtube_section_lead', 'youtube_items',
})


def _clip(s, n=500):
    if s is None:
        return ''
    t = str(s).strip()
    return t[:n]


def _sanitize_config(raw):
    """허용 키만, 길이 제한. HTML 저장 없음(텍스트만)."""
    if not isinstance(raw, dict):
        return None, '설정 객체가 올바르지 않습니다.'
    out = {}
    for k in ALLOWED_KEYS:
        if k not in raw:
            continue
        v = raw[k]
        if k == 'notice_visible':
            out[k] = bool(v)
        elif k == 'features':
            if not isinstance(v, list):
                continue
            feats = []
            for item in v[:4]:
                if not isinstance(item, dict):
                    continue
                feats.append({
                    'icon': _clip(item.get('icon'), 12),
                    'title': _clip(item.get('title'), 80),
                    'desc': _clip(item.get('desc'), 200),
                })
            out[k] = feats
        elif k == 'logo_url':
            out[k] = _clip(v, 800)
        elif k == 'cta_url':
            out[k] = _clip(v, 800)
        elif k == 'browser_tab_title':
            out[k] = _clip(v, 120)
        elif k == 'meta_description':
            out[k] = _clip(v, 500)
        elif k == 'footer_copyright':
            out[k] = _clip(v, 300)
        elif k == 'footer_seo_block':
            out[k] = _clip(v, 4000)
        elif k == 'quote_section_title':
            out[k] = _clip(v, 200)
        elif k == 'quote_section_subtitle':
            out[k] = _clip(v, 800)
        elif k == 'inquiry_email':
            out[k] = _clip(v, 200)
        elif k == 'service_section_title':
            out[k] = _clip(v, 200)
        elif k == 'service_section_lead':
            out[k] = _clip(v, 800)
        elif k == 'service_cards':
            if not isinstance(v, list):
                continue
            cards = []
            for item in v[:8]:
                if not isinstance(item, dict):
                    continue
                title = _clip(item.get('title'), 120)
                if not title:
                    continue
                cards.append({
                    'image_url': _clip(item.get('image_url'), 800),
                    'title': title,
                    'body': _clip(item.get('body'), 1200),
                })
            out[k] = cards
        elif k == 'partner_section_title':
            out[k] = _clip(v, 200)
        elif k == 'partner_section_lead':
            out[k] = _clip(v, 800)
        elif k == 'youtube_section_title':
            out[k] = _clip(v, 200)
        elif k == 'youtube_section_lead':
            out[k] = _clip(v, 800)
        elif k == 'banner_images':
            if not isinstance(v, list):
                continue
            out[k] = [_clip(u, 800) for u in v[:20] if isinstance(u, str) and str(u).strip()]
        elif k == 'partner_logos':
            if not isinstance(v, list):
                continue
            pl = []
            for item in v[:24]:
                if not isinstance(item, dict):
                    continue
                url = _clip(item.get('image_url'), 800)
                if not url:
                    continue
                pl.append({'image_url': url, 'label': _clip(item.get('label'), 120)})
            out[k] = pl
        elif k == 'youtube_items':
            if not isinstance(v, list):
                continue
            yt = []
            for item in v[:12]:
                if not isinstance(item, dict):
                    continue
                vid = _clip(item.get('video_id'), 20)
                if len(vid) != 11:
                    continue
                yt.append({'video_id': vid, 'title': _clip(item.get('title'), 200)})
            out[k] = yt
        elif k == 'hero_slides':
            if not isinstance(v, list):
                continue
            slides = []
            for item in v[:12]:
                if not isinstance(item, dict):
                    continue
                img = _clip(item.get('image_url'), 800)
                if not img:
                    continue
                slides.append({
                    'image_url': img,
                    'button_label': _clip(item.get('button_label'), 80) or '자세히 보기',
                    'link_url': _clip(item.get('link_url'), 800),
                })
            out[k] = slides
        else:
            out[k] = _clip(v, 2000)
    try:
        blob = json.dumps(out, ensure_ascii=False)
    except Exception:
        return None, 'JSON 직렬화에 실패했습니다.'
    if len(blob) > 48000:
        return None, '설정 용량이 너무 큽니다.'
    return out, None


@homepage_bp.route('/config', methods=['GET'])
def get_config():
    """공개: 로그인 화면에서 호출."""
    try:
        cfg = get_homepage_portal_config_merged()
        return jsonify({'success': True, 'config': cfg})
    except Exception as e:
        print(f'[homepage] GET config 오류: {e}')
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'message': str(e)}), 500


@homepage_bp.route('/upload-image', methods=['POST'])
def upload_portal_image():
    """관리자만: Cloudinary `homepage_portal` 폴더에 이미지 업로드 (슬라이드·배너·로고 등)."""
    actor = _verify_admin_actor()
    if not actor:
        return jsonify({'success': False, 'message': '관리자만 업로드할 수 있습니다.'}), 403
    if 'file' not in request.files:
        return jsonify({'success': False, 'message': '파일이 없습니다.'}), 400
    file = request.files['file']
    if not file or not file.filename:
        return jsonify({'success': False, 'message': '파일명이 없습니다.'}), 400
    mime = (getattr(file, 'mimetype', None) or getattr(file, 'content_type', None) or '').lower()
    if not mime.startswith('image/'):
        return jsonify({'success': False, 'message': '이미지 파일만 업로드할 수 있습니다.'}), 400
    size = 0
    try:
        pos = file.tell()
    except Exception:
        pos = 0
    try:
        file.seek(0, 2)
        size = file.tell()
        file.seek(0)
    except Exception:
        try:
            file.seek(pos)
        except Exception:
            pass
        size = 0
    max_bytes = 8 * 1024 * 1024
    if size and size > max_bytes:
        return jsonify({'success': False, 'message': '이미지는 8MB 이하여야 합니다.'}), 400
    try:
        upload_result = upload_to_cloudinary(file, folder='homepage_portal')
    except Exception as e:
        print(f'[homepage] upload-image 오류: {e}')
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'message': f'업로드 실패: {e}'}), 500
    url = (upload_result or {}).get('secure_url') or (upload_result or {}).get('url')
    if not url:
        return jsonify({'success': False, 'message': '업로드 응답에 URL이 없습니다.'}), 500
    return jsonify({
        'success': True,
        'data': {'file_url': url},
        'message': '업로드되었습니다.',
    })


@homepage_bp.route('/config', methods=['PUT'])
def put_config():
    """관리자만 저장."""
    actor = _verify_admin_actor()
    if not actor:
        return jsonify({'success': False, 'message': '관리자만 저장할 수 있습니다.'}), 403
    data = request.get_json(silent=True) or {}
    raw = data.get('config')
    sanitized, err = _sanitize_config(raw)
    if err:
        return jsonify({'success': False, 'message': err}), 400
    username = (actor.get('username') or '').strip()
    try:
        merged = set_homepage_portal_config(sanitized, username)
        return jsonify({'success': True, 'config': merged, 'message': '저장되었습니다.'})
    except Exception as e:
        print(f'[homepage] PUT config 오류: {e}')
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'message': str(e)}), 500
