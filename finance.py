import streamlit as st
import pandas as pd
from database import get_connection
from datetime import datetime
from utils import send_sms  # <-- SaaS সাপোর্টেড SMS মডিউল

def show_finance():
    st.title("💰 ছাত্র বেতন ও ফি কালেকশন")
    st.markdown("---")
    
    tenant_id = st.session_state.get('tenant_id', 1)
    institute_name = st.session_state.get('madrasa_name', 'স্মার্ট মাদরাসা')
    
    tab_collect, tab_receipt, tab_due = st.tabs(["💵 ফি গ্রহণ (Collection)", "🧾 মানি রিসিট ও ইতিহাস", "⚠️ বকেয়া রিপোর্ট"])
    
    conn = get_connection()
    if not conn:
        st.error("ডাটাবেস কানেকশন এরর!")
        return
        
    conn.rollback() # আগের কোনো আটকে থাকা ট্রানজেকশন ক্লিয়ার করার জন্য
    cur = conn.cursor()

    try:
        # শুধুমাত্র এই মাদরাসার (tenant_id) অ্যাক্টিভ ছাত্রদের লিস্ট আনা হলো
        cur.execute("SELECT id, name, class_name, roll_no, COALESCE(monthly_fee, 0), mobile_no FROM students WHERE COALESCE(status, 'Active') = 'Active' AND tenant_id = %s ORDER BY class_name, roll_no", (tenant_id,))
        students = cur.fetchall()
        st_dict = {f"{r[1]} (রোল: {r[3]}, শ্রেণী: {r[2]})": r for r in students}
    except Exception as e:
        conn.rollback()
        st.error(f"ছাত্র লোড এরর: {e}")
        st_dict = {}

    # ==========================================
    # --- ট্যাব ১: ফি কালেকশন ---
    # ==========================================
    with tab_collect:
        if st_dict:
            col_sel1, col_sel2 = st.columns(2)
            sel_st = col_sel1.selectbox("ছাত্র নির্বাচন করুন", list(st_dict.keys()), key="coll_st")
            fee_month = col_sel2.selectbox("মাসের নাম", ["জানুয়ারি", "ফেব্রুয়ারি", "মার্চ", "এপ্রিল", "মে", "জুন", "জুলাই", "আগস্ট", "সেপ্টেম্বর", "অক্টোবর", "নভেম্বর", "ডিসেম্বর"])
            
            s_id, s_name, s_cls, s_roll, fee_amt, s_mob = st_dict[sel_st]
            
            try:
                # ডাটাবেস থেকে রিয়েল-টাইম পেমেন্ট চেক করা
                cur.execute("SELECT SUM(amount_paid) FROM fees WHERE student_id = %s AND fee_month = %s AND tenant_id = %s", (s_id, fee_month, tenant_id))
                paid_already = cur.fetchone()[0] or 0
                due_amt = float(fee_amt) - float(paid_already)

                st.markdown("### 📊 পেমেন্ট স্ট্যাটাস")
                col1, col2 = st.columns(2)
                col1.info(f"📌 নির্ধারিত মাসিক ফি: **{fee_amt:,.0f} ৳**")
                col2.warning(f"📌 ইতিমধ্যে জমা হয়েছে: **{paid_already:,.0f} ৳**")
                
                if due_amt > 0:
                    st.error(f"⚠️ বর্তমান বকেয়া: **{due_amt:,.0f} ৳**")
                elif due_amt < 0:
                    st.success(f"💡 অতিরিক্ত জমা (অ্যাডভান্স): **{-due_amt:,.0f} ৳**")
                else:
                    st.success("✅ আলহামদুলিল্লাহ! এই মাসের সম্পূর্ণ ফি ক্লিয়ার।")

                with st.form("fee_form", clear_on_submit=True):
                    st.subheader("নতুন পেমেন্ট এন্ট্রি")
                    pay_amt = st.number_input("জমা দেওয়ার পরিমাণ (৳) *", value=float(due_amt) if due_amt > 0 else 0.0, min_value=0.0)
                    
                    pay_method = st.radio("পেমেন্টের মাধ্যম", ["নগদ গ্রহণ (ছাত্র দিচ্ছে)", "মাদরাসার ফান্ড থেকে পরিশোধ (গরিব ছাত্রদের জন্য)"], horizontal=True)
                    
                    selected_fund = None
                    if pay_method == "মাদরাসার ফান্ড থেকে পরিশোধ (গরিব ছাত্রদের জন্য)":
                        selected_fund = st.selectbox("কোন ফান্ড থেকে এই ছাত্রের ফি দেওয়া হবে?", ["যাকাত ফান্ড (Zakat)", "লিল্লাহ বোর্ডিং (Lillah Boarding)"])

                    send_sms_checkbox = st.checkbox("📲 অভিভাবককে পেমেন্ট কনফার্মেশন SMS পাঠান", value=True)

                    if st.form_submit_button("✅ ফি জমা করুন", use_container_width=True, type="primary"):
                        if pay_amt <= 0:
                            st.warning("⚠️ জমা দেওয়ার পরিমাণ ০ এর বেশি হতে হবে!")
                        else:
                            try:
                                # ১. ছাত্রের ফি জমা সেভ করা
                                cur.execute("INSERT INTO fees (student_id, fee_month, amount_paid, payment_date, tenant_id) VALUES (%s, %s, %s, %s, %s)",
                                            (s_id, fee_month, pay_amt, datetime.now().date(), tenant_id))
                                
                                # ২. যদি ফান্ড থেকে হয়, তবে খরচের খাতায় এন্ট্রি দেওয়া
                                if selected_fund:
                                    desc = f"{s_name} (রোল: {s_roll}) এর {fee_month} মাসের ফি বাবদ প্রদান"
                                    recorder = st.session_state.get('username', 'Admin')
                                    cur.execute("INSERT INTO expenses (expense_date, fund_source, category, amount, description, recorded_by, tenant_id) VALUES (%s, %s, %s, %s, %s, %s, %s)",
                                                (datetime.now().date(), selected_fund, "ছাত্রদের ফি প্রদান (যাকাত/লিল্লাহ থেকে)", pay_amt, desc, recorder, tenant_id))
                                
                                conn.commit()
                                st.success(f"🎉 আলহামদুলিল্লাহ! {pay_amt:,.0f} ৳ সফলভাবে জমা হয়েছে!")
                                st.balloons()
                                
                                # ৩. SMS পাঠানো
                                if send_sms_checkbox and s_mob:
                                    msg = f"আলহামদুলিল্লাহ! আপনার সন্তান {s_name}-এর {fee_month} মাসের ফি বাবদ {pay_amt:,.0f}৳ জমা হয়েছে। - {institute_name}"
                                    success, response_msg = send_sms(tenant_id, s_mob, msg)
                                    if success:
                                        st.toast("✅ SMS সফলভাবে পাঠানো হয়েছে!")
                                    else:
                                        st.error(f"SMS Error: {response_msg}")
                            except Exception as e:
                                conn.rollback()
                                st.error(f"ডাটাবেস সেভ এরর: {e}")
                                
                if st.button("🔄 পেমেন্ট স্ট্যাটাস রিফ্রেশ করুন"):
                    st.rerun()
            except Exception as e:
                conn.rollback()
                st.error(f"ফি ডাটা লোড এরর: {e}")
        else:
            st.warning("⚠️ আপনার মাদরাসায় কোনো অ্যাক্টিভ ছাত্র পাওয়া যায়নি।")

    # ==========================================
    # --- ট্যাব ২: মানি রিসিট ও ইতিহাস ---
    # ==========================================
    with tab_receipt:
        st.subheader("পেমেন্ট ইতিহাস ও রিসিট প্রিন্ট")
        if st_dict:
            sel_rec_st = st.selectbox("কার পেমেন্ট ইতিহাস দেখতে চান? (ছাত্র নির্বাচন করুন)", list(st_dict.keys()), key="rec_st")
            r_id, r_name, r_cls, r_roll, _, _ = st_dict[sel_rec_st]
            
            try:
                cur.execute("SELECT id, fee_month, amount_paid, payment_date FROM fees WHERE student_id = %s AND tenant_id = %s ORDER BY id DESC", (r_id, tenant_id))
                history = cur.fetchall()
                
                if history:
                    df_hist = pd.DataFrame(history, columns=["রিসিট নং", "মাসের নাম", "জমা (৳)", "তারিখ"])
                    st.dataframe(df_hist, use_container_width=True, hide_index=True)
                    
                    st.markdown("---")
                    receipt_to_print = st.selectbox("কোন রিসিটটি প্রিন্ট করবেন?", [f"রিসিট নং: {h[0]} | মাস: {h[1]} | ৳ {h[2]}" for h in history])
                    
                    if st.button("🖨️ প্রিন্ট রিসিট (Print Receipt)", use_container_width=True):
                        rec_details = receipt_to_print.split(" | ")
                        
                        # প্রিন্ট ডিজাইন
                        st.markdown(f"""
                        <div style='border: 2px dashed #4CAF50; padding: 25px; border-radius: 12px; text-align: center; background-color: #fdfdfd; color: black; max-width: 400px; margin: auto;'>
                            <h2 style='color: #4CAF50; margin-bottom: 5px; font-size: 24px;'>{institute_name}</h2>
                            <p style='color: gray; margin-top: 0; font-size: 14px;'>মানি রিসিট (Money Receipt)</p>
                            <hr style='border-top: 1px dashed #ccc;'>
                            
                            <p align='left' style='font-size: 16px;'>
                                <b>ছাত্রের নাম:</b> {r_name} <br>
                                <b>শ্রেণী:</b> {r_cls} | <b>রোল:</b> {r_roll}
                            </p>
                            
                            <div style='background: #e8f5e9; padding: 10px; border-radius: 8px; margin: 15px 0;'>
                                <h3 align='center' style='color: #2E7D32; margin: 0;'>জমা: {rec_details[2]}</h3>
                            </div>
                            
                            <p align='left' style='font-size: 15px;'>
                                <b>মাসের নাম:</b> {rec_details[1]} <br>
                                <b>{rec_details[0]}</b> <br>
                                <b>তারিখ:</b> {datetime.now().strftime('%d/%m/%Y')}
                            </p>
                            <br><br>
                            <p align='right' style='margin-bottom: 0;'>___________________<br><span style='font-size: 13px; color: gray;'>কর্তৃপক্ষের স্বাক্ষর</span></p>
                        </div>
                        """, unsafe_allow_html=True)
                        st.info("🖨️ প্রিন্ট করতে **Ctrl + P** চাপুন।")
                else:
                    st.warning("⚠️ এই ছাত্রের কোনো পেমেন্ট রেকর্ড পাওয়া যায়নি।")
            except Exception as e:
                conn.rollback()
                st.error(f"ইতিহাস লোড এরর: {e}")

    # ==========================================
    # --- ট্যাব ৩: বকেয়া রিপোর্ট ও SMS ---
    # ==========================================
    with tab_due:
        st.subheader("মাসিক বকেয়া রিপোর্ট ও SMS রিমাইন্ডার")
        rep_month = st.selectbox("কোন মাসের রিপোর্ট দেখতে চান?", ["জানুয়ারি", "ফেব্রুয়ারি", "মার্চ", "এপ্রিল", "মে", "জুন", "জুলাই", "আগস্ট", "সেপ্টেম্বর", "অক্টোবর", "নভেম্বর", "ডিসেম্বর"], key="due_rep_mo")
        
        try:
            # SaaS Security Fix: Added f.tenant_id = %s in the ON clause
            cur.execute("""
                SELECT s.name, s.class_name, s.roll_no, COALESCE(s.monthly_fee, 0), 
                       COALESCE(SUM(f.amount_paid), 0) as paid, s.mobile_no
                FROM students s
                LEFT JOIN fees f ON s.id = f.student_id AND f.fee_month = %s AND f.tenant_id = %s
                WHERE COALESCE(s.status, 'Active') = 'Active' AND s.tenant_id = %s
                GROUP BY s.id, s.name, s.class_name, s.roll_no, s.monthly_fee, s.mobile_no
            """, (rep_month, tenant_id, tenant_id))
            due_data = cur.fetchall()

            if due_data:
                res = []
                for d in due_data:
                    due = float(d[3]) - float(d[4])
                    if due > 0:
                        res.append({"নাম": d[0], "শ্রেণী": d[1], "রোল": d[2], "বকেয়া": due, "মোবাইল": d[5]})
                
                if res:
                    st.error(f"⚠️ {rep_month} মাসে মোট {len(res)} জন ছাত্রের ফি বকেয়া আছে।")
                    df_due = pd.DataFrame(res)
                    st.table(df_due[["নাম", "শ্রেণী", "রোল", "বকেয়া"]])
                    
                    st.markdown("---")
                    st.markdown("### 📩 বকেয়া রিমাইন্ডার SMS")
                    
                    selected_st_sms = st.selectbox("কার অভিভাবককে বকেয়া SMS পাঠাবেন?", [f"{r['নাম']} (রোল: {r['রোল']})" for r in res])
                    
                    col_sms1, col_sms2 = st.columns(2)
                    
                    with col_sms1:
                        if st.button("📩 নির্বাচিত ছাত্রকে SMS দিন", use_container_width=True):
                            with st.spinner("SMS পাঠানো হচ্ছে..."):
                                for r in res:
                                    if f"{r['নাম']} (রোল: {r['রোল']})" == selected_st_sms:
                                        if r['মোবাইল']:
                                            msg = f"সম্মানিত অভিভাবক, আপনার সন্তান {r['নাম']}-এর {rep_month} মাসের ফি {r['বকেয়া']:,.0f} টাকা বকেয়া আছে। দ্রুত পরিশোধের অনুরোধ করা হলো। - {institute_name}"
                                            success, response_msg = send_sms(tenant_id, r['মোবাইল'], msg)
                                            if success:
                                                st.success(f"✅ {r['নাম']}-এর অভিভাবককে SMS পাঠানো হয়েছে।")
                                            else:
                                                st.error(f"SMS Error: {response_msg}")
                                        else:
                                            st.warning("⚠️ এই ছাত্রের অভিভাবকের কোনো মোবাইল নম্বর দেওয়া নেই!")
                                            
                    with col_sms2:
                        if st.button("🚀 লিস্টের সবাইকে একসাথে SMS দিন", type="primary", use_container_width=True):
                            with st.spinner("সব বকেয়া ছাত্রদের SMS পাঠানো হচ্ছে (একটু সময় লাগতে পারে)..."):
                                success_count = 0
                                for r in res:
                                    if r['মোবাইল'] and len(str(r['মোবাইল'])) >= 11:
                                        msg = f"সম্মানিত অভিভাবক, আপনার সন্তান {r['নাম']}-এর {rep_month} মাসের ফি {r['বকেয়া']:,.0f} টাকা বকেয়া আছে। দ্রুত পরিশোধের অনুরোধ করা হলো। - {institute_name}"
                                        success, _ = send_sms(tenant_id, r['মোবাইল'], msg)
                                        if success:
                                            success_count += 1
                                
                                st.success(f"🎉 আলহামদুলিল্লাহ! মোট {success_count} জনকে বকেয়া রিমাইন্ডার পাঠানো হয়েছে।")
                else:
                    st.success(f"✅ আলহামদুলিল্লাহ! {rep_month} মাসে সবার ফি ক্লিয়ার আছে। কোনো বকেয়া নেই।")
        except Exception as e:
            conn.rollback()
            st.error(f"রিপোর্ট জেনারেট এরর: {e}")

    cur.close()