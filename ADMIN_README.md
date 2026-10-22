# Web管理画面

既存のVercelプロジェクトに、このフォルダのファイルを再デプロイしてください。
管理画面: https://あなたのドメイン/manage-events-7f2c9a
パスワードは不要です。環境変数 ADMIN_PATH を設定するとパスを変更できます（例：my-event-control-長いランダム文字列）。先頭の / は不要です。管理画面のURLを知っている人は操作できます。公開フォームには管理画面へのリンクを設けていません。

必要な環境変数:
- BLOB_READ_WRITE_TOKEN : 既存のVercel Blobトークン
- DISCORD_WEBHOOK_URL : 既存のDiscord Webhook
- ADMIN_PATH : 任意、管理パス名

ON/OFF状態はVercel Blobに保存され、再起動後も維持されます。初期状態はONです。OFF時は /send_random_event_to_discord からの実行を停止します。GETとPOSTの両方に対応しています。外部スケジューラーはこのURLを週1回呼び出してください。ONにするだけでスケジューラーが作成されるわけではありません。管理画面の手動実行はOFF中も可能で、クリックごとに1件送信します。

イベントの追加・修正・削除は既存のBlobストアに反映されます。Discordへの送信成功後にイベントを削除します。Blobへの修正は新しいオブジェクトを保存して古いオブジェクトを削除するため、複数管理者の同時編集や送信の同時実行は避けてください。Discord送信とBlob削除は一括トランザクションではないため、通信障害時はDiscordを確認してから再実行してください。既存の /get_random_event は取得時にイベントを削除する仕様を維持しています。

ローカル起動: Python 3.10以降で pip install -r requirements.txt の後、環境変数を設定して python main.py。http://localhost:5000/manage-events-7f2c9a からアクセスできます。本番はVercelのHTTPSで公開してください。

本変更はファイル作成までで、既存の公開サイトへのデプロイや実際のDiscord投稿は実施していません。

## Basic認証（追加）
管理画面とその配下の管理APIにはBasic認証が必要です。Vercelの環境変数に ADMIN_USERNAME と ADMIN_PASSWORD を設定して再デプロイしてください。未設定の場合は管理画面を503で閉じます。登録フォームは認証不要です。管理画面へのリンクは登録フォーム右上にあります。Basic認証は必ずHTTPS環境で使用してください。パスワード不要という前述の説明は、この追加仕様で置き換えます。
