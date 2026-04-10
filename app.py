import streamlit as st
import google.generativeai as genai
from PIL import Image
import pandas as pd
from datetime import datetime
import json
import requests
from io import BytesIO

# --- 1. CẤU HÌNH HỆ THỐNG ---
st.set_page_config(page_title="AI Kiểm Tra Kinh Doanh", layout="wide", page_icon="🛡️")

# Lấy API Key an toàn
try:
    api_key = st.secrets["GOOGLE_API_KEY"]
    genai.configure(api_key=api_key)
except:
    st.error("⚠️ Lỗi: Không tìm thấy GOOGLE_API_KEY trong mục Secrets!")

# ĐỔI SANG MODEL 1.5 FLASH ĐỂ CÓ HẠN MỨC CAO HƠN
MODEL_NAME = 'gemini-1.5-flash' 

# --- 2. HÀM TRA CỨU TRẠNG THÁI THUẾ ---
def check_mst_status(mst):
    mst_clean = mst.replace('.', '').replace(' ', '').replace('-', '').strip()
    if not mst_clean: return "Không có MST", ""
    try:
        # Tra cứu qua API VietQR (Hỗ trợ dữ liệu doanh nghiệp VN)
        url = f"https://api.vietqr.io/v2/business/{mst_clean}"
        res = requests.get(url, timeout=5).json()
        if res.get('code') == '00':
            return "Đang hoạt động ✅", res.get('data', {}).get('name', '')
        return "Ngừng hoạt động/Không tồn tại ❌", ""
    except:
        return "Lỗi kết nối tra cứu ⚠️", ""

# --- 3. GIAO DIỆN ---
st.title("🛡️ Hệ thống Đối soát AI (Bản 1.5 Flash)")
st.info("Phiên bản tối ưu hạn mức - Hoạt động ổn định hơn cho nhiều người dùng.")

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
                model = genai.GenerativeModel(MODEL_NAME)
                # Prompt tối ưu để AI không trả về rác
                prompt = "Đọc ảnh Đăng ký kinh doanh. Trả về duy nhất 1 mã JSON với các trường: ten, mst, diachi, daidien, nganh, ngaycap. Không thêm lời dẫn."
                
                response = model.generate_content([prompt, img])
                res_text = response.text.strip()
                
                # Làm sạch dữ liệu JSON
                if "```json" in res_text:
                    res_text = res_text.split("```json")[1].split("```")[0].strip()
                elif "```" in res_text:
                    res_text = res_text.split("```")[1].strip()
                
                data = json.loads(res_text)
                
                # Tra cứu trạng thái thuế
                status, name_tax = check_mst_status(data.get('mst', ''))

                with col_out:
                    st.subheader("📋 Kết quả đối soát")
                    if "Hoạt động" in status: st.success(status)
                    else: st.error(status)
                    
                    st.write(f"🏢 **Tên hộ/DN:** {data.get('ten', 'N/A')}")
                    if name_tax: st.caption(f"(Hệ thống thuế: {name_tax})")
                    st.write(f"🆔 **Mã số:** {data.get('mst', 'N/A')}")
                    st.write(f"👤 **Đại diện:** {data.get('daidien', 'N/A')}")
                    st.write(f"📍 **Địa chỉ:** {data.get('diachi', 'N/A')}")
                    st.write(f"📝 **Ngành nghề:** {data.get('nganh', 'N/A')}")
                    
                    # Chuẩn bị file Excel
                    df_export = pd.DataFrame([{
                        "Thời gian": datetime.now().strftime("%d/%m/%Y %H:%M"),
                        "MST": data.get('mst'),
                        "Tên": data.get('ten'),
                        "Trạng thái": status,
                        "Địa chỉ": data.get('diachi'),
                        "Ngành nghề": data.get('nganh')
                    }])
                    
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
                st.error(f"Sự cố: {e}")
                st.info("Có thể bạn đã hết lượt dùng trong phút này. Hãy đợi 30 giây rồi nhấn lại.")
