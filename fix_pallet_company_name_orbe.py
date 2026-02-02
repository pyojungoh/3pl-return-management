"""
파레트 화주사명 통일: "오르베엔코" → "오르베앤코"
정산 파레트 불러오기가 동작하도록 pallets, pallet_monthly_settlements, pallet_settlement_companies, pallet_fees 테이블 업데이트
로컬(SQLite) 및 배포(PostgreSQL) 환경 모두 지원
"""
import os
import sys

# 프로젝트 루트에서 실행
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

OLD_NAME = '오르베엔코'
NEW_NAME = '오르베앤코'

USE_POSTGRESQL = bool(os.environ.get('DATABASE_URL') or os.environ.get('POSTGRES_URL'))


def run_sqlite():
    import sqlite3
    db_path = os.path.join(os.path.dirname(__file__), 'data.db')
    if not os.path.exists(db_path):
        print(f"❌ SQLite DB 파일 없음: {db_path}")
        return False
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    try:
        _run_updates(cursor, conn, use_pg=False)
        return True
    finally:
        cursor.close()
        conn.close()


def run_postgresql():
    try:
        import psycopg2
        from psycopg2.extras import RealDictCursor
    except ImportError:
        print("❌ psycopg2가 필요합니다. pip install psycopg2-binary")
        return False

    db_url = os.environ.get('DATABASE_URL') or os.environ.get('POSTGRES_URL')
    if not db_url:
        db_url = "postgresql://neondb_owner:npg_CNqVFs9j2Bpi@ep-dark-queen-a4w25otz-pooler.us-east-1.aws.neon.tech/neondb?sslmode=require"
        print("ℹ️  환경변수 DATABASE_URL 없음 → 배포 DB URL 사용")

    try:
        conn = psycopg2.connect(db_url)
        cursor = conn.cursor(cursor_factory=RealDictCursor)
    except Exception as e:
        print(f"❌ PostgreSQL 연결 실패: {e}")
        import traceback
        traceback.print_exc()
        return False

    try:
        _run_updates(cursor, conn, use_pg=True)
        return True
    finally:
        cursor.close()
        conn.close()


def _run_updates(cursor, conn, use_pg: bool):
    param = '%s' if use_pg else '?'
    updated = {'pallets': 0, 'pallet_monthly_settlements': 0, 'pallet_settlement_companies': 0, 'pallet_fees': 0}

    # 1. pallets
    if use_pg:
        cursor.execute('UPDATE pallets SET company_name = %s WHERE company_name = %s', (NEW_NAME, OLD_NAME))
    else:
        cursor.execute('UPDATE pallets SET company_name = ? WHERE company_name = ?', (NEW_NAME, OLD_NAME))
    updated['pallets'] = cursor.rowcount

    # 2. pallet_monthly_settlements
    if use_pg:
        cursor.execute('UPDATE pallet_monthly_settlements SET company_name = %s WHERE company_name = %s', (NEW_NAME, OLD_NAME))
    else:
        cursor.execute('UPDATE pallet_monthly_settlements SET company_name = ? WHERE company_name = ?', (NEW_NAME, OLD_NAME))
    updated['pallet_monthly_settlements'] = cursor.rowcount

    # 3. pallet_settlement_companies
    if use_pg:
        cursor.execute('UPDATE pallet_settlement_companies SET company_name = %s WHERE company_name = %s', (NEW_NAME, OLD_NAME))
    else:
        cursor.execute('UPDATE pallet_settlement_companies SET company_name = ? WHERE company_name = ?', (NEW_NAME, OLD_NAME))
    updated['pallet_settlement_companies'] = cursor.rowcount

    # 4. pallet_fees (UNIQUE on company_name - 오르베앤코가 이미 있으면 충돌)
    if use_pg:
        cursor.execute('SELECT 1 FROM pallet_fees WHERE company_name = %s LIMIT 1', (NEW_NAME,))
    else:
        cursor.execute('SELECT 1 FROM pallet_fees WHERE company_name = ? LIMIT 1', (NEW_NAME,))
    new_exists = cursor.fetchone() is not None

    if new_exists:
        # 오르베앤코가 이미 있으면 오르베엔코 행 삭제
        if use_pg:
            cursor.execute('DELETE FROM pallet_fees WHERE company_name = %s', (OLD_NAME,))
        else:
            cursor.execute('DELETE FROM pallet_fees WHERE company_name = ?', (OLD_NAME,))
        updated['pallet_fees'] = cursor.rowcount
        if cursor.rowcount > 0:
            print(f"   pallet_fees: 오르베앤코가 이미 있어 오르베엔코 행 {cursor.rowcount}건 삭제")
    else:
        if use_pg:
            cursor.execute('UPDATE pallet_fees SET company_name = %s WHERE company_name = %s', (NEW_NAME, OLD_NAME))
        else:
            cursor.execute('UPDATE pallet_fees SET company_name = ? WHERE company_name = ?', (NEW_NAME, OLD_NAME))
        updated['pallet_fees'] = cursor.rowcount

    conn.commit()

    print("=" * 50)
    print(f"파레트 화주사명 변경: '{OLD_NAME}' → '{NEW_NAME}'")
    print("=" * 50)
    for tbl, cnt in updated.items():
        print(f"  {tbl}: {cnt}건 업데이트")
    print("=" * 50)
    total = sum(updated.values())
    if total > 0:
        print("✅ 완료. 정산 메뉴에서 파레트 불러오기를 다시 시도해보세요.")
    else:
        print("ℹ️  변경된 데이터가 없습니다. (이미 변경되었거나 해당 화주사 데이터가 없음)")


def main():
    print("=" * 50)
    print("파레트 화주사명 통일 스크립트")
    print("=" * 50)
    print(f"변경: '{OLD_NAME}' → '{NEW_NAME}'")
    print()

    if USE_POSTGRESQL:
        print("📌 PostgreSQL(배포) DB 사용")
        ok = run_postgresql()
    else:
        print("📌 SQLite(로컬) DB 사용")
        ok = run_sqlite()

    return 0 if ok else 1


if __name__ == '__main__':
    sys.exit(main())
