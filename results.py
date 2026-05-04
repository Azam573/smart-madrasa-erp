import streamlit as st
import pandas as pd
from database import get_connection
import qrcode
from io import BytesIO
import base64

# --- গ্রেড ও জিপিএ ফাংশন ---
def get_grade(marks):
    if marks >= 80: return "A+"
    elif marks >= 70: return "A"
    elif marks >= 60: return "A-"
    elif marks >= 50: return "B"
    elif marks >= 40: return "C"
    elif marks >= 33: return "D"
    else: return "F"

def get_gpa(marks):
    if marks >= 80: return 5.00
    elif marks >= 70: return 4.00
    elif marks >= 60: return 3.50
    elif marks >= 50: return 3.00
    elif marks >= 40: return 2.00
    elif marks >= 33: return 1.00
    else: return 0.00

# --- কিউআর কোড জেনারেটর ---
def generate_qr(data):
    qr = qrcode.QRCode(version=1, box_size=10, border=2)
    qr.add_data(data)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    buffered = BytesIO()
    img.save(buffered, format="PNG")
    return base64.b64encode(buffered.getvalue()).decode()

def show_results():
    # প্রিন্ট CSS (বাম পাশ থেকে শুরু, যাতে কোড শো না করে)
    print_css = """
<style>
@media print {
    [data-testid="stSidebar"], header, .stButton, .stSelectbox, .stNumberInput, .stTextInput, .stTabs, div.stMarkdown:first-of-type, .stAlert {
        display: none !important;
    }
    .marksheet-container { display: block !important; visibility: visible !important; margin-top: 30px !important;}
    body { background-color: white !important; }
}
</style>
"""
    st.markdown(print_css, unsafe_allow_html=True)

    inst_name = st.session_state.get('madrasa_name', 'স্মার্ট মাদরাসা ম্যানেজমেন্ট')
    tenant_id = st.session_state.get('tenant_id', 1)
    est_year = st.session_state.get('established_year', '২০২৪')
    inst_year = f"স্থাপিত: {est_year}"

    st.title(f"🎓 {inst_name} - রেজাল্ট ও মার্কশিট")
    st.markdown("---")
    
    tab1, tab2 = st.tabs(["📝 নম্বর ইনপুট", "📜 মার্কশিট জেনারেটর"])

    conn = get_connection()
    if not conn:
        st.error("ডাটাবেস কানেকশন এরর!")
        return
        
    cur = conn.cursor()

    try:
        cur.execute("SELECT id, name, class_name, roll_no FROM students WHERE tenant_id = %s AND COALESCE(status, 'Active') = 'Active' ORDER BY class_name, roll_no", (tenant_id,))
        students = cur.fetchall()
        st_dict = {f"{n} (রোল: {r}, শ্রেণী: {c})": (i, n, c, r) for i, n, c, r in students} if students else {}

        # ==========================================
        # --- ট্যাব ১: নম্বর এন্ট্রি ---
        # ==========================================
        with tab1:
            st.subheader("ছাত্রের নম্বর এন্ট্রি করুন")
            if students:
                with st.form("marks_entry_form", clear_on_submit=False):
                    sel_st = st.selectbox("ছাত্র নির্বাচন", list(st_dict.keys()), key="entry_st")
                    exam = st.selectbox("পরীক্ষার নাম", ["প্রথম সাময়িক", "দ্বিতীয় সাময়িক", "বার্ষিক পরীক্ষা", "মাসিক মূল্যায়ন"])
                    
                    col1, col2, col3 = st.columns(3)
                    sub = col1.text_input("বিষয়ের নাম (উদা: আরবি) *")
                    obt_m = col2.number_input("প্রাপ্ত নম্বর", min_value=0.0, max_value=100.0)
                    tot_m = col3.number_input("মোট নম্বর", value=100.0)

                    if st.form_submit_button("✅ নম্বর সেভ করুন", use_container_width=True):
                        if not sub:
                            st.warning("⚠️ বিষয়ের নাম লিখতে হবে!")
                        else:
                            st_id = st_dict[sel_st][0]
                            try:
                                cur.execute("SELECT id FROM exam_results WHERE student_id=%s AND exam_name=%s AND subject_name=%s AND tenant_id=%s", (st_id, exam, sub, tenant_id))
                                exists = cur.fetchone()
                                if exists:
                                    cur.execute("UPDATE exam_results SET marks=%s, total_marks=%s WHERE id=%s", (obt_m, tot_m, exists[0]))
                                else:
                                    cur.execute("INSERT INTO exam_results (tenant_id, student_id, exam_name, subject_name, marks, total_marks) VALUES (%s, %s, %s, %s, %s, %s)", (tenant_id, st_id, exam, sub, obt_m, tot_m))
                                conn.commit()
                                st.success(f"🎉 {sub} বিষয়ের নম্বর সফলভাবে সেভ হয়েছে!")
                            except Exception as e:
                                conn.rollback()
                                st.error(f"ভুল হয়েছে: {e}")
            else:
                st.info("📌 কোনো অ্যাক্টিভ ছাত্র নেই।")

        # ==========================================
        # --- ট্যাব ২: মার্কশিট জেনারেটর ---
        # ==========================================
        with tab2:
            st.subheader("ডিজিটাল মার্কশিট তৈরি")
            if students:
                col_a, col_b = st.columns(2)
                with col_a:
                    sel_st_res = st.selectbox("ছাত্র নির্বাচন করুন", list(st_dict.keys()), key="view_res")
                    sel_exam = st.selectbox("কোন পরীক্ষার রেজাল্ট?", ["প্রথম সাময়িক", "দ্বিতীয় সাময়িক", "বার্ষিক পরীক্ষা", "মাসিক মূল্যায়ন"], key="view_exam")
                with col_b:
                    akhlaq = st.selectbox("আচরণ ও শিষ্টাচার", ["অতি উত্তম", "উত্তম", "সন্তোষজনক", "উন্নতি প্রয়োজন"])
                    remarks = st.text_input("শিক্ষকের মন্তব্য", value="আরও পরিশ্রম করতে হবে।")
                
                if st.button("📄 মার্কশিট দেখুন ও প্রিন্ট করুন", type="primary", use_container_width=True):
                    st_id, st_name, st_class, st_roll = st_dict[sel_st_res]
                    try:
                        cur.execute("SELECT subject_name, marks, total_marks FROM exam_results WHERE student_id = %s AND exam_name = %s AND tenant_id = %s ORDER BY subject_name", (st_id, sel_exam, tenant_id))
                        results = cur.fetchall()
                        
                        if results:
                            # মেধাক্রম
                            cur.execute("SELECT s.id, SUM(e.marks) as total_sum FROM exam_results e JOIN students s ON e.student_id = s.id WHERE e.exam_name = %s AND e.tenant_id = %s AND s.class_name = %s AND s.tenant_id = %s GROUP BY s.id ORDER BY total_sum DESC", (sel_exam, tenant_id, st_class, tenant_id))
                            merit_list = cur.fetchall()
                            position = "N/A"
                            for idx, row in enumerate(merit_list):
                                if row[0] == st_id:
                                    position = idx + 1
                                    break
                            pos_text = f"{position}ম" if position in [1, 2, 3] else f"{position}তম"

                            # হাজিরা
                            cur.execute("SELECT COUNT(DISTINCT date) FROM attendance WHERE tenant_id = %s", (tenant_id,))
                            total_days = cur.fetchone()[0] or 0
                            cur.execute("SELECT COUNT(id) FROM attendance WHERE student_id = %s AND status = 'Present' AND tenant_id = %s", (st_id, tenant_id))
                            present_days = cur.fetchone()[0] or 0
                            att_percent = int((present_days / total_days) * 100) if total_days > 0 else 0

                            table_rows = ""
                            total_obt = 0
                            total_gpa_points = 0.0
                            has_failed = False

                            for r in results:
                                sub_name, obt, tot = r[0], r[1], r[2]
                                total_obt += obt
                                cur.execute("SELECT MAX(e.marks) FROM exam_results e JOIN students s ON e.student_id = s.id WHERE e.exam_name = %s AND e.subject_name = %s AND s.class_name = %s AND e.tenant_id = %s", (sel_exam, sub_name, st_class, tenant_id))
                                highest = cur.fetchone()[0] or obt
                                grade = get_grade(obt)
                                gpa_point = get_gpa(obt)
                                total_gpa_points += gpa_point
                                if gpa_point == 0: has_failed = True
                                table_rows += f"<tr><td style='border: 1px solid black; padding: 8px;'>{sub_name}</td><td style='border: 1px solid black; padding: 8px; text-align: center;'>{tot}</td><td style='border: 1px solid black; padding: 8px; text-align: center; color: #1565c0; font-weight: bold;'>{highest}</td><td style='border: 1px solid black; padding: 8px; text-align: center; font-weight: bold;'>{obt}</td><td style='border: 1px solid black; padding: 8px; text-align: center; font-weight: bold; color: {'red' if grade=='F' else 'black'};'>{grade}</td><td style='border: 1px solid black; padding: 8px; text-align: center;'>{gpa_point:.2f}</td></tr>"

                            final_cgpa = 0.00 if has_failed else (total_gpa_points / len(results))
                            qr_data = f"Inst: {inst_name}\nStudent: {st_name}\nExam: {sel_exam}\nGPA: {final_cgpa:.2f}\nPos: {pos_text}"
                            qr_base64 = generate_qr(qr_data)

                            # HTML ডিজাইন (একেবারে বাম পাশ থেকে শুরু, যাতে কোড শো না করে)
                            html_code = f"""
<div class="marksheet-container" style="border: 4px solid #1B5E20; padding: 30px; border-radius: 10px; background: white; color: black; font-family: 'Arial', sans-serif;">
    <table style="width: 100%; border: none;">
        <tr>
            <td style="width: 20%; text-align: left; vertical-align: top;">
                <img src="data:image/png;base64,{qr_base64}" width="90" style="border: 1px solid #ccc; padding: 2px;"><br>
                <span style="font-size: 10px; color: gray; font-weight: bold;">Scan to Verify</span>
            </td>
            <td style="width: 60%; text-align: center; vertical-align: top;">
                <h1 style='color: #1B5E20; margin: 0; font-size: 28px;'>{inst_name}</h1>
                <p style='margin: 5px 0; font-size: 14px;'>{inst_year}</p>
                <p style='background-color: #1B5E20; color: white; display: inline-block; padding: 5px 20px; border-radius: 20px; font-weight: bold; font-size: 16px;'>একাডেমিক ট্রান্সক্রিপ্ট</p>
            </td>
            <td style="width: 20%; text-align: right; vertical-align: top;">
                <div style="border: 2px solid #1B5E20; padding: 10px; text-align: center; border-radius: 5px; background: #e8f5e9;">
                    <b style="color: #1B5E20;">মেধাক্রম</b><br>
                    <span style="font-size: 24px; color: #d32f2f; font-weight: bold;">{pos_text}</span>
                </div>
            </td>
        </tr>
    </table>
    <hr style="border: 1px solid #1B5E20; margin: 15px 0;">
    <table style="width: 100%; border: none; margin-bottom: 20px;">
        <tr>
            <td style="width: 60%; line-height: 1.8; font-size: 15px;">
                <b>ছাত্রের নাম:</b> {st_name}<br>
                <b>শ্রেণী:</b> {st_class} | <b>রোল নং:</b> {st_roll}<br>
                <b>পরীক্ষা:</b> <span style="color: #1565c0; font-weight: bold;">{sel_exam}</span>
            </td>
            <td style="width: 40%; line-height: 1.6; text-align: right; font-size: 13px; background: #f1f8e9; padding: 10px; border-radius: 5px; border: 1px solid #a5d6a7;">
                <b style="color: #2E7D32; font-size: 14px;">হাজিরার সারাংশ</b><br>
                মোট ক্লাস: {total_days} দিন | উপস্থিতি: {present_days} দিন<br>
                <b style="font-size: 14px;">উপস্থিতির হার: {att_percent}%</b>
            </td>
        </tr>
    </table>
    <table style="width: 100%; border-collapse: collapse; text-align: center; border: 1px solid black; font-size: 15px;">
        <tr style="background-color: #c8e6c9; color: #1B5E20;">
            <th style="border: 1px solid black; padding: 10px;">বিষয়ের নাম</th>
            <th style="border: 1px solid black; padding: 10px;">পূর্ণমান</th>
            <th style="border: 1px solid black; padding: 10px; color: #1565c0;">সর্বোচ্চ নম্বর</th>
            <th style="border: 1px solid black; padding: 10px;">প্রাপ্ত নম্বর</th>
            <th style="border: 1px solid black; padding: 10px;">লেটার গ্রেড</th>
            <th style="border: 1px solid black; padding: 10px;">জিপিএ (GPA)</th>
        </tr>
        {table_rows}
    </table>
    <div style="margin-top: 20px; display: flex; justify-content: space-between; align-items: flex-start;">
        <div style="width: 55%; background: #f9f9f9; padding: 15px; border-radius: 5px; border: 1px solid #ddd; font-size: 14px;">
            <p style="margin: 0 0 8px 0;"><b>আচরণ ও শিষ্টাচার:</b> {akhlaq}</p>
            <p style="margin: 0;"><b>শিক্ষকের মন্তব্য:</b> <i>"{remarks}"</i></p>
        </div>
        <div style="width: 40%; text-align: right; background: #e3f2fd; padding: 15px; border-radius: 8px; border: 2px solid #90caf9;">
            <p style="margin: 0; font-size: 15px; color: #424242;">মোট প্রাপ্ত নম্বর: <b>{total_obt}</b></p>
            <p style="margin: 5px 0 0 0; font-size: 22px; color: {'red' if has_failed else '#1565c0'}; font-weight: bold;">GPA: {final_cgpa:.2f}</p>
        </div>
    </div>
    <br><br><br><br>
    <div style="display: flex; justify-content: space-between; font-weight: bold; font-size: 14px;">
        <p style="border-top: 1px dashed black; width: 180px; text-align: center; padding-top: 5px;">অভিভাবকের স্বাক্ষর</p>
        <p style="border-top: 1px dashed black; width: 180px; text-align: center; padding-top: 5px;">অধ্যক্ষের স্বাক্ষর ও সিল</p>
    </div>
</div>
"""
                            st.markdown(html_code, unsafe_allow_html=True)
                            st.markdown('<br><button onclick="window.print()" style="padding: 10px 20px; background-color: #1B5E20; color: white; border: none; border-radius: 5px; cursor: pointer; width: 100%; font-size: 16px;">🖨️ মার্কশিট প্রিন্ট করুন</button>', unsafe_allow_html=True)
                        else:
                            st.warning("⚠️ ডাটাবেসে এই পরীক্ষার কোনো নম্বর পাওয়া যায়নি।")
                    except Exception as e:
                        st.error(f"মার্কশিট এরর: {e}")
    except Exception as e:
        st.error(f"ছাত্র লোড এরর: {e}")
    finally:
        if cur: cur.close()