
import psycopg2
import streamlit as st
import urllib.parse

@st.cache_resource
def get_connection():
    try:
        # ১. পাসওয়ার্ড এনকোড করা (পাসওয়ার্ডে @ থাকায় এটি জরুরি)
        password = "qZEwjuvZYeSZyZ72@"
        encoded_password = urllib.parse.quote_plus(password)
        
        # ২. সুপাবেসের স্ট্যাবল হোস্ট এড্রেস (Transaction Pooler)
        # আপনার প্রজেক্টের জন্য এটি সবচেয়ে বেশি কাজ করবে
        host = "db.hgifhvgjdulhhjdgrxhe.supabase.co"
        
        # ৩. কানেকশন স্ট্রিং তৈরি
        # সরাসরি কানেকশন এর বদলে আমরা সেশন মোড ব্যবহার করার চেষ্টা করছি
        conn_str = f"postgresql://postgres:{encoded_password}@{host}:5432/postgres?sslmode=require"
        
        conn = psycopg2.connect(conn_str)
        return conn
    except Exception as e:
        # এরর মেসেজটি অ্যাপের স্ক্রিনে দেখাবে
        st.error(f"❌ ডাটাবেস কানেকশন এরর: {e}")
        return None

def check_conn_health(conn):
    if conn is None: return False
    try:
        with conn.cursor() as cur:
            cur.execute('SELECT 1')
        return True
    except:
        return False
