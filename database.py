import psycopg2
import streamlit as st
import urllib.parse

@st.cache_resource
def get_connection():
    try:
        # আপনার পাসওয়ার্ডে '@' থাকায় এটি নিরাপদ করার জন্য এনকোড করা প্রয়োজন
        password = "qZEwjuvZYeSZyZ72@"
        encoded_password = urllib.parse.quote_plus(password)
        
        # এনকোড করা পাসওয়ার্ড দিয়ে কানেকশন স্ট্রিং তৈরি
        connection_url = f"postgresql://postgres:{encoded_password}@db.hgifhvgjdulhhjdgrxhe.supabase.co:5432/postgres?sslmode=require"
        
        conn = psycopg2.connect(connection_url)
        return conn
    except Exception as e:
        st.error(f"❌ অনলাইন ডাটাবেস কানেকশন এরর: {e}")
        return None

def check_conn_health(conn):
    if conn is None:
        return False
    try:
        with conn.cursor() as cur:
            cur.execute('SELECT 1')
        return True
    except:
        return False
