"""
Google Sheets 데이터 간단히 읽어오기
인증 없이 공개된 시트만 읽을 수 있습니다.
"""
import json
import urllib.request
import urllib.parse

# 스프레드시트 ID
SPREADSHEET_ID = '1utFJtDnIzJHpCMKu1WJkU8HR8SH1TB76cK9flw9jTuU'
SHEET_NAME = '2025년11월'  # 시트 이름

def read_google_sheets_public():
    """
    공개된 Google Sheets 데이터 읽기 (인증 불필요)
    """
    try:
        # Google Sheets를 CSV 형식으로 export하는 URL
        url = f'https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}/gviz/tq?tqx=out:json&sheet={urllib.parse.quote(SHEET_NAME)}'
        
        print(f"데이터 읽어오는 중...")
        print(f"URL: {url}\n")
        
        # 데이터 가져오기
        with urllib.request.urlopen(url) as response:
            data = response.read().decode('utf-8')
            
            # 응답이 JSONP 형식이므로 JSON 부분만 추출
            json_str = data.split('(', 1)[1].rsplit(')', 1)[0]
            json_data = json.loads(json_str)
            
            # 데이터 파싱
            rows = json_data['table']['rows']
            cols = json_data['table']['cols']
            
            print(f"✅ 총 {len(rows)}행의 데이터를 읽었습니다.\n")
            
            # 컬럼 이름
            print("=" * 100)
            print("컬럼 정보:")
            for i, col in enumerate(cols):
                label = col.get('label', f'컬럼{i+1}')
                print(f"  [{i}] {label}")
            
            print("\n" + "=" * 100)
            print("데이터 (처음 10행):\n")
            
            # 데이터 출력 (처음 10행)
            for idx, row in enumerate(rows[:10]):
                print(f"--- 행 {idx + 1} ---")
                cells = row.get('c', [])
                for i, cell in enumerate(cells):
                    if cell:
                        value = cell.get('v', '')
                        formatted = cell.get('f', value)
                        col_label = cols[i].get('label', f'컬럼{i+1}')
                        if value:
                            print(f"  {col_label}: {formatted}")
                print()
            
            # 전체 데이터를 파일로 저장
            output_data = []
            for row in rows:
                row_data = {}
                cells = row.get('c', [])
                for i, cell in enumerate(cells):
                    col_label = cols[i].get('label', f'컬럼{i+1}')
                    if cell:
                        value = cell.get('v', '')
                        formatted = cell.get('f', value)
                        row_data[col_label] = formatted
                    else:
                        row_data[col_label] = ''
                output_data.append(row_data)
            
            # JSON 파일로 저장
            with open('sheets_data.json', 'w', encoding='utf-8') as f:
                json.dump(output_data, f, ensure_ascii=False, indent=2)
            
            print("=" * 100)
            print(f"✅ 전체 데이터를 'sheets_data.json' 파일로 저장했습니다.")
            print(f"   총 {len(output_data)}건의 데이터")
            
            return output_data
            
    except urllib.error.HTTPError as e:
        if e.code == 403:
            print("❌ 접근 권한이 없습니다.")
            print("   해당 Google Sheets가 '링크가 있는 모든 사용자'로 공유되어 있는지 확인하세요.")
        else:
            print(f"❌ HTTP 에러: {e.code} - {e.reason}")
        return None
    except Exception as e:
        print(f"❌ 에러 발생: {e}")
        return None


if __name__ == '__main__':
    print("=" * 100)
    print("Google Sheets 데이터 읽기")
    print("=" * 100)
    print()
    
    data = read_google_sheets_public()
    
    if data:
        print(f"\n✅ 성공: sheets_data.json 파일을 확인하세요!")
    else:
        print(f"\n❌ 실패: 시트가 공개되어 있지 않으면 Google API 인증이 필요합니다.")
        print("\n📌 해결 방법:")
        print("   1. Google Sheets를 '링크가 있는 모든 사용자' 권한으로 공유")
        print("   2. 또는 Google Cloud에서 서비스 계정 생성 후 인증 파일 사용")





