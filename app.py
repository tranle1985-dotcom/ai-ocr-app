import streamlit as st
import google.generativeai as genai
from PIL import Image
import pandas as pd
from datetime import datetime
import json
import requests
from io import BytesIO

# --- 1. CẤU HÌNH HỆ THỐNG ---
st.set_page_config(page_title="AI Kiểm tra Thị trường - Phiên bản Excel", layout="wide", page_icon="📑")

# Giao diện Sidebar
with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/1041/1041916.png", width=80)
    st.title("QLTT THANH HÓA")
    st.info("Phiên bản xuất Excel độc lập cho từng địa bàn.")
    st.divider()
    st.caption("Ứng dụng sử dụng Gemini 3 Flash & API Thuế Quốc gia.")

# Cấu hình AI
genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
model = genai.GenerativeModel('gemini-3-flash-preview')

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
st.title("🛡️ Trích xuất & Đối soát Hộ kinh doanh")

col_in, col_out = st.columns([1, 1])

with col_in:
    st.subheader("📸 Thu thập dữ liệu")
    mode = st.radio("Chọn nguồn:", ["Máy ảnh (Di động)", "Tải ảnh lên"], horizontal=True)
    source = st.camera_input("Chụp trực tiếp") if mode == "Máy ảnh (Di động)" else st.file_uploader("Chọn tệp ảnh", type=["jpg","jpeg","png"])

if source:
    img = Image.open(source)
    with col_in:
        st.image(img, caption="Ảnh hiện trường", use_container_width=True)
    
    if st.button("🔍 PHÂN TÍCH & ĐỐI SOÁT"):
        with st.spinner("AI đang đọc dữ liệu và tra cứu thuế..."):
            try:
                # AI đọc thông tin
                prompt = "Trích xuất JSON: {ten, mst, diachi, daidien, nganh, ngaycap}"
                raw_res = model.generate_content([prompt, img])
                data = json.loads(raw_res.text.replace('```json', '').replace('```', '').strip())
                
                # Tra cứu thuế
                status, name_tax = check_mst_status(data['mst'])

                with col_out:
                    st.subheader("📋 Kết quả xác thực")
                    
                    # Cảnh báo trạng thái
                    if "Hoạt động" in status:
                        st.success(status)
                    else:
                        st.error(status)
                    
                    # Hiển thị thông tin chi tiết
                    st.write(f"🏢 **Tên cơ sở:** {data['ten']}")
                    if name_tax: st.caption(f"(Tên trên hệ thống thuế: {name_tax})")
                    st.write(f"🆔 **Mã số:** {data['mst']}")
                    st.write(f"👤 **Đại diện:** {data['daidien']}")
                    st.write(f"📍 **Địa chỉ:** {data['diachi']}")
                    st.write(f"📝 **Ngành nghề:** {data['nganh']}")
                    
                    # Tạo DataFrame để chuẩn bị xuất Excel
                    df_export = pd.DataFrame([{
                        "Thời gian quét": datetime.now().strftime("%d/%m/%Y %H:%M"),
                        "Mã số thuế": data['mst'],
                        "Tên cơ sở": data['ten'],
                        "Trạng thái thuế": status,
                        "Địa chỉ": data['diachi'],
                        "Người đại diện": data['daidien'],
                        "Ngành nghề": data['nganh'],
                        "Ngày cấp phép": data['ngaycap']
                    }])

                    # Xử lý xuất file Excel
                    output = BytesIO()
                    with pd.ExcelWriter(output, engine='openpyxl') as writer:
                        df_export.to_excel(writer, index=False, sheet_name='KiemTra')
                    excel_data = output.getvalue()

                    st.divider()
                    st.download_button(
                        label="📥 TẢI FILE EXCEL KẾT QUẢ",
                        data=excel_data,
                        file_name=f"KiemTra_{data['mst']}.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                    )
                    st.balloons()

            except Exception as e:
                st.error("Lỗi: AI không thể đọc rõ ảnh hoặc lỗi API. Vui lòng chụp lại rõ nét hơn.")
