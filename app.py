import streamlit as st
import google.generativeai as genai
from PIL import Image
import pandas as pd
from datetime import datetime
import json
import requests
from io import BytesIO

# --- 1. CẤU HÌNH HỆ THỐNG ---
st.set_page_config(page_title="AI Extractor Pro", layout="wide", page_icon="📑")

# Lấy API Key từ Secrets
try:
    api_key = st.secrets["GOOGLE_API_KEY"]
    genai.configure(api_key=api_key)
except:
    st.error("❌ Chưa tìm thấy API Key trong mục Secrets của Streamlit!")

# Thử nghiệm với model ổn định nhất hiện tại
MODEL_NAME = 'gemini-2.0-flash' # Đổi về bản 2.0 để ổn định nhất

# --- 2. HÀM TRA CỨU MST ---
def check_mst_status(mst):
    mst_clean = mst.replace('.', '').replace(' ', '').replace('-', '').strip()
    try:
        url = f"https://api.vietqr.io/v2/business/{mst_clean}"
        res = requests.get(url, timeout=5).json()
        if res.get('code') == '00':
            return "Đang hoạt động ✅", res.get('data', {}).get('name', '')
        return "Ngừng hoạt động/Không tồn tại ❌", ""
    except:
        return "Lỗi kết nối tra cứu ⚠️", ""

# --- 3. GIAO DIỆN CHÍNH ---
st.title("🛡️ AI Đối soát Hộ kinh doanh v2.1")

col_in, col_out = st.columns([1, 1])

with col_in:
    st.subheader("📸 Chụp ảnh hoặc Tải file")
    source = st.camera_input("Chụp ảnh giấy phép")
    if not source:
        source = st.file_uploader("Hoặc chọn ảnh từ máy", type=["jpg","jpeg","png"])

if source:
    img = Image.open(source)
    with col_in:
        st.image(img, caption="Ảnh hiện trường", use_container_width=True)
    
    if st.button("🚀 BẮT ĐẦU PHÂN TÍCH"):
        with st.spinner("Đang đọc dữ liệu..."):
            try:
                model = genai.GenerativeModel(MODEL_NAME)
                prompt = "Trích xuất thông tin từ ảnh sang định dạng JSON chính xác với các trường: ten, mst, diachi, daidien, nganh, ngaycap. Chỉ trả về mã JSON, không kèm lời giải thích."
                
                response = model.generate_content([prompt, img])
                res_text = response.text.strip()
                
                # --- TỰ ĐỘNG LÀM SẠCH JSON (Fix lỗi hay gặp nhất) ---
                if "```json" in res_text:
                    res_text = res_text.split("```json")[1].split("```")[0].strip()
                elif "```" in res_text:
                    res_text = res_text.split("```")[1].strip()
                
                data = json.loads(res_text)
                
                # Tra cứu thuế
                status, name_tax = check_mst_status(data.get('mst', ''))

                with col_out:
                    st.subheader("📋 Kết quả xác thực")
                    if "Hoạt động" in status: st.success(status)
                    else: st.error(status)
                    
                    st.write(f"🏢 **Tên cơ sở:** {data.get('ten', 'N/A')}")
                    if name_tax: st.caption(f"(Tên trên hệ thống thuế: {name_tax})")
                    st.write(f"🆔 **Mã số:** {data.get('mst', 'N/A')}")
                    st.write(f"👤 **Đại diện:** {data.get('daidien', 'N/A')}")
                    st.write(f"📍 **Địa chỉ:** {data.get('diachi', 'N/A')}")
                    st.write(f"📝 **Ngành nghề:** {data.get('nganh', 'N/A')}")
                    
                    # Xuất Excel
                    df_export = pd.DataFrame([data])
                    df_export['Trạng thái thuế'] = status
                    df_export['Thời gian'] = datetime.now().strftime("%d/%m/%Y %H:%M")
                    
                    output = BytesIO()
                    with pd.ExcelWriter(output, engine='openpyxl') as writer:
                        df_export.to_excel(writer, index=False)
                    
                    st.divider()
                    st.download_button(
                        label="📥 TẢI FILE EXCEL",
                        data=output.getvalue(),
                        file_name=f"KetQua_{data.get('mst', 'HKD')}.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                    )

            except Exception as e:
                st.error("🚨 ĐÃ XẢY RA LỖI:")
                st.code(f"{e}") # Hiện lỗi thật để biết đường sửa
                st.info("Mẹo: Hãy thử nhấn nút Phân tích lại hoặc chụp ảnh rõ nét hơn.")
