import os
import sqlite3
import subprocess
import psutil
import math
import json
import requests
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
    with app.app_context():
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

    if first == "cd":
        target = parts[1] if len(parts) > 1 else os.path.expanduser("~")
        new_path = os.path.abspath(os.path.join(get_cwd(), target))
        if os.path.isdir(new_path) and new_path.startswith(BASE_DIR):
            set_cwd(new_path)
            return f"📂 Changed directory to {new_path}"
        return f"❌ No such directory: {target}"

    elif first == "pwd":
        return get_cwd()

    elif first == "ls":
        path = get_cwd() if len(parts) == 1 else os.path.join(get_cwd(), parts[1])
        try:
            files = os.listdir(path)
            return "\n".join(files) if files else "Empty directory"
        except Exception as e:
            return f"⚠️ Error: {e}"

    elif first == "clear":
        return "__CLEAR__"

    elif first == "history":
        db = get_db()
        rows = db.execute("SELECT command FROM history ORDER BY id ASC").fetchall()
        return "\n".join([row["command"] for row in rows])

    elif first == "mkdir":
        try:
            path = os.path.join(get_cwd(), parts[1])
            os.makedirs(path, exist_ok=True)
            return f"📂 Directory '{parts[1]}' created."
        except Exception as e:
            return f"⚠️ {e}"

    elif first == "rm":
         try:
            path = os.path.join(get_cwd(), parts[1])
            if os.path.isdir(path):
                import shutil
                shutil.rmtree(path)
                return f"🗑️ Directory '{parts[1]}' deleted."
            elif os.path.isfile(path):
                os.remove(path)
                return f"🗑️ File '{parts[1]}' deleted."
            else:
                return f"❌ No such file or directory: {parts[1]}"
         except Exception as e:
            return f"⚠️ {e}"

    elif first == "touch":
        try:
            path = os.path.join(get_cwd(), parts[1])
            open(path, "a").close()
            return f"📝 File '{parts[1]}' created."
        except Exception as e:
            return f"⚠️ {e}"

    elif first == "cat":
        try:
            path = os.path.join(get_cwd(), parts[1])
            with open(path, "r") as f:
                return f.read()
        except Exception as e:
            return f"⚠️ {e}"

    elif first == "nano":
        if len(parts) > 1:
            file_path = os.path.join(get_cwd(), parts[1])
            try:
                with open(file_path, "r") as f:
                    return f.read()
            except FileNotFoundError:
                return "" # Return empty for new file
            except Exception as e:
                return f"⚠️ Error: {e}"
        return "Usage: nano <filename>"

    pip_result = simulate_pip(cmd)
    if pip_result:
        return pip_result
        
    math_result = run_math(cmd)
    if math_result is not None:
        return f"🧮 {math_result}"

    try:
        result = subprocess.run(cmd, shell=True, cwd=get_cwd(),
                                capture_output=True, text=True, timeout=10)
        return result.stdout.strip() or result.stderr.strip() or f"✅ Command '{cmd}' executed."
    except Exception as e:
        return f"⚠️ {e}"

# ================== ROUTES ==================
@app.route("/")
def index():
    return render_template("index.html")

@app.route("/run", methods=["POST"])
def run():
    data = request.get_json()
    command = data.get("command", "").strip()
    output = run_command(command)
    if command.lower() != 'history':
        db = get_db()
        db.execute("INSERT INTO history (command, output) VALUES (?, ?)", (command, output))
        db.commit()
    return jsonify({"output": output})
    
@app.route('/interpret', methods=['POST'])
def interpret_command():
    data = request.json
    natural_language_query = data.get('query')

    if not natural_language_query:
        return jsonify({'error': 'No query provided'}), 400

    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
         return jsonify({'error': 'API key not configured. Set GEMINI_API_KEY environment variable.'}), 500

    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-pro:generateContent?key={api_key}"
    
    system_prompt = (
        "You are an expert command-line terminal assistant. "
        "Your task is to translate natural language queries into a single, executable shell command for a Linux environment. "
        "Only return the shell command itself, with no explanation, decoration, or extra text. "
        "For example, if the user says 'create a file called test.txt', you should only output 'touch test.txt'."
    )
    
    payload = {
        "contents": [{"parts": [{"text": natural_language_query}]}],
        "system_instruction": {"parts": [{"text": system_prompt}]}
    }

    try:
        response = requests.post(url, json=payload, headers={'Content-Type': 'application/json'})
        response.raise_for_status()
        result = response.json()
        command = result['candidates'][0]['content']['parts'][0]['text'].strip()
        return jsonify({'command': command})
    except requests.exceptions.RequestException as e:
        return jsonify({'error': str(e)}), 500
    except (KeyError, IndexError) as e:
        return jsonify({'error': 'Failed to parse AI response'}), 500

@app.route('/save', methods=['POST'])
def save_file():
    data = request.json
    file_path = os.path.join(get_cwd(), data['filename'])
    with open(file_path, 'w') as f:
        f.write(data['content'])
    return jsonify({'output': f"File '{data['filename']}' saved."})

# ================== MAIN ==================
if __name__ == "__main__":
    init_db()
    app.run(host="0.0.0.0", port=5050, debug=True)

