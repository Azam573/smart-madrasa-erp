import streamlit as st
import pandas as pd
from database import get_connection
from datetime import datetime
import base64
from io import BytesIO
from PIL import Image

def image_to_base64(uploaded_file):
    if uploaded_file is not None:
        try:
            img = Image.open(uploaded_file)
            img.thumbnail((300, 300))
            buffered = BytesIO()
            img.save(buffered, format="PNG")
            return base64.b64encode(buffered.getvalue()).decode()
        except Exception as e:
            return None
    return None

def show_hr():
    st.title("👥 শিক্ষক ও স্টাফ ম্যানেজমেন্ট (Advanced HR)")
    st.markdown("---")
    
    tenant_id = st.session_state.get('tenant_id', 1)
    
    tab_list, tab_entry, tab_att, tab_payroll, tab_report = st.tabs([
        "📋 স্টাফ তালিকা", "➕ নতুন নিয়োগ/এডিট", "📅 হাজিরা", "💰 বেতন ও অগ্রিম", "📊 বকেয়া রিপোর্ট"
    ])
    
    conn = get_connection()
    if not conn:
        st.error("ডাটাবেস কানেকশন এরর!")
        return
        
    conn.rollback()
    cur = conn.cursor()

    # --- ডাটা সংগ্রহ (স্ট্যাটাস সহ) ---
    try:
        cur.execute("SELECT id, name, designation, mobile_no, base_salary, photo, join_date, COALESCE(status, 'Active') FROM staff WHERE tenant_id = %s ORDER BY name", (tenant_id,))
        staff_data = cur.fetchall()
        staff_dict = {f"{r[1]} ({r[2]}) - {r[7]}": r for r in staff_data}
        
        # শুধু যারা বর্তমানে কর্মরত আছেন (Active) তাদের তালিকা ফিল্টার করা
        active_staff = [s for s in staff_data if s[7] == 'Active']
    except Exception as e:
        conn.rollback()
        st.error(f"স্টাফ ডাটা লোড এরর: {e}")
        staff_data = []
        staff_dict = {}
        active_staff = []

    # ==========================================
    # --- ট্যাব ১: স্টাফ তালিকা ---
    # ==========================================
    with tab_list:
        st.subheader("মাদরাসার সকল শিক্ষক ও স্টাফ")
        if staff_data:
            for s in staff_data:
                # যারা চলে গেছেন তাদের নামের পাশে 🔴 (সাবেক) লেখা থাকবে
                status_icon = "🟢" if s[7] == 'Active' else "🔴 (সাবেক/পদত্যাগী)"
                with st.expander(f"👤 {s[1]} - {s[2]} | {status_icon}"):
                    c1, c2 = st.columns([1, 3])
                    with c1:
                        if s[5]: 
                            st.image(f"data:image/png;base64,{s[5]}", width=120)
                        else:
                            st.write("🖼️ ছবি নেই")
                    with c2:
                        st.write(f"**বর্তমান অবস্থা:** {s[7]}")
                        st.write(f"**মোবাইল:** {s[3]}")
                        st.write(f"**নির্ধারিত বেতন:** {s[4]:,.0f} ৳")
                        st.write(f"**যোগদান:** {s[6]}")
        else:
            st.info("📌 কোনো স্টাফ ডাটা পাওয়া যায়নি।")

    # ==========================================
    # --- ট্যাব ২: নতুন নিয়োগ ও এডিট ---
    # ==========================================
    with tab_entry:
        mode = st.radio("মোড নির্বাচন করুন", ["নতুন নিয়োগ", "তথ্য এডিট করুন"], horizontal=True)
        edit_staff_id = None
        default_val = {"name": "", "desig": "সহকারী শিক্ষক", "mob": "", "sal": 0, "photo": None, "status": "Active"}
        
        if mode == "তথ্য এডিট করুন":
            sel_edit = st.selectbox("কার তথ্য পরিবর্তন করবেন?", ["নির্বাচন করুন"] + list(staff_dict.keys()))
            if sel_edit != "নির্বাচন করুন":
                s_info = staff_dict[sel_edit]
                edit_staff_id = s_info[0]
                default_val = {"name": s_info[1], "desig": s_info[2], "mob": s_info[3], "sal": int(s_info[4]), "photo": s_info[5], "status": s_info[7]}

        with st.form("staff_form", clear_on_submit=True):
            f_name = st.text_input("পুরো নাম *", value=default_val["name"])
            f_desig = st.selectbox("পদবি", ["অধ্যক্ষ / মুহতামিম", "সিনিয়র শিক্ষক", "সহকারী শিক্ষক", "অফিস স্টাফ", "খাদেম / অন্যান্য"], 
                                 index=["অধ্যক্ষ / মুহতামিম", "সিনিয়র শিক্ষক", "সহকারী শিক্ষক", "অফিস স্টাফ", "খাদেম / অন্যান্য"].index(default_val["desig"]))
            f_mob = st.text_input("মোবাইল নম্বর *", value=default_val["mob"])
            f_sal = st.number_input("নির্ধারিত মাসিক বেতন (৳) *", value=default_val["sal"], min_value=0)
            
            f_status = st.selectbox("বর্তমান অবস্থা", ["Active", "Inactive (চলে গেছেন)"], index=0 if default_val["status"] == "Active" else 1)
            f_photo = st.file_uploader("ছবি আপলোড করুন (JPG/PNG)", type=['jpg', 'png'])
            
            if st.form_submit_button("💾 ডাটা সেভ করুন", use_container_width=True):
                if not f_name or not f_mob:
                    st.warning("⚠️ নাম এবং মোবাইল নম্বর দেওয়া আবশ্যক!")
                else:
                    try:
                        photo_b64 = image_to_base64(f_photo) if f_photo else default_val["photo"]
                        status_val = "Active" if f_status == "Active" else "Inactive"
                        
                        if mode == "নতুন নিয়োগ":
                            cur.execute("""
                                INSERT INTO staff (tenant_id, name, designation, mobile_no, base_salary, photo, join_date, status) 
                                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                            """, (tenant_id, f_name, f_desig, f_mob, f_sal, photo_b64, datetime.now().date(), status_val))
                            st.success("✅ নতুন নিয়োগ সফল হয়েছে!")
                        else:
                            cur.execute("""
                                UPDATE staff 
                                SET name=%s, designation=%s, mobile_no=%s, base_salary=%s, photo=%s, status=%s 
                                WHERE id=%s AND tenant_id=%s
                            """, (f_name, f_desig, f_mob, f_sal, photo_b64, status_val, edit_staff_id, tenant_id))
                            st.success("✅ তথ্য আপডেট করা হয়েছে!")
                        
                        conn.commit()
                        st.rerun()
                    except Exception as e:
                        conn.rollback()
                        st.error(f"সেভ এরর: {e}")

    # ==========================================
    # --- ট্যাব ৩: স্টাফ হাজিরা ---
    # ==========================================
    with tab_att:
        st.subheader("📋 আজকের স্টাফ হাজিরা")
        st.info("💡 যারা মাদরাসা থেকে চলে গেছেন (Inactive), তাদের নাম এই তালিকায় আসবে না।")
        if active_staff:
            today = datetime.now().date()
            with st.form("staff_att_form"):
                att_data = []
                for s in active_staff: 
                    s_id, name, desig = s[0], s[1], s[2]
                    c1, c2 = st.columns([2, 2])
                    c1.write(f"**{name}** ({desig})")
                    status = c2.radio("অবস্থা", ["Present", "Absent", "Leave"], horizontal=True, key=f"s_att_{s_id}")
                    att_data.append((s_id, status))
                
                if st.form_submit_button("✅ হাজিরা সেভ করুন", use_container_width=True):
                    try:
                        for s_id, status in att_data:
                            # আগে চেক করবে আজকের হাজিরা আছে কি না
                            cur.execute("SELECT id FROM staff_attendance WHERE staff_id=%s AND attendance_date=%s AND tenant_id=%s", (s_id, today, tenant_id))
                            exists = cur.fetchone()
                            if exists:
                                cur.execute("UPDATE staff_attendance SET status=%s WHERE id=%s", (status, exists[0]))
                            else:
                                cur.execute("INSERT INTO staff_attendance (tenant_id, staff_id, attendance_date, status) VALUES (%s, %s, %s, %s)", (tenant_id, s_id, today, status))
                        
                        conn.commit()
                        st.success("✅ আলহামদুলিল্লাহ! আজকের হাজিরা সফলভাবে সেভ হয়েছে!")
                    except Exception as e:
                        conn.rollback()
                        st.error(f"হাজিরা সেভ এরর: {e}")
        else:
            st.warning("বর্তমানে কোনো সক্রিয় (Active) স্টাফ নেই।")

    # ==========================================
    # --- ট্যাব ৪: বেতন ও অগ্রিম ---
    # ==========================================
    with tab_payroll:
        st.subheader("💸 বেতন ও অগ্রিম (Advance) প্রদান")
        if active_staff:
            active_staff_dict = {f"{s[1]} ({s[2]})": s for s in active_staff}
            
            c_p1, c_p2 = st.columns(2)
            sel_p_staff = c_p1.selectbox("শিক্ষক নির্বাচন করুন", list(active_staff_dict.keys()), key="p_st")
            pay_month = c_p2.selectbox("মাস", ["জানুয়ারি", "ফেব্রুয়ারি", "মার্চ", "এপ্রিল", "মে", "জুন", "জুলাই", "আগস্ট", "সেপ্টেম্বর", "অক্টোবর", "নভেম্বর", "ডিসেম্বর"], key="p_mo")
            
            s_id, s_name, s_desig, s_mob, base_sal, _, _, _ = active_staff_dict[sel_p_staff]
            
            try:
                cur.execute("SELECT SUM(paid_amount) FROM staff_salary WHERE staff_id = %s AND salary_month = %s AND tenant_id = %s", (s_id, pay_month, tenant_id))
                paid_sum = cur.fetchone()[0] or 0
                remaining = float(base_sal) - float(paid_sum)
                
                st.markdown(f"**নির্ধারিত বেতন:** {base_sal:,.0f} ৳ | **ইতিমধ্যে দেওয়া হয়েছে:** {paid_sum:,.0f} ৳")
                
                if remaining > 0:
                    st.error(f"💰 **বর্তমানে পাওনা আছে: {remaining:,.0f} ৳**")
                    default_pay = remaining
                elif remaining < 0:
                    st.success(f"💡 **তিনি ইতিমধ্যে {-remaining:,.0f} ৳ অগ্রিম নিয়েছেন।**")
                    default_pay = 0.0
                else:
                    st.success("✅ এই মাসের সম্পূর্ণ বেতন ক্লিয়ার।")
                    default_pay = 0.0
                
                with st.form("payment_form", clear_on_submit=True):
                    amount = st.number_input("আজ কত টাকা দিচ্ছেন? (৳)", value=float(default_pay), min_value=0.0)
                    
                    if st.form_submit_button("✅ পেমেন্ট সম্পন্ন করুন", use_container_width=True, type="primary"):
                        if amount > 0:
                            # ১. স্টাফ স্যালারি টেবিলে এন্ট্রি
                            cur.execute("INSERT INTO staff_salary (tenant_id, staff_id, salary_month, paid_amount, payment_date) VALUES (%s, %s, %s, %s, %s)",
                                        (tenant_id, s_id, pay_month, amount, datetime.now().date()))
                            
                            # ২. খরচের খাতায় অটোমেটিক লিংক (ম্যাজিক ফিচার)
                            exp_type = "অগ্রিম বেতন" if (remaining <= 0 or amount > remaining) else "শিক্ষক ও স্টাফ বেতন"
                            fund_src = "সাধারণ তহবিল (General Fund)"
                            recorder = st.session_state.get('username', 'Admin')
                            
                            cur.execute("""
                                INSERT INTO expenses (tenant_id, expense_date, fund_source, category, amount, description, recorded_by) 
                                VALUES (%s, %s, %s, %s, %s, %s, %s)
                            """, (tenant_id, datetime.now().date(), fund_src, "শিক্ষক ও স্টাফ বেতন", amount, f"{s_name} এর {pay_month} মাসের {exp_type}", recorder))
                            
                            conn.commit()
                            st.success(f"🎉 আলহামদুলিল্লাহ! {amount:,.0f} ৳ পেমেন্ট সফল হয়েছে এবং খরচের খাতায় যুক্ত হয়েছে!")
                            st.balloons()
                        else:
                            st.warning("⚠️ পেমেন্টের পরিমাণ ০ এর চেয়ে বেশি হতে হবে।")
            except Exception as e:
                conn.rollback()
                st.error(f"পেমেন্ট এরর: {e}")
        else:
            st.warning("বর্তমানে কোনো সক্রিয় (Active) স্টাফ নেই।")

    # ==========================================
    # --- ট্যাব ৫: বকেয়া ও অগ্রিম রিপোর্ট ---
    # ==========================================
    with tab_report:
        st.subheader("📊 বকেয়া এবং অগ্রিম বেতনের তালিকা")
        target_m = st.selectbox("কোন মাসের রিপোর্ট দেখবেন?", ["জানুয়ারি", "ফেব্রুয়ারি", "মার্চ", "এপ্রিল", "মে", "জুন", "জুলাই", "আগস্ট", "সেপ্টেম্বর", "অক্টোবর", "নভেম্বর", "ডিসেম্বর"], index=datetime.now().month-1)
        
        try:
            # SaaS Security Double check on JOIN
            cur.execute("""
                SELECT s.name, s.designation, s.base_salary, COALESCE(SUM(ss.paid_amount), 0) as paid
                FROM staff s
                LEFT JOIN staff_salary ss ON s.id = ss.staff_id AND ss.salary_month = %s AND ss.tenant_id = %s
                WHERE s.tenant_id = %s
                GROUP BY s.id, s.name, s.designation, s.base_salary
            """, (target_m, tenant_id, tenant_id))
            report_data = cur.fetchall()
            
            if report_data:
                due_list = []
                adv_list = []
                
                for r in report_data:
                    diff = r[2] - r[3]
                    if diff > 0:
                        due_list.append([r[0], r[1], r[2], r[3], diff])
                    elif diff < 0:
                        adv_list.append([r[0], r[1], r[2], r[3], abs(diff)])
                
                col_rep1, col_rep2 = st.columns(2)
                with col_rep1:
                    st.markdown("### 🔴 বকেয়া তালিকা (পাওনাদার)")
                    if due_list:
                        df_due = pd.DataFrame(due_list, columns=["নাম", "পদবি", "বেতন", "পরিশোধিত", "বকেয়া"])
                        st.dataframe(df_due, hide_index=True)
                        st.error(f"মোট বকেয়া: {df_due['বকেয়া'].sum():,.0f} ৳")
                    else:
                        st.success("✅ কারো বকেয়া নেই।")
                        
                with col_rep2:
                    st.markdown("### 🔵 অগ্রিম তালিকা (অ্যাডভান্স)")
                    if adv_list:
                        df_adv = pd.DataFrame(adv_list, columns=["নাম", "পদবি", "বেতন", "পরিশোধিত", "অগ্রিম নিয়েছেন"])
                        st.dataframe(df_adv, hide_index=True)
                        st.info(f"মোট অগ্রিম প্রদান: {df_adv['অগ্রিম নিয়েছেন'].sum():,.0f} ৳")
                    else:
                        st.write("📌 কেউ অগ্রিম নেননি।")
            else:
                st.info("কোনো ডাটা পাওয়া যায়নি।")
        except Exception as e:
            conn.rollback()
            st.error(f"রিপোর্ট এরর: {e}")

    cur.close()