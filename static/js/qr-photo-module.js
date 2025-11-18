/**
 * QR 자동 스캔 및 사진 촬영 모듈
 * 기존 index.html의 기능을 재사용하여 모듈화
 */

// ========= 전역 변수 =========
let qrStream = null;
let qrScanInterval = null;
let photoStream = null;
let selectedPhotos = [];
let uploadedPhotos = [];
let currentTrackingNumber = '';
let currentReturnData = null;
let availableMonths = [];
let isUploading = false;

// ========= 초기화 =========
document.addEventListener('DOMContentLoaded', function() {
    console.log('📱 QR 자동 스캔 페이지 초기화');
    
    // 월 목록 로드
    loadAvailableMonths();
    
    // 페이지 로드 시 자동으로 QR 스캔 시작
    setTimeout(() => {
        startAutoQRScan();
    }, 500);
});

// ========= 월 목록 로드 =========
async function loadAvailableMonths() {
    try {
        const response = await fetch('/api/returns/available-months');
        const data = await response.json();
        
        if (data.success) {
            availableMonths = data.months || [];
            console.log('✅ 월 목록 로드 완료:', availableMonths.length, '개');
        } else {
            console.error('❌ 월 목록 로드 실패:', data.message);
        }
    } catch (error) {
        console.error('❌ 월 목록 로드 오류:', error);
    }
}

// ========= QR 자동 스캔 시작 =========
async function startAutoQRScan() {
    console.log('🔍 QR 자동 스캔 시작');
    
    const qrScanMode = document.querySelector('.qr-scan-mode');
    const qrStatusMessage = document.getElementById('qrStatusMessage');
    
    // HTTPS 체크
    if (location.protocol !== 'https:' && location.hostname !== 'localhost' && location.hostname !== '127.0.0.1') {
        showQRStatus('⚠️ 카메라 사용을 위해 HTTPS가 필요합니다.', 'error');
        return;
    }
    
    // 미디어 디바이스 지원 확인
    if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
        showQRStatus('⚠️ 이 브라우저는 카메라를 지원하지 않습니다.', 'error');
        showManualInputMode();
        return;
    }
    
    // jsQR 라이브러리 확인
    if (typeof jsQR === 'undefined') {
        showQRStatus('⚠️ QR 스캔 라이브러리를 로드할 수 없습니다.', 'error');
        showManualInputMode();
        return;
    }
    
    try {
        showQRStatus('카메라 권한을 요청하는 중...', '');
        
        // QR 스캔용 카메라 설정 (낮은 해상도, 빠른 스캔)
        const constraints = {
            video: {
                facingMode: 'environment',
                width: { ideal: 640, max: 1280 },
                height: { ideal: 480, max: 720 }
            }
        };
        
        qrStream = await navigator.mediaDevices.getUserMedia(constraints);
        
        const qrVideo = document.getElementById('qrVideo');
        qrVideo.srcObject = qrStream;
        qrVideo.setAttribute('playsinline', 'true');
        qrVideo.setAttribute('webkit-playsinline', 'true');
        
        await qrVideo.play();
        
        qrScanMode.classList.remove('hidden');
        showQRStatus('QR 코드를 카메라에 비춰주세요.', '');
        
        // Canvas 생성
        const canvas = document.createElement('canvas');
        const context = canvas.getContext('2d');
        
        qrVideo.addEventListener('loadedmetadata', function() {
            canvas.width = qrVideo.videoWidth;
            canvas.height = qrVideo.videoHeight;
            console.log('📹 비디오 크기:', canvas.width, 'x', canvas.height);
        }, { once: true });
        
        // QR 코드 감지 루프
        let scanAttempts = 0;
        qrScanInterval = setInterval(function() {
            if (qrVideo.readyState === qrVideo.HAVE_ENOUGH_DATA && canvas.width > 0 && canvas.height > 0) {
                try {
                    context.drawImage(qrVideo, 0, 0, canvas.width, canvas.height);
                    const imageData = context.getImageData(0, 0, canvas.width, canvas.height);
                    
                    const code = jsQR(imageData.data, imageData.width, imageData.height, {
                        inversionAttempts: 'attemptBoth',
                    });
                    
                    if (code) {
                        console.log('✅ QR 코드 감지됨:', code.data);
                        handleQRDetected(code.data);
                    }
                    
                    scanAttempts++;
                    if (scanAttempts % 100 === 0) {
                        console.log('🔍 QR 스캔 시도:', scanAttempts, '회');
                    }
                } catch (err) {
                    console.error('❌ QR 스캔 오류:', err);
                }
            }
        }, 150);
        
    } catch (error) {
        console.error('❌ 카메라 오류:', error);
        handleCameraError(error);
    }
}

// ========= QR 코드 감지 처리 =========
async function handleQRDetected(trackingNumber) {
    console.log('📦 QR 코드 인식 완료:', trackingNumber);
    
    // QR 스캔 중단
    stopQRScan();
    
    currentTrackingNumber = trackingNumber;
    showQRStatus('✅ QR 코드 인식 완료! 데이터 검색 중...', 'success');
    
    // 데이터 자동 검색
    await searchReturnData(trackingNumber);
}

// ========= 반품 데이터 검색 =========
async function searchReturnData(trackingNumber) {
    try {
        // 현재 월 자동 선택
        const today = new Date();
        const currentMonth = `${today.getFullYear()}년${today.getMonth()+1}월`;
        let selectedMonth = currentMonth;
        
        if (!availableMonths.includes(currentMonth) && availableMonths.length > 0) {
            selectedMonth = availableMonths[0];
        }
        
        if (!selectedMonth) {
            showQRStatus('⚠️ 사용 가능한 월 데이터가 없습니다.', 'error');
            showManualInputMode();
            return;
        }
        
        console.log('🔍 데이터 검색 시작:', trackingNumber, selectedMonth);
        
        const response = await fetch(
            `/api/uploads/find-by-tracking?trackingNumber=${encodeURIComponent(trackingNumber)}&month=${encodeURIComponent(selectedMonth)}`
        );
        const data = await response.json();
        
        if (data.success && data.data) {
            console.log('✅ 데이터 검색 완료:', data.data);
            
            // 반품 데이터 저장
            currentReturnData = {
                return_date: new Date().toISOString().split('T')[0],
                company_name: data.data.company || '',
                product: data.data.product || '',
                customer_name: data.data.customer || '',
                tracking_number: trackingNumber,
                return_type: '',
                stock_status: '',
                inspection: '',
                completed: '',
                memo: '',
                photo_links: '',
                other_courier: '',
                shipping_fee: '',
                client_request: '',
                client_confirmed: '',
                month: selectedMonth
            };
            
            // 사진 촬영 모드로 전환
            switchToPhotoMode();
            
        } else {
            console.warn('⚠️ 데이터를 찾을 수 없음');
            showQRStatus('⚠️ 해당 송장번호 데이터를 찾을 수 없습니다.', 'error');
            
            // 수동 입력 모드 표시
            setTimeout(() => {
                showManualInputMode();
            }, 2000);
        }
        
    } catch (error) {
        console.error('❌ 데이터 검색 오류:', error);
        showQRStatus('⚠️ 데이터 검색 중 오류가 발생했습니다.', 'error');
        showManualInputMode();
    }
}

// ========= 사진 촬영 모드로 전환 =========
async function switchToPhotoMode() {
    console.log('📷 사진 촬영 모드로 전환');
    
    // QR 스캔 모드 숨기기
    document.querySelector('.qr-scan-mode').classList.add('hidden');
    
    // 사진 촬영 모드 표시
    const photoMode = document.querySelector('.photo-mode');
    photoMode.classList.add('active');
    
    // 정보 패널 표시
    updateInfoPanel();
    
    // 사진 촬영용 카메라 시작
    await startPhotoCamera();
}

// ========= 사진 촬영용 카메라 시작 =========
async function startPhotoCamera() {
    try {
        // QR 스캔 카메라 정리
        if (qrStream) {
            qrStream.getTracks().forEach(track => track.stop());
            qrStream = null;
        }
        
        // 사진 촬영용 카메라 설정 (높은 해상도)
        const constraints = {
            video: {
                facingMode: 'environment',
                width: { ideal: 1920, max: 3840 },
                height: { ideal: 1080, max: 2160 }
            }
        };
        
        photoStream = await navigator.mediaDevices.getUserMedia(constraints);
        
        const photoVideo = document.getElementById('photoVideo');
        photoVideo.srcObject = photoStream;
        photoVideo.setAttribute('playsinline', 'true');
        photoVideo.setAttribute('webkit-playsinline', 'true');
        
        await photoVideo.play();
        console.log('✅ 사진 촬영 카메라 시작 완료');
        
    } catch (error) {
        console.error('❌ 사진 촬영 카메라 오류:', error);
        showOverlay('카메라 오류', '사진 촬영 카메라를 시작할 수 없습니다.');
        setTimeout(() => hideOverlay(), 3000);
    }
}

// ========= 사진 촬영 =========
function capturePhoto() {
    const photoVideo = document.getElementById('photoVideo');
    
    if (photoVideo.readyState !== photoVideo.HAVE_ENOUGH_DATA) {
        console.warn('⚠️ 비디오가 준비되지 않음');
        return;
    }
    
    try {
        const canvas = document.createElement('canvas');
        canvas.width = photoVideo.videoWidth;
        canvas.height = photoVideo.videoHeight;
        
        const context = canvas.getContext('2d');
        context.drawImage(photoVideo, 0, 0, canvas.width, canvas.height);
        
        // Base64로 변환
        const photoData = canvas.toDataURL('image/jpeg', 0.8);
        
        // 사진 배열에 추가
        selectedPhotos.push(photoData);
        
        // 썸네일 업데이트
        updatePhotoThumbnails();
        
        console.log('📸 사진 촬영 완료:', selectedPhotos.length, '장');
        
        // 촬영 효과 (선택사항)
        flashEffect();
        
    } catch (error) {
        console.error('❌ 사진 촬영 오류:', error);
    }
}

// ========= 썸네일 업데이트 =========
function updatePhotoThumbnails() {
    const thumbnailsContainer = document.getElementById('photoThumbnails');
    const uploadBtn = document.getElementById('uploadBtn');
    
    thumbnailsContainer.innerHTML = '';
    
    selectedPhotos.forEach((photoData, index) => {
        const thumbnail = document.createElement('div');
        thumbnail.className = 'photo-thumbnail';
        
        const img = document.createElement('img');
        img.src = photoData;
        
        const deleteBtn = document.createElement('button');
        deleteBtn.className = 'delete-btn';
        deleteBtn.innerHTML = '×';
        deleteBtn.onclick = () => removePhoto(index);
        
        thumbnail.appendChild(img);
        thumbnail.appendChild(deleteBtn);
        thumbnailsContainer.appendChild(thumbnail);
    });
    
    // 업로드 버튼 표시/숨김
    if (selectedPhotos.length > 0) {
        uploadBtn.classList.remove('hidden');
        uploadBtn.textContent = `📤 업로드 (${selectedPhotos.length}장)`;
    } else {
        uploadBtn.classList.add('hidden');
    }
}

// ========= 사진 삭제 =========
function removePhoto(index) {
    selectedPhotos.splice(index, 1);
    updatePhotoThumbnails();
    console.log('🗑️ 사진 삭제:', selectedPhotos.length, '장 남음');
}

// ========= 즉시 업로드 =========
async function uploadPhotos() {
    if (isUploading) {
        console.log('⏳ 이미 업로드 중입니다.');
        return;
    }
    
    if (selectedPhotos.length === 0) {
        console.warn('⚠️ 업로드할 사진이 없습니다.');
        return;
    }
    
    if (!currentTrackingNumber) {
        console.error('❌ 송장번호가 없습니다.');
        return;
    }
    
    isUploading = true;
    const uploadBtn = document.getElementById('uploadBtn');
    uploadBtn.disabled = true;
    uploadBtn.textContent = '📤 업로드 중...';
    
    console.log('📤 사진 업로드 시작:', selectedPhotos.length, '장');
    showOverlay('사진 업로드 중', `${selectedPhotos.length}장의 사진을 업로드하고 있습니다...`);
    
    try {
        // 이미지 업로드
        const response = await fetch('/api/uploads/upload-images', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                images: selectedPhotos,
                trackingNumber: currentTrackingNumber
            })
        });
        
        const contentType = response.headers.get('content-type');
        if (!contentType || !contentType.includes('application/json')) {
            const text = await response.text();
            throw new Error(`서버 오류 (${response.status}): ${text.substring(0, 200)}`);
        }
        
        const data = await response.json();
        
        if (!response.ok) {
            throw new Error(data.message || `서버 오류 (${response.status})`);
        }
        
        if (data.success && data.photoLinks) {
            console.log('✅ 사진 업로드 완료:', data.photoLinks);
            
            // 반품 데이터에 사진 링크 추가
            if (currentReturnData) {
                const existingLinks = currentReturnData.photo_links || '';
                const newLinks = existingLinks 
                    ? existingLinks + '\n' + data.photoLinks 
                    : data.photoLinks;
                currentReturnData.photo_links = newLinks;
            }
            
            // 업로드된 사진들을 배열에서 제거
            uploadedPhotos.push(...selectedPhotos);
            selectedPhotos = [];
            updatePhotoThumbnails();
            
            // 반품 데이터 저장
            await saveReturnData();
            
            hideOverlay();
            showOverlay('업로드 완료', `${uploadedPhotos.length}장의 사진이 업로드되었습니다.`, 2000);
            
        } else {
            throw new Error(data.message || '사진 업로드 실패');
        }
        
    } catch (error) {
        console.error('❌ 사진 업로드 오류:', error);
        hideOverlay();
        showOverlay('업로드 실패', error.message || '사진 업로드 중 오류가 발생했습니다.', 3000);
    } finally {
        isUploading = false;
        uploadBtn.disabled = false;
    }
}

// ========= 반품 데이터 저장 =========
async function saveReturnData() {
    if (!currentReturnData) {
        console.warn('⚠️ 저장할 반품 데이터가 없습니다.');
        return;
    }
    
    try {
        console.log('💾 반품 데이터 저장 시작');
        
        const response = await fetch('/api/returns/create', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(currentReturnData)
        });
        
        const contentType = response.headers.get('content-type');
        if (!contentType || !contentType.includes('application/json')) {
            const text = await response.text();
            throw new Error(`서버 오류 (${response.status}): ${text.substring(0, 200)}`);
        }
        
        const data = await response.json();
        
        if (!response.ok) {
            throw new Error(data.message || `서버 오류 (${response.status})`);
        }
        
        if (data.success) {
            console.log('✅ 반품 데이터 저장 완료:', data.id);
        } else {
            throw new Error(data.message || '반품 데이터 저장 실패');
        }
        
    } catch (error) {
        console.error('❌ 반품 데이터 저장 오류:', error);
        // 저장 실패해도 사진은 업로드되었으므로 계속 진행
    }
}

// ========= 정보 패널 업데이트 =========
function updateInfoPanel() {
    if (!currentReturnData) return;
    
    const infoPanel = document.getElementById('infoPanel');
    infoPanel.innerHTML = `
        <div class="info-panel-item">
            <span class="info-panel-label">화주명:</span>
            <span>${currentReturnData.company_name || '-'}</span>
        </div>
        <div class="info-panel-item">
            <span class="info-panel-label">제품:</span>
            <span>${currentReturnData.product || '-'}</span>
        </div>
        <div class="info-panel-item">
            <span class="info-panel-label">고객명:</span>
            <span>${currentReturnData.customer_name || '-'}</span>
        </div>
        <div class="info-panel-item">
            <span class="info-panel-label">송장번호:</span>
            <span>${currentReturnData.tracking_number || '-'}</span>
        </div>
    `;
    infoPanel.classList.add('show');
}

// ========= QR 스캔 중단 =========
function stopQRScan() {
    console.log('⏹️ QR 스캔 중단');
    
    if (qrScanInterval) {
        clearInterval(qrScanInterval);
        qrScanInterval = null;
    }
    
    if (qrStream) {
        qrStream.getTracks().forEach(track => track.stop());
        qrStream = null;
    }
    
    const qrVideo = document.getElementById('qrVideo');
    if (qrVideo) {
        qrVideo.srcObject = null;
        qrVideo.pause();
    }
}

// ========= 카메라 오류 처리 =========
function handleCameraError(error) {
    let errorMessage = '카메라를 사용할 수 없습니다.';
    
    if (error.name === 'NotAllowedError' || error.name === 'PermissionDeniedError') {
        errorMessage = '카메라 권한이 거부되었습니다. 브라우저 설정에서 카메라 권한을 허용해주세요.';
    } else if (error.name === 'NotFoundError' || error.name === 'DevicesNotFoundError') {
        errorMessage = '카메라를 찾을 수 없습니다.';
    } else if (error.name === 'NotReadableError' || error.name === 'TrackStartError') {
        errorMessage = '카메라가 다른 애플리케이션에서 사용 중입니다.';
    }
    
    showQRStatus('⚠️ ' + errorMessage, 'error');
    showManualInputMode();
}

// ========= QR 상태 메시지 표시 =========
function showQRStatus(message, type) {
    const qrStatusMessage = document.getElementById('qrStatusMessage');
    if (qrStatusMessage) {
        qrStatusMessage.textContent = message;
        qrStatusMessage.className = 'qr-status-message';
        if (type) {
            qrStatusMessage.classList.add(type);
        }
    }
}

// ========= 수동 입력 모드 표시 =========
function showManualInputMode() {
    const manualInputMode = document.querySelector('.manual-input-mode');
    if (manualInputMode) {
        manualInputMode.classList.add('active');
    }
}

// ========= 수동 입력 처리 =========
function handleManualInput() {
    const trackingInput = document.getElementById('manualTrackingInput');
    const trackingNumber = trackingInput ? trackingInput.value.trim() : '';
    
    if (!trackingNumber) {
        alert('송장번호를 입력해주세요.');
        return;
    }
    
    currentTrackingNumber = trackingNumber;
    
    // 수동 입력 모드 숨기기
    const manualInputMode = document.querySelector('.manual-input-mode');
    if (manualInputMode) {
        manualInputMode.classList.remove('active');
    }
    
    // 데이터 검색
    searchReturnData(trackingNumber);
}

// ========= 오버레이 표시 =========
function showOverlay(title, desc, autoHide = null) {
    const overlay = document.getElementById('overlay');
    const overlayTitle = document.getElementById('overlayTitle');
    const overlayDesc = document.getElementById('overlayDesc');
    
    if (overlayTitle) overlayTitle.textContent = title || '처리 중...';
    if (overlayDesc) overlayDesc.textContent = desc || '잠시만 기다려주세요.';
    if (overlay) overlay.classList.add('show');
    
    if (autoHide) {
        setTimeout(() => hideOverlay(), autoHide);
    }
}

// ========= 오버레이 숨기기 =========
function hideOverlay() {
    const overlay = document.getElementById('overlay');
    if (overlay) overlay.classList.remove('show');
}

// ========= 플래시 효과 =========
function flashEffect() {
    const flash = document.createElement('div');
    flash.style.cssText = `
        position: fixed;
        inset: 0;
        background: #fff;
        opacity: 0.8;
        z-index: 10000;
        pointer-events: none;
        animation: flash 0.2s ease-out;
    `;
    
    const style = document.createElement('style');
    style.textContent = `
        @keyframes flash {
            0% { opacity: 0.8; }
            100% { opacity: 0; }
        }
    `;
    document.head.appendChild(style);
    document.body.appendChild(flash);
    
    setTimeout(() => {
        flash.remove();
        style.remove();
    }, 200);
}

// ========= 전역 함수 (HTML에서 호출) =========
window.capturePhoto = capturePhoto;
window.uploadPhotos = uploadPhotos;
window.removePhoto = removePhoto;
window.handleManualInput = handleManualInput;
window.closeManualInput = function() {
    document.querySelector('.manual-input-mode').classList.remove('active');
};

