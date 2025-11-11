// ===== Code.gs 파일에 넣을 코드 =====
// 버전: v77-optimized (속도 개선)

// 스프레드시트 설정
const SPREADSHEET_ID = '1utFJtDnIzJHpCMKu1WJkU8HR8SH1TB76cK9flw9jTuU';

// 드라이브 폴더 설정 (월별 사진 저장용)
const DRIVE_FOLDER_NAME = '반품내역';

// 웹앱 메인 함수
function doGet(e) {
  try {
    // 1. ?api=1 파라미터가 있으면 JSON 반환 (API 호출용)
    if (e && e.parameter && e.parameter.api == '1') {
      return getAllReturnsWithPhotos();
    }
    
    // 2. ?page=admin → 관리자용 사진 업로드 폼
    if (e && e.parameter && e.parameter.page == 'admin') {
      return HtmlService.createTemplateFromFile('index').evaluate()
        .setTitle('반품교환 등록')
        .setXFrameOptionsMode(HtmlService.XFrameOptionsMode.ALLOWALL);
    }
    
    // 3. 기본: 화주사 대시보드 (로그인 폼 포함)
    return HtmlService.createHtmlOutputFromFile('dashboard')
      .setTitle('화주사 반품 관리')
      .setXFrameOptionsMode(HtmlService.XFrameOptionsMode.ALLOWALL);
      
  } catch (error) {
    // 에러 발생 시 에러 페이지 표시
    return HtmlService.createHtmlOutput(
      '<h1>오류 발생</h1>' +
      '<p>페이지를 로드하는 중 오류가 발생했습니다.</p>' +
      '<p>에러 메시지: ' + error.toString() + '</p>' +
      '<p><a href="?">다시 시도</a></p>' +
      '<p><a href="?page=admin">관리자 페이지로 이동</a></p>'
    ).setTitle('오류');
  }
}

// HTML 파일 include 함수
function include(filename) {
  return HtmlService.createHtmlOutputFromFile(filename).getContent();
}

// 월별 시트명 생성 함수
function getSheetName(year, month) {
  return `${year}년${month}월`;
}

// 시트 찾기 함수 (띄어쓰기, 대소문자 무시)
function findSheet(ss, targetSheetName) {
  const sheets = ss.getSheets();
  
  // 정확한 이름으로 먼저 찾기
  let sheet = ss.getSheetByName(targetSheetName);
  if (sheet) {
    return sheet;
  }
  
  // 띄어쓰기와 대소문자 무시하고 찾기
  const normalizedTarget = targetSheetName.replace(/\s/g, '').toLowerCase();
  
  for (let i = 0; i < sheets.length; i++) {
    const currentSheet = sheets[i];
    const currentName = currentSheet.getName().replace(/\s/g, '').toLowerCase();
    
    if (currentName === normalizedTarget) {
      return currentSheet;
    }
  }
  
  return null;
}

// 현재 월의 시트명 가져오기
function getCurrentSheetName() {
  const today = new Date();
  const year = today.getFullYear();
  const month = today.getMonth() + 1;
  return getSheetName(year, month);
}

// 사용 가능한 시트 목록 가져오기 (년월 형태의 시트만)
function getAvailableSheets() {
  try {
    console.log('getAvailableSheets 함수 시작');
    
    const ss = SpreadsheetApp.openById(SPREADSHEET_ID);
    const sheets = ss.getSheets();
    const availableSheets = [];
    
    console.log('전체 시트 개수:', sheets.length);
    
    sheets.forEach(sheet => {
      const sheetName = sheet.getName();
      console.log('시트명 확인:', sheetName);
      
      // 년월 패턴 (예: 2025년7월, 2025년 7월, 2025년6월 등)
      if (sheetName.match(/\d{4}년\s*\d{1,2}월/)) {
        availableSheets.push(sheetName);
        console.log('년월 시트 추가:', sheetName);
      }
    });
    
    console.log('찾은 년월 시트들:', availableSheets);
    
    // 최신순으로 정렬
    availableSheets.sort((a, b) => {
      const aMatch = a.match(/(\d{4})년\s*(\d{1,2})월/);
      const bMatch = b.match(/(\d{4})년\s*(\d{1,2})월/);
      
      if (aMatch && bMatch) {
        const aYear = parseInt(aMatch[1]);
        const aMonth = parseInt(aMatch[2]);
        const bYear = parseInt(bMatch[1]);
        const bMonth = parseInt(bMatch[2]);
        
        if (aYear !== bYear) {
          return bYear - aYear; // 년도 내림차순
        }
        return bMonth - aMonth; // 월 내림차순
      }
      return 0;
    });
    
    console.log('정렬된 시트 목록:', availableSheets);
    
    return availableSheets;
    
  } catch (error) {
    console.error('사용 가능한 시트 목록 가져오기 오류:', error);
    return ['2025년7월', '2025년6월', '2025년5월']; // 테스트용 기본값
  }
}

// 기존 행의 사진 링크만 업데이트 (하이퍼링크 방식)
function addReturnData(data) {
  try {
    // 중복실행 방지
    PropertiesService.getScriptProperties().setProperty('isRunning', 'true');
    
    console.log('🔍 기존 행 업데이트 시작:', JSON.stringify(data));
    
    const ss = SpreadsheetApp.openById(SPREADSHEET_ID);
    
    // 시트명 결정 (data.selectedMonth가 있으면 사용, 없으면 현재 월)
    let sheetName;
    if (data.selectedMonth) {
      sheetName = data.selectedMonth;
    } else {
      sheetName = getCurrentSheetName();
    }
    
    console.log('📋 대상 시트명:', sheetName);
    
    // 시트 찾기
    const sheet = findSheet(ss, sheetName);
    if (!sheet) {
      console.log('❌ 시트를 찾을 수 없습니다:', sheetName);
      PropertiesService.getScriptProperties().deleteProperty('isRunning');
      return `${sheetName} 시트를 찾을 수 없습니다.`;
    }
    
    console.log('✅ 시트 찾기 성공:', sheet.getName());
    
    const allData = sheet.getDataRange().getValues();
    console.log('📊 시트 전체 데이터 행 수:', allData.length);
    
    // 헤더 확인 (2행)
    if (allData.length > 1) {
      console.log('📑 헤더 (2행):', allData[1]);
    }
    
    // 검색할 고객명과 송장번호 로그
    console.log('🔎 검색 조건 - 고객명:', data.customer, '송장번호:', data.trackingNumber);
    
    // 헤더는 2행(인덱스 1), 데이터는 3행(인덱스 2)부터 검색
    for (let i = 2; i < allData.length; i++) {
      const rowData = allData[i];
      const rowCustomer = rowData[3] ? rowData[3].toString().trim() : ''; // D열: 고객명
      const rowTracking = rowData[4] ? rowData[4].toString().trim() : ''; // E열: 송장번호 (문자열로 변환)
      
      // 각 행 검색 로그 (처음 10개만)
      if (i < 12) {
        console.log(`🔍 ${i+1}행 확인 - 고객명: "${rowCustomer}", 송장번호: "${rowTracking}"`);
      }
      
      // 송장번호도 문자열로 변환해서 비교
      const searchTracking = data.trackingNumber.toString().trim();
      
      // 고객명과 송장번호가 일치하는 행 찾기
      if (rowCustomer === data.customer && rowTracking === searchTracking) {
        const rowIndex = i + 1; // 스프레드시트 행 번호 (1부터 시작)
        
        console.log('🎯 일치하는 행 발견:', rowIndex, '행');
        console.log('📸 업데이트할 사진 링크:', data.photoLinks);
        
        // 시트의 실제 최대 열 확인
        const lastColumn = sheet.getLastColumn();
        console.log('📐 시트 최대 열 수:', lastColumn);
        
        // K열이 없으면 확장
        if (lastColumn < 11) {
          console.log('🔧 K열이 없어서 시트 확장 중...');
          // K열 헤더 추가 (2행에)
          sheet.getRange(2, 11).setValue('사진');
        }
        
        // 사진 링크들을 파싱해서 하이퍼링크 생성
        if (data.photoLinks) {
          console.log('🖼️ 사진 링크 처리 시작');
          
          const photoEntries = data.photoLinks.split('\n');
          console.log('📄 사진 항목들:', photoEntries);
          
          const richTextValues = [];
          
          photoEntries.forEach((entry, index) => {
            if (entry.trim()) {
              const parts = entry.split(': ');
              if (parts.length === 2) {
                const linkText = parts[0]; // 사진1, 사진2 등
                const linkUrl = parts[1];  // 실제 URL
                
                console.log(`🔗 링크 ${index + 1}: "${linkText}" -> "${linkUrl}"`);
                
                // RichTextValue로 하이퍼링크 생성
                const richText = SpreadsheetApp.newRichTextValue()
                  .setText(linkText)
                  .setLinkUrl(linkUrl)
                  .build();
                  
                richTextValues.push(richText);
              }
            }
          });
          
          console.log('📝 생성된 리치텍스트 개수:', richTextValues.length);
          
          // K열(11번째)에 여러 하이퍼링크를 줄바꿈으로 구분해서 삽입
          if (richTextValues.length > 0) {
            let combinedText = '';
            const textBuilder = SpreadsheetApp.newRichTextValue();
            
            richTextValues.forEach((richText, index) => {
              if (index > 0) {
                combinedText += '\n';
              }
              combinedText += richText.getText();
            });
            
            console.log('📋 최종 텍스트:', combinedText);
            
            // 전체 텍스트 설정
            textBuilder.setText(combinedText);
            
            // 각 링크별로 URL 설정
            let currentPos = 0;
            richTextValues.forEach((richText, index) => {
              const text = richText.getText();
              const url = richText.getLinkUrl();
              
              if (url) {
                textBuilder.setLinkUrl(currentPos, currentPos + text.length, url);
                console.log(`🔗 링크 설정: 위치 ${currentPos}-${currentPos + text.length}, URL: ${url}`);
              }
              
              currentPos += text.length + (index < richTextValues.length - 1 ? 1 : 0); // 줄바꿈 고려
            });
            
            // K열에 실제 데이터 입력
            console.log(`💾 K열(${rowIndex}행, 11열)에 데이터 입력 중...`);
            sheet.getRange(rowIndex, 11).setRichTextValue(textBuilder.build());
            console.log('✅ K열 데이터 입력 완료');
          }
        } else {
          console.log('⚠️ 사진 링크가 없습니다');
        }
        
        console.log('🎉 사진 링크 업데이트 완료');
        
        // 중복실행 방지 해제
        PropertiesService.getScriptProperties().deleteProperty('isRunning');
        
        return '사진 링크 업데이트 완료!';
      }
    }
    
    // 일치하는 행을 찾지 못한 경우
    console.log('❌ 일치하는 행을 찾지 못했습니다');
    console.log('🔍 검색 조건 재확인:');
    console.log('   - 찾는 고객명:', `"${data.customer}"`);
    console.log('   - 찾는 송장번호:', `"${data.trackingNumber.toString()}"`);
    console.log('   - 검색한 시트:', sheetName);
    console.log('   - 총 데이터 행 수:', allData.length - 2, '행 (헤더 제외)');
    
    // 19행 데이터 특별히 확인
    if (allData.length > 19) {
      const row19 = allData[18]; // 19행은 인덱스 18
      console.log('🔍 19행 특별 확인:');
      console.log('   - 고객명:', `"${row19[3] ? row19[3].toString().trim() : ''}"`);
      console.log('   - 송장번호:', `"${row19[4] ? row19[4].toString().trim() : ''}"`);
    }
    
    // 중복실행 방지 해제
    PropertiesService.getScriptProperties().deleteProperty('isRunning');
    
    return '해당 데이터를 찾을 수 없습니다. 고객명과 송장번호를 다시 확인해주세요.';
    
  } catch (error) {
    // 중복실행 방지 해제
    PropertiesService.getScriptProperties().deleteProperty('isRunning');
    
    console.error('💥 업데이트 오류:', error);
    console.error('💥 오류 상세:', error.toString());
    console.error('💥 스택 트레이스:', error.stack);
    return '오류 발생: ' + error.toString();
  }
}

// 구글 드라이브에 이미지 업로드 (월별 폴더)
function uploadImages(imageDataList, trackingNumber) {
  try {
    // 입력값 검증
    if (!imageDataList || !Array.isArray(imageDataList) || imageDataList.length === 0) {
      console.log('이미지 데이터가 없습니다.');
      return '';
    }
    
    if (!trackingNumber) {
      console.log('송장번호가 없습니다.');
      return '';
    }
    
    console.log('📸 이미지 업로드 시작:', imageDataList.length, '개');
    
    // 메인 폴더 찾기 또는 생성
    let mainFolder;
    const mainFolders = DriveApp.getFoldersByName(DRIVE_FOLDER_NAME);
    if (mainFolders.hasNext()) {
      mainFolder = mainFolders.next();
      console.log('✅ 메인 폴더 찾기 성공:', DRIVE_FOLDER_NAME);
    } else {
      console.log('📁 메인 폴더 생성 중:', DRIVE_FOLDER_NAME);
      mainFolder = DriveApp.createFolder(DRIVE_FOLDER_NAME);
      console.log('✅ 메인 폴더 생성 완료');
    }
    
    // 현재 월 폴더 찾기 또는 생성
    const today = new Date();
    const yearMonth = Utilities.formatDate(today, 'Asia/Seoul', 'yyyy년MM월');
    console.log('📅 대상 월 폴더:', yearMonth);
    
    let monthFolder;
    const monthFolders = mainFolder.getFoldersByName(yearMonth);
    if (monthFolders.hasNext()) {
      monthFolder = monthFolders.next();
      console.log('✅ 월 폴더 찾기 성공:', yearMonth);
    } else {
      console.log('📁 월 폴더 생성 중:', yearMonth);
      try {
        monthFolder = mainFolder.createFolder(yearMonth);
        console.log('✅ 월 폴더 생성 완료:', yearMonth);
      } catch (folderError) {
        console.error('❌ 월 폴더 생성 실패:', folderError);
        throw new Error('월 폴더 생성 실패: ' + folderError.toString());
      }
    }
    
    const photoTexts = [];
    const timestamp = Utilities.formatDate(new Date(), 'Asia/Seoul', 'yyyyMMdd_HHmmss');
    
    console.log('🖼️ 개별 이미지 업로드 시작...');
    
    // 모든 이미지 업로드
    for (let i = 0; i < imageDataList.length; i++) {
      try {
        const imageData = imageDataList[i];
        
        if (!imageData || typeof imageData !== 'string') {
          console.log(`⚠️ 이미지 ${i + 1} 데이터가 유효하지 않습니다.`);
          continue;
        }
        
        console.log(`📤 이미지 ${i + 1} 업로드 중...`);
        
        // Base64 데이터에서 파일 생성
        const base64Data = imageData.includes(',') ? imageData.split(',')[1] : imageData;
        const blob = Utilities.newBlob(
          Utilities.base64Decode(base64Data),
          'image/jpeg',
          `${trackingNumber}_${timestamp}_${i + 1}.jpg`
        );
        
        // 드라이브에 업로드
        const file = monthFolder.createFile(blob);
        
        // 공유 설정 (누구나 링크로 볼 수 있도록)
        file.setSharing(DriveApp.Access.ANYONE_WITH_LINK, DriveApp.Permission.VIEW);
        
        // 하이퍼링크 형태로 텍스트 생성
        const linkText = `사진${i + 1}`;
        const linkUrl = file.getUrl();
        photoTexts.push(`${linkText}: ${linkUrl}`);
        
        console.log(`✅ 이미지 ${i + 1} 업로드 완료:`, file.getName());
        console.log(`🔗 링크:`, linkUrl);
        
      } catch (error) {
        console.error(`❌ 이미지 ${i + 1} 업로드 오류:`, error);
        // 개별 이미지 실패해도 계속 진행
      }
    }
    
    console.log('🎉 모든 이미지 업로드 완료:', photoTexts.length, '개');
    console.log('📝 생성된 링크들:', photoTexts);
    
    if (photoTexts.length === 0) {
      throw new Error('업로드된 이미지가 없습니다.');
    }
    
    // 줄바꿈으로 구분된 텍스트 반환
    return photoTexts.join('\n');
    
  } catch (error) {
    console.error('💥 이미지 업로드 전체 오류:', error);
    console.error('💥 오류 상세:', error.toString());
    throw error; // 오류를 다시 던져서 HTML에서 처리하도록
  }
}

// 고객명과 송장번호 뒤4자리로 기존 데이터 찾기 (월별 시트 지원)
function findDataByCustomerAndLast4(searchText, selectedMonth) {
  try {
    const ss = SpreadsheetApp.openById(SPREADSHEET_ID);
    
    // 시트명 결정
    let sheetName;
    if (selectedMonth) {
      sheetName = selectedMonth;
    } else {
      sheetName = getCurrentSheetName();
    }
    
    console.log('검색 대상 시트:', sheetName);
    
    // 시트 찾기
    const sheet = findSheet(ss, sheetName);
    if (!sheet) {
      console.log('시트를 찾을 수 없습니다:', sheetName);
      return null;
    }
    
    const data = sheet.getDataRange().getValues();
    
    // 검색어에서 고객명과 뒤4자리 분리
    const parts = searchText.trim().split(' ');
    if (parts.length < 2) {
      return null;
    }
    
    const customerName = parts.slice(0, -1).join(' '); // 마지막 부분 제외한 나머지
    const last4Digits = parts[parts.length - 1]; // 마지막 부분 (뒤4자리)
    
    // 헤더는 2행(인덱스 1), 데이터는 3행(인덱스 2)부터 검색
    for (let i = 2; i < data.length; i++) {
      const rowCustomer = data[i][3] ? data[i][3].toString().trim() : ''; // D열: 고객명
      const rowTracking = data[i][4] ? data[i][4].toString() : '';        // E열: 송장번호
      
      // 고객명 일치 확인
      if (rowCustomer === customerName) {
        // 송장번호 뒤4자리 일치 확인
        if (rowTracking.length >= 4 && rowTracking.slice(-4) === last4Digits) {
          return {
            company: data[i][1] || '',      // B열: 화주명
            product: data[i][2] || '',      // C열: 제품
            customer: data[i][3] || '',     // D열: 고객명
            trackingNumber: data[i][4] || '', // E열: 송장번호
            returnType: data[i][5] || '',   // F열: 반품/교환/오배송
            stockStatus: data[i][6] || ''   // G열: 재고상태
          };
        }
      }
    }
    
    return null;
    
  } catch (error) {
    console.error('데이터 찾기 오류:', error);
    return null;
  }
}

// 송장번호 전체로 기존 데이터 찾기 (QR 전용)
function findDataByTrackingNumber(trackingNumber, selectedMonth) {
  try {
    if (!trackingNumber) {
      console.log('⚠️ 송장번호가 비어 있어 검색을 종료합니다.');
      return null;
    }

    const ss = SpreadsheetApp.openById(SPREADSHEET_ID);

    // 시트명 결정
    let sheetName;
    if (selectedMonth) {
      sheetName = selectedMonth;
    } else {
      sheetName = getCurrentSheetName();
    }

    console.log('QR 검색 대상 시트:', sheetName);

    const sheet = findSheet(ss, sheetName);
    if (!sheet) {
      console.log('QR 검색 시트를 찾을 수 없습니다:', sheetName);
      return null;
    }

    const data = sheet.getDataRange().getValues();
    const targetTrackingRaw = trackingNumber.toString().trim();
    const targetTrackingNormalized = targetTrackingRaw.replace(/[\s-]/g, '');

    console.log('QR 검색 송장번호:', targetTrackingRaw, '(정규화:', targetTrackingNormalized + ')');

    for (let i = 2; i < data.length; i++) {
      const rowTrackingRaw = data[i][4] ? data[i][4].toString().trim() : '';
      const rowTrackingNormalized = rowTrackingRaw.replace(/[\s-]/g, '');

      if (!rowTrackingRaw) {
        continue;
      }

      if (rowTrackingRaw === targetTrackingRaw || rowTrackingNormalized === targetTrackingNormalized) {
        console.log('✅ QR 검색 일치 행 발견:', i + 1, '행');
        return {
          company: data[i][1] || '',
          product: data[i][2] || '',
          customer: data[i][3] || '',
          trackingNumber: rowTrackingRaw,
          returnType: data[i][5] || '',
          stockStatus: data[i][6] || ''
        };
      }
    }

    console.log('QR 검색 결과 없음:', targetTrackingRaw);
    return null;

  } catch (error) {
    console.error('QR 송장 검색 오류:', error);
    return null;
  }
}

// 테스트 함수 - 디버깅용
function testPhotoLink() {
  try {
    console.log('=== 사진 링크 테스트 시작 ===');
    
    const testData = {
      customer: "홍길동",
      trackingNumber: "111111111",
      photoLinks: "사진1: https://drive.google.com/test1\n사진2: https://drive.google.com/test2",
      selectedMonth: "2025년6월"
    };
    
    console.log('테스트 데이터:', JSON.stringify(testData));
    
    const result = addReturnData(testData);
    console.log('테스트 결과:', result);
    
    return result;
    
  } catch (error) {
    console.error('테스트 오류:', error);
    return '테스트 실패: ' + error.toString();
  }
}

// 테스트 함수들 유지
function simpleTest() {
  return '연결 성공! 현재 시각: ' + new Date().toLocaleString('ko-KR');
}
function testSpecificData() {
  try {
    console.log('=== 금성교 4840 테스트 시작 ===');
    
    // 실제 데이터로 테스트
    const testData = {
      customer: "금성교",
      trackingNumber: "4840", // 또는 전체 송장번호
      photoLinks: "사진1: https://drive.google.com/test1\n사진2: https://drive.google.com/test2",
      selectedMonth: "2025년7월"
    };
    
    console.log('테스트 데이터:', JSON.stringify(testData));
    
    // 먼저 2025년7월 시트에서 해당 데이터가 있는지 확인
    const searchResult = findDataByCustomerAndLast4("금성교 4840", "2025년7월");
    console.log('검색 결과:', searchResult);
    
    if (searchResult) {
      console.log('데이터 발견됨. 사진 링크 업데이트 시도...');
      testData.trackingNumber = searchResult.trackingNumber; // 전체 송장번호 사용
      
      const result = addReturnData(testData);
      console.log('업데이트 결과:', result);
      
      return result;
    } else {
      return '2025년7월 시트에서 금성교 4840 데이터를 찾을 수 없습니다.';
    }
    
  } catch (error) {
    console.error('특정 데이터 테스트 오류:', error);
    return '테스트 실패: ' + error.toString();
  }
}

// 2025년7월 시트 전체 구조 확인
function check2025July() {
  try {
    console.log('=== 2025년7월 시트 확인 ===');
    
    const ss = SpreadsheetApp.openById(SPREADSHEET_ID);
    const sheet = findSheet(ss, "2025년7월");
    
    if (!sheet) {
      console.log('❌ 2025년7월 시트를 찾을 수 없습니다');
      return '2025년7월 시트를 찾을 수 없습니다';
    }
    
    console.log('✅ 시트 찾기 성공:', sheet.getName());
    console.log('📊 최대 행:', sheet.getLastRow());
    console.log('📊 최대 열:', sheet.getLastColumn());
    
    // 헤더 확인 (2행)
    if (sheet.getLastRow() >= 2) {
      const headers = sheet.getRange(2, 1, 1, Math.max(11, sheet.getLastColumn())).getValues()[0];
      console.log('📑 헤더 (2행):', headers);
      console.log('📑 K열 헤더:', headers[10]);
    }
    
    // 데이터 몇 개 확인
    const dataRows = Math.min(5, sheet.getLastRow() - 2);
    if (dataRows > 0) {
      console.log('📋 데이터 확인 (최대 5행):');
      for (let i = 3; i <= 3 + dataRows - 1; i++) {
        const rowData = sheet.getRange(i, 1, 1, Math.max(11, sheet.getLastColumn())).getValues()[0];
        const customer = rowData[3] || '';
        const tracking = rowData[4] || '';
        console.log(`${i}행: 고객명="${customer}", 송장번호="${tracking}"`);
        
        // 금성교가 있는지 특별히 확인
        if (customer.toString().includes('금성교')) {
          console.log('🎯 금성교 발견!', `전체 데이터:`, rowData);
        }
      }
    }
    
    return '2025년7월 시트 확인 완료';
    
  } catch (error) {
    console.error('2025년7월 시트 확인 오류:', error);
    return '확인 실패: ' + error.toString();
  }
}
// ========== 화주사 로그인 관련 함수 ==========

// 화주사 로그인 함수 (v77-optimized)
function loginClient(username, password) {
  try {
    console.log('로그인 시도:', username);
    
    if (!username || !password) {
      return { success: false, message: '아이디와 비밀번호를 입력해주세요.' };
    }
    
    const ss = SpreadsheetApp.openById(SPREADSHEET_ID);
    const accountSheet = ss.getSheetByName('화주사계정');
    
    if (!accountSheet) {
      console.error('화주사계정 시트를 찾을 수 없습니다.');
      return { success: false, message: '화주사계정 시트가 없습니다. 관리자에게 문의하세요.' };
    }
    
    const data = accountSheet.getDataRange().getValues();
    console.log('화주사계정 시트 데이터 행 수:', data.length);
    
    // 헤더 제외하고 검색 (2행부터, 인덱스 1부터)
    for (let i = 1; i < data.length; i++) {
      const row = data[i];
      const company = row[0] ? row[0].toString().trim() : '';
      const loginId = row[1] ? row[1].toString().trim() : '';
      const loginPw = row[2] ? row[2].toString().trim() : '';
      const role = row[3] ? row[3].toString().trim() : '';
      
      console.log(`행 ${i + 1} 확인:`, { company, loginId: loginId ? '있음' : '없음', role });
      
      if (loginId === username && loginPw === password) {
        console.log('로그인 성공:', company, '권한:', role);
        return {
          success: true,
          company: company,
          role: role,
          username: username
        };
      }
    }
    
    console.log('로그인 실패: 아이디 또는 비밀번호 불일치');
    return { success: false, message: '아이디 또는 비밀번호가 일치하지 않습니다.' };
    
  } catch (error) {
    console.error('로그인 오류:', error);
    console.error('오류 상세:', error.toString());
    console.error('스택 트레이스:', error.stack);
    return { success: false, message: '로그인 중 오류가 발생했습니다: ' + error.toString() };
  }
}

// 화주사별 반품 데이터 조회
function getReturnsByCompany(company, selectedMonth, role) {
  try {
    console.log('데이터 조회:', company, selectedMonth, '권한:', role);
    
    const ss = SpreadsheetApp.openById(SPREADSHEET_ID);
    
    // 시트명 결정
    const sheetName = selectedMonth || getCurrentSheetName();
    const sheet = findSheet(ss, sheetName);
    
    if (!sheet) {
      return { success: false, message: `${sheetName} 시트를 찾을 수 없습니다.` };
    }
    
    const lastRow = sheet.getLastRow();
    if (lastRow < 3) {
      return { success: true, data: [], message: '데이터가 없습니다.' };
    }
    
    // A~O열 (15개) 읽기 (다른외부택배사, 배송비, 화주사요청, 화주사확인완료 포함)
    const lastCol = Math.max(15, sheet.getLastColumn());
    const data = sheet.getRange(3, 1, lastRow - 2, lastCol).getValues();
    const richTextData = sheet.getRange(3, 1, lastRow - 2, lastCol).getRichTextValues();
    
    const results = [];
    
    for (let i = 0; i < data.length; i++) {
      const rowCompany = data[i][1] ? data[i][1].toString().trim() : '';
      const customerName = data[i][3] ? data[i][3].toString().trim() : ''; // D열: 고객명
      const trackingNumber = data[i][4] ? data[i][4].toString().trim() : ''; // E열: 송장번호
      
      // 유효한 반품 데이터인지 확인
      // 1. 고객명이 있어야 함
      // 2. 송장번호가 있어야 함
      // 3. 송장번호가 숫자여야 함 (문자가 들어있으면 유효하지 않음)
      const hasCustomerName = customerName && customerName.length > 0;
      const hasTrackingNumber = trackingNumber && trackingNumber.length > 0;
      
      // 송장번호가 숫자인지 확인 (숫자, 하이픈, 공백만 허용)
      const isNumericTracking = hasTrackingNumber && /^[\d\s\-]+$/.test(trackingNumber);
      
      const isValidData = hasCustomerName && isNumericTracking;
      
      if (!isValidData) {
        // 유효하지 않은 데이터 건너뛰기 (빈 행, 헤더, 공지사항 등)
        continue;
      }
      
      // D열(권한)이 "관리자"면 모든 데이터 보기, 아니면 자기 회사 데이터만 보기
      const isAdmin = (role && role.toString().trim() === '관리자');
      const shouldInclude = isAdmin || (rowCompany === company);
      
      if (shouldInclude) {
        // 사진 링크 추출
        let photoLinks = '';
        const photoCell = richTextData[i][10]; // K열
        if (photoCell) {
          const runs = photoCell.getRuns();
          const texts = [];
          if (runs && runs.length > 0) {
            runs.forEach(run => {
              const text = photoCell.getText().substring(run.getStartIndex(), run.getEndIndex());
              const url = run.getLinkUrl();
              if (url) texts.push({ text: text, url: url });
            });
            photoLinks = texts;
          }
        }
        
        results.push({
          rowIndex: i + 3, // 실제 시트 행 번호
          '반품 접수일': data[i][0] || '',
          '화주명': data[i][1] || '',
          '제품': data[i][2] || '',
          '고객명': data[i][3] || '',
          '송장번호': data[i][4] || '',
          '반품/교환/오배송': data[i][5] || '',
          '재고상태': data[i][6] || '',
          '검품유무': data[i][7] || '',
          '처리완료': data[i][8] || '',
          '비고': data[i][9] || '',
          '사진': photoLinks,
          '다른외부택배사': data[i][11] || '', // L열
          '배송비': data[i][12] || '', // M열
          '화주사요청': data[i][13] || '', // N열
          '화주사확인완료': data[i][14] || '' // O열
        });
      }
    }
    
    // 최신순 정렬 (반품 접수일 기준 내림차순)
    results.sort((a, b) => {
      const dateA = a['반품 접수일'] ? a['반품 접수일'].toString() : '';
      const dateB = b['반품 접수일'] ? b['반품 접수일'].toString() : '';
      
      // 날짜가 없는 경우 맨 아래로
      if (!dateA && dateB) return 1;
      if (dateA && !dateB) return -1;
      if (!dateA && !dateB) return 0;
      
      // 문자열 비교 (숫자 형태면 숫자로, 아니면 문자열로)
      // 날짜 형태 감지 (예: 2025-11-07, 11/7, 7 등)
      const numA = parseFloat(dateA);
      const numB = parseFloat(dateB);
      
      if (!isNaN(numA) && !isNaN(numB)) {
        return numB - numA; // 숫자면 큰 수가 먼저 (최신)
      }
      
      // 문자열이면 역순 정렬 (최신이 위)
      return dateB.localeCompare(dateA);
    });
    
    console.log(`${company} 데이터 ${results.length}건 조회 완료 (최신순 정렬)`);
    return { success: true, data: results, count: results.length };
    
  } catch (error) {
    console.error('데이터 조회 오류:', error);
    return { success: false, message: '데이터 조회 중 오류: ' + error.toString() };
  }
}

// 새 반품 건 추가 (관리자 전용)
function addNewReturn(newReturn, sheetName, managerName) {
  try {
    console.log('새 반품 건 등록:', newReturn, sheetName, '담당자:', managerName);
    
    const ss = SpreadsheetApp.openById(SPREADSHEET_ID);
    const sheet = findSheet(ss, sheetName);
    
    if (!sheet) {
      return { success: false, message: '시트를 찾을 수 없습니다.' };
    }
    
    // 실제 데이터가 있는 마지막 행 찾기
    const lastRow = sheet.getLastRow();
    
    // E열(송장번호) 기준으로 실제 데이터가 있는 마지막 행 찾기
    let actualLastRow = 2; // 헤더 다음부터
    for (let i = lastRow; i >= 3; i--) {
      const trackingValue = sheet.getRange(i, 5).getValue(); // E열: 송장번호
      const customerValue = sheet.getRange(i, 4).getValue(); // D열: 고객명
      
      // 송장번호와 고객명이 있는 행을 찾으면 그게 마지막 데이터 행
      if (trackingValue && customerValue) {
        actualLastRow = i;
        break;
      }
    }
    
    const newRow = actualLastRow + 1;
    
    console.log('시트 getLastRow():', lastRow);
    console.log('실제 데이터 마지막 행:', actualLastRow);
    console.log('새 데이터 추가 행:', newRow);
    
    // 새 행 데이터 (A~L열)
    const rowData = [
      newReturn.returnDate || '',      // A: 반품 접수일
      newReturn.company || '',          // B: 화주명
      newReturn.product || '',          // C: 제품
      newReturn.customer || '',         // D: 고객명
      newReturn.trackingNumber || '',   // E: 송장번호
      newReturn.returnType || '',       // F: 반품/교환/오배송
      newReturn.stockStatus || '',      // G: 재고상태
      managerName || '',                // H: 검품유무 (담당자 이름)
      '',                               // I: 처리완료
      newReturn.memo || '',             // J: 비고
      '',                               // K: 사진
      ''                                // L: QR 코드 자리
    ];
    
    console.log('새 행 데이터:', rowData);
    console.log('추가할 행 번호:', newRow);
    
    // 시트에 데이터 추가
    sheet.getRange(newRow, 1, 1, rowData.length).setValues([rowData]);

    // L열에 QR 코드 이미지(송장번호 기반) 생성
    const trackingNumber = newReturn.trackingNumber ? newReturn.trackingNumber.toString().trim() : '';
    if (trackingNumber) {
      const qrUrl = 'https://api.qrserver.com/v1/create-qr-code/?size=200x200&data=' + encodeURIComponent(trackingNumber);
      const formula = '=IMAGE("' + qrUrl + '")';
      sheet.getRange(newRow, 12).setFormula(formula);
      console.log('QR 코드 생성 완료:', qrUrl);
    } else {
      console.log('송장번호가 없어 QR 코드를 생성하지 않습니다.');
    }
    
    console.log('새 반품 건 등록 완료');
    console.log(`✅ ${sheetName} 시트의 ${newRow}행에 데이터 추가됨`);
    console.log('✅ 시트 이름:', sheet.getName());
    console.log('✅ 시트 URL:', ss.getUrl());
    
    return { 
      success: true, 
      message: '새 반품 건이 등록되었습니다. QR 코드가 생성되었습니다.' 
    };
    
  } catch (error) {
    console.error('새 반품 건 등록 오류:', error);
    return { success: false, message: '등록 중 오류: ' + error.toString() };
  }
}

// 비고 저장 (관리자 전용)
function saveMemo(rowIndex, sheetName, memoText) {
  try {
    console.log('비고 저장:', rowIndex, sheetName, memoText);
    
    const ss = SpreadsheetApp.openById(SPREADSHEET_ID);
    const sheet = findSheet(ss, sheetName);
    
    if (!sheet) {
      return { success: false, message: '시트를 찾을 수 없습니다.' };
    }
    
    // J열(10번째)에 비고 저장
    sheet.getRange(rowIndex, 10).setValue(memoText);
    
    console.log(`J열(${rowIndex}행)에 비고 저장 완료`);
    return { success: true, message: '비고가 저장되었습니다.' };
    
  } catch (error) {
    console.error('비고 저장 오류:', error);
    return { success: false, message: '비고 저장 중 오류: ' + error.toString() };
  }
}

// 관리자 처리완료 처리
function markAsCompleted(rowIndex, sheetName, managerName) {
  try {
    console.log('처리완료 처리:', rowIndex, sheetName, managerName);
    
    const ss = SpreadsheetApp.openById(SPREADSHEET_ID);
    const sheet = findSheet(ss, sheetName);
    
    if (!sheet) {
      return { success: false, message: '시트를 찾을 수 없습니다.' };
    }
    
    // I열(9번째)에 담당자 이름 저장
    sheet.getRange(rowIndex, 9).setValue(managerName);
    
    console.log(`I열(${rowIndex}행)에 "${managerName}" 입력 완료`);
    return { success: true, message: `처리완료되었습니다. 담당자: ${managerName}` };
    
  } catch (error) {
    console.error('처리완료 처리 오류:', error);
    return { success: false, message: '처리완료 중 오류: ' + error.toString() };
  }
}

// 화주사 요청사항 저장
function saveClientRequest(rowIndex, sheetName, requestText) {
  try {
    console.log('요청사항 저장:', rowIndex, sheetName, requestText);
    
    const ss = SpreadsheetApp.openById(SPREADSHEET_ID);
    const sheet = findSheet(ss, sheetName);
    
    if (!sheet) {
      return { success: false, message: '시트를 찾을 수 없습니다.' };
    }
    
    // N열에 요청사항 저장
    sheet.getRange(rowIndex, 14).setValue(requestText);
    
    // O열에 "요청완료" 표시
    sheet.getRange(rowIndex, 15).setValue('요청완료');
    
    console.log('요청사항 저장 완료');
    return { success: true, message: '요청사항이 저장되었습니다.' };
    
  } catch (error) {
    console.error('요청사항 저장 오류:', error);
    return { success: false, message: '저장 중 오류: ' + error.toString() };
  }
}

// 기존 API 함수 (관리자용)
function getAllReturnsWithPhotos() {
  const ss = SpreadsheetApp.openById(SPREADSHEET_ID);
  const sheet = ss.getSheetByName('2025년7월'); // 필요시 동적으로 변경
  const lastRow = sheet.getLastRow();
  const lastCol = 11; // A~K = 11개 컬럼

  // 데이터: 3행~ 마지막행, A~K
  const data = sheet.getRange(3, 1, lastRow-2, lastCol).getRichTextValues();

  const results = [];
  for (let i = 0; i < data.length; i++) {
    const row = {};
    row['반품 접수일'] = data[i][0] ? data[i][0].getText() : '';
    row['화주명'] = data[i][1] ? data[i][1].getText() : '';
    row['제품'] = data[i][2] ? data[i][2].getText() : '';
    row['고객명'] = data[i][3] ? data[i][3].getText() : '';
    row['송장번호'] = data[i][4] ? data[i][4].getText() : '';
    row['반품/교환/오배송'] = data[i][5] ? data[i][5].getText() : '';
    row['재고상태'] = data[i][6] ? data[i][6].getText() : '';
    row['검품유무'] = data[i][7] ? data[i][7].getText() : '';
    row['처리완료'] = data[i][8] ? data[i][8].getText() : '';
    row['비고'] = data[i][9] ? data[i][9].getText() : '';
    // 사진(하이퍼링크)
    const cell = data[i][10];
    if (cell) {
      const texts = [];
      const runs = cell.getRuns();
      if (runs && runs.length > 0) {
        runs.forEach(run => {
          const text = cell.getText().substring(run.getStartIndex(), run.getEndIndex());
          const url = run.getLinkUrl();
          if (url) texts.push(text + ': ' + url);
        });
        row['사진'] = texts.join('\n');
      } else if (cell.getLinkUrl()) {
        row['사진'] = cell.getText() + ': ' + cell.getLinkUrl();
      } else {
        row['사진'] = cell.getText();
      }
    } else {
      row['사진'] = '';
    }
    results.push(row);
  }
  return ContentService.createTextOutput(JSON.stringify({returns: results, success: true})).setMimeType(ContentService.MimeType.JSON);
}
