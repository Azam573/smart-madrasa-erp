import psycopg2
import streamlit as st
import urllib.parse

@st.cache_resource
def get_connection():
    try:
        # ১. পাসওয়ার্ড এনকোড করা (যেহেতু আপনার পাসওয়ার্ডে '@' আছে)
        password = "qZEwjuvZYeSZyZ72@"
        encoded_password = urllib.parse.quote_plus(password)
        
        # ২. আপনার দেওয়া নতুন Pooler Connection Details
        host = "aws-1-ap-south-1.pooler.supabase.com"
        port = "6543" 
        dbname = "postgres"
        user = "postgres.hgifhvgjdulhhjdgrxhe"
        
        # ৩. চূড়ান্ত কানেকশন স্ট্রিং
        conn_str = f"postgresql://{user}:{encoded_password}@{host}:{port}/{dbname}?sslmode=require"
        
        # ৪. ডাটাবেসের সাথে কানেক্ট করা
        conn = psycopg2.connect(conn_str)
        return conn
    except Exception as e:
        st.error(f"❌ ডাটাবেস কানেকশন এরর: {e}")
        return None

# কানেকশন হেলথ চেক (এটি নিশ্চিত করবে ডাটাবেস লাইভ আছে কি না)
def check_conn_health(conn):
    try:
        if conn and not conn.closed:
            return True
    except:
        return False
    return False
