/**
 * 🔒 보안 강화된 설정 관리 모듈
 * 
 * 기존 configUI.js의 보안 강화 버전
 * - 민감한 정보 보호
 * - 설정값 검증
 * - 안전한 환경변수 관리
 */

// ========================================
// 🔐 보안 설정 상수
// ========================================

const SECURE_CONFIG = {
  // 환경변수 키 (실제 값은 PropertiesService에 저장)
  ENV_KEYS: {
    FORM_URL: 'FORM_BASE_URL',
    QR_SERVICE_URL: 'QR_SERVICE_URL',
    ADMIN_EMAILS: 'ADMIN_EMAILS',
    ALLOWED_USERS: 'ALLOWED_USERS'
  },
  
  // 기본값
  DEFAULTS: {
    FORM_URL: 'https://docs.google.com/forms/d/e/1FAIpQLSdDmnWcW27tfDptUvuSjEgN8K7nNNQWecdpeMMhwftTtbiyIQ/viewform',
    QR_SERVICE_URL: 'https://quickchart.io/qr',
    ADMIN_EMAILS: 'jjay220304@gmail.com',
    ALLOWED_USERS: ''
  }
};

// ========================================
// 🔒 안전한 설정값 관리
// ========================================

/**
 * 환경변수에서 안전하게 값 가져오기
 * @param {string} key - 설정 키
 * @param {string} defaultValue - 기본값
 * @returns {string} - 설정값
 */
function getSecureConfig(key, defaultValue = '') {
  try {
    const properties = PropertiesService.getScriptProperties();
    const value = properties.getProperty(key);
    
    if (value === null || value === undefined) {
      // 기본값 설정
      setSecureConfig(key, defaultValue);
      return defaultValue;
    }
    
    return value;
    
  } catch (error) {
    logSecurityEvent('ERROR', 'Failed to get secure config', {
      key: key,
      error: error.message
    });
    return defaultValue;
  }
}

/**
 * 환경변수에 안전하게 값 저장
 * @param {string} key - 설정 키
 * @param {string} value - 저장할 값
 * @returns {boolean} - 성공 여부
 */
function setSecureConfig(key, value) {
  try {
    // 값 검증
    if (!isValidConfigKey(key)) {
      throw new Error('Invalid config key');
    }
    
    const sanitizedValue = sanitizeInput(value, 'general');
    if (sanitizedValue === null) {
      throw new Error('Invalid config value');
    }
    
    const properties = PropertiesService.getScriptProperties();
    properties.setProperty(key, sanitizedValue);
    
    logSecurityEvent('INFO', 'Config updated', {
      key: key,
      value: maskSensitiveInfo(sanitizedValue, 4)
    });
    
    return true;
    
  } catch (error) {
    logSecurityEvent('ERROR', 'Failed to set secure config', {
      key: key,
      error: error.message
    });
    return false;
  }
}

/**
 * 설정 키 유효성 검사
 */
function isValidConfigKey(key) {
  return Object.values(SECURE_CONFIG.ENV_KEYS).includes(key);
}

/**
 * 모든 설정 초기화
 */
function initializeSecureConfig() {
  return safeExecute(() => {
    Object.entries(SECURE_CONFIG.DEFAULTS).forEach(([key, value]) => {
      const envKey = SECURE_CONFIG.ENV_KEYS[key];
      if (envKey) {
        setSecureConfig(envKey, value);
      }
    });
    
    logSecurityEvent('INFO', 'Secure config initialized');
    return true;
  }, 'initializeSecureConfig', false);
}

// ========================================
// 🔒 보안 강화된 설정 시트 관리
// ========================================

/**
 * 보안 강화된 필터 설정 템플릿 생성
 */
function createFilterSettingsTemplateHorizontalSecure() {
  // 권한 검증
  if (!requireAdminPermission('createFilterSettingsTemplate')) {
    return;
  }
  
  return safeExecute(() => {
    const ss = SpreadsheetApp.getActiveSpreadsheet();
    let sheet = ss.getSheetByName("설정");
    if (!sheet) sheet = ss.insertSheet("설정");
    else sheet.clear();

    const headers = [
      "파레트 ID 검색어",    // A1
      "화주사 선택",         // B1
      "품목 키워드",         // C1
      "입고 시작일",         // D1
      "입고 종료일",         // E1
      "출력완료 포함 여부",   // F1
      "보관 상태 필터"        // G1
    ];

    // 헤더 설정
    sheet.getRange(1, 1, 1, headers.length).setValues([headers]);
    sheet.getRange(1, 1, 1, headers.length).setFontWeight("bold").setBackground("#eeeeee");
    sheet.setFrozenRows(1);

    // 열 너비 설정
    sheet.setColumnWidth(1, 220);
    for (let i = 2; i <= 7; i++) sheet.setColumnWidth(i, 160);

    // 체크박스 설정
    sheet.getRange(2, 6).insertCheckboxes();

    // 화주사 선택 구역
    sheet.getRange("A5:G5").merge()
      .setValue("화주사 선택")
      .setFontWeight("bold")
      .setBackground("#d9ead3")
      .setHorizontalAlignment("center");
    
    logSecurityEvent('INFO', 'Filter settings template created');
    
  }, 'createFilterSettingsTemplate', null);
}

/**
 * 보안 강화된 필터 드롭다운 업데이트
 */
function updateFilterDropdownsSecure() {
  return safeExecute(() => {
    const ss = SpreadsheetApp.getActiveSpreadsheet();
    const configSheet = ss.getSheetByName("설정");
    const sourceSheet = ss.getSheetByName("파레트 요약 정산");
    
    if (!configSheet || !sourceSheet) {
      throw new Error('필수 시트가 없습니다.');
    }

    const data = sourceSheet.getDataRange().getValues();
    const header = data[0];
    const vendorIdx = header.indexOf("화주사");
    const statusIdx = header.indexOf("상태");

    const vendorSet = new Set();
    const statusSet = new Set(["전체"]);

    // 데이터 검증 및 수집
    for (let i = 1; i < data.length; i++) {
      const vendor = sanitizeInput(data[i][vendorIdx], 'vendor');
      const status = sanitizeInput(data[i][statusIdx], 'general');
      
      if (vendor) vendorSet.add(vendor);
      if (status) statusSet.add(status);
    }

    const vendorList = Array.from(vendorSet).sort();
    const statusList = Array.from(statusSet).sort();

    // 체크박스 영역 초기화
    configSheet.getRange("A6:G20").clearContent()
      .removeCheckboxes()
      .setBorder(false, false, false, false, false, false);

    // 화주사 체크박스 생성
    const startRow = 6;
    const itemsPerColumn = 3;
    let col = 1;

    for (let i = 0; i < vendorList.length; i++) {
      const rowOffset = (i % itemsPerColumn) * 2;
      const row = startRow + rowOffset;
      const column = col + Math.floor(i / itemsPerColumn);

      const nameCell = configSheet.getRange(row, column);
      const checkboxCell = configSheet.getRange(row + 1, column);

      nameCell.setValue(vendorList[i])
        .setFontWeight("normal")
        .setHorizontalAlignment("center")
        .setBorder(true, true, true, true, false, false);
      checkboxCell.insertCheckboxes()
        .setBorder(true, true, true, true, false, false);
    }

    // 드롭다운 설정
    const statusRule = SpreadsheetApp.newDataValidation()
      .requireValueInList(statusList, true)
      .build();
    configSheet.getRange("G2").setDataValidation(statusRule);

    const vendorDropdownRule = SpreadsheetApp.newDataValidation()
      .requireValueInList(["전체"].concat(vendorList), true)
      .build();
    configSheet.getRange("B2").setDataValidation(vendorDropdownRule);

    // 선택된 화주사 자동 입력
    updateSelectedVendorsToB2();
    
    logSecurityEvent('INFO', 'Filter dropdowns updated', {
      vendorCount: vendorList.length,
      statusCount: statusList.length
    });
    
  }, 'updateFilterDropdowns', null);
}

/**
 * 선택된 화주사를 B2에 안전하게 업데이트
 */
function updateSelectedVendorsToB2() {
  return safeExecute(() => {
    const sheet = SpreadsheetApp.getActiveSpreadsheet().getSheetByName("설정");
    if (!sheet) return;

    const selectedVendors = [];
    for (let col = 1; col <= 7; col++) {
      for (let row = 6; row <= 20; row += 2) {
        const name = sheet.getRange(row, col).getValue();
        const checked = sheet.getRange(row + 1, col).getValue();
        
        if (name && checked === true) {
          const sanitizedVendor = sanitizeInput(name, 'vendor');
          if (sanitizedVendor) {
            selectedVendors.push(sanitizedVendor);
          }
        }
      }
    }
    
    const vendorText = selectedVendors.join(", ");
    sheet.getRange("B2").setValue(vendorText);
    
  }, 'updateSelectedVendorsToB2', null);
}

/**
 * 보안 강화된 파레트 ID 쿼리 파싱
 */
function parsePalletIdQuerySecure() {
  return safeExecute(() => {
    const sheet = SpreadsheetApp.getActiveSpreadsheet().getSheetByName("설정");
    if (!sheet) return { terms: [], regex: null };
    
    const raw = String(sheet.getRange("A2").getValue() || "");
    const sanitized = sanitizeInput(raw, 'general');
    
    if (!sanitized) return { terms: [], regex: null };
    
    const terms = sanitized.split(",")
      .map(s => sanitizeInput(s.trim(), 'palletId'))
      .filter(Boolean);
    
    if (!terms.length) return { terms: [], regex: null };

    const patterns = terms.map(t => {
      if (t.includes("_")) {
        return "(?:" + "^" + _esc_(t) + "$" + ")";
      } else {
        return "(?:" + "^" + _esc_(t) + "(?:_|$)" + ")";
      }
    });

    const regex = new RegExp(patterns.join("|"));
    return { terms, regex };
    
  }, 'parsePalletIdQuery', { terms: [], regex: null });
}

/**
 * 보안 강화된 필터 파라미터 가져오기
 */
function getFilterParamsSecure() {
  return safeExecute(() => {
    const ss = SpreadsheetApp.getActiveSpreadsheet();
    const cfg = ss.getSheetByName("설정");
    if (!cfg) return null;

    const vendors = getSelectedVendorsFromCheckboxesSecure();
    const b2Value = String(cfg.getRange("B2").getValue() || "");
    const b2Vendors = b2Value.split(",")
      .map(s => sanitizeInput(s.trim(), 'vendor'))
      .filter(Boolean);

    const finalVendors = vendors.length > 0 ? vendors : b2Vendors;

    return {
      palletQuery: parsePalletIdQuerySecure(),
      vendors: finalVendors,
      itemKeyword: sanitizeInput(cfg.getRange("C2").getValue(), 'product'),
      startDate: safeParseDate(cfg.getRange("D2").getValue()),
      endDate: safeParseDate(cfg.getRange("E2").getValue()),
      includePrinted: cfg.getRange("F2").getValue() === true,
      status: sanitizeInput(cfg.getRange("G2").getValue(), 'general') || "전체"
    };
    
  }, 'getFilterParams', null);
}

/**
 * 보안 강화된 화주사 선택 가져오기
 */
function getSelectedVendorsFromCheckboxesSecure() {
  return safeExecute(() => {
    const sheet = SpreadsheetApp.getActiveSpreadsheet().getSheetByName("설정");
    if (!sheet) return [];

    const selected = [];
    for (let col = 1; col <= 7; col++) {
      for (let row = 6; row <= 20; row += 2) {
        const name = sheet.getRange(row, col).getValue();
        const checked = sheet.getRange(row + 1, col).getValue();
        
        if (name && checked === true) {
          const sanitizedVendor = sanitizeInput(name, 'vendor');
          if (sanitizedVendor) {
            selected.push(sanitizedVendor);
          }
        }
      }
    }
    return selected;
  }, 'getSelectedVendorsFromCheckboxes', []);
}

// ========================================
// 🔒 자동화 설정 관리
// ========================================

/**
 * 보안 강화된 자동화 버튼 설정
 */
function setupAutoSyncButtonSecure() {
  // 권한 검증
  if (!requireAdminPermission('setupAutoSyncButton')) {
    return;
  }
  
  return safeExecute(() => {
    const sheet = SpreadsheetApp.getActiveSpreadsheet().getSheetByName("설정");
    if (!sheet) return;

    sheet.getRange("A18").setValue("자동화 ON/OFF")
      .setFontWeight("bold")
      .setBackground("#cfe2f3");
    sheet.getRange("A19").setValue("사용")
      .setFontWeight("bold")
      .setBackground("#d9ead3");
    
    const rule = SpreadsheetApp.newDataValidation()
      .requireValueInList(["사용", "중단"], true)
      .setAllowInvalid(false)
      .build();
    sheet.getRange("A19").setDataValidation(rule);
    
    logSecurityEvent('INFO', 'Auto sync button setup completed');
    
  }, 'setupAutoSyncButton', null);
}

/**
 * 보안 강화된 자동화 비활성화
 */
function disableAutoSyncSecure() {
  return safeExecute(() => {
    const sheet = SpreadsheetApp.getActiveSpreadsheet().getSheetByName("설정");
    if (!sheet) return;
    
    sheet.getRange("A19").setValue("중단");
    
    logSecurityEvent('INFO', 'Auto sync disabled automatically');
    
  }, 'disableAutoSync', null);
}

/**
 * 보안 강화된 자동 비활성화 트리거 설정
 */
function setAutoDisableTriggerSecure() {
  // 권한 검증
  if (!requireAdminPermission('setAutoDisableTrigger')) {
    return;
  }
  
  return safeExecute(() => {
    // 기존 트리거 삭제
    const triggers = ScriptApp.getProjectTriggers();
    triggers.forEach(trigger => {
      if (trigger.getHandlerFunction() === 'disableAutoSyncSecure') {
        ScriptApp.deleteTrigger(trigger);
      }
    });
    
    // 새 트리거 생성
    ScriptApp.newTrigger('disableAutoSyncSecure')
      .timeBased()
      .onMonthDay(1)
      .atHour(0)
      .create();
    
    logSecurityEvent('INFO', 'Auto disable trigger set');
    
  }, 'setAutoDisableTrigger', null);
}

// ========================================
// 🔄 기존 함수들의 보안 강화 래퍼
// ========================================

/**
 * 기존 함수들의 보안 강화 버전
 */
function createFilterSettingsTemplateHorizontal() {
  return createFilterSettingsTemplateHorizontalSecure();
}

function updateFilterDropdowns() {
  return updateFilterDropdownsSecure();
}

function parsePalletIdQuery() {
  return parsePalletIdQuerySecure();
}

function getFilterParams() {
  return getFilterParamsSecure();
}

function getSelectedVendorsFromCheckboxes() {
  return getSelectedVendorsFromCheckboxesSecure();
}

function getFilterVendorList() {
  return getSelectedVendorsFromCheckboxesSecure();
}

function setupAutoSyncButton() {
  return setupAutoSyncButtonSecure();
}

function disableAutoSync() {
  return disableAutoSyncSecure();
}

function setAutoDisableTrigger() {
  return setAutoDisableTriggerSecure();
}

// 정규식 이스케이프 유틸 (기존 함수 유지)
function _esc_(s) {
  return String(s).replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}




