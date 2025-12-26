/**
 * Google Forms 질문 ID 확인 스크립트
 * 
 * 이 스크립트를 실행하면 Google Forms의 모든 질문 ID를 확인할 수 있습니다.
 */

function getFormQuestionIds() {
  try {
    // 현재 열려있는 Google Forms 가져오기
    const form = FormApp.getActiveForm();
    
    if (!form) {
      SpreadsheetApp.getUi().alert('Google Forms를 열어주세요.');
      return;
    }
    
    const items = form.getItems();
    let result = '📋 Google Forms 질문 ID 목록\n\n';
    
    items.forEach((item, index) => {
      const title = item.getTitle();
      const id = item.getId();
      const type = item.getType().toString();
      
      // 질문 ID를 entry. 형식으로 변환
      // Google Forms의 내부 ID를 entry. 형식으로 변환하는 방법
      // 참고: 실제 entry ID는 URL에서 확인하는 것이 가장 정확합니다
      
      result += `${index + 1}. ${title}\n`;
      result += `   타입: ${type}\n`;
      result += `   ID: ${id}\n`;
      result += `   (실제 entry ID는 URL에서 확인하세요)\n\n`;
    });
    
    result += '\n💡 참고:\n';
    result += '실제 entry.숫자 형식의 ID는 Google Forms URL이나\n';
    result += '미리 채워진 링크에서 확인할 수 있습니다.\n';
    result += '\n확인 방법:\n';
    result += '1. 질문을 클릭하고 URL 확인\n';
    result += '2. 미리보기 → 미리 채워진 링크 가져오기\n';
    result += '3. 생성된 URL에서 entry.숫자 확인';
    
    SpreadsheetApp.getUi().alert(result);
    
    // 콘솔에도 출력
    console.log(result);
    
  } catch (error) {
    console.error('질문 ID 확인 오류:', error);
    SpreadsheetApp.getUi().alert('오류 발생: ' + error.message);
  }
}

/**
 * Google Forms의 실제 entry ID를 URL에서 추출하는 방법 안내
 */
function showHowToGetEntryIds() {
  const guide = `
📖 Google Forms 질문 ID (entry.숫자) 확인 방법

방법 1: 질문 클릭 후 URL 확인
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
1. Google Forms 편집 화면에서 질문을 클릭
2. 브라우저 주소창의 URL 확인
3. URL 끝에 #response=entry.419411235 같은 부분이 있음
   → entry.419411235가 질문 ID

방법 2: 미리 채워진 링크 사용 (가장 정확)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
1. Google Forms 편집 화면에서
   오른쪽 상단 "미리보기" 아이콘 클릭
   
2. 미리보기 화면에서
   오른쪽 상단 "..." 메뉴 클릭
   → "미리 채워진 링크 가져오기" 선택
   
3. 각 질문에 테스트 값 입력
   예: 파레트 ID에 "TEST001" 입력
   
4. "링크 가져오기" 버튼 클릭
   
5. 생성된 URL 확인:
   https://docs.google.com/forms/d/e/.../viewform?usp=pp_url
   &entry.419411235=TEST001
   &entry.427884801=보관종료
   &entry.211034502=화주사명
   &entry.306824944=품목명
   
   → entry.419411235 = 파레트 ID 질문
   → entry.427884801 = 작업 유형 질문
   → entry.211034502 = 화주사 질문
   → entry.306824944 = 품목명 질문

방법 3: 기존 코드에서 확인
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
qrcod.js 파일을 보면:
  entry.419411235 = 파레트 ID
  entry.427884801 = 작업 유형
  entry.2110345042 = 화주사
  entry.306824944 = 품목명

이미 사용 중인 ID들을 확인할 수 있습니다.
  `;
  
  SpreadsheetApp.getUi().alert(guide);
  console.log(guide);
}

