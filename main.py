from flask import Flask, render_template, request, jsonify
import sqlite3

app = Flask(__name__)

# إعداد قاعدة البيانات
def init_db():
    conn = sqlite3.connect('appointments.db')
    c = conn.cursor()

    # إنشاء جدول المواعيد
    c.execute('''
        CREATE TABLE IF NOT EXISTS appointments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            car_type TEXT,
            appointment_time TEXT,
            status TEXT
        )
    ''')

    # جدول الرسائل للمستخدمين
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

# حجز موعد
@app.route('/book_appointment', methods=['POST'])
def book_appointment():
    name = request.json.get('name')
    car_type = request.json.get('car_type')
    appointment_time = request.json.get('appointment_time')

    conn = sqlite3.connect('appointments.db')
    c = conn.cursor()
    c.execute('''
        INSERT INTO appointments (name, car_type, appointment_time, status)
        VALUES (?, ?, ?, ?)
    ''', (name, car_type, appointment_time, 'pending'))
    conn.commit()
    conn.close()

    return jsonify({'message': 'تم تقديم الحجز بنجاح. في انتظار موافقة صاحب الكراج.'})

# لوحة تحكم الادمين
@app.route('/admin', methods=['GET', 'POST'])
def admin():
    conn = sqlite3.connect('appointments.db')
    c = conn.cursor()

    if request.method == 'POST':
        data = request.get_json()
        appointment_id = data['appointment_id']
        status = data['status']

        # تحديث حالة الموعد
        c.execute('''
            UPDATE appointments
            SET status = ?
            WHERE id = ?
        ''', (status, appointment_id))

        # جلب اسم المستخدم من الموعد
        c.execute('SELECT name FROM appointments WHERE id = ?', (appointment_id,))
        user_name = c.fetchone()[0]

        # إرسال إشعار للمستخدم
        message_text = 'تم قبول حجزك ✅' if status == 'approved' else 'تم رفض حجزك ❌'
        c.execute('''
            INSERT INTO notifications (user_name, message)
            VALUES (?, ?)
        ''', (user_name, message_text))

        conn.commit()
        conn.close()

        return jsonify({'success': True})

    # عرض الحجوزات المعلقة
    c.execute('SELECT * FROM appointments WHERE status = "pending"')
    appointments = c.fetchall()
    conn.close()

    return render_template('admin.html', appointments=appointments)

# عرض حالة الحجز والرسائل
@app.route('/status')
def status():
    name = request.args.get('name')
    conn = sqlite3.connect('appointments.db')
    c = conn.cursor()

    # جلب الرسائل للمستخدم
    c.execute('''
        SELECT message FROM notifications
        WHERE user_name = ? AND is_read = 0
    ''', (name,))
    messages = c.fetchall()

    # تعيين الرسائل كمقروءة
    c.execute('''
        UPDATE notifications
        SET is_read = 1
        WHERE user_name = ?
    ''', (name,))

    conn.commit()
    conn.close()

    return render_template('status.html', messages=messages, name=name)

if __name__ == '__main__':
    app.run(debug=True)
