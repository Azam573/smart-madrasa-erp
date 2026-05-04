import os
import subprocess
from datetime import datetime
import time
import schedule

# ==========================================
# ১. আপনার ডাটাবেস কনফিগারেশন (আপনার আসল ডাটাবেসের তথ্য দিন)
# ==========================================
DB_NAME = "smart_school_db"  # আপনার ডাটাবেসের নাম
DB_USER = "postgres"          # ডাটাবেসের ইউজারনেম
DB_PASS = "maimuna123"        # আপনার ডাটাবেসের পাসওয়ার্ড
DB_HOST = "localhost"         # সার্ভার অ্যাড্রেস (লোকাল পিসির জন্য localhost)
DB_PORT = "5432"              # পোর্ট

# ==========================================
# ২. ব্যাকআপ সেভ করার ফোল্ডার তৈরি
# ==========================================
BACKUP_DIR = "database_backups"

# যদি ফোল্ডারটি আগে থেকে না থাকে, তবে নতুন করে তৈরি করে নিবে
if not os.path.exists(BACKUP_DIR):
    os.makedirs(BACKUP_DIR)

# ==========================================
# ৩. ডাটাবেস ব্যাকআপ নেওয়ার মূল ফাংশন
# ==========================================
def backup_database():
    """ডাটাবেস ব্যাকআপ নেওয়ার ফাংশন"""
    # ব্যাকআপ ফাইলের নামে আজকের তারিখ ও সময় যুক্ত করা হচ্ছে
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    backup_file = os.path.join(BACKUP_DIR, f"backup_{timestamp}.sql")

    # PostgreSQL এর pg_dump কমান্ড সেট করা
    os.environ['PGPASSWORD'] = DB_PASS
    command = f"pg_dump -h {DB_HOST} -p {DB_PORT} -U {DB_USER} -f {backup_file} {DB_NAME}"

    print(f"\n⏳ [{timestamp}] ব্যাকআপ প্রক্রিয়া শুরু হচ্ছে...")
    
    try:
        # কমান্ডটি রান করানো
        subprocess.run(command, shell=True, check=True)
        print(f"✅ আলহামদুলিল্লাহ! ব্যাকআপ সফলভাবে তৈরি হয়েছে।")
        print(f"📁 ফাইল লোকেশন: {backup_file}")
        
    except subprocess.CalledProcessError as e:
        print(f"❌ ব্যাকআপ নিতে সমস্যা হয়েছে: {e}")

# ==========================================
# ৪. অটোমেটিক শিডিউলার (দিনে ৫ বার)
# ==========================================
print("🛡️ অটোমেটিক ডাটাবেস ব্যাকআপ সিস্টেম চালু হয়েছে...")
print("অপেক্ষা করা হচ্ছে... (দিনে ৫ বার ব্যাকআপ নেওয়া হবে)")

# দিনে ৫ বার ব্যাকআপ নেওয়ার নির্দিষ্ট সময়
schedule.every().day.at("08:00").do(backup_database)  # সকাল ৮টা (অফিস শুরুর সময়)
schedule.every().day.at("13:00").do(backup_database)  # দুপুর ১টা (হাজিরা শেষে)
schedule.every().day.at("17:00").do(backup_database)  # বিকেল ৫টা (অফিস ছুটির সময়)
schedule.every().day.at("21:00").do(backup_database)  # রাত ৯টা
schedule.every().day.at("02:00").do(backup_database)  # রাত ২টা (সার্ভার যখন ফ্রি থাকে)

# মেইন লুপ - যা সময় চেক করতে থাকবে
if __name__ == "__main__":
    while True:
        schedule.run_pending()
        time.sleep(60) # প্রতি ৬০ সেকেন্ড (১ মিনিট) পর পর চেক করবে সময় হয়েছে কি না