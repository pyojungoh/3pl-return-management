"""
배포된 PostgreSQL 데이터베이스의 데이터를 로컬로 가져오는 스크립트

사용 방법:
1. 배포된 DATABASE_URL을 환경변수로 설정하거나 직접 입력
2. python export_production_db.py 실행
3. 데이터가 CSV 파일로 저장되거나 로컬 SQLite DB로 복사됨
"""
import os
import sys
import csv
import json
from datetime import datetime

# 배포된 DATABASE_URL 입력 (Vercel 환경변수에서 가져오거나 직접 입력)
# 
# Vercel에서 DATABASE_URL 확인 방법:
# 1. https://vercel.com 접속 후 로그인
# 2. 프로젝트 선택 (jjaysolution.com 또는 3pl-return-management)
# 3. 상단 메뉴에서 "Settings" 클릭
# 4. 왼쪽 사이드바에서 "Environment Variables" 클릭
# 5. "DATABASE_URL" 찾기 (값이 마스킹되어 있으면 "Reveal" 버튼 클릭)
# 6. 전체 연결 문자열 복사 (postgresql://... 형식)
#
# 또는 환경변수로 설정:
# Windows PowerShell: $env:PRODUCTION_DATABASE_URL="postgresql://..."
# Windows CMD: set PRODUCTION_DATABASE_URL=postgresql://...
# Linux/Mac: export PRODUCTION_DATABASE_URL="postgresql://..."

PRODUCTION_DATABASE_URL = os.environ.get('PRODUCTION_DATABASE_URL')

if not PRODUCTION_DATABASE_URL:
    print('\n' + '=' * 60)
    print('DATABASE_URL 입력 필요')
    print('=' * 60)
    print('\nVercel에서 DATABASE_URL 확인 방법:')
    print('1. https://vercel.com 접속 후 로그인')
    print('2. 프로젝트 선택 (jjaysolution.com 또는 3pl-return-management)')
    print('3. 상단 메뉴에서 "Settings" 클릭')
    print('4. 왼쪽 사이드바에서 "Environment Variables" 클릭')
    print('5. "DATABASE_URL" 찾기 (값이 마스킹되어 있으면 "Reveal" 버튼 클릭)')
    print('6. 전체 연결 문자열 복사 (postgresql://... 형식)')
    print('\n또는 환경변수로 설정:')
    print('  Windows PowerShell: $env:PRODUCTION_DATABASE_URL="postgresql://..."')
    print('  Windows CMD: set PRODUCTION_DATABASE_URL=postgresql://...')
    print('  Linux/Mac: export PRODUCTION_DATABASE_URL="postgresql://..."')
    print('\n' + '-' * 60)
    print('\n⚠️ 주의: DATABASE_URL 값만 입력하세요 (명령어 전체가 아닙니다)')
    print('   예: postgresql://user:password@host:port/database?sslmode=require')
    print('   ❌ 잘못된 입력: $env:PRODUCTION_DATABASE_URL="postgresql://..."')
    print('   ✅ 올바른 입력: postgresql://user:password@host:port/database?sslmode=require')
    print('\n' + '-' * 60)
    user_input = input('\n배포된 DATABASE_URL을 입력하세요: ').strip()
    
    # 사용자가 명령어 전체를 입력한 경우 자동으로 추출
    if user_input.startswith('$env:PRODUCTION_DATABASE_URL=') or user_input.startswith('set PRODUCTION_DATABASE_URL=') or user_input.startswith('export PRODUCTION_DATABASE_URL='):
        # 따옴표로 감싸진 부분 추출
        import re
        match = re.search(r'["\'](postgresql://[^"\']+)["\']', user_input)
        if match:
            PRODUCTION_DATABASE_URL = match.group(1)
            print(f'\n✅ DATABASE_URL 자동 추출: {PRODUCTION_DATABASE_URL[:50]}...')
        else:
            # 등호 뒤의 값 추출
            if '=' in user_input:
                PRODUCTION_DATABASE_URL = user_input.split('=', 1)[1].strip('"\'')
            else:
                PRODUCTION_DATABASE_URL = user_input
    else:
        PRODUCTION_DATABASE_URL = user_input.strip('"\'')

if not PRODUCTION_DATABASE_URL:
    print('❌ DATABASE_URL이 필요합니다.')
    sys.exit(1)

try:
    import psycopg2
    from psycopg2.extras import RealDictCursor
except ImportError:
    print('❌ psycopg2가 설치되지 않았습니다. pip install psycopg2-binary 실행하세요.')
    sys.exit(1)

def connect_to_production_db():
    """배포된 PostgreSQL 데이터베이스에 연결"""
    try:
        # SSL 모드 추가
        if 'sslmode' not in PRODUCTION_DATABASE_URL and 'sslmode=' not in PRODUCTION_DATABASE_URL:
            if '?' in PRODUCTION_DATABASE_URL:
                conn = psycopg2.connect(PRODUCTION_DATABASE_URL + '&sslmode=require')
            else:
                conn = psycopg2.connect(PRODUCTION_DATABASE_URL + '?sslmode=require')
        else:
            conn = psycopg2.connect(PRODUCTION_DATABASE_URL)
        print('✅ 배포된 데이터베이스에 연결되었습니다.')
        return conn
    except Exception as e:
        print(f'❌ 데이터베이스 연결 오류: {e}')
        sys.exit(1)

def get_all_tables(conn):
    """모든 테이블 목록 가져오기"""
    cursor = conn.cursor()
    cursor.execute("""
        SELECT table_name 
        FROM information_schema.tables 
        WHERE table_schema = 'public' 
        AND table_type = 'BASE TABLE'
        ORDER BY table_name
    """)
    tables = [row[0] for row in cursor.fetchall()]
    cursor.close()
    return tables

def export_table_to_csv(conn, table_name, output_dir='exported_data'):
    """테이블 데이터를 CSV로 내보내기"""
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    try:
        cursor.execute(f'SELECT * FROM {table_name} ORDER BY id')
        rows = cursor.fetchall()
        
        if not rows:
            print(f'   ⚠️ {table_name}: 데이터 없음')
            return 0
        
        # CSV 파일로 저장
        csv_file = os.path.join(output_dir, f'{table_name}.csv')
        with open(csv_file, 'w', newline='', encoding='utf-8-sig') as f:
            if rows:
                writer = csv.DictWriter(f, fieldnames=rows[0].keys())
                writer.writeheader()
                for row in rows:
                    writer.writerow(dict(row))
        
        print(f'   ✅ {table_name}: {len(rows)}건 → {csv_file}')
        return len(rows)
    except Exception as e:
        print(f'   ❌ {table_name}: 오류 - {e}')
        return 0
    finally:
        cursor.close()

def export_table_to_json(conn, table_name, output_dir='exported_data'):
    """테이블 데이터를 JSON으로 내보내기"""
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    try:
        cursor.execute(f'SELECT * FROM {table_name} ORDER BY id')
        rows = cursor.fetchall()
        
        if not rows:
            return 0
        
        # JSON 파일로 저장
        json_file = os.path.join(output_dir, f'{table_name}.json')
        data = []
        for row in rows:
            row_dict = dict(row)
            # 날짜 객체를 문자열로 변환
            for key, value in row_dict.items():
                if isinstance(value, datetime):
                    row_dict[key] = value.isoformat()
            data.append(row_dict)
        
        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2, default=str)
        
        print(f'   ✅ {table_name}: {len(rows)}건 → {json_file}')
        return len(rows)
    except Exception as e:
        print(f'   ❌ {table_name}: 오류 - {e}')
        return 0
    finally:
        cursor.close()

def copy_to_local_sqlite(conn, output_db='data.db'):
    """PostgreSQL 데이터를 로컬 SQLite로 복사 (로컬 개발용 data.db에 직접 복사)"""
    import sqlite3
    
    print(f'\n📦 배포된 데이터를 로컬 data.db로 복사 중...')
    print(f'   (로컬 서버 실행 시 배포된 상태와 동일하게 보이도록)')
    
    # SQLite 연결
    sqlite_conn = sqlite3.connect(output_db)
    sqlite_cursor = sqlite_conn.cursor()
    
    tables = get_all_tables(conn)
    total_rows = 0
    
    for table_name in tables:
        try:
            # PostgreSQL에서 데이터 가져오기
            pg_cursor = conn.cursor(cursor_factory=RealDictCursor)
            pg_cursor.execute(f'SELECT * FROM {table_name} ORDER BY id')
            rows = pg_cursor.fetchall()
            pg_cursor.close()
            
            if not rows:
                print(f'   ⚠️ {table_name}: 데이터 없음')
                continue
            
            # 테이블 스키마 가져오기
            pg_cursor = conn.cursor()
            pg_cursor.execute(f"""
                SELECT column_name, data_type 
                FROM information_schema.columns 
                WHERE table_name = '{table_name}'
                ORDER BY ordinal_position
            """)
            columns = pg_cursor.fetchall()
            pg_cursor.close()
            
            # SQLite 테이블 생성 (간단한 버전)
            column_defs = []
            for col_name, col_type in columns:
                if 'int' in col_type.lower():
                    column_defs.append(f'{col_name} INTEGER')
                elif 'text' in col_type.lower() or 'varchar' in col_type.lower():
                    column_defs.append(f'{col_name} TEXT')
                elif 'timestamp' in col_type.lower() or 'date' in col_type.lower():
                    column_defs.append(f'{col_name} TEXT')
                else:
                    column_defs.append(f'{col_name} TEXT')
            
            # 기존 테이블 삭제
            sqlite_cursor.execute(f'DROP TABLE IF EXISTS {table_name}')
            
            # 테이블 생성
            create_sql = f'CREATE TABLE {table_name} ({", ".join(column_defs)})'
            sqlite_cursor.execute(create_sql)
            
            # 데이터 삽입
            if rows:
                col_names = list(rows[0].keys())
                placeholders = ','.join(['?' for _ in col_names])
                insert_sql = f'INSERT INTO {table_name} ({",".join(col_names)}) VALUES ({placeholders})'
                
                for row in rows:
                    values = []
                    for col in col_names:
                        val = dict(row).get(col)
                        if isinstance(val, datetime):
                            val = val.isoformat()
                        values.append(val)
                    sqlite_cursor.execute(insert_sql, values)
            
            sqlite_conn.commit()
            print(f'   ✅ {table_name}: {len(rows)}건 복사 완료')
            total_rows += len(rows)
        except Exception as e:
            print(f'   ❌ {table_name}: 오류 - {e}')
            import traceback
            traceback.print_exc()
    
    sqlite_conn.close()
    print(f'\n✅ 총 {total_rows}건의 데이터가 {output_db}에 저장되었습니다.')
    return total_rows

def main():
    print('=' * 60)
    print('배포된 PostgreSQL 데이터베이스 내보내기')
    print('=' * 60)
    
    # 데이터베이스 연결
    conn = connect_to_production_db()
    
    try:
        # 테이블 목록 가져오기
        tables = get_all_tables(conn)
        print(f'\n📋 발견된 테이블: {len(tables)}개')
        for table in tables:
            print(f'   - {table}')
        
        # 배포된 데이터를 로컬 data.db로 복사 (로컬 개발 환경과 동일하게)
        print('\n📦 배포된 데이터를 로컬 data.db로 복사 중...')
        print('   (로컬 서버 실행 시 배포된 상태와 동일하게 보이도록)')
        copy_to_local_sqlite(conn)
        
        print('\n✅ 완료! 이제 로컬에서 python app.py 실행하면 배포된 데이터를 볼 수 있습니다.')
    
    finally:
        conn.close()
        print('\n✅ 작업 완료!')

if __name__ == '__main__':
    main()

