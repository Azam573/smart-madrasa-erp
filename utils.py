import requests
from database import get_connection

def send_sms(tenant_id, phone_number, message):
    """
    SaaS মডেলে প্রতিটি মাদরাসার নিজস্ব API Key দিয়ে SMS পাঠানোর ফাংশন।
    """
    if not phone_number or len(str(phone_number)) < 11:
        return False, "অবৈধ মোবাইল নাম্বার"

    conn = get_connection()
    if not conn:
        return False, "ডাটাবেস কানেকশন নেই"
        
    try:
        cur = conn.cursor()
        # ওই নির্দিষ্ট মাদরাসার SMS API সেটিং খুঁজে বের করা
        cur.execute("SELECT sms_api_key, sms_sender_id, is_sms_active FROM madrasas WHERE tenant_id = %s", (tenant_id,))
        sms_settings = cur.fetchone()
        cur.close()
        
        if not sms_settings:
            return False, "মাদরাসার তথ্য পাওয়া যায়নি।"
            
        api_key, sender_id, is_sms_active = sms_settings
        
        if not is_sms_active or not api_key:
            return False, "এই মাদরাসার SMS সার্ভিস অ্যাক্টিভ নেই বা API Key বসানো নেই।"

        # API তে রিকোয়েস্ট পাঠানো
        url = "http://api.bulksmsbd.net/api/smsapi"
        payload = {
            "api_key": api_key,
            "type": "unicode",
            "number": phone_number,
            "senderid": sender_id,
            "message": message
        }
        
        response = requests.get(url, params=payload)
        
        if response.status_code == 200:
            return True, "SMS সফলভাবে পাঠানো হয়েছে!"
        else:
            return False, f"SMS গেটওয়ে এরর: {response.status_code}"
            
    except Exception as e:
        return False, f"সিস্টেম এরর: {e}"