"""
구글 드라이브 인증 테스트 스크립트
"""
import os
import sys
import json

# 프로젝트 루트를 Python 경로에 추가
sys.path.insert(0, os.path.dirname(__file__))

def test_environment_variable():
    """환경 변수 확인"""
    print("=" * 60)
    print("1. 환경 변수 확인")
    print("=" * 60)
    
    creds_json = os.environ.get('GOOGLE_SERVICE_ACCOUNT_JSON')
    
    if not creds_json:
        print("❌ GOOGLE_SERVICE_ACCOUNT_JSON 환경 변수가 설정되지 않았습니다.")
        print("\n로컬 파일 확인 중...")
        
        # 로컬 파일 확인
        creds_path = os.path.join(os.path.dirname(__file__), 'service_account.json')
        if os.path.exists(creds_path):
            print(f"✅ 로컬 파일 발견: {creds_path}")
            try:
                with open(creds_path, 'r', encoding='utf-8') as f:
                    creds_data = json.load(f)
                print(f"   서비스 계정: {creds_data.get('client_email', '알 수 없음')}")
                return True, None
            except Exception as e:
                print(f"❌ 로컬 파일 읽기 실패: {e}")
                return False, None
        else:
            print(f"❌ 로컬 파일도 없습니다: {creds_path}")
            return False, None
    else:
        print(f"✅ 환경 변수 발견 (길이: {len(creds_json)} 문자)")
        print(f"   처음 100자: {creds_json[:100]}...")
        return True, creds_json

def test_json_parsing(creds_json):
    """JSON 파싱 테스트"""
    print("\n" + "=" * 60)
    print("2. JSON 파싱 테스트")
    print("=" * 60)
    
    if not creds_json:
        print("⚠️ JSON 문자열이 없습니다. 로컬 파일 테스트로 건너뜁니다.")
        return None
    
    try:
        # 기본 파싱 시도
        creds_json_cleaned = creds_json.strip()
        creds_info = json.loads(creds_json_cleaned)
        print("✅ JSON 파싱 성공 (기본)")
        return creds_info
    except json.JSONDecodeError as json_error:
        print(f"❌ JSON 파싱 실패 (기본): {json_error}")
        print(f"   오류 위치: {json_error.msg} (라인 {json_error.lineno}, 컬럼 {json_error.colno})")
        
        # 다양한 방법 시도
        print("\n다른 방법으로 파싱 시도 중...")
        
        # 방법 1: 이스케이프 문자 처리
        try:
            creds_json_unescaped = creds_json.replace('\\n', '\n').replace('\\t', '\t')
            creds_info = json.loads(creds_json_unescaped)
            print("✅ JSON 파싱 성공 (이스케이프 문자 처리)")
            return creds_info
        except:
            pass
        
        # 방법 2: eval 사용 (보안 위험 있지만 테스트용)
        try:
            creds_info = eval(creds_json)
            if isinstance(creds_info, dict):
                print("✅ JSON 파싱 성공 (eval 사용)")
                return creds_info
        except:
            pass
        
        print(f"❌ 모든 파싱 방법 실패")
        print(f"   처음 500자: {creds_json[:500]}")
        print(f"   마지막 200자: {creds_json[-200:]}")
        return None
    except Exception as e:
        print(f"❌ 예상치 못한 오류: {e}")
        import traceback
        traceback.print_exc()
        return None

def test_required_fields(creds_info):
    """필수 필드 확인"""
    print("\n" + "=" * 60)
    print("3. 필수 필드 확인")
    print("=" * 60)
    
    if not creds_info:
        print("⚠️ JSON 정보가 없습니다.")
        return False
    
    required_fields = ['type', 'project_id', 'private_key', 'client_email']
    missing_fields = [field for field in required_fields if field not in creds_info]
    
    if missing_fields:
        print(f"❌ 필수 필드 누락: {missing_fields}")
        print(f"   존재하는 필드: {list(creds_info.keys())}")
        return False
    else:
        print("✅ 모든 필수 필드 존재")
        print(f"   타입: {creds_info.get('type')}")
        print(f"   프로젝트 ID: {creds_info.get('project_id')}")
        print(f"   서비스 계정: {creds_info.get('client_email')}")
        print(f"   private_key 존재: {bool(creds_info.get('private_key'))}")
        return True

def test_credentials_loading():
    """인증 정보 로드 테스트"""
    print("\n" + "=" * 60)
    print("4. 인증 정보 로드 테스트 (google_drive.get_credentials)")
    print("=" * 60)
    
    try:
        from api.uploads.google_drive import get_credentials
        credentials = get_credentials()
        
        if credentials:
            print("✅ 인증 정보 로드 성공")
            return True
        else:
            print("❌ 인증 정보 로드 실패 (None 반환)")
            return False
    except Exception as e:
        print(f"❌ 인증 정보 로드 오류: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_service_account_creation():
    """서비스 계정 인증 객체 생성 테스트"""
    print("\n" + "=" * 60)
    print("5. 서비스 계정 인증 객체 생성 테스트")
    print("=" * 60)
    
    try:
        from google.oauth2 import service_account
        
        # 환경 변수에서 직접 가져오기
        creds_json = os.environ.get('GOOGLE_SERVICE_ACCOUNT_JSON')
        
        if not creds_json:
            # 로컬 파일 시도
            creds_path = os.path.join(os.path.dirname(__file__), 'service_account.json')
            if os.path.exists(creds_path):
                credentials = service_account.Credentials.from_service_account_file(
                    creds_path, scopes=['https://www.googleapis.com/auth/drive'])
                print("✅ 서비스 계정 인증 객체 생성 성공 (로컬 파일)")
                return True
            else:
                print("❌ 환경 변수와 로컬 파일 모두 없습니다.")
                return False
        
        # JSON 파싱
        creds_info = json.loads(creds_json.strip())
        
        # 인증 객체 생성
        credentials = service_account.Credentials.from_service_account_info(
            creds_info, scopes=['https://www.googleapis.com/auth/drive'])
        
        print("✅ 서비스 계정 인증 객체 생성 성공 (환경 변수)")
        print(f"   서비스 계정: {creds_info.get('client_email')}")
        return True
        
    except Exception as e:
        print(f"❌ 서비스 계정 인증 객체 생성 실패: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """메인 테스트 함수"""
    print("\n" + "=" * 60)
    print("구글 드라이브 인증 테스트 시작")
    print("=" * 60 + "\n")
    
    results = []
    
    # 1. 환경 변수 확인
    has_env, creds_json = test_environment_variable()
    results.append(("환경 변수 확인", has_env))
    
    # 2. JSON 파싱 테스트
    if has_env and creds_json:
        creds_info = test_json_parsing(creds_json)
        results.append(("JSON 파싱", creds_info is not None))
        
        # 3. 필수 필드 확인
        if creds_info:
            has_required = test_required_fields(creds_info)
            results.append(("필수 필드 확인", has_required))
    
    # 4. 인증 정보 로드 테스트
    load_success = test_credentials_loading()
    results.append(("인증 정보 로드", load_success))
    
    # 5. 서비스 계정 인증 객체 생성 테스트
    create_success = test_service_account_creation()
    results.append(("서비스 계정 객체 생성", create_success))
    
    # 결과 요약
    print("\n" + "=" * 60)
    print("테스트 결과 요약")
    print("=" * 60)
    
    for test_name, success in results:
        status = "✅ 성공" if success else "❌ 실패"
        print(f"{test_name}: {status}")
    
    all_passed = all(success for _, success in results)
    print("\n" + "=" * 60)
    if all_passed:
        print("✅ 모든 테스트 통과!")
    else:
        print("❌ 일부 테스트 실패")
    print("=" * 60 + "\n")

if __name__ == '__main__':
    main()

