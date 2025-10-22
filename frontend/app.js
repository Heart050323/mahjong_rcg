// グローバル変数
let handTilesImages = [];
let doraTilesImages = [];
let cameraStream = null;
let unifiedImage = null;

// DOM要素の取得
const form = document.getElementById('mahjongForm');
const calculateBtn = document.getElementById('calculateBtn');
const loading = document.getElementById('loading');
const resultSection = document.getElementById('resultSection');
const imageModal = document.getElementById('imageModal');
const imageModalImage = document.getElementById('imageModalImage');
const imageModalHeader = document.getElementById('imageModalHeader');
const imageModalClose = document.getElementById('imageModalClose');

// イベントリスナーの設定
document.addEventListener('DOMContentLoaded', function() {
    // フォーム送信イベント
    form.addEventListener('submit', handleFormSubmit);
    
    // ドラッグ&ドロップイベント
    setupDragAndDrop('unifiedPhotoArea', 'unified');
    
    // ファイル選択イベント
    document.getElementById('unifiedPhotoFile').addEventListener('change', function(e) {
        handleUnifiedFileSelect(e);
    });
    
    // モーダル関連のイベントリスナー
    setupImageModal();
});

// 統合カメラを開く
function openUnifiedCamera() {
    if (navigator.mediaDevices && navigator.mediaDevices.getUserMedia) {
        navigator.mediaDevices.getUserMedia({ 
            video: { 
                width: { ideal: 1280 },
                height: { ideal: 720 },
                facingMode: 'environment' // 背面カメラを優先
            } 
        })
        .then(function(stream) {
            cameraStream = stream;
            showUnifiedCameraModal();
        })
        .catch(function(error) {
            alert('カメラへのアクセスが拒否されました: ' + error.message);
        });
    } else {
        alert('このブラウザではカメラ機能がサポートされていません');
    }
}

// 統合カメラモーダルを表示
function showUnifiedCameraModal() {
    const modal = document.createElement('div');
    modal.style.cssText = `
        position: fixed;
        top: 0;
        left: 0;
        width: 100%;
        height: 100%;
        background: rgba(0,0,0,0.8);
        z-index: 1000;
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        padding: 16px 12px calc(env(safe-area-inset-bottom) + 80px) 12px;
        overflow: hidden;
    `;
    
    // Video + overlay container
    const frame = document.createElement('div');
    frame.style.cssText = `
        position: relative;
        width: 100%;
        max-width: 800px;
        max-height: 70vh;
        margin: 0 auto;
        border-radius: 10px;
        overflow: hidden;
        background: #000;
        display: flex;
        align-items: center;
        justify-content: center;
    `;
    
    const video = document.createElement('video');
    video.srcObject = cameraStream;
    video.autoplay = true;
    video.setAttribute('playsinline', 'true');
    video.style.cssText = `
        width: 100%;
        height: auto;
        max-height: 70vh;
        display: block;
        border-radius: 10px;
        background: #000;
        object-fit: cover;
    `;
    
    // AR風の枠を追加 - ビデオが読み込まれた後に位置を調整
    const overlay = document.createElement('div');
    overlay.style.cssText = `
        position: absolute;
        top: 0;
        left: 0;
        width: 100%;
        height: 100%;
        pointer-events: none;
        display: none;
    `;
    
    // ドラ表示牌エリアの枠（上側）
    const doraFrame = document.createElement('div');
    doraFrame.className = 'dora-frame';
    doraFrame.style.cssText = `
        position: absolute;
        border: 3px solid #4ecdc4;
        border-radius: 10px;
        background: rgba(78, 205, 196, 0.1);
    `;
    
    const doraLabel = document.createElement('div');
    doraLabel.textContent = '🀅 ドラ表示牌エリア';
    doraLabel.style.cssText = `
        position: absolute;
        top: -25px;
        left: 0;
        color: #4ecdc4;
        font-weight: bold;
        background: rgba(0,0,0,0.7);
        padding: 5px 10px;
        border-radius: 5px;
        font-size: 12px;
        white-space: nowrap;
    `;
    
    // 手牌エリアの枠（下側）
    const handFrame = document.createElement('div');
    handFrame.className = 'hand-frame';
    handFrame.style.cssText = `
        position: absolute;
        border: 3px solid #ff6b6b;
        border-radius: 10px;
        background: rgba(255, 107, 107, 0.1);
    `;
    
    const handLabel = document.createElement('div');
    handLabel.textContent = '🀄 手牌エリア';
    handLabel.style.cssText = `
        position: absolute;
        top: -25px;
        left: 0;
        color: #ff6b6b;
        font-weight: bold;
        background: rgba(0,0,0,0.7);
        padding: 5px 10px;
        border-radius: 5px;
        font-size: 12px;
        white-space: nowrap;
    `;
    
    doraFrame.appendChild(doraLabel);
    handFrame.appendChild(handLabel);
    overlay.appendChild(doraFrame);
    overlay.appendChild(handFrame);
    
    // ビデオが読み込まれた後にオーバーレイを調整
    video.addEventListener('loadedmetadata', function() {
        adjustOverlayPosition(video, overlay, doraFrame, handFrame);
        overlay.style.display = 'block';
    });
    
    // 画面回転やリサイズ時にも調整
    window.addEventListener('resize', function() {
        setTimeout(() => {
            adjustOverlayPosition(video, overlay, doraFrame, handFrame);
        }, 100);
    });
    
    const controls = document.createElement('div');
    controls.style.cssText = `
        position: fixed;
        left: 50%;
        bottom: calc(env(safe-area-inset-bottom) + 16px);
        transform: translateX(-50%);
        width: min(92%, 800px);
        display: flex;
        gap: 12px;
        justify-content: center;
        background: rgba(0,0,0,0.4);
        backdrop-filter: blur(6px);
        padding: 10px 12px;
        border-radius: 14px;
    `;
    
    const captureBtn = document.createElement('button');
    captureBtn.textContent = '📷 撮影';
    captureBtn.style.cssText = `
        background: #ff6b6b;
        color: white;
        border: none;
        padding: 15px 30px;
        border-radius: 25px;
        font-size: 16px;
        cursor: pointer;
    `;
    captureBtn.onclick = () => captureUnifiedPhoto(video, modal);
    
    const cancelBtn = document.createElement('button');
    cancelBtn.textContent = '❌ キャンセル';
    cancelBtn.style.cssText = `
        background: #666;
        color: white;
        border: none;
        padding: 15px 30px;
        border-radius: 25px;
        font-size: 16px;
        cursor: pointer;
    `;
    cancelBtn.onclick = () => closeCamera(modal);
    
    controls.appendChild(captureBtn);
    controls.appendChild(cancelBtn);
    
    frame.appendChild(video);
    frame.appendChild(overlay);
    modal.appendChild(frame);
    modal.appendChild(controls);
    document.body.appendChild(modal);
}

// オーバーレイの位置を調整する関数
function adjustOverlayPosition(video, overlay, doraFrame, handFrame) {
    const videoRect = video.getBoundingClientRect();
    const overlayRect = overlay.getBoundingClientRect();
    
    // ビデオの実際の表示領域を計算
    const videoAspectRatio = video.videoWidth / video.videoHeight;
    const containerAspectRatio = videoRect.width / videoRect.height;
    
    let actualVideoWidth, actualVideoHeight, offsetX, offsetY;
    
    if (videoAspectRatio > containerAspectRatio) {
        // ビデオが横長の場合（横向きスマホなど）
        actualVideoWidth = videoRect.width;
        actualVideoHeight = videoRect.width / videoAspectRatio;
        offsetX = 0;
        offsetY = (videoRect.height - actualVideoHeight) / 2;
    } else {
        // ビデオが縦長の場合
        actualVideoWidth = videoRect.height * videoAspectRatio;
        actualVideoHeight = videoRect.height;
        offsetX = (videoRect.width - actualVideoWidth) / 2;
        offsetY = 0;
    }
    
    // ドラ表示牌エリア（上側20%）
    const doraTop = offsetY + actualVideoHeight * 0.2;
    const doraLeft = offsetX + actualVideoWidth * 0.1;
    const doraWidth = actualVideoWidth * 0.8;
    const doraHeight = actualVideoHeight * 0.2;
    
    doraFrame.style.top = doraTop + 'px';
    doraFrame.style.left = doraLeft + 'px';
    doraFrame.style.width = doraWidth + 'px';
    doraFrame.style.height = doraHeight + 'px';
    
    // 手牌エリア（中央から下側30%）
    const handTop = offsetY + actualVideoHeight * 0.5;
    const handLeft = offsetX + actualVideoWidth * 0.1;
    const handWidth = actualVideoWidth * 0.8;
    const handHeight = actualVideoHeight * 0.3;
    
    handFrame.style.top = handTop + 'px';
    handFrame.style.left = handLeft + 'px';
    handFrame.style.width = handWidth + 'px';
    handFrame.style.height = handHeight + 'px';
}

// 統合写真を撮影
function captureUnifiedPhoto(video, modal) {
    // 既存の画像をクリア
    clearExistingImages();
    
    const canvas = document.createElement('canvas');
    const context = canvas.getContext('2d');
    
    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;
    context.drawImage(video, 0, 0);
    
    const imageData = canvas.toDataURL('image/jpeg', 0.8);
    unifiedImage = imageData;
    
    // カメラ撮影でも画像エディターを表示
    showImageEditor(imageData);
    
    closeCamera(modal);
}

// カメラを閉じる
function closeCamera(modal) {
    if (cameraStream) {
        cameraStream.getTracks().forEach(track => track.stop());
        cameraStream = null;
    }
    document.body.removeChild(modal);
}

// 統合ファイル選択
function selectUnifiedFile() {
    const fileInput = document.getElementById('unifiedPhotoFile');
    fileInput.click();
}

// 統合ファイル選択処理
function handleUnifiedFileSelect(event) {
    const file = event.target.files[0];
    if (file && file.type.startsWith('image/')) {
        // 既存の画像をクリア
        clearExistingImages();
        
        const reader = new FileReader();
        reader.onload = function(e) {
            const imageData = e.target.result;
            unifiedImage = imageData;
            showImageEditor(imageData);
        };
        reader.readAsDataURL(file);
    }
    
    // ファイル入力をリセットして同じファイルも選択できるようにする
    event.target.value = '';
}

// ドラッグ&ドロップの設定
function setupDragAndDrop(areaId, type) {
    const area = document.getElementById(areaId);
    
    area.addEventListener('dragover', function(e) {
        e.preventDefault();
        area.classList.add('dragover');
    });
    
    area.addEventListener('dragleave', function(e) {
        e.preventDefault();
        area.classList.remove('dragover');
    });
    
    area.addEventListener('drop', function(e) {
        e.preventDefault();
        area.classList.remove('dragover');
        
        const file = e.dataTransfer.files[0];
        if (file && file.type.startsWith('image/')) {
            // 既存の画像をクリア
            clearExistingImages();
            
            const reader = new FileReader();
            reader.onload = function(e) {
                const imageData = e.target.result;
                unifiedImage = imageData;
                showImageEditor(imageData);
            };
            reader.readAsDataURL(file);
        }
    });
}

// 画像編集エディターを表示
function showImageEditor(imageData) {
    const editor = document.getElementById('imageEditor');
    const editorImage = document.getElementById('editorImage');
    
    editorImage.src = imageData;
    editor.style.display = 'block';
    
    // 画像の読み込み完了後にクロップボックスの位置を調整
    editorImage.onload = function() {
        initializeCropBoxes();
    };
}

// クロップボックスの初期化
function initializeCropBoxes() {
    const handBox = document.getElementById('handCropBox');
    const doraBox = document.getElementById('doraCropBox');
    const editorImage = document.getElementById('editorImage');
    
    // デフォルト位置を設定（上:ドラ表示牌、下:手牌）
    doraBox.style.top = '20%';
    doraBox.style.left = '10%';
    doraBox.style.width = '80%';
    doraBox.style.height = '20%';
    
    handBox.style.top = '50%';
    handBox.style.left = '10%';
    handBox.style.width = '80%';
    handBox.style.height = '30%';
    
    // ドラッグ&リサイズ機能を追加
    setupCropBoxInteraction(handBox);
    setupCropBoxInteraction(doraBox);
}

// クロップボックスの操作機能を設定
function setupCropBoxInteraction(cropBox) {
    let isDragging = false;
    let isResizing = false;
    let startMouseX, startMouseY, startWidth, startHeight, startLeft, startTop;
    let currentHandle = null;
    
    // ドラッグ開始
    cropBox.addEventListener('mousedown', function(e) {
        if (e.target.classList.contains('handle')) {
            isResizing = true;
            currentHandle = e.target;
            const rect = cropBox.getBoundingClientRect();
            const parentRect = cropBox.parentElement.getBoundingClientRect();
            
            startMouseX = e.clientX;
            startMouseY = e.clientY;
            startWidth = rect.width;
            startHeight = rect.height;
            startLeft = rect.left - parentRect.left;
            startTop = rect.top - parentRect.top;
            
            document.addEventListener('mousemove', resize);
            document.addEventListener('mouseup', stopResize);
        } else {
            isDragging = true;
            const rect = cropBox.getBoundingClientRect();
            const parentRect = cropBox.parentElement.getBoundingClientRect();
            
            // マウスの相対位置を記録（ボックス内での位置）
            startMouseX = e.clientX;
            startMouseY = e.clientY;
            startLeft = rect.left - parentRect.left;
            startTop = rect.top - parentRect.top;
            
            document.addEventListener('mousemove', drag);
            document.addEventListener('mouseup', stopDrag);
        }
        e.preventDefault();
    });
    
    function drag(e) {
        if (!isDragging) return;
        
        const parentRect = cropBox.parentElement.getBoundingClientRect();
        
        // マウスの移動量を計算
        const deltaX = e.clientX - startMouseX;
        const deltaY = e.clientY - startMouseY;
        
        // 新しい位置を計算
        const newLeft = startLeft + deltaX;
        const newTop = startTop + deltaY;
        
        // 境界チェック
        const maxLeft = parentRect.width - cropBox.offsetWidth;
        const maxTop = parentRect.height - cropBox.offsetHeight;
        
        const constrainedLeft = Math.max(0, Math.min(newLeft, maxLeft));
        const constrainedTop = Math.max(0, Math.min(newTop, maxTop));
        
        cropBox.style.left = constrainedLeft + 'px';
        cropBox.style.top = constrainedTop + 'px';
    }
    
    function resize(e) {
        if (!isResizing || !currentHandle) return;
        
        const parentRect = cropBox.parentElement.getBoundingClientRect();
        const deltaX = e.clientX - startMouseX;
        const deltaY = e.clientY - startMouseY;
        
        // 角のハンドル
        const isNW = currentHandle.classList.contains('nw');
        const isNE = currentHandle.classList.contains('ne');
        const isSW = currentHandle.classList.contains('sw');
        const isSE = currentHandle.classList.contains('se');
        
        // 辺のハンドル
        const isN = currentHandle.classList.contains('n');
        const isS = currentHandle.classList.contains('s');
        const isW = currentHandle.classList.contains('w');
        const isE = currentHandle.classList.contains('e');
        
        let newWidth = startWidth;
        let newHeight = startHeight;
        let newLeft = startLeft;
        let newTop = startTop;
        
        // 各ハンドルに応じた正しいリサイズ計算
        if (isNW) {
            // 左上: 左と上の境界を移動、右下は固定
            newWidth = Math.max(50, startWidth - deltaX);
            newHeight = Math.max(40, startHeight - deltaY);
            newLeft = startLeft + (startWidth - newWidth);
            newTop = startTop + (startHeight - newHeight);
        } else if (isNE) {
            // 右上: 右と上の境界を移動、左下は固定
            newWidth = Math.max(50, startWidth + deltaX);
            newHeight = Math.max(40, startHeight - deltaY);
            newLeft = startLeft; // 左側は固定
            newTop = startTop + (startHeight - newHeight);
        } else if (isSW) {
            // 左下: 左と下の境界を移動、右上は固定
            newWidth = Math.max(50, startWidth - deltaX);
            newHeight = Math.max(40, startHeight + deltaY);
            newLeft = startLeft + (startWidth - newWidth);
            newTop = startTop; // 上側は固定
        } else if (isSE) {
            // 右下: 右と下の境界を移動、左上は固定
            newWidth = Math.max(50, startWidth + deltaX);
            newHeight = Math.max(40, startHeight + deltaY);
            newLeft = startLeft; // 左側は固定
            newTop = startTop; // 上側は固定
        } else if (isN) {
            // 上辺: 上の境界のみ移動、左右下は固定
            newHeight = Math.max(40, startHeight - deltaY);
            newTop = startTop + (startHeight - newHeight);
            newWidth = startWidth; // 幅は固定
            newLeft = startLeft; // 左側は固定
        } else if (isS) {
            // 下辺: 下の境界のみ移動、左右上は固定
            newHeight = Math.max(40, startHeight + deltaY);
            newTop = startTop; // 上側は固定
            newWidth = startWidth; // 幅は固定
            newLeft = startLeft; // 左側は固定
        } else if (isW) {
            // 左辺: 左の境界のみ移動、上下右は固定
            newWidth = Math.max(50, startWidth - deltaX);
            newLeft = startLeft + (startWidth - newWidth);
            newHeight = startHeight; // 高さは固定
            newTop = startTop; // 上側は固定
        } else if (isE) {
            // 右辺: 右の境界のみ移動、上下左は固定
            newWidth = Math.max(50, startWidth + deltaX);
            newLeft = startLeft; // 左側は固定
            newHeight = startHeight; // 高さは固定
            newTop = startTop; // 上側は固定
        }
        
        // 境界チェック
        const parentWidth = parentRect.width;
        const parentHeight = parentRect.height;
        
        // 左境界チェック
        if (newLeft < 0) {
            newWidth += newLeft;
            newLeft = 0;
        }
        // 右境界チェック
        if (newLeft + newWidth > parentWidth) {
            newWidth = parentWidth - newLeft;
        }
        // 上境界チェック
        if (newTop < 0) {
            newHeight += newTop;
            newTop = 0;
        }
        // 下境界チェック
        if (newTop + newHeight > parentHeight) {
            newHeight = parentHeight - newTop;
        }
        
        // 最小サイズを保証
        newWidth = Math.max(50, newWidth);
        newHeight = Math.max(40, newHeight);
        
        cropBox.style.width = newWidth + 'px';
        cropBox.style.height = newHeight + 'px';
        cropBox.style.left = newLeft + 'px';
        cropBox.style.top = newTop + 'px';
    }
    
    function stopDrag() {
        isDragging = false;
        document.removeEventListener('mousemove', drag);
        document.removeEventListener('mouseup', stopDrag);
    }
    
    function stopResize() {
        isResizing = false;
        currentHandle = null;
        document.removeEventListener('mousemove', resize);
        document.removeEventListener('mouseup', stopResize);
    }
}

// 画像を切り出し
function cropImages() {
    const editorImage = document.getElementById('editorImage');
    const handBox = document.getElementById('handCropBox');
    const doraBox = document.getElementById('doraCropBox');
    
    const img = new Image();
    img.onload = function() {
        const canvas = document.createElement('canvas');
        const context = canvas.getContext('2d');
        
        // 手牌エリアを切り出し
        const handRect = handBox.getBoundingClientRect();
        const parentRect = handBox.parentElement.getBoundingClientRect();
        const handCanvas = document.createElement('canvas');
        const handContext = handCanvas.getContext('2d');
        
        const handX = (handRect.left - parentRect.left) / parentRect.width * img.width;
        const handY = (handRect.top - parentRect.top) / parentRect.height * img.height;
        const handW = handRect.width / parentRect.width * img.width;
        const handH = handRect.height / parentRect.height * img.height;
        
        handCanvas.width = handW;
        handCanvas.height = handH;
        handContext.drawImage(img, handX, handY, handW, handH, 0, 0, handW, handH);
        const handImageData = handCanvas.toDataURL('image/jpeg', 0.8);
        
        // ドラ表示牌エリアを切り出し
        const doraRect = doraBox.getBoundingClientRect();
        const doraCanvas = document.createElement('canvas');
        const doraContext = doraCanvas.getContext('2d');
        
        const doraX = (doraRect.left - parentRect.left) / parentRect.width * img.width;
        const doraY = (doraRect.top - parentRect.top) / parentRect.height * img.height;
        const doraW = doraRect.width / parentRect.width * img.width;
        const doraH = doraRect.height / parentRect.height * img.height;
        
        doraCanvas.width = doraW;
        doraCanvas.height = doraH;
        doraContext.drawImage(img, doraX, doraY, doraW, doraH, 0, 0, doraW, doraH);
        const doraImageData = doraCanvas.toDataURL('image/jpeg', 0.8);
        
        // 配列をクリアして新しい画像を追加
        handTilesImages = [handImageData];
        doraTilesImages = [doraImageData];
        
        // プレビューを更新
        updatePreview('handTilesPreview', handTilesImages);
        updatePreview('doraTilesPreview', doraTilesImages);
        
        // エディターを非表示
        document.getElementById('imageEditor').style.display = 'none';
    };
    img.src = editorImage.src;
}

// 切り出しをキャンセル
function cancelCrop() {
    document.getElementById('imageEditor').style.display = 'none';
    unifiedImage = null;
}



// プレビューの更新
function updatePreview(containerId, images) {
    const container = document.getElementById(containerId);
    container.innerHTML = '';
    
    images.forEach((imageData, index) => {
        const previewItem = document.createElement('div');
        previewItem.className = 'preview-item';
        
        const img = document.createElement('img');
        img.src = imageData;
        img.alt = `Preview ${index + 1}`;
        
        // 画像クリックでモーダル表示
        img.onclick = () => showImageModal(imageData, containerId, index);
        
        const removeBtn = document.createElement('button');
        removeBtn.className = 'remove-btn';
        removeBtn.textContent = '×';
        removeBtn.onclick = (e) => {
            e.stopPropagation(); // 画像クリックイベントを防ぐ
            removeImage(containerId, index);
        };
        
        previewItem.appendChild(img);
        previewItem.appendChild(removeBtn);
        container.appendChild(previewItem);
    });
    
    // 上書き通知の表示/非表示を制御
    updateOverwriteNotice();
}

// 上書き通知の表示/非表示を制御
function updateOverwriteNotice() {
    const overwriteNotice = document.getElementById('overwriteNotice');
    const hasImages = handTilesImages.length > 0 || doraTilesImages.length > 0;
    
    if (hasImages) {
        overwriteNotice.style.display = 'block';
    } else {
        overwriteNotice.style.display = 'none';
    }
}

// 既存の画像をクリア
function clearExistingImages() {
    // 画像配列をクリア
    handTilesImages = [];
    doraTilesImages = [];
    unifiedImage = null;
    
    // プレビューをクリア
    updatePreview('handTilesPreview', handTilesImages);
    updatePreview('doraTilesPreview', doraTilesImages);
    
    // 画像エディターを非表示
    const editor = document.getElementById('imageEditor');
    if (editor) {
        editor.style.display = 'none';
    }
    
    // 結果セクションを非表示
    resultSection.classList.remove('show');
}

// 画像を削除
function removeImage(containerId, index) {
    if (containerId === 'handTilesPreview') {
        handTilesImages.splice(index, 1);
        updatePreview('handTilesPreview', handTilesImages);
    } else {
        doraTilesImages.splice(index, 1);
        updatePreview('doraTilesPreview', doraTilesImages);
    }
    
    // 両方の画像が削除された場合は統合画像もクリア
    if (handTilesImages.length === 0 && doraTilesImages.length === 0) {
        unifiedImage = null;
    }
}

// フォーム送信処理
async function handleFormSubmit(event) {
    event.preventDefault();
    
    // バリデーション
    if (handTilesImages.length === 0) {
        alert('手牌の写真を撮影または選択してください');
        return;
    }
    
    // ローディング表示
    showLoading(true);
    calculateBtn.disabled = true;
    
    try {
        // フォームデータの取得
        const formData = {
            handTiles: handTilesImages,
            doraTiles: doraTilesImages,
            riichi: document.getElementById('riichi').checked,
            winType: document.getElementById('winType').value,
            roundWind: document.getElementById('roundWind').value,
            playerWind: document.getElementById('playerWind').value
        };
        
        // API呼び出し
        const response = await fetch('https://mahjong-rcg-client.onrender.com/api/calculate', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(formData)
        });
        
        const result = await response.json();
        
        if (response.ok) {
            console.log('API応答を受信:', result);
            console.log('result.cost:', result.cost);
            console.log('result.cost type:', typeof result.cost);
            if (result.cost) {
                console.log('result.cost.main:', result.cost.main);
                console.log('result.cost.additional:', result.cost.additional);
            }
            displayResult(result);
        } else {
            showError(result.error || '計算中にエラーが発生しました');
        }
        
    } catch (error) {
        console.error('Error:', error);
        showError('サーバーとの通信中にエラーが発生しました');
    } finally {
        showLoading(false);
        calculateBtn.disabled = false;
    }
}

// 結果の表示
function displayResult(result) {
    document.getElementById('hanValue').textContent = result.han;
    document.getElementById('fuValue').textContent = result.fu;
    
    // デバッグ用: 受け取った結果を表示
    console.log('displayResult - 受け取った結果:', result);
    console.log('displayResult - cost:', result.cost);
    console.log('displayResult - main:', result.cost?.main);
    console.log('displayResult - additional:', result.cost?.additional);
    console.log('displayResult - cost type:', typeof result.cost);
    console.log('displayResult - main type:', typeof result.cost?.main);
    console.log('displayResult - additional type:', typeof result.cost?.additional);
    
    // 点数の表示
    let costText = '';
    if (result.cost && typeof result.cost === 'object' && result.cost.main !== undefined) {
        const main = parseInt(result.cost.main);
        const additional = parseInt(result.cost.additional);
        
        // フロントエンドのフォームからwinTypeを取得
        const winType = document.getElementById('winType').value;
        console.log('displayResult - winType:', winType);
        console.log('displayResult - main (parsed):', main);
        console.log('displayResult - additional (parsed):', additional);
        
        if (winType === 'tsumo') {
            // ツモの場合
            console.log('ツモ判定 - main:', main, 'additional:', additional);
            if (additional === 0) {
                // additionalが0の場合は親のみ（ロンと同じ）
                costText = `${main}点`;
                console.log('ツモ（親のみ）:', costText);
            } else if (main === additional) {
                // 親子同じ点数（オール）の場合
                costText = `${main}点オール`;
                console.log('ツモ（オール）:', costText);
            } else {
                // 親子異なる点数の場合
                costText = `親: ${main}点, 子: ${additional}点`;
                console.log('ツモ（親子異なる）:', costText);
            }
        } else {
            // ロンの場合
            costText = `${main}点`;
            console.log('ロン:', costText);
        }
    } else {
        console.log('displayResult - costが無効:', result.cost);
        costText = '点数計算エラー';
    }
    console.log('displayResult - 最終的なcostText:', costText);
    document.getElementById('costValue').textContent = costText;
    
    // 役の表示
    const yakuList = document.getElementById('yakuList');
    yakuList.innerHTML = '';
    
    if (result.yaku && result.yaku.length > 0) {
        result.yaku.forEach(yaku => {
            const yakuItem = document.createElement('div');
            yakuItem.className = 'yaku-item';
            yakuItem.textContent = yaku;
            yakuList.appendChild(yakuItem);
        });
    } else {
        const noYakuItem = document.createElement('div');
        noYakuItem.className = 'yaku-item';
        noYakuItem.textContent = '役なし';
        yakuList.appendChild(noYakuItem);
    }
    
    // 結果セクションを表示
    resultSection.classList.add('show');
    resultSection.scrollIntoView({ behavior: 'smooth' });
}

// ローディング表示の切り替え
function showLoading(show) {
    if (show) {
        loading.classList.add('show');
        resultSection.classList.remove('show');
    } else {
        loading.classList.remove('show');
    }
}

// エラー表示
function showError(message) {
    const errorDiv = document.createElement('div');
    errorDiv.className = 'error';
    errorDiv.textContent = message;
    
    // 既存のエラーメッセージを削除
    const existingError = document.querySelector('.error');
    if (existingError) {
        existingError.remove();
    }
    
    // エラーメッセージを挿入
    const mainContent = document.querySelector('.main-content');
    mainContent.insertBefore(errorDiv, mainContent.firstChild);
    
    // 3秒後に自動削除
    setTimeout(() => {
        if (errorDiv.parentNode) {
            errorDiv.parentNode.removeChild(errorDiv);
        }
    }, 5000);
}

// 単一牌認識のテスト関数（開発用）
async function testSingleTileRecognition(imageData) {
    try {
        const response = await fetch('https://mahjong-rcg-client.onrender.com/api/recognize', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ image: imageData })
        });
        
        const result = await response.json();
        console.log('Recognition result:', result);
        return result;
    } catch (error) {
        console.error('Recognition error:', error);
        return null;
    }
}

// 画像モーダルの設定
function setupImageModal() {
    // モーダルを閉じるイベント
    imageModalClose.onclick = hideImageModal;
    
    // モーダル背景をクリックしたら閉じる
    imageModal.onclick = function(e) {
        if (e.target === imageModal) {
            hideImageModal();
        }
    };
    
    // ESCキーでモーダルを閉じる
    document.addEventListener('keydown', function(e) {
        if (e.key === 'Escape' && imageModal.classList.contains('show')) {
            hideImageModal();
        }
    });
}

// 画像モーダルを表示
function showImageModal(imageData, containerId, index) {
    imageModalImage.src = imageData;
    
    // ヘッダーのテキストを設定
    if (containerId === 'handTilesPreview') {
        imageModalHeader.textContent = `手牌`;
    } else if (containerId === 'doraTilesPreview') {
        imageModalHeader.textContent = `ドラ表示牌`;
    } else {
        imageModalHeader.textContent = '画像プレビュー';
    }
    
    imageModal.classList.add('show');
    document.body.style.overflow = 'hidden'; // スクロールを無効化
}

// 画像モーダルを非表示
function hideImageModal() {
    imageModal.classList.remove('show');
    document.body.style.overflow = ''; // スクロールを有効化
    imageModalImage.src = '';
}

// デバッグ用の関数
function debugInfo() {
    console.log('Hand tiles:', handTilesImages.length);
    console.log('Dora tiles:', doraTilesImages.length);
    console.log('Form data:', {
        riichi: document.getElementById('riichi').checked,
        winType: document.getElementById('winType').value,
        roundWind: document.getElementById('roundWind').value,
        playerWind: document.getElementById('playerWind').value
    });
}
