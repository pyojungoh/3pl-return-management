"""
수동으로 데이터베이스에 데이터 입력하는 스크립트
"""
import sys
import os

# 프로젝트 루트 경로 추가
sys.path.insert(0, os.path.dirname(__file__))

from api.database.models import create_company, create_return


def add_company():
    """화주사 계정 추가"""
    print("=" * 50)
    print("화주사 계정 추가")
    print("=" * 50)
    
    company_name = input("화주사명: ").strip()
    username = input("아이디: ").strip()
    password = input("비밀번호: ").strip()
    role = input("권한 (화주사/관리자) [기본: 화주사]: ").strip() or '화주사'
    
    if create_company(company_name, username, password, role):
        print(f"✅ 화주사 계정이 생성되었습니다: {company_name} ({username})")
    else:
        print(f"❌ 화주사 계정 생성 실패: 이미 존재하거나 오류 발생")


def add_return():
    """반품 데이터 추가"""
    print("=" * 50)
    print("반품 데이터 추가")
    print("=" * 50)
    
    return_data = {
        'return_date': input("반품 접수일 (예: 2025-01-15): ").strip(),
        'company_name': input("화주명: ").strip(),
        'product': input("제품명: ").strip(),
        'customer_name': input("고객명: ").strip(),
        'tracking_number': input("송장번호: ").strip(),
        'return_type': input("반품/교환/오배송: ").strip(),
        'stock_status': input("재고상태 (정상/불량): ").strip(),
        'inspection': input("검품유무: ").strip(),
        'completed': input("처리완료: ").strip(),
        'memo': input("비고: ").strip(),
        'photo_links': input("사진 링크 (줄바꿈으로 구분): ").strip(),
        'other_courier': input("다른외부택배사: ").strip(),
        'shipping_fee': input("배송비: ").strip(),
        'client_request': input("화주사요청: ").strip(),
        'client_confirmed': input("화주사확인완료: ").strip(),
        'month': input("월 (예: 2025년1월): ").strip()
    }
    
    # 필수 필드 확인
    if not return_data['customer_name'] or not return_data['tracking_number']:
        print("❌ 고객명과 송장번호는 필수입니다.")
        return
    
    if not return_data['month']:
        print("❌ 월은 필수입니다.")
        return
    
    return_id = create_return(return_data)
    if return_id:
        print(f"✅ 반품 데이터가 생성되었습니다: ID {return_id}")
    else:
        print("❌ 반품 데이터 생성 실패")


def main():
    """메인 함수"""
    while True:
        print("\n" + "=" * 50)
        print("데이터 입력 메뉴")
        print("=" * 50)
        print("1. 화주사 계정 추가")
        print("2. 반품 데이터 추가")
        print("3. 종료")
        print("=" * 50)
        
        choice = input("선택: ").strip()
        
        if choice == '1':
            add_company()
        elif choice == '2':
            add_return()
        elif choice == '3':
            print("종료합니다.")
            break
        else:
            print("❌ 잘못된 선택입니다.")


if __name__ == '__main__':
    main()



