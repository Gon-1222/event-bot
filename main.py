import json
import os
import random
import uuid
from urllib.request import urlopen

from flask import Flask, jsonify, request, send_from_directory,render_template
from vercel.blob import BlobClient
from discord_webhook import DiscordWebhook

app = Flask(__name__, template_folder=".")
blob_client = BlobClient()


@app.route("/form.html", methods=["GET"])
def form():
    return render_template("form.html", events=get_all_events())
#submit後ページ

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
    result = blob_client.list_objects(prefix="events/")
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

    return send_from_directory(".", "success.html")


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
        webhook = DiscordWebhook(
            url=os.environ.get("DISCORD_WEBHOOK_URL"),
            content=("<@&&1444302300540834015>\n""登録されているイベントがありません"),
        )
        webhook.execute()

        return jsonify({
            "error": "登録されているイベントがありません"
        }), 404

    webhook_url = os.environ.get("DISCORD_WEBHOOK_URL")

    if not webhook_url:
        return jsonify({
            "error": "DISCORD_WEBHOOK_URLが設定されていません"
        }), 500
    responsible = random.choice([{ "名前": "宮坂", "ID": "1003641670107148348" }, { "名前": "赤井", "ID": "744467692043501579" }, { "名前": "堀口", "ID": "951295131607248926" }, { "名前": "松山", "ID": "1028669102048411728" }, { "名前": "浜中", "ID": "1227503809220182057" }, { "名前": "田中", "ID": "1226223297176272950" }, { "名前": "福島", "ID": "1444308346097107035" }, { "名前": "竹内", "ID": "1469979675542425742" }, { "名前": "茨田", "ID": "1449013383981568132" }, { "名前": "西村", "ID": "1442839010396606525" }, { "名前": "西", "ID": "1115606453705781288" }]) 
    event["responsible"] = responsible  # 担当者をイベントに追加
    webhook = DiscordWebhook(
        url=webhook_url,
        content=(
            "<@&1444302300540834015>\n"
            f"今週のイベントは「{event['event']}」です！\n"
            f"担当は<@{event['responsible']['ID']}>です。\n"
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

def get_all_events():
    result = blob_client.list_objects(prefix="events/")
    blobs = result.blobs

    events = []
    for blob in blobs:
        with urlopen(blob.url) as response:
            event = json.loads(response.read().decode("utf-8"))
            events.append(event)

    return events

if __name__ == "__main__":
    app.run(debug=True)