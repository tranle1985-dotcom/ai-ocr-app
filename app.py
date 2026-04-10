import streamlit as st
from openai import OpenAI
import base64
from PIL import Image
import pandas as pd
import json
import requests
from io import BytesIO

# --- 1. CẤU HÌNH HỆ THỐNG ---
st.set_page_config(page_title="AI QLTT - OpenAI Edition", layout="wide", page_icon="🤖")

# Khởi tạo OpenAI Client
if "OPENAI_API_KEY" in st.secrets:
    client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])
else:
    st.error("❌ Thiếu OPENAI_API_KEY trong Secrets!")

# Hàm mã hóa ảnh sang Base64 để gửi cho OpenAI
def encode_image(image_file):
    return base64.b64encode(image_file.getvalue()).decode('utf-8')

# --- 2. HÀM TRA CỨU MST ---
def check_mst_status(mst):
    mst_clean = "".join(filter(str.isdigit, str(mst)))
    if not mst_clean or len(mst_clean) < 10: return "Chưa rõ", ""
    try:
        url = f"https://api.vietqr.io/v2/business/{mst_clean}"
        res = requests.get(url, timeout=5).json()
        if res.get('code') == '00':
            return "Đang hoạt động ✅", res.get('data', {}).get('name', '')
        return "Ngừng hoạt động ❌", ""
    except:
        return "Lỗi API Thuế ⚠️", ""

# --- 3. GIAO DIỆN ---
st.title("🛡️ Hệ thống Đối soát OpenAI (v6.0)")
st.info("Sử dụng công nghệ GPT-4o để trích xuất 16 trường dữ liệu nghiệp vụ.")

col_in, col_out = st.columns([1, 1.3])

with col_in:
    source = st.camera_input("Chụp ảnh GCN Đăng ký kinh doanh")
    if not source:
        source = st.file_uploader("Hoặc tải ảnh lên", type=["jpg","jpeg","png"])

if source:
    img_base64 = encode_image(source)
    with col_in: st.image(source, use_container_width=True)
    
    if st.button("🚀 PHÂN TÍCH ĐẦY ĐỦ 16 TRƯỜNG"):
        with st.spinner("OpenAI đang xử lý..."):
            try:
                # Gọi API OpenAI
                response = client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[
                        {
                            "role": "user",
                            "content": [
                                {"type": "text", "text": """Trích xuất JSON từ ảnh ĐKKD Việt Nam (16 trường):
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
                                    "nganh_nghe": "Ngành nghề kinh doanh chi tiết",
                                    "co_quan_cap_gcn": "Cơ quan cấp Giấy phép",
                                    "ngay_cap_dau": "Ngày đăng ký lần đầu",
                                    "ngay_thay_doi": "Ngày thay đổi gần nhất"
                                }. Chỉ trả về mã JSON."""},
                                {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{img_base64}"}}
                            ],
                        }
                    ],
                    response_format={"type": "json_object"}
                )
                
                data = json.loads(response.choices[0].message.content)
                status, name_tax = check_mst_status(data.get('mst', data.get('so_gcn')))

                with col_out:
                    st.subheader("📋 Kết quả phân tích (GPT-4o)")
                    if "Hoạt động" in status: st.success(status)
                    else: st.error(status)
                    
                    # Bảng hiển thị 16 trường
                    items = [
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
                        ("🆕 Đăng ký đầu", data.get('ngay_cap_dau')),
                        ("🔄 Thay đổi gần nhất", data.get('ngay_thay_doi'))
                    ]
                    st.table(pd.DataFrame(items, columns=["Hạng mục", "Thông tin"]))

                    # XUẤT EXCEL
                    df_excel = pd.DataFrame([data])
                    df_excel['Trạng thái thuế'] = status
                    output = BytesIO()
                    with pd.ExcelWriter(output, engine='openpyxl') as writer:
                        df_excel.to_excel(writer, index=False)
                    
                    st.download_button("📥 TẢI EXCEL FULL", output.getvalue(), f"OpenAI_{data.get('mst')}.xlsx")

            except Exception as e:
                st.error(f"Sự cố OpenAI: {e}")
