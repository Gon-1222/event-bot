from pathlib import Path
p=Path('main.py')
s=p.read_text(encoding='utf-8-sig')
s=s.replace('from urllib.request import urlopen','from urllib.request import urlopen\nfrom urllib.parse import urlparse')
s=s.replace('app = Flask(__name__, template_folder=".")','app = Flask(__name__, template_folder=".")\napp.config["MAX_CONTENT_LENGTH"] = 16384')
s=s.replace('    result = blob_client.list_objects(prefix="events/")\n    blobs = result.blobs','    blobs = list_blobs("events/")')
s=s.replace('    if not event_content:', '    if not event_content or len(event_content) > 1000:')
s=s.replace('@app.route("/send_random_event_to_discord", methods=["POST"])','@app.route("/send_random_event_to_discord", methods=["GET", "POST"])')
s=s.replace('def send_random_event_to_discord():\n', 'def send_random_event_to_discord():\n    if not bot_enabled():\n        return jsonify({"status": "disabled", "message": "BOTはOFFです"})\n    return execute_discord()\n\ndef execute_discord():\n    if not os.environ.get("DISCORD_WEBHOOK_URL"):\n        return jsonify({"error": "DISCORD_WEBHOOK_URLが設定されていません"}), 503\n')
start=s.index('    if event is None:',s.index('def execute_discord():'))
end=s.index('    webhook_url =',start)
s=s[:start]+'''    if event is None:
        return jsonify({"error": "登録されているイベントがありません"}), 404

'''+s[end:]
s=s.replace('    app.run(debug=True)','    app.run(host=os.getenv("HOST", "127.0.0.1"), port=int(os.getenv("PORT", "5000")))')
addition='''
def list_blobs(prefix):
    blobs, cursor = [], None
    while True:
        kwargs = {"prefix": prefix}
        if cursor:
            kwargs["cursor"] = cursor
        result = blob_client.list_objects(**kwargs)
        blobs.extend(result.blobs)
        if not getattr(result, "has_more", False):
            return blobs
        cursor = result.cursor


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
    if old_blob:
        event = {"id": event_id, "event": content.strip()}
        blob_client.put("events/" + str(uuid.uuid4()) + ".json", json.dumps(event, ensure_ascii=False).encode("utf-8"), access="public", content_type="application/json")
        blob_client.delete(old_blob.url)
    else:
        event, _ = save_event(content.strip())
    return jsonify(event), 200 if old_blob else 201

'''
s=s.replace('if __name__ == "__main__":',addition+'\nif __name__ == "__main__":')
p.write_text(s,encoding='utf-8')
