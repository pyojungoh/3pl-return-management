"""
OAuth 2.0 토큰 재발급 스크립트 (Vercel용)
토큰이 만료/폐기되었을 때 로컬에서 새로 인증받고 Vercel 환경 변수용 JSON을 출력합니다.

사용법:
  python refresh_oauth_for_vercel.py

실행 후:
  1. 브라우저가 열리면 Google 로그인
  2. 출력된 JSON 전체를 복사
  3. Vercel → Settings → Environment Variables → GOOGLE_OAUTH_TOKEN_JSON 값에 붙여넣기
  4. 재배포
"""
import os
import json
import pickle

# credentials.json 경로 (프로젝트 루트)
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
CREDENTIALS_FILE = os.path.join(SCRIPT_DIR, 'credentials.json')
TOKEN_FILE = os.path.join(SCRIPT_DIR, 'token.pickle')
SCOPES = ['https://www.googleapis.com/auth/drive']


def main():
    # 1. credentials.json 확인
    creds_path = CREDENTIALS_FILE
    if not os.path.exists(creds_path):
        # client_secret_*.json 파일 찾기
        for f in os.listdir(SCRIPT_DIR):
            if f.startswith('client_secret') and f.endswith('.json'):
                creds_path = os.path.join(SCRIPT_DIR, f)
                print(f"✅ credentials 파일 사용: {f}")
                break
        if not os.path.exists(creds_path):
            print(f"❌ credentials.json 또는 client_secret_*.json 파일을 찾을 수 없습니다.")
            print("\n해결 방법:")
            print("1. Google Cloud Console → APIs & Services → Credentials")
            print("2. OAuth 2.0 클라이언트 ID 생성 (Desktop app)")
            print("3. JSON 다운로드 후 credentials.json으로 저장")
            return 1

    # 2. 기존 토큰 삭제 (재인증 강제)
    if os.path.exists(TOKEN_FILE):
        os.remove(TOKEN_FILE)
        print(f"🗑️ 기존 토큰 삭제됨 (재인증 필요)")

    # 3. OAuth 플로우 실행
    from google_auth_oauthlib.flow import InstalledAppFlow

    print("\n🔐 Google 로그인 창이 열립니다...")
    print("   (브라우저가 안 열리면 표시된 URL을 직접 접속하세요)\n")

    flow = InstalledAppFlow.from_client_secrets_file(creds_path, SCOPES)
    creds = flow.run_local_server(port=0, open_browser=True)

    # 4. 토큰 저장
    with open(TOKEN_FILE, 'wb') as f:
        pickle.dump(creds, f)
    print("✅ 토큰 저장 완료\n")

    # 5. Vercel용 JSON 출력
    token_dict = {
        'token': creds.token,
        'refresh_token': creds.refresh_token,
        'token_uri': creds.token_uri,
        'client_id': creds.client_id,
        'client_secret': creds.client_secret,
        'scopes': list(creds.scopes) if creds.scopes else []
    }
    if getattr(creds, 'expiry', None):
        token_dict['expiry'] = creds.expiry.isoformat()

    token_json = json.dumps(token_dict, indent=2)

    print("=" * 60)
    print("Vercel 환경 변수에 설정할 값 (아래 전체 복사)")
    print("=" * 60)
    print(token_json)
    print("=" * 60)
    print("\n💡 한 줄 버전 (Vercel에서 줄바꿈 문제 시 사용):")
    print(json.dumps(token_dict))
    print("\n📋 다음 단계:")
    print("1. 위 JSON 전체를 복사 (Ctrl+A, Ctrl+C)")
    print("2. Vercel 대시보드 → 프로젝트 → Settings → Environment Variables")
    print("3. GOOGLE_OAUTH_TOKEN_JSON 찾아서 Edit")
    print("4. Value에 붙여넣기 (한 줄로 되어 있어도 됨)")
    print("5. Save 후 Redeploy")

    # 파일로도 저장
    out_file = os.path.join(SCRIPT_DIR, 'oauth_token_for_vercel.json')
    with open(out_file, 'w', encoding='utf-8') as f:
        f.write(token_json)
    print(f"\n✅ {out_file} 에도 저장됨")

    return 0


if __name__ == '__main__':
    try:
        exit(main())
    except Exception as e:
        print(f"\n❌ 오류: {e}")
        import traceback
        traceback.print_exc()
        exit(1)
