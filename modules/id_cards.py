import streamlit as st
import pandas as pd
from database import get_connection
import streamlit.components.v1 as components
import qrcode
import base64
from io import BytesIO

# ==========================================
# QR Code তৈরি করার ফাংশন
# ==========================================
def generate_qr_base64(data):
    qr = qrcode.QRCode(version=1, box_size=10, border=2)
    qr.add_data(data)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    buffered = BytesIO()
    img.save(buffered, format="PNG")
    return base64.b64encode(buffered.getvalue()).decode()

def show_id_cards():
    # সেশন থেকে বর্তমান মাদরাসার নাম ও আইডি নিয়ে আসা
    inst_name = st.session_state.get('madrasa_name', 'স্মার্ট মাদরাসা ম্যানেজমেন্ট')
    tenant_id = st.session_state.get('tenant_id', 1)
    
    st.title("🪪 স্মার্ট আইডি কার্ড ও QR কোড")
    st.markdown("---")
    
    tab_student, tab_staff = st.tabs(["🎓 ছাত্রদের আইডি কার্ড", "👥 শিক্ষক ও স্টাফ আইডি কার্ড"])
    
    conn = get_connection()
    if not conn:
        st.error("ডাটাবেস কানেকশন এরর!")
        return
        
    cur = conn.cursor()

    # ==========================================
    # --- ছাত্রদের আইডি কার্ড ---
    # ==========================================
    with tab_student:
        try:
            # নতুন ডাটাবেস স্ট্রাকচার অনুযায়ী কোয়েরি
            cur.execute("""
                SELECT id, name, class_name, roll_no, mobile_no, photo 
                FROM students 
                WHERE tenant_id = %s AND COALESCE(status, 'Active') = 'Active' 
                ORDER BY class_name, roll_no
            """, (tenant_id,))
            students = cur.fetchall()
            
            if students:
                st_dict = {f"{r[1]} (রোল: {r[3]}, শ্রেণী: {r[2]})": r for r in students}
                sel_st = st.selectbox("কার আইডি কার্ড দেখতে চান? (ছাত্র নির্বাচন করুন)", list(st_dict.keys()), key="id_st")
                
                s_id, s_name, s_cls, s_roll, s_mob, s_photo = st_dict[sel_st]
                
                # QR Code জেনারেট (STU-ID ফরম্যাটে)
                qr_b64 = generate_qr_base64(f"STU-{s_id}")
                img_src = f"data:image/png;base64,{s_photo}" if s_photo else "https://cdn-icons-png.flaticon.com/512/3135/3135715.png"
                
                html_card = f"""
                <div style="width: 320px; border: 2px solid #1E88E5; border-radius: 15px; padding: 15px; text-align: center; background: white; font-family: sans-serif; box-shadow: 4px 4px 15px rgba(0,0,0,0.1); margin: auto; color: black;">
                    <h3 style="color: #1E88E5; margin: 0; font-size: 18px;">{inst_name}</h3>
                    <p style="margin: 0; font-size: 10px; color: gray; margin-bottom: 10px;">STUDENT ID CARD</p>
                    <div style="display: flex; justify-content: space-between; align-items: center; text-align: left;">
                        <img src="{img_src}" style="width: 90px; height: 90px; border-radius: 10px; border: 2px solid #1E88E5; object-fit: cover;">
                        <div style="margin-left: 10px;">
                            <h4 style="margin: 0; color: #333;">{s_name}</h4>
                            <p style="margin: 2px 0; font-size: 12px;">শ্রেণী: {s_cls}</p>
                            <p style="margin: 2px 0; font-size: 12px;">রোল: {s_roll}</p>
                        </div>
                    </div>
                    <div style="margin-top: 15px; display: flex; justify-content: space-around; align-items: center;">
                        <img src="data:image/png;base64,{qr_b64}" style="width: 70px; height: 70px;">
                        <div style="background: #1E88E5; color: white; padding: 5px 15px; border-radius: 20px; font-weight: bold; font-size: 12px;">
                            ID: STU-{s_id:04d}
                        </div>
                    </div>
                </div>
                """
                components.html(html_card, height=300)
                st.info("💡 এই কার্ডের QR Code স্ক্যান করে ছাত্ররা স্মার্ট হাজিরা দিতে পারবে।")
            else:
                st.warning("⚠️ আপনার মাদরাসায় কোনো রানিং ছাত্র পাওয়া যায়নি।")
        except Exception as e:
            st.error(f"ছাত্রদের ডাটা লোড এরর: {e}")

    # ==========================================
    # --- স্টাফদের আইডি কার্ড ---
    # ==========================================
    with tab_staff:
        try:
            # স্টাফ টেবিলের জন্য নতুন কোয়েরি
            cur.execute("""
                SELECT id, name, designation, mobile_no, photo 
                FROM staff 
                WHERE tenant_id = %s AND COALESCE(status, 'Active') = 'Active'
            """, (tenant_id,))
            staff_data = cur.fetchall()
            
            if staff_data:
                stf_dict = {f"{r[1]} ({r[2]})": r for r in staff_data}
                sel_stf = st.selectbox("কার আইডি কার্ড দেখতে চান? (স্টাফ নির্বাচন করুন)", list(stf_dict.keys()), key="id_stf")
                
                t_id, t_name, t_desig, t_mob, t_photo = stf_dict[sel_stf]
                
                qr_b64_stf = generate_qr_base64(f"EMP-{t_id}")
                img_src_stf = f"data:image/png;base64,{t_photo}" if t_photo else "https://cdn-icons-png.flaticon.com/512/3135/3135715.png"
                
                html_card_stf = f"""
                <div style="width: 320px; border: 2px solid #D84315; border-radius: 15px; padding: 15px; text-align: center; background: white; font-family: sans-serif; box-shadow: 4px 4px 15px rgba(0,0,0,0.1); margin: auto; color: black;">
                    <h3 style="color: #D84315; margin: 0; font-size: 18px;">{inst_name}</h3>
                    <p style="margin: 0; font-size: 10px; color: gray; margin-bottom: 10px;">OFFICIAL ID CARD</p>
                    <div style="display: flex; justify-content: space-between; align-items: center; text-align: left;">
                        <img src="{img_src_stf}" style="width: 90px; height: 90px; border-radius: 10px; border: 2px solid #D84315; object-fit: cover;">
                        <div style="margin-left: 10px;">
                            <h4 style="margin: 0; color: #333;">{t_name}</h4>
                            <p style="margin: 2px 0; font-size: 12px;">পদবি: {t_desig}</p>
                        </div>
                    </div>
                    <div style="margin-top: 15px; display: flex; justify-content: space-around; align-items: center;">
                        <img src="data:image/png;base64,{qr_b64_stf}" style="width: 70px; height: 70px;">
                        <div style="background: #D84315; color: white; padding: 5px 15px; border-radius: 20px; font-weight: bold; font-size: 12px;">
                            ID: EMP-{t_id:04d}
                        </div>
                    </div>
                </div>
                """
                components.html(html_card_stf, height=300)
            else:
                st.warning("⚠️ কোনো রানিং স্টাফ পাওয়া যায়নি।")
        except Exception as e:
            st.error(f"স্টাফ ডাটা লোড এরর: {e}")

    cur.close()