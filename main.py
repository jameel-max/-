from flask import Flask, render_template, request, jsonify
import sqlite3

app = Flask(__name__)

# إعداد قاعدة البيانات
def init_db():
    conn = sqlite3.connect('appointments.db')
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS appointments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            car_type TEXT,
            appointment_time TEXT,
            status TEXT
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
    
    # حفظ البيانات في قاعدة البيانات مع حالة "معلق"
    conn = sqlite3.connect('appointments.db')
    c = conn.cursor()
    c.execute('''
        INSERT INTO appointments (name, car_type, appointment_time, status)
        VALUES (?, ?, ?, ?)
    ''', (name, car_type, appointment_time, 'pending'))  # الحالة مبدئيًا هي 'pending'
    conn.commit()
    conn.close()

    return jsonify({'message': 'تم تقديم الحجز بنجاح. في انتظار موافقة صاحب الكراج.'})

# لوحة تحكم صاحب الكراج
@app.route('/admin', methods=['GET', 'POST'])
def admin():
    if request.method == 'POST':
        data = request.get_json()  # استلام البيانات بتنسيق JSON
        appointment_id = data['appointment_id']
        status = data['status']

        # تحديث حالة الحجز في قاعدة البيانات
        conn = sqlite3.connect('appointments.db')
        c = conn.cursor()
        c.execute('''
            UPDATE appointments
            SET status = ?
            WHERE id = ?
        ''', (status, appointment_id))
        conn.commit()
        conn.close()

        return jsonify({'success': True})

    # جلب جميع الحجوزات المعلقة فقط
    conn = sqlite3.connect('appointments.db')
    c = conn.cursor()
    c.execute('SELECT * FROM appointments WHERE status="pending"')
    appointments = c.fetchall()
    conn.close()

    return render_template('admin.html', appointments=appointments)

if __name__ == '__main__':
    app.run(debug=True)
