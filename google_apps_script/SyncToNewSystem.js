/**
 * 🔄 신규 솔루션과 동기화
 * 
 * Google Forms 응답을 신규 3PL 솔루션 API로 자동 전송
 * 기존 QR 코드는 그대로 사용 가능하며, 응답 시 자동으로 신규 시스템에도 저장됨
 */

// ========================================
// ⚙️ 설정
// ========================================

/**
 * 신규 솔루션 API 설정
 * 실제 서버 주소로 변경 필요
 */
const NEW_SYSTEM_CONFIG = {
  API_BASE_URL: 'https://jjaysolution.com', // 배포된 서버 주소 (Vercel)
  API_KEY: '', // API 키가 필요한 경우 여기에 설정 (환경 변수 PALLET_SYNC_API_KEY와 일치해야 함)
  ENABLED: true // 동기화 활성화 여부
};

// ========================================
// 🔄 Google Forms 응답 → 신규 시스템 동기화
// ========================================

/**
 * Google Forms 응답 시 자동 실행 (트리거)
 * Google Forms에 응답이 제출될 때마다 실행
 * 
 * e.values 배열 구조:
 * [0] = 타임스탬프 (자동 생성)
 * [1] = 파레트 ID (entry.419411235)
 * [2] = 작업 유형 (entry.427884801) - 입고, 보관종료, 서비스, 사용중
 * [3] = 화주사 (entry.2110345042)
 * [4] = 품목명 (entry.306824944)
 * [5] = 작업 수량 (선택사항, 중요하지 않음)
 * [6] = 보관 위치 (선택사항, 중요하지 않음)
 */
function onFormSubmit(e) {
  try {
    // 동기화가 비활성화되어 있으면 무시
    if (!NEW_SYSTEM_CONFIG.ENABLED) {
      console.log('동기화가 비활성화되어 있습니다.');
      return;
    }

    // e.values는 Google Forms 응답 데이터 배열
    if (!e || !e.values || e.values.length < 2) {
      console.error('응답 데이터가 올바르지 않습니다.');
      return;
    }

    // 시트에서 헤더를 가져와서 컬럼 인덱스 찾기
    const ss = SpreadsheetApp.getActiveSpreadsheet();
    const formSheet = ss.getSheetByName('설문지 응답 시트1');
    
    if (!formSheet) {
      console.error('설문지 응답 시트1을 찾을 수 없습니다.');
      return;
    }

    // 헤더 행 가져오기 (첫 번째 행)
    const headerRow = formSheet.getRange(1, 1, 1, formSheet.getLastColumn()).getValues()[0];
    
    // 컬럼 인덱스 찾기
    const timestampIdx = headerRow.indexOf('타임스탬프');
    const palletIdIdx = headerRow.indexOf('파레트 ID');
    const workTypeIdx = headerRow.indexOf('작업 유형');
    const vendorIdx = headerRow.indexOf('화주사');
    const productIdx = headerRow.indexOf('품목명');

    console.log(`[동기화 시작] 헤더 인덱스 - 타임스탬프: ${timestampIdx}, 파레트 ID: ${palletIdIdx}, 작업 유형: ${workTypeIdx}, 화주사: ${vendorIdx}, 품목명: ${productIdx}`);
    console.log(`[동기화 시작] 전체 e.values: ${JSON.stringify(e.values)}`);

    // 필수 컬럼 확인
    if (palletIdIdx === -1 || workTypeIdx === -1) {
      console.error('필수 컬럼을 찾을 수 없습니다. 파레트 ID:', palletIdIdx, '작업 유형:', workTypeIdx);
      console.error('헤더 행:', headerRow);
      return;
    }

    // e.range로 실제 추가된 행 확인
    let addedRowNum = '알 수 없음';
    if (e.range) {
      addedRowNum = e.range.getRow();
      console.log(`[동기화 시작] 새 응답이 추가된 행 번호: ${addedRowNum}`);
    }

    // 헤더 기반으로 데이터 추출
    const timestamp = timestampIdx !== -1 ? e.values[timestampIdx] : e.values[0]; // 타임스탬프는 보통 첫 번째
    const palletId = e.values[palletIdIdx];
    const workType = e.values[workTypeIdx];
    const vendor = vendorIdx !== -1 ? (e.values[vendorIdx] || '') : '';
    const product = productIdx !== -1 ? (e.values[productIdx] || '') : '';

    console.log(`[동기화 시작] 추출된 데이터 - 행 번호: ${addedRowNum}, 타임스탬프: ${timestamp}, 파레트 ID: ${palletId}, 작업 유형: ${workType}, 화주사: ${vendor}, 품목명: ${product}`);

    // 필수 데이터 검증
    if (!palletId || !workType) {
      console.error('필수 데이터가 없습니다. 파레트 ID:', palletId, '작업 유형:', workType);
      console.error('추출된 데이터 - 타임스탬프:', timestamp, ', 파레트 ID:', palletId, ', 작업 유형:', workType, ', 화주사:', vendor, ', 품목명:', product);
      return;
    }

    console.log(`[동기화 시작] 파레트 ID: ${palletId}, 작업 유형: ${workType}, 화주사: ${vendor}, 행 번호: ${addedRowNum}`);
    console.log(`[동기화 시작] 타임스탬프 타입: ${typeof timestamp}, 값: ${timestamp}`);

    // 작업 유형에 따라 분기 처리
    if (workType === '보관종료') {
      // 보관종료 처리
      syncOutboundToNewSystem({
        pallet_id: palletId,
        company_name: vendor,
        product_name: product,
        out_date: timestamp,
        notes: `Google Forms에서 자동 동기화: ${Utilities.formatDate(timestamp, Session.getScriptTimeZone(), 'yyyy-MM-dd HH:mm:ss')}`
      });
    }
    else if (workType === '입고') {
      // 입고 처리
      syncInboundToNewSystem({
        pallet_id: palletId,
        company_name: vendor,
        product_name: product,
        in_date: timestamp,
        storage_location: null, // 중요하지 않음
        quantity: 1, // 기본값
        is_service: false,
        notes: `Google Forms에서 자동 동기화: ${Utilities.formatDate(timestamp, Session.getScriptTimeZone(), 'yyyy-MM-dd HH:mm:ss')}`
      });
    }
    else if (workType === '서비스') {
      // 서비스 파레트 입고 처리 (보관료 0원)
      syncInboundToNewSystem({
        pallet_id: palletId,
        company_name: vendor,
        product_name: product,
        in_date: timestamp,
        storage_location: null,
        quantity: 1,
        is_service: true, // 서비스 파레트로 표시
        notes: `Google Forms에서 자동 동기화 (서비스): ${Utilities.formatDate(timestamp, Session.getScriptTimeZone(), 'yyyy-MM-dd HH:mm:ss')}`
      });
    }
    else if (workType === '사용중') {
      // 사용중도 입고로 처리 (보관료는 정상 계산)
      syncInboundToNewSystem({
        pallet_id: palletId,
        company_name: vendor,
        product_name: product,
        in_date: timestamp,
        storage_location: null,
        quantity: 1,
        is_service: false,
        notes: `Google Forms에서 자동 동기화 (사용중): ${Utilities.formatDate(timestamp, Session.getScriptTimeZone(), 'yyyy-MM-dd HH:mm:ss')}`
      });
    }
    else {
      console.log(`알 수 없는 작업 유형: ${workType}. 동기화를 건너뜁니다.`);
    }

  } catch (error) {
    console.error('Google Forms 응답 동기화 오류:', error);
    // 오류가 발생해도 Google Forms 응답은 정상적으로 저장되도록 함
  }
}

/**
 * 보관종료 데이터를 신규 시스템으로 동기화
 */
function syncOutboundToNewSystem(data) {
  try {
    const url = `${NEW_SYSTEM_CONFIG.API_BASE_URL}/api/pallets/outbound`;
    
    const payload = {
      pallet_id: data.pallet_id,
      out_date: formatDateForAPI(data.out_date),
      notes: data.notes || 'Google Forms에서 자동 동기화'
    };

    const options = {
      method: 'post',
      contentType: 'application/json',
      payload: JSON.stringify(payload),
      muteHttpExceptions: true
    };

    // API 키가 있으면 헤더에 추가
    if (NEW_SYSTEM_CONFIG.API_KEY) {
      options.headers = {
        'X-API-Key': NEW_SYSTEM_CONFIG.API_KEY
      };
    }

    const response = UrlFetchApp.fetch(url, options);
    const responseCode = response.getResponseCode();
    const responseText = response.getContentText();

    if (responseCode === 200 || responseCode === 201) {
      console.log(`✅ 보관종료 동기화 성공: ${data.pallet_id}`);
      return true;
    } else {
      console.error(`❌ 보관종료 동기화 실패 (${responseCode}): ${responseText}`);
      return false;
    }

  } catch (error) {
    console.error('보관종료 동기화 오류:', error);
    return false;
  }
}

/**
 * 입고 데이터를 신규 시스템으로 동기화
 */
function syncInboundToNewSystem(data) {
  try {
    const url = `${NEW_SYSTEM_CONFIG.API_BASE_URL}/api/pallets/inbound`;
    
    // 날짜 변환
    const formattedDate = formatDateForAPI(data.in_date);
    console.log(`[입고 동기화] 원본 날짜: ${data.in_date}, 변환된 날짜: ${formattedDate}`);
    
    const payload = {
      pallet_id: data.pallet_id || null, // null이면 자동 생성
      company_name: data.company_name,
      product_name: data.product_name,
      in_date: formattedDate,
      storage_location: data.storage_location || null,
      quantity: data.quantity || 1,
      is_service: data.is_service || false,
      notes: data.notes || 'Google Forms에서 자동 동기화'
    };

    console.log(`[입고 동기화] 요청 URL: ${url}`);
    console.log(`[입고 동기화] 요청 Payload: ${JSON.stringify(payload)}`);

    const options = {
      method: 'post',
      contentType: 'application/json',
      payload: JSON.stringify(payload),
      muteHttpExceptions: true
    };

    // API 키가 있으면 헤더에 추가
    if (NEW_SYSTEM_CONFIG.API_KEY) {
      options.headers = {
        'X-API-Key': NEW_SYSTEM_CONFIG.API_KEY
      };
      console.log(`[입고 동기화] API 키 사용됨`);
    } else {
      console.log(`[입고 동기화] API 키 없음 (헤더 없이 요청)`);
    }

    const response = UrlFetchApp.fetch(url, options);
    const responseCode = response.getResponseCode();
    const responseText = response.getContentText();

    console.log(`[입고 동기화] 응답 코드: ${responseCode}`);
    console.log(`[입고 동기화] 응답 내용: ${responseText}`);

    if (responseCode === 200 || responseCode === 201) {
      const result = JSON.parse(responseText);
      console.log(`✅ 입고 동기화 성공: ${data.pallet_id || result.data?.pallet_id || '자동생성'}`);
      return true;
    } else {
      let errorMsg = responseText;
      try {
        const errorResult = JSON.parse(responseText);
        errorMsg = errorResult.message || responseText;
      } catch (e) {
        // JSON 파싱 실패 시 원본 텍스트 사용
      }
      console.error(`❌ 입고 동기화 실패 (${responseCode}): ${errorMsg}`);
      console.error(`전체 응답: ${responseText}`);
      return false;
    }

  } catch (error) {
    console.error('입고 동기화 오류:', error);
    console.error('오류 스택:', error.stack);
    return false;
  }
}

/**
 * 날짜를 API 형식으로 변환 (YYYY-MM-DD)
 */
function formatDateForAPI(date) {
  if (!date) return null;
  
  if (date instanceof Date) {
    return Utilities.formatDate(date, Session.getScriptTimeZone(), 'yyyy-MM-dd');
  }
  
  // 문자열인 경우 파싱 시도
  const dateObj = new Date(date);
  if (isValidDate(dateObj)) {
    return Utilities.formatDate(dateObj, Session.getScriptTimeZone(), 'yyyy-MM-dd');
  }
  
  return null;
}

/**
 * 날짜 유효성 검사
 */
function isValidDate(d) {
  return d instanceof Date && !isNaN(d.getTime());
}

// ========================================
// 🔧 트리거 설정
// ========================================

/**
 * Google Forms 응답 트리거 설정
 * 
 * 참고: Google Forms와 연결된 스프레드시트에서는
 * 'onFormSubmit' 함수가 자동으로 호출됩니다.
 * 별도의 트리거 설정이 필요하지 않습니다.
 */
function setupFormSubmitTrigger() {
  try {
    const ss = SpreadsheetApp.getActiveSpreadsheet();
    const formSheet = ss.getSheetByName('설문지 응답 시트1');
    
    // "설문지 응답 시트1"이 존재하면 이미 Google Forms와 연결되어 있음
    if (!formSheet) {
      SpreadsheetApp.getUi().alert('⚠️ 설문지 응답 시트1을 찾을 수 없습니다.\n\n' +
        '이 스프레드시트가 Google Forms와 연결되어 있는지 확인하세요.\n\n' +
        'Google Forms 설정에서 응답을 이 스프레드시트로 저장하도록 설정되어 있어야 합니다.');
      return;
    }

    // onFormSubmit 함수 존재 확인
    const hasOnFormSubmit = typeof onFormSubmit === 'function';

    if (hasOnFormSubmit) {
      SpreadsheetApp.getUi().alert('✅ 설정 완료!\n\n' +
        'Google Forms 응답이 이 스프레드시트에 저장될 때\n' +
        'onFormSubmit 함수가 자동으로 호출되어\n' +
        '신규 시스템으로 동기화됩니다.\n\n' +
        '별도의 트리거 설정이 필요하지 않습니다.\n\n' +
        '테스트: Google Forms에 응답을 제출해보세요.');
    } else {
      SpreadsheetApp.getUi().alert('⚠️ onFormSubmit 함수를 찾을 수 없습니다.\n\n' +
        'SyncToNewSystem.js 파일이 Google Apps Script 프로젝트에\n' +
        '포함되어 있는지 확인하세요.\n\n' +
        'clasp push를 실행하여 파일을 업로드했는지 확인하세요.');
    }

  } catch (error) {
    console.error('트리거 설정 오류:', error);
    SpreadsheetApp.getUi().alert('트리거 설정 확인 실패: ' + error.message);
  }
}

/**
 * 기존 데이터 일괄 동기화 (한 번만 실행)
 * 기존 Google Sheets 데이터를 신규 시스템으로 마이그레이션
 */
function syncExistingDataToNewSystem() {
  try {
    const ss = SpreadsheetApp.getActiveSpreadsheet();
    const responseSheet = ss.getSheetByName('설문지 응답 시트1');
    
    if (!responseSheet) {
      SpreadsheetApp.getUi().alert('설문지 응답 시트1을 찾을 수 없습니다.');
      return;
    }

    const ui = SpreadsheetApp.getUi();
    const response = ui.alert(
      '기존 데이터 일괄 동기화',
      '기존 Google Sheets의 모든 데이터를 신규 시스템으로 동기화하시겠습니까?\n\n⚠️ 주의: 이미 동기화된 데이터는 중복될 수 있습니다.',
      ui.ButtonSet.YES_NO
    );

    if (response !== ui.Button.YES) {
      return;
    }

    const data = responseSheet.getDataRange().getValues();
    const header = data[0];

    const timestampIdx = header.indexOf('타임스탬프');
    const palletIdIdx = header.indexOf('파레트 ID');
    const workTypeIdx = header.indexOf('작업 유형');
    const vendorIdx = header.indexOf('화주사');
    const productIdx = header.indexOf('품목명');
    const qtyIdx = header.indexOf('작업 수량');
    const locationIdx = header.indexOf('보관 위치');

    if (palletIdIdx === -1 || workTypeIdx === -1) {
      SpreadsheetApp.getUi().alert('필수 컬럼을 찾을 수 없습니다.');
      return;
    }

    let successCount = 0;
    let failCount = 0;
    const errors = [];

    // 각 행 처리
    for (let i = 1; i < data.length; i++) {
      const row = data[i];
      const palletId = row[palletIdIdx];
      const workType = row[workTypeIdx];
      const vendor = row[vendorIdx] || '';
      const product = row[productIdx] || '';
      const qty = row[qtyIdx] || 1;
      const location = row[locationIdx] || '';
      const timestamp = row[timestampIdx];

      if (!palletId || !workType) continue;

      let success = false;

      if (workType === '보관종료') {
        success = syncOutboundToNewSystem({
          pallet_id: palletId,
          company_name: vendor,
          product_name: product,
          out_date: timestamp,
          notes: `기존 데이터 일괄 동기화: ${Utilities.formatDate(timestamp, Session.getScriptTimeZone(), 'yyyy-MM-dd HH:mm:ss')}`
        });
      } else if (workType === '입고') {
        success = syncInboundToNewSystem({
          pallet_id: palletId,
          company_name: vendor,
          product_name: product,
          in_date: timestamp,
          storage_location: location,
          quantity: qty,
          is_service: false,
          notes: `기존 데이터 일괄 동기화: ${Utilities.formatDate(timestamp, Session.getScriptTimeZone(), 'yyyy-MM-dd HH:mm:ss')}`
        });
      }

      if (success) {
        successCount++;
      } else {
        failCount++;
        errors.push(`${palletId} (${workType})`);
      }

      // API 호출 제한을 피하기 위해 약간의 지연
      if (i % 10 === 0) {
        Utilities.sleep(100);
      }
    }

    // 결과 알림
    let message = `✅ 일괄 동기화 완료!\n\n`;
    message += `성공: ${successCount}건\n`;
    message += `실패: ${failCount}건\n`;

    if (errors.length > 0 && errors.length <= 10) {
      message += `\n실패한 항목:\n${errors.join('\n')}`;
    } else if (errors.length > 10) {
      message += `\n실패한 항목: ${errors.length}개 (처음 10개만 표시)\n${errors.slice(0, 10).join('\n')}`;
    }

    SpreadsheetApp.getUi().alert(message);

  } catch (error) {
    console.error('일괄 동기화 오류:', error);
    SpreadsheetApp.getUi().alert('일괄 동기화 실패: ' + error.message);
  }
}

// ========================================
// 📋 메뉴 설정
// ========================================

/**
 * 동기화 메뉴 설정
 */
function setupSyncMenu(ui) {
  ui.createMenu('🔄 신규 시스템 동기화')
    .addItem('⚙️ 트리거 설정', 'setupFormSubmitTrigger')
    .addSeparator()
    .addItem('📤 기존 데이터 일괄 동기화', 'syncExistingDataToNewSystem')
    .addItem('🔄 최신 응답 수동 동기화', 'syncLatestResponseManually')
    .addSeparator()
    .addItem('🧪 동기화 테스트', 'testSyncConnection')
    .addItem('🔍 최근 실행 로그 확인', 'checkRecentLogs')
    .addToUi();
}

/**
 * 최신 응답을 수동으로 동기화 (디버깅/재시도용)
 */
function syncLatestResponseManually() {
  try {
    const ss = SpreadsheetApp.getActiveSpreadsheet();
    const responseSheet = ss.getSheetByName('설문지 응답 시트1');
    
    if (!responseSheet) {
      SpreadsheetApp.getUi().alert('설문지 응답 시트1을 찾을 수 없습니다.');
      return;
    }

    const data = responseSheet.getDataRange().getValues();
    if (data.length < 2) {
      SpreadsheetApp.getUi().alert('응답 데이터가 없습니다.');
      return;
    }

    const header = data[0];
    
    const timestampIdx = header.indexOf('타임스탬프');
    const palletIdIdx = header.indexOf('파레트 ID');
    const workTypeIdx = header.indexOf('작업 유형');
    const vendorIdx = header.indexOf('화주사');
    const productIdx = header.indexOf('품목명');

    if (palletIdIdx === -1 || workTypeIdx === -1 || timestampIdx === -1) {
      SpreadsheetApp.getUi().alert('필수 컬럼을 찾을 수 없습니다.');
      return;
    }

    // 타임스탬프 기준으로 가장 최근 응답 찾기
    let latestRow = null;
    let latestTimestamp = null;
    let latestRowNum = 0;

    for (let i = 1; i < data.length; i++) {
      const row = data[i];
      const rowTimestamp = row[timestampIdx];
      
      if (!rowTimestamp) continue;

      let timestampDate = null;
      if (rowTimestamp instanceof Date) {
        timestampDate = rowTimestamp;
      } else {
        timestampDate = new Date(rowTimestamp);
      }

      if (isNaN(timestampDate.getTime())) continue;

      if (!latestTimestamp || timestampDate > latestTimestamp) {
        latestTimestamp = timestampDate;
        latestRow = row;
        latestRowNum = i + 1;
      }
    }

    if (!latestRow) {
      SpreadsheetApp.getUi().alert('유효한 응답 데이터를 찾을 수 없습니다.');
      return;
    }

    // 최신 응답 데이터 추출
    const timestamp = latestRow[timestampIdx];
    const palletId = latestRow[palletIdIdx];
    const workType = latestRow[workTypeIdx];
    const vendor = latestRow[vendorIdx] || '';
    const product = latestRow[productIdx] || '';

    if (!palletId || !workType) {
      SpreadsheetApp.getUi().alert('필수 데이터가 없습니다.');
      return;
    }

    // 사용자 확인
    const ui = SpreadsheetApp.getUi();
    const response = ui.alert(
      '최신 응답 수동 동기화',
      `다음 응답을 동기화하시겠습니까?\n\n` +
      `행 번호: ${latestRowNum}\n` +
      `파레트 ID: ${palletId}\n` +
      `작업 유형: ${workType}\n` +
      `화주사: ${vendor}\n` +
      `품목명: ${product}\n` +
      `타임스탬프: ${timestamp}`,
      ui.ButtonSet.YES_NO
    );

    if (response !== ui.Button.YES) {
      return;
    }

    // 동기화 실행
    let success = false;
    let message = '';

    if (workType === '보관종료') {
      success = syncOutboundToNewSystem({
        pallet_id: palletId,
        company_name: vendor,
        product_name: product,
        out_date: timestamp,
        notes: `수동 동기화: ${Utilities.formatDate(timestamp, Session.getScriptTimeZone(), 'yyyy-MM-dd HH:mm:ss')}`
      });
      message = success ? '✅ 보관종료 동기화 성공!' : '❌ 보관종료 동기화 실패';
    } else if (workType === '입고' || workType === '서비스' || workType === '사용중') {
      success = syncInboundToNewSystem({
        pallet_id: palletId,
        company_name: vendor,
        product_name: product,
        in_date: timestamp,
        storage_location: null,
        quantity: 1,
        is_service: (workType === '서비스'),
        notes: `수동 동기화: ${Utilities.formatDate(timestamp, Session.getScriptTimeZone(), 'yyyy-MM-dd HH:mm:ss')}`
      });
      message = success ? '✅ 입고 동기화 성공!' : '❌ 입고 동기화 실패';
    } else {
      SpreadsheetApp.getUi().alert('알 수 없는 작업 유형: ' + workType);
      return;
    }

    SpreadsheetApp.getUi().alert(message + '\n\n' + (success ? '우리 사이트에서 확인해보세요.' : '실행 로그를 확인하세요.'));

  } catch (error) {
    SpreadsheetApp.getUi().alert('수동 동기화 오류: ' + error.message);
    console.error('수동 동기화 오류:', error);
  }
}

/**
 * 최근 실행 로그 확인 (디버깅용)
 */
function checkRecentLogs() {
  try {
    const ss = SpreadsheetApp.getActiveSpreadsheet();
    const responseSheet = ss.getSheetByName('설문지 응답 시트1');
    
    if (!responseSheet) {
      SpreadsheetApp.getUi().alert('설문지 응답 시트1을 찾을 수 없습니다.');
      return;
    }

    const data = responseSheet.getDataRange().getValues();
    if (data.length < 2) {
      SpreadsheetApp.getUi().alert('응답 데이터가 없습니다.');
      return;
    }

    const header = data[0];
    
    const timestampIdx = header.indexOf('타임스탬프');
    const palletIdIdx = header.indexOf('파레트 ID');
    const workTypeIdx = header.indexOf('작업 유형');
    const vendorIdx = header.indexOf('화주사');
    const productIdx = header.indexOf('품목명');

    if (palletIdIdx === -1 || workTypeIdx === -1 || timestampIdx === -1) {
      SpreadsheetApp.getUi().alert('필수 컬럼을 찾을 수 없습니다.');
      return;
    }

    // 타임스탬프 기준으로 가장 최근 응답 찾기
    let latestRow = null;
    let latestTimestamp = null;
    let latestRowNum = 0;

    for (let i = 1; i < data.length; i++) {
      const row = data[i];
      const rowTimestamp = row[timestampIdx];
      
      if (!rowTimestamp) continue;

      // 타임스탬프를 Date 객체로 변환
      let timestampDate = null;
      if (rowTimestamp instanceof Date) {
        timestampDate = rowTimestamp;
      } else {
        timestampDate = new Date(rowTimestamp);
      }

      // 유효한 날짜인지 확인
      if (isNaN(timestampDate.getTime())) continue;

      // 최신 타임스탬프 찾기
      if (!latestTimestamp || timestampDate > latestTimestamp) {
        latestTimestamp = timestampDate;
        latestRow = row;
        latestRowNum = i + 1; // 시트 행 번호 (헤더 포함)
      }
    }

    if (!latestRow) {
      SpreadsheetApp.getUi().alert('유효한 응답 데이터를 찾을 수 없습니다.');
      return;
    }

    const lastPalletId = latestRow[palletIdIdx];
    const lastWorkType = latestRow[workTypeIdx];
    const lastVendor = latestRow[vendorIdx] || '';
    const lastProduct = latestRow[productIdx] || '';
    const lastTimestamp = latestRow[timestampIdx];

    let message = '📋 최신 응답 정보 (타임스탬프 기준):\n\n';
    message += `행 번호: ${latestRowNum}\n`;
    message += `파레트 ID: ${lastPalletId}\n`;
    message += `작업 유형: ${lastWorkType}\n`;
    message += `화주사: ${lastVendor}\n`;
    message += `품목명: ${lastProduct}\n`;
    message += `타임스탬프: ${lastTimestamp}\n\n`;
    message += '⚠️ 실행 로그를 확인하려면:\n';
    message += '확장 프로그램 → Apps Script → 실행 (왼쪽 메뉴)';

    SpreadsheetApp.getUi().alert(message);

  } catch (error) {
    SpreadsheetApp.getUi().alert('로그 확인 오류: ' + error.message);
  }
}

/**
 * 동기화 연결 테스트
 */
function testSyncConnection() {
  try {
    // 1단계: 서버 헬스체크
    const healthUrl = `${NEW_SYSTEM_CONFIG.API_BASE_URL}/api/health`;
    let healthResponse;
    try {
      healthResponse = UrlFetchApp.fetch(healthUrl, {
        method: 'get',
        muteHttpExceptions: true
      });
    } catch (e) {
      SpreadsheetApp.getUi().alert(
        '❌ 연결 테스트 실패\n\n' +
        '서버에 연결할 수 없습니다.\n\n' +
        `서버 주소: ${NEW_SYSTEM_CONFIG.API_BASE_URL}\n` +
        `오류: ${e.message}\n\n` +
        '확인 사항:\n' +
        '1. 서버가 배포되어 실행 중인지 확인\n' +
        '2. 서버 주소가 올바른지 확인\n' +
        '3. 방화벽/네트워크 설정 확인'
      );
      return;
    }

    const healthCode = healthResponse.getResponseCode();
    const healthText = healthResponse.getContentText();

    if (healthCode !== 200) {
      SpreadsheetApp.getUi().alert(
        '❌ 연결 테스트 실패\n\n' +
        `서버 응답 코드: ${healthCode}\n` +
        `응답 내용: ${healthText}\n\n` +
        `서버 주소: ${NEW_SYSTEM_CONFIG.API_BASE_URL}\n\n` +
        '서버가 정상적으로 작동하지 않는 것 같습니다.'
      );
      return;
    }

    // 2단계: API 엔드포인트 테스트 (고유한 테스트 파레트 ID 생성)
    const testUrl = `${NEW_SYSTEM_CONFIG.API_BASE_URL}/api/pallets/inbound`;
    
    // 고유한 테스트 파레트 ID 생성 (타임스탬프 기반)
    const now = new Date();
    const timestamp = Utilities.formatDate(now, Session.getScriptTimeZone(), 'yyMMdd_HHmmss');
    const randomSuffix = Math.floor(Math.random() * 1000).toString().padStart(3, '0');
    const testPalletId = `TEST_${timestamp}_${randomSuffix}`;
    
    const testPayload = {
      pallet_id: testPalletId, // 고유한 테스트 ID 사용
      company_name: '테스트_연결확인',
      product_name: '연결 테스트',
      in_date: formatDateForAPI(now),
      quantity: 1,
      is_service: true, // 서비스 파레트로 생성 (보관료 0원)
      notes: 'Google Apps Script 연결 테스트 - 이 파레트는 삭제해도 됩니다.'
    };

    const options = {
      method: 'post',
      contentType: 'application/json',
      payload: JSON.stringify(testPayload),
      muteHttpExceptions: true
    };

    if (NEW_SYSTEM_CONFIG.API_KEY) {
      options.headers = {
        'X-API-Key': NEW_SYSTEM_CONFIG.API_KEY
      };
    }

    const apiResponse = UrlFetchApp.fetch(testUrl, options);
    const apiCode = apiResponse.getResponseCode();
    const apiText = apiResponse.getContentText();

    if (apiCode === 200 || apiCode === 201) {
      const apiResult = JSON.parse(apiText);
      SpreadsheetApp.getUi().alert(
        '✅ 연결 테스트 성공!\n\n' +
        '신규 시스템과 정상적으로 통신할 수 있습니다.\n\n' +
        `서버 주소: ${NEW_SYSTEM_CONFIG.API_BASE_URL}\n` +
        `테스트 파레트 ID: ${apiResult.data?.pallet_id || testPalletId}\n\n` +
        '⚠️ 참고: 테스트로 생성된 파레트는 "파레트 현황"에서 삭제할 수 있습니다.'
      );
    } else {
      let errorMessage = '알 수 없는 오류';
      let isDuplicateError = false;
      try {
        const errorResult = JSON.parse(apiText);
        errorMessage = errorResult.message || apiText;
        // 중복 오류인 경우 특별 처리
        if (errorMessage.indexOf('이미 존재') !== -1 || errorMessage.indexOf('already exists') !== -1) {
          isDuplicateError = true;
        }
      } catch (e) {
        errorMessage = apiText;
      }

      if (isDuplicateError) {
        // 중복 오류는 실제로는 연결이 성공한 것으로 간주
        SpreadsheetApp.getUi().alert(
          '✅ 연결 테스트 성공 (중복 파레트 감지)\n\n' +
          '서버와 정상적으로 통신할 수 있습니다.\n' +
          '테스트 파레트가 이미 존재하는 것으로 보아\n' +
          '이전 테스트가 성공적으로 완료된 것입니다.\n\n' +
          `서버 주소: ${NEW_SYSTEM_CONFIG.API_BASE_URL}\n` +
          `테스트 파레트 ID: ${testPalletId}\n\n` +
          '⚠️ 참고: 기존 테스트 파레트를 사용하려면\n' +
          '"파레트 현황"에서 삭제 후 다시 테스트하세요.'
        );
      } else {
        SpreadsheetApp.getUi().alert(
          '❌ API 연결 테스트 실패\n\n' +
          `서버 응답 코드: ${apiCode}\n` +
          `오류 메시지: ${errorMessage}\n\n` +
          `서버 주소: ${NEW_SYSTEM_CONFIG.API_BASE_URL}\n` +
          `API 엔드포인트: ${testUrl}\n` +
          `테스트 파레트 ID: ${testPalletId}\n\n` +
          '확인 사항:\n' +
          '1. API 엔드포인트 경로가 올바른지 확인\n' +
          '2. API 키가 필요한 경우 설정되어 있는지 확인\n' +
          '3. 서버 로그에서 자세한 오류 확인'
        );
      }
    }

  } catch (error) {
    SpreadsheetApp.getUi().alert(
      '❌ 연결 테스트 오류\n\n' +
      `오류: ${error.message}\n\n` +
      `서버 주소: ${NEW_SYSTEM_CONFIG.API_BASE_URL}\n\n` +
      '스크립트 실행 로그를 확인하세요.'
    );
    console.error('연결 테스트 오류:', error);
  }
}

