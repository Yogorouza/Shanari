# Shanari

Twitter, Misskey, Blueskyにクロスポストを行うアプリケーション

## 必要なもの

- Python 3.10 もしくは Google App Engine

## 使うサービスに応じて用意するもの

- TwitterのConsumer KeysとAuthentication Tokens(FreeでOK)
- Misskeyのアクセストークン
- BlueskyのIDとパスワード
- Google Places API(New)のAPI Key

## Google App Engineで動作させる場合

1. 任意の場所にリポジトリをクローン
```
git clone https://github.com/Yogorouza/Shanari.git
cd Shanari
```

2. 環境変数を記入  
`app.yaml.sample`を`app.yaml`にリネームして記載されている各設定値をご自身の環境に基づいて記入してください。  
使用しないSNSの設定は空欄のままでOKです。(投稿時にそのSNSをOFFにしてください)

3. プロジェクトにデプロイ
```
gcloud app deploy
```

## GAE以外のセットアップ手順

1. リポジトリをクローン
```
git clone https://github.com/Yogorouza/Shanari.git
```

2. 仮想環境を作成しアクティベート
```
cd Shanari
python3 -m venv .venv
source .venv/bin/activate
```

3. 仮想環境に必要なパッケージをインストール
```
pip install -r requirements.txt
```

4. 環境変数を記入  
`mysettings`に記載されている各設定値をご自身の環境に基づいて記入してください。  
使用しないSNSの設定は空欄のままでOKです。(投稿時にそのSNSをOFFにしてください)
```
#FLASKアプリケーション定義
export FLASK_APP=shanari.webapp

#認証関連(いい感じに変更して使ってください)
export FLASK_SECRET_KEY='ac6adf3964047db6'
export FLASK_LOGIN_ID='user'
export FLASK_LOGIN_PASSWORD='pass'

#Twitter
export FLASK_TWITTER_BEARAR_TOKEN=''
export FLASK_TWITTER_CONSUMER_KEY=''
export FLASK_TWITTER_CONSUMER_SECRET=''
export FLASK_TWITTER_ACCESS_TOKEN_KEY=''
export FLASK_TWITTER_ACCESS_TOKEN_SECRET=''

#Misskey
export FLASK_MISSKEY_HOST='misskey.io'
export FLASK_MISSKEY_TOKEN=''

#Bluesky
export FLASK_BLUESKY_AGENT='https://bsky.social'
export FLASK_BLUESKY_ID='xxxxxx.bsky.social'
export FLASK_BLUESKY_PASS=''
export FLASK_BLUESKY_MAX_FILE_SIZE=1000000

#Google Places API
export FLASK_GOOGLE_PLACES_API_KEY=''
```

5. 環境変数を仮想環境に反映
```
source mysettings
```

6. アプリケーションを実行
```
flask run
```
もしくは  
```
gunicorn --workers 5 --bind 0.0.0.0:5002 shanari.webapp:app
```
みたいな感じで、パラメータはお好みで。  
実運用に際しては下記みたくなるはず、です。  
```
gunicorn --workers 5 --bind 0.0.0.0:443 shanari.webapp:app --certfile fullchain.pem --keyfile privkey.pem
```

## 使用方法
とりあえず見たままです。  
- SNS名をタップして投稿のON/OFFを切り替え  
- 画像追加ボタンをタップして添付画像を選択(4枚まで,PCブラウザではドラッグドロップとクリップボード貼り付けが動くかも)  
- プレビュー画像をタップして添付画像を初期化  
- テキストエリアに投稿内容を記述(各SNSの最大文字数は考慮せずそのまま流します)  
- POSTをタップして投稿(投稿が終わると結果がボタンの下に表示されるかも)  
- CLEARをタップして画面を初期化  
- ピンボタンをタップして近所の施設を左スワイプで投稿欄に施設情報が編集されるので必要に応じてテキストや画像を追加して投稿
- 要件を満たしていればiOSでホーム画面に追加するとPWAぽく動作する(ようです)  
- 同じく要件を満たしていればPC版chromeでアプリショートカット化が出来る(ようです)   
- 概ねこんな感じの見た目です   
![image](https://github.com/Yogorouza/Shanari/assets/31218595/8b11df11-e5bf-4057-a432-f2e2565d2a0f)
![image](https://github.com/Yogorouza/Shanari/assets/31218595/54aa60fd-7d9c-4ca8-a5c1-8661ce6f3b2f)

## 注意点
- iOSのPWAでピンボタンをタップしても何も起きない≒位置情報アラートが開かない場合はそのままSafariを開くとSafari側でアラートが表示されることがあるっぽい
- もしくはSafariの位置情報設定を触ってみる
- 如何ともしがたい場合は「設定」->「一般」->「リセット」->「位置情報とプライバシーをリセット」とかすると位置情報ダイアログが表示されるようになる(と思う)ので許可を選択(リセット操作なのでくれぐれも自己責任で…)
- 素人の仕事ですので拙い点はご容赦を
- (念のため)Twitterについては利用者本人がセットアップしたAPIを同じく本人が立てたサーバで本人が使っているので大丈夫だとは思いますが今のTwitterでは何が起きるか分かりませんので各自の判断に基づいて利用してください

## 作者
Bluesky: @yunoji.bsky.social  
Twitter: @Yunoji  
.NET開発者、芸歴20余年で今時のオープンソース開発の知識が乏し過ぎることに今さら気付いて手を動かしてみたらしい。  

## License
Almost of this software is released under the MIT License, see LICENSE file in this package.  
