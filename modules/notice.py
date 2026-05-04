import streamlit as st
import pandas as pd
from database import get_connection
from utils import send_sms

def show_notice():
    tenant_id = st.session_state.get('tenant_id', 1)
    
    st.title("✉️ নোটিশ বোর্ড ও SMS প্যানেল")
    st.markdown("---")
    
    tab_send, tab_settings = st.tabs(["🚀 SMS পাঠান", "⚙️ SMS সেটিংস (API)"])
    
    conn = get_connection()
    if not conn:
        st.error("ডাটাবেস কানেকশন এরর!")
        return
        
    conn.rollback()
    cur = conn.cursor()

    # ==========================================
    # --- ট্যাব ১: SMS পাঠানোর ফর্ম ---
    # ==========================================
    with tab_send:
        col1, col2 = st.columns([1.5, 1])
        
        with col1:
            st.markdown("#### 📝 নতুন মেসেজ লিখুন")
            
            # কাদের পাঠাবেন তার লজিক
            target_group = st.selectbox("কাদের SMS পাঠাবেন?", ["একজন নির্দিষ্ট ব্যক্তিকে", "সব শিক্ষার্থী (All)", "নির্দিষ্ট ক্লাস"])
            
            target_number = ""
            selected_class = ""
            
            if target_group == "একজন নির্দিষ্ট ব্যক্তিকে":
                target_number = st.text_input("মোবাইল নাম্বার দিন (যেমন: 01712345678)")
                
            elif target_group == "নির্দিষ্ট ক্লাস":
                try:
                    cur.execute("SELECT DISTINCT class_name FROM students WHERE tenant_id = %s AND status = 'Active'", (tenant_id,))
                    db_classes = [row[0] for row in cur.fetchall() if row[0] is not None]
                    if db_classes:
                        selected_class = st.selectbox("কোন ক্লাসের ছাত্রদের পাঠাবেন?", db_classes)
                    else:
                        st.warning("আপনার মাদরাসায় কোনো ক্লাস পাওয়া যায়নি।")
                except Exception as e:
                    st.error(f"ক্লাস লোড এরর: {e}")
            
            message_body = st.text_area("মেসেজ টাইপ করুন (বাংলা বা ইংরেজি)", height=150)
            
            if st.button("🚀 SMS পাঠান", type="primary", use_container_width=True):
                if not message_body:
                    st.warning("⚠️ আগে মেসেজ টাইপ করুন!")
                elif target_group == "একজন নির্দিষ্ট ব্যক্তিকে" and not target_number:
                    st.warning("⚠️ মোবাইল নাম্বার দিতে হবে!")
                elif target_group == "নির্দিষ্ট ক্লাস" and not selected_class:
                    st.warning("⚠️ ক্লাস নির্বাচন করতে হবে!")
                else:
                    with st.spinner("SMS পাঠানো হচ্ছে (অপেক্ষা করুন)..."):
                        
                        # --- ১. নির্দিষ্ট একজনকে পাঠানো ---
                        if target_group == "একজন নির্দিষ্ট ব্যক্তিকে":
                            success, msg = send_sms(tenant_id, target_number, message_body)
                            if success:
                                st.success("🎉 " + msg)
                                st.balloons()
                            else:
                                st.error("❌ " + msg)
                                
                        # --- ২. সব শিক্ষার্থী বা নির্দিষ্ট ক্লাসকে একসাথে পাঠানো (Bulk SMS) ---
                        else:
                            try:
                                if target_group == "সব শিক্ষার্থী (All)":
                                    cur.execute("SELECT name, mobile_no FROM students WHERE tenant_id = %s AND status = 'Active'", (tenant_id,))
                                else:
                                    cur.execute("SELECT name, mobile_no FROM students WHERE tenant_id = %s AND class_name = %s AND status = 'Active'", (tenant_id, selected_class))
                                
                                targets = cur.fetchall()
                                
                                if targets:
                                    success_count = 0
                                    fail_count = 0
                                    
                                    for target in targets:
                                        name, mobile = target
                                        if mobile and len(str(mobile)) >= 11:
                                            # SMS API কল
                                            success, _ = send_sms(tenant_id, mobile, message_body)
                                            if success:
                                                success_count += 1
                                            else:
                                                fail_count += 1
                                        else:
                                            fail_count += 1 # নাম্বার ভুল বা না থাকলে
                                            
                                    st.success(f"🎉 আলহামদুলিল্লাহ! মোট {success_count} জন ছাত্রকে সফলভাবে নোটিশ পাঠানো হয়েছে। (ব্যর্থ: {fail_count} জন)")
                                    st.balloons()
                                else:
                                    st.warning("⚠️ ডাটাবেসে কোনো সক্রিয় (Active) ছাত্রের নাম্বার পাওয়া যায়নি।")
                            
                            except Exception as e:
                                conn.rollback()
                                st.error(f"Bulk SMS এরর: {e}")

    # ==========================================
    # --- ট্যাব ২: মাদরাসা অ্যাডমিনের SMS সেটিংস ---
    # ==========================================
    with tab_settings:
        st.markdown("#### ⚙️ আপনার SMS API কনফিগারেশন")
        st.info("💡 আপনার কেনা SMS প্রোভাইডারের (যেমন: BulkSMSBD) API Key এবং Sender ID এখানে বসান। এই তথ্যগুলো সম্পূর্ণ এনক্রিপ্টেড থাকবে।")
        
        try:
            cur.execute("SELECT sms_api_key, sms_sender_id, is_sms_active FROM madrasas WHERE tenant_id = %s", (tenant_id,))
            current_settings = cur.fetchone()
            
            curr_api = current_settings[0] if current_settings and current_settings[0] else ""
            curr_sender = current_settings[1] if current_settings and current_settings[1] else ""
            curr_active = current_settings[2] if current_settings and current_settings[2] is not None else False
            
            with st.form("sms_settings_form"):
                new_api_key = st.text_input("🔑 API Key (এপিআই কী)", value=curr_api, type="password")
                new_sender_id = st.text_input("🏷️ Sender ID (সেন্ডার আইডি)", value=curr_sender)
                is_active = st.checkbox("✅ অটোমেটিক SMS সার্ভিস চালু রাখুন (হাজিরা/বেতন/নোটিশ)", value=curr_active)
                
                if st.form_submit_button("💾 সেটিংস সেভ করুন", type="primary", use_container_width=True):
                    cur.execute("""
                        UPDATE madrasas 
                        SET sms_api_key = %s, sms_sender_id = %s, is_sms_active = %s 
                        WHERE tenant_id = %s
                    """, (new_api_key, new_sender_id, is_active, tenant_id))
                    conn.commit()
                    st.success("🎉 আলহামদুলিল্লাহ! আপনার SMS সেটিংস সফলভাবে আপডেট হয়েছে।")
                    st.rerun()
                    
        except Exception as e:
            conn.rollback()
            st.error(f"সেটিংস লোড এরর: {e}")

    cur.close()