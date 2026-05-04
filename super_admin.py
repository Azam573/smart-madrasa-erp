import streamlit as st
import pandas as pd
from database import get_connection
from datetime import datetime, timedelta

def show_super_admin():
    st.title("👑 সুপার অ্যাডমিন কন্ট্রোল প্যানেল (SaaS)")
    st.markdown("সফটওয়্যার ওনার ড্যাশবোর্ড: ক্লায়েন্ট ম্যানেজমেন্ট এবং বিলিং কন্ট্রোল।")
    st.markdown("---")
    
    tab_new, tab_list, tab_billing, tab_settings = st.tabs([
        "➕ নতুন মাদরাসা", 
        "🏫 ক্লায়েন্ট তালিকা", 
        "💰 সাবস্ক্রিপশন ও বিলিং", 
        "⚙️ সেটিংস ও পাসওয়ার্ড"
    ])
    
    conn = get_connection()
    if not conn:
        st.error("ডাটাবেস কানেকশন পাওয়া যাচ্ছে না!")
        return
        
    cur = conn.cursor()

    # ==========================================
    # --- ট্যাব ১: নতুন মাদরাসা (ক্লায়েন্ট) যুক্ত করা ---
    # ==========================================
    with tab_new:
        st.subheader("নতুন ক্লায়েন্ট রেজিস্ট্রেশন")
        with st.form("new_madrasa_form", clear_on_submit=True):
            col1, col2 = st.columns(2)
            m_name = col1.text_input("মাদরাসার নাম *")
            m_contact = col2.text_input("যোগাযোগ নম্বর (মোবাইল) *")
            
            username = col1.text_input("অ্যাডমিন ইউজারনেম (ইংরেজিতে) *")
            password = col2.text_input("লগিন পাসওয়ার্ড *", type="password")
            
            sub_fee = col1.number_input("মাসিক সাবস্ক্রিপশন ফি (৳)", value=1000)
            validity_days = col2.selectbox("প্রাথমিক ভ্যালিডিটি (দিন)", [30, 90, 180, 365, 7, 15])
            
            if st.form_submit_button("✅ মাদরাসা যুক্ত করুন", use_container_width=True, type="primary"):
                if m_name and username and password:
                    valid_date = datetime.now().date() + timedelta(days=validity_days)
                    try:
                        # ১. মাদরাসা টেবিলে ডাটা সেভ
                        cur.execute("""
                            INSERT INTO madrasas (madrasa_name, admin_user, admin_pass, contact_no, monthly_fee, valid_until, status)
                            VALUES (%s, %s, %s, %s, %s, %s, 'Active') RETURNING tenant_id
                        """, (m_name, username, password, m_contact, sub_fee, valid_date))
                        new_tenant_id = cur.fetchone()[0]

                        # ২. ওই মাদরাসার জন্য মেইন ইউজার (Admin) তৈরি করা
                        cur.execute("""
                            INSERT INTO users (username, password, role, tenant_id)
                            VALUES (%s, %s, 'Admin', %s)
                        """, (username, password, new_tenant_id))
                        
                        conn.commit()
                        st.success(f"🎉 '{m_name}' সফলভাবে যুক্ত হয়েছে! ইউজারনেম: {username}")
                        st.balloons()
                    except Exception as e:
                        conn.rollback()
                        st.error(f"ইউজারনেম '{username}' ইতিমধ্যে ব্যবহৃত হচ্ছে বা ডাটাবেস এরর।")
                else:
                    st.warning("⚠️ সব তথ্য পূরণ করা বাধ্যতামূলক।")

    # ==========================================
    # --- ট্যাব ২: সকল ক্লায়েন্ট লিস্ট ---
    # ==========================================
    with tab_list:
        st.subheader("আপনার ক্লায়েন্টদের তালিকা")
        try:
            cur.execute("SELECT tenant_id, madrasa_name, contact_no, admin_user, status, valid_until FROM madrasas ORDER BY tenant_id")
            madrasas = cur.fetchall()
            
            if madrasas:
                df_m = pd.DataFrame(madrasas, columns=["ID", "মাদরাসার নাম", "মোবাইল", "ইউজারনেম", "স্ট্যাটাস", "ভ্যালিডিটি শেষ"])
                st.dataframe(df_m, use_container_width=True, hide_index=True)
                
                st.markdown("---")
                st.markdown("#### 🔒 ক্লায়েন্ট স্ট্যাটাস কন্ট্রোল")
                m_id_to_update = st.selectbox("মাদরাসা নির্বাচন করুন:", [f"{r[0]} - {r[1]}" for r in madrasas])
                new_status = st.radio("নতুন স্ট্যাটাস:", ["Active", "Blocked"], horizontal=True)
                
                if st.button("আপডেট স্ট্যাটাস", use_container_width=True):
                    selected_id = int(m_id_to_update.split(" - ")[0])
                    cur.execute("UPDATE madrasas SET status = %s WHERE tenant_id = %s", (new_status, selected_id))
                    conn.commit()
                    st.success("✅ স্ট্যাটাস আপডেট হয়েছে!")
                    st.rerun()
            else:
                st.info("📌 কোনো ক্লায়েন্ট পাওয়া যায়নি।")
        except Exception as e:
            st.error(f"ডাটা লোড এরর: {e}")

    # ==========================================
    # --- ট্যাব ৩: সাবস্ক্রিপশন ও বিলিং ---
    # ==========================================
    with tab_billing:
        st.subheader("📊 বিলিং ও রেভিনিউ ট্র্যাকিং")
        
        try:
            # ১. ফাইন্যান্সিয়াল সামারি
            cur.execute("SELECT COUNT(*), SUM(monthly_fee) FROM madrasas WHERE status = 'Active'")
            active_data = cur.fetchone()
            active_clients = active_data[0] or 0
            demand = active_data[1] or 0
            
            cur.execute("SELECT SUM(amount) FROM saas_payments WHERE DATE_TRUNC('month', payment_date) = DATE_TRUNC('month', CURRENT_DATE)")
            collected = cur.fetchone()[0] or 0
            
            b1, b2, b3 = st.columns(3)
            b1.metric("🚀 মোট ক্লায়েন্ট", f"{active_clients} টি")
            b2.metric("💸 মাসিক ডিমান্ড", f"৳ {demand:,.0f}")
            b3.metric("✅ এই মাসে আদায়", f"৳ {collected:,.0f}")
            
            st.markdown("---")
            col_p, col_d = st.columns([1, 1])
            
            # ২. পেমেন্ট ও মেয়াদ বৃদ্ধি
            with col_p:
                st.markdown("#### 💰 পেমেন্ট গ্রহণ")
                cur.execute("SELECT tenant_id, madrasa_name, valid_until, monthly_fee FROM madrasas WHERE status = 'Active'")
                active_m = cur.fetchall()
                
                if active_m:
                    m_dict = {f"{m[1]} ({m[2]})": m for m in active_m}
                    selected_pay = st.selectbox("মাদরাসা নির্বাচন", list(m_dict.keys()), key="bill_sel")
                    m_info = m_dict[selected_pay]
                    
                    with st.form("billing_form", clear_on_submit=True):
                        amt = st.number_input("পেমেন্ট (৳)", value=float(m_info[3]))
                        days = st.selectbox("মেয়াদ বাড়ান (দিন)", [30, 90, 180, 365, 7])
                        note = st.text_input("পেমেন্ট নোট")
                        
                        if st.form_submit_button("পেমেন্ট সেভ ও মেয়াদ বৃদ্ধি", use_container_width=True):
                            t_id, current_validity = m_info[0], m_info[2]
                            today = datetime.now().date()
                            
                            new_val = (current_validity if current_validity > today else today) + timedelta(days=days)
                            
                            cur.execute("INSERT INTO saas_payments (tenant_id, amount, payment_date, extended_days, note) VALUES (%s, %s, %s, %s, %s)", 
                                        (t_id, amt, today, days, note))
                            cur.execute("UPDATE madrasas SET valid_until = %s WHERE tenant_id = %s", (new_val, t_id))
                            conn.commit()
                            st.success(f"✅ পেমেন্ট সফল! নতুন মেয়াদ: {new_val}")
                            st.rerun()

            # ৩. এক্সপায়ারি অ্যালার্ট
            with col_d:
                st.markdown("#### ⚠️ এক্সপায়ারি অ্যালার্ট")
                today_dt = datetime.now().date()
                warning_dt = today_dt + timedelta(days=7)
                
                cur.execute("SELECT madrasa_name, valid_until FROM madrasas WHERE valid_until <= %s AND status = 'Active'", (warning_dt,))
                dues = cur.fetchall()
                
                if dues:
                    df_due = pd.DataFrame(dues, columns=["নাম", "মেয়াদ শেষ"])
                    def color_date(val):
                        if val < today_dt: return 'color: red; font-weight: bold;'
                        return 'color: orange; font-weight: bold;'
                    
                    st.dataframe(df_due.style.map(color_date, subset=['মেয়াদ শেষ']), hide_index=True, use_container_width=True)
                else:
                    st.success("সব ক্লায়েন্টের মেয়াদ ঠিক আছে।")
        except Exception as e:
            st.error(f"বিলিং লোড এরর: {e}")

    # ==========================================
    # --- ট্যাব ৪: সুপার অ্যাডমিন প্রোফাইল ---
    # ==========================================
    with tab_settings:
        st.subheader("⚙️ সুপার অ্যাডমিন প্রোফাইল")
        with st.form("sa_prof_form"):
            new_sa_user = st.text_input("নতুন সুপার অ্যাডমিন ইউজার", value=st.session_state.get('username', 'superadmin'))
            new_sa_pass = st.text_input("নতুন পাসওয়ার্ড", type="password")
            
            if st.form_submit_button("পাসওয়ার্ড আপডেট করুন"):
                if new_sa_pass:
                    cur.execute("UPDATE system_admin SET username=%s, password=%s WHERE id=1", (new_sa_user, new_sa_pass))
                    conn.commit()
                    st.success("✅ সুপার অ্যাডমিন ক্রেডেনশিয়াল আপডেট হয়েছে!")
                else:
                    st.warning("পাসওয়ার্ড দিন।")
                    
    if cur: cur.close()

# ==========================================
# --- মাদরাসা প্রোফাইল সেটিংস ফাংশন ---
# ==========================================
def show_settings():
    st.markdown("---")
    st.subheader("⚙️ মাদরাসা প্রোফাইল সেটিংস")
    
    tenant_id = st.session_state.get('tenant_id')
    current_year = st.session_state.get('established_year', 2024)

    new_year = st.number_input("মাদরাসার স্থাপিত সাল পরিবর্তন করুন", 
                               min_value=1800, 
                               max_value=2100, 
                               value=int(current_year))

    if st.button("সাল আপডেট করুন", type="primary"):
        conn = get_connection()
        if conn:
            cur = conn.cursor()
            try:
                cur.execute("UPDATE madrasas SET established_year = %s WHERE tenant_id = %s", (new_year, tenant_id))
                conn.commit()
                st.session_state['established_year'] = new_year
                st.success(f"✅ আলহামদুলিল্লাহ! স্থাপিত সাল সফলভাবে {new_year} আপডেট হয়েছে।")
                st.info("পরিবর্তনটি মার্কশিটে দেখতে চাইলে একবার পেজটি রিফ্রেশ করুন।")
            except Exception as e:
                conn.rollback()
                st.error(f"আপডেট করতে সমস্যা হয়েছে: {e}")
            finally:
                if cur: cur.close()