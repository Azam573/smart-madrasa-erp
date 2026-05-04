import streamlit as st
import pandas as pd
from database import get_connection

def show_students():
    tenant_id = st.session_state.get('tenant_id', 1)
    
    st.markdown("## 👨‍🎓 শিক্ষার্থী ব্যবস্থাপনা (Student Management)")
    st.markdown("এখান থেকে আপনি বর্তমান ছাত্রদের তালিকা দেখতে পারবেন এবং চাইলে কাউকে ডিঅ্যাক্টিভ/টিসি (TC) দিতে পারবেন।")
    st.markdown("---")

    conn = get_connection()
    if not conn:
        st.error("ডাটাবেস কানেকশন পাওয়া যাচ্ছে না!")
        return
    cur = conn.cursor()

    # দুটি আলাদা ট্যাব তৈরি
    tab_active, tab_inactive = st.tabs(["✅ বর্তমান শিক্ষার্থী (Active)", "❌ প্রাক্তন/ডিঅ্যাক্টিভ শিক্ষার্থী"])

    # ==========================================
    # ট্যাব ১: অ্যাক্টিভ শিক্ষার্থী
    # ==========================================
    with tab_active:
        st.markdown("### 🟢 বর্তমান শিক্ষার্থীদের তালিকা")
        try:
            cur.execute("SELECT id, roll_no, name, class_name FROM students WHERE status = 'Active' AND tenant_id = %s ORDER BY class_name, roll_no", (tenant_id,))
            active_students = cur.fetchall()
            
            if active_students:
                df_active = pd.DataFrame(active_students, columns=["ID", "রোল", "নাম", "ক্লাস"])
                st.dataframe(df_active, use_container_width=True, hide_index=True)
                
                # ছাত্র ডিঅ্যাক্টিভ করার অপশন
                st.markdown("---")
                st.markdown("#### ⚠️ শিক্ষার্থী ডিঅ্যাক্টিভ করুন (TC)")
                
                with st.form("deactivate_form", clear_on_submit=True):
                    col1, col2 = st.columns([3, 1])
                    suspend_id = col1.number_input("যে শিক্ষার্থীকে ডিঅ্যাক্টিভ করতে চান তার ID দিন:", min_value=1, step=1)
                    submit_suspend = col2.form_submit_button("ডিঅ্যাক্টিভ করুন", type="primary", use_container_width=True)
                    
                    if submit_suspend:
                        # চেক করা যে ID টি এই মাদরাসার এবং অ্যাক্টিভ কি না
                        cur.execute("SELECT id FROM students WHERE id = %s AND status = 'Active' AND tenant_id = %s", (suspend_id, tenant_id))
                        if cur.fetchone():
                            cur.execute("UPDATE students SET status = 'Inactive' WHERE id = %s AND tenant_id = %s", (suspend_id, tenant_id))
                            conn.commit()
                            st.success(f"✅ ID {suspend_id} কে সফলভাবে ডিঅ্যাক্টিভ করা হয়েছে!")
                            st.rerun()
                        else:
                            st.error("⚠️ এই ID-র কোনো অ্যাক্টিভ ছাত্র আপনার মাদরাসায় পাওয়া যায়নি!")
            else:
                st.info("📌 কোনো অ্যাক্টিভ শিক্ষার্থী পাওয়া যায়নি।")
        except Exception as e:
            conn.rollback()
            st.error(f"ডাটা লোড করতে সমস্যা: {e}")

    # ==========================================
    # ট্যাব ২: ডিঅ্যাক্টিভ শিক্ষার্থী
    # ==========================================
    with tab_inactive:
        st.markdown("### 🔴 প্রাক্তন বা ডিঅ্যাক্টিভ শিক্ষার্থীদের তালিকা")
        try:
            cur.execute("SELECT id, roll_no, name, class_name FROM students WHERE status = 'Inactive' AND tenant_id = %s ORDER BY class_name", (tenant_id,))
            inactive_students = cur.fetchall()
            
            if inactive_students:
                df_inactive = pd.DataFrame(inactive_students, columns=["ID", "রোল", "নাম", "ক্লাস"])
                st.dataframe(df_inactive, use_container_width=True, hide_index=True)
                
                # ভুল করে ডিঅ্যাক্টিভ হলে আবার অ্যাক্টিভ করার অপশন
                st.markdown("---")
                st.markdown("#### ♻️ পুনরায় অ্যাক্টিভ করুন")
                
                with st.form("reactivate_form", clear_on_submit=True):
                    col3, col4 = st.columns([3, 1])
                    reactivate_id = col3.number_input("পুনরায় অ্যাক্টিভ করতে ID দিন:", min_value=1, step=1, key="react")
                    submit_react = col4.form_submit_button("অ্যাক্টিভ করুন", use_container_width=True)
                    
                    if submit_react:
                        # চেক করা যে ID টি ইনঅ্যাক্টিভ কি না
                        cur.execute("SELECT id FROM students WHERE id = %s AND status = 'Inactive' AND tenant_id = %s", (reactivate_id, tenant_id))
                        if cur.fetchone():
                            cur.execute("UPDATE students SET status = 'Active' WHERE id = %s AND tenant_id = %s", (reactivate_id, tenant_id))
                            conn.commit()
                            st.success(f"✅ ID {reactivate_id} কে পুনরায় অ্যাক্টিভ করা হয়েছে!")
                            st.rerun()
                        else:
                            st.error("⚠️ এই ID-র কোনো ইনঅ্যাক্টিভ ছাত্র পাওয়া যায়নি!")
            else:
                st.info("📌 আপনার মাদরাসায় বর্তমানে কোনো ডিঅ্যাক্টিভ শিক্ষার্থী নেই।")
        except Exception as e:
            conn.rollback()
            st.error(f"ডাটা লোড করতে সমস্যা: {e}")

    if cur:
        cur.close()