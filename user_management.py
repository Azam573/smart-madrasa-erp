import streamlit as st
import pandas as pd
from database import get_connection

def show_user_management():
    st.title("🔐 স্টাফ লগিন এক্সেস ও ইউজার কন্ট্রোল")
    st.markdown("এখান থেকে আপনি আপনার মাদরাসার শিক্ষক ও স্টাফদের জন্য সফটওয়্যারে লগিন করার আলাদা ইউজারনেম ও পাসওয়ার্ড তৈরি করতে পারবেন।")
    st.markdown("---")
    
    # সেশন থেকে বর্তমান মাদরাসার (tenant_id) নেওয়া হচ্ছে
    tenant_id = st.session_state.get('tenant_id', 1)
    
    conn = get_connection()
    if not conn: 
        st.error("ডাটাবেস কানেকশন এরর!")
        return
        
    conn.rollback()
    cur = conn.cursor()
    
    col1, col2 = st.columns([1, 1])
    
    # ==========================================
    # --- নতুন ইউজার তৈরি ---
    # ==========================================
    with col1:
        st.subheader("নতুন ইউজার তৈরি করুন")
        with st.form("add_user_form", clear_on_submit=True):
            new_user = st.text_input("ইউজারনেম (ইংরেজিতে, স্পেস ছাড়া) *")
            new_pass = st.text_input("পাসওয়ার্ড *", type="password")
            
            # অ্যাডমিন কাদের এক্সেস দিতে পারবে
            role = st.selectbox("অ্যাক্সেস লেভেল (Role)", ["Teacher", "Accountant"])
            
            if st.form_submit_button("✅ লগিন এক্সেস দিন", use_container_width=True, type="primary"):
                if new_user and new_pass:
                    # ইউজারনেমে স্পেস চেক
                    if " " in new_user:
                        st.warning("⚠️ ইউজারনেমে কোনো স্পেস রাখা যাবে না। (যেমন: admin_123)")
                    else:
                        try:
                            # SaaS Security: চেক করা যে এই ইউজারনেম অন্য কেউ ব্যবহার করছে কি না
                            cur.execute("SELECT id FROM users WHERE username = %s", (new_user,))
                            if cur.fetchone():
                                st.error("⚠️ এই ইউজারনেমটি ইতিমধ্যে সিস্টেমে আছে। দয়া করে নামের সাথে কোনো সংখ্যা (যেমন: mamun12) ব্যবহার করুন।")
                            else:
                                cur.execute("INSERT INTO users (username, password, role, tenant_id) VALUES (%s, %s, %s, %s)", 
                                            (new_user, new_pass, role, tenant_id))
                                conn.commit()
                                st.success(f"🎉 আলহামদুলিল্লাহ! {role} এর জন্য '{new_user}' সফলভাবে তৈরি হয়েছে!")
                                st.rerun()
                        except Exception as e:
                            conn.rollback()
                            st.error(f"ডাটাবেস এরর: {e}")
                else:
                    st.warning("⚠️ ইউজারনেম এবং পাসওয়ার্ড দিতে হবে।")

    # ==========================================
    # --- বর্তমান ইউজারদের তালিকা ---
    # ==========================================
    with col2:
        st.subheader("আপনার বর্তমান স্টাফ ইউজার লিস্ট")
        try:
            # শুধুমাত্র এই মাদরাসার ইউজারদের আনা হচ্ছে
            cur.execute("SELECT id, username, role FROM users WHERE tenant_id = %s ORDER BY role", (tenant_id,))
            users_data = cur.fetchall()
            
            if users_data:
                df = pd.DataFrame(users_data, columns=["ID", "ইউজারনেম", "রোল"])
                st.table(df[["ইউজারনেম", "রোল"]])
                
                # শুধু Teacher এবং Accountant দের ডিলিট করার অপশন (Admin কে ডিলিট করা যাবে না)
                deleteable_users = [r for r in users_data if r[2] != 'Admin']
                
                if deleteable_users:
                    st.markdown("---")
                    with st.form("delete_user_form"):
                        user_to_delete = st.selectbox("ইউজার ডিলিট করুন (লগিন বাতিল):", [f"{r[1]} ({r[2]})" for r in deleteable_users])
                        if st.form_submit_button("❌ এক্সেস বাতিল করুন", use_container_width=True):
                            del_user = user_to_delete.split(" ")[0]
                            try:
                                cur.execute("DELETE FROM users WHERE username = %s AND tenant_id = %s", (del_user, tenant_id))
                                conn.commit()
                                st.success(f"✅ {del_user} এর লগিন এক্সেস বাতিল করা হয়েছে!")
                                st.rerun()
                            except Exception as e:
                                conn.rollback()
                                st.error(f"ডিলিট এরর: {e}")
                else:
                    st.info("💡 ডিলিট করার মতো কোনো এক্সট্রা স্টাফ ইউজার নেই। (মেইন অ্যাডমিন আইডি ডিলিট করা যায় না)")
            else:
                st.info("📌 আপনি এখনো কোনো স্টাফকে লগিন এক্সেস দেননি।")
        except Exception as e:
            conn.rollback()
            st.error(f"ডাটা লোড এরর: {e}")
            
    cur.close()