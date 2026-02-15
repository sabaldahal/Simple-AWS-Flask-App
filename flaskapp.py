from flask import Flask, render_template, request, redirect, url_for, send_from_directory, session
from flask import jsonify
import os
import sqlite3
from contextlib import contextmanager


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_NAME = os.path.join(BASE_DIR, 'mydatabase.db')




@contextmanager
def get_connection():
    conn = None
    try:
        conn = sqlite3.connect(DB_NAME)
        conn.row_factory = sqlite3.Row
        yield conn
    except Exception as e:
        if conn:
            conn.rollback()
        raise e
    finally:
        if conn:
            conn.close()

def init_db():
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS users 
            (id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT NOT NULL UNIQUE,
                    password TEXT NOT NULL,
                    email TEXT NOT NULL,
                first_name TEXT NOT NULL,
                last_name TEXT NOT NULL,
            address TEXT NOT NULL,
            is_admin INTEGER DEFAULT 0
            )""")
        
        cur.execute("""
            CREATE TABLE IF NOT EXISTS limericks
            (id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL REFERENCES users(id),
            filename TEXT NOT NULL)
            """)
        conn.commit()

init_db()

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = os.path.join(BASE_DIR, 'uploads')
app.secret_key = 'someprivatekey'



def count_words(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        text = f.read()
    return len(text.split())

@app.route('/check_username')
def check_username():
    username = request.args.get('username', '').strip()

    if not username:
        return jsonify({"available": False, "message": "Username is required."})

    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("SELECT 1 FROM users WHERE username = ?", (username,))
        row = cur.fetchone()

    if row:
        return jsonify({"available": False, "message": "Username already exists."})
    else:
        return jsonify({"available": True, "message": "Username is available."})



@app.route('/', methods=['GET', 'POST'])
@app.route('/register', methods=['GET', 'POST'])
def register():
    message = ''
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        first_name = request.form.get('first_name')
        last_name = request.form.get('last_name')
        email = request.form.get('email')
        address = request.form.get('address')


        with get_connection() as conn:
            cur = conn.cursor()
            cur.execute(
                "INSERT INTO users (username, password, email, first_name, last_name, address) VALUES (?, ?, ?, ?, ?, ?)",
                (username, password, email, first_name, last_name, address)
            )
            conn.commit()
        

            # 4e: handle file upload (Limerick.txt)
            uploaded = request.files.get('limerick')
            if uploaded and uploaded.filename:
                # save file
                os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
                newfilename = f'{username}'
                filepath = os.path.join(app.config['UPLOAD_FOLDER'], newfilename)
                uploaded.save(filepath)

                cur.execute(
                    "INSERT INTO limericks (user_id, filename) VALUES (?, ?)",
                    (cur.lastrowid, newfilename)
                )
            conn.commit()


        session['username'] = username
        return redirect(url_for('details'))
    session.pop('username', None)
    return render_template('register.html')


@app.route('/details', methods=['GET', 'POST'])
def details():
    username = session.get('username')
    user_details = None
    if not username:
        return redirect(url_for('login'))
    
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("SELECT id, first_name, last_name, email, address FROM users WHERE username = ?", (username,))
        row = cur.fetchone()
    
        if row:
            user_details = {
                "first_name": row["first_name"],
                "last_name": row["last_name"],
                "email": row["email"],
                "address": row["address"]
            }
    
      
        if request.method == 'POST':
            uploaded = request.files.get('limerick')

            if uploaded and uploaded.filename:
                os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
                newfilename = f'{username}'
                filepath = os.path.join(app.config['UPLOAD_FOLDER'], newfilename)
                uploaded.save(filepath)
                cur.execute(
                    "INSERT INTO limericks (user_id, filename) VALUES (?, ?)",
                    (row["id"], newfilename)
                )
                conn.commit()

        cur.execute("SELECT filename FROM limericks WHERE user_id = ?", (row["id"],))
        limerick_row = cur.fetchone()
        file_info = {
            "filename": limerick_row["filename"] if limerick_row else None,
            "word_count": count_words(os.path.join(app.config['UPLOAD_FOLDER'], limerick_row["filename"])) if limerick_row else 0
        }


    return render_template('details.html',
                           details=user_details,
                           file_info=file_info)


@app.route('/download_limerick/<filename>')
def download_limerick(filename):
    if filename is None:
        return "No file uploaded yet.", 400
    return send_from_directory(app.config['UPLOAD_FOLDER'],
                               filename,
                               as_attachment=True)


@app.route('/login', methods=['GET', 'POST'])
def login():
    message = ''
    user_data = None

    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        with get_connection() as conn:
            cur = conn.cursor()
            cur.execute("""
                SELECT first_name, last_name, email, address
                FROM users
                WHERE username = ? AND password = ?
            """, (username, password))
            row = cur.fetchone()


        if row is None:
            message = 'Invalid username or password'
            return render_template('login.html', message=message)
        else:
            session['username'] = username
            return redirect(url_for('details'))
    session.pop('username', None) 
    return render_template('login.html',
                           message=message,
                           user=user_data)


@app.route('/admin', methods=['GET', 'POST'])
def admin():
    message = ''
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        with get_connection() as conn:
            cur = conn.cursor()
            cur.execute("""
                SELECT username
                FROM users
                WHERE username = ? AND password = ? AND is_admin = 1
            """, (username, password))
            row = cur.fetchone()

        if row is None:
            message = 'Invalid admin credentials'
            return render_template('admin_login.html', message=message)
        else:
            session['admin'] = True
            return redirect(url_for('admin_dashboard'))

    session.pop('admin', None)
    return render_template('admin_login.html', message=message)

@app.route('/admin_dash')
def admin_dashboard():
    if not session.get('admin'):
        return redirect(url_for('admin'))

    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("""
            SELECT id, username, email, first_name, last_name, address
            FROM users
            ORDER BY id
        """)
        rows = cur.fetchall()

    return render_template('admin_dashboard.html', users=rows)

@app.route('/logout')
def logout():
    session.pop('username', None)
    session.pop('admin', None)
    return redirect(url_for('admin'))

if __name__ == '__main__':
    app.run(debug=True)
