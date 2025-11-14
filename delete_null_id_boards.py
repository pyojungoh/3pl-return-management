#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
ID가 null인 게시글 삭제 스크립트
"""
import sqlite3

def delete_null_id_boards():
    """ID가 null인 게시글 삭제"""
    conn = sqlite3.connect('data.db')
    cursor = conn.cursor()
    
    try:
        # ID가 null인 게시글 조회
        cursor.execute('SELECT id, title FROM boards WHERE id IS NULL')
        null_id_boards = cursor.fetchall()
        
        if not null_id_boards:
            print("[OK] ID가 null인 게시글이 없습니다.")
            return
        
        print(f"[WARNING] ID가 null인 게시글 {len(null_id_boards)}개를 찾았습니다:")
        for board in null_id_boards:
            print(f"  - ID: {board[0]}, 제목: {board[1]}")
        
        # 자동으로 삭제 (비대화형 환경 대응)
        print("\n[INFO] ID가 null인 게시글들을 자동으로 삭제합니다...")
        
        # ID가 null인 게시글 삭제
        cursor.execute('DELETE FROM boards WHERE id IS NULL')
        deleted_count = cursor.rowcount
        conn.commit()
        
        print(f"[OK] {deleted_count}개의 게시글이 삭제되었습니다.")
        
        # 삭제 후 확인
        cursor.execute('SELECT COUNT(*) FROM boards WHERE id IS NULL')
        remaining = cursor.fetchone()[0]
        if remaining == 0:
            print("[OK] 모든 null ID 게시글이 삭제되었습니다.")
        else:
            print(f"[WARNING] 아직 {remaining}개의 null ID 게시글이 남아있습니다.")
            
    except Exception as e:
        print(f"[ERROR] 오류 발생: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == '__main__':
    delete_null_id_boards()

