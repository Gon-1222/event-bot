from flask import Flask, jsonify, request, send_from_directory
from vercel.blob import BlobClient
from discord_webhook import DiscordWebhook

blob_client = BlobClient()
app = Flask(__name__)


@app.route('form.html', methods=['GET'])
def form():
    return send_from_directory('.', 'form.html')

@app.route('/submit', methods=['POST'])
def submit():
    data = request.form.to_dict()
    #入力されたイベントを文字データへ
    data['event'] = str(data['event'])
    #blobのJSONにデータを追加する
    blob_client.append_to_json(data)
    return jsonify(data)

@app.route('/get_random_event', methods=['GET'])
def get_random_event():
    #blobのJSONからランダムにイベントを取得する
    event = blob_client.get_random_json()
    #デリートする
    blob_client.delete_json(event)
    return jsonify(event)

@app.route("/send_random_event_to_discord", methods=["POST"])
def send_random_event_to_discord():
    event = get_random_event()
    # DiscordにWebhookでイベントを送信する
    webhook_url = "https://discord.com/api/webhooks/your_webhook_url"  # ここにDiscordのWebhook URLを入力してください
    webhook = DiscordWebhook(url=webhook_url, content=f"今週のイベントは「{event['event']}」です！")
    response = webhook.execute()
    if response.status_code != 200:
        return jsonify({"error": "Failed to send event to Discord"}), 500
    blob_client.delete_json(event)  # Discordに送信後、イベントを削除する
    return jsonify(event)

if __name__ == '__main__':
    app.run(debug=True)
