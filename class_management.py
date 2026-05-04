import streamlit as st
import pandas as pd
from database import get_connection

def show_class_management():
    st.title("🏫 ক্লাস ও সেকশন ম্যানেজমেন্ট")
    st.markdown("---")
    
    tenant_id = st.session_state.get('tenant_id', 1)
    
    conn = get_connection()
    if not conn:
        st.error("ডাটাবেস কানেকশন পাওয়া যাচ্ছে না!")
        return
        
    conn.rollback()
    cur = conn.cursor()

    tab_add, tab_list = st.tabs(["➕ নতুন ক্লাস যুক্ত করুন", "📋 ক্লাসের তালিকা ও আপডেট"])

    # ==========================================
    # --- ট্যাব ১: নতুন ক্লাস যুক্ত করা ---
    # ==========================================
    with tab_add:
        st.subheader("নতুন ক্লাস ও ফি সেটআপ")
        
        with st.form("add_class_form", clear_on_submit=True):
            col1, col2 = st.columns(2)
            
            with col1:
                selected_class = st.selectbox("ক্লাসের নাম *", [
                    "প্লে (Play)", "নার্সারি (Nursery)", "কেজি (KG)",
                    "১ম শ্রেণি", "২য় শ্রেণি", "৩য় শ্রেণি", "৪র্থ শ্রেণি", "৫ম শ্রেণি",
                    "৬ষ্ঠ শ্রেণি", "৭ম শ্রেণি", "৮ম শ্রেণি", "৯ম শ্রেণি", "১০ম শ্রেণি",
                    "হিফজ", "মক্তব", "অন্যান্য"
                ])
                
                # যদি অন্যান্য সিলেক্ট করে, তবেই টেক্সট বক্স দেখাবে
                custom_class = ""
                if selected_class == "অন্যান্য":
                    custom_class = st.text_input("ক্লাসের নাম লিখুন *")
                    
                section = st.text_input("সেকশন বা গ্রুপ (যেমন: A, B, বিজ্ঞান)")
                
            with col2:
                class_teacher = st.text_input("শ্রেণী শিক্ষকের নাম (Class Teacher)")
                monthly_fee = st.number_input("এই ক্লাসের নির্ধারিত মাসিক ফি (৳) *", min_value=0, value=500, step=50)

            submit_btn = st.form_submit_button("✅ ক্লাস সেভ করুন", use_container_width=True)
            
            if submit_btn:
                final_class_name = custom_class if selected_class == "অন্যান্য" else selected_class
                
                if not final_class_name:
                    st.warning("⚠️ ক্লাসের নাম দেওয়া আবশ্যক!")
                else:
                    try:
                        # চেক করা যে এই ক্লাস ও সেকশন আগেই আছে কি না
                        cur.execute("SELECT id FROM classes WHERE class_name=%s AND section=%s AND tenant_id=%s", (final_class_name, section, tenant_id))
                        if cur.fetchone():
                            st.error(f"⚠️ '{final_class_name}' ({section}) ক্লাসটি ইতিমধ্যেই ডাটাবেসে যুক্ত আছে!")
                        else:
                            cur.execute("""
                                INSERT INTO classes (tenant_id, class_name, section, class_teacher, monthly_fee, status) 
                                VALUES (%s, %s, %s, %s, %s, 'Active')
                            """, (tenant_id, final_class_name, section, class_teacher, monthly_fee))
                            conn.commit()
                            st.success(f"🎉 আলহামদুলিল্লাহ! '{final_class_name}' সফলভাবে যুক্ত হয়েছে।")
                            st.balloons()
                    except Exception as e:
                        conn.rollback()
                        st.error(f"সেভ এরর: {e}")

    # ==========================================
    # --- ট্যাব ২: তালিকা ও স্মার্ট আপডেট ---
    # ==========================================
    with tab_list:
        st.subheader("বিদ্যমান ক্লাসের তালিকা (এডিট করার সুবিধা সহ)")
        st.info("💡 কোনো ক্লাসের ফি বা শিক্ষকের নাম পরিবর্তন করতে চাইলে সরাসরি নিচের টেবিলে ক্লিক করে পরিবর্তন করুন এবং 'আপডেট সেভ করুন' বাটনে চাপ দিন।")
        
        try:
            cur.execute("SELECT id, class_name, section, class_teacher, monthly_fee, status FROM classes WHERE tenant_id=%s ORDER BY id", (tenant_id,))
            class_data = cur.fetchall()
            
            if class_data:
                # ডাটাফ্রেম তৈরি করা
                df = pd.DataFrame(class_data, columns=["ID", "ক্লাসের নাম", "সেকশন", "শ্রেণী শিক্ষক", "মাসিক ফি (৳)", "স্ট্যাটাস"])
                
                # st.data_editor দিয়ে এডিটেবল টেবিল তৈরি
                with st.form("update_classes_form"):
                    edited_df = st.data_editor(
                        df,
                        column_config={
                            "ID": st.column_config.NumberColumn(disabled=True), 
                            "ক্লাসের নাম": st.column_config.TextColumn(disabled=True),
                            "সেকশন": st.column_config.TextColumn(),
                            "শ্রেণী শিক্ষক": st.column_config.TextColumn(),
                            "মাসিক ফি (৳)": st.column_config.NumberColumn(min_value=0),
                            "স্ট্যাটাস": st.column_config.SelectboxColumn(options=["Active", "Inactive"])
                        },
                        hide_index=True,
                        use_container_width=True
                    )
                    
                    update_btn = st.form_submit_button("💾 আপডেট সেভ করুন", type="primary")
                    
                    if update_btn:
                        try:
                            # লুপ চালিয়ে এডিট করা ডাটা আপডেট করা
                            for index, row in edited_df.iterrows():
                                cur.execute("""
                                    UPDATE classes 
                                    SET section=%s, class_teacher=%s, monthly_fee=%s, status=%s 
                                    WHERE id=%s AND tenant_id=%s
                                """, (row["সেকশন"], row["শ্রেণী শিক্ষক"], row["মাসিক ফি (৳)"], row["স্ট্যাটাস"], row["ID"], tenant_id))
                            
                            conn.commit()
                            st.success("✅ আলহামদুলিল্লাহ! সব আপডেট সফলভাবে সেভ হয়েছে।")
                            st.rerun()
                        except Exception as e:
                            conn.rollback()
                            st.error(f"আপডেট এরর: {e}")
            else:
                st.warning("📌 আপনার মাদরাসায় এখনো কোনো ক্লাস যুক্ত করা হয়নি।")
        except Exception as e:
            conn.rollback()
            st.error(f"ডাটা লোড এরর: {e}")

    cur.close()