import streamlit as st
from database import get_connection
import qrcode
from io import BytesIO
import base64
from datetime import datetime

def generate_qr(data):
    qr = qrcode.QRCode(version=1, box_size=5, border=2)
    qr.add_data(data)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    buffered = BytesIO()
    img.save(buffered, format="PNG")
    return base64.b64encode(buffered.getvalue()).decode()

def show_certificates():
    # প্রিন্ট CSS (বাম পাশ থেকে শুরু, যাতে কোড শো না করে)
    print_css = """
<style>
@media print {
    [data-testid="stSidebar"], header, .stButton, .stSelectbox, .stTabs, div.stMarkdown:first-of-type, .stAlert { display: none !important; }
    .certificate-border { border: 15px double #1B5E20 !important; padding: 50px !important; margin-top: 50px !important;}
    body { background-color: white !important; }
}
</style>
"""
    st.markdown(print_css, unsafe_allow_html=True)

    inst_name = st.session_state.get('madrasa_name', 'স্মার্ট মাদরাসা মডেল একাডেমি')
    tenant_id = st.session_state.get('tenant_id', 1)
    
    # ডাইনামিক স্থাপিত সাল
    est_year = st.session_state.get('established_year', '২০২৪')
    inst_year = f"স্থাপিত: {est_year}"
    
    st.title("📜 প্রশংসাপত্র ও সার্টিফিকেট")
    st.markdown("---")
    
    conn = get_connection()
    if not conn:
        st.error("ডাটাবেস কানেকশন এরর!")
        return
        
    cur = conn.cursor()
    
    try:
        cur.execute("SELECT id, name, class_name, roll_no, father_name, mother_name FROM students WHERE tenant_id = %s ORDER BY class_name, roll_no", (tenant_id,))
        students = cur.fetchall()
        
        if students:
            st_dict = {f"{r[1]} (রোল: {r[3]}, শ্রেণী: {r[2]})": r for r in students}
            
            col1, col2 = st.columns(2)
            selected_label = col1.selectbox("সার্টিফিকেটের জন্য ছাত্র নির্বাচন করুন", list(st_dict.keys()))
            cert_type = col2.selectbox("সার্টিফিকেটের ধরন", ["প্রশংসাপত্র (Testimonial)", "অধ্যয়নরত প্রত্যয়নপত্র (Appeared Certificate)"])
            
            if st.button("সার্টিফিকেট জেনারেট করুন", use_container_width=True, type="primary"):
                s_data = st_dict[selected_label]
                s_id, s_name, s_class, s_roll = s_data[0], s_data[1], s_data[2], s_data[3]
                f_name = s_data[4] or "দেওয়া হয়নি"
                m_name = s_data[5] or "দেওয়া হয়নি"
                
                v_code = f"CERT-{s_id}-{datetime.now().strftime('%y%m%d')}"
                qr_base64 = generate_qr(f"Verified by {inst_name}\nStudent: {s_name}\nClass: {s_class}\nID: STU-{s_id}\nVerify Code: {v_code}")

                if cert_type == "প্রশংসাপত্র (Testimonial)":
                    content = f"এই মর্মে প্রত্যয়ন করা যাচ্ছে যে, <b>{s_name}</b>, পিতা: {f_name}, মাতা: {m_name}, এই প্রতিষ্ঠানে <b>{s_class}</b> শ্রেণীতে অত্যন্ত সুনামের সাথে অধ্যয়ন শেষ করেছে। তার রোল নম্বর ছিল {s_roll}। অত্র প্রতিষ্ঠানে অবস্থানকালে সে অত্যন্ত নিষ্ঠাবান এবং উত্তম চরিত্রের অধিকারী ছিল। আমার জানামতে সে মাদরাসা বা রাষ্ট্র বিরোধী কোনো কার্যকলাপে জড়িত ছিল না। আমি তার সার্বিক সাফল্য ও উজ্জ্বল ভবিষ্যৎ কামনা করি।"
                else:
                    content = f"এই মর্মে প্রত্যয়ন করা যাচ্ছে যে, <b>{s_name}</b>, পিতা: {f_name}, মাতা: {m_name}, বর্তমানে এই প্রতিষ্ঠানে <b>{s_class}</b> শ্রেণীতে অধ্যয়নরত আছে। তার রোল নম্বর {s_roll}। অত্র প্রতিষ্ঠানের ভর্তি রেজিস্ট্রার ও নথিপত্র অনুযায়ী সে একজন নিয়মিত ও ভদ্র ছাত্র।"

                # HTML ডিজাইন (একেবারে বাম পাশ থেকে শুরু)
                html_code = f"""
<div class="certificate-border" style="border: 10px double #1B5E20; padding: 40px; background: #fffcf5; color: black; font-family: 'Arial', sans-serif; text-align: center; position: relative;">
    <div style="border: 2px solid #1B5E20; padding: 20px;">
        <h1 style="color: #1B5E20; margin: 0; font-size: 35px; font-weight: bold;">{inst_name}</h1>
        <p style="margin: 5px 0; font-size: 16px;">{inst_year}</p>
        <hr style="border: 1px solid #1B5E20; width: 80%; margin-top: 15px;">
        <h2 style="text-decoration: underline; margin: 25px 0; color: #b91c1c; font-size: 28px;">{cert_type.split(' (')[0]}</h2>
        <p style="text-align: right; font-size: 15px; font-weight: bold; padding-right: 20px;">তারিখ: {datetime.now().strftime('%d/%m/%Y')}</p>
        <div style="text-align: justify; text-align-last: center; line-height: 2.2; font-size: 18px; margin: 30px 0; padding: 0 30px;">
            {content}
        </div>
        <div style="display: flex; justify-content: space-between; align-items: flex-end; margin-top: 70px; padding: 0 20px;">
            <div style="text-align: left;">
                <img src="data:image/png;base64,{qr_base64}" width="90" style="border: 1px solid #ddd; padding: 2px;"><br>
                <span style="font-size: 11px; color: #4b5563; font-weight: bold;">Verify: {v_code}</span>
            </div>
            <div style="text-align: center;">
                <p style="border-top: 2px dashed black; width: 200px; padding-top: 10px; font-weight: bold; font-size: 16px; margin: 0;">অধ্যক্ষের স্বাক্ষর ও সিল</p>
            </div>
        </div>
    </div>
</div>
"""
                st.markdown(html_code, unsafe_allow_html=True)
                st.markdown('<br><button onclick="window.print()" style="padding: 10px 20px; background-color: #1B5E20; color: white; border: none; border-radius: 5px; cursor: pointer; width: 100%; font-size: 16px; font-weight: bold;">🖨️ সার্টিফিকেট প্রিন্ট করুন</button>', unsafe_allow_html=True)

        else:
            st.warning("⚠️ ডাটাবেসে কোনো ছাত্রের ডাটা পাওয়া যায়নি।")
    except Exception as e:
        st.error(f"সার্টিফিকেট লোড এরর: {e}")
    finally:
        if cur: cur.close()
        # conn.close() রিমুভ করা হয়েছে, ডাটাবেস লিক বা ক্র্যাশ হবে না