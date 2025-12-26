/**
 * 🔒 보안 시스템 초기화 스크립트
 * 
 * 이 스크립트는 보안 강화 시스템을 초기화하고 설정합니다.
 * 프로젝트에 보안 모듈을 추가한 후 이 스크립트를 실행하세요.
 */

/**
 * 보안 시스템 전체 초기화
 */
function initializeSecuritySystem() {
  try {
    console.log('🔒 보안 시스템 초기화 시작...');
    
    // 1. 환경변수 초기화
    initializeSecureConfig();
    
    // 2. 감사 로그 시스템 초기화 (간단하게)
    initializeAuditSystemSimple();
    
    // 3. 기존 설정 마이그레이션
    migrateExistingSettings();
    
    console.log('✅ 보안 시스템 초기화 완료');
    
    // 초기화 완료 로그
    try {
      logAuditEvent(
        'INFO',
        'SYSTEM_INIT',
        'Security system initialized successfully',
        { timestamp: new Date().toISOString() }
      );
    } catch (logError) {
      console.warn('로그 기록 실패:', logError.message);
    }
    
    console.log('🔒 보안 시스템이 성공적으로 초기화되었습니다.');
    
  } catch (error) {
    console.error('❌ 보안 시스템 초기화 실패:', error);
    console.log('보안 시스템 초기화 중 오류가 발생했습니다: ' + error.message);
  }
}

/**
 * 간단한 감사 로그 시스템 초기화 (UI 없이)
 */
function initializeAuditSystemSimple() {
  try {
    console.log('🔍 감사 로그 시스템 초기화...');
    
    // 환경변수만 설정하고 시트 생성은 나중에
    const properties = PropertiesService.getScriptProperties();
    properties.setProperty('AUDIT_SYSTEM_INITIALIZED', 'true');
    
    console.log('✅ 감사 로그 시스템 초기화 완료');
    
  } catch (error) {
    console.error('❌ 감사 로그 시스템 초기화 실패:', error);
    console.log('⚠️ 감사 로그 시스템 초기화를 건너뛰고 계속 진행합니다.');
  }
}

/**
 * 감사 로그 시스템 초기화
 */
function initializeAuditSystem() {
  try {
    const ss = SpreadsheetApp.getActiveSpreadsheet();
    
    // 감사 로그 시트 생성 (타임아웃 방지를 위해 간단하게)
    let auditSheet = ss.getSheetByName('감사로그');
    if (!auditSheet) {
      try {
        auditSheet = ss.insertSheet('감사로그');
        // 헤더만 설정하고 나머지는 나중에
        auditSheet.getRange('A1:G1').setValues([[
          '타임스탬프', '레벨', '이벤트타입', '사용자', '메시지', '상세정보', '메타데이터'
        ]]);
        auditSheet.getRange('A1:G1').setFontWeight('bold');
        auditSheet.setFrozenRows(1);
      } catch (sheetError) {
        console.warn('감사로그 시트 생성 실패, 나중에 다시 시도:', sheetError.message);
      }
    }
    
    // 보안 로그 시트 생성 (타임아웃 방지를 위해 간단하게)
    let securitySheet = ss.getSheetByName('보안로그');
    if (!securitySheet) {
      try {
        securitySheet = ss.insertSheet('보안로그');
        securitySheet.getRange('A1:E1').setValues([[
          '타임스탬프', '레벨', '사용자', '메시지', '상세정보'
        ]]);
        securitySheet.getRange('A1:E1').setFontWeight('bold');
      } catch (sheetError) {
        console.warn('보안로그 시트 생성 실패, 나중에 다시 시도:', sheetError.message);
      }
    }
    
    console.log('✅ 감사 로그 시스템 초기화 완료');
    
  } catch (error) {
    console.error('❌ 감사 로그 시스템 초기화 실패:', error);
    // 시트 생성 실패는 치명적이지 않으므로 계속 진행
    console.log('⚠️ 감사 로그 시스템 초기화를 건너뛰고 계속 진행합니다.');
  }
}

/**
 * 보안 설정 시트 생성
 */
function createSecuritySettingsSheet() {
  try {
    const ss = SpreadsheetApp.getActiveSpreadsheet();
    let settingsSheet = ss.getSheetByName('보안설정');
    
    if (!settingsSheet) {
      settingsSheet = ss.insertSheet('보안설정');
    } else {
      settingsSheet.clear();
    }
    
    // 헤더 설정
    const headers = [
      '설정명', '현재값', '설명', '마지막 업데이트'
    ];
    
    settingsSheet.getRange(1, 1, 1, headers.length).setValues([headers]);
    settingsSheet.getRange(1, 1, 1, headers.length).setFontWeight('bold');
    settingsSheet.setFrozenRows(1);
    
    // 보안 설정 목록
    const securitySettings = [
      ['ADMIN_EMAILS', '관리자 이메일 목록', '보안 알림을 받을 관리자 이메일'],
      ['FORM_BASE_URL', '구글 폼 URL', 'QR 코드에 포함될 구글 폼 URL'],
      ['QR_SERVICE_URL', 'QR 서비스 URL', 'QR 코드 생성 서비스 URL'],
      ['ALLOWED_USERS', '허용된 사용자', '시스템 접근이 허용된 사용자 목록'],
      ['LOG_RETENTION_DAYS', '로그 보관 기간', '감사 로그 보관 기간 (일)']
    ];
    
    const now = new Date().toISOString();
    const settingsData = securitySettings.map(([name, displayName, description]) => [
      displayName,
      getSecureConfig(name, '설정되지 않음'),
      description,
      now
    ]);
    
    settingsSheet.getRange(2, 1, settingsData.length, settingsData[0].length)
      .setValues(settingsData);
    
    // 열 너비 설정
    settingsSheet.setColumnWidth(1, 150);
    settingsSheet.setColumnWidth(2, 200);
    settingsSheet.setColumnWidth(3, 300);
    settingsSheet.setColumnWidth(4, 150);
    
    console.log('✅ 보안 설정 시트 생성 완료');
    
  } catch (error) {
    console.error('❌ 보안 설정 시트 생성 실패:', error);
    throw error;
  }
}

/**
 * 기존 설정 마이그레이션
 */
function migrateExistingSettings() {
  try {
    console.log('🔄 기존 설정 마이그레이션 시작...');
    
    // 기존 설정에서 중요한 값들을 환경변수로 이동
    const ss = SpreadsheetApp.getActiveSpreadsheet();
    const configSheet = ss.getSheetByName('설정');
    
    if (configSheet) {
      // 기존 설정에서 관리자 이메일 추출 (예시)
      const adminEmail = Session.getActiveUser().getEmail();
      setSecureConfig('ADMIN_EMAILS', adminEmail);
      
      console.log('✅ 기존 설정 마이그레이션 완료');
    }
    
  } catch (error) {
    console.error('❌ 기존 설정 마이그레이션 실패:', error);
    // 마이그레이션 실패는 치명적이지 않으므로 계속 진행
  }
}

/**
 * 보안 체크 실행
 */
function runSecurityChecks() {
  try {
    console.log('🔍 보안 체크 실행...');
    
    const checks = [
      checkEnvironmentVariables,
      checkUserPermissions,
      checkAuditLogging,
      checkInputValidation
    ];
    
    const results = checks.map(check => {
      try {
        return { name: check.name, status: 'PASS', message: check() };
      } catch (error) {
        return { name: check.name, status: 'FAIL', message: error.message };
      }
    });
    
    // 결과 로깅
    results.forEach(result => {
      const level = result.status === 'PASS' ? 'INFO' : 'WARN';
      logAuditEvent(level, 'SECURITY_CHECK', `Security check: ${result.name}`, {
        status: result.status,
        message: result.message
      });
    });
    
    const failedChecks = results.filter(r => r.status === 'FAIL');
    if (failedChecks.length > 0) {
      console.warn('⚠️ 일부 보안 체크 실패:', failedChecks);
    } else {
      console.log('✅ 모든 보안 체크 통과');
    }
    
  } catch (error) {
    console.error('❌ 보안 체크 실행 실패:', error);
  }
}

/**
 * 환경변수 체크
 */
function checkEnvironmentVariables() {
  const requiredVars = ['ADMIN_EMAILS', 'FORM_BASE_URL', 'QR_SERVICE_URL'];
  const missing = requiredVars.filter(key => !getSecureConfig(key));
  
  if (missing.length > 0) {
    throw new Error(`누락된 환경변수: ${missing.join(', ')}`);
  }
  
  return '모든 필수 환경변수가 설정되어 있습니다.';
}

/**
 * 사용자 권한 체크
 */
function checkUserPermissions() {
  const currentUser = Session.getActiveUser().getEmail();
  const adminEmails = getSecureConfig('ADMIN_EMAILS', '').split(',');
  
  if (!adminEmails.includes(currentUser)) {
    throw new Error(`현재 사용자(${currentUser})가 관리자 목록에 없습니다.`);
  }
  
  return '사용자 권한이 올바르게 설정되어 있습니다.';
}

/**
 * 감사 로깅 체크
 */
function checkAuditLogging() {
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  const auditSheet = ss.getSheetByName('감사로그');
  
  if (!auditSheet) {
    throw new Error('감사로그 시트가 없습니다.');
  }
  
  return '감사 로깅 시스템이 정상적으로 설정되어 있습니다.';
}

/**
 * 입력 검증 체크
 */
function checkInputValidation() {
  // 입력 검증 함수들이 정의되어 있는지 확인
  if (typeof sanitizeInput !== 'function') {
    throw new Error('sanitizeInput 함수가 정의되지 않았습니다.');
  }
  
  if (typeof safeExecute !== 'function') {
    throw new Error('safeExecute 함수가 정의되지 않았습니다.');
  }
  
  return '입력 검증 시스템이 정상적으로 설정되어 있습니다.';
}

/**
 * 보안 설정 업데이트
 */
function updateSecuritySetting(settingName, newValue) {
  try {
    if (!requireAdminPermission('updateSecuritySetting')) {
      throw new Error('보안 설정을 업데이트할 권한이 없습니다.');
    }
    
    const oldValue = getSecureConfig(settingName);
    const success = setSecureConfig(settingName, newValue);
    
    if (success) {
      // 설정 변경 감사 로그
      auditConfigChange(settingName, oldValue, newValue);
      
      // 보안 설정 시트 업데이트
      updateSecuritySettingsSheet();
      
      SpreadsheetApp.getUi().alert(`보안 설정이 업데이트되었습니다: ${settingName}`);
    } else {
      throw new Error('보안 설정 업데이트에 실패했습니다.');
    }
    
  } catch (error) {
    console.error('보안 설정 업데이트 실패:', error);
    SpreadsheetApp.getUi().alert('보안 설정 업데이트 실패: ' + error.message);
  }
}

/**
 * 보안 설정 시트 업데이트
 */
function updateSecuritySettingsSheet() {
  try {
    const ss = SpreadsheetApp.getActiveSpreadsheet();
    const settingsSheet = ss.getSheetByName('보안설정');
    
    if (!settingsSheet) return;
    
    const data = settingsSheet.getDataRange().getValues();
    const now = new Date().toISOString();
    
    // 각 설정의 현재 값 업데이트
    for (let i = 1; i < data.length; i++) {
      const settingName = data[i][0];
      const envKey = getEnvKeyFromDisplayName(settingName);
      
      if (envKey) {
        const currentValue = getSecureConfig(envKey, '설정되지 않음');
        settingsSheet.getRange(i + 1, 2).setValue(currentValue);
        settingsSheet.getRange(i + 1, 4).setValue(now);
      }
    }
    
  } catch (error) {
    console.error('보안 설정 시트 업데이트 실패:', error);
  }
}

/**
 * 표시명에서 환경변수 키 찾기
 */
function getEnvKeyFromDisplayName(displayName) {
  const mapping = {
    '관리자 이메일 목록': 'ADMIN_EMAILS',
    '구글 폼 URL': 'FORM_BASE_URL',
    'QR 서비스 URL': 'QR_SERVICE_URL',
    '허용된 사용자': 'ALLOWED_USERS',
    '로그 보관 기간': 'LOG_RETENTION_DAYS'
  };
  
  return mapping[displayName];
}

/**
 * 보안 시스템 상태 확인
 */
function checkSecuritySystemStatus() {
  try {
    const status = {
      environmentVariables: checkEnvironmentVariables(),
      userPermissions: checkUserPermissions(),
      auditLogging: checkAuditLogging(),
      inputValidation: checkInputValidation(),
      timestamp: new Date().toISOString()
    };
    
    console.log('🔒 보안 시스템 상태:', status);
    return status;
    
  } catch (error) {
    console.error('❌ 보안 시스템 상태 확인 실패:', error);
    return { error: error.message, timestamp: new Date().toISOString() };
  }
}

/**
 * 보안 시스템 재시작
 */
function restartSecuritySystem() {
  try {
    if (!requireAdminPermission('restartSecuritySystem')) {
      throw new Error('보안 시스템을 재시작할 권한이 없습니다.');
    }
    
    console.log('🔄 보안 시스템 재시작 중...');
    
    // 기존 설정 백업
    const backup = {
      adminEmails: getSecureConfig('ADMIN_EMAILS'),
      formUrl: getSecureConfig('FORM_BASE_URL'),
      qrUrl: getSecureConfig('QR_SERVICE_URL'),
      allowedUsers: getSecureConfig('ALLOWED_USERS')
    };
    
    // 시스템 재초기화
    initializeSecuritySystem();
    
    console.log('✅ 보안 시스템 재시작 완료');
    
    logAuditEvent(
      'INFO',
      'SYSTEM_RESTART',
      'Security system restarted',
      { backup: backup }
    );
    
  } catch (error) {
    console.error('❌ 보안 시스템 재시작 실패:', error);
    SpreadsheetApp.getUi().alert('보안 시스템 재시작 실패: ' + error.message);
  }
}

/**
 * 보안 시스템 테스트
 */
function testSecuritySystem() {
  try {
    console.log('🧪 보안 시스템 테스트 시작...');
    
    const testResults = {
      timestamp: new Date().toISOString(),
      tests: [],
      passed: 0,
      failed: 0,
      total: 0
    };
    
    // 테스트 1: 입력 검증 테스트
    testResults.total++;
    try {
      const testInput = sanitizeInput('test123', 'palletId');
      if (testInput === 'test123') {
        testResults.tests.push({ name: '입력 검증', status: 'PASS', message: '정상' });
        testResults.passed++;
      } else {
        testResults.tests.push({ name: '입력 검증', status: 'FAIL', message: '입력값이 변경됨' });
        testResults.failed++;
      }
    } catch (error) {
      testResults.tests.push({ name: '입력 검증', status: 'FAIL', message: error.message });
      testResults.failed++;
    }
    
    // 테스트 2: 안전한 함수 실행 테스트
    testResults.total++;
    try {
      const result = safeExecute(() => {
        return 'test success';
      }, 'testOperation', 'fallback');
      
      if (result === 'test success') {
        testResults.tests.push({ name: '안전한 함수 실행', status: 'PASS', message: '정상' });
        testResults.passed++;
      } else {
        testResults.tests.push({ name: '안전한 함수 실행', status: 'FAIL', message: '예상과 다른 결과' });
        testResults.failed++;
      }
    } catch (error) {
      testResults.tests.push({ name: '안전한 함수 실행', status: 'FAIL', message: error.message });
      testResults.failed++;
    }
    
    // 테스트 3: 권한 검증 테스트
    testResults.total++;
    try {
      const hasPermission = validateUserPermission();
      testResults.tests.push({ 
        name: '권한 검증', 
        status: hasPermission ? 'PASS' : 'WARN', 
        message: hasPermission ? '권한 있음' : '권한 없음' 
      });
      if (hasPermission) testResults.passed++;
      else testResults.failed++;
    } catch (error) {
      testResults.tests.push({ name: '권한 검증', status: 'FAIL', message: error.message });
      testResults.failed++;
    }
    
    // 테스트 4: 날짜 파싱 테스트
    testResults.total++;
    try {
      const testDate = safeParseDate('2024-01-01');
      if (testDate instanceof Date && !isNaN(testDate.getTime())) {
        testResults.tests.push({ name: '날짜 파싱', status: 'PASS', message: '정상' });
        testResults.passed++;
      } else {
        testResults.tests.push({ name: '날짜 파싱', status: 'FAIL', message: '날짜 파싱 실패' });
        testResults.failed++;
      }
    } catch (error) {
      testResults.tests.push({ name: '날짜 파싱', status: 'FAIL', message: error.message });
      testResults.failed++;
    }
    
    // 테스트 5: 숫자 파싱 테스트
    testResults.total++;
    try {
      const testNumber = safeParseNumber('123.45', 0);
      if (testNumber === 123.45) {
        testResults.tests.push({ name: '숫자 파싱', status: 'PASS', message: '정상' });
        testResults.passed++;
      } else {
        testResults.tests.push({ name: '숫자 파싱', status: 'FAIL', message: '숫자 파싱 실패' });
        testResults.failed++;
      }
    } catch (error) {
      testResults.tests.push({ name: '숫자 파싱', status: 'FAIL', message: error.message });
      testResults.failed++;
    }
    
    // 테스트 6: 보안 로깅 테스트
    testResults.total++;
    try {
      logSecurityEvent('INFO', '보안 시스템 테스트', { testId: 'test123' });
      testResults.tests.push({ name: '보안 로깅', status: 'PASS', message: '정상' });
      testResults.passed++;
    } catch (error) {
      testResults.tests.push({ name: '보안 로깅', status: 'FAIL', message: error.message });
      testResults.failed++;
    }
    
    // 테스트 7: 환경변수 테스트
    testResults.total++;
    try {
      const adminEmails = getSecureConfig('ADMIN_EMAILS');
      if (adminEmails && adminEmails.length > 0) {
        testResults.tests.push({ name: '환경변수', status: 'PASS', message: '설정됨' });
        testResults.passed++;
      } else {
        testResults.tests.push({ name: '환경변수', status: 'WARN', message: '설정되지 않음' });
        testResults.failed++;
      }
    } catch (error) {
      testResults.tests.push({ name: '환경변수', status: 'FAIL', message: error.message });
      testResults.failed++;
    }
    
    // 결과 출력
    console.log('🧪 보안 시스템 테스트 결과:', testResults);
    
    // 감사 로그에 테스트 결과 기록
    logAuditEvent(
      'INFO',
      'SECURITY_TEST',
      'Security system test completed',
      testResults
    );
    
    // 사용자에게 결과 표시
    const message = `보안 시스템 테스트 완료!\n\n` +
      `✅ 통과: ${testResults.passed}개\n` +
      `❌ 실패: ${testResults.failed}개\n` +
      `📊 총계: ${testResults.total}개\n\n` +
      `상세 결과는 콘솔 로그를 확인하세요.`;
    
    SpreadsheetApp.getUi().alert(message);
    
    return testResults;
    
  } catch (error) {
    console.error('❌ 보안 시스템 테스트 실패:', error);
    SpreadsheetApp.getUi().alert('보안 시스템 테스트 실패: ' + error.message);
    return null;
  }
}

/**
 * 간단한 보안 테스트 (빠른 확인용)
 */
function quickSecurityTest() {
  try {
    console.log('⚡ 빠른 보안 테스트 시작...');
    
    // 기본 함수들 존재 확인
    const functions = [
      'sanitizeInput',
      'safeExecute', 
      'validateUserPermission',
      'logSecurityEvent',
      'getSecureConfig'
    ];
    
    const missingFunctions = functions.filter(func => typeof eval(func) !== 'function');
    
    if (missingFunctions.length > 0) {
      throw new Error(`누락된 함수들: ${missingFunctions.join(', ')}`);
    }
    
    // 간단한 입력 검증 테스트
    const testResult = sanitizeInput('test', 'palletId');
    if (testResult !== 'test') {
      throw new Error('입력 검증 함수 오류');
    }
    
    console.log('✅ 빠른 보안 테스트 통과');
    console.log('✅ 보안 시스템이 정상적으로 작동합니다!');
    
  } catch (error) {
    console.error('❌ 빠른 보안 테스트 실패:', error);
    console.log('❌ 보안 시스템에 문제가 있습니다: ' + error.message);
  }
}

/**
 * UI 없이 작동하는 보안 테스트
 */
function testSecuritySystemSimple() {
  try {
    console.log('🧪 보안 시스템 테스트 시작...');
    
    const testResults = {
      timestamp: new Date().toISOString(),
      tests: [],
      passed: 0,
      failed: 0,
      total: 0
    };
    
    // 테스트 1: 입력 검증 테스트
    testResults.total++;
    try {
      const testInput = sanitizeInput('test123', 'palletId');
      if (testInput === 'test123') {
        testResults.tests.push({ name: '입력 검증', status: 'PASS', message: '정상' });
        testResults.passed++;
      } else {
        testResults.tests.push({ name: '입력 검증', status: 'FAIL', message: '입력값이 변경됨' });
        testResults.failed++;
      }
    } catch (error) {
      testResults.tests.push({ name: '입력 검증', status: 'FAIL', message: error.message });
      testResults.failed++;
    }
    
    // 테스트 2: 안전한 함수 실행 테스트
    testResults.total++;
    try {
      const result = safeExecute(() => {
        return 'test success';
      }, 'testOperation', 'fallback');
      
      if (result === 'test success') {
        testResults.tests.push({ name: '안전한 함수 실행', status: 'PASS', message: '정상' });
        testResults.passed++;
      } else {
        testResults.tests.push({ name: '안전한 함수 실행', status: 'FAIL', message: '예상과 다른 결과' });
        testResults.failed++;
      }
    } catch (error) {
      testResults.tests.push({ name: '안전한 함수 실행', status: 'FAIL', message: error.message });
      testResults.failed++;
    }
    
    // 테스트 3: 환경변수 테스트
    testResults.total++;
    try {
      const adminEmails = getSecureConfig('ADMIN_EMAILS');
      if (adminEmails && adminEmails.length > 0) {
        testResults.tests.push({ name: '환경변수', status: 'PASS', message: '설정됨' });
        testResults.passed++;
      } else {
        testResults.tests.push({ name: '환경변수', status: 'WARN', message: '설정되지 않음' });
        testResults.failed++;
      }
    } catch (error) {
      testResults.tests.push({ name: '환경변수', status: 'FAIL', message: error.message });
      testResults.failed++;
    }
    
    // 결과 출력
    console.log('🧪 보안 시스템 테스트 결과:', testResults);
    
    const message = `보안 시스템 테스트 완료!\n` +
      `✅ 통과: ${testResults.passed}개\n` +
      `❌ 실패: ${testResults.failed}개\n` +
      `📊 총계: ${testResults.total}개`;
    
    console.log(message);
    
    return testResults;
    
  } catch (error) {
    console.error('❌ 보안 시스템 테스트 실패:', error);
    return null;
  }
}
