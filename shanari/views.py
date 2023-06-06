import os, datetime, time
import flask_login, flask_wtf, wtforms
import tweepy, misskey
import py_ogp_parser.parser
import urllib.error
import urllib.request
from . import app
from flask import render_template, redirect, request
from nanoatp import BskyAgent
from PIL import Image, ImageOps, ExifTags
from PIL.ExifTags import TAGS
from urlextract import URLExtract

UPLOAD_FOLDER = app.config['UPLOAD_FOLDER']

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

# --- 投稿処理 ---
@app.route('/postTweet', methods=['POST'])
@flask_login.login_required
def postTweet():
    # 本文と投稿先の指定フラグを取得
    postText = request.form.get('postText', '')
    twitterCheck = request.form.get('twitterCheck', 'off')
    misskeyCheck = request.form.get('misskeyCheck', 'off')
    blueskyCheck = request.form.get('blueskyCheck', 'off')
    resultText = ''

    # 本文が空白だったらメッセージを返す
    if postText == '':
        resultText = '[ERROR]Content is blank.'
        return resultText

    # Twitter(Tweepy)
    if twitterCheck == 'on' and app.config['TWITTER_BEARAR_TOKEN'] != '':
        try:
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
        except Exception as e:
            resultText = '<b>Twitter[ERROR]</b>' + str(e)
            pass
        else:
            resultText = '<b>Twitter</b>:OK'
    else:
        resultText = '<b>Twitter</b>:OFF'
        
    # Misskey(Misskey.py)
    if misskeyCheck == 'on' and app.config['MISSKEY_TOKEN'] != '':
        try:
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
        except misskey.exceptions.MisskeyAPIException as e:
            # Exceptionが空で戻ってくるのでとりあえず仕様書通りに捕捉
            resultText = resultText + ('' if resultText=='' else '\n') + '<b>Misskey[ERROR]</b>MisskeyAPIException : ' + str(e)
            pass
        except misskey.exceptions.MisskeyAuthorizeFailedException:
            resultText = resultText + ('' if resultText=='' else '\n') + '<b>Misskey[ERROR]</b>MisskeyAuthorizeFailedException'
            pass
        except misskey.exceptions.MisskeyMiAuthFailedException:
            resultText = resultText + ('' if resultText=='' else '\n') + '<b>Misskey[ERROR]</b>MisskeyMiAuthFailedException'
            pass
        else:
            resultText = resultText + ('' if resultText=='' else '\n') + '<b>Misskey:</b>OK'
    else:
        resultText = resultText + ('' if resultText=='' else '\n') + '<b>Misskey:</b>OFF'

    # Bluesky(nanoatp)
    if blueskyCheck == 'on' and app.config['BLUESKY_PASS'] != '':
        try:
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
                        ogTitle = result['title']
                        ogImage = result['ogp']['og:image'][0]
                        ogImageFilename = os.path.basename(ogImage)
                        ogDesc = result['ogp']['og:description'][0]
                        # 一旦画像を保存
                        downloadFile(ogImage, os.path.join(UPLOAD_FOLDER, ogImageFilename))

            # 画像ファイルサイズ1MB上限対応
            MAX_FILE_SIZE = app.config['BLUESKY_MAX_FILE_SIZE']
            for f in os.listdir(UPLOAD_FOLDER):
                imagePath = os.path.join(UPLOAD_FOLDER, f)
                #回転情報を反映
                with Image.open(imagePath) as im:
                    rotationImage(im)
                #サイズ超過かつpngだったらとりあえずjpgに変換
                if os.path.getsize(imagePath) > MAX_FILE_SIZE and f.endswith('.png'):
                    with Image.open(imagePath) as im:
                        im = im.convert('RGB')
                        imagePath = imagePath[:-3]+'jpg'
                        im.save(imagePath)
                        os.remove(imagePath[:-3]+'png')
                #指定サイズ未満まで20%ちっこくしていく
                with Image.open(imagePath) as im:
                    while os.path.getsize(imagePath) > MAX_FILE_SIZE:
                        ratio = 0.8 
                        size = tuple(int(d * ratio) for d in im.size)
                        im.thumbnail(size)
                        im.save(imagePath, quality=85, optimize=True)

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
                if isLinkcardAttached == True and len(mediaList) > 0:
                    # リンクカードあり
                    external = {"uri": urlList[0], "title": ogTitle, "description": ogDesc, "thumb": mediaList[0]['image']}
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
        except Exception as e:
            resultText = resultText + ('' if resultText=='' else '\n') + '<b>Bluesky[ERROR]</b>' + str(e)
            pass
        else:
            resultText = resultText + ('' if resultText=='' else '\n') + '<b>Bluesky:</b>OK'
    else:
        resultText = resultText + ('' if resultText=='' else '\n') + '<b>Bluesky:</b>OFF'
        
    # エラーが発生していない場合は一時フォルダの画像をすべて削除
    if resultText.find('ERROR') == -1:
        for f in os.listdir(UPLOAD_FOLDER):
            os.remove(os.path.join(UPLOAD_FOLDER, f))

    return resultText

# exif情報に従って画像を回転させる
def rotationImage(im):
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
            return
    except Exception:
        return
    # Orientationが含まれていなければ何もしない
    if 'Orientation' not in exifTable:
        return
    # Orientationに従って回転させる(exif情報は削除する)
    rotate, reverse = getExifRotation(exifTable['Orientation'])
    with Image.new(im.mode, im.size) as newIm:
        newIm.putdata(im.getdata())
        if reverse == 1:
            newIm = ImageOps.mirror(newIm)
        if rotate != 0:
            newIm = newIm.rotate(rotate, expand=True)
        newIm.save(im.filename)

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

# URL指定されたファイルを保存する
def downloadFile(url, dstPath):
    try:
        with urllib.request.urlopen(url) as webFile:
            data = webFile.read()
            with open(dstPath, mode='wb') as localFile:
                localFile.write(data)
    except urllib.error.URLError as e:
        pass
