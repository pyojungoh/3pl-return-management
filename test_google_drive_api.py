"""
구글 드라이브 API 실제 호출 테스트 스크립트
"""
import os
import sys

# 프로젝트 루트를 Python 경로에 추가
sys.path.insert(0, os.path.dirname(__file__))

def test_folder_access():
    """폴더 접근 테스트"""
    print("=" * 60)
    print("구글 드라이브 폴더 접근 테스트")
    print("=" * 60 + "\n")
    
    try:
        from api.uploads.google_drive import get_credentials, SETTLEMENT_MAIN_FOLDER_ID, SETTLEMENT_MAIN_FOLDER_NAME
        from googleapiclient.discovery import build
        from googleapiclient.errors import HttpError
        
        # 인증 정보 가져오기
        print("1. 인증 정보 로드 중...")
        credentials = get_credentials()
        if not credentials:
            print("❌ 인증 정보를 가져올 수 없습니다.")
            return False
        
        print("✅ 인증 정보 로드 성공")
        
        # Drive API 서비스 생성
        print("\n2. Drive API 서비스 생성 중...")
        service = build('drive', 'v3', credentials=credentials)
        print("✅ Drive API 서비스 생성 성공")
        
        # 메인 폴더 접근 확인
        print(f"\n3. 메인 폴더 접근 확인: {SETTLEMENT_MAIN_FOLDER_NAME}")
        print(f"   폴더 ID: {SETTLEMENT_MAIN_FOLDER_ID}")
        
        try:
            folder_info = service.files().get(
                fileId=SETTLEMENT_MAIN_FOLDER_ID,
                fields='id, name, permissions, shared, owners',
                supportsAllDrives=True
            ).execute()
            
            folder_name = folder_info.get('name', '알 수 없음')
            folder_shared = folder_info.get('shared', False)
            permissions = folder_info.get('permissions', [])
            
            print(f"✅ 폴더 접근 성공: {folder_name}")
            print(f"   폴더 ID: {SETTLEMENT_MAIN_FOLDER_ID}")
            print(f"   공유됨: {folder_shared}")
            print(f"   권한 수: {len(permissions)}")
            
            # 서비스 계정 이메일 확인
            try:
                import json
                creds_json = os.environ.get('GOOGLE_SERVICE_ACCOUNT_JSON')
                if creds_json:
                    creds_info = json.loads(creds_json.strip())
                    sa_email = creds_info.get('client_email', '')
                else:
                    creds_path = os.path.join(os.path.dirname(__file__), 'service_account.json')
                    with open(creds_path, 'r', encoding='utf-8') as f:
                        creds_info = json.load(f)
                    sa_email = creds_info.get('client_email', '')
                
                print(f"\n4. 서비스 계정 권한 확인: {sa_email}")
                has_service_account = False
                for perm in permissions:
                    email = perm.get('emailAddress', '')
                    role = perm.get('role', '')
                    if email == sa_email:
                        has_service_account = True
                        print(f"   ✅ 서비스 계정 발견: {email} (권한: {role})")
                        break
                
                if not has_service_account:
                    print(f"   ⚠️ 서비스 계정이 권한 목록에 없지만, 폴더 접근은 가능합니다.")
                    
            except Exception as e:
                print(f"   ⚠️ 서비스 계정 이메일 확인 실패: {e}")
            
            return True
            
        except HttpError as e:
            error_status = e.resp.status if hasattr(e, 'resp') else '알 수 없음'
            error_msg = str(e)
            
            print(f"❌ 폴더 접근 실패: {error_msg}")
            print(f"   오류 코드: {error_status}")
            
            if error_status == 404:
                print(f"\n⚠️ 폴더를 찾을 수 없습니다. (ID: {SETTLEMENT_MAIN_FOLDER_ID})")
                print(f"   폴더가 존재하지 않거나 삭제되었습니다.")
            elif error_status == 403:
                print(f"\n⚠️ 폴더에 접근할 수 없습니다. (403 Forbidden)")
                print(f"   서비스 계정이 폴더에 접근할 권한이 없습니다.")
                print(f"\n해결 방법:")
                print(f"1. Google Drive 접속: https://drive.google.com/")
                print(f"2. '{SETTLEMENT_MAIN_FOLDER_NAME}' 폴더 우클릭 → '공유' 클릭")
                print(f"3. 서비스 계정 이메일 추가 (편집자 권한)")
                print(f"4. '전송' 클릭")
            
            return False
        
        except Exception as e:
            print(f"❌ 폴더 접근 오류: {e}")
            import traceback
            traceback.print_exc()
            return False
            
    except Exception as e:
        print(f"❌ 테스트 오류: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_target_folder():
    """대상 폴더(정산파일) 확인"""
    print("\n" + "=" * 60)
    print("대상 폴더(정산파일) 확인")
    print("=" * 60 + "\n")
    
    try:
        from api.uploads.google_drive import get_credentials, find_folder_in_shared, SETTLEMENT_MAIN_FOLDER_ID, SETTLEMENT_MAIN_FOLDER_NAME
        from googleapiclient.discovery import build
        
        # 인증 정보 가져오기
        credentials = get_credentials()
        if not credentials:
            print("❌ 인증 정보를 가져올 수 없습니다.")
            return False
        
        service = build('drive', 'v3', credentials=credentials)
        
        folder_name = '정산파일'
        print(f"1. '{folder_name}' 폴더 검색 중...")
        print(f"   부모 폴더: {SETTLEMENT_MAIN_FOLDER_NAME} (ID: {SETTLEMENT_MAIN_FOLDER_ID})")
        
        target_folder_id = find_folder_in_shared(service, folder_name, SETTLEMENT_MAIN_FOLDER_ID)
        
        if target_folder_id:
            print(f"✅ '{folder_name}' 폴더 찾기 성공 (ID: {target_folder_id})")
            return True
        else:
            print(f"❌ '{folder_name}' 폴더를 찾을 수 없습니다.")
            print(f"\n해결 방법:")
            print(f"1. Google Drive 접속: https://drive.google.com/")
            print(f"2. '{SETTLEMENT_MAIN_FOLDER_NAME}' 폴더 열기")
            print(f"3. '새로 만들기' → '폴더' 클릭")
            print(f"4. 폴더 이름: '{folder_name}'")
            print(f"5. 폴더 생성 후 서비스 계정과 공유 (상위 폴더 공유 시 자동 공유됨)")
            return False
            
    except Exception as e:
        print(f"❌ 테스트 오류: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """메인 테스트 함수"""
    print("\n" + "=" * 60)
    print("구글 드라이브 API 실제 호출 테스트 시작")
    print("=" * 60 + "\n")
    
    results = []
    
    # 1. 폴더 접근 테스트
    folder_access = test_folder_access()
    results.append(("폴더 접근", folder_access))
    
    # 2. 대상 폴더 확인
    if folder_access:
        target_folder = test_target_folder()
        results.append(("대상 폴더 확인", target_folder))
    
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
        print("구글 드라이브 API 연동이 정상적으로 작동합니다.")
    else:
        print("❌ 일부 테스트 실패")
        print("위의 오류 메시지와 해결 방법을 확인하세요.")
    print("=" * 60 + "\n")

if __name__ == '__main__':
    main()

