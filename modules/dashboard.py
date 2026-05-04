import streamlit as st
from database import get_connection
from datetime import datetime

def show_dashboard():
    tenant_id = st.session_state.get('tenant_id', 1)
    institute_name = st.session_state.get('madrasa_name', 'স্মার্ট মাদরাসা')

    # ==========================================
    # CSS স্টাইলিং (আপনার করা অসাধারণ ডিজাইন)
    # ==========================================
    st.markdown("""
        <style>
        div[data-testid="stAppViewContainer"] { background-color: #F4F7FE; font-family: 'Arial', sans-serif; }
        .white-card { 
            background: white; border-radius: 12px; padding: 20px; 
            box-shadow: 0px 4px 15px rgba(0,0,0,0.03); margin-bottom: 20px; height: 100%;
        }
        .top-header { display: flex; justify-content: space-between; align-items: center; padding: 10px 5px;}
        .top-title { font-size: 22px; font-weight: 700; color: #2B3674; margin: 0;}
        .top-year { font-size: 15px; font-weight: 600; color: #A3AED0; margin: 0;}

        .kpi-wrapper { display: flex; background: white; border-radius: 10px; padding: 15px 20px; box-shadow: 0px 4px 15px rgba(0,0,0,0.03); align-items: center;}
        .kpi-wrapper.c1 { border-left: 6px solid #FF8A65; } 
        .kpi-wrapper.c2 { border-left: 6px solid #4CAF50; } 
        .kpi-wrapper.c3 { border-left: 6px solid #5E35B1; } 
        .kpi-wrapper.c4 { border-left: 6px solid #E53935; } 
        .kpi-icon { font-size: 30px; margin-right: 15px; width: 50px; text-align: left; }
        .kpi-value { font-size: 24px; color: #2B3674; font-weight: 800; margin: 0;}
        .kpi-title { font-size: 14px; color: #A3AED0; font-weight: 600;}

        div[data-testid="stButton"] button {
            background-color: #F4F7FE !important; border: 1px solid #E0E5F2 !important;
            color: #2B3674 !important; border-radius: 8px !important; font-weight: 600 !important;
            padding: 12px !important; transition: all 0.3s ease !important; width: 100% !important;
        }
        div[data-testid="stButton"] button:hover {
            background-color: #5E35B1 !important; color: white !important;
            border-color: #5E35B1 !important; transform: translateY(-3px) !important;
            box-shadow: 0 4px 12px rgba(94,53,177,0.2) !important;
        }

        .student-card { border-radius: 15px; padding: 20px 10px; text-align: center; color: white; margin-top: 10px;}
        .sc-1 { background: linear-gradient(135deg, #4CAF50, #2E7D32); } 
        .sc-2 { background: linear-gradient(135deg, #7E57C2, #4527A0); } 
        .sc-3 { background: linear-gradient(135deg, #FFCA28, #FF8F00); } 
        .sec-title { font-size: 17px; font-weight: 700; color: #2B3674; margin-bottom: 15px; border-bottom: 1px solid #eee; padding-bottom: 10px;}
        .sc-rank { font-size: 14px; font-weight: bold; background: rgba(255,255,255,0.2); padding: 3px 10px; border-radius: 10px; display: inline-block; margin-top: 5px;}
        </style>
    """, unsafe_allow_html=True)

    # --- ডাটাবেস থেকে রিয়েল ডাটা সংগ্রহ ---
    conn = get_connection()
    total_students = 0
    today_attendance = 0
    expected_revenue = 0
    top_performers = []
    score_label = ""
    
    if conn:
        cur = conn.cursor()
        try:
            # মোট শিক্ষার্থী এবং সম্ভাব্য মাসিক আয় (Expected Revenue)
            cur.execute("SELECT COUNT(id), COALESCE(SUM(monthly_fee), 0) FROM students WHERE tenant_id = %s AND status = 'Active'", (tenant_id,))
            student_data = cur.fetchone()
            if student_data:
                total_students = student_data[0]
                expected_revenue = student_data[1]
            
            # আজকের উপস্থিতি
            today_str = datetime.now().date()
            cur.execute("SELECT COUNT(id) FROM attendance WHERE date = %s AND status = 'Present' AND tenant_id = %s", (today_str, tenant_id))
            att_count = cur.fetchone()
            today_attendance = att_count[0] if att_count else 0
            
            # --- রিয়েল সেরা শিক্ষার্থী খোঁজার স্মার্ট লজিক ---
            try:
                # প্রথমে চেষ্টা করবে পরীক্ষার রেজাল্ট অনুযায়ী বের করতে
                cur.execute("""
                    SELECT s.name, SUM(e.total_marks) as score
                    FROM students s
                    JOIN exam_results e ON s.id = e.student_id
                    WHERE s.tenant_id = %s AND e.tenant_id = %s AND s.status = 'Active'
                    GROUP BY s.id, s.name
                    ORDER BY score DESC
                    LIMIT 3
                """, (tenant_id, tenant_id))
                top_performers = cur.fetchall()
                score_label = "নম্বর"
                
                if not top_performers:
                    raise Exception("No Exam Data")
                    
            except Exception:
                conn.rollback()
                # রেজাল্ট টেবিল খালি থাকলে, সর্বোচ্চ হাজিরার ভিত্তিতে সেরা ৩ জন বের করবে
                cur.execute("""
                    SELECT s.name, COUNT(a.id) as score
                    FROM students s
                    JOIN attendance a ON s.id = a.student_id
                    WHERE s.tenant_id = %s AND a.tenant_id = %s AND a.status = 'Present' AND s.status = 'Active'
                    GROUP BY s.id, s.name
                    ORDER BY score DESC
                    LIMIT 3
                """, (tenant_id, tenant_id))
                top_performers = cur.fetchall()
                score_label = "দিন (উপস্থিতি)"
                
            cur.close()
        except Exception as e:
            conn.rollback()
            st.error(f"ড্যাশবোর্ড ডাটা লোড এরর: {e}")

    # ==========================================
    # ১. হেডার
    # ==========================================
    current_year = datetime.now().year
    st.markdown(f"<div class='white-card' style='padding: 15px 25px;'><div class='top-header'><p class='top-title'>স্বাগতম, {institute_name} ড্যাশবোর্ডে</p><p class='top-year'>শিক্ষাবর্ষ {current_year} 📚</p></div></div>", unsafe_allow_html=True)

    # ==========================================
    # ২. স্ট্যাটাস কার্ড (KPI)
    # ==========================================
    c1, c2, c3, c4 = st.columns(4)
    with c1: st.markdown(f"<div class='kpi-wrapper c1'><div class='kpi-icon'>👨‍🎓</div><div class='kpi-details'><div class='kpi-title'>মোট শিক্ষার্থী</div><div class='kpi-value'>{total_students} জন</div></div></div>", unsafe_allow_html=True)
    with c2: st.markdown(f"<div class='kpi-wrapper c2'><div class='kpi-icon'>✅</div><div class='kpi-details'><div class='kpi-title'>আজকের উপস্থিতি</div><div class='kpi-value'>{today_attendance} জন</div></div></div>", unsafe_allow_html=True)
    with c3: st.markdown(f"<div class='kpi-wrapper c3'><div class='kpi-icon'>💵</div><div class='kpi-details'><div class='kpi-title'>সম্ভাব্য মাসিক আয়</div><div class='kpi-value'>৳ {expected_revenue:,.0f}</div></div></div>", unsafe_allow_html=True)
    with c4: st.markdown("<div class='kpi-wrapper c4'><div class='kpi-icon'>⚠️</div><div class='kpi-details'><div class='kpi-title'>বকেয়া ফি</div><div class='kpi-value'>৳ ০</div></div></div>", unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # ==========================================
    # ৩. মাঝখানের সেকশন (চার্টস)
    # ==========================================
    col_mid1, col_mid2 = st.columns([1.2, 1])
    with col_mid1:
        st.markdown(f"<div class='white-card'><div class='sec-title'>হাজিরা ক্যালেন্ডার (ওভারভিউ)</div><div style='display: flex; justify-content: space-between; border-bottom: 4px solid #eee; padding-bottom: 5px; margin-bottom: 15px; color: #A3AED0; font-size:13px; font-weight: 600;'><span>{current_year-2}</span><span>{current_year-1}</span><span style='color: #5E35B1; border-bottom: 4px solid #5E35B1; padding-bottom: 5px; margin-bottom: -9px;'>{current_year}</span><span>{current_year+1}</span></div><div style='display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 12px; text-align: left; font-weight: bold; font-size: 14px;'><div style='padding: 10px; color: #4CAF50;'>জানুয়ারি</div><div style='padding: 10px; color: #FFCA28;'>ফেব্রুয়ারি</div><div style='padding: 10px; color: #FFCA28;'>মার্চ</div><div style='padding: 10px; background: #4CAF50; color: white; border-radius: 5px;'>এপ্রিল</div><div style='padding: 10px; color: #FFCA28;'>মে</div><div style='padding: 10px; color: #FFCA28;'>জুন</div><div style='padding: 10px; color: #FFCA28;'>জুলাই</div><div style='padding: 10px; color: #FFCA28;'>আগস্ট</div><div style='padding: 10px; color: #FFCA28;'>সেপ্টেম্বর</div></div></div>", unsafe_allow_html=True)
    with col_mid2:
        st.markdown(f"<div class='white-card'><div class='sec-title'>শিক্ষার্থী পরিসংখ্যান <span style='float:right; font-size:11px; color:#A3AED0; font-weight:normal; margin-top:5px;'>{current_year} এর ডাটা</span></div><div style='display: flex; justify-content: space-around; align-items: flex-end; height: 160px; padding-top: 20px; padding-bottom: 10px; border-bottom: 1px solid #eee;'><div style='text-align: center; width: 20%;'><div style='background: #5E35B1; height: 130px; width: 100%; border-radius: 4px 4px 0 0;'></div></div><div style='text-align: center; width: 20%;'><div style='background: #FFCA28; height: 80px; width: 100%; border-radius: 4px 4px 0 0;'></div></div><div style='text-align: center; width: 20%;'><div style='background: #4CAF50; height: 75px; width: 100%; border-radius: 4px 4px 0 0;'></div></div></div><div style='display: flex; justify-content: space-around; margin-top: 10px; font-size: 13px; font-weight: bold; color: #2B3674;'><span><span style='color:#5E35B1;'>●</span> হাইস্কুল</span><span><span style='color:#FFCA28;'>●</span> প্রাইমারি</span><span><span style='color:#4CAF50;'>●</span> হিফজ/মক্তব</span></div></div>", unsafe_allow_html=True)

    # ==========================================
    # ৪. নিচের সেকশন (কুইক অ্যাকশন এবং সেরা শিক্ষার্থী)
    # ==========================================
    col_left, col_right = st.columns([1, 1.5])

    with col_left:
        st.markdown("<div class='white-card'><div style='border-bottom: 1px solid #eee; padding-bottom: 10px; margin-bottom: 15px;'><span style='font-size: 17px; font-weight: 700; color: #2B3674;'>⚡ কুইক অ্যাকশন মেনু</span></div>", unsafe_allow_html=True)
        
        # পেজ নেভিগেশন ফাংশন
        def navigate_to(page_name):
            st.session_state.choice = page_name
            
        b_col1, b_col2 = st.columns(2)
        if b_col1.button("🎓 ভর্তি ফরম"):
            navigate_to("ভর্তি ফরম ও তালিকা")
            st.rerun()
        if b_col2.button("🏫 ক্লাস ম্যানেজমেন্ট"):
            navigate_to("ক্লাস ম্যানেজমেন্ট")
            st.rerun()
        if b_col1.button("📅 হাজিরা"):
            navigate_to("হাজিরা")
            st.rerun()
        if b_col2.button("💵 ফি কালেকশন"):
            navigate_to("বেতন ও ফি কালেকশন")
            st.rerun()
        if b_col1.button("📊 ফলাফল"):
            navigate_to("রেজাল্ট ও মার্কশিট")
            st.rerun()
        if b_col2.button("🪪 আইডি কার্ড"):
            navigate_to("আইডি কার্ড জেনারেটর")
            st.rerun()
            
        st.markdown("</div>", unsafe_allow_html=True)

    with col_right:
        st.markdown("<div class='white-card'><div class='sec-title' style='border:none; padding:0; margin-bottom:0;'>🏆 সেরা শিক্ষার্থী (Top Performers)</div>", unsafe_allow_html=True)
        
        if len(top_performers) > 0:
            cols = st.columns(3)
            bg_classes = ["sc-1", "sc-2", "sc-3"]
            avatars = ["👦🏻", "👧🏻", "👦🏽"]
            medals = ["১ম স্থান", "২য় স্থান", "৩য় স্থান"]
            
            for i in range(min(3, len(top_performers))):
                name = top_performers[i][0]
                score = top_performers[i][1]
                
                with cols[i]:
                    st.markdown(f"""
                    <div class='student-card {bg_classes[i]}'>
                        <div style='font-size:30px; margin-bottom:5px;'>{avatars[i]}</div>
                        <div style='font-size:15px; font-weight:600;'>{name}</div>
                        <div style='font-size:18px; font-weight:800; margin-top:5px;'>{score} {score_label}</div>
                        <div class='sc-rank'>{medals[i]}</div>
                    </div>
                    """, unsafe_allow_html=True)
        else:
            st.info("💡 পর্যাপ্ত ডাটা নেই। শিক্ষার্থী ভর্তি করে হাজিরা বা রেজাল্ট সেভ করুন, তাদের নাম এখানে অটোমেটিক চলে আসবে!")
            
        st.markdown("</div>", unsafe_allow_html=True)

    # ==========================================
    # ৫. মাদরাসা প্রোফাইল সেটিংস (ক্লায়েন্টদের জন্য)
    # ==========================================
    st.markdown("---")
    st.subheader("⚙️ মাদরাসা প্রোফাইল সেটিংস")
    
    # শুধুমাত্র অ্যাডমিনদের এই অপশন দেখাবে
    if st.session_state.get('role') == 'Admin':
        current_year = st.session_state.get('established_year', 2024)

        col1, col2 = st.columns([1, 2])
        with col1:
            new_year = st.number_input("মাদরাসার স্থাপিত সাল সেট করুন", 
                                       min_value=1800, 
                                       max_value=2100, 
                                       value=int(current_year))

            if st.button("সাল আপডেট করুন", type="primary", use_container_width=True):
                conn = get_connection()
                if conn:
                    cur = conn.cursor()
                    try:
                        cur.execute("UPDATE madrasas SET established_year = %s WHERE tenant_id = %s", (new_year, tenant_id))
                        conn.commit()
                        
                        # আপডেট সাথে সাথে কাজ করানোর জন্য
                        st.session_state['established_year'] = new_year
                        st.success(f"✅ সাল সফলভাবে {new_year}-এ আপডেট হয়েছে।")
                    except Exception as e:
                        conn.rollback()
                        st.error(f"আপডেট করতে সমস্যা হয়েছে: {e}")
                    finally:
                        if cur: cur.close()
    else:
        st.info("📌 প্রোফাইল সেটিংস পরিবর্তন করার জন্য মাদরাসা অ্যাডমিন হিসেবে লগিন করুন।")