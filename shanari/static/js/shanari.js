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
            let file = item.getAsFile();
            imgPreview(file);
            let formData = new FormData();
            formData.append('pics', file);
            postImg(formData);
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
    let formData = new FormData();
    for (let file of e.dataTransfer.files) {
        // 画像だけ
        if (file.type.indexOf('image') < 0) continue;
        // 4件以上追加できない
        if (picCnt++ >= 4) break;
        // プレビュー表示して送信用のformDataに追加する
        imgPreview(file);
        formData.append('pics', file);
    }
    //送信
    postImg(formData);
});

// アップロード指定されたファイルを送信する
function storePics(event) {
    let formData = new FormData();
    for (let file of event.target.files) {
        // 画像だけ
        if (file.type.indexOf('image') < 0) continue;
        // 4件以上追加できない
        if (picCnt++ >= 4) break;
        // プレビュー表示して送信用のformDataに追加する
        imgPreview(file);
        formData.append('pics', file);
    }
    //送信
    postImg(formData);
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
});

// 画像をサーバに送信する
function postImg(formData) {
    $.ajax({
        url: '/uploadImg',
        type: 'post',
        data: formData,
        dataType: 'text',
        processData: false,
        contentType: false,
        timeout: 10000
    }).always(function(receivedData) {
        let resultMsg = receivedData;
        resultMsg = resultMsg.replace(/\r?\n/g, '<br>');
        $('#resultMsg').html(resultMsg);
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
        let resultMsg = receivedData;
        resultMsg = resultMsg.replace(/\r?\n/g, '<br>');
        $('#resultMsg').html(resultMsg);
    });
    // プレビューを初期化する
    picCnt = 0;
    let preview = document.getElementById('previewArea');
    while (preview.firstChild) {
        preview.removeChild(preview.firstChild);
    }
}

// 機能を初期状態に戻す
function initialize() {
    removeImg();
    clearForm();
}

// formを初期状態に戻す
function clearForm() {
    picCnt = 0;
    let preview = document.getElementById('previewArea');
    while (preview.firstChild) {
        preview.removeChild(preview.firstChild);
    }
    $('#word-count').text('0 / 280');
    document.forms['uploadForm'].reset();
}

// 画像以外のform情報を送信(投稿実行)
function postTweet() {
    $('#resultMsg').html('processing...');
    $('#sendButton').prop('disabled',true);
    $('#clearButton').prop('disabled',true);
    $('#files').prop('disabled',true);
    document.getElementById('spinner').style.display = 'block';
    let form = $('#uploadForm').get()[0];
    let formData = new FormData(form);
    let receivedData = ''
    $.ajax({
        url: '/postTweet',
        type: 'post',
        data: formData,
        dataType: 'text',
        processData: false,
        contentType: false,
        timeout: 30000
    }).done(function(receivedData) {
        resultMsg = receivedData;
        new Promise((resolve) => {
            if(resultMsg.indexOf('ERROR') == -1){
                clearForm();
            }
            resolve();
        }).then(() => {
            document.getElementById('spinner').style.display = 'none';
            resultMsg = resultMsg.replace(/\r?\n/g, '<br>');
            $('#resultMsg').html(resultMsg);
            $('#sendButton').prop('disabled',false);
            $('#clearButton').prop('disabled',false);
            $('#files').prop('disabled',false);
        });
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
        $('#word-count').text(len + ' / 280');
    });
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
        // 4sqAPI経由で周辺施設を取得
        let position = await getCurrentPositionPromise();
        let formData = new FormData();
        formData.append('lat', position.coords.latitude);
        formData.append('lng', position.coords.longitude);
        $.ajax({
            url: '/get4sqVenues',
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
            listSrc = '<div class="instructions">左スワイプでチェックインします</div>';
            listSrc += '<ul class="list-container" id="itemList">';
            receivedData.forEach(item => {
                listSrc += '<li class="list-item" data-id="' + `${item.fsq_id}` + '">';
                listSrc += '<span class="list-item-name">' + `${item.name}` + '</span>';
                listSrc += '<span class="list-item-distance">' + `${item.distance}` + 'm</span>';
                listSrc += '</li>';
            });
            listSrc += '</ul>';
            listSrc += '<div class="notice">このアプリケーションは、Foursquare® アプリケーションのプログラミングインターフェースを使用しておりますが、Foursquare Labs, Inc. によって承認または認定されているわけではございません。<br />本アプリケーションに表示されているすべての Foursquare® ロゴ(すべてのバッジを含む)と登録商標は、Foursquare Labs, Inc. に帰属します。<br /></div>';
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
                            let venueId = item.getAttribute('data-id');
                            let venueName = item.querySelector('.list-item-name').textContent;
                            let venueText = "I'm at " + venueName + '\r\nhttps://foursquare.com/v/' + venueId;
                            textarea.value = venueText;
                            // 4qsにチェックインを送信
                            let formDataChkin = new FormData();
                            formDataChkin.append('venueid', venueId);
                            $.ajax({
                                url: '/chkin4sqVenue',
                                type: 'post',
                                data: formDataChkin,
                                dataType: 'text',
                                processData: false,
                                contentType: false,
                                timeout: 10000
                            }).always(function(receivedData) {
                                let resultMsg = receivedData;
                                resultMsg = resultMsg.replace(/\r?\n/g, '<br>');
                                $('#resultMsg').html(resultMsg);
                            });
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
const showModalBtn = document.querySelector(".button4sq");
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
