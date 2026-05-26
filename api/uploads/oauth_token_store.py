"""
Google Drive OAuth 토큰 DB 저장 (Vercel 환경 변수 수동 갱신 없이 refresh·재연결용)
"""
import json
from datetime import datetime
from typing import Any, Dict, Optional

from google.oauth2.credentials import Credentials

from api.database.models import USE_POSTGRESQL, get_db_connection

TOKEN_ROW_ID = 1


def ensure_google_oauth_token_table():
    """google_oauth_token_store 테이블 생성 (단일 행 id=1)."""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        if USE_POSTGRESQL:
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS google_oauth_token_store (
                    id INTEGER PRIMARY KEY,
                    token_json TEXT NOT NULL,
                    google_email TEXT,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
        else:
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS google_oauth_token_store (
                    id INTEGER NOT NULL PRIMARY KEY,
                    token_json TEXT NOT NULL,
                    google_email TEXT,
                    updated_at TEXT DEFAULT (datetime('now'))
                )
            ''')
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        cursor.close()
        conn.close()


def credentials_to_token_dict(creds: Credentials) -> Dict[str, Any]:
    token_dict = {
        'token': creds.token,
        'refresh_token': creds.refresh_token,
        'token_uri': creds.token_uri,
        'client_id': creds.client_id,
        'client_secret': creds.client_secret,
        'scopes': list(creds.scopes) if creds.scopes else [],
    }
    if getattr(creds, 'expiry', None):
        token_dict['expiry'] = creds.expiry.isoformat()
    return token_dict


def load_stored_token_dict() -> Optional[Dict[str, Any]]:
    """DB에 저장된 OAuth 토큰 JSON (없으면 None)."""
    try:
        ensure_google_oauth_token_table()
    except Exception as e:
        print(f'[경고] google_oauth_token_store 테이블 확인 실패: {e}')
        return None

    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            'SELECT token_json FROM google_oauth_token_store WHERE id = %s'
            if USE_POSTGRESQL else
            'SELECT token_json FROM google_oauth_token_store WHERE id = ?',
            (TOKEN_ROW_ID,),
        )
        row = cursor.fetchone()
        if not row:
            return None
        raw = row[0] if not isinstance(row, dict) else row.get('token_json')
        if not raw:
            return None
        return json.loads(raw)
    except Exception as e:
        print(f'[경고] OAuth 토큰 DB 로드 실패: {e}')
        return None
    finally:
        cursor.close()
        conn.close()


def save_stored_token_dict(token_dict: Dict[str, Any], google_email: Optional[str] = None) -> bool:
    """OAuth 토큰 JSON을 DB에 저장 (upsert id=1)."""
    if not token_dict or not token_dict.get('refresh_token'):
        print('[경고] refresh_token 없는 OAuth JSON은 DB에 저장하지 않습니다.')
        return False

    ensure_google_oauth_token_table()
    blob = json.dumps(token_dict, ensure_ascii=False)
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        if USE_POSTGRESQL:
            cursor.execute(
                '''
                INSERT INTO google_oauth_token_store (id, token_json, google_email, updated_at)
                VALUES (%s, %s, %s, CURRENT_TIMESTAMP)
                ON CONFLICT (id) DO UPDATE SET
                    token_json = EXCLUDED.token_json,
                    google_email = COALESCE(EXCLUDED.google_email, google_oauth_token_store.google_email),
                    updated_at = CURRENT_TIMESTAMP
                ''',
                (TOKEN_ROW_ID, blob, google_email),
            )
        else:
            cursor.execute(
                '''
                INSERT OR REPLACE INTO google_oauth_token_store (id, token_json, google_email, updated_at)
                VALUES (?, ?, ?, datetime('now'))
                ''',
                (TOKEN_ROW_ID, blob, google_email),
            )
        conn.commit()
        print('[성공] OAuth 토큰 DB 저장 완료')
        return True
    except Exception as e:
        conn.rollback()
        print(f'[오류] OAuth 토큰 DB 저장 실패: {e}')
        return False
    finally:
        cursor.close()
        conn.close()


def save_credentials_object(creds: Credentials, google_email: Optional[str] = None) -> bool:
    return save_stored_token_dict(credentials_to_token_dict(creds), google_email=google_email)


def get_stored_token_meta() -> Optional[Dict[str, Any]]:
    """상태 API용 — 이메일·갱신 시각."""
    try:
        ensure_google_oauth_token_table()
    except Exception:
        return None

    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            'SELECT google_email, updated_at FROM google_oauth_token_store WHERE id = %s'
            if USE_POSTGRESQL else
            'SELECT google_email, updated_at FROM google_oauth_token_store WHERE id = ?',
            (TOKEN_ROW_ID,),
        )
        row = cursor.fetchone()
        if not row:
            return None
        if isinstance(row, dict):
            return {
                'google_email': row.get('google_email'),
                'updated_at': row.get('updated_at'),
            }
        return {'google_email': row[0], 'updated_at': row[1]}
    except Exception:
        return None
    finally:
        cursor.close()
        conn.close()
