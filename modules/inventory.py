import streamlit as st
import pandas as pd
from database import get_connection
from datetime import datetime

def show_inventory():
    inst_name = st.session_state.get('madrasa_name', 'স্মার্ট মাদরাসা ম্যানেজমেন্ট')
    tenant_id = st.session_state.get('tenant_id', 1)
    
    st.title(f"📚 {inst_name} - লাইব্রেরি ও হোস্টেল")
    st.markdown("---")

    tab_lib, tab_hostel = st.tabs(["📖 লাইব্রেরি (কিতাব ইস্যু)", "🛏️ হোস্টেল (সিট বরাদ্দ)"])

    conn = get_connection()
    if not conn:
        st.error("ডাটাবেস কানেকশন এরর!")
        return
        
    conn.rollback()
    cur = conn.cursor()

    # ছাত্রের তালিকা ডাটাবেস থেকে আনা (Tenant filter সহ)
    try:
        cur.execute("SELECT id, name, roll_no, class_name FROM students WHERE tenant_id = %s AND COALESCE(status, 'Active') = 'Active' ORDER BY name", (tenant_id,))
        students = cur.fetchall()
        st_dict = {f"{r[1]} (রোল: {r[2]}, শ্রেণী: {r[3]})": r[0] for r in students}
    except Exception as e:
        conn.rollback()
        st.error(f"ছাত্র তালিকা লোড এরর: {e}")
        students = []
        st_dict = {}

    # ==========================================
    # --- ট্যাব ১: লাইব্রেরি ম্যানেজমেন্ট ---
    # ==========================================
    with tab_lib:
        col1, col2 = st.columns([1, 1.5])
        with col1:
            st.subheader("কিতাব ইস্যু করুন")
            if students:
                with st.form("book_issue_form", clear_on_submit=True):
                    sel_st = st.selectbox("ছাত্র নির্বাচন করুন", list(st_dict.keys()))
                    book_name = st.text_input("কিতাবের নাম (যেমন: তাফসীরে ইবনে কাসীর) *")
                    
                    if st.form_submit_button("✅ কিতাব ইস্যু করুন", use_container_width=True, type="primary"):
                        st_id = st_dict[sel_st]
                        if book_name:
                            try:
                                cur.execute("""
                                    INSERT INTO inventory (tenant_id, item_type, item_name, student_id, issue_date, status) 
                                    VALUES (%s, %s, %s, %s, %s, %s)
                                """, (tenant_id, 'Book', book_name, st_id, datetime.now().date(), 'Issued'))
                                conn.commit()
                                st.success(f"✅ '{book_name}' কিতাবটি সফলভাবে ইস্যু করা হয়েছে!")
                                st.rerun()
                            except Exception as e:
                                conn.rollback()
                                st.error(f"ইস্যু এরর: {e}")
                        else:
                            st.warning("⚠️ দয়া করে কিতাবের নাম লিখুন।")
            else:
                st.info("📌 আপনার মাদরাসায় কোনো অ্যাক্টিভ ছাত্র পাওয়া যায়নি।")

        with col2:
            st.subheader("বর্তমান ইস্যুকৃত কিতাবের তালিকা")
            try:
                cur.execute('''
                    SELECT i.id, s.name, s.class_name, i.item_name, i.issue_date
                    FROM inventory i
                    JOIN students s ON i.student_id = s.id
                    WHERE i.item_type = 'Book' AND i.status = 'Issued' AND i.tenant_id = %s
                    ORDER BY i.issue_date DESC
                ''', (tenant_id,))
                issued_books = cur.fetchall()
                
                if issued_books:
                    for row in issued_books:
                        c_id, c_name, c_cls, c_book, c_date = row[0], row[1], row[2], row[3], row[4]
                        with st.expander(f"📖 {c_book} - {c_name} (শ্রেণী: {c_cls})"):
                            st.write(f"**ইস্যুর তারিখ:** {c_date}")
                            if st.button("✅ কিতাব ফেরত নেওয়া হয়েছে", key=f"ret_book_{c_id}", use_container_width=True):
                                cur.execute("UPDATE inventory SET status = 'Returned' WHERE id = %s AND tenant_id = %s", (c_id, tenant_id))
                                conn.commit()
                                st.success("কিতাবটি লাইব্রেরিতে সফলভাবে ফেরত নেওয়া হয়েছে!")
                                st.rerun()
                else:
                    st.info("📌 বর্তমানে লাইব্রেরি থেকে কোনো কিতাব ইস্যু করা নেই।")
            except Exception as e:
                conn.rollback()
                st.error(f"কিতাবের তালিকা লোড এরর: {e}")

    # ==========================================
    # --- ট্যাব ২: হোস্টেল সিট ম্যানেজমেন্ট ---
    # ==========================================
    with tab_hostel:
        col_h1, col_h2 = st.columns([1, 1.5])
        with col_h1:
            st.subheader("সিট বরাদ্দ করুন")
            if students:
                with st.form("hostel_assign_form", clear_on_submit=True):
                    sel_st_h = st.selectbox("ছাত্র নির্বাচন করুন", list(st_dict.keys()))
                    room_no = st.text_input("রুম বা সিট নম্বর (যেমন: Room-302, Seat-A) *")
                    
                    if st.form_submit_button("✅ সিট বরাদ্দ করুন", use_container_width=True, type="primary"):
                        st_id = st_dict[sel_st_h]
                        if room_no:
                            try:
                                # --- ডাবল বুকিং চেক করার লজিক (SaaS Security সহ) ---
                                cur.execute("SELECT student_id FROM inventory WHERE item_type = 'Seat' AND item_name = %s AND status = 'Occupied' AND tenant_id = %s", (room_no, tenant_id))
                                is_booked = cur.fetchone()
                                
                                if is_booked:
                                    st.error(f"⚠️ দুঃখিত! '{room_no}' সিটটি ইতিমধ্যে অন্য একজন ছাত্রের জন্য বরাদ্দ করা আছে। সিট বাতিল না করা পর্যন্ত এটি অন্য কাউকে দেওয়া যাবে না।")
                                else:
                                    cur.execute("""
                                        INSERT INTO inventory (tenant_id, item_type, item_name, student_id, issue_date, status) 
                                        VALUES (%s, %s, %s, %s, %s, %s)
                                    """, (tenant_id, 'Seat', room_no, st_id, datetime.now().date(), 'Occupied'))
                                    conn.commit()
                                    st.success(f"🎉 সিট {room_no} সফলভাবে বরাদ্দ করা হয়েছে!")
                                    st.rerun()
                            except Exception as e:
                                conn.rollback()
                                st.error(f"সিট বরাদ্দ এরর: {e}")
                        else:
                            st.warning("⚠️ রুম/সিট নম্বর লিখতে হবে।")
            else:
                st.info("📌 কোনো ছাত্র পাওয়া যায়নি।")

        with col_h2:
            st.subheader("হোস্টেলে অবস্থানরত ছাত্রদের তালিকা")
            try:
                cur.execute('''
                    SELECT i.id, s.name, s.class_name, i.item_name, s.mobile_no
                    FROM inventory i
                    JOIN students s ON i.student_id = s.id
                    WHERE i.item_type = 'Seat' AND i.status = 'Occupied' AND i.tenant_id = %s
                    ORDER BY i.item_name ASC
                ''', (tenant_id,))
                occupied_seats = cur.fetchall()
                
                if occupied_seats:
                    for row in occupied_seats:
                        c_id, c_name, c_cls, c_room, c_mob = row[0], row[1], row[2], row[3], row[4]
                        c1, c2 = st.columns([3, 1])
                        with c1:
                            st.markdown(f"🛏️ **{c_room}** | {c_name} ({c_cls})<br>📞 মোবাইল: {c_mob}", unsafe_allow_html=True)
                        with c2:
                            if st.button("❌ সিট বাতিল", key=f"vacate_seat_{c_id}"):
                                cur.execute("UPDATE inventory SET status = 'Vacated' WHERE id = %s AND tenant_id = %s", (c_id, tenant_id))
                                conn.commit()
                                st.success("ছাত্রের সিটটি বাতিল করা হয়েছে!")
                                st.rerun()
                        st.divider()
                else:
                    st.info("📌 বর্তমানে হোস্টেলে কোনো সিট বরাদ্দ নেই।")
            except Exception as e:
                conn.rollback()
                st.error(f"হোস্টেল তালিকা লোড এরর: {e}")

    cur.close()