import streamlit as st
import google.generativeai as genai
from PIL import Image
import pandas as pd
import json
import requests
from io import BytesIO

# --- 1. CẤU HÌNH HỆ THỐNG ---
st.set_page_config(page_title="AI QLTT v5.4 - Fix 404", layout="wide", page_icon="🛡️")

# Kết nối API
if "GOOGLE_API_KEY" in st.secrets:
    genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
else:
    st.error("❌ Thiếu API Key trong Secrets!")

# --- HÀM TÌM MODEL KHẢ DỤNG (QUAN TRỌNG ĐỂ SỬA LỖI 404) ---
def get_working_model():
    try:
        # Lấy danh sách model thực tế từ tài khoản của anh
        available_models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        
        # Danh sách ưu tiên (thử từng cái)
        targets = [
            'models/gemini-1.5-flash-latest', 
            'models/gemini-1.5-flash', 
            'models/gemini-2.0-flash',
            'models/gemini-1.0-pro'
        ]
        
        for target in targets:
            if target in available_models:
                return target
        
        # Nếu không có cái nào trong danh sách ưu tiên, lấy cái đầu tiên tìm thấy
        return available_models[0] if available_models else None
    except Exception as e:
        st.warning(f"Không thể liệt kê model: {e}")
        return 'gemini-1.5-flash' # Mặc định cuối cùng

# Tự động chọn model "sống"
SELECTED_MODEL = get_working_model()

# --- 2. HÀM TRA CỨU MST ---
def check_mst_status(mst):
    mst_clean = "".join(filter(str.isdigit, str(mst)))
    if not mst_clean or len(mst_clean) < 10: return "Chưa xác định", ""
    try:
        url = f"https://api.vietqr.io/v2/business/{mst_clean}"
        res = requests.get(url, timeout=5).json()
        if res.get('code') == '00':
            return "Đang hoạt động ✅", res.get('data', {}).get('name', '')
        return "Ngừng hoạt động ❌", ""
    except:
        return "Lỗi API Thuế ⚠️", ""

# --- 3. GIAO DIỆN ---
st.title("🛡️ Hệ thống Đối soát Full 16 Trường (v5.4)")
st.caption(f"🚀 Hệ thống đang kết nối qua: **{SELECTED_MODEL}**")

col_in, col_out = st.columns([1, 1.3])

with col_in:
    source = st.camera_input("Chụp ảnh Giấy chứng nhận")
    if not source:
        source = st.file_uploader("Hoặc tải ảnh lên", type=["jpg","jpeg","png"])

if source:
    img = Image.open(source)
    with col_in: st.image(img, use_container_width=True)
    
    if st.button("🚀 PHÂN TÍCH ĐẦY ĐỦ 16 TRƯỜNG"):
        with st.spinner("AI đang làm việc..."):
            try:
                # Khởi tạo model từ cái tên đã tìm được ở trên
                model = genai.GenerativeModel(SELECTED_MODEL)
                
                prompt = """Trích xuất JSON từ ảnh Đăng ký kinh doanh Việt Nam. 
                Yêu cầu bóc tách chính xác 16 trường sau:
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
                    "noi_cap_cccd": "Nơi cấp CCCD (Cơ quan cấp công an/cục trưởng...)",
                    "cho_o": "Chỗ ở hiện nay",
                    "nganh_nghe": "Ngành nghề kinh doanh chi tiết",
                    "co_quan_cap_gcn": "Cơ quan cấp Giấy phép (Phòng TC-KH...)",
                    "ngay_cap_dau": "Ngày đăng ký lần đầu",
                    "ngay_thay_doi": "Ngày thay đổi gần nhất"
                }. Chỉ trả về duy nhất mã JSON."""
                
                response = model.generate_content([prompt, img])
                res_text = response.text.strip()
                
                # Làm sạch JSON đề phòng Markdown
                if "```" in res_text:
                    res_text = res_text.split("```")[1].replace("json", "").strip()
                
                data = json.loads(res_text)
                status, name_tax = check_mst_status(data.get('mst', data.get('so_gcn')))

                with col_out:
                    st.subheader("📋 Báo cáo Chi tiết")
                    if "Hoạt động" in status: st.success(status)
                    else: st.error(status)
                    
                    # Bảng hiển thị ĐẦY ĐỦ 16 TRƯỜNG
                    full_items = [
                        ("🏢 Tên Hộ/DN", data.get('ten_hkd')),
                        ("🆔 Mã số hộ/GCN", data.get('so_gcn')),
                        ("🔢 Mã số thuế", data.get('mst')),
                        ("📍 Địa chỉ trụ sở", data.get('dia_chi')),
                        ("👤 Người đại diện", data.get('dai_dien')),
                        ("📞 Số điện thoại", data.get('phone')),
                        ("⚤ Giới tính", data.get('gioi_tinh')),
                        ("🎂 Ngày sinh", data.get('ngay_sinh')),
                        ("🪪 Số CCCD", data.get('cccd')),
                        ("📅 Ngày cấp CCCD", data.get('ngay_cap_cccd')),
                        ("🏛️ Nơi cấp CCCD", data.get('noi_cap_cccd')),
                        ("🏠 Chỗ ở hiện nay", data.get('cho_o')),
                        ("📝 Ngành nghề", data.get('nganh_nghe')),
                        ("🏦 Cơ quan cấp GCN", data.get('co_quan_cap_gcn')),
                        ("🆕 Đăng ký lần đầu", data.get('ngay_cap_dau')),
                        ("🔄 Thay đổi gần nhất", data.get('ngay_thay_doi'))
                    ]
                    
                    st.table(pd.DataFrame(full_items, columns=["Hạng mục", "Thông tin"]))

                    # XUẤT EXCEL
                    df_excel = pd.DataFrame([data])
                    df_excel['Trạng thái thuế'] = status
                    output = BytesIO()
                    with pd.ExcelWriter(output, engine='openpyxl') as writer:
                        df_excel.to_excel(writer, index=False)
                    
                    st.divider()
                    st.download_button("📥 TẢI EXCEL FULL 16 TRƯỜNG", output.getvalue(), f"QLTT_{data.get('mst') or data.get('so_gcn')}.xlsx")

            except Exception as e:
                if "429" in str(e):
                    st.error("⚠️ Lỗi quá tải (429). Anh đợi 1 phút rồi nhấn lại nhé.")
                else:
                    st.error(f"Sự cố: {e}")
