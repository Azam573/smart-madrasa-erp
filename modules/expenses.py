import streamlit as st
import pandas as pd
from database import get_connection
from datetime import datetime

def show_expenses():
    st.title("⚖️ পূর্ণাঙ্গ আয়-ব্যয় ও ক্যাশবুক")
    st.markdown("---")
    
    tenant_id = st.session_state.get('tenant_id', 1)
    institute_name = st.session_state.get('madrasa_name', 'স্মার্ট মাদরাসা')
    
    tab_exp, tab_inc, tab_report = st.tabs(["💸 নতুন খরচ (Expense)", "🕌 ফান্ড ও অনুদান (Funds)", "📊 ফান্ডভিত্তিক ব্যালেন্স"])
    
    conn = get_connection()
    if not conn:
        st.error("ডাটাবেস কানেকশন এরর!")
        return
        
    conn.rollback()
    cur = conn.cursor()

    fund_categories = [
        "সাধারণ তহবিল (General Fund)", "যাকাত ফান্ড (Zakat)", 
        "লিল্লাহ বোর্ডিং (Lillah Boarding)", "মাসিক চাঁদা ও ডোনেশন", 
        "ফিতরা ও কাফফারা", "কুরবানির চামড়া বিক্রয়", "সরকারি/বেসরকারি অনুদান"
    ]

    # ==========================================
    # --- ট্যাব ১: খরচ এন্ট্রি (Expense) ---
    # ==========================================
    with tab_exp:
        col1, col2 = st.columns([1, 1.5])
        with col1:
            st.subheader("খরচের ভাউচার এন্ট্রি")
            with st.form("expense_form", clear_on_submit=True):
                exp_date = st.date_input("তারিখ", datetime.now())
                fund_source = st.selectbox("কোন ফান্ড থেকে খরচ হবে?", fund_categories)
                category = st.selectbox("খরচের খাত/ক্যাটাগরি", [
                    "শিক্ষক ও স্টাফ বেতন", "ছাত্রদের ফি প্রদান (যাকাত/লিল্লাহ থেকে)", "খাবার ও বোর্ডিং খরচ", 
                    "বিদ্যুৎ ও গ্যাস বিল", "অফিস খরচ ও স্টেশনারি", "রক্ষণাবেক্ষণ ও মেরামত", "অন্যান্য"
                ])
                amount = st.number_input("পরিমাণ (৳) *", min_value=1)
                desc = st.text_input("বিবরণ (যেমন: মে মাসের বিদ্যুৎ বিল)")
                
                if st.form_submit_button("✅ খরচ সেভ করুন", use_container_width=True):
                    recorder = st.session_state.get('username', 'Admin')
                    try:
                        cur.execute("""
                            INSERT INTO expenses (tenant_id, expense_date, fund_source, category, amount, description, recorded_by) 
                            VALUES (%s, %s, %s, %s, %s, %s, %s)
                        """, (tenant_id, exp_date, fund_source, category, amount, desc, recorder))
                        conn.commit()
                        st.success(f"✅ সফলভাবে {amount} ৳ '{fund_source}' থেকে খরচ হিসেবে সেভ হয়েছে!")
                    except Exception as e:
                        conn.rollback()
                        st.error(f"ডাটাবেস এরর: {e}")
                    
        with col2:
            st.subheader("সাম্প্রতিক খরচের তালিকা ও ভাউচার")
            try:
                # ID সহ ডাটা আনা হলো রিসিটের জন্য
                cur.execute("SELECT id, expense_date, fund_source, category, amount, description FROM expenses WHERE tenant_id=%s ORDER BY id DESC LIMIT 10", (tenant_id,))
                exp_data = cur.fetchall()
                
                if exp_data:
                    # টেবিল দেখানোর জন্য ID কলাম বাদ দিয়ে DataFrame তৈরি
                    df_exp = pd.DataFrame(exp_data, columns=["id", "তারিখ", "ফান্ড", "খাত", "পরিমাণ (৳)", "বিবরণ"])
                    st.dataframe(df_exp.drop(columns=["id"]), use_container_width=True, hide_index=True)
                    
                    st.markdown("---")
                    st.markdown("### 🖨️ খরচের ভাউচার প্রিন্ট")
                    
                    # প্রিন্ট করার অপশন
                    exp_to_print = st.selectbox("কোন খরচের ভাউচার প্রিন্ট করবেন?", [f"ভাউচার নং: {e[0]} | তারিখ: {e[1]} | খাত: {e[3]} | ৳ {e[4]}" for e in exp_data])
                    
                    if st.button("🖨️ প্রিন্ট ভাউচার (Expense Voucher)", use_container_width=True):
                        exp_details = exp_to_print.split(" | ")
                        
                        # নির্দিষ্ট ভাউচারের ফান্ড ও বিবরণ বের করা
                        fund_text = ""
                        desc_text = ""
                        for d in exp_data:
                            if str(d[0]) == exp_details[0].split(": ")[1]:
                                fund_text = d[2]
                                desc_text = d[5]
                                break
                        
                        # Markdown Error বাইপাস করার জন্য এক লাইনের HTML ডিজাইন
                        expense_html = (
                            f"<div style='border: 2px dashed #E64A19; padding: 25px; border-radius: 12px; text-align: center; background-color: #fdfdfd; color: black; max-width: 400px; margin: auto;'>"
                            f"<h2 style='color: #E64A19; margin-bottom: 5px; font-size: 24px;'>{institute_name}</h2>"
                            f"<p style='color: gray; margin-top: 0; font-size: 14px;'>পেমেন্ট ভাউচার (Payment Voucher)</p>"
                            f"<hr style='border-top: 1px dashed #ccc;'>"
                            f"<p align='left' style='font-size: 15px;'><b>{exp_details[0]}</b> <br><b>তারিখ:</b> {exp_details[1].replace('তারিখ: ', '')}</p>"
                            f"<p align='left' style='font-size: 16px; margin-top: 10px;'><b>খরচের খাত:</b> {exp_details[2].replace('খাত: ', '')}</p>"
                            f"<p align='left' style='font-size: 14px; color: #555;'><b>কোন ফান্ড থেকে:</b> {fund_text}<br><b>বিবরণ:</b> {desc_text}</p>"
                            f"<div style='background: #FBE9E7; padding: 10px; border-radius: 8px; margin: 15px 0;'>"
                            f"<h3 align='center' style='color: #D84315; margin: 0;'>পরিশোধিত: {exp_details[3]}</h3>"
                            f"</div>"
                            f"<br><br><div style='display: flex; justify-content: space-between;'>"
                            f"<p align='left' style='margin-bottom: 0;'>___________________<br><span style='font-size: 13px; color: gray;'>গ্রহীতার স্বাক্ষর</span></p>"
                            f"<p align='right' style='margin-bottom: 0;'>___________________<br><span style='font-size: 13px; color: gray;'>কর্তৃপক্ষের স্বাক্ষর</span></p>"
                            f"</div>"
                            f"</div>"
                        )
                        st.markdown(expense_html, unsafe_allow_html=True)
                        st.info("🖨️ প্রিন্ট করতে কীবোর্ড থেকে **Ctrl + P** চাপুন।")
                else:
                    st.info("কোনো খরচের রেকর্ড পাওয়া যায়নি।")
            except Exception as e:
                conn.rollback()
                st.error(f"লোড এরর: {e}")

    # ==========================================
    # --- ট্যাব ২: নির্দিষ্ট ফান্ড ও অনুদান এন্ট্রি ---
    # ==========================================
    with tab_inc:
        col_i1, col_i2 = st.columns([1, 1.5])
        with col_i1:
            st.subheader("ফান্ড সংগ্রহ এন্ট্রি")
            with st.form("income_form", clear_on_submit=True):
                inc_date = st.date_input("তারিখ", datetime.now(), key="inc_date")
                source = st.selectbox("আয়ের খাত (Fund Category)", fund_categories)
                inc_amount = st.number_input("পরিমাণ (৳) *", min_value=1, key="inc_amt")
                inc_desc = st.text_input("বিবরণ (উদা: জনাব রহিমের যাকাতের টাকা)")
                
                if st.form_submit_button("✅ আয় সেভ করুন", use_container_width=True):
                    recorder = st.session_state.get('username', 'Admin')
                    try:
                        cur.execute("""
                            INSERT INTO other_incomes (tenant_id, income_date, source, amount, description, recorded_by) 
                            VALUES (%s, %s, %s, %s, %s, %s)
                        """, (tenant_id, inc_date, source, inc_amount, inc_desc, recorder))
                        conn.commit()
                        st.success(f"✅ সফলভাবে {inc_amount} ৳ '{source}' এ যুক্ত হয়েছে!")
                    except Exception as e:
                        conn.rollback()
                        st.error(f"ডাটাবেস এরর: {e}")

        with col_i2:
            st.subheader("সাম্প্রতিক ফান্ড তালিকা ও রিসিট")
            try:
                # ID সহ ডাটা আনা হলো রিসিটের জন্য
                cur.execute("SELECT id, income_date, source, amount, description FROM other_incomes WHERE tenant_id=%s ORDER BY id DESC LIMIT 10", (tenant_id,))
                inc_data = cur.fetchall()
                
                if inc_data:
                    # টেবিল দেখানোর জন্য ID কলাম বাদ দিয়ে DataFrame তৈরি
                    df_inc = pd.DataFrame(inc_data, columns=["id", "তারিখ", "ফান্ড", "পরিমাণ (৳)", "বিবরণ"])
                    st.dataframe(df_inc.drop(columns=["id"]), use_container_width=True, hide_index=True)
                    
                    st.markdown("---")
                    st.markdown("### 🖨️ আয়/চাঁদার রিসিট প্রিন্ট")
                    
                    # প্রিন্ট করার অপশন
                    inc_to_print = st.selectbox("কোন আয়ের রিসিট প্রিন্ট করবেন?", [f"রিসিট নং: {i[0]} | তারিখ: {i[1]} | দাতা/খাত: {i[2]} | ৳ {i[3]}" for i in inc_data])
                    
                    if st.button("🖨️ প্রিন্ট রিসিট (Income Receipt)", use_container_width=True):
                        inc_details = inc_to_print.split(" | ")
                        
                        # নির্দিষ্ট রিসিটের বিবরণ বের করা
                        desc_text = ""
                        for d in inc_data:
                            if str(d[0]) == inc_details[0].split(": ")[1]:
                                desc_text = d[4]
                                break

                        # Markdown Error বাইপাস করার জন্য এক লাইনের HTML ডিজাইন
                        income_html = (
                            f"<div style='border: 2px dashed #4CAF50; padding: 25px; border-radius: 12px; text-align: center; background-color: #fdfdfd; color: black; max-width: 400px; margin: auto;'>"
                            f"<h2 style='color: #4CAF50; margin-bottom: 5px; font-size: 24px;'>{institute_name}</h2>"
                            f"<p style='color: gray; margin-top: 0; font-size: 14px;'>মানি রিসিট - প্রাপ্তি স্বীকার (Income Receipt)</p>"
                            f"<hr style='border-top: 1px dashed #ccc;'>"
                            f"<p align='left' style='font-size: 15px;'><b>{inc_details[0]}</b> <br><b>তারিখ:</b> {inc_details[1].replace('তারিখ: ', '')}</p>"
                            f"<p align='left' style='font-size: 16px; margin-top: 10px;'><b>দাতা/খাত:</b> {inc_details[2].replace('দাতা/খাত: ', '')}</p>"
                            f"<p align='left' style='font-size: 14px; color: #555;'><b>বিবরণ:</b> {desc_text}</p>"
                            f"<div style='background: #e8f5e9; padding: 10px; border-radius: 8px; margin: 15px 0;'>"
                            f"<h3 align='center' style='color: #2E7D32; margin: 0;'>জমা: {inc_details[3]}</h3>"
                            f"</div>"
                            f"<br><br><p align='right' style='margin-bottom: 0;'>___________________<br><span style='font-size: 13px; color: gray;'>কর্তৃপক্ষের স্বাক্ষর</span></p>"
                            f"</div>"
                        )
                        st.markdown(income_html, unsafe_allow_html=True)
                        st.info("🖨️ প্রিন্ট করতে কীবোর্ড থেকে **Ctrl + P** চাপুন।")
                else:
                    st.info("কোনো আয়ের রেকর্ড পাওয়া যায়নি।")
            except Exception as e:
                conn.rollback()
                st.error(f"লোড এরর: {e}")

    # ==========================================
    # --- ট্যাব ৩: ফান্ডভিত্তিক ব্যালেন্স রিপোর্ট ---
    # ==========================================
    with tab_report:
        st.subheader("📊 ফান্ডভিত্তিক ব্যালেন্স ও ক্যাশবুক")
        
        try:
            # ছাত্রদের বেতন কালেকশন (সাধারণ তহবিল)
            cur.execute("SELECT SUM(amount_paid) FROM fees WHERE tenant_id=%s", (tenant_id,))
            fee_result = cur.fetchone()
            fee_income = fee_result[0] if fee_result[0] else 0
            
            # অন্যান্য ফান্ড কালেকশন
            cur.execute("SELECT source, SUM(amount) FROM other_incomes WHERE tenant_id=%s GROUP BY source", (tenant_id,))
            fund_incomes = dict(cur.fetchall())
            
            # ফান্ড ভিত্তিক খরচ
            cur.execute("SELECT fund_source, SUM(amount) FROM expenses WHERE tenant_id=%s GROUP BY fund_source", (tenant_id,))
            fund_expenses = dict(cur.fetchall())
            
            report_list = []
            
            # সাধারণ তহবিল হিসাব (বেতন + অন্যান্য সাধারণ আয়)
            gen_inc = fee_income + fund_incomes.get("সাধারণ তহবিল (General Fund)", 0)
            gen_exp = fund_expenses.get("সাধারণ তহবিল (General Fund)", 0)
            report_list.append(["সাধারণ তহবিল (General Fund)", gen_inc, gen_exp, gen_inc - gen_exp])
            
            # অন্যান্য ফান্ডের হিসাব
            for f in fund_categories:
                if f != "সাধারণ তহবিল (General Fund)":
                    f_inc = fund_incomes.get(f, 0)
                    f_exp = fund_expenses.get(f, 0)
                    report_list.append([f, f_inc, f_exp, f_inc - f_exp])
                    
            df_balance = pd.DataFrame(report_list, columns=["ফান্ডের নাম", "মোট জমা (৳)", "মোট খরচ (৳)", "বর্তমান ব্যালেন্স (৳)"])
            
            # --- ম্যাজিক: খাত অনুযায়ী আলাদা ফান্ড শো করা ---
            st.markdown("### 🏷️ খাত অনুযায়ী বর্তমান ফান্ডের অবস্থা")
            cols = st.columns(3)
            
            for i, row in df_balance.iterrows():
                fund_name = row["ফান্ডের নাম"].split(" (")[0] 
                bal = row['বর্তমান ব্যালেন্স (৳)']
                cols[i % 3].metric(label=f"🟢 {fund_name}", value=f"{bal:,.0f} ৳")
            
            st.markdown("<br>", unsafe_allow_html=True)
            
            # --- সর্বমোট শো করা ---
            total_cash = df_balance["বর্তমান ব্যালেন্স (৳)"].sum()
            st.success(f"## 🏦 সর্বমোট ক্যাশ-ইন-হ্যান্ড: {total_cash:,.0f} ৳")
            st.markdown("*(সবগুলো ফান্ডের টাকা মিলিয়ে মাদরাসার কাছে বর্তমানে এই পরিমাণ ক্যাশ আছে)*")
            
            st.markdown("---")
            st.markdown("### 📋 বিস্তারিত আয়-ব্যয় টেবিল")
            st.table(df_balance)
            
            # --- ভিজ্যুয়াল চার্ট ---
            st.divider()
            st.markdown("### 📌 ভিজ্যুয়াল অ্যানালিটিক্স (গ্রাফ)")
            chart_col1, chart_col2 = st.columns(2)
            
            with chart_col1:
                if not df_balance.empty:
                    st.write("**ফান্ডভিত্তিক বর্তমান ব্যালেন্স**")
                    df_chart_bal = df_balance.set_index("ফান্ডের নাম")[["বর্তমান ব্যালেন্স (৳)"]]
                    st.bar_chart(df_chart_bal, color="#2E7D32")
                    
            with chart_col2:
                cur.execute("SELECT category, SUM(amount) FROM expenses WHERE tenant_id=%s GROUP BY category", (tenant_id,))
                exp_chart_data = cur.fetchall()
                if exp_chart_data:
                    st.write("**খাতভিত্তিক মোট খরচের পরিমাণ**")
                    df_chart_exp = pd.DataFrame(exp_chart_data, columns=["খাত", "খরচ (৳)"]).set_index("খাত")
                    st.bar_chart(df_chart_exp, color="#d32f2f")
                else:
                    st.info("চার্ট দেখানোর মতো খরচের কোনো ডাটা নেই।")

        except Exception as e:
            conn.rollback()
            st.error(f"রিপোর্ট লোড এরর: {e}")

    cur.close()
