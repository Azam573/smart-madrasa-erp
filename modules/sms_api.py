import requests
import streamlit as st

def send_real_sms(number, text):
    """
    এই ফাংশনটি রিয়েল SMS পাঠাবে। 
    আপাতত এটি স্ক্রিনে নোটিফিকেশন দেখাবে। API কেনার পর কমেন্ট মুছে দিলে আসল মোবাইলে যাবে।
    """
    if not number or len(str(number)) < 11:
        return False
        
    # বাংলাদেশের যেকোনো SMS প্রোভাইডার থেকে কেনা API এখানে বসবে
    API_KEY = "YOUR_API_KEY_HERE"
    SENDER_ID = "YOUR_SENDER_ID"
    
    # এটি একটি ডেমো URL, প্রোভাইডার আপনাকে আসল URL বা API লিঙ্ক দেবে
    url = f"http://bulksmsbd.net/api/smsapi?api_key={API_KEY}&type=text&number={number}&senderid={SENDER_ID}&message={text}"
    
    try:
        # ⚠️ আসল SMS পাঠাতে নিচের ২ লাইনের সামনের '#' চিহ্নটি মুছে দিন:
        # response = requests.get(url)
        # if response.status_code == 200: return True
        
        # আপাতত টেস্টিংয়ের জন্য স্ক্রিনে মেসেজ দেখাবে (টাকা কাটবে না)
        st.toast(f"📩 SMS পাঠানো হয়েছে ({number}): {text}", icon="✅")
        return True
    except Exception as e:
        print("SMS Error:", e)
        return False