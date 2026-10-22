from pathlib import Path
p=Path('main.py');s=p.read_text(encoding='utf-8');s=s.replace('import random','import random\nimport secrets',1);s=s.replace('render_template("form.html", events=get_all_events())','render_template("form.html", events=get_all_events(), admin_base="/" + ADMIN_PATH)');needle='@app.before_request\ndef protect_admin_mutations():';addition='''@app.before_request
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


''';s=s.replace(needle,addition+needle);p.write_text(s,encoding='utf-8')
