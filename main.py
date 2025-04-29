from flask import Flask, render_template, request, jsonify, session, redirect, url_for
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3
from functools import wraps

app = Flask(__name__)
app.secret_key = 'secret-key'
ADMIN_PASSWORD = 'admin123'

# حماية الصفحات التي تتطلب تسجيل دخول
def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'username' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated

# إعداد قاعدة البيانات
def init_db():
    conn = sqlite3.connect('appointments.db')
    c = conn.cursor()

    c.execute('''CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE,
        password TEXT
    )''')

    c.execute('''CREATE TABLE IF NOT EXISTS appointments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        car_type TEXT,
        appointment_time TEXT,
        status TEXT
    )''')

    c.execute('''CREATE TABLE IF NOT EXISTS notifications (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_name TEXT,
        message TEXT,
        is_read INTEGER DEFAULT 0
    )''')

    c.execute('''CREATE TABLE IF NOT EXISTS chat (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        appointment_id INTEGER,
        sender TEXT,
        message TEXT,
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(appointment_id) REFERENCES appointments(id)
    )''')

    conn.commit()
    conn.close()

init_db()

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        conn = sqlite3.connect('appointments.db')
        c = conn.cursor()
        c.execute('SELECT * FROM users WHERE username = ?', (username,))
        user = c.fetchone()
        conn.close()

        if user and check_password_hash(user[2], password):
            session['username'] = username
            return redirect(url_for('home'))
        return 'فشل في تسجيل الدخول'

    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = generate_password_hash(request.form['password'])

        conn = sqlite3.connect('appointments.db')
        c = conn.cursor()
        c.execute('INSERT INTO users (username, password) VALUES (?, ?)', (username, password))
        conn.commit()
        conn.close()

        return redirect(url_for('login'))

    return render_template('register.html')

@app.route('/logout')
def logout():
    session.pop('username', None)
    return redirect(url_for('login'))

@app.route('/book_appointment', methods=['POST'])
@login_required
def book_appointment():
    name = session['username']
    car_type = request.json.get('car_type')
    appointment_time = request.json.get('appointment_time')

    conn = sqlite3.connect('appointments.db')
    c = conn.cursor()
    c.execute('INSERT INTO appointments (name, car_type, appointment_time, status) VALUES (?, ?, ?, ?)',
              (name, car_type, appointment_time, 'pending'))
    conn.commit()
    conn.close()

    return jsonify({'message': 'تم تقديم الحجز بنجاح'})

@app.route('/admin_login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        password = request.form['password']
        if password == ADMIN_PASSWORD:
            session['is_admin'] = True
            return redirect(url_for('admin'))
        return 'كلمة المرور خاطئة'
    return render_template('admin_login.html')

@app.route('/admin_logout')
def admin_logout():
    session.pop('is_admin', None)
    return redirect(url_for('admin_login'))

@app.route('/admin', methods=['GET', 'POST'])
def admin():
    if not session.get('is_admin'):
        return redirect(url_for('admin_login'))

    conn = sqlite3.connect('appointments.db')
    c = conn.cursor()

    if request.method == 'POST':
        data = request.get_json()
        appointment_id = data['appointment_id']
        status = data['status']

        c.execute('UPDATE appointments SET status = ? WHERE id = ?', (status, appointment_id))

        c.execute('SELECT name FROM appointments WHERE id = ?', (appointment_id,))
        user_name = c.fetchone()[0]
        message = 'تم قبول حجزك ✅' if status == 'approved' else 'تم رفض حجزك ❌'
        c.execute('INSERT INTO notifications (user_name, message) VALUES (?, ?)', (user_name, message))

        conn.commit()
        conn.close()
        return jsonify({'success': True})

    c.execute('SELECT * FROM appointments WHERE status = "pending"')
    appointments = c.fetchall()
    conn.close()
    return render_template('admin.html', appointments=appointments)

@app.route('/status')
@login_required
def status():
    name = session['username']
    conn = sqlite3.connect('appointments.db')
    c = conn.cursor()

    c.execute('SELECT message FROM notifications WHERE user_name = ? AND is_read = 0', (name,))
    messages = c.fetchall()

    c.execute('UPDATE notifications SET is_read = 1 WHERE user_name = ?', (name,))
    conn.commit()
    conn.close()

    return render_template('status.html', messages=messages, name=name)

@app.route('/chat/<int:appointment_id>', methods=['GET'])
@login_required
def chat(appointment_id):
    conn = sqlite3.connect('appointments.db')
    c = conn.cursor()
    c.execute('SELECT sender, message, timestamp FROM chat WHERE appointment_id = ? ORDER BY timestamp ASC', (appointment_id,))
    messages = c.fetchall()

    c.execute('SELECT * FROM appointments WHERE id = ?', (appointment_id,))
    appointment = c.fetchone()

    conn.close()
    return render_template('chat.html', messages=messages, appointment=appointment)

@app.route('/send_message/<int:appointment_id>', methods=['POST'])
@login_required
def send_message(appointment_id):
    sender = session['username']
    message = request.json.get('message')

    conn = sqlite3.connect('appointments.db')
    c = conn.cursor()
    c.execute('INSERT INTO chat (appointment_id, sender, message) VALUES (?, ?, ?)', (appointment_id, sender, message))
    conn.commit()
    conn.close()

    return jsonify({'success': True})

@app.route('/get_messages/<int:appointment_id>', methods=['GET'])
@login_required
def get_messages(appointment_id):
    conn = sqlite3.connect('appointments.db')
    c = conn.cursor()
    c.execute('SELECT sender, message FROM chat WHERE appointment_id = ? ORDER BY timestamp ASC', (appointment_id,))
    messages = [{'sender': row[0], 'message': row[1]} for row in c.fetchall()]
    conn.close()
    return jsonify({'messages': messages})

@app.route('/my_appointments')
@login_required
def my_appointments():
    conn = sqlite3.connect('appointments.db')
    c = conn.cursor()
    c.execute('SELECT id, car_type, appointment_time, status FROM appointments WHERE name = ?', (session['username'],))
    appointments = c.fetchall()
    conn.close()
    return render_template('my_appointments.html', appointments=appointments)

@app.route('/set_username', methods=['POST'])
def set_username():
    username = request.form['username']
    session['username'] = username
    return redirect('/chat_global')

@app.route('/chat_global')
def chat_global():
    if 'username' not in session:
        return redirect('/enter_name')
    return render_template('chat_global.html')  # صفحة الدردشة

@app.route('/enter_name')
def enter_name():
    return render_template('enter_name.html')

@app.route('/send_message', methods=['POST'])
def send_message():
    sender = session.get('username', 'مستخدم مجهول')
    message = request.json.get('message')

    conn = sqlite3.connect('appointments.db')
    c = conn.cursor()
    c.execute('INSERT INTO chat (appointment_id, sender, message) VALUES (?, ?, ?)', (1, sender, message))
    conn.commit()
    conn.close()

    return jsonify({'success': True})

if __name__ == '__main__':
    app.run(debug=True)
