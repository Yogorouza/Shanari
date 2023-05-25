import os, datetime, time
import flask_login, flask_wtf, wtforms
import tweepy, misskey
from . import app
from flask import render_template, redirect, request
from nanoatp import BskyAgent
from PIL import Image

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

# --- 画像添付(非同期) ---
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

# --- 画面初期化(同期) ---
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

# --- 投稿処理(同期) ---
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
        resultText = 'Content is blank.'
        return resultText

    #Twitter(Tweepy)
    if twitterCheck == 'on':
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

    #Misskey(Misskey.py)
    if misskeyCheck == 'on':
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

    #Bluesky(nanoatp)
    if blueskyCheck == 'on':
        try:
            # 画像ファイルサイズ1MB上限対応
            MAX_FILE_SIZE = app.config['BLUESKY_MAX_FILE_SIZE']
            for f in os.listdir(UPLOAD_FOLDER):
                image_path = os.path.join(UPLOAD_FOLDER, f)
                #とりあえずpngだったらjpgに変換
                if f.endswith('.png'):
                    im = Image.open(image_path)
                    im = im.convert('RGB')
                    image_path = image_path[:-3]+'jpg'
                    im.save(image_path)
                    os.remove(image_path[:-3]+'png')
                #それでもまだでかいなら指定サイズ未満まで10%ちっこくしていく
                with Image.open(image_path) as im:
                    while os.path.getsize(image_path) > MAX_FILE_SIZE:
                        ratio = 0.9 
                        size = tuple(int(d * ratio) for d in im.size)
                        im.thumbnail(size)
                        im.save(image_path, quality=85, optimize=True)
            # 認証
            agent = BskyAgent(app.config['BLUESKY_AGENT'])
            agent.login(identifier=app.config['BLUESKY_ID'], password=app.config['BLUESKY_PASS'])
            # 画像アップロード
            mediaList = []
            for f in os.listdir(UPLOAD_FOLDER):
                image = agent.uploadImage(os.path.join(UPLOAD_FOLDER, f))
                mediaList.append(image)
            # 投稿
            if len(mediaList) == 0:
                record = {"text": postText}
            else:
                embed = {"$type": "app.bsky.embed.images#main", "images": mediaList}
                record = {"text": postText, "embed": embed}
            agent.post(record)
        except Exception as e:
            resultText = resultText + ('' if resultText=='' else '\n') + '<b>Bluesky[ERROR]</b>' + str(e)
            pass
        else:
            resultText = resultText + ('' if resultText=='' else '\n') + '<b>Bluesky:</b>OK'

    return resultText
