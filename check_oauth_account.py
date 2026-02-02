"""
GOOGLE_OAUTH_TOKEN_JSON에 연결된 Google 계정(이메일) 확인
"""
import os
import json
import sys

# .env 로드 시도
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

def main():
    oauth_token = os.environ.get('GOOGLE_OAUTH_TOKEN_JSON')
    oauth_creds = os.environ.get('GOOGLE_OAUTH_CREDENTIALS_JSON')
    
    if not oauth_token or not oauth_creds:
        print("=" * 60)
        print("OAuth 계정 확인 스크립트")
        print("=" * 60)
        print("\n필요한 환경 변수가 없습니다.")
        print("  GOOGLE_OAUTH_TOKEN_JSON:      " + ("설정됨" if oauth_token else "없음"))
        print("  GOOGLE_OAUTH_CREDENTIALS_JSON: " + ("설정됨" if oauth_creds else "없음"))
        print("\n.env 파일에 두 변수를 설정하거나, Vercel에서 복사해")
        print("PowerShell에서 $env:GOOGLE_OAUTH_TOKEN_JSON = '...' 형태로 설정 후 실행하세요.")
        return 1
    
    try:
        from google.oauth2.credentials import Credentials
        from google.auth.transport.requests import Request
        import urllib.request
        
        creds_info = json.loads(oauth_creds)
        src = creds_info.get('installed') or creds_info.get('web') or creds_info
        if isinstance(src, dict):
            client_id = src.get('client_id', '')
            client_secret = src.get('client_secret', '')
        else:
            client_id = creds_info.get('client_id', '')
            client_secret = creds_info.get('client_secret', '')
        
        token_info = json.loads(oauth_token)
        creds = Credentials(
            token=token_info.get('token'),
            refresh_token=token_info.get('refresh_token'),
            token_uri=token_info.get('token_uri', 'https://oauth2.googleapis.com/token'),
            client_id=client_id,
            client_secret=client_secret,
            scopes=token_info.get('scopes', ['https://www.googleapis.com/auth/drive'])
        )
        
        if creds.expired and creds.refresh_token:
            print("토큰 갱신 중...")
            creds.refresh(Request())
        
        access_token = creds.token
        if not access_token:
            print("토큰을 가져올 수 없습니다.")
            return 1
        
        req = urllib.request.Request(
            'https://www.googleapis.com/oauth2/v2/userinfo',
            headers={'Authorization': f'Bearer {access_token}'}
        )
        with urllib.request.urlopen(req) as resp:
            data = json.loads(resp.read().decode())
        
        print("=" * 50)
        print("OAuth 토큰에 연결된 Google 계정")
        print("=" * 50)
        print(f"  이메일: {data.get('email', 'N/A')}")
        print(f"  이름:   {data.get('name', 'N/A')}")
        print("=" * 50)
        print("\n→ 이 계정이 '제이제이솔루션' 폴더를 소유하거나 공유받아야 합니다.")
        return 0
        
    except Exception as e:
        print(f"오류: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == '__main__':
    sys.exit(main() or 0)
