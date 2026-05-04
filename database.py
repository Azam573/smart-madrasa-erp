import psycopg2
import streamlit as st

# কানেকশন ক্যাশ করে রাখার ফাংশন যাতে বারবার ডাটাবেস লোড না হয়
@st.cache_resource
def get_connection():
    try:
        # আপনার Supabase ডাটাবেসের সঠিক ইনফরমেশন এখানে বসিয়ে দিয়েছি
        conn = psycopg2.connect(
            dbname="postgres", 
            user="postgres",
            password="qZEwjuvZYeSZyZ72@", # আপনার দেওয়া পাসওয়ার্ড
            host="db.hgifhvgjdulhhjdgrxhe.supabase.co",
            port="5432"
        )
        return conn
    except Exception as e:
        # কানেকশন না হলে স্ক্রিনে লাল বক্সে এরর দেখাবে
        st.error(f"❌ অনলাইন ডাটাবেস কানেকশন এরর: {e}")
        return None

# কানেকশন সচল আছে কি না তা চেক করার হেল্পার ফাংশন
def check_conn_health(conn):
    if conn is None:
        return False
    try:
        with conn.cursor() as cur:
            cur.execute('SELECT 1')
        return True
    except:
        return False