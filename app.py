import streamlit as st
import google.generativeai as genai
from PIL import Image
import pandas as pd
from datetime import datetime
import json
import requests
from io import BytesIO

# --- 1. CẤU HÌNH HỆ THỐNG ---
st.set_page_config(page_title="AI QLTT Nga Sơn v4.0", layout="wide", page_icon="⚖️")

# Kết nối API
try:
    api_key = st.secrets["GOOGLE_API_KEY"]
    genai.configure(api_key=api_key)
except:
    st.error("❌ Không tìm thấy API Key trong Secrets!")

# Dùng model Gemini 3 Flash mới nhất cho năm 2026
MODEL_NAME = 'gemini-3-flash'

# --- 2. HÀM TRA CỨU MST ---
def check_mst_status(mst):
    mst_clean = "".join(filter(str.isdigit, str(mst)))
    if not mst_clean: return "Chưa rõ", ""
    try:
        url = f"https://api.vietqr.io/v2/business/{mst_clean}"
        res = requests.get(url, timeout=5).json()
        if res.get('code') == '00':
            return "Đang hoạt động ✅", res.get('data', {}).get('name', '')
        return "Ngừng hoạt động/Đóng MST ❌", ""
    except:
        return "Lỗi API Thuế ⚠️", ""

# --- 3. GIAO DIỆN ---
st.title("🛡️ Hệ thống Trích xuất Dữ liệu Pháp lý (v4.0)")
st.info("Ứng dụng chuyên dụng cho cán bộ QLTT Thanh Hoá - Trích xuất 15 trường dữ liệu.")

col_in, col_out = st.columns([1, 1.2])

with col_in:
    source = st.camera_input("Chụp ảnh GCN Đăng ký kinh doanh")
    if not source:
        source = st.file_uploader("Hoặc tải ảnh lên", type=["jpg","jpeg","png"])

if source:
    img = Image.open(source)
    with col_in: st.image(img, use_container_width=True)
    
    if st.button("🚀 BẮT ĐẦU PHÂN TÍCH CHI TIẾT"):
        with st.spinner("Đang sử dụng Gemini 3 Flash để bóc tách dữ liệu..."):
            try:
                model = genai.GenerativeModel(MODEL_NAME)
                
                # Prompt khôi phục đầy đủ 15 trường thông tin như anh yêu cầu
                prompt = """
                Bạn là chuyên gia đọc hồ sơ pháp lý Việt Nam. Hãy trích xuất thông tin từ ảnh sang JSON. 
                Dữ liệu phải cực kỳ chính xác. JSON gồm các trường:
                {
                    "so_gcn": "Số giấy chứng nhận/Mã số hộ",
                    "ten_hkd": "Tên hộ kinh doanh/Doanh nghiệp",
                    "mst": "Mã số thuế",
                    "dia_chi": "Địa chỉ trụ sở chính",
                    "dai_dien": "Họ tên người đại diện",
                    "phone": "Số điện thoại",
                    "gioi_tinh": "Giới tính",
                    "ngay_sinh": "Ngày sinh",
                    "cccd": "Số CCCD/Hộ chiếu",
                    "ngay_cap_cccd": "Ngày cấp CCCD",
                    "noi_cap_cccd": "Nơi cấp CCCD",
                    "cho_o": "Chỗ ở hiện nay",
                    "nganh_nghe": "Ngành nghề kinh doanh",
                    "ngay_cap_dau": "Ngày đăng ký lần đầu",
                    "ngay_thay_doi": "Ngày thay đổi gần nhất"
                }
                Chỉ trả về mã JSON, không thêm văn bản khác.
                """
                
                response = model.generate_content([prompt, img])
                res_text = response.text.strip()
                
                # Làm sạch JSON đề phòng AI trả về Markdown
                if "```" in res_text:
                    res_text = res_text.split("```")[1].replace("json", "").strip()
                
                data = json.loads(res_text)
                
                # Đối soát MST trực tuyến
                status, name_tax = check_mst_status(data.get('mst', data.get('so_gcn')))

                with col_out:
                    st.subheader("📋 Báo cáo Chi tiết")
                    if "Hoạt động" in status: st.success(status)
                    else: st.error(status)
                    
                    # Trình bày dữ liệu 15 trường vào bảng
                    df_view = pd.DataFrame({
                        "Hạng mục": [
                            "Tên Hộ/DN", "Mã số (GCN/MST)", "Địa chỉ trụ sở", "Người đại diện", 
                            "Điện thoại", "Giới tính", "Ngày sinh", "Số CCCD", 
                            "Ngày/Nơi cấp CCCD", "Chỗ ở hiện nay", "Ngành nghề kinh doanh", 
                            "Ngày cấp lần đầu", "Thay đổi gần nhất"
                        ],
                        "Thông tin trích xuất": [
                            data.get('ten_hkd'),
                            data.get('mst') or data.get('so_gcn'),
                            data.get('dia_chi'),
                            data.get('dai_dien'),
                            data.get('phone'),
                            data.get('gioi_tinh'),
                            data.get('ngay_sinh'),
                            data.get('cccd'),
                            f"{data.get('ngay_cap_cccd')} tại {data.get('noi_cap_cccd')}",
                            data.get('cho_o'),
                            data.get('nganh_nghe'),
                            data.get('ngay_cap_dau'),
                            data.get('ngay_thay_doi')
                        ]
                    })
                    st.table(df_view)

                    # --- XUẤT EXCEL ---
                    df_excel = pd.DataFrame([data])
                    df_excel['Trạng thái thuế'] = status
                    output = BytesIO()
                    with pd.ExcelWriter(output, engine='openpyxl') as writer:
                        df_excel.to_excel(writer, index=False)
                    
                    st.download_button(
                        label="📥 TẢI EXCEL FULL 15 TRƯỜNG",
                        data=output.getvalue(),
                        file_name=f"QLTT_NgaSon_{data.get('mst') or data.get('so_gcn')}.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                    )

            except Exception as e:
                st.error(f"Sự cố kỹ thuật: {e}")
                st.info("Anh hãy thử nhấn lại hoặc kiểm tra xem ảnh có bị lóa sáng không nhé.")
