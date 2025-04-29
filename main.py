from flask import Flask, render_template, request, jsonify, session, redirect, url_for
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3
from functools import wraps

app = Flask(__name__)
app.secret_key = 'secret-key'  # مفتاح سري لتشفير الجلسات
ADMIN_PASSWORD = 'admin123'  # كلمة مرور المدير

# ديكور: حماية تسجيل دخول المستخدم
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'username' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

# إعداد قاعدة البيانات
def init_db():
    conn = sqlite3.connect('appointments.db')
    c = conn.cursor()

    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE,
            password TEXT
        )
    ''')

    c.execute('''
        CREATE TABLE IF NOT EXISTS appointments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            car_type TEXT,
            appointment_time TEXT,
            status TEXT
        )
    ''')

    c.execute('''
        CREATE TABLE IF NOT EXISTS notifications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_name TEXT,
            message TEXT,
            is_read INTEGER DEFAULT 0
        )
    ''')

    conn.commit()
    conn.close()

init_db()

# الصفحة الرئيسية
@app.route('/')
def home():
    return render_template('index.html')

# تسجيل دخول المستخدم
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
        else:
            return 'فشل في تسجيل الدخول'

    return render_template('login.html')

# تسجيل الخروج للمستخدم
@app.route('/logout')
def logout():
    session.pop('username', None)
    return redirect(url_for('login'))

# صفحة تسجيل مستخدم جديد
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

# حجز موعد (يتطلب تسجيل دخول)
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

    return jsonify({'message': 'تم تقديم الحجز بنجاح. في انتظار موافقة صاحب الكراج.'})

# تسجيل دخول الإدمن
@app.route('/admin_login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        password = request.form['password']
        if password == ADMIN_PASSWORD:
            session['is_admin'] = True
            return redirect(url_for('admin'))
        else:
            return 'كلمة المرور خاطئة!'
    return render_template('admin_login.html')

# تسجيل خروج الإدمن
@app.route('/admin_logout')
def admin_logout():
    session.pop('is_admin', None)
    return redirect(url_for('admin_login'))

# لوحة تحكم الإدمن (يتطلب كلمة مرور الإدمن)
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

        message_text = 'تم قبول حجزك ✅' if status == 'approved' else 'تم رفض حجزك ❌'
        c.execute('INSERT INTO notifications (user_name, message) VALUES (?, ?)', (user_name, message_text))

        conn.commit()
        conn.close()
        return jsonify({'success': True})

    c.execute('SELECT * FROM appointments WHERE status = "pending"')
    appointments = c.fetchall()
    conn.close()
    return render_template('admin.html', appointments=appointments)

# صفحة الحالة (للمستخدم المسجل فقط)
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

# حذف رسالة
@app.route('/delete_message', methods=['POST'])
@login_required
def delete_message():
    message = request.json.get('message')
    name = session['username']

    conn = sqlite3.connect('appointments.db')
    c = conn.cursor()
    c.execute('DELETE FROM notifications WHERE user_name = ? AND message = ?', (name, message))
    conn.commit()
    conn.close()

    return jsonify({'success': True})

# حذف موعد
@app.route('/delete_appointment', methods=['POST'])
@login_required
def delete_appointment():
    data = request.get_json()
    appointment_id = data['appointment_id']

    conn = sqlite3.connect('appointments.db')
    c = conn.cursor()
    c.execute('DELETE FROM appointments WHERE id = ?', (appointment_id,))
    conn.commit()
    conn.close()

    return jsonify({'success': True})

# صفحة التحقق من الحالة
@app.route('/check_status')
@login_required
def check_status():
    return render_template('check_status.html')

if __name__ == '__main__':
    app.run(debug=True)
