import psycopg2
import streamlit as st

@st.cache_resource
def get_connection():
    try:
        # আমরা এখানে কানেকশন স্ট্রিং ব্যবহার করছি যা বেশি স্ট্যাবল
        conn = psycopg2.connect(
            "postgresql://postgres:qZEwjuvZYeSZyZ72@db.hgifhvgjdulhhjdgrxhe.supabase.co:5432/postgres?sslmode=require"
        )
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
