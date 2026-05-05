import streamlit as st
import pandas as pd
from database import get_connection
from datetime import datetime
import base64
from io import BytesIO
from PIL import Image
import datetime as dt # Added this import

def image_to_base64(uploaded_file):
    if uploaded_file is not None:
        try:
            img = Image.open(uploaded_file)
            img.thumbnail((300, 300))
            buffered = BytesIO()
            img.save(buffered, format="PNG")
            return base64.b64encode(buffered.getvalue()).decode()
        except Exception as e:
            st.error(f"ছবি প্রসেস করতে সমস্যা হয়েছে: {e}")
            return None
    return None

def show_admission():
    st.title("🎓 ছাত্র ভর্তি ও প্রোফাইল ম্যানেজমেন্ট")
    
    tenant_id = st.session_state.get('tenant_id', 1)
    
    tab_list, tab_entry = st.tabs(["📋 ছাত্র তালিকা ও প্রোফাইল", "📝 নতুন ভর্তি / প্রোফাইল এডিট"])
    
    conn = get_connection()
    if not conn:
        st.error("ডাটাবেস কানেকশন এরর!")
        return
        
    conn.rollback()
    cur = conn.cursor()

    # ডাটাবেস থেকে ডায়নামিক ক্লাসের তালিকা আনা
    try:
        cur.execute("SELECT class_name FROM classes WHERE tenant_id = %s AND status = 'Active'", (tenant_id,))
        dynamic_classes = [row[0] for row in cur.fetchall()]
        if not dynamic_classes:
            dynamic_classes = ["প্লে (Play)", "নার্সারি (Nursery)", "১ম শ্রেণি", "২য় শ্রেণি", "৩য় শ্রেণি", "৪র্থ শ্রেণি","৫ম শ্রেণি", "৬ষ্ঠ শ্রেণি", "৭ম শ্রেণি","৮ম শ্রেণি", "৯ম শ্রেণি","১০ম শ্রেণি"] # ডিফল্ট
    except Exception:
        dynamic_classes = ["প্লে (Play)", "নার্সারি (Nursery)", "১ম শ্রেণি" "২য় শ্রেণি", "৩য় শ্রেণি", "৪র্থ শ্রেণি","৫ম শ্রেণি", "৬ষ্ঠ শ্রেণি", "৭ম শ্রেণি","৮ম শ্রেণি", "৯ম শ্রেণি","১০ম শ্রেণি"]

    try:
        # ডাটাবেস থেকে শুধুমাত্র এই মাদরাসার (tenant_id) ছাত্রদের ডাটা সংগ্রহ
        cur.execute("""
            SELECT id, name, father_name, class_name, roll_no, mobile_no, monthly_fee, 
                   photo, COALESCE(status, 'Active'), blood_group, dob, mother_name, address 
            FROM students 
            WHERE tenant_id = %s 
            ORDER BY class_name, roll_no
        """, (tenant_id,))
        students_data = cur.fetchall()
        
        student_dict = {f"{r[1]} (রোল: {r[4]}, শ্রেণী: {r[3]})": r for r in students_data}
    except Exception as e:
        st.error(f"ডাটা লোড এরর: {e}")
        students_data = []
        student_dict = {}

    # ==========================================
    # --- ট্যাব ১: ছাত্র তালিকা ---
    # ==========================================
    with tab_list:
        st.subheader("মাদরাসার সকল ছাত্রের তালিকা")
        
        view_filter = st.radio("কাদের তালিকা দেখতে চান?", ["শুধু রানিং ছাত্র (Active)", "প্রাক্তন/চলে যাওয়া ছাত্র (Inactive)", "সবাই"], horizontal=True)
        
        filtered_students = []
        for s in students_data:
            if view_filter == "শুধু রানিং ছাত্র (Active)" and s[8] == 'Active':
                filtered_students.append(s)
            elif view_filter == "প্রাক্তন/চলে যাওয়া ছাত্র (Inactive)" and s[8] != 'Active':
                filtered_students.append(s)
            elif view_filter == "সবাই":
                filtered_students.append(s)

        if filtered_students:
            for s in filtered_students:
                status_icon = "🟢" if s[8] == 'Active' else "🔴 (সাবেক)"
                with st.expander(f"🎓 {s[1]} - শ্রেণী: {s[3]} (রোল: {s[4]}) | {status_icon}"):
                    c1, c2, c3 = st.columns([1, 2, 2])
                    with c1:
                        if s[7]: 
                            st.image(f"data:image/png;base64,{s[7]}", width=120)
                        else:
                            st.write("🖼️ ছবি নেই")
                    with c2:
                        st.write(f"**পিতার নাম:** {s[2]}")
                        st.write(f"**মাতার নাম:** {s[11] or 'দেওয়া হয়নি'}")
                        st.write(f"**মোবাইল:** {s[5]}")
                        st.write(f"**ঠিকানা:** {s[12] or 'দেওয়া হয়নি'}")
                    with c3:
                        st.write(f"**জন্ম তারিখ:** {s[10] or 'দেওয়া হয়নি'}")
                        st.write(f"**রক্তের গ্রুপ:** {s[9] or 'জানা নেই'}")
                        st.write(f"**মাসিক ফি:** {s[6]:,.0f} ৳")
                        st.write(f"**বর্তমান অবস্থা:** {s[8]}")
        else:
            st.info("এই ক্যাটাগরিতে কোনো ছাত্র পাওয়া যায়নি।")

    # ==========================================
    # --- ট্যাব ২: নতুন ভর্তি ও এডিট ---
    # ==========================================
    with tab_entry:
        mode = st.radio("কাজ নির্বাচন করুন", ["নতুন ভর্তি", "তথ্য এডিট করুন"], horizontal=True)
        
        edit_st_id = None
        default_val = {
            "name": "", "fname": "", "mname": "", "cls": dynamic_classes[0], 
            "roll": 1, "mob": "", "fee": 500, "photo": None, "status": "Active",
            "bg": "জানা নেই", "dob": datetime.now().date(), "address": ""
        }
        
        if mode == "তথ্য এডিট করুন":
            sel_edit = st.selectbox("কার তথ্য পরিবর্তন করবেন?", ["নির্বাচন করুন"] + list(student_dict.keys()))
            if sel_edit != "নির্বাচন করুন":
                s_info = student_dict[sel_edit]
                edit_st_id = s_info[0]
                default_val = {
                    "name": s_info[1], "fname": s_info[2], "cls": s_info[3], 
                    "roll": int(s_info[4]) if s_info[4] else 1, "mob": s_info[5], 
                    "fee": int(s_info[6]) if s_info[6] else 0, "photo": s_info[7], 
                    "status": s_info[8], "bg": s_info[9] or "জানা নেই", 
                    "dob": s_info[10] or datetime.now().date(), 
                    "mname": s_info[11] or "", "address": s_info[12] or ""
                }

        with st.form("admission_form", clear_on_submit=True):
            st.subheader("ছাত্রের ব্যক্তিগত ও একাডেমিক তথ্য")
            
            col1, col2, col3 = st.columns(3)
            
            with col1:
                f_name = st.text_input("ছাত্রের পুরো নাম *", value=default_val["name"])
                # Updated st.date_input with min_value and max_value
                f_dob = st.date_input("জন্ম তারিখ", value=default_val["dob"], min_value=dt.date(1990, 1, 1), max_value=dt.date.today())
                f_bg = st.selectbox("রক্তের গ্রুপ", ["জানা নেই", "A+", "A-", "B+", "B-", "AB+", "AB-", "O+", "O-"], index=["জানা নেই", "A+", "A-", "B+", "B-", "AB+", "AB-", "O+", "O-"].index(default_val["bg"]))
                
            with col2:
                f_fname = st.text_input("পিতার নাম *", value=default_val["fname"])
                f_mname = st.text_input("মাতার নাম", value=default_val["mname"])
                f_mob = st.text_input("মোবাইল নম্বর *", value=default_val["mob"])
                
            with col3:
                cls_idx = dynamic_classes.index(default_val["cls"]) if default_val["cls"] in dynamic_classes else 0
                f_cls = st.selectbox("শ্রেণী/বিভাগ *", dynamic_classes, index=cls_idx)
                f_roll = st.number_input("রোল নম্বর *", min_value=1, value=default_val["roll"])
                f_fee = st.number_input("মাসিক ফি (৳)", min_value=0, value=default_val["fee"])

            f_address = st.text_input("পূর্ণাঙ্গ ঠিকানা", value=default_val["address"])
            
            c_stat, c_pic = st.columns(2)
            f_status = c_stat.selectbox("বর্তমান অবস্থা", ["Active (রানিং)", "Inactive (চলে গেছে)"], index=0 if default_val["status"] == "Active" else 1)
            f_photo = c_pic.file_uploader("ছবি আপলোড (JPG/PNG)", type=['jpg', 'png'])
            
            submit = st.form_submit_button("💾 ডাটা সেভ করুন", use_container_width=True)
            
            if submit:
                if not f_name or not f_mob or not f_cls:
                    st.warning("⚠️ নাম, শ্রেণী এবং মোবাইল নম্বর দেওয়া আবশ্যক!")
                else:
                    try:
                        photo_b64 = image_to_base64(f_photo) if f_photo else default_val["photo"]
                        status_val = "Active" if "Active" in f_status else "Inactive"
                        
                        if mode == "নতুন ভর্তি":
                            cur.execute("""
                                INSERT INTO students (tenant_id, name, father_name, mother_name, class_name, roll_no, mobile_no, monthly_fee, dob, blood_group, address, admission_date, photo, status) 
                                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                            """, (tenant_id, f_name, f_fname, f_mname, f_cls, f_roll, f_mob, f_fee, f_dob, f_bg, f_address, datetime.now().date(), photo_b64, status_val))
                            st.success(f"🎉 আলহামদুলিল্লাহ! {f_name}-কে সফলভাবে ভর্তি করা হয়েছে।")
                        else:
                            cur.execute("""
                                UPDATE students 
                                SET name=%s, father_name=%s, mother_name=%s, class_name=%s, roll_no=%s, mobile_no=%s, monthly_fee=%s, dob=%s, blood_group=%s, address=%s, photo=%s, status=%s 
                                WHERE id=%s AND tenant_id=%s
                            """, (f_name, f_fname, f_mname, f_cls, f_roll, f_mob, f_fee, f_dob, f_bg, f_address, photo_b64, status_val, edit_st_id, tenant_id))
                            st.success("✅ তথ্য সফলভাবে আপডেট করা হয়েছে!")
                        
                        conn.commit()
                        st.rerun()
                    except Exception as e:
                        conn.rollback()
                        st.error(f"ডাটাবেসে সেভ করতে সমস্যা হয়েছে: {e}")

    cur.close()
