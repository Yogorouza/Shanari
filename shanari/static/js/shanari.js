// 添付画像数
var picCnt = 0;

// eventからクリップボードのアイテムを取り出し送信する
document.onpaste = function (event) {
    let items = (event.clipboardData || event.originalEvent.clipboardData).items;
    for (let i = 0; i < items.length; i++) {
        let item = items[i];
        // 画像だけ
        if (item.type.indexOf('image') != -1) {
            // 4件以上追加できない
            if (picCnt++ >= 4) return;
            // プレビュー表示して送信
            $('#resultMsg').html('<b>uploading...</b>');
            document.getElementById('spinner').style.visibility = 'visible';
            let file = item.getAsFile();
            imgPreview(file);
            postImg(file);
        }
    }
}

// ドラッグドロップされたファイルを取り出し送信する
document.addEventListener('dragover', function(e) {
    e.preventDefault();
    e.dataTransfer.dropEffect = 'copy';
});
document.addEventListener('drop', function(e) {
    e.preventDefault();
    for (let file of e.dataTransfer.files) {
        // 画像だけ
        if (file.type.indexOf('image') < 0) continue;
        // 4件以上追加できない
        if (picCnt++ >= 4) break;
        // プレビュー表示して送信
        $('#resultMsg').html('<b>uploading...</b>');
        document.getElementById('spinner').style.visibility = 'visible';
        imgPreview(file);
        postImg(file);
    }
});

// アップロード指定されたファイルを送信する
function storePics(event) {
    $('#resultMsg').html('<b>uploading...</b>');
    document.getElementById('spinner').style.visibility = 'visible';
    for (let file of event.target.files) {
        // 画像だけ
        if (file.type.indexOf('image') < 0) continue;
        // 4件以上追加できない
        if (picCnt++ >= 4) break;
        // プレビュー表示して送信
        imgPreview(file);
        postImg(file);
    }
}

// ファイルのプレビューを表示
function imgPreview(file) {
    let preview = document.getElementById('previewArea');
    let reader = new FileReader();
    reader.onload = function (event) {
        let img = document.createElement('img');
        img.setAttribute('src', reader.result);
        img.setAttribute('id', 'previewImage-previewArea');
        img.setAttribute('class', 'tmp');
        preview.appendChild(img);
    };
    reader.readAsDataURL(file);
}

// プレビュー画像がタップされたら添付ファイルを初期化する
document.getElementById('previewArea').addEventListener('click', function(e) {
    removeImg();
    $('#resultMsg').html(resultMsg);
});

// 画像をサーバに送信する
function postImg(file) {
    if(enableServerCompress == '1')
        postImgNoCompress(file);
    else
        postImgWithCompress(file);
};

// 画像をサーバに送信する(縮小しない)
function postImgNoCompress(file) {
    let formData = new FormData();
    formData.append('pics', file);
    $.ajax({
        url: '/uploadImg',
        type: 'post',
        data: formData,
        dataType: 'text',
        processData: false,
        contentType: false,
        timeout: 20000
    }).always(function(receivedData) {
        document.getElementById('spinner').style.visibility = 'hidden';
        let resultMsg = receivedData;
        resultMsg = '<b>' + resultMsg.replace(/\r?\n/g, '<br>') + '</b>';
        $('#resultMsg').html(resultMsg);
    });
};

// 画像をサーバに送信する(必要に応じて縮小する)
function postImgWithCompress(file) {
    resizeImg(file).then(function(resizedBlob) {
        let formData = new FormData();
        formData.append('pics', resizedBlob, file.name);
        $.ajax({
            url: '/uploadImg',
            type: 'post',
            data: formData,
            dataType: 'text',
            processData: false,
            contentType: false,
            timeout: 20000
        }).always(function(receivedData) {
            document.getElementById('spinner').style.visibility = 'hidden';
            let resultMsg = receivedData;
            resultMsg = '<b>' + resultMsg.replace(/\r?\n/g, '<br>') + '</b>';
            $('#resultMsg').html(resultMsg);
        });
    });
};

// 添付ファイルを初期化する
function removeImg() {
    // サーバの画像フォルダを初期化する
    let formData = new FormData();
    $.ajax({
        url: '/clearImg',
        type: 'post',
        data: formData,
        dataType: 'text',
        processData: false,
        contentType: false,
        timeout: 10000
    }).always(function(receivedData) {
    });
    // プレビューを初期化する
    picCnt = 0;
    let preview = document.getElementById('previewArea');
    while (preview.firstChild) {
        preview.removeChild(preview.firstChild);
    }
}

//ファイルサイズを1MBまで縮小する
function resizeImg(file) {
    return new Promise((resolve, reject) => {
        var img = new Image();
        img.onload = () => {
            var canvas = document.createElement('canvas');
            var ctx = canvas.getContext('2d');
            var width = img.width;
            var height = img.height;
            var quality = 0.9; // 画質を維持するための初期品質値
            // 画像を縮小する関数
            const resize = () => {
                canvas.width = width;
                canvas.height = height;
                ctx.drawImage(img, 0, 0, width, height);
                canvas.toBlob((blob) => {
                    if (blob.size <= 1.0 * 1024 * 1024) {
                        resolve(blob); // サイズが要件を満たしたらPromiseを解決
                    } else {
                        // サイズがまだ大きい場合は、さらに縮小
                        width *= 0.9; // 幅を10%縮小
                        height *= 0.9; // 高さを10%縮小
                        resize(); // 再帰的に縮小処理を呼び出し
                    }
                }, 'image/jpeg', quality);
            };
            resize(); // 最初の縮小処理を呼び出し
        };
        img.onerror = reject;
        img.src = URL.createObjectURL(file); // ファイルからURLを生成して画像を読み込む
    });
}

// 機能を初期状態に戻す
function initialize() {
    removeImg();
    clearForm();
    $('#resultMsg').text('Shanari: Initialized.');
}

// formを初期状態に戻す
function clearForm() {
    picCnt = 0;
    let preview = document.getElementById('previewArea');
    while (preview.firstChild) {
        preview.removeChild(preview.firstChild);
    }
    document.forms['uploadForm'].reset();
    updateCheckbox();
}

// チェックボックスの外観を更新する
function updateCheckbox() {
    let chk = document.getElementById('twitterCheck');
    let el = document.getElementById('twitterCheck').nextElementSibling;
    while (el) {
        el.style.opacity = chk.checked ? "1" : "0.2";
        el = el.nextElementSibling;
    }
    chk = document.getElementById('misskeyCheck');
    el = document.getElementById('misskeyCheck').nextElementSibling;
    while (el) {
        el.style.opacity = chk.checked ? "1" : "0.2";
        el = el.nextElementSibling;
    }
    chk = document.getElementById('blueskyCheck');
    el = document.getElementById('blueskyCheck').nextElementSibling;
    while (el) {
        el.style.opacity = chk.checked ? "1" : "0.2";
        el = el.nextElementSibling;
    }
}

// 投稿時のajax発呼処理
function ajaxCall(url, data, snsName) {
    return new Promise((resolve, reject) => {
        $.ajax({
            url: url,
            type: 'post',
            data: data,
            dataType: 'text',
            processData: false,
            contentType: false,
            timeout: 20000,
            success: function(response) {
                let resultMsg = $('#resultMsg').html();
                let responseMsg = '<br>' + response;
                $('#resultMsg').html(resultMsg + responseMsg);
                resolve(response);
            },
            error: function(jqXHR, textStatus, errorThrown) {
                let resultMsg = $('#resultMsg').html();
                let responseMsg = '<br><b>' + snsName + '[ERROR]</b>:' + textStatus;
                $('#resultMsg').html(resultMsg + responseMsg);
                reject(errorThrown);
            }
        });
    });
}

// 画像以外のform情報を送信(投稿実行)
function postTweet() {
    let textarea = document.getElementById('postText');
    if(textarea.value.trim() == ''){
        $('#resultMsg').html('[ERROR]Content is blank.');
        return;
    }
    $('#resultMsg').html('processing...<br>');
    $('#sendButton').prop('disabled',true);
    $('#clearButton').prop('disabled',true);
    $('#files').prop('disabled',true);
    document.getElementById('spinner').style.visibility = 'visible';
    let form = $('#uploadForm').get()[0];
    let formData = new FormData(form);
    Promise.allSettled([
        ajaxCall('/postTwitter', formData, 'Twitter'),
        ajaxCall('/postMisskey', formData, 'Misskey'),
        ajaxCall('/postBluesky', formData, 'Bluesky')
    ]).then(function(results) {
        let errFlg = 0;
        results.forEach((result) => {
            let resultMsg = $('#resultMsg').html();
            if (result.status === "fulfilled" && resultMsg.indexOf('ERROR') == -1) {
            } else {
                errFlg = 1;
            }
        });
        if(errFlg == 0){
            removeImg();
            clearForm();
        }
        document.getElementById('spinner').style.visibility = 'hidden';
        $('#sendButton').prop('disabled',false);
        $('#clearButton').prop('disabled',false);
        $('#files').prop('disabled',false);
        let resultMsg = $('#resultMsg').html();
        resultMsg = resultMsg.replace('processing...','done.');
        $('#resultMsg').html(resultMsg);
    });
}

// textareaの文字数カウント
$(function () {
    $('textarea').keyup(function () {
        let str = $(this).val();
        let len = 0;
        for (let i = 0; i < str.length; i++) {
            let c = str.charCodeAt(i);
            if ((c >= 0x0 && c < 0x81) || (c == 0xf8f0) || (c >= 0xff61 && c < 0xffa0) || (c >= 0xf8f1 && c < 0xf8f4))
                len += 1;
            else
                len += 2;
        }
        $('#resultMsg').text(len + ' / 280');
    });
});

// チェックボックスの外観補助
document.getElementById('twitterCheck').addEventListener('change', function() {
    updateCheckbox();
});
document.getElementById('misskeyCheck').addEventListener('change', function() {
    updateCheckbox();
});
document.getElementById('blueskyCheck').addEventListener('change', function() {
    updateCheckbox();
});

// 位置情報取得
function getCurrentPositionPromise(options = {}) {
    return new Promise((resolve, reject) => {
        navigator.geolocation.getCurrentPosition(resolve, reject, options);
    });
}

// ボトムシートの内訳生成
async function genBottomSheetContents() {
    try {
        // Google Places API経由で周辺施設を取得
        let position = await getCurrentPositionPromise();
        let formData = new FormData();
        formData.append('lat', position.coords.latitude);
        formData.append('lng', position.coords.longitude);
        $.ajax({
            url: '/getNearby',
            type: 'post',
            data: formData,
            dataType: 'json',
            processData: false,
            contentType: false,
            timeout: 10000
        }).always(function(receivedData) {
            bottomSheetContent.innerHTML = '';
            if (receivedData.hasOwnProperty("errText")) {
                $('#resultMsg').html(receivedData.errText);
                return;
            }
            // 施設の取得に成功したら一覧生成
            let listSrc = '';
            listSrc = '<div class="instructions">左スワイプで本文に設定します</div>';
            listSrc += '<ul class="list-container" id="itemList">';
            receivedData.forEach(item => {
               let pref = item.addressComponents
                    .filter(component => component.types.includes('administrative_area_level_1'))
                    .map(component => component.shortText);
                let addr = pref + item.addressComponents
                    .filter(component => component.types.includes('locality'))
                    .map(component => component.shortText);
                listSrc += '<li class="list-item" url="' + `${item.googleMapsUri}` + '" addr="' + `${addr}` + '">';
                listSrc += '<span class="list-item-name">' + `${item.displayName.text}` + '</span>';
                listSrc += '</li>';
            });
            listSrc += '</ul>';
            bottomSheetContent.innerHTML = listSrc;
            // スワイプイベントをli要素に割り当てる
            let listItems = document.querySelectorAll('.list-item');
            listItems.forEach(item => {
                let hammer = new Hammer(item);
                let isSwiping = false;
                let isVerticalScrolling = false;
                hammer.on('panstart', function(e) {
                    isVerticalScrolling = Math.abs(e.angle) > 30 && Math.abs(e.angle) < 150;
                });
                hammer.on('pan', function(e) {
                    if (isVerticalScrolling)
                        return true;
                    isSwiping = true;
                    item.style.transform = `translateX(${e.deltaX}px)`;
                });
                hammer.on('panend', function(e) {
                    if (isSwiping) {
                        // スワイプ実行時
                        const halfWidth = item.offsetWidth / 2;
                        if (Math.abs(e.deltaX) > halfWidth) {
                            // 投稿用テキストを生成
                            let textarea = document.getElementById('postText');
                            let nearbyUrl = item.getAttribute('url');
                            let nearbyAddr = item.getAttribute('addr');
                            let nearbyName = item.querySelector('.list-item-name').textContent + '(' + nearbyAddr + ')';
                            let nearbyText = "I'm at " + nearbyName + '\r\n' + nearbyUrl;
                            textarea.value = nearbyText;
                            // ボトムテキストを閉じる
                            bottomSheet.classList.remove("show");
                            document.body.style.overflowY = "auto";
                        }
                        item.style.transform = 'translateX(0px)';
                        isSwiping = false;
                    }
                });
            });
            // ボトムシート表示
            bottomSheet.classList.add("show");
            document.body.style.overflowY = "hidden";
            updateSheetHeight(50);
        });
    } catch (error) {
        console.error('位置情報の取得に失敗しました:', error);
    }
}

  // ボトムシート動作定義
const showModalBtn = document.querySelector(".buttonMap");
const bottomSheet = document.querySelector(".bottom-sheet");
const sheetOverlay = bottomSheet.querySelector(".sheet-overlay");
const sheetContent = bottomSheet.querySelector(".content");
const dragIcon = bottomSheet.querySelector(".drag-icon");
const bottomSheetContent = document.getElementById("bottomSheetContent");
var isDragging = false, startY, startHeight;
const showBottomSheet = () => {
    genBottomSheetContents();
}
const updateSheetHeight = (height) => {
    sheetContent.style.height = `${height}vh`;
    bottomSheet.classList.toggle("fullscreen", height === 100);
}
const hideBottomSheet = () => {
    bottomSheet.classList.remove("show");
    document.body.style.overflowY = "auto";
}
const dragStart = (e) => {
    isDragging = true;
    startY = e.pageY || e.touches?.[0].pageY;
    startHeight = parseInt(sheetContent.style.height);
    bottomSheet.classList.add("dragging");
}
const dragging = (e) => {
    if(!isDragging) return;
    const delta = startY - (e.pageY || e.touches?.[0].pageY);
    const newHeight = startHeight + delta / window.innerHeight * 100;
    updateSheetHeight(newHeight);
}
const dragStop = () => {
    isDragging = false;
    bottomSheet.classList.remove("dragging");
    const sheetHeight = parseInt(sheetContent.style.height);
    sheetHeight < 25 ? hideBottomSheet() : sheetHeight > 75 ? updateSheetHeight(100) : updateSheetHeight(50);
}
dragIcon.addEventListener("mousedown", dragStart);
document.addEventListener("mousemove", dragging);
document.addEventListener("mouseup", dragStop);
dragIcon.addEventListener("touchstart", dragStart);
document.addEventListener("touchmove", dragging);
document.addEventListener("touchend", dragStop);
sheetOverlay.addEventListener("click", hideBottomSheet);
showModalBtn.addEventListener("click", showBottomSheet);
