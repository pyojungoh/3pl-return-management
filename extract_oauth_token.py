"""
OAuth 2.0 토큰을 환경 변수용 JSON으로 변환하는 스크립트
로컬에서 인증 받은 후 이 스크립트를 실행하여 Vercel 환경 변수에 설정할 값을 생성합니다.
"""
import pickle
import json
import os

TOKEN_FILE = 'token.pickle'

def extract_token():
    """token.pickle에서 토큰 정보를 추출하여 JSON으로 변환"""
    if not os.path.exists(TOKEN_FILE):
        print(f"❌ {TOKEN_FILE} 파일을 찾을 수 없습니다.")
        print("먼저 로컬에서 OAuth 2.0 인증을 받아주세요.")
        print("1. python app.py 실행")
        print("2. http://localhost:5000/test-excel-upload.html 접속")
        print("3. 엑셀 파일 업로드 시도 (자동으로 인증 플로우 시작)")
        return None
    
    try:
        with open(TOKEN_FILE, 'rb') as f:
            creds = pickle.load(f)
        
        # 토큰 정보 추출
        token_dict = {
            'token': creds.token,
            'refresh_token': creds.refresh_token,
            'token_uri': creds.token_uri,
            'client_id': creds.client_id,
            'client_secret': creds.client_secret,
            'scopes': list(creds.scopes) if creds.scopes else []
        }
        
        # JSON으로 변환
        token_json = json.dumps(token_dict, indent=2)
        
        print("✅ 토큰 정보 추출 완료!")
        print("\n" + "="*60)
        print("Vercel 환경 변수 설정:")
        print("="*60)
        print(f"\nKey: GOOGLE_OAUTH_TOKEN_JSON")
        print(f"Value: (아래 JSON 전체를 복사하세요)\n")
        print(token_json)
        print("\n" + "="*60)
        print("\n⚠️ 주의: 이 토큰 정보는 보안상 중요합니다. 공유하지 마세요!")
        
        # 파일로도 저장 (선택사항)
        output_file = 'oauth_token_for_vercel.json'
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(token_json)
        print(f"\n✅ 토큰 정보가 {output_file} 파일로도 저장되었습니다.")
        print(f"   (이 파일도 .gitignore에 추가되어 Git에 커밋되지 않습니다)")
        
        return token_json
        
    except Exception as e:
        print(f"❌ 토큰 추출 실패: {e}")
        import traceback
        traceback.print_exc()
        return None

if __name__ == '__main__':
    extract_token()

