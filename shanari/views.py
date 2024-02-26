import os, io, datetime, time, requests, tempfile, json
import flask_login, flask_wtf, wtforms
import tweepy, misskey
import py_ogp_parser.parser
import urllib.error
import urllib.request
from . import app
from flask import render_template, redirect, request
from nanoatp import BskyAgent
from PIL import Image, ImageOps
from PIL.ExifTags import TAGS
from urlextract import URLExtract

# --- 作業フォルダを掘る ---
temp_dir = tempfile.gettempdir()
UPLOAD_FOLDER = temp_dir + '/shanariwk'
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

# --- ログインマネージャ・認証関連 ---
login_manager = flask_login.LoginManager()
login_manager.init_app(app)

class User(flask_login.UserMixin):
    def __init__(self, user_id):
        self.id = user_id

class LoginForm(flask_wtf.FlaskForm):
    user_id = wtforms.StringField('user_id', [wtforms.validators.DataRequired(), wtforms.validators.Length(min=3, max=20)])
    password = wtforms.PasswordField('password', [wtforms.validators.DataRequired(), wtforms.validators.Length(min=3, max=20)])

@login_manager.user_loader
def load_user(user_id):
    return User(user_id)

@login_manager.unauthorized_handler
def unauthorized():
    return redirect('/login')

@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm(request.form)
    if form.validate_on_submit():
        if form.user_id.data == app.config['LOGIN_ID'] and form.password.data == app.config['LOGIN_PASSWORD']:
            user = User(form.user_id.data)
            flask_login.login_user(user)
            return redirect('/')
        else:
            pass
    return render_template('login.html', form=form)
    
@app.route('/logout', methods=['GET'])
def logout():
    flask_login.logout_user()
    return 'logout'

# --- ルート(投稿画面) ---
@app.route('/')
@flask_login.login_required
def index():
    return render_template('postForm.html')

# --- 画像添付 ---
@app.route('/uploadImg', methods=['POST'])
@flask_login.login_required
def uploadImg():
    resultText = ''
    try:
        # ファイル名にタイムスタンプを付与して保存
        for pic in request.files.getlist('pics'):
            newFileName = datetime.datetime.now().strftime('%Y%m%d%H%M%S%f')[:-2] + '_' + pic.filename
            pic.save(os.path.join(UPLOAD_FOLDER, newFileName))
        # 現在のファイル数を示すメッセージを返す
        fileCnt = sum(os.path.isfile(os.path.join(UPLOAD_FOLDER, name)) for name in os.listdir(UPLOAD_FOLDER))
        resultText = str(fileCnt) + (' image' if fileCnt == 1 else ' images') + ' ready.'
    except Exception as e:
        resultText = str(e)
        pass
    return resultText

# --- 画面初期化 ---
@app.route('/clearImg', methods=['POST'])
@flask_login.login_required
def clearImg():
    resultText = ''
    try:
        # 現在送信されている画像をすべて削除
        for f in os.listdir(UPLOAD_FOLDER):
            os.remove(os.path.join(UPLOAD_FOLDER, f))
    except Exception as e:
        resultText = str(e)
        pass
    return resultText

# --- 投稿処理(Twitter) ---
@app.route('/postTwitter', methods=['POST'])
@flask_login.login_required
def postTwitter():
    # 本文と投稿先の指定フラグを取得
    postText = request.form.get('postText', '')
    twitterCheck = request.form.get('twitterCheck', 'off')
    resultText = ''

    # Twitter(Tweepy)
    if twitterCheck == 'on' and app.config['TWITTER_BEARAR_TOKEN'] != '':
        try:
            timeStart = time.perf_counter()
            # APIv1認証
            auth = tweepy.OAuthHandler(app.config['TWITTER_CONSUMER_KEY'], app.config['TWITTER_CONSUMER_SECRET'])
            auth.set_access_token(app.config['TWITTER_ACCESS_TOKEN_KEY'], app.config['TWITTER_ACCESS_TOKEN_SECRET'])
            api = tweepy.API(auth)
            # 画像アップロード
            mediaList = []
            for f in os.listdir(UPLOAD_FOLDER):
                image_path = os.path.join(UPLOAD_FOLDER, f)
                media = api.media_upload(filename=image_path)
                mediaList.append(media.media_id)
            # APIv2認証
            client = tweepy.Client(
                bearer_token = app.config['TWITTER_BEARAR_TOKEN'],
                consumer_key = app.config['TWITTER_CONSUMER_KEY'],
                consumer_secret = app.config['TWITTER_CONSUMER_SECRET'],
                access_token = app.config['TWITTER_ACCESS_TOKEN_KEY'],
                access_token_secret = app.config['TWITTER_ACCESS_TOKEN_SECRET']
            )
            # 投稿
            if len(mediaList) == 0:
                client.create_tweet(text=postText)
            else:
                client.create_tweet(text=postText, media_ids=mediaList)
            timeEnd = time.perf_counter()
        except Exception as e:
            resultText = '<b>Twitter[ERROR]</b>' + str(e)
            pass
        else:
            sec = round(timeEnd- timeStart, 1)
            resultText = '<b>Twitter</b>:OK(' + str(sec) + 'sec)'
    else:
        resultText = '<b>Twitter</b>:OFF'

    return resultText

# --- 投稿処理(Misskey) ---
@app.route('/postMisskey', methods=['POST'])
@flask_login.login_required
def postMisskey():
    # 本文と投稿先の指定フラグを取得
    postText = request.form.get('postText', '')
    misskeyCheck = request.form.get('misskeyCheck', 'off')
    resultText = ''

    # Misskey(Misskey.py)
    if misskeyCheck == 'on' and app.config['MISSKEY_TOKEN'] != '':
        try:
            timeStart = time.perf_counter()
            # 認証
            api = misskey.Misskey(app.config['MISSKEY_HOST'])
            api.token = app.config['MISSKEY_TOKEN']
            # 画像アップロード
            mediaList = []
            for f in os.listdir(UPLOAD_FOLDER):
                with open(os.path.join(UPLOAD_FOLDER, f), 'rb') as f:
                    data = api.drive_files_create(f)
                mediaList.append(data['id']);
            # 投稿
            if len(mediaList) == 0:
                api.notes_create(text=postText)
            else:
                api.notes_create(text=postText, file_ids=mediaList)
            timeEnd = time.perf_counter()
        except misskey.exceptions.MisskeyAPIException as e:
            # Exceptionが空で戻ってくるのでとりあえず仕様書通りに捕捉
            resultText = '<b>Misskey[ERROR]</b>MisskeyAPIException : ' + str(e)
            pass
        except misskey.exceptions.MisskeyAuthorizeFailedException:
            resultText = '<b>Misskey[ERROR]</b>MisskeyAuthorizeFailedException'
            pass
        except misskey.exceptions.MisskeyMiAuthFailedException:
            resultText = '<b>Misskey[ERROR]</b>MisskeyMiAuthFailedException'
            pass
        else:
            sec = round(timeEnd- timeStart, 1)
            resultText = '<b>Misskey:</b>OK(' + str(sec) + 'sec)'
    else:
        resultText = '<b>Misskey:</b>OFF'

    return resultText

# --- 投稿処理(Bluesky) ---
@app.route('/postBluesky', methods=['POST'])
@flask_login.login_required
def postBluesky():
    # 本文と投稿先の指定フラグを取得
    postText = request.form.get('postText', '')
    blueskyCheck = request.form.get('blueskyCheck', 'off')
    resultText = ''

    # Bluesky(nanoatp)
    if blueskyCheck == 'on' and app.config['BLUESKY_PASS'] != '':
        try:
            timeStart = time.perf_counter()
            # 添付画像有無を確認
            isFileAttached = False
            for f in os.listdir(UPLOAD_FOLDER):
                isFileAttached = True
                break

            # 添付画像が無ければリンクカードの生成を試みる
            isLinkcardAttached = False
            if(isFileAttached == False):
                extractor = URLExtract()
                urlList = extractor.find_urls(postText)
                # URLが含まれていれば生成する
                if len(urlList) > 0:
                    status_code, result = py_ogp_parser.parser.request(urlList[0])
                    if status_code == 200:
                        isLinkcardAttached = True
                        ogTitle = ''
                        ogDesc = ''
                        try:
                            ogTitle = result['title']
                            ogDesc = result['ogp']['og:description'][0]
                            ogImage = result['ogp']['og:image'][0]
                            ogImageFilename = os.path.basename(ogImage)
                            ogImageFilename = ogImageFilename.split('?')[0]
                            ogImageFilename = ogImageFilename.split('&')[0]
                            # 画像を保存
                            saveDownloadImage(ogImage, os.path.join(UPLOAD_FOLDER, ogImageFilename))
                            # 画像ファイルサイズ1MB上限対応
                            MAX_FILE_SIZE = app.config['BLUESKY_MAX_FILE_SIZE']
                            for f in os.listdir(UPLOAD_FOLDER):
                                imagePath = os.path.join(UPLOAD_FOLDER, f)
                                # サイズ超過してれば縮小する
                                if os.path.getsize(imagePath) <= MAX_FILE_SIZE:
                                    continue
                                with Image.open(imagePath) as im:
                                    # 指定サイズ未満まで20%ちっこくしていく
                                    compressImage(im, imagePath, MAX_FILE_SIZE)
                        except:
                            # タイトルが取得出来ていなかったらリンクカードの生成は行わない
                            if ogTitle is None or ogTitle == '':
                                isLinkcardAttached = False
                            pass

            # 認証
            agent = BskyAgent(app.config['BLUESKY_AGENT'])
            agent.login(identifier=app.config['BLUESKY_ID'], password=app.config['BLUESKY_PASS'])
            # 画像アップロード
            mediaList = []
            for f in os.listdir(UPLOAD_FOLDER):
                image = agent.uploadImage(os.path.join(UPLOAD_FOLDER, f))
                mediaList.append(image)
            # 投稿情報生成
            if isFileAttached == False:
                # 画像添付なし
                if isLinkcardAttached == True:
                    # リンクカードあり
                    if len(mediaList) > 0:
                        # 画像あり
                        external = {"uri": urlList[0], "title": ogTitle, "description": ogDesc, "thumb": mediaList[0]['image']}
                    else:
                        # 画像なし
                        external = {"uri": urlList[0], "title": ogTitle, "description": ogDesc}
                    embed = {"$type": "app.bsky.embed.external", "external": external}
                    record = {"text": postText, "embed": embed}
                else:
                    # リンクカードなし
                    record = {"text": postText}
            else:
                # 画像添付あり
                embed = {"$type": "app.bsky.embed.images#main", "images": mediaList}
                record = {"text": postText, "embed": embed}
            # 投稿
            agent.post(record)
            timeEnd = time.perf_counter()
        except Exception as e:
            resultText = '<b>Bluesky[ERROR]</b>' + str(e)
            pass
        else:
            sec = round(timeEnd- timeStart, 1)
            resultText = '<b>Bluesky:</b>OK(' + str(sec) + 'sec)'
    else:
        resultText = '<b>Bluesky:</b>OFF'
        
    return resultText

# --- Google Placesより周辺情報取得 ---
@app.route('/getNearby', methods=['POST'])
@flask_login.login_required
def getNearby():
    lat = request.form.get('lat', '')
    lng = request.form.get('lng', '')
    nearby = get_nearby(lat, lng)
    return nearby

# 指定サイズまで画像ファイルサイズを縮小
def compressImage(im, outputPath, maxSize):
    # 回転情報を取得
    rotate, reverse = getOrientationInfo(im)
    # 20%ずつ縮小する
    ratio = 0.8
    while True:
        # 縮小
        width, height = im.size
        newResolution = (int(width * ratio), int(height * ratio))
        resizedIm = im.resize(newResolution)
        # 縮小結果をメモリに保存
        byteArr = io.BytesIO()
        resizedIm.save(byteArr, format='JPEG', quality=70, optimize=True)
        size = byteArr.tell()
        # サイズを確認する
        if size <= maxSize:
            # 指定サイズ以下であれば保存する
            # 回転の必要があれば適用する
            if rotate is not None and (reverse == 1 or rotate != 0):
                with Image.new(resizedIm.mode, resizedIm.size) as newIm:
                    newIm.putdata(resizedIm.getdata())
                    if reverse == 1:
                        newIm = ImageOps.mirror(newIm)
                    if rotate != 0:
                        newIm = newIm.rotate(rotate, expand=True)
                    byteArr = io.BytesIO()
                    newIm.save(byteArr, format='JPEG', quality=70, optimize=True)
                    rotate = None
                # 回転後のサイズを一応チェック
                size = byteArr.tell()
                if size > maxSize:
                    # 超過してたらループ継続
                    im = Image.open(byteArr)
                    continue
            # ファイルに保存する
            byteArr.seek(0)
            os.remove(outputPath)
            outputPath = os.path.splitext(os.path.basename(outputPath))[0] + '.jpg'
            outputPath = os.path.join(UPLOAD_FOLDER, outputPath)
            with open(outputPath, 'wb') as f:
                f.write(byteArr.read())
            return
        else:
            # まだ指定サイズより大きければループ継続
            im = Image.open(byteArr)

# exif情報にOrientationが含まれていれば画像の回転情報を返す
def getOrientationInfo(im):
    # exif情報取得
    exifTable = {}
    try:
        exif = None
        exif = im._getexif()
        if exif is not None:
            for tagId, value in exif.items():
                tag = TAGS.get(tagId, tagId)
                exifTable[tag] = value
        else:
            return (None, None)
    except Exception:
        return (None, None)
    # Orientationが含まれていれば画像の回転情報を返す
    if 'Orientation' not in exifTable:
        return (None, None)
    else:
        return getExifRotation(exifTable['Orientation'])

# Orientationの回転情報を返す
def getExifRotation(orientationNum):
    if orientationNum == 1:
        return 0, 0
    if orientationNum == 2:
        return 0, 1
    if orientationNum == 3:
        return 180, 0
    if orientationNum == 4:
        return 180, 1
    if orientationNum == 5:
        return 270, 1
    if orientationNum == 6:
        return 270, 0
    if orientationNum == 7:
        return 90, 1
    if orientationNum == 8:
        return 90, 0

# URL指定された画像ファイルを保存する
def saveDownloadImage(url, dstPath):
    try:
        with urllib.request.urlopen(url) as webFile:
            data = webFile.read()
            with open(dstPath, mode='wb') as localFile:
                localFile.write(data)
    except urllib.error.URLError as e:
        pass

# Google Places APIより周辺施設を取得
def get_nearby(lat, lng, radius=300, limit=20):
    url = 'https://places.googleapis.com/v1/places:searchNearby'
    api_key = app.config['GOOGLE_PLACES_API_KEY']
    headers = {
        'Content-Type': 'application/json',
        'X-Goog-Api-Key': api_key,
        'X-Goog-FieldMask': 'places.displayName,places.addressComponents,places.googleMapsUri',
    }
    params = {
        'maxResultCount': limit,
        'languageCode': 'ja',
        'locationRestriction': {
            'circle': {
                'center': {'latitude': f'{lat}', 'longitude': f'{lng}'},
                'radius': radius
            }
        }
    }
    response = requests.post(url, headers=headers, data=json.dumps(params))
    if response.status_code == 200:
        return response.json()['places']
    else:
        errText = f"<b>GooglePlaces[ERROR]</b>Failed to retrieve nearby: {response.status_code}, {response.text}"
        return {'errText': errText}
