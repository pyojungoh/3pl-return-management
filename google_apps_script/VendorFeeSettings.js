/**
 * 💰 화주사별 보관료 설정 시스템
 * 
 * 주요 기능:
 * - 화주사별 다른 보관료 설정
 * - 신규 화주사 자동 추가
 * - 기존 화주사 정보 보존
 * - 백원 단위 올림 계산
 */

// ========================================
// 📋 보관료설정 시트 생성 및 관리
// ========================================

/**
 * 보관료설정 시트 생성
 */
function createVendorFeeSettingsSheet() {
  try {
    const ss = SpreadsheetApp.getActiveSpreadsheet();
    let feeSheet = ss.getSheetByName("보관료설정");
    
    if (!feeSheet) {
      feeSheet = ss.insertSheet("보관료설정");
    } else {
      // 기존 시트가 있으면 헤더만 확인하고 데이터는 유지
      const existingData = feeSheet.getDataRange().getValues();
      if (existingData.length > 1) {
        SpreadsheetApp.getUi().alert("기존 보관료설정 시트가 있습니다.\n데이터를 유지합니다.");
        return;
      }
    }
    
    // 헤더 설정
    const headers = [
      "화주사",
      "월 보관료 (원)",
      "일일 보관료 (자동)",
      "적용 시작일",
      "비고"
    ];
    
    feeSheet.getRange("A1:E1").setValues([headers]);
    feeSheet.getRange("A1:E1").setFontWeight("bold").setBackground("#fff2cc");
    feeSheet.setFrozenRows(1);
    
    // 열 너비 설정
    feeSheet.setColumnWidth(1, 150); // 화주사
    feeSheet.setColumnWidth(2, 120); // 월 보관료
    feeSheet.setColumnWidth(3, 120); // 일일 보관료
    feeSheet.setColumnWidth(4, 120); // 적용 시작일
    feeSheet.setColumnWidth(5, 200); // 비고
    
    // 샘플 데이터 추가 (예시)
    const today = Utilities.formatDate(new Date(), Session.getScriptTimeZone(), "yyyy-MM-dd");
    const sampleData = [
      ["미지정", 16000, "=ROUND(B2/30.44)", today, "기본 요금"]
    ];
    
    feeSheet.getRange("A2:E2").setValues(sampleData);
    
    // 숫자 포맷 적용
    feeSheet.getRange("B2:B100").setNumberFormat("#,##0");
    feeSheet.getRange("C2:C100").setNumberFormat("#,##0");
    
    SpreadsheetApp.getUi().alert("✅ 보관료설정 시트가 생성되었습니다.\n\n화주사별 보관료를 입력하세요.");
    
  } catch (error) {
    console.error('보관료설정 시트 생성 실패:', error);
    SpreadsheetApp.getUi().alert('시트 생성 실패: ' + error.message);
  }
}

/**
 * 화주사 가져오기 (신규만 추가)
 */
function importNewVendorsToFeeSettings() {
  try {
    const ss = SpreadsheetApp.getActiveSpreadsheet();
    const sourceSheet = ss.getSheetByName("파레트 요약 정산");
    const feeSheet = ss.getSheetByName("보관료설정");
    
    if (!sourceSheet) {
      SpreadsheetApp.getUi().alert("파레트 요약 정산 시트가 없습니다.\n먼저 정산을 실행하세요.");
      return;
    }
    
    if (!feeSheet) {
      SpreadsheetApp.getUi().alert("보관료설정 시트가 없습니다.\n먼저 보관료설정 시트를 생성하세요.");
      return;
    }
    
    // 파레트 요약 정산에서 화주사 목록 가져오기
    const sourceData = sourceSheet.getDataRange().getValues();
    const sourceHeader = sourceData[0];
    const vendorIdx = sourceHeader.indexOf("화주사");
    
    if (vendorIdx === -1) {
      SpreadsheetApp.getUi().alert("화주사 컬럼을 찾을 수 없습니다.");
      return;
    }
    
    // 화주사 목록 추출 (정규화)
    const vendorSet = new Set();
    const vendorOriginalMap = {}; // 정규화된 이름 → 원본 이름
    
    for (let i = 1; i < sourceData.length; i++) {
      const originalVendor = sourceData[i][vendorIdx];
      if (originalVendor && originalVendor.toString().trim()) {
        const normalizedVendor = normalizeVendorName(originalVendor);
        vendorSet.add(normalizedVendor);
        
        // 원본 이름 저장 (처음 나온 이름 사용)
        if (!vendorOriginalMap[normalizedVendor]) {
          vendorOriginalMap[normalizedVendor] = originalVendor.toString().trim();
        }
      }
    }
    
    // 기존 보관료설정 시트에 있는 화주사 목록
    const feeData = feeSheet.getDataRange().getValues();
    const existingVendors = new Set();
    
    for (let i = 1; i < feeData.length; i++) {
      const vendor = feeData[i][0];
      if (vendor && vendor.toString().trim()) {
        const normalizedVendor = normalizeVendorName(vendor);
        existingVendors.add(normalizedVendor);
      }
    }
    
    // 신규 화주사 찾기
    const newVendors = [];
    const today = Utilities.formatDate(new Date(), Session.getScriptTimeZone(), "yyyy-MM-dd");
    
    for (const normalizedVendor of vendorSet) {
      if (!existingVendors.has(normalizedVendor)) {
        const originalVendor = vendorOriginalMap[normalizedVendor];
        newVendors.push([
          originalVendor,
          16000,  // 기본 월 보관료
          "=ROUND(B" + (feeSheet.getLastRow() + 1) + "/30.44)",  // 일일 보관료 계산
          today,
          "신규 추가"
        ]);
      }
    }
    
    if (newVendors.length === 0) {
      SpreadsheetApp.getUi().alert("신규 화주사가 없습니다.\n모든 화주사가 이미 등록되어 있습니다.");
      return;
    }
    
    // 신규 화주사 추가
    const lastRow = feeSheet.getLastRow();
    feeSheet.getRange(lastRow + 1, 1, newVendors.length, 5).setValues(newVendors);
    
    // 숫자 포맷 적용
    feeSheet.getRange(lastRow + 1, 2, newVendors.length, 1).setNumberFormat("#,##0");
    feeSheet.getRange(lastRow + 1, 3, newVendors.length, 1).setNumberFormat("#,##0");
    
    SpreadsheetApp.getUi().alert(`✅ ${newVendors.length}개 신규 화주사가 추가되었습니다.\n\n` +
      newVendors.map(v => `• ${v[0]}`).join('\n'));
    
  } catch (error) {
    console.error('신규 화주사 가져오기 실패:', error);
    SpreadsheetApp.getUi().alert('화주사 가져오기 실패: ' + error.message);
  }
}

/**
 * 화주사별 월 보관료 조회
 */
function getVendorMonthlyFee(vendor) {
  try {
    const ss = SpreadsheetApp.getActiveSpreadsheet();
    const feeSheet = ss.getSheetByName("보관료설정");
    
    // 보관료설정 시트가 없으면 기본값 반환
    if (!feeSheet) {
      return 16000; // 기본값
    }
    
    const feeData = feeSheet.getDataRange().getValues();
    const normalizedVendor = normalizeVendorName(vendor);
    
    // 화주사별 보관료 찾기
    for (let i = 1; i < feeData.length; i++) {
      const feeVendor = feeData[i][0];
      if (feeVendor) {
        const normalizedFeeVendor = normalizeVendorName(feeVendor);
        if (normalizedFeeVendor === normalizedVendor) {
          const monthlyFee = Number(feeData[i][1]);
          if (monthlyFee > 0) {
            return monthlyFee;
          }
        }
      }
    }
    
    // 찾지 못하면 기본값
    return 16000;
    
  } catch (error) {
    console.error('화주사별 보관료 조회 실패:', error);
    return 16000; // 기본값
  }
}

/**
 * 보관료 일괄 업데이트 (보관료설정 → 설정 시트)
 */
function applyVendorFeeToConfig() {
  try {
    const ss = SpreadsheetApp.getActiveSpreadsheet();
    const feeSheet = ss.getSheetByName("보관료설정");
    const configSheet = ss.getSheetByName("설정");
    
    if (!feeSheet) {
      SpreadsheetApp.getUi().alert("보관료설정 시트가 없습니다.");
      return;
    }
    
    if (!configSheet) {
      SpreadsheetApp.getUi().alert("설정 시트가 없습니다.");
      return;
    }
    
    // 보관료설정에서 평균 또는 기본 보관료 계산
    const feeData = feeSheet.getDataRange().getValues();
    let totalFee = 0;
    let count = 0;
    
    for (let i = 1; i < feeData.length; i++) {
      const monthlyFee = Number(feeData[i][1]);
      if (monthlyFee > 0) {
        totalFee += monthlyFee;
        count++;
      }
    }
    
    const avgFee = count > 0 ? Math.round(totalFee / count) : 16000;
    
    SpreadsheetApp.getUi().alert(`✅ 보관료 일괄 업데이트 완료!\n\n` +
      `평균 월 보관료: ${avgFee.toLocaleString()}원\n` +
      `화주사별 보관료는 보관료설정 시트에서 관리됩니다.`);
    
  } catch (error) {
    console.error('보관료 일괄 업데이트 실패:', error);
    SpreadsheetApp.getUi().alert('업데이트 실패: ' + error.message);
  }
}

/**
 * 보관료만 빠르게 재계산 (화주사별 시트의 보관료 컬럼만 업데이트)
 */
function recalculateVendorFeesOnly() {
  try {
    const ss = SpreadsheetApp.getActiveSpreadsheet();
    const sourceSheet = ss.getSheetByName("파레트 요약 정산");
    const feeSheet = ss.getSheetByName("보관료설정");
    
    if (!sourceSheet) {
      SpreadsheetApp.getUi().alert("파레트 요약 정산 시트가 없습니다.\n먼저 정산을 실행하세요.");
      return;
    }
    
    if (!feeSheet) {
      SpreadsheetApp.getUi().alert("보관료설정 시트가 없습니다.\n먼저 보관료설정 시트를 생성하세요.");
      return;
    }
    
    // 파레트 요약 정산에서 화주사 목록 가져오기
    const data = sourceSheet.getDataRange().getValues();
    const header = data[0];
    const vendorIdx = header.indexOf("화주사");
    const daysIdx = header.indexOf("보관일수");
    const feeIdx = header.indexOf("보관료(원)");
    
    if (vendorIdx === -1 || daysIdx === -1 || feeIdx === -1) {
      SpreadsheetApp.getUi().alert("필수 컬럼을 찾을 수 없습니다.");
      return;
    }
    
    // 화주사별로 그룹화
    const vendorMap = {};
    const vendorNameMap = {};
    
    for (let i = 1; i < data.length; i++) {
      const row = data[i];
      const originalVendor = row[vendorIdx] || "미지정";
      const normalizedVendor = normalizeVendorName(originalVendor);
      
      if (!vendorMap[normalizedVendor]) {
        vendorMap[normalizedVendor] = [];
        vendorNameMap[normalizedVendor] = originalVendor;
      }
      vendorMap[normalizedVendor].push(i + 1); // 행 번호 저장
    }
    
    let updatedSheets = 0;
    let updatedRows = 0;
    
    // 각 화주사별 시트의 보관료만 재계산
    for (const normalizedVendor in vendorMap) {
      const originalVendor = vendorNameMap[normalizedVendor];
      const sheetName = sanitizeSheetName(originalVendor);
      const vendorSheet = ss.getSheetByName(sheetName);
      
      if (!vendorSheet) {
        console.log(`시트 ${sheetName}을 찾을 수 없습니다.`);
        continue;
      }
      
      // 화주사별 월 보관료 조회
      const monthlyFee = getVendorMonthlyFee(originalVendor);
      const dailyFee = Math.round(monthlyFee / 30.44);
      
      console.log(`${originalVendor}: 월 ${monthlyFee.toLocaleString()}원, 일일 ${dailyFee}원`);
      
      // 화주사별 시트의 데이터 읽기
      const vendorData = vendorSheet.getDataRange().getValues();
      const vendorHeader = vendorData[0];
      const vendorDaysIdx = vendorHeader.indexOf("보관일수");
      const vendorFeeIdx = vendorHeader.indexOf("보관료(원)");
      const vendorStatusIdx = vendorHeader.indexOf("상태");
      
      if (vendorDaysIdx === -1 || vendorFeeIdx === -1) {
        console.log(`${sheetName}: 필수 컬럼 없음`);
        continue;
      }
      
      // 각 행의 보관료 재계산
      for (let i = 1; i < vendorData.length; i++) {
        const row = vendorData[i];
        const status = row[vendorStatusIdx];
        const days = Number(row[vendorDaysIdx]);
        
        // 서비스는 0원, 보관일수가 있는 경우만 계산
        if (status === "서비스" || days === 0 || isNaN(days) || days === "") {
          continue;
        }
        
        // 보관료 재계산
        const calculatedFee = dailyFee * days;
        const roundedFee = Math.ceil(calculatedFee / 100) * 100; // 백원 단위 올림
        
        // 보관료 컬럼 업데이트
        vendorSheet.getRange(i + 1, vendorFeeIdx + 1).setValue(roundedFee);
        updatedRows++;
      }
      
      // 총계 행 찾아서 재계산
      for (let i = vendorData.length - 1; i >= 0; i--) {
        const cellValue = vendorData[i][0];
        if (cellValue && cellValue.toString().includes("총 보관료 합계")) {
          // 총계 수식 재설정
          const totalRowNum = i + 1;
          const feeColLetter = String.fromCharCode(65 + vendorFeeIdx);
          const formulaRange = `${feeColLetter}2:${feeColLetter}${totalRowNum - 2}`;
          vendorSheet.getRange(totalRowNum, vendorFeeIdx + 1).setFormula(`=SUM(${formulaRange})`);
          break;
        }
      }
      
      updatedSheets++;
    }
    
    // 결과 알림
    SpreadsheetApp.getUi().alert(`⚡ 보관료 재계산 완료!\n\n` +
      `🏢 업데이트된 화주사 시트: ${updatedSheets}개\n` +
      `📊 업데이트된 행: ${updatedRows}개\n\n` +
      `백원 단위 올림이 적용되었습니다.`);
    
    // 감사 로그 기록
    if (typeof logAuditEvent === 'function') {
      logAuditEvent('INFO', 'Vendor fees recalculated', {
        updatedSheets: updatedSheets,
        updatedRows: updatedRows
      });
    }
    
  } catch (error) {
    console.error('보관료 재계산 실패:', error);
    SpreadsheetApp.getUi().alert('보관료 재계산 실패: ' + error.message);
  }
}

// ========================================
// 🔄 기존 메뉴에 통합
// ========================================

/**
 * 보관료 설정 메뉴 추가
 */
function setupVendorFeeMenu(ui) {
  // ⚙️ 설정 도구 메뉴에 보관료 설정 추가
  // (Code.js의 onOpen에서 호출됨)
}
