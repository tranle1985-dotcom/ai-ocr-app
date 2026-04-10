import streamlit as st
import google.generativeai as genai
from PIL import Image
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime
import json
import requests

# --- 1. CẤU HÌNH TRANG & GIAO DIỆN ---
st.set_page_config(page_title="Hệ thống Kiểm soát Kinh doanh AI", layout="wide", page_icon="🛡️")

# CSS tùy chỉnh để giao diện chuyên nghiệp hơn
st.markdown("""
    <style>
    .main { background-color: #f5f7f9; }
    .stButton>button { width: 100%; border-radius: 5px; height: 3em; background-color: #007bff; color: white; }
    .stMetric { background-color: #ffffff; padding: 15px; border-radius: 10px; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }
    </style>
    """, unsafe_allow_html=True)

# Kết nối Google Sheets & AI
conn = st.connection("gsheets", type=GSheetsConnection)
genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
model = genai.GenerativeModel('gemini-3-flash-preview')

# --- 2. CÁC HÀM BỔ TRỢ ---
def check_mst_status(mst):
    """Tra cứu trạng thái MST từ API công khai"""
    mst_clean = mst.replace('.', '').replace(' ', '').replace('-', '').strip()
    try:
        url = f"https://api.vietqr.io/v2/business/{mst_clean}"
        res = requests.get(url, timeout=5).json()
        if res.get('code') == '00':
            return "Đang hoạt động ✅", res.get('data', {}).get('name', '')
        return "Ngừng hoạt động/Không tồn tại ❌", ""
    except:
        return "Lỗi kết nối tra cứu ⚠️", ""

# --- 3. SIDEBAR (THANH BÊN) ---
with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/1041/1041916.png", width=100)
    st.title("QUẢN LÝ THỊ TRƯỜNG")
    st.divider()
    st.write("👤 **Cán bộ:** Trần Lê")
    st.write("📍 **Đơn vị:** Đội QLTT số 10")
    st.divider()
    if st.button("Làm mới hệ thống"):
        st.rerun()

# --- 4. NỘI DUNG CHÍNH ---
st.title("🛡️ Hệ thống Giám sát & Xác thực Kinh doanh")

tab1, tab2, tab3 = st.tabs(["🔍 KIỂM TRA MỚI", "📋 NHẬT KÝ HỆ THỐNG", "📊 THỐNG KÊ"])

with tab1:
    c1, c2 = st.columns([1, 1])
    
    with c1:
        st.subheader("Đầu vào dữ liệu")
        mode = st.radio("Phương thức:", ["Camera điện thoại", "Tải tệp lên"], horizontal=True)
        source = st.camera_input("Chụp ảnh") if mode == "Camera điện thoại" else st.file_uploader("Chọn ảnh", type=["jpg","png","jpeg"])

    if source:
        img = Image.open(source)
        with c1: st.image(img, caption="Ảnh đã nạp", use_container_width=True)
        
        if st.button("BẮT ĐẦU ĐỐI SOÁT DỮ LIỆU"):
            with st.spinner("Đang phân tích pháp lý..."):
                try:
                    # AI trích xuất
                    prompt = "Trích xuất thông tin ĐKKD sang JSON: {ten, mst, diachi, daidien, nganh, ngaycap}"
                    raw_res = model.generate_content([prompt, img])
                    data = json.loads(raw_res.text.replace('```json', '').replace('```', '').strip())
                    
                    # Tra cứu thuế
                    status, name_tax = check_mst_status(data['mst'])

                    with c2:
                        st.subheader("Kết quả đối soát")
                        if "Hoạt động" in status: st.success(status)
                        else: st.error(status)
                        
                        st.write(f"🏢 **Tên hộ/DN:** {data['ten']}")
                        if name_tax: st.caption(f"(Tên gốc: {name_tax})")
                        st.write(f"🆔 **Mã số:** {data['mst']}")
                        st.write(f"👤 **Đại diện:** {data['daidien']}")
                        st.write(f"📍 **Địa chỉ:** {data['diachi']}")
                        st.write(f"📝 **Ngành nghề:** {data['nganh']}")

                        # Lưu vào Sheets
                        new_data = pd.DataFrame([{
                            "Thời gian": datetime.now().strftime("%d/%m/%Y %H:%M"),
                            "MST": data['mst'],
                            "Cơ sở": data['ten'],
                            "Trạng thái": status,
                            "Địa chỉ": data['diachi'],
                            "Đại diện": data['daidien']
                        }])
                        
                        old_data = conn.read(worksheet="Sheet1")
                        combined = pd.concat([old_data, new_data], ignore_index=True)
                        conn.update(worksheet="Sheet1", data=combined)
                        st.toast("Đã đồng bộ dữ liệu lên Cloud!")

                except Exception as e:
                    st.error("AI không đọc được ảnh. Vui lòng chụp rõ hơn.")

with tab2:
    st.subheader("Lịch sử kiểm tra toàn địa bàn")
    df_logs = conn.read(worksheet="Sheet1")
    st.dataframe(df_logs.sort_values(by="Thời gian", ascending=False), use_container_width=True)

with tab3:
    st.subheader("Báo cáo nhanh")
    df_stat = conn.read(worksheet="Sheet1")
    m1, m2, m3 = st.columns(3)
    m1.metric("Tổng lượt quét", len(df_stat))
    m2.metric("Số cơ sở Đang hoạt động", len(df_stat[df_stat['Trạng thái'].str.contains("Hoạt động")]))
    m3.metric("Số cơ sở Bất thường", len(df_stat[~df_stat['Trạng thái'].str.contains("Hoạt động")]))
