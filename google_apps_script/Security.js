/**
 * 🔒 3PL 자동화 시스템 보안 모듈
 * 
 * 주요 기능:
 * - 입력 검증 및 데이터 정제
 * - 안전한 에러 처리
 * - 보안 감사 로그
 * - 민감한 정보 보호
 * - 권한 검증
 */

// ========================================
// 🔐 보안 설정 및 상수
// ========================================

const SECURITY_CONFIG = {
  // 최대 입력 길이 제한
  MAX_INPUT_LENGTH: 1000,
  MAX_PALLET_ID_LENGTH: 50,
  MAX_VENDOR_NAME_LENGTH: 100,
  MAX_PRODUCT_NAME_LENGTH: 200,
  
  // 허용된 문자 패턴
  ALLOWED_PALLET_ID_PATTERN: /^[A-Za-z0-9_-]+$/,
  ALLOWED_VENDOR_PATTERN: /^[가-힣A-Za-z0-9\s&.-]+$/,
  ALLOWED_PRODUCT_PATTERN: /^[가-힣A-Za-z0-9\s&.-]+$/,
  
  // 금지된 키워드 (XSS, SQL 인젝션 등)
  FORBIDDEN_PATTERNS: [
    /<script/i,
    /javascript:/i,
    /on\w+\s*=/i,
    /union\s+select/i,
    /drop\s+table/i,
    /delete\s+from/i,
    /insert\s+into/i,
    /update\s+set/i
  ],
  
  // 로그 레벨
  LOG_LEVELS: {
    ERROR: 'ERROR',
    WARN: 'WARN',
    INFO: 'INFO',
    DEBUG: 'DEBUG'
  }
};

// ========================================
// 🛡️ 입력 검증 및 데이터 정제
// ========================================

/**
 * 입력값을 안전하게 정제하고 검증
 * @param {*} input - 검증할 입력값
 * @param {string} type - 입력 타입 ('palletId', 'vendor', 'product', 'general')
 * @param {boolean} allowEmpty - 빈 값 허용 여부
 * @returns {string|null} - 정제된 값 또는 null
 */
function sanitizeInput(input, type = 'general', allowEmpty = true) {
  try {
    // null/undefined 처리
    if (input === null || input === undefined) {
      return allowEmpty ? '' : null;
    }
    
    // 문자열 변환 및 공백 제거
    let sanitized = String(input).trim();
    
    // 빈 값 처리
    if (!sanitized) {
      return allowEmpty ? '' : null;
    }
    
    // 길이 제한 검사
    const maxLength = getMaxLengthForType(type);
    if (sanitized.length > maxLength) {
      logSecurityEvent('WARN', `Input too long for type ${type}`, {
        input: sanitized.substring(0, 50) + '...',
        maxLength: maxLength
      });
      sanitized = sanitized.substring(0, maxLength);
    }
    
    // 금지된 패턴 검사
    if (containsForbiddenPattern(sanitized)) {
      logSecurityEvent('ERROR', 'Forbidden pattern detected', {
        input: sanitized,
        type: type
      });
      return null;
    }
    
    // 타입별 특수 검증
    if (!validateByType(sanitized, type)) {
      logSecurityEvent('WARN', `Invalid format for type ${type}`, {
        input: sanitized
      });
      return null;
    }
    
    return sanitized;
    
  } catch (error) {
    logSecurityEvent('ERROR', 'Input sanitization failed', {
      error: error.message,
      input: String(input).substring(0, 100),
      type: type
    });
    return null;
  }
}

/**
 * 타입별 최대 길이 반환
 */
function getMaxLengthForType(type) {
  switch (type) {
    case 'palletId': return SECURITY_CONFIG.MAX_PALLET_ID_LENGTH;
    case 'vendor': return SECURITY_CONFIG.MAX_VENDOR_NAME_LENGTH;
    case 'product': return SECURITY_CONFIG.MAX_PRODUCT_NAME_LENGTH;
    default: return SECURITY_CONFIG.MAX_INPUT_LENGTH;
  }
}

/**
 * 금지된 패턴 포함 여부 검사
 */
function containsForbiddenPattern(input) {
  return SECURITY_CONFIG.FORBIDDEN_PATTERNS.some(pattern => pattern.test(input));
}

/**
 * 타입별 형식 검증
 */
function validateByType(input, type) {
  switch (type) {
    case 'palletId':
      return SECURITY_CONFIG.ALLOWED_PALLET_ID_PATTERN.test(input);
    case 'vendor':
      return SECURITY_CONFIG.ALLOWED_VENDOR_PATTERN.test(input);
    case 'product':
      return SECURITY_CONFIG.ALLOWED_PRODUCT_PATTERN.test(input);
    default:
      return true; // 일반 입력은 기본 검증만
  }
}

// ========================================
// 🔒 안전한 에러 처리
// ========================================

/**
 * 안전한 함수 실행 래퍼
 * @param {Function} func - 실행할 함수
 * @param {string} operation - 작업명
 * @param {*} fallbackValue - 실패 시 반환값
 * @returns {*} - 함수 결과 또는 fallbackValue
 */
function safeExecute(func, operation, fallbackValue = null) {
  try {
    return func();
  } catch (error) {
    logSecurityEvent('ERROR', `Operation failed: ${operation}`, {
      error: error.message,
      stack: error.stack ? error.stack.substring(0, 500) : 'No stack trace'
    });
    
    // 사용자에게는 일반적인 메시지만 표시
    if (typeof SpreadsheetApp !== 'undefined') {
      SpreadsheetApp.getUi().alert(`작업 중 오류가 발생했습니다: ${operation}`);
    }
    
    return fallbackValue;
  }
}

/**
 * 안전한 시트 작업
 * @param {Function} sheetOperation - 시트 작업 함수
 * @param {string} operation - 작업명
 * @returns {boolean} - 성공 여부
 */
function safeSheetOperation(sheetOperation, operation) {
  return safeExecute(() => {
    sheetOperation();
    return true;
  }, operation, false);
}

// ========================================
// 📊 보안 감사 로그
// ========================================

/**
 * 보안 이벤트 로깅
 * @param {string} level - 로그 레벨
 * @param {string} message - 로그 메시지
 * @param {Object} details - 추가 정보
 */
function logSecurityEvent(level, message, details = {}) {
  try {
    const timestamp = new Date().toISOString();
    const userEmail = Session.getActiveUser().getEmail();
    
    const logEntry = {
      timestamp: timestamp,
      level: level,
      user: userEmail,
      message: message,
      details: details
    };
    
    // 콘솔 로그
    console.log(`[${level}] ${message}`, logEntry);
    
    // 스프레드시트에 로그 저장 (선택사항)
    if (level === 'ERROR' || level === 'WARN') {
      saveSecurityLogToSheet(logEntry);
    }
    
  } catch (error) {
    console.error('Failed to log security event:', error);
  }
}

/**
 * 보안 로그를 시트에 저장
 */
function saveSecurityLogToSheet(logEntry) {
  try {
    const ss = SpreadsheetApp.getActiveSpreadsheet();
    let logSheet = ss.getSheetByName('보안로그');
    
    if (!logSheet) {
      logSheet = ss.insertSheet('보안로그');
      logSheet.getRange('A1:E1').setValues([[
        '타임스탬프', '레벨', '사용자', '메시지', '상세정보'
      ]]);
      logSheet.getRange('A1:E1').setFontWeight('bold');
    }
    
    const row = [
      logEntry.timestamp,
      logEntry.level,
      logEntry.user,
      logEntry.message,
      JSON.stringify(logEntry.details)
    ];
    
    logSheet.appendRow(row);
    
    // 로그가 너무 많아지면 오래된 것 삭제 (최근 1000개만 유지)
    const maxRows = 1000;
    if (logSheet.getLastRow() > maxRows) {
      const rowsToDelete = logSheet.getLastRow() - maxRows;
      logSheet.deleteRows(2, rowsToDelete);
    }
    
  } catch (error) {
    console.error('Failed to save security log to sheet:', error);
  }
}

// ========================================
// 🔐 권한 및 접근 제어
// ========================================

/**
 * 사용자 권한 검증
 * @param {Array} allowedUsers - 허용된 사용자 이메일 목록
 * @returns {boolean} - 권한 여부
 */
function validateUserPermission(allowedUsers = []) {
  try {
    const currentUser = Session.getActiveUser().getEmail();
    
    // 관리자 계정은 항상 허용
    const adminEmails = [
      'jjay220304@gmail.com' // 프로젝트 소유자
    ];
    
    if (adminEmails.includes(currentUser)) {
      return true;
    }
    
    // 허용된 사용자 목록 확인
    if (allowedUsers.length > 0 && !allowedUsers.includes(currentUser)) {
      logSecurityEvent('WARN', 'Unauthorized access attempt', {
        user: currentUser,
        allowedUsers: allowedUsers
      });
      return false;
    }
    
    return true;
    
  } catch (error) {
    logSecurityEvent('ERROR', 'Permission validation failed', {
      error: error.message
    });
    return false;
  }
}

/**
 * 민감한 작업 전 권한 확인
 * @param {string} operation - 작업명
 * @returns {boolean} - 권한 여부
 */
function requireAdminPermission(operation) {
  const hasPermission = validateUserPermission();
  
  if (!hasPermission) {
    logSecurityEvent('ERROR', 'Admin permission required', {
      operation: operation,
      user: Session.getActiveUser().getEmail()
    });
    
    if (typeof SpreadsheetApp !== 'undefined') {
      SpreadsheetApp.getUi().alert('이 작업을 수행할 권한이 없습니다.');
    }
  }
  
  return hasPermission;
}

// ========================================
// 🔒 민감한 정보 보호
// ========================================

/**
 * 민감한 정보 마스킹
 * @param {string} text - 마스킹할 텍스트
 * @param {number} visibleChars - 보여줄 문자 수
 * @returns {string} - 마스킹된 텍스트
 */
function maskSensitiveInfo(text, visibleChars = 4) {
  if (!text || text.length <= visibleChars) {
    return '***';
  }
  
  const masked = '*'.repeat(text.length - visibleChars);
  return masked + text.substring(text.length - visibleChars);
}

/**
 * 안전한 URL 생성 (하드코딩된 URL 제거)
 * @param {string} baseUrl - 기본 URL
 * @param {Object} params - URL 파라미터
 * @returns {string} - 안전한 URL
 */
function createSafeUrl(baseUrl, params = {}) {
  try {
    // URL 검증
    if (!isValidUrl(baseUrl)) {
      throw new Error('Invalid base URL');
    }
    
    // 파라미터 인코딩
    const encodedParams = Object.keys(params)
      .filter(key => params[key] !== null && params[key] !== undefined)
      .map(key => `${encodeURIComponent(key)}=${encodeURIComponent(String(params[key]))}`)
      .join('&');
    
    return encodedParams ? `${baseUrl}?${encodedParams}` : baseUrl;
    
  } catch (error) {
    logSecurityEvent('ERROR', 'Failed to create safe URL', {
      error: error.message,
      baseUrl: baseUrl
    });
    return '';
  }
}

/**
 * URL 유효성 검사
 */
function isValidUrl(string) {
  try {
    new URL(string);
    return true;
  } catch (_) {
    return false;
  }
}

// ========================================
// 🛠️ 유틸리티 함수
// ========================================

/**
 * 안전한 날짜 파싱
 * @param {*} input - 날짜 입력값
 * @returns {Date|null} - 파싱된 날짜 또는 null
 */
function safeParseDate(input) {
  try {
    if (!input) return null;
    
    // 이미 Date 객체인 경우
    if (input instanceof Date) {
      return isValidDate(input) ? input : null;
    }
    
    // 문자열 정제
    const cleanInput = sanitizeInput(input, 'general');
    if (!cleanInput) return null;
    
    // 날짜 파싱 시도
    const parsed = new Date(cleanInput);
    return isValidDate(parsed) ? parsed : null;
    
  } catch (error) {
    logSecurityEvent('WARN', 'Date parsing failed', {
      input: String(input).substring(0, 50),
      error: error.message
    });
    return null;
  }
}

/**
 * 날짜 유효성 검사
 */
function isValidDate(date) {
  return date instanceof Date && !isNaN(date.getTime());
}

/**
 * 안전한 숫자 변환
 * @param {*} input - 입력값
 * @param {number} defaultValue - 기본값
 * @returns {number} - 변환된 숫자
 */
function safeParseNumber(input, defaultValue = 0) {
  try {
    const sanitized = sanitizeInput(input, 'general');
    if (!sanitized) return defaultValue;
    
    const parsed = parseFloat(sanitized);
    return isNaN(parsed) ? defaultValue : parsed;
    
  } catch (error) {
    logSecurityEvent('WARN', 'Number parsing failed', {
      input: String(input).substring(0, 50),
      error: error.message
    });
    return defaultValue;
  }
}

// ========================================
// 🔄 기존 함수들의 보안 강화 래퍼
// ========================================

/**
 * 기존 tryParseDate 함수의 보안 강화 버전
 */
function secureTryParseDate(input) {
  return safeParseDate(input);
}

/**
 * 기존 isValidDate 함수의 보안 강화 버전
 */
function secureIsValidDate(d) {
  return isValidDate(d);
}

/**
 * 안전한 시트 이름 생성
 * @param {string} name - 원본 이름
 * @returns {string} - 안전한 시트 이름
 */
function createSafeSheetName(name) {
  const sanitized = sanitizeInput(name, 'general');
  if (!sanitized) return 'Sheet_' + Date.now();
  
  // 시트 이름에 사용할 수 없는 문자 제거
  return sanitized
    .replace(/[\\/\[\]\*\?]/g, '_')
    .substring(0, 99);
}


