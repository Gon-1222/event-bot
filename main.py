import json
import os
import random
import secrets
import uuid
from urllib.request import urlopen
from urllib.parse import urlparse

from flask import Flask, jsonify, request, send_from_directory,render_template
from vercel.blob import sync as blob_sdk

class BlobClient:
    put = staticmethod(blob_sdk.put_blob)
    delete = staticmethod(blob_sdk.delete_blob)
from discord_webhook import DiscordWebhook

app = Flask(__name__, template_folder=".")
app.config["MAX_CONTENT_LENGTH"] = 16384
blob_client = BlobClient()


@app.route("/", methods=["GET"])
@app.route("/form.html", methods=["GET"])
def form():
    return render_template("form.html", events=get_all_events(), admin_base="/" + ADMIN_PATH)
#submit後ページ

def save_event(event_content, name):
    event = {
        "id": str(uuid.uuid4()),
        "event": event_content,
        "name": name,
    }

    result = blob_client.put(
        f"events/{event['id']}.json",
        json.dumps(event, ensure_ascii=False).encode("utf-8"),
        access="public",
        content_type="application/json",
    )

    return event, result

def take_random_event():
    blobs = list_blobs("events/")

    if not blobs:
        return None, None

    selected_blob = random.choice(blobs)

    with urlopen(selected_blob.url) as response:
        event = json.loads(response.read().decode("utf-8"))

    return event, selected_blob


@app.route("/submit", methods=["POST"])
def submit():
    event_content = request.form.get("event_content", "").strip()

    if not event_content or len(event_content) > 1000:
        return jsonify({
            "error": "イベント内容を入力してください"
        }), 400

    name = request.form.get("name", "").strip()
    if not 1 <= len(name) <= 100:
        return jsonify({"error": "名前は1〜100文字で入力してください"}), 400

    event, _ = save_event(event_content, name)

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


@app.route("/send_random_event_to_discord", methods=["GET", "POST"])
def send_random_event_to_discord():
    if not bot_enabled():
        return jsonify({"status": "disabled", "message": "BOTはOFFです"})
    return execute_discord()

def execute_discord():
    if not os.environ.get("DISCORD_WEBHOOK_URL"):
        return jsonify({"error": "DISCORD_WEBHOOK_URLが設定されていません"}), 503
    event, selected_blob = take_random_event()

    if event is None:
        return jsonify({"error": "登録されているイベントがありません"}), 404

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
            f"提案者：{event.get('name') or '未登録'}\n"
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
    blobs = list_blobs("events/")

    events = []
    for blob in blobs:
        with urlopen(blob.url) as response:
            event = json.loads(response.read().decode("utf-8"))
            events.append(event)

    return events


def list_blobs(prefix):
    return list(blob_sdk.query_blobs(prefix=prefix))


def bot_enabled():
    return not bool(list_blobs("bot-control/disabled/"))


def find_event(event_id):
    for blob in list_blobs("events/"):
        with urlopen(blob.url, timeout=15) as response:
            event = json.loads(response.read().decode("utf-8"))
        if event.get("id") == event_id:
            return event, blob
    return None, None


ADMIN_PATH = os.getenv("ADMIN_PATH", "manage-events-7f2c9a").strip("/")
if not ADMIN_PATH or "/" in ADMIN_PATH:
    raise ValueError("ADMIN_PATHには空でない単一のパス名を指定してください")


@app.before_request
def require_admin_auth():
    if request.path == "/" + ADMIN_PATH or request.path.startswith("/" + ADMIN_PATH + "/"):
        username = os.getenv("ADMIN_USERNAME", "")
        password = os.getenv("ADMIN_PASSWORD", "")
        if not username or not password:
            return jsonify({"error": "管理者認証が未設定です。ADMIN_USERNAMEとADMIN_PASSWORDを設定してください"}), 503
        auth = request.authorization
        if (not auth or auth.type.lower() != "basic"
                or not secrets.compare_digest((auth.username or "").encode(), username.encode())
                or not secrets.compare_digest((auth.password or "").encode(), password.encode())):
            return app.response_class("認証が必要です", 401, {"WWW-Authenticate": 'Basic realm="Event Bot Admin", charset="UTF-8"', "Cache-Control": "no-store"})


@app.before_request
def protect_admin_mutations():
    if request.path.startswith("/" + ADMIN_PATH + "/api/") and request.method in ("POST", "PUT", "DELETE"):
        if request.headers.get("X-Admin-Request") != "1":
            return jsonify({"error": "管理画面から操作してください"}), 403
        origin = request.headers.get("Origin")
        if origin and urlparse(origin).netloc != request.host:
            return jsonify({"error": "アクセス元が異なります"}), 403


@app.after_request
def no_cache_admin(response):
    if request.path.startswith("/" + ADMIN_PATH):
        response.headers["Cache-Control"] = "no-store"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["X-Robots-Tag"] = "noindex, nofollow"
    return response


@app.get("/" + ADMIN_PATH)
def admin_page():
    return render_template("admin.html", admin_base="/" + ADMIN_PATH)


@app.get("/" + ADMIN_PATH + "/api/state")
def admin_state():
    return jsonify({"enabled": bot_enabled(), "events": get_all_events(), "webhook_configured": bool(os.getenv("DISCORD_WEBHOOK_URL"))})


@app.post("/" + ADMIN_PATH + "/api/toggle")
def admin_toggle():
    data = request.get_json(silent=True) or {}
    if not isinstance(data.get("enabled"), bool):
        return jsonify({"error": "enabledは真偽値で指定してください"}), 400
    if data["enabled"]:
        for blob in list_blobs("bot-control/disabled/"):
            blob_client.delete(blob.url)
    elif bot_enabled():
        blob_client.put("bot-control/disabled/" + str(uuid.uuid4()) + ".json", b'{"disabled":true}', access="public", content_type="application/json")
    return jsonify({"enabled": bot_enabled()})


@app.post("/" + ADMIN_PATH + "/api/run")
def admin_run():
    return execute_discord()


@app.route("/" + ADMIN_PATH + "/api/events", methods=["POST"])
@app.route("/" + ADMIN_PATH + "/api/events/<event_id>", methods=["PUT", "DELETE"])
def admin_events(event_id=None):
    old_blob = None
    if event_id:
        old_event, old_blob = find_event(event_id)
        if old_event is None:
            return jsonify({"error": "イベントが見つかりません。再読み込みしてください"}), 404
    if request.method == "DELETE":
        blob_client.delete(old_blob.url)
        return jsonify({"status": "deleted"})
    data = request.get_json(silent=True) or {}
    content = data.get("event", "")
    if not isinstance(content, str) or not 1 <= len(content.strip()) <= 1000:
        return jsonify({"error": "イベント内容は1〜1000文字で入力してください"}), 400
    name = data.get("name", old_event.get("name", "") if old_blob else "")
    if not isinstance(name, str) or len(name.strip()) > 100 or (not old_blob and not name.strip()):
        return jsonify({"error": "名前は1〜100文字で入力してください"}), 400
    if old_blob:
        event = {**old_event, "id": event_id, "event": content.strip(), "name": name.strip()}
        blob_client.put("events/" + str(uuid.uuid4()) + ".json", json.dumps(event, ensure_ascii=False).encode("utf-8"), access="public", content_type="application/json")
        blob_client.delete(old_blob.url)
    else:
        event, _ = save_event(content.strip(), name.strip())
    return jsonify(event), 200 if old_blob else 201


if __name__ == "__main__":
    app.run(host=os.getenv("HOST", "127.0.0.1"), port=int(os.getenv("PORT", "5000")))