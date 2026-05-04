
import psycopg2
import streamlit as st
import urllib.parse

@st.cache_resource
def get_connection():
    try:
        # পাসওয়ার্ড নিরাপদ করা
        password = "qZEwjuvZYeSZyZ72@"
        encoded_password = urllib.parse.quote_plus(password)
        
        # ট্রানজেকশন পুলাার ব্যবহার করা হচ্ছে (এটিই আপনার সার্ভারলেস অ্যাপের জন্য সেরা)
        # পোর্টটি আপনার ড্যাশবোর্ড থেকে দেখে ৬৫৪৩ হলে তা নিশ্চিত করুন
        host = "db.hgifhvgjdulhhjdgrxhe.supabase.co"
        port = "6543" 
        dbname = "postgres"
        
        conn_str = f"postgresql://postgres:{encoded_password}@{host}:{port}/{dbname}?sslmode=require"
        
        # কানেকশন তৈরি
        conn = psycopg2.connect(conn_str)
        return conn
    except Exception as e:
        st.error(f"❌ ডাটাবেস কানেকশন এরর: {e}")
        return None

# কানেকশন হেলথ চেক
def check_conn_health(conn):
    try:
        if conn and not conn.closed:
            return True
    except:
        return False
    return False
