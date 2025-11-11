"""
관리자 계정 생성 스크립트
로컬에서 실행하여 관리자 계정을 생성한 후 data.db 파일을 배포에 포함시키세요.
"""
import os
import sys

# 프로젝트 루트 디렉토리를 Python 경로에 추가
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from api.database.models import init_db, create_company, get_company_by_username

def create_admin_account():
    """관리자 계정 생성"""
    # 데이터베이스 초기화
    print("데이터베이스 초기화 중...")
    init_db()
    print("✅ 데이터베이스 초기화 완료")
    
    # 관리자 계정 정보
    admin_username = "admin"
    admin_password = "admin123"  # 비밀번호 변경 권장
    admin_company = "관리자"
    
    # 기존 계정 확인
    existing = get_company_by_username(admin_username)
    if existing:
        print(f"⚠️  이미 존재하는 계정: {admin_username}")
        print(f"   회사명: {existing['company_name']}")
        response = input("기존 계정을 삭제하고 새로 만들까요? (y/n): ")
        if response.lower() != 'y':
            print("취소되었습니다.")
            return
        # 기존 계정 삭제 (여기서는 수동으로 삭제하거나 DB에서 직접 삭제)
        print("기존 계정을 수동으로 삭제해주세요.")
        return
    
    # 관리자 계정 생성
    print(f"\n관리자 계정 생성 중...")
    print(f"   아이디: {admin_username}")
    print(f"   비밀번호: {admin_password}")
    print(f"   회사명: {admin_company}")
    print(f"   권한: 관리자")
    
    success = create_company(
        company_name=admin_company,
        username=admin_username,
        password=admin_password,
        role="관리자"
    )
    
    if success:
        print("✅ 관리자 계정이 생성되었습니다!")
        print(f"\n로그인 정보:")
        print(f"   아이디: {admin_username}")
        print(f"   비밀번호: {admin_password}")
        print(f"\n⚠️  보안을 위해 배포 후 비밀번호를 변경하세요!")
    else:
        print("❌ 관리자 계정 생성에 실패했습니다.")

def create_test_company():
    """테스트 화주사 계정 생성"""
    # 테스트 화주사 계정 정보
    test_username = "test"
    test_password = "test123"
    test_company = "테스트 화주사"
    
    # 기존 계정 확인
    existing = get_company_by_username(test_username)
    if existing:
        print(f"⚠️  이미 존재하는 계정: {test_username}")
        return
    
    # 테스트 화주사 계정 생성
    print(f"\n테스트 화주사 계정 생성 중...")
    success = create_company(
        company_name=test_company,
        username=test_username,
        password=test_password,
        role="화주사"
    )
    
    if success:
        print("✅ 테스트 화주사 계정이 생성되었습니다!")
        print(f"   아이디: {test_username}")
        print(f"   비밀번호: {test_password}")
    else:
        print("❌ 테스트 화주사 계정 생성에 실패했습니다.")

if __name__ == '__main__':
    print("=" * 50)
    print("관리자 계정 생성 스크립트")
    print("=" * 50)
    
    # 관리자 계정 생성
    create_admin_account()
    
    # 테스트 화주사 계정 생성 여부 확인
    response = input("\n테스트 화주사 계정도 생성하시겠습니까? (y/n): ")
    if response.lower() == 'y':
        create_test_company()
    
    print("\n" + "=" * 50)
    print("완료!")
    print("=" * 50)

