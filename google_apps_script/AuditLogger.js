/**
 * 🔍 보안 감사 로그 시스템
 * 
 * 주요 기능:
 * - 사용자 활동 추적
 * - 보안 이벤트 로깅
 * - 시스템 성능 모니터링
 * - 감사 보고서 생성
 */

// ========================================
// 📊 감사 로그 설정
// ========================================

const AUDIT_CONFIG = {
  // 로그 레벨
  LEVELS: {
    CRITICAL: 'CRITICAL',  // 시스템 중단, 보안 침해
    ERROR: 'ERROR',        // 오류 발생
    WARN: 'WARN',          // 경고
    INFO: 'INFO',          // 일반 정보
    DEBUG: 'DEBUG'         // 디버그 정보
  },
  
  // 이벤트 타입
  EVENT_TYPES: {
    USER_LOGIN: 'USER_LOGIN',
    USER_LOGOUT: 'USER_LOGOUT',
    DATA_ACCESS: 'DATA_ACCESS',
    DATA_MODIFY: 'DATA_MODIFY',
    CONFIG_CHANGE: 'CONFIG_CHANGE',
    SECURITY_VIOLATION: 'SECURITY_VIOLATION',
    SYSTEM_ERROR: 'SYSTEM_ERROR',
    PERFORMANCE: 'PERFORMANCE'
  },
  
  // 로그 보관 설정
  RETENTION: {
    CRITICAL: 365,  // 1년
    ERROR: 90,      // 3개월
    WARN: 30,       // 1개월
    INFO: 7,        // 1주일
    DEBUG: 1        // 1일
  }
};

// ========================================
// 🔍 감사 로그 기록
// ========================================

/**
 * 감사 로그 기록
 * @param {string} level - 로그 레벨
 * @param {string} eventType - 이벤트 타입
 * @param {string} message - 로그 메시지
 * @param {Object} details - 상세 정보
 * @param {Object} metadata - 메타데이터
 */
function logAuditEvent(level, eventType, message, details = {}, metadata = {}) {
  try {
    const timestamp = new Date().toISOString();
    const userEmail = Session.getActiveUser().getEmail();
    const scriptId = ScriptApp.getScriptId();
    
    const logEntry = {
      timestamp: timestamp,
      level: level,
      eventType: eventType,
      user: userEmail,
      scriptId: scriptId,
      message: message,
      details: details,
      metadata: {
        ...metadata,
        userAgent: 'Google Apps Script',
        version: '1.0.0'
      }
    };
    
    // 콘솔 로그
    console.log(`[AUDIT ${level}] ${eventType}: ${message}`, logEntry);
    
    // 스프레드시트에 저장
    saveAuditLogToSheet(logEntry);
    
    // 중요한 이벤트는 즉시 알림
    if (level === AUDIT_CONFIG.LEVELS.CRITICAL || level === AUDIT_CONFIG.LEVELS.ERROR) {
      sendSecurityAlert(logEntry);
    }
    
  } catch (error) {
    console.error('Failed to log audit event:', error);
  }
}

/**
 * 감사 로그를 스프레드시트에 저장
 */
function saveAuditLogToSheet(logEntry) {
  try {
    const ss = SpreadsheetApp.getActiveSpreadsheet();
    let logSheet = ss.getSheetByName('감사로그');
    
    if (!logSheet) {
      logSheet = createAuditLogSheet();
    }
    
    const row = [
      logEntry.timestamp,
      logEntry.level,
      logEntry.eventType,
      logEntry.user,
      logEntry.message,
      JSON.stringify(logEntry.details),
      JSON.stringify(logEntry.metadata)
    ];
    
    logSheet.appendRow(row);
    
    // 로그 정리 (오래된 로그 삭제)
    cleanupOldLogs(logSheet);
    
  } catch (error) {
    console.error('Failed to save audit log to sheet:', error);
  }
}

/**
 * 감사 로그 시트 생성
 */
function createAuditLogSheet() {
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  const logSheet = ss.insertSheet('감사로그');
  
  const headers = [
    '타임스탬프',
    '레벨',
    '이벤트타입',
    '사용자',
    '메시지',
    '상세정보',
    '메타데이터'
  ];
  
  logSheet.getRange(1, 1, 1, headers.length).setValues([headers]);
  logSheet.getRange(1, 1, 1, headers.length).setFontWeight('bold');
  logSheet.setFrozenRows(1);
  
  // 열 너비 설정
  logSheet.setColumnWidth(1, 150); // 타임스탬프
  logSheet.setColumnWidth(2, 80);  // 레벨
  logSheet.setColumnWidth(3, 120); // 이벤트타입
  logSheet.setColumnWidth(4, 150); // 사용자
  logSheet.setColumnWidth(5, 200); // 메시지
  logSheet.setColumnWidth(6, 300); // 상세정보
  logSheet.setColumnWidth(7, 300); // 메타데이터
  
  return logSheet;
}

/**
 * 오래된 로그 정리
 */
function cleanupOldLogs(logSheet) {
  try {
    const data = logSheet.getDataRange().getValues();
    const now = new Date();
    const rowsToDelete = [];
    
    for (let i = 1; i < data.length; i++) {
      const timestamp = new Date(data[i][0]);
      const level = data[i][1];
      
      const retentionDays = AUDIT_CONFIG.RETENTION[level] || 7;
      const cutoffDate = new Date(now.getTime() - (retentionDays * 24 * 60 * 60 * 1000));
      
      if (timestamp < cutoffDate) {
        rowsToDelete.push(i + 1); // 1-based row number
      }
    }
    
    // 뒤에서부터 삭제 (인덱스 변경 방지)
    for (let i = rowsToDelete.length - 1; i >= 0; i--) {
      logSheet.deleteRow(rowsToDelete[i]);
    }
    
    if (rowsToDelete.length > 0) {
      console.log(`Cleaned up ${rowsToDelete.length} old audit logs`);
    }
    
  } catch (error) {
    console.error('Failed to cleanup old logs:', error);
  }
}

// ========================================
// 🚨 보안 알림
// ========================================

/**
 * 보안 알림 전송
 */
function sendSecurityAlert(logEntry) {
  try {
    const adminEmails = getSecureConfig('ADMIN_EMAILS', 'jjay220304@gmail.com').split(',');
    
    const subject = `🚨 보안 알림 - ${logEntry.eventType}`;
    const body = `
보안 이벤트가 발생했습니다.

시간: ${logEntry.timestamp}
레벨: ${logEntry.level}
이벤트: ${logEntry.eventType}
사용자: ${logEntry.user}
메시지: ${logEntry.message}

상세 정보:
${JSON.stringify(logEntry.details, null, 2)}

메타데이터:
${JSON.stringify(logEntry.metadata, null, 2)}

이 이벤트를 검토해주세요.
    `;
    
    adminEmails.forEach(email => {
      if (email.trim()) {
        MailApp.sendEmail({
          to: email.trim(),
          subject: subject,
          body: body
        });
      }
    });
    
  } catch (error) {
    console.error('Failed to send security alert:', error);
  }
}

// ========================================
// 📊 감사 보고서 생성
// ========================================

/**
 * 보안 감사 보고서 생성
 * @param {Date} startDate - 시작일
 * @param {Date} endDate - 종료일
 * @returns {Object} - 감사 보고서
 */
function generateSecurityAuditReport(startDate, endDate) {
  return safeExecute(() => {
    const ss = SpreadsheetApp.getActiveSpreadsheet();
    const logSheet = ss.getSheetByName('감사로그');
    
    if (!logSheet) {
      throw new Error('감사로그 시트가 없습니다.');
    }
    
    const data = logSheet.getDataRange().getValues();
    const filteredData = data.filter((row, index) => {
      if (index === 0) return false; // 헤더 제외
      
      const timestamp = new Date(row[0]);
      return timestamp >= startDate && timestamp <= endDate;
    });
    
    const report = {
      period: {
        start: startDate.toISOString(),
        end: endDate.toISOString()
      },
      summary: {
        totalEvents: filteredData.length,
        criticalEvents: 0,
        errorEvents: 0,
        warningEvents: 0,
        infoEvents: 0
      },
      eventsByType: {},
      eventsByUser: {},
      securityViolations: [],
      performanceIssues: []
    };
    
    // 데이터 분석
    filteredData.forEach(row => {
      const level = row[1];
      const eventType = row[2];
      const user = row[3];
      const message = row[4];
      const details = JSON.parse(row[5] || '{}');
      
      // 레벨별 카운트
      if (level === AUDIT_CONFIG.LEVELS.CRITICAL) report.summary.criticalEvents++;
      else if (level === AUDIT_CONFIG.LEVELS.ERROR) report.summary.errorEvents++;
      else if (level === AUDIT_CONFIG.LEVELS.WARN) report.summary.warningEvents++;
      else if (level === AUDIT_CONFIG.LEVELS.INFO) report.summary.infoEvents++;
      
      // 이벤트 타입별 카운트
      report.eventsByType[eventType] = (report.eventsByType[eventType] || 0) + 1;
      
      // 사용자별 카운트
      report.eventsByUser[user] = (report.eventsByUser[user] || 0) + 1;
      
      // 보안 위반 이벤트
      if (eventType === AUDIT_CONFIG.EVENT_TYPES.SECURITY_VIOLATION) {
        report.securityViolations.push({
          timestamp: row[0],
          user: user,
          message: message,
          details: details
        });
      }
      
      // 성능 이슈
      if (eventType === AUDIT_CONFIG.EVENT_TYPES.PERFORMANCE) {
        report.performanceIssues.push({
          timestamp: row[0],
          user: user,
          message: message,
          details: details
        });
      }
    });
    
    // 보고서를 시트에 저장
    saveAuditReportToSheet(report);
    
    logAuditEvent(
      AUDIT_CONFIG.LEVELS.INFO,
      AUDIT_CONFIG.EVENT_TYPES.DATA_ACCESS,
      'Security audit report generated',
      { reportPeriod: `${startDate.toISOString()} to ${endDate.toISOString()}` }
    );
    
    return report;
    
  }, 'generateSecurityAuditReport', null);
}

/**
 * 감사 보고서를 시트에 저장
 */
function saveAuditReportToSheet(report) {
  try {
    const ss = SpreadsheetApp.getActiveSpreadsheet();
    let reportSheet = ss.getSheetByName('감사보고서');
    
    if (!reportSheet) {
      reportSheet = ss.insertSheet('감사보고서');
    } else {
      reportSheet.clear();
    }
    
    let row = 1;
    
    // 헤더
    reportSheet.getRange(row, 1).setValue('보안 감사 보고서');
    reportSheet.getRange(row, 1).setFontSize(16).setFontWeight('bold');
    row += 2;
    
    // 기간
    reportSheet.getRange(row, 1).setValue('보고 기간:');
    reportSheet.getRange(row, 2).setValue(`${report.period.start} ~ ${report.period.end}`);
    row += 2;
    
    // 요약
    reportSheet.getRange(row, 1).setValue('요약');
    reportSheet.getRange(row, 1).setFontWeight('bold');
    row++;
    
    reportSheet.getRange(row, 1).setValue('총 이벤트 수:');
    reportSheet.getRange(row, 2).setValue(report.summary.totalEvents);
    row++;
    
    reportSheet.getRange(row, 1).setValue('Critical 이벤트:');
    reportSheet.getRange(row, 2).setValue(report.summary.criticalEvents);
    row++;
    
    reportSheet.getRange(row, 1).setValue('Error 이벤트:');
    reportSheet.getRange(row, 2).setValue(report.summary.errorEvents);
    row++;
    
    reportSheet.getRange(row, 1).setValue('Warning 이벤트:');
    reportSheet.getRange(row, 2).setValue(report.summary.warningEvents);
    row++;
    
    reportSheet.getRange(row, 1).setValue('Info 이벤트:');
    reportSheet.getRange(row, 2).setValue(report.summary.infoEvents);
    row += 2;
    
    // 이벤트 타입별 통계
    reportSheet.getRange(row, 1).setValue('이벤트 타입별 통계');
    reportSheet.getRange(row, 1).setFontWeight('bold');
    row++;
    
    Object.entries(report.eventsByType).forEach(([type, count]) => {
      reportSheet.getRange(row, 1).setValue(type);
      reportSheet.getRange(row, 2).setValue(count);
      row++;
    });
    
    row += 2;
    
    // 사용자별 통계
    reportSheet.getRange(row, 1).setValue('사용자별 통계');
    reportSheet.getRange(row, 1).setFontWeight('bold');
    row++;
    
    Object.entries(report.eventsByUser).forEach(([user, count]) => {
      reportSheet.getRange(row, 1).setValue(user);
      reportSheet.getRange(row, 2).setValue(count);
      row++;
    });
    
    // 서식 적용
    reportSheet.autoResizeColumns(1, 2);
    
  } catch (error) {
    console.error('Failed to save audit report to sheet:', error);
  }
}

// ========================================
// 🔍 특수 감사 함수들
// ========================================

/**
 * 사용자 로그인 감사
 */
function auditUserLogin(userEmail, loginMethod = 'Google Apps Script') {
  logAuditEvent(
    AUDIT_CONFIG.LEVELS.INFO,
    AUDIT_CONFIG.EVENT_TYPES.USER_LOGIN,
    'User logged in',
    { user: userEmail, method: loginMethod }
  );
}

/**
 * 데이터 접근 감사
 */
function auditDataAccess(operation, dataType, recordCount = 0) {
  logAuditEvent(
    AUDIT_CONFIG.LEVELS.INFO,
    AUDIT_CONFIG.EVENT_TYPES.DATA_ACCESS,
    `Data accessed: ${operation}`,
    { dataType: dataType, recordCount: recordCount }
  );
}

/**
 * 데이터 수정 감사
 */
function auditDataModification(operation, dataType, recordCount = 0, changes = {}) {
  logAuditEvent(
    AUDIT_CONFIG.LEVELS.INFO,
    AUDIT_CONFIG.EVENT_TYPES.DATA_MODIFY,
    `Data modified: ${operation}`,
    { 
      dataType: dataType, 
      recordCount: recordCount,
      changes: changes
    }
  );
}

/**
 * 설정 변경 감사
 */
function auditConfigChange(configKey, oldValue, newValue) {
  logAuditEvent(
    AUDIT_CONFIG.LEVELS.WARN,
    AUDIT_CONFIG.EVENT_TYPES.CONFIG_CHANGE,
    `Configuration changed: ${configKey}`,
    { 
      key: configKey,
      oldValue: maskSensitiveInfo(oldValue, 4),
      newValue: maskSensitiveInfo(newValue, 4)
    }
  );
}

/**
 * 보안 위반 감사
 */
function auditSecurityViolation(violationType, details = {}) {
  logAuditEvent(
    AUDIT_CONFIG.LEVELS.CRITICAL,
    AUDIT_CONFIG.EVENT_TYPES.SECURITY_VIOLATION,
    `Security violation: ${violationType}`,
    details
  );
}

/**
 * 성능 이슈 감사
 */
function auditPerformanceIssue(operation, duration, details = {}) {
  logAuditEvent(
    AUDIT_CONFIG.LEVELS.WARN,
    AUDIT_CONFIG.EVENT_TYPES.PERFORMANCE,
    `Performance issue: ${operation}`,
    { 
      operation: operation,
      duration: duration,
      ...details
    }
  );
}

// ========================================
// 🔄 기존 보안 로그 함수와 통합
// ========================================

/**
 * 기존 logSecurityEvent 함수를 감사 로그와 통합
 */
function logSecurityEvent(level, message, details = {}) {
  // 기존 Security.gs의 logSecurityEvent와 호환성 유지
  logAuditEvent(level, AUDIT_CONFIG.EVENT_TYPES.SECURITY_VIOLATION, message, details);
}




