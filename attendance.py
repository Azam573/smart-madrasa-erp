import streamlit as st
import pandas as pd
from database import get_connection
from datetime import datetime
from utils import send_sms  # <-- SaaS সাপোর্টেড SMS মডিউল

def show_attendance():
    tenant_id = st.session_state.get('tenant_id', 1)
    institute_name = st.session_state.get('madrasa_name', 'স্মার্ট মাদরাসা') # name update

    st.markdown("## 📅 দৈনিক হাজিরা খাতা ও SMS")
    st.markdown("---")

    conn = get_connection()
    if not conn:
        st.error("ডাটাবেস কানেকশন পাওয়া যাচ্ছে না!")
        return
    
    conn.rollback() 
    cur = conn.cursor()

    standard_classes = [
        "প্লে (Play)", "নার্সারি (Nursery)", "কেজি (KG)",
        "১ম শ্রেণি", "২য় শ্রেণি", "৩য় শ্রেণি", "৪র্থ শ্রেণি", "৫ম শ্রেণি",
        "৬ষ্ঠ শ্রেণি", "৭ম শ্রেণি", "৮ম শ্রেণি", "৯ম শ্রেণি", "১০ম শ্রেণি",
        "হিফজ", "মক্তব"
    ]

    # ডায়নামিক ক্লাস লোড
    try:
        cur.execute("SELECT DISTINCT class_name FROM students WHERE tenant_id = %s AND status = 'Active'", (tenant_id,))
        db_classes = [row[0] for row in cur.fetchall() if row[0] is not None]
        for c in db_classes:
            if c not in standard_classes: standard_classes.append(c)
    except Exception:
        conn.rollback()

    # ==========================================
    # 🎯 গ্লোবাল ফিল্টার (সবার উপরে থাকবে)
    # ==========================================
    col1, col2 = st.columns(2)
    att_date = col1.date_input("তারিখ নির্বাচন করুন", datetime.now().date())
    selected_class = col2.selectbox("ক্লাস নির্বাচন করুন", standard_classes, key="att_class")
    
    st.markdown("---")

    tab_entry, tab_report = st.tabs(["📝 হাজিরা এন্ট্রি", "📊 হাজিরা রিপোর্ট"])

    # ==========================================
    # --- ট্যাব ১: হাজিরা এন্ট্রি ও SMS ---
    # ==========================================
    with tab_entry:
        try:
            # ক্লাস সিলেক্ট করার সাথে সাথেই অটো ডাটা ফেচ হবে (কোনো এক্সট্রা বাটন ছাড়া)
            cur.execute("SELECT id, roll_no, name, mobile_no FROM students WHERE class_name = %s AND tenant_id = %s AND status = 'Active' ORDER BY roll_no", (selected_class, tenant_id)) 
            students = cur.fetchall()

            if students:
                st.success(f"✅ {len(students)} জন ছাত্র পাওয়া গেছে।")
                
                cur.execute("SELECT student_id, status FROM attendance WHERE date = %s AND tenant_id = %s", (att_date, tenant_id))
                existing_att = {row[0]: row[1] for row in cur.fetchall()}

                df_data = []
                student_dict = {} 
                
                for s in students:
                    s_id, roll, name, mobile = s
                    student_dict[s_id] = {"name": name, "mobile": mobile}
                    df_data.append({"ID": s_id, "রোল": roll, "নাম": name, "উপস্থিতি": existing_att.get(s_id, "Present")})
                
                df = pd.DataFrame(df_data)

                with st.form("attendance_form_v3", clear_on_submit=False):
                    edited_df = st.data_editor(
                        df,
                        column_config={
                            "ID": st.column_config.NumberColumn(disabled=True),
                            "রোল": st.column_config.TextColumn(disabled=True),
                            "নাম": st.column_config.TextColumn(disabled=True),
                            "উপস্থিতি": st.column_config.SelectboxColumn(options=["Present", "Absent", "Leave"], required=True)
                        },
                        hide_index=True, 
                        width="stretch" 
                    )

                    st.markdown("---")
                    send_sms_checkbox = st.checkbox("📲 সেভ করার সাথে সাথে অভিভাবকদের হাজিরা/অনুপস্থিতির অটোমেটিক SMS পাঠান", value=False)

                    submit_btn = st.form_submit_button("✅ সবার হাজিরা এক ক্লিকে সেভ করুন", use_container_width=True)
                    
                    if submit_btn:
                        with st.spinner("ডাটাবেসে সেভ হচ্ছে এবং SMS পাঠানো হচ্ছে..."):
                            try:
                                sms_count = 0
                                for index, row in edited_df.iterrows():
                                    s_id = int(row['ID'])
                                    status = str(row['উপস্থিতি'])
                                    
                                    # ১. ডাটাবেসে সেভ বা আপডেট
                                    cur.execute("SELECT id FROM attendance WHERE student_id=%s AND date=%s AND tenant_id=%s", (s_id, att_date, tenant_id))
                                    exists = cur.fetchone()
                                    
                                    if exists:
                                        cur.execute("UPDATE attendance SET status=%s WHERE id=%s", (status, exists[0]))
                                    else:
                                        cur.execute("INSERT INTO attendance (student_id, date, status, tenant_id) VALUES (%s, %s, %s, %s)", (s_id, att_date, status, tenant_id))
                                    
                                    # ২. SMS পাঠানো
                                    if send_sms_checkbox:
                                        mobile = student_dict[s_id]['mobile']
                                        name = student_dict[s_id]['name']
                                        
                                        # মোবাইল নম্বর থাকলেই কেবল SMS পাঠাবে
                                        if mobile and len(str(mobile)) >= 11:
                                            if status == "Present":
                                                msg = f"সম্মানিত অভিভাবক, আপনার সন্তান {name} আজ মাদরাসায় উপস্থিত হয়েছে। - {institute_name}"
                                                success, _ = send_sms(tenant_id, mobile, msg)
                                                if success: sms_count += 1
                                                
                                            elif status == "Absent":
                                                msg = f"সম্মানিত অভিভাবক, আপনার সন্তান {name} আজ মাদরাসায় অনুপস্থিত। - {institute_name}"
                                                success, _ = send_sms(tenant_id, mobile, msg)
                                                if success: sms_count += 1
                                                
                                            elif status == "Leave":
                                                msg = f"সম্মানিত অভিভাবক, আপনার সন্তান {name}-এর আজকের ছুটি মঞ্জুর করা হয়েছে। - {institute_name}"
                                                success, _ = send_sms(tenant_id, mobile, msg)
                                                if success: sms_count += 1

                                conn.commit()
                                
                                if send_sms_checkbox:
                                    st.success(f"🎉 আলহামদুলিল্লাহ! হাজিরা সফলভাবে সেভ হয়েছে এবং মোট {sms_count} জনকে SMS পাঠানো হয়েছে।")
                                else:
                                    st.success("🎉 আলহামদুলিল্লাহ! হাজিরা সফলভাবে সেভ হয়েছে। (SMS বন্ধ ছিল)")
                                
                                st.balloons()
                            except Exception as e:
                                conn.rollback()
                                st.error(f"❌ সেভ করার সময় ডাটাবেস এরর: {e}") 
            else:
                st.info("⚠️ এই ক্লাসে কোনো রানিং ছাত্র পাওয়া যায়নি।")
        except Exception as e:
            conn.rollback()
            st.error(f"লোড এরর: {e}")

    # ==========================================
    # --- ট্যাব ২: হাজিরা রিপোর্ট ---
    # ==========================================
    with tab_report:
        st.subheader(f"📊 {selected_class} - এর আজকের রিপোর্ট")
        try:
            # নির্দিষ্ট ক্লাস এবং নির্দিষ্ট তারিখের রিপোর্ট
            cur.execute("""
                SELECT a.status, COUNT(a.id) FROM attendance a
                JOIN students s ON a.student_id = s.id
                WHERE a.date = %s AND s.class_name = %s AND a.tenant_id = %s AND s.tenant_id = %s
                GROUP BY a.status
            """, (att_date, selected_class, tenant_id, tenant_id))
            report_data = cur.fetchall()

            if report_data:
                col_c, col_d = st.columns([2, 1])
                df_rep = pd.DataFrame(report_data, columns=["Status", "Count"])
                
                # বার চার্ট
                col_c.bar_chart(df_rep.set_index("Status"))
                
                # সামারি বক্স
                for _, row in df_rep.iterrows():
                    if row['Status'] == 'Present':
                        col_d.success(f"**উপস্থিত (Present):** {row['Count']} জন")
                    elif row['Status'] == 'Absent':
                        col_d.error(f"**অনুপস্থিত (Absent):** {row['Count']} জন")
                    else:
                        col_d.warning(f"**ছুটি (Leave):** {row['Count']} জন")
            else:
                st.info("📌 এই তারিখ এবং ক্লাসের কোনো হাজিরার ডাটা এখনো এন্ট্রি করা হয়নি।")
        except Exception as e:
            conn.rollback()
            st.error(f"রিপোর্ট এরর: {e}")

    cur.close()