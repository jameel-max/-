import os

if os.path.exists("appointments.db"):
    os.remove("appointments.db")
    print("تم حذف قاعدة البيانات.")
else:
    print("الملف مش موجود.")
