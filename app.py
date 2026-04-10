import streamlit as st
import google.generativeai as genai
from PIL import Image
import pandas as pd
from datetime import datetime
import json
import requests
from io import BytesIO

# --- 1. CẤU HÌNH HỆ THỐNG ---
st.set_page_config(page_title="Hệ thống QLTT Thanh Hoá v2.0", layout="wide", page_icon="🛡️")

@st.cache_resource
def setup_ai(api_key):
    genai.configure(api_key=api_key)
    return genai.GenerativeModel('gemini-1.5-flash')

try:
    api_key = st.secrets["GOOGLE_API_KEY"]
    model = setup_ai(api_key)
except:
    st.error("❌ Thiếu API Key trong Secrets!")

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
st.title("🛡️ Hệ thống Đối soát ")
st.info("Bản cập nhật: Đã bổ sung đầy đủ Nơi cấp CCCD và Cơ quan cấp Giấy phép.")

col_in, col_out = st.columns([1, 1.3])

with col_in:
    source = st.camera_input("Chụp ảnh Giấy chứng nhận")
    if not source:
        source = st.file_uploader("Hoặc tải ảnh lên", type=["jpg","jpeg","png"])

if source:
    img = Image.open(source)
    with col_in: st.image(img, use_container_width=True)
    
    if st.button("🚀 PHÂN TÍCH ĐẦY ĐỦ"):
        with st.spinner("AI đang bóc tách 16 trường dữ liệu..."):
            try:
                # Prompt yêu cầu ĐẦY ĐỦ các trường, nhấn mạnh NƠI CẤP
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
                    "noi_cap_cccd": "Nơi cấp CCCD (Cơ quan cấp CCCD)",
                    "cho_o": "Chỗ ở hiện nay",
                    "nganh_nghe": "Ngành nghề kinh doanh chi tiết",
                    "co_quan_cap_gcn": "Nơi cấp giấy phép/Cơ quan cấp GCN",
                    "ngay_cap_dau": "Ngày đăng ký lần đầu",
                    "ngay_thay_doi": "Ngày thay đổi gần nhất"
                }. Chỉ trả về duy nhất mã JSON, không thêm văn bản khác."""
                
                response = model.generate_content([prompt, img])
                res_text = response.text.strip()
                
                # Làm sạch JSON
                if "```" in res_text:
                    res_text = res_text.split("```")[1].replace("json", "").strip()
                
                data = json.loads(res_text)
                status, name_tax = check_mst_status(data.get('mst', data.get('so_gcn')))

                with col_out:
                    st.subheader("📋 Kết quả bóc tách 16 Trường")
                    if "Hoạt động" in status: st.success(status)
                    else: st.error(status)
                    
                    # Cấu trúc hiển thị rõ ràng từng mục
                    full_items = {
                        "Hạng mục thông tin": [
                            "1. Số GCN/Mã số hộ", "2. Tên Hộ/Doanh nghiệp", "3. Mã số thuế", 
                            "4. Địa chỉ trụ sở chính", "5. Họ tên người đại diện", "6. Số điện thoại",
                            "7. Giới tính", "8. Ngày sinh", "9. Số CCCD/Hộ chiếu",
                            "10. Ngày cấp CCCD", "11. Nơi cấp CCCD", "12. Chỗ ở hiện nay",
                            "13. Ngành nghề kinh doanh", "14. Cơ quan cấp Giấy phép", 
                            "15. Ngày đăng ký đầu", "16. Thay đổi gần nhất"
                        ],
                        "Dữ liệu trích xuất": [
                            data.get('so_gcn'), data.get('ten_hkd'), data.get('mst'),
                            data.get('dia_chi'), data.get('dai_dien'), data.get('phone'),
                            data.get('gioi_tinh'), data.get('ngay_sinh'), data.get('cccd'),
                            data.get('ngay_cap_cccd'), data.get('noi_cap_cccd'), data.get('cho_o'),
                            data.get('nganh_nghe'), data.get('co_quan_cap_gcn'), 
                            data.get('ngay_cap_dau'), data.get('ngay_thay_doi')
                        ]
                    }
                    st.table(pd.DataFrame(full_items))

                    # XUẤT EXCEL ĐẦY ĐỦ
                    df_excel = pd.DataFrame([data])
                    df_excel['Trạng thái thuế'] = status
                    
                    output = BytesIO()
                    with pd.ExcelWriter(output, engine='openpyxl') as writer:
                        df_excel.to_excel(writer, index=False)
                    
                    st.divider()
                    st.download_button(
                        label="📥 TẢI EXCEL (FULL 16 TRƯỜNG)",
                        data=output.getvalue(),
                        file_name=f"QLTT_Full_{data.get('mst') or data.get('so_gcn')}.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                    )

            except Exception as e:
                if "429" in str(e):
                    st.error("⚠️ Lỗi quá tải. Anh vui lòng đợi 1 phút.")
                else:
                    st.error(f"Sự cố: {e}")
