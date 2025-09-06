import os
from flask import Flask, request, jsonify, Response
from pymongo import MongoClient
from dotenv import load_dotenv
import json

# 環境変数を読み込む（ローカル開発用）
load_dotenv()

app = Flask(__name__)

# --- データベース接続設定 ---
try:
    MONGO_URI = os.getenv("MONGO_URI")
    client = MongoClient(MONGO_URI)
    db = client['file_editor_db']
    files_collection = db['files']
    print("MongoDBへの接続に成功しました！")
except Exception as e:
    print(f"MongoDBへの接続に失敗しました: {e}")
    files_collection = None # 接続失敗時はNoneにしておく

# --- HTMLテンプレート（文字列として埋め込む） ---
INDEX_HTML = """
<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>ホームページ - pokemoguプロジェクト</title>
    <link rel="apple-touch-icon" sizes="180x180" href="https://kakaomames.github.io/Minecraft-flask-app/static/apple-touch-icon.png">
<link rel="icon" type="image/png" sizes="32x32" href="https://kakaomames.github.io/Minecraft-flask-app/static/favicon-32x32.png">
<link rel="icon" type="image/png" sizes="16x16" href="https://kakaomames.github.io/Minecraft-flask-app/static/favicon-16x16.png">
<link rel="manifest" href="https://kakaomames.github.io/Minecraft-flask-app/static/site.webmanifest">
    <link rel="stylesheet" href="https://kakaomames.github.io/Minecraft-flask-app/static/style.css">
</head>
<body>
    <header>
        <h1>HOME🏠</h1>
        <nav>
            <ul>
                <li><a href="/home">ホーム</a></li>
            </ul>
        </nav>
    </header>
    <main>
    </main>
    <footer>
        <p>&copy; 2025  pokemoguプロジェクト</p>
    </footer>
</body>
</html>
"""

HOME_HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>ホーム</title>
</head>
<body>
    <h1>ファイル一覧</h1>
    <a href="/editor">新規作成</a><br>
    <a href="/upload">ファイルアップロード</a>
    <hr>
    <h3>既存のファイル</h3>
    <ul id="file-list">
        </ul>
    <script>
        document.addEventListener('DOMContentLoaded', () => {
            fetch('/list')
                .then(response => response.json())
                .then(data => {
                    const fileList = document.getElementById('file-list');
                    if (data.length === 0) {
                        fileList.innerHTML = '<li>ファイルはありません。</li>';
                        return;
                    }
                    data.forEach(file => {
                        const li = document.createElement('li');
                        li.innerHTML = `
                            ${file.file_name} 
                            <a href="/editor?name=${encodeURIComponent(file.file_name)}">編集</a> | 
                            <a href="/dl?name=${encodeURIComponent(file.file_name)}">ダウンロード</a> | 
                            <button onclick="deleteFile('${file.file_name}')">削除</button>
                        `;
                        fileList.appendChild(li);
                    });
                });
        });

        function deleteFile(fileName) {
            if (confirm(`本当に '${fileName}' を削除しますか？`)) {
                fetch('/delete', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ fileName: fileName })
                }).then(response => response.json())
                .then(data => {
                    alert(data.message);
                    location.reload(); // ページをリロードしてリストを更新
                });
            }
        }
    </script>
</body>
</html>
"""

EDITOR_HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>ファイルエディタ</title>
</head>
<body>
    <h1>ファイルエディタ</h1>
    <form id="editor-form">
        <input type="text" id="fileNameInput" name="fileName" placeholder="ファイル名" required><br>
        <textarea id="contentInput" name="content" rows="15" cols="80" placeholder="ここに内容を入力..."></textarea><br>
        <button type="submit">保存</button>
    </form>
    <script>
        document.addEventListener('DOMContentLoaded', () => {
            const params = new URLSearchParams(window.location.search);
            const fileName = params.get('name');
            if (fileName) {
                document.getElementById('fileNameInput').value = fileName;
                fetch(`/get_content?name=${encodeURIComponent(fileName)}`)
                    .then(response => response.json())
                    .then(data => {
                        document.getElementById('contentInput').value = data.content;
                    });
            }
        });

        document.getElementById('editor-form').addEventListener('submit', (e) => {
            e.preventDefault();
            const fileName = document.getElementById('fileNameInput').value;
            const content = document.getElementById('contentInput').value;
            
            fetch('/save', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ fileName, content })
            }).then(response => response.json())
            .then(data => {
                alert(data.message);
            });
        });
    </script>
</body>
</html>
"""
# --- ルートの定義 ---

# トップページ
@app.route('/')
def index():
    return INDEX_HTML

# ホームページ
@app.route('/home')
def home():
    return HOME_HTML

# ファイルリストをJSONで返すAPI
@app.route('/list')
def list_files():
    if files_collection is None:
        return jsonify([])
    files = list(files_collection.find({}, {"file_name": 1, "_id": 0}))
    return jsonify(files)

# エディタページ
@app.route('/editor')
def editor():
    return EDITOR_HTML

# ファイルの内容を取得するAPI
@app.route('/get_content')
def get_content():
    file_name = request.args.get('name')
    if files_collection is None:
        return jsonify({"error": "データベースに接続できません"}), 500
    file_doc = files_collection.find_one({"file_name": file_name})
    if file_doc:
        return jsonify({"content": file_doc.get("content", "")})
    return jsonify({"content": ""})

# ファイルを保存するAPI
@app.route('/save', methods=['POST'])
def save_file():
    if files_collection is None:
        return jsonify({"error": "データベースに接続できません"}), 500
    data = request.get_json()
    file_name = data.get('fileName')
    content = data.get('content')
    if not file_name or content is None:
        return jsonify({"error": "ファイル名と内容が必要です"}), 400
    files_collection.update_one(
        {"file_name": file_name},
        {"$set": {"content": content}},
        upsert=True
    )
    return jsonify({"message": f"ファイル '{file_name}' を保存しました"}), 200

# ファイルを削除するAPI
@app.route('/delete', methods=['POST'])
def delete_file():
    if files_collection is None:
        return jsonify({"error": "データベースに接続できません"}), 500
    data = request.get_json()
    file_name = data.get('fileName')
    if not file_name:
        return jsonify({"error": "ファイル名が必要です"}), 400
    result = files_collection.delete_one({"file_name": file_name})
    if result.deleted_count == 1:
        return jsonify({"message": f"ファイル '{file_name}' を削除しました"})
    return jsonify({"message": f"ファイル '{file_name}' が見つかりませんでした"}), 404

# ファイルをダウンロードするAPI
@app.route('/dl', methods=['GET', 'POST'])
def download_file():
    if request.method == 'GET':
        html_string = """
        <!DOCTYPE html>
        <html>
        <head>
            <title>ファイルダウンロード</title>
        </head>
        <body>
            <h1>ファイルダウンロード</h1>
            <p>ファイル名を入力してダウンロードボタンを押してください。</p>
            <form action="/dl" method="post">
                <input type="text" name="fileName" placeholder="ファイル名" required><br>
                <button type="submit">ダウンロード</button>
            </form>
        </body>
        </html>
        """
        return html_string
    
    elif request.method == 'POST':
        if files_collection is None:
            return jsonify({"error": "データベースに接続できません"}), 500
        file_name = request.form.get('fileName')
        file_doc = files_collection.find_one({"file_name": file_name})
        if file_doc:
            content = file_doc.get("content", "")
            return Response(
                content,
                mimetype="text/plain",
                headers={"Content-Disposition": f"attachment;filename={file_name}"}
            )
        return "ファイルが見つかりませんでした。", 404

# ファイルをアップロードするAPI
@app.route('/upload', methods=['GET', 'POST'])
def upload_file():
    if request.method == 'GET':
        html_string = """
        <!DOCTYPE html>
        <html>
        <head>
            <title>ファイルアップロード</title>
        </head>
        <body>
            <h1>ファイルアップロード</h1>
            <p>テキストファイルをアップロードしてください。</p>
            <form action="/upload" method="post" enctype="multipart/form-data">
                <input type="file" name="file" required>
                <button type="submit">アップロード</button>
            </form>
        </body>
        </html>
        """
        return html_string
    
    elif request.method == 'POST':
        if files_collection is None:
            return jsonify({"error": "データベースに接続できません"}), 500
        if 'file' not in request.files:
            return "ファイルがありません。", 400
        file = request.files['file']
        if file.filename == '':
            return "ファイルが選択されていません。", 400
        
        content = file.read().decode('utf-8')
        file_name = file.filename
        
        files_collection.update_one(
            {"file_name": file_name},
            {"$set": {"content": content}},
            upsert=True
        )
        return "ファイルのアップロードに成功しました！"

if __name__ == '__main__':
    app.run(debug=True)
