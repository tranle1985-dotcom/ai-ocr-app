import streamlit as st
import google.generativeai as genai
from PIL import Image
import pandas as pd
from datetime import datetime
import json
import requests
from io import BytesIO

# --- 1. CẤU HÌNH HỆ THỐNG ---
st.set_page_config(page_title="AI Extractor Pro", layout="wide", page_icon="🛡️")

# Kết nối API
try:
    api_key = st.secrets["GOOGLE_API_KEY"]
    genai.configure(api_key=api_key)
except:
    st.error("❌ Không tìm thấy API Key trong Secrets!")

# --- HÀM TỰ ĐỘNG CHỌN MODEL (Sửa lỗi 404) ---
def get_available_model():
    try:
        models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        # Ưu tiên các dòng Flash vì nó nhanh và hạn mức cao
        priority_list = [
            'models/gemini-1.5-flash', 
            'models/gemini-1.5-flash-latest',
            'models/gemini-2.0-flash',
            'models/gemini-1.0-pro'
        ]
        for p in priority_list:
            if p in models:
                return p
        return models[0] if models else None
    except Exception as e:
        st.error(f"Lỗi liệt kê model: {e}")
        return 'models/gemini-1.5-flash' # Mặc định nếu lỗi

# Chọn model khả dụng
SELECTED_MODEL = get_available_model()

# --- 2. HÀM TRA CỨU MST ---
def check_mst_status(mst):
    mst_clean = "".join(filter(str.isdigit, str(mst)))
    if not mst_clean: return "MST không hợp lệ", ""
    try:
        url = f"https://api.vietqr.io/v2/business/{mst_clean}"
        res = requests.get(url, timeout=5).json()
        if res.get('code') == '00':
            return "Đang hoạt động ✅", res.get('data', {}).get('name', '')
        return "Ngừng hoạt động/Không tồn tại ❌", ""
    except:
        return "Lỗi kết nối tra cứu ⚠️", ""

# --- 3. GIAO DIỆN ---
st.title("🛡️ Hệ thống Đối soát AI v2.2")
st.caption(f"Đang sử dụng Model: **{SELECTED_MODEL}**")

col_in, col_out = st.columns([1, 1])

with col_in:
    source = st.camera_input("Chụp ảnh giấy phép")
    if not source:
        source = st.file_uploader("Hoặc tải ảnh lên", type=["jpg","jpeg","png"])

if source:
    img = Image.open(source)
    with col_in: st.image(img, use_container_width=True)
    
    if st.button("🚀 BẮT ĐẦU PHÂN TÍCH"):
        with st.spinner("AI đang làm việc..."):
            try:
                model = genai.GenerativeModel(SELECTED_MODEL)
                prompt = "Đọc ảnh Đăng ký kinh doanh. Trả về duy nhất mã JSON (không kèm lời dẫn): {ten, mst, diachi, daidien, nganh, ngaycap}"
                
                response = model.generate_content([prompt, img])
                res_text = response.text.strip()
                
                # Làm sạch JSON
                if "```" in res_text:
                    res_text = res_text.split("```")[1].replace("json", "").strip()
                
                data = json.loads(res_text)
                status, name_tax = check_mst_status(data.get('mst', ''))

                with col_out:
                    st.subheader("📋 Kết quả đối soát")
                    if "Hoạt động" in status: st.success(status)
                    else: st.error(status)
                    
                    st.write(f"🏢 **Tên:** {data.get('ten')}")
                    st.write(f"🆔 **MST:** {data.get('mst')}")
                    st.write(f"👤 **Đại diện:** {data.get('daidien')}")
                    st.write(f"📍 **Địa chỉ:** {data.get('diachi')}")
                    st.write(f"📝 **Ngành:** {data.get('nganh')}")
                    
                    # Xuất Excel
                    df = pd.DataFrame([data])
                    df['Trạng thái'] = status
                    output = BytesIO()
                    with pd.ExcelWriter(output, engine='openpyxl') as writer:
                        df.to_excel(writer, index=False)
                    
                    st.divider()
                    st.download_button("📥 TẢI FILE EXCEL", output.getvalue(), f"KQ_{data.get('mst')}.xlsx")

            except Exception as e:
                st.error(f"Sự cố: {e}")
                st.info("Hãy thử nhấn lại lần nữa hoặc kiểm tra kết nối mạng.")
