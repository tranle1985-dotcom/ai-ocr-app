import streamlit as st
import google.generativeai as genai
from PIL import Image
import pandas as pd
import json
import requests
from io import BytesIO

# --- CẤU HÌNH ---
st.set_page_config(page_title="AI QLTT - Tối ưu Quota", layout="wide")

# Kết nối API
try:
    api_key = st.secrets["GOOGLE_API_KEY"]
    genai.configure(api_key=api_key)
except:
    st.error("Chưa cấu hình API Key trong Secrets!")

# ÉP DÙNG 1.5 FLASH ĐỂ TRÁNH LỖI 429 CỦA BẢN 2.0
MODEL_NAME = 'gemini-1.5-flash'

def check_mst_status(mst):
    mst_clean = "".join(filter(str.isdigit, str(mst)))
    if not mst_clean: return "MST trống", ""
    try:
        url = f"https://api.vietqr.io/v2/business/{mst_clean}"
        res = requests.get(url, timeout=5).json()
        if res.get('code') == '00':
            return "Đang hoạt động ✅", res.get('data', {}).get('name', '')
        return "Ngừng hoạt động ❌", ""
    except:
        return "Lỗi API Thuế ⚠️", ""

# --- GIAO DIỆN ---
st.title("🛡️ AI Đối soát Kinh doanh (v2.3)")
st.warning("⚠️ Lưu ý: Nếu gặp lỗi 429, hãy đợi 1 phút trước khi nhấn lại. Không nhấn liên tục.")

col1, col2 = st.columns(2)

with col1:
    source = st.camera_input("Chụp ảnh")
    if not source:
        source = st.file_uploader("Tải ảnh", type=["jpg","png","jpeg"])

if source:
    img = Image.open(source)
    with col1: st.image(img, use_container_width=True)
    
    if st.button("🚀 PHÂN TÍCH NGAY"):
        with st.spinner("Đang xử lý (Vui lòng không nhấn thêm)..."):
            try:
                model = genai.GenerativeModel(MODEL_NAME)
                # Prompt ngắn gọn để tiết kiệm Token
                prompt = "Read business license. Return JSON only: {ten, mst, diachi, daidien, nganh, ngaycap}"
                
                response = model.generate_content([prompt, img])
                res_text = response.text.strip()
                
                if "```" in res_text:
                    res_text = res_text.split("```")[1].replace("json", "").strip()
                
                data = json.loads(res_text)
                status, name_tax = check_mst_status(data.get('mst', ''))

                with col2:
                    st.subheader("Kết quả")
                    if "Hoạt động" in status: st.success(status)
                    else: st.error(status)
                    
                    st.write(f"🏢 **Tên:** {data.get('ten')}")
                    st.write(f"🆔 **MST:** {data.get('mst')}")
                    st.write(f"👤 **Đại diện:** {data.get('daidien')}")
                    
                    df = pd.DataFrame([data])
                    df['Trạng thái'] = status
                    output = BytesIO()
                    with pd.ExcelWriter(output, engine='openpyxl') as writer:
                        df.to_excel(writer, index=False)
                    
                    st.download_button("📥 TẢI EXCEL", output.getvalue(), f"KQ_{data.get('mst')}.xlsx")

            except Exception as e:
                if "429" in str(e):
                    st.error("Hệ thống AI đang quá tải lượt dùng. Vui lòng nghỉ 1 phút rồi thử lại.")
                else:
                    st.error(f"Sự cố: {e}")
