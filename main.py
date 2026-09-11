import json
import os
import random
import uuid
from urllib.request import urlopen

from flask import Flask, jsonify, request, send_from_directory
from vercel.blob import BlobClient
from discord_webhook import DiscordWebhook

app = Flask(__name__)
blob_client = BlobClient()


@app.route("/form.html", methods=["GET"])
def form():
    return send_from_directory(".", "form.html")


def save_event(event_content):
    event = {
        "id": str(uuid.uuid4()),
        "event": event_content,
    }

    result = blob_client.put(
        f"events/{event['id']}.json",
        json.dumps(event, ensure_ascii=False).encode("utf-8"),
        access="public",
        content_type="application/json",
    )

    return event, result


def take_random_event():
    result = blob_client.list(prefix="events/")
    blobs = result.blobs

    if not blobs:
        return None, None

    selected_blob = random.choice(blobs)

    with urlopen(selected_blob.url) as response:
        event = json.loads(response.read().decode("utf-8"))

    return event, selected_blob


@app.route("/submit", methods=["POST"])
def submit():
    event_content = request.form.get("event_content", "").strip()

    if not event_content:
        return jsonify({
            "error": "イベント内容を入力してください"
        }), 400

    event, _ = save_event(event_content)

    return jsonify({
        "message": "イベントを登録しました",
        **event,
    })


@app.route("/get_random_event", methods=["GET"])
def get_random_event():
    event, selected_blob = take_random_event()

    if event is None:
        return jsonify({
            "error": "登録されているイベントがありません"
        }), 404

    # 取得と同時に削除する場合
    blob_client.delete(selected_blob.url)

    return jsonify(event)


@app.route("/send_random_event_to_discord", methods=["POST"])
def send_random_event_to_discord():
    event, selected_blob = take_random_event()

    if event is None:
        return jsonify({
            "error": "登録されているイベントがありません"
        }), 404

    webhook_url = os.environ.get("DISCORD_WEBHOOK_URL")

    if not webhook_url:
        return jsonify({
            "error": "DISCORD_WEBHOOK_URLが設定されていません"
        }), 500

    webhook = DiscordWebhook(
        url=webhook_url,
        content=(
            f"今週のイベントは「{event['event']}」です！\n\n"
            "イベントの追加はこちら！↓\n"
            "https://event-bot-ten.vercel.app/form.html"
        ),
    )

    response = webhook.execute()

    if response.status_code not in (200, 204):
        return jsonify({
            "error": "Discordへの送信に失敗しました"
        }), 500

    # Discordへの送信が成功した場合だけ削除
    blob_client.delete(selected_blob.url)

    return jsonify(event)


if __name__ == "__main__":
    app.run(debug=True)