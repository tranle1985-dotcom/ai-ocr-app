import streamlit as st
import google.generativeai as genai
from PIL import Image
import pandas as pd
from datetime import datetime
import json
import requests
from io import BytesIO

# --- 1. CẤU HÌNH HỆ THỐNG ---
st.set_page_config(page_title="AI QLTT Thanh Hoá v5.0", layout="wide", page_icon="⚖️")

# Kết nối API
try:
    api_key = st.secrets["GOOGLE_API_KEY"]
    genai.configure(api_key=api_key)
except:
    st.error("❌ Không tìm thấy API Key trong Secrets!")

# --- HÀM TỰ ĐỘNG CHỌN MODEL KHẢ DỤNG (Xử lý lỗi 404) ---
def find_best_model():
    try:
        # Lấy danh sách tất cả model mà tài khoản của anh được dùng
        models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        
        # Danh sách ưu tiên từ mới đến cũ
        priorities = [
            'models/gemini-2.0-flash',
            'models/gemini-1.5-flash-latest',
            'models/gemini-1.5-flash',
            'models/gemini-pro-vision'
        ]
        
        for p in priorities:
            if p in models:
                return p
        return models[0] if models else None
    except Exception as e:
        return 'models/gemini-1.5-flash' # Mặc định nếu không liệt kê được

SELECTED_MODEL = find_best_model()

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
st.title("🛡️ Hệ thống Trích xuất Dữ liệu Pháp lý (v5.0)")
st.caption(f"🚀 Hệ thống đang chạy trên: **{SELECTED_MODEL}**")

col_in, col_out = st.columns([1, 1.2])

with col_in:
    source = st.camera_input("Chụp ảnh GCN Đăng ký kinh doanh")
    if not source:
        source = st.file_uploader("Hoặc tải ảnh lên", type=["jpg","jpeg","png"])

if source:
    img = Image.open(source)
    with col_in: st.image(img, use_container_width=True)
    
    if st.button("🚀 BẮT ĐẦU PHÂN TÍCH 15 TRƯỜNG"):
        with st.spinner("Đang bóc tách dữ liệu..."):
            try:
                model = genai.GenerativeModel(SELECTED_MODEL)
                
                # Prompt khôi phục đầy đủ 15 trường thông tin
                prompt = """
                Bạn là chuyên gia đọc hồ sơ pháp lý Việt Nam. Hãy trích xuất thông tin từ ảnh sang JSON. 
                JSON gồm các trường:
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
                Lưu ý: Chỉ trả về mã JSON, không thêm văn bản khác.
                """
                
                response = model.generate_content([prompt, img])
                res_text = response.text.strip()
                
                # Làm sạch JSON
                if "```" in res_text:
                    res_text = res_text.split("```")[1].replace("json", "").strip()
                
                data = json.loads(res_text)
                status, name_tax = check_mst_status(data.get('mst', data.get('so_gcn')))

                with col_out:
                    st.subheader("📋 Báo cáo Chi tiết")
                    if "Hoạt động" in status: st.success(status)
                    else: st.error(status)
                    
                    # Bảng hiển thị 15 trường
                    items = {
                        "Hạng mục": ["Tên Hộ/DN", "Mã số", "Địa chỉ", "Đại diện", "SĐT", "Giới tính/Ngày sinh", "CCCD", "Nơi cấp CCCD", "Chỗ ở", "Ngành nghề", "Ngày cấp", "Ngày thay đổi"],
                        "Thông tin": [
                            data.get('ten_hkd'), data.get('mst') or data.get('so_gcn'), data.get('dia_chi'), data.get('dai_dien'), data.get('phone'),
                            f"{data.get('gioi_tinh')} - {data.get('ngay_sinh')}", data.get('cccd'), data.get('noi_cap_cccd'), data.get('cho_o'),
                            data.get('nganh_nghe'), data.get('ngay_cap_dau'), data.get('ngay_thay_doi')
                        ]
                    }
                    st.table(pd.DataFrame(items))

                    # XUẤT EXCEL
                    df_excel = pd.DataFrame([data])
                    df_excel['Trạng thái thuế'] = status
                    output = BytesIO()
                    with pd.ExcelWriter(output, engine='openpyxl') as writer:
                        df_excel.to_excel(writer, index=False)
                    
                    st.download_button("📥 TẢI EXCEL FULL", output.getvalue(), f"QLTT_{data.get('mst')}.xlsx")

            except Exception as e:
                if "429" in str(e):
                    st.error("Hệ thống quá tải. Anh vui lòng đợi 1 phút.")
                else:
                    st.error(f"Sự cố: {e}")
