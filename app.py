import os
import sqlite3
import subprocess
import psutil
import math
from flask import Flask, render_template, request, jsonify, g, session, send_from_directory
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = "supersecretkey"

DB_NAME = "terminal.db"
BASE_DIR = os.path.abspath(".")
UPLOAD_FOLDER = os.path.join(BASE_DIR, "uploads")
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# ================== DATABASE ==================
def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(DB_NAME)
        g.db.row_factory = sqlite3.Row
    return g.db

@app.teardown_appcontext
def close_db(exception):
    db = g.pop("db", None)
    if db:
        db.close()

def init_db():
    db = get_db()
    db.execute("""
        CREATE TABLE IF NOT EXISTS history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            command TEXT NOT NULL,
            output TEXT NOT NULL
        )
    """)
    db.commit()

# ================== SESSION & HELPERS ==================
def get_cwd():
    if "cwd" not in session:
        session["cwd"] = BASE_DIR
    return session["cwd"]

def set_cwd(path):
    session["cwd"] = path

def run_math(command):
    try:
        allowed_names = {k: v for k, v in math.__dict__.items() if not k.startswith("__")}
        result = eval(command, {"__builtins__": {}}, allowed_names)
        return str(result)
    except Exception:
        return None

def simulate_pip(command):
    """Simulate pip install."""
    parts = command.split()
    if len(parts) >= 3 and parts[0] == "pip" and parts[1] == "install":
        packages = parts[2:]
        return f"📦 Successfully installed: {', '.join(packages)}"
    return None

# ================== COMMAND EXECUTION ==================
def run_command(cmd):
    cmd = cmd.strip()
    if not cmd:
        return ""

    parts = cmd.split()
    first = parts[0].lower()

    # ================== Built-in commands ==================
    if first == "cd":
        target = parts[1] if len(parts) > 1 else os.path.expanduser("~")
        new_path = os.path.abspath(os.path.join(get_cwd(), target))
        if os.path.isdir(new_path) and new_path.startswith(BASE_DIR):
            set_cwd(new_path)
            return f"📂 Changed directory to {new_path}"
        else:
            return f"❌ No such directory: {target}"

    elif first == "pwd":
        return get_cwd()

    elif first == "ls":
        path = get_cwd() if len(parts) == 1 else os.path.join(get_cwd(), parts[1])
        try:
            files = os.listdir(path)
            return "\n".join(files)
        except Exception as e:
            return f"⚠️ Error: {e}"

    elif first == "clear":
        return "__CLEAR__"

    elif first == "history":
        db = get_db()
        rows = db.execute("SELECT command FROM history ORDER BY id DESC LIMIT 50").fetchall()
        return "\n".join([row["command"] for row in reversed(rows)])

    # ================== File commands ==================
    elif first == "mkdir":
        try:
            path = os.path.join(get_cwd(), parts[1])
            os.makedirs(path, exist_ok=True)
            return f"📂 Directory '{parts[1]}' created successfully."
        except Exception as e:
            return f"⚠️ {e}"

    elif first in ["rmdir", "rm", "del"]:
        try:
            path = os.path.join(get_cwd(), parts[1])
            if os.path.isdir(path):
                os.rmdir(path)
                return f"🗑️ Directory '{parts[1]}' deleted successfully."
            elif os.path.isfile(path):
                os.remove(path)
                return f"🗑️ File '{parts[1]}' deleted successfully."
            else:
                return f"❌ No such file or directory: {parts[1]}"
        except Exception as e:
            return f"⚠️ {e}"

    elif first == "touch":
        try:
            path = os.path.join(get_cwd(), parts[1])
            open(path, "a").close()
            return f"📝 File '{parts[1]}' created successfully."
        except Exception as e:
            return f"⚠️ {e}"

    elif first == "cat":
        try:
            path = os.path.join(get_cwd(), parts[1])
            with open(path, "r") as f:
                return f.read()
        except Exception as e:
            return f"⚠️ {e}"

    elif first in ["mv", "cp"]:
        try:
            src = os.path.join(get_cwd(), parts[1])
            dest = os.path.join(get_cwd(), parts[2])
            if first == "mv":
                os.rename(src, dest)
                return f"📂 Moved '{parts[1]}' to '{parts[2]}'."
            else:
                import shutil
                if os.path.isdir(src):
                    shutil.copytree(src, dest)
                else:
                    shutil.copy2(src, dest)
                return f"📄 Copied '{parts[1]}' to '{parts[2]}'."
        except Exception as e:
            return f"⚠️ {e}"

    # ================== Pip simulation ==================
    pip_result = simulate_pip(cmd)
    if pip_result:
        return pip_result

    # ================== Math expressions ==================
    math_result = run_math(cmd)
    if math_result is not None:
        return f"🧮 {math_result}"

    # ================== Default shell ==================
    try:
        result = subprocess.run(cmd, shell=True, cwd=get_cwd(),
                                capture_output=True, text=True, timeout=5)
        return result.stdout.strip() or result.stderr.strip() or f"✅ Command '{cmd}' executed successfully."
    except Exception as e:
        return f"⚠️ {e}"

# ================== ROUTES ==================
@app.route("/")
def index():
    return render_template("index.html")

@app.route("/stats")
def stats():
    processes = [p.info for p in psutil.process_iter(['pid', 'name', 'cpu_percent'])][:5]
    return jsonify({
        "cpu": psutil.cpu_percent(),
        "memory": psutil.virtual_memory().percent,
        "disk": psutil.disk_usage("/").percent,
        "processes": processes
    })

@app.route("/run", methods=["POST"])
def run():
    data = request.get_json()
    command = data.get("command", "").strip()
    output = run_command(command)

    db = get_db()
    db.execute("INSERT INTO history (command, output) VALUES (?, ?)", (command, output))
    db.commit()

    return jsonify({"output": output})

@app.route("/history")
def history():
    db = get_db()
    rows = db.execute("SELECT command, output FROM history ORDER BY id DESC LIMIT 50").fetchall()
    return jsonify([dict(row) for row in rows])

# ================== File Upload/Download ==================
@app.route("/upload", methods=["POST"])
def upload():
    if 'file' not in request.files:
        return jsonify({"output": "❌ No file part"})
    file = request.files['file']
    if file.filename == '':
        return jsonify({"output": "❌ No selected file"})
    filename = secure_filename(file.filename)
    file.save(os.path.join(UPLOAD_FOLDER, filename))
    return jsonify({"output": f"📄 File '{filename}' uploaded successfully."})

@app.route("/download/<filename>")
def download(filename):
    return send_from_directory(UPLOAD_FOLDER, filename, as_attachment=True)

# ================== MAIN ==================
if __name__ == "__main__":
    with app.app_context():
        init_db()
    app.run(host="0.0.0.0", port=5050, debug=True)
