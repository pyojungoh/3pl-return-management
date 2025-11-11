"""
PostgreSQL 데이터베이스 모델 (Supabase용)
SQLite에서 PostgreSQL로 전환
"""
import os
import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import datetime
from typing import Optional, List, Dict

# 데이터베이스 연결 문자열
DATABASE_URL = os.environ.get('DATABASE_URL')

# DATABASE_URL이 없으면 SQLite 사용 (호환성)
USE_POSTGRESQL = bool(DATABASE_URL)

def get_db_connection():
    """데이터베이스 연결 가져오기"""
    if USE_POSTGRESQL:
        # PostgreSQL 사용
        if not DATABASE_URL:
            raise ValueError("DATABASE_URL 환경 변수가 설정되지 않았습니다.")
        conn = psycopg2.connect(DATABASE_URL)
        return conn
    else:
        # SQLite 사용 (기존 방식)
        import sqlite3
        # ... 기존 SQLite 코드 ...

def init_db():
    """데이터베이스 초기화 (테이블 생성)"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        if USE_POSTGRESQL:
            # PostgreSQL 테이블 생성
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS companies (
                    id SERIAL PRIMARY KEY,
                    company_name TEXT NOT NULL,
                    username TEXT NOT NULL UNIQUE,
                    password TEXT NOT NULL,
                    role TEXT NOT NULL DEFAULT '화주사',
                    business_number TEXT,
                    business_name TEXT,
                    business_address TEXT,
                    business_tel TEXT,
                    business_email TEXT,
                    business_certificate_url TEXT,
                    last_login TIMESTAMP,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS returns (
                    id SERIAL PRIMARY KEY,
                    return_date TEXT,
                    company_name TEXT NOT NULL,
                    product TEXT,
                    customer_name TEXT NOT NULL,
                    tracking_number TEXT NOT NULL,
                    return_type TEXT,
                    stock_status TEXT,
                    inspection TEXT,
                    completed TEXT,
                    memo TEXT,
                    photo_links TEXT,
                    other_courier TEXT,
                    shipping_fee TEXT,
                    client_request TEXT,
                    client_confirmed TEXT,
                    month TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(customer_name, tracking_number, month)
                )
            ''')
            
            # 인덱스 생성
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_returns_company 
                ON returns(company_name, month)
            ''')
            
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_returns_tracking 
                ON returns(tracking_number)
            ''')
        else:
            # SQLite 테이블 생성 (기존 코드)
            # ... 기존 SQLite 코드 ...
        
        conn.commit()
        print("✅ 데이터베이스 초기화 완료")
    
    except Exception as e:
        print(f"❌ 데이터베이스 초기화 오류: {e}")
        conn.rollback()
    finally:
        cursor.close()
        conn.close()

def get_company_by_username(username: str) -> Optional[Dict]:
    """화주사 계정 조회"""
    conn = get_db_connection()
    
    if USE_POSTGRESQL:
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        try:
            cursor.execute('SELECT * FROM companies WHERE username = %s', (username,))
            row = cursor.fetchone()
            return dict(row) if row else None
        finally:
            cursor.close()
            conn.close()
    else:
        # SQLite 코드 (기존)
        # ... 기존 SQLite 코드 ...

# 주의: 모든 함수에서 USE_POSTGRESQL에 따라 분기 처리 필요
# SQLite: ? 플레이스홀더
# PostgreSQL: %s 플레이스홀더

