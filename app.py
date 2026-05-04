import streamlit as st
from datetime import datetime
from database import get_connection

# --- আপনার দেয়া মডিউল নাম অনুযায়ী ইমপোর্ট ---
from modules.dashboard import show_dashboard
from modules.admission import show_admission
from modules.finance import show_finance
from modules.attendance import show_attendance
from modules.results import show_results
from modules.certificates import show_certificates
from modules.inventory import show_inventory
from modules.expenses import show_expenses
from modules.hr import show_hr
from modules.id_cards import show_id_cards
from modules.notice import show_notice
from modules.super_admin import show_super_admin
from modules.user_management import show_user_management
from modules.class_management import show_class_management

# পেজ কনফিগ
st.set_page_config(page_title="স্মার্ট মাদরাসা ইআরপি (SaaS)", layout="wide", page_icon="🏢")

# --- সেশন স্টেট ইনিশিয়ালাইজেশন ---
if 'logged_in' not in st.session_state:
    st.session_state.update({
        'logged_in': False, 
        'role': None, 
        'username': None, 
        'tenant_id': None, 
        'madrasa_name': "স্মার্ট মাদরাসা ম্যানেজমেন্ট",
        'established_year': 2024, # ডিফল্ট সাল
        'choice': "ড্যাশবোর্ড"
    })

# --- লগিন ফাংশন (SaaS Multi-tenant Logic) ---
def login():
    st.markdown("<h2 style='text-align: center; color: #1E88E5;'>🔒 সিকিউর লগিন প্যানেল (SaaS)</h2>", unsafe_allow_html=True)
    
    col_l, col_m, col_r = st.columns([1, 1.5, 1])
    with col_m:
        with st.form("login_form"):
            u = st.text_input("ইউজারনেম")
            p = st.text_input("পাসওয়ার্ড", type="password")
            
            if st.form_submit_button("লগিন", use_container_width=True, type="primary"):
                conn = get_connection()
                if conn:
                    cur = conn.cursor()
                    try:
                        # ১. সুপার অ্যাডমিন চেক
                        cur.execute("SELECT username FROM system_admin WHERE username=%s AND password=%s", (u, p))
                        if cur.fetchone():
                            st.session_state.update({
                                'logged_in': True, 'role': 'Super Admin (CEO)', 
                                'username': u, 'tenant_id': 0,
                                'madrasa_name': '👑 কন্ট্রোল প্যানেল',
                                'established_year': 2024,
                                'choice': "সুপার অ্যাডমিন প্যানেল"
                            })
                            st.rerun()
                        
                        # ২. মাদরাসা অ্যাডমিন চেক (এখানে established_year যুক্ত করা হয়েছে)
                        cur.execute("SELECT tenant_id, madrasa_name, status, valid_until, established_year FROM madrasas WHERE admin_user=%s AND admin_pass=%s", (u, p))
                        client = cur.fetchone()
                        if client:
                            t_id, m_name, status, v_until, est_year = client
                            if status != 'Active':
                                st.error("🚫 অ্যাকাউন্টটি স্থগিত করা হয়েছে।")
                            elif v_until and v_until < datetime.now().date():
                                st.error(f"⏳ মেয়াদ শেষ হয়ে গেছে! ({v_until})")
                            else:
                                st.session_state.update({
                                    'logged_in': True, 'role': 'Admin', 'username': u, 
                                    'tenant_id': t_id, 'madrasa_name': m_name, 
                                    'established_year': est_year if est_year else 2024, # সাল সেভ হচ্ছে
                                    'choice': "ড্যাশবোর্ড"
                                })
                                st.rerun()
                        
                        # ৩. স্টাফ ইউজার চেক (এখানেও established_year যুক্ত করা হয়েছে)
                        cur.execute("SELECT role, tenant_id FROM users WHERE username=%s AND password=%s", (u, p))
                        user = cur.fetchone()
                        if user:
                            role, t_id = user
                            cur.execute("SELECT madrasa_name, established_year FROM madrasas WHERE tenant_id=%s", (t_id,))
                            m_data = cur.fetchone()
                            m_name = m_data[0]
                            est_year = m_data[1]
                            
                            st.session_state.update({
                                'logged_in': True, 'role': role, 'username': u,
                                'tenant_id': t_id, 'madrasa_name': m_name, 
                                'established_year': est_year if est_year else 2024, # সাল সেভ হচ্ছে
                                'choice': "ড্যাশবোর্ড"
                            })
                            st.rerun()
                        else:
                            st.error("❌ ইউজারনেম বা পাসওয়ার্ড ভুল!")
                    except Exception as e:
                        st.error(f"Error: {e}")
                    finally: 
                        if cur: cur.close()

# --- মেইন ড্যাশবোর্ড লজিক ---
if not st.session_state['logged_in']:
    login()
else:
    # সাইডবার মেনু
    st.sidebar.title(f"🏢 {st.session_state['madrasa_name']}")
    st.sidebar.success(f"👤 {st.session_state['username'].upper()} ({st.session_state['role']})")
    
    if st.sidebar.button("🚪 লগআউট", use_container_width=True):
        st.session_state.clear()
        st.rerun()
    
    st.sidebar.markdown("---")
    
    # রোল অনুযায়ী মেনু ফিল্টার (RBAC)
    roles = {
        'Super Admin (CEO)': ["সুপার অ্যাডমিন প্যানেল"],
        'Admin': ["ড্যাশবোর্ড", "ইউজার কন্ট্রোল", "ভর্তি ফরম ও তালিকা", "বেতন ও ফি কালেকশন", "হাজিরা", "ক্লাস ম্যানেজমেন্ট", "রেজাল্ট ও মার্কশিট", "লাইব্রেরি ও হোস্টেল", "হিসাব ও ব্যয় (Accounts)", "শিক্ষক ও স্টাফ (HR)", "আইডি কার্ড জেনারেটর", "সাধারণ বিজ্ঞপ্তি (SMS)", "সার্টিফিকেট জেনারেটর"],
        'Accountant': ["ড্যাশবোর্ড", "বেতন ও ফি কালেকশন", "হিসাব ও ব্যয় (Accounts)"],
        'Teacher': ["ড্যাশবোর্ড", "ভর্তি ফরম ও তালিকা", "হাজিরা", "রেজাল্ট ও মার্কশিট"]
    }
    
    menu_options = roles.get(st.session_state['role'], ["ড্যাশবোর্ড"])
    if st.session_state.choice not in menu_options:
        st.session_state.choice = menu_options[0]
        
    menu = st.sidebar.radio("মেনু নির্বাচন করুন", menu_options, index=menu_options.index(st.session_state.choice))
    
    if menu != st.session_state.choice:
        st.session_state.choice = menu
        st.rerun()

    # --- পেজ রাউটিং (আপনার মডিউল নাম অনুযায়ী) ---
    page = st.session_state.choice
    
    if page == "ড্যাশবোর্ড": show_dashboard()
    elif page == "ইউজার কন্ট্রোল": show_user_management()
    elif page == "ভর্তি ফরম ও তালিকা": show_admission()
    elif page == "বেতন ও ফি কালেকশন": show_finance()
    elif page == "হাজিরা": show_attendance()
    elif page == "রেজাল্ট ও মার্কশিট": show_results()
    elif page == "সার্টিফিকেট জেনারেটর": show_certificates()
    elif page == "লাইব্রেরি ও হোস্টেল": show_inventory()
    elif page == "হিসাব ও ব্যয় (Accounts)": show_expenses()
    elif page == "শিক্ষক ও স্টাফ (HR)": show_hr()
    elif page == "আইডি কার্ড জেনারেটর": show_id_cards()
    elif page == "সাধারণ বিজ্ঞপ্তি (SMS)": show_notice()
    elif page == "সুপার অ্যাডমিন প্যানেল": show_super_admin()
    elif page == "ক্লাস ম্যানেজমেন্ট": show_class_management()