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
  API_BASE_URL: 'http://192.168.0.114:5000', // 실제 서버 주소로 변경
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
    if (!e || !e.values || e.values.length < 5) {
      console.error('응답 데이터가 올바르지 않습니다.');
      return;
    }

    // 배열에서 데이터 추출
    const timestamp = e.values[0]; // 타임스탬프
    const palletId = e.values[1]; // 파레트 ID
    const workType = e.values[2]; // 작업 유형
    const vendor = e.values[3] || ''; // 화주사
    const product = e.values[4] || ''; // 품목명
    // e.values[5] = 작업 수량 (사용 안 함)
    // e.values[6] = 보관 위치 (사용 안 함)

    // 필수 데이터 검증
    if (!palletId || !workType) {
      console.error('필수 데이터가 없습니다. 파레트 ID:', palletId, '작업 유형:', workType);
      return;
    }

    console.log(`[동기화 시작] 파레트 ID: ${palletId}, 작업 유형: ${workType}, 화주사: ${vendor}`);

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
    
    const payload = {
      pallet_id: data.pallet_id || null, // null이면 자동 생성
      company_name: data.company_name,
      product_name: data.product_name,
      in_date: formatDateForAPI(data.in_date),
      storage_location: data.storage_location || null,
      quantity: data.quantity || 1,
      is_service: data.is_service || false,
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
      console.log(`✅ 입고 동기화 성공: ${data.pallet_id || '자동생성'}`);
      return true;
    } else {
      console.error(`❌ 입고 동기화 실패 (${responseCode}): ${responseText}`);
      return false;
    }

  } catch (error) {
    console.error('입고 동기화 오류:', error);
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
 * 이 함수를 한 번 실행하면 자동으로 트리거가 설정됨
 */
function setupFormSubmitTrigger() {
  try {
    const ss = SpreadsheetApp.getActiveSpreadsheet();
    const formSheet = ss.getSheetByName('설문지 응답 시트1');
    
    if (!formSheet) {
      SpreadsheetApp.getUi().alert('설문지 응답 시트1을 찾을 수 없습니다.');
      return;
    }

    // 기존 트리거 제거
    const triggers = ScriptApp.getProjectTriggers();
    triggers.forEach(trigger => {
      if (trigger.getHandlerFunction() === 'onFormSubmit') {
        ScriptApp.deleteTrigger(trigger);
      }
    });

    // 새 트리거 생성
    ScriptApp.newTrigger('onFormSubmit')
      .onFormSubmit()
      .create();

    SpreadsheetApp.getUi().alert('✅ Google Forms 응답 트리거가 설정되었습니다.\n\n이제 Google Forms에 응답이 들어오면 자동으로 신규 시스템으로 동기화됩니다.');

  } catch (error) {
    console.error('트리거 설정 오류:', error);
    SpreadsheetApp.getUi().alert('트리거 설정 실패: ' + error.message);
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
    .addSeparator()
    .addItem('🧪 동기화 테스트', 'testSyncConnection')
    .addToUi();
}

/**
 * 동기화 연결 테스트
 */
function testSyncConnection() {
  try {
    const testData = {
      pallet_id: 'TEST_001',
      company_name: '테스트',
      product_name: '테스트 상품',
      out_date: new Date(),
      notes: '연결 테스트'
    };

    const result = syncOutboundToNewSystem(testData);
    
    if (result) {
      SpreadsheetApp.getUi().alert('✅ 연결 테스트 성공!\n\n신규 시스템과 정상적으로 통신할 수 있습니다.');
    } else {
      SpreadsheetApp.getUi().alert('❌ 연결 테스트 실패\n\n서버 주소와 API 설정을 확인하세요.');
    }

  } catch (error) {
    SpreadsheetApp.getUi().alert('❌ 연결 테스트 오류: ' + error.message);
  }
}

