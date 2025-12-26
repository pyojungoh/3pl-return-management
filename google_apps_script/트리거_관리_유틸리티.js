/**
 * 🔄 트리거 관리 유틸리티
 * 
 * 현재 설정된 트리거를 확인하고 관리하는 함수들
 */

/**
 * 현재 설정된 모든 트리거 확인
 */
function checkAllTriggers() {
  try {
    const triggers = ScriptApp.getProjectTriggers();
    const ui = SpreadsheetApp.getUi();
    
    if (triggers.length === 0) {
      ui.alert("설정된 트리거가 없습니다.");
      return;
    }
    
    let message = `📋 설정된 트리거 목록 (총 ${triggers.length}개)\n\n`;
    
    triggers.forEach((trigger, index) => {
      const handlerFunction = trigger.getHandlerFunction();
      const eventType = trigger.getEventType();
      
      message += `${index + 1}. 함수: ${handlerFunction}\n`;
      message += `   타입: ${getEventTypeName(eventType)}\n`;
      
      if (eventType === ScriptApp.EventType.CLOCK) {
        // 시간 기반 트리거 정보
        const triggerSourceId = trigger.getTriggerSourceId();
        message += `   실행 시간: ${triggerSourceId}\n`;
      } else if (eventType === ScriptApp.EventType.ON_EDIT) {
        message += `   시트: ${trigger.getTriggerSourceId()}\n`;
      }
      
      message += `\n`;
    });
    
    ui.alert(message);
    
    // 콘솔에도 출력
    console.log("=== 설정된 트리거 목록 ===");
    triggers.forEach(trigger => {
      console.log(`함수: ${trigger.getHandlerFunction()}`);
      console.log(`타입: ${getEventTypeName(trigger.getEventType())}`);
    });
    
    return triggers;
    
  } catch (error) {
    console.error('트리거 확인 실패:', error);
    SpreadsheetApp.getUi().alert('트리거 확인 실패: ' + error.message);
    return [];
  }
}

/**
 * 이벤트 타입 이름 변환
 */
function getEventTypeName(eventType) {
  const typeMap = {
    [ScriptApp.EventType.CLOCK]: '시간 기반',
    [ScriptApp.EventType.ON_EDIT]: '편집 이벤트',
    [ScriptApp.EventType.ON_FORM_SUBMIT]: '폼 제출',
    [ScriptApp.EventType.ON_OPEN]: '열기 이벤트',
    [ScriptApp.EventType.ON_CHANGE]: '변경 이벤트'
  };
  
  return typeMap[eventType] || '알 수 없음';
}

/**
 * 특정 함수의 트리거 확인
 */
function checkTriggerForFunction(functionName) {
  try {
    const triggers = ScriptApp.getProjectTriggers();
    const matchingTriggers = triggers.filter(
      trigger => trigger.getHandlerFunction() === functionName
    );
    
    if (matchingTriggers.length === 0) {
      console.log(`${functionName} 함수에 대한 트리거가 없습니다.`);
      return [];
    }
    
    console.log(`${functionName} 함수에 대한 트리거 ${matchingTriggers.length}개 발견:`);
    matchingTriggers.forEach(trigger => {
      console.log(`- 타입: ${getEventTypeName(trigger.getEventType())}`);
    });
    
    return matchingTriggers;
    
  } catch (error) {
    console.error('트리거 확인 실패:', error);
    return [];
  }
}

/**
 * 자동화 관련 트리거 확인
 */
function checkAutoSyncTriggers() {
  try {
    const triggers = ScriptApp.getProjectTriggers();
    const autoSyncTriggers = [];
    
    // 자동화 관련 함수들
    const autoSyncFunctions = [
      'disableAutoSync',
      'disableAutoSyncSecure',
      'exportVendorSheetsSeparately',
      'summarizePalletData_FormControlled'
    ];
    
    triggers.forEach(trigger => {
      const handlerFunction = trigger.getHandlerFunction();
      if (autoSyncFunctions.includes(handlerFunction)) {
        autoSyncTriggers.push({
          function: handlerFunction,
          type: getEventTypeName(trigger.getEventType()),
          trigger: trigger
        });
      }
    });
    
    if (autoSyncTriggers.length === 0) {
      SpreadsheetApp.getUi().alert("자동화 관련 트리거가 설정되어 있지 않습니다.");
      return [];
    }
    
    let message = `🔄 자동화 관련 트리거 (${autoSyncTriggers.length}개)\n\n`;
    
    autoSyncTriggers.forEach((item, index) => {
      message += `${index + 1}. ${item.function}\n`;
      message += `   타입: ${item.type}\n\n`;
    });
    
    SpreadsheetApp.getUi().alert(message);
    
    return autoSyncTriggers;
    
  } catch (error) {
    console.error('자동화 트리거 확인 실패:', error);
    SpreadsheetApp.getUi().alert('트리거 확인 실패: ' + error.message);
    return [];
  }
}

/**
 * 모든 트리거 삭제 (주의: 신중하게 사용)
 */
function deleteAllTriggers() {
  try {
    const ui = SpreadsheetApp.getUi();
    const response = ui.alert(
      '⚠️ 경고',
      '모든 트리거를 삭제하시겠습니까?\n\n이 작업은 되돌릴 수 없습니다.',
      ui.ButtonSet.YES_NO
    );
    
    if (response !== ui.Button.YES) {
      ui.alert('트리거 삭제가 취소되었습니다.');
      return;
    }
    
    const triggers = ScriptApp.getProjectTriggers();
    let deletedCount = 0;
    
    triggers.forEach(trigger => {
      ScriptApp.deleteTrigger(trigger);
      deletedCount++;
    });
    
    ui.alert(`✅ ${deletedCount}개의 트리거가 삭제되었습니다.`);
    console.log(`${deletedCount}개의 트리거가 삭제되었습니다.`);
    
    return deletedCount;
    
  } catch (error) {
    console.error('트리거 삭제 실패:', error);
    SpreadsheetApp.getUi().alert('트리거 삭제 실패: ' + error.message);
    return 0;
  }
}

/**
 * 특정 함수의 트리거 삭제
 */
function deleteTriggerForFunction(functionName) {
  try {
    const triggers = ScriptApp.getProjectTriggers();
    let deletedCount = 0;
    
    triggers.forEach(trigger => {
      if (trigger.getHandlerFunction() === functionName) {
        ScriptApp.deleteTrigger(trigger);
        deletedCount++;
        console.log(`${functionName} 트리거가 삭제되었습니다.`);
      }
    });
    
    if (deletedCount === 0) {
      console.log(`${functionName} 함수에 대한 트리거가 없습니다.`);
    } else {
      SpreadsheetApp.getUi().alert(`✅ ${functionName} 함수의 트리거 ${deletedCount}개가 삭제되었습니다.`);
    }
    
    return deletedCount;
    
  } catch (error) {
    console.error('트리거 삭제 실패:', error);
    SpreadsheetApp.getUi().alert('트리거 삭제 실패: ' + error.message);
    return 0;
  }
}

/**
 * 자동화 중단 트리거 재설정 (중복 방지 포함)
 * 
 * 주의: runPreviousMonthAutomation() 함수 내부에서 자동으로 disableAutoSync()를 호출하므로
 * 별도 트리거가 필요하지 않을 수 있습니다.
 */
function resetAutoDisableTrigger() {
  try {
    // 기존 트리거 삭제
    deleteTriggerForFunction('disableAutoSync');
    deleteTriggerForFunction('disableAutoSyncSecure');
    
    // 새 트리거 생성
    ScriptApp.newTrigger('disableAutoSync')
      .timeBased()
      .onMonthDay(1)
      .atHour(0)
      .create();
    
    SpreadsheetApp.getUi().alert('✅ 자동화 중단 트리거가 재설정되었습니다.\n\n매월 1일 0시에 실행됩니다.\n\n' +
      '참고: runPreviousMonthAutomation() 함수 내부에서도 자동화 중단이 실행됩니다.');
    console.log('자동화 중단 트리거 재설정 완료');
    
  } catch (error) {
    console.error('트리거 재설정 실패:', error);
    SpreadsheetApp.getUi().alert('트리거 재설정 실패: ' + error.message);
  }
}

/**
 * 자동 백업 트리거 재설정 (중복 방지 포함)
 * 
 * 주의: runPreviousMonthAutomation() 함수 내부에서 전달 데이터 백업이 실행되므로
 * 별도 트리거가 필요하지 않을 수 있습니다.
 */
function resetBackupTrigger() {
  try {
    // 기존 트리거 삭제
    deleteTriggerForFunction('exportVendorSheetsSeparately');
    deleteTriggerForFunction('exportPreviousMonthBackup');
    
    // 새 트리거 생성 (기존 함수 유지)
    ScriptApp.newTrigger('exportVendorSheetsSeparately')
      .timeBased()
      .onMonthDay(1)
      .atHour(1)
      .create();
    
    SpreadsheetApp.getUi().alert('✅ 자동 백업 트리거가 재설정되었습니다.\n\n매월 1일 오전 1시에 실행됩니다.\n\n' +
      '참고: runPreviousMonthAutomation() 함수 내부에서도 전달 데이터 백업이 실행됩니다.');
    console.log('자동 백업 트리거 재설정 완료');
    
  } catch (error) {
    console.error('트리거 재설정 실패:', error);
    SpreadsheetApp.getUi().alert('트리거 재설정 실패: ' + error.message);
  }
}

/**
 * 모든 자동화 트리거 재설정
 */
function resetAllAutoSyncTriggers() {
  try {
    const ui = SpreadsheetApp.getUi();
    const response = ui.alert(
      '트리거 재설정',
      '모든 자동화 트리거를 재설정하시겠습니까?',
      ui.ButtonSet.YES_NO
    );
    
    if (response !== ui.Button.YES) {
      return;
    }
    
    // 전달 자동화 트리거 재설정 (권장)
    if (typeof setPreviousMonthAutomationTrigger === 'function') {
      setPreviousMonthAutomationTrigger();
    }
    
    // 자동화 중단 트리거 재설정
    resetAutoDisableTrigger();
    
    // 자동 백업 트리거 재설정
    resetBackupTrigger();
    
    ui.alert('✅ 모든 자동화 트리거가 재설정되었습니다.\n\n' +
      '주요 트리거:\n' +
      '- runPreviousMonthAutomation: 매월 1일 0시 (전달 데이터 정산+백업)\n' +
      '- disableAutoSync: 매월 1일 0시 (자동화 중단)');
    
  } catch (error) {
    console.error('트리거 재설정 실패:', error);
    SpreadsheetApp.getUi().alert('트리거 재설정 실패: ' + error.message);
  }
}

