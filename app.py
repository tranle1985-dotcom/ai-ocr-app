import streamlit as st
from openai import OpenAI
import gspread
from google.oauth2.service_account import Credentials
import pandas as pd
import json
import base64
import requests
from io import BytesIO
from datetime import datetime
from PIL import Image

# ================= CONFIG & TỐI ƯU =================
st.set_page_config(page_title="QLTT Thanh Hoá", layout="wide", page_icon="🛡️")

# Hàm nén ảnh đi hiện trường (Tiết kiệm 4G)
def process_image(image_file):
    img = Image.open(image_file)
    img.thumbnail((1500, 1500)) 
    buffered = BytesIO()
    img.save(buffered, format="JPEG", quality=85)
    return buffered

# Hàm tra cứu Thuế VietQR
def check_mst_status(mst):
    mst_clean = "".join(filter(str.isdigit, str(mst)))
    if not mst_clean or len(mst_clean) < 10: return "MST không hợp lệ ⚠️", ""
    try:
        url = f"https://api.vietqr.io/v2/business/{mst_clean}"
        res = requests.get(url, timeout=5).json()
        if res.get('code') == '00':
            return "Đang hoạt động ✅", res.get('data', {}).get('name', '')
        return "Ngừng hoạt động/Không tồn tại ❌", ""
    except:
        return "Lỗi API Thuế ⚠️", ""

# ================= STYLE GIAO DIỆN =================
st.markdown("""
<style>
.main { background-color: #f5f7fa; }
h1 { text-align: center; color: #0b3d91; font-weight: 800; }
.stButton>button {
    background-color: #d90429;
    color: white;
    border-radius: 8px;
    height: 45px;
    font-weight: bold;
    border: none;
    transition: 0.3s;
}
.stButton>button:hover { background-color: #b00320; }
.card {
    background-color: #ffffff;
    padding: 10px;
    border-radius: 6px;
    margin-bottom: 2px;
    border-left: 4px solid #0b3d91;
    box-shadow: 0 1px 3px rgba(0,0,0,0.1);
    font-size: 14px;
}
</style>
""", unsafe_allow_html=True)

# ================= KHỞI TẠO HỆ THỐNG =================
if "OPENAI_API_KEY" not in st.secrets:
    st.error("❌ Thiếu OPENAI_API_KEY trong cấu hình Secrets")
    st.stop()

client_ai = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

def connect_gsheet():
    try:
        scope = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
        creds_dict = json.loads(st.secrets["GCP_SERVICE_ACCOUNT"])
        creds = Credentials.from_service_account_info(creds_dict, scopes=scope)
        client = gspread.authorize(creds)
        return client.open_by_url(st.secrets["GSHEET_URL"])
    except Exception as e:
        st.error(f"❌ Lỗi Google Sheets: {e}")
        return None

# ================= HEADER & SIDEBAR =================
st.markdown("<h1>🛡️ HỆ THỐNG PHÂN TÍCH DỮ LIỆU - QLTT THANH HOÁ</h1><hr>", unsafe_allow_html=True)

st.sidebar.title("⚙️ Cấu hình hệ thống")
danh_sach_doi = [f"Đội QLTT số {i}" for i in range(1, 16)]
selected_doi = st.sidebar.selectbox("🚩 Chọn đội công tác", danh_sach_doi)
user = st.sidebar.text_input("👤 Cán bộ thực hiện", placeholder="Nhập họ tên...")

st.sidebar.divider()
st.sidebar.write("📂 **Cơ sở dữ liệu:**")
if "GSHEET_URL" in st.secrets:
    st.sidebar.link_button("👁️ Xem CSDL Google Sheet", st.secrets["GSHEET_URL"], use_container_width=True)

# ================= UPLOAD ẢNH =================
col1, col2 = st.columns(2)

with col1:
    st.subheader("📷 Dữ liệu đầu vào")
    source = st.camera_input("Chụp ảnh trực tiếp")
    if not source:
        source = st.file_uploader("Hoặc tải ảnh từ thiết bị", type=["jpg","jpeg","png"])

with col2:
    st.subheader("🖼️ Xem trước tài liệu")
    if source:
        st.image(source, use_container_width=True)
    else:
        st.info("Vui lòng chụp hoặc tải ảnh Giấy phép lên hệ thống.")

# ================= AI BÓC TÁCH CHUYÊN SÂU =================
if source:
    if st.button("🚀 BẮT ĐẦU PHÂN TÍCH DỮ LIỆU", use_container_width=True):
        with st.spinner("Hệ thống AI đang quét sâu 16 trường nghiệp vụ..."):
            try:
                # Nén ảnh trước khi gửi
                compressed_img = process_image(source)
                img_base64 = base64.b64encode(compressed_img.getvalue()).decode('utf-8')

                response = client_ai.chat.completions.create(
                    model="gpt-4o-mini",
                    temperature=0.1, # Ép AI đọc chính xác, không đoán mò
                    messages=[
                        {
                            "role": "system",
                            "content": "Bạn là chuyên gia đọc Giấy chứng nhận đăng ký hộ kinh doanh tại Việt Nam. Đọc cẩn thận từng chữ, ưu tiên phần 'Thông tin về chủ hộ kinh doanh' và tiêu đề góc trên cùng bên trái."
                        },
                        {
                            "role": "user",
                            "content": [
                                {
                                    "type": "text", 
                                    "text": """Trích xuất dữ liệu sang JSON. Bắt buộc trả về đúng 16 trường (tên trường không chứa số thứ tự).
                                    Hướng dẫn vị trí lấy dữ liệu:
                                    {
                                        "Mã số hộ kinh doanh": "Dãy số dưới chữ GIẤY CHỨNG NHẬN...",
                                        "Tên hộ kinh doanh": "Tên đầy đủ của hộ",
                                        "Mã số thuế": "Lấy Mã số thuế, nếu không có thì lấy Mã số hộ kinh doanh",
                                        "Địa chỉ trụ sở chính": "Địa chỉ kinh doanh",
                                        "Họ tên người đại diện": "Tên chủ hộ",
                                        "Số điện thoại": "Số điện thoại",
                                        "Giới tính": "Nam hoặc Nữ",
                                        "Ngày sinh": "Ngày tháng năm sinh",
                                        "Số CCCD": "Đọc chính xác dòng 'Số giấy tờ pháp lý của cá nhân' hoặc 'Số CMND/CCCD'",
                                        "Ngày cấp CCCD": "Ngày cấp nằm ngay dưới số giấy tờ pháp lý",
                                        "Nơi cấp CCCD": "Cơ quan cấp (VD: Cục trưởng Cục CSQLHC về trật tự xã hội...)",
                                        "Chỗ ở hiện nay": "Địa chỉ thường trú hoặc liên lạc",
                                        "Ngành nghề kinh doanh": "Liệt kê chi tiết ngành nghề",
                                        "Cơ quan cấp phép": "Đọc 2-3 dòng chữ in hoa ở GÓC TRÊN CÙNG BÊN TRÁI (VD: UBND HUYỆN... PHÒNG TÀI CHÍNH - KẾ HOẠCH). KHÔNG LẤY Ở PHẦN CON DẤU.",
                                        "Ngày đăng ký đầu": "Đăng ký lần đầu ngày...",
                                        "Thay đổi gần nhất": "Đăng ký thay đổi lần thứ... ngày... (không có ghi 'Không có')"
                                    }.
                                    Nếu không tìm thấy, hãy điền 'Không có'."""
                                },
                                {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{img_base64}"}}
                            ]
                        }
                    ],
                    response_format={"type": "json_object"}
                )

                st.session_state.data = json.loads(response.choices[0].message.content)
            except Exception as e:
                st.error(f"❌ Lỗi AI: {e}")

# ================= FORM HIỆU CHỈNH =================
if "data" in st.session_state:
    st.markdown("---")
    st.subheader("📝 Kiểm tra & Hiệu chỉnh dữ liệu")
    
    # Check trạng thái thuế tự động
    mst_target = st.session_state.data.get('Mã số thuế', '') or st.session_state.data.get('Mã số hộ kinh doanh', '')
    status, name_tax = check_mst_status(mst_target)
    
    if "Hoạt động" in status:
        st.success(f"🔍 Đối soát hệ thống thuế: **{status} | {name_tax}**")
    else:
        st.warning(f"🔍 Đối soát hệ thống thuế: **{status}**")

    cols = st.columns(2)
    edited = {}

    for i, key in enumerate(st.session_state.data.keys()):
        value = str(st.session_state.data[key])
        safe_key = key.replace(" ", "_").replace(":", "").replace("-", "_")

        with cols[i % 2]:
            st.markdown(f"<div class='card'><b>{key}</b></div>", unsafe_allow_html=True)
            
            if key in ["Ngành nghề kinh doanh", "Cơ quan cấp phép", "Chỗ ở hiện nay", "Địa chỉ trụ sở chính"]:
                edited[key] = st.text_area(label="Hidden", value=value, key=f"input_{safe_key}", label_visibility="collapsed")
            else:
                edited[key] = st.text_input(label="Hidden", value=value, key=f"input_{safe_key}", label_visibility="collapsed")

    # ================= LƯU CSDL =================
    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("💾 XÁC NHẬN LƯU VÀO CƠ SỞ DỮ LIỆU CHI CỤC", use_container_width=True):
        if not user:
            st.warning("⚠️ BẮT BUỘC: Vui lòng nhập tên 'Cán bộ thực hiện' ở cột bên trái trước khi lưu!")
        else:
            with st.spinner("Đang đồng bộ dữ liệu an toàn lên Google Sheets..."):
                sh = connect_gsheet()
                if sh:
                    try:
                        try:
                            ws = sh.worksheet(selected_doi)
                        except gspread.WorksheetNotFound:
                            ws = sh.add_worksheet(title=selected_doi, rows="1000", cols="30")

                        # Tạo Header nếu sheet trống
                        if not ws.get_all_values():
                            headers = list(edited.keys()) + ["Trạng thái thuế", "Cán bộ thực hiện", "Thời gian quét"]
                            ws.append_row(headers)

                        # Ghi dữ liệu
                        row_data = list(edited.values()) + [status, user, datetime.now().strftime("%d/%m/%Y %H:%M:%S")]
                        ws.append_row(row_data)

                        st.success(f"✅ Đã lưu thành công hồ sơ vào hệ thống ({selected_doi})")

                        # Nút xuất Excel phụ trợ
                        df = pd.DataFrame([edited])
                        df['Trạng thái thuế'] = status
                        output = BytesIO()
                        with pd.ExcelWriter(output, engine="openpyxl") as writer:
                            df.to_excel(writer, index=False)

                        st.download_button("📥 Tải file Excel đính kèm", output.getvalue(), file_name=f"Hoso_{mst_target}.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

                    except Exception as e:
                        st.error(f"❌ Lỗi ghi dữ liệu: {e}")

# ================= FOOTER =================
st.markdown("""
<hr>
<p style='text-align:center; color:gray; font-size: 13px;'>
Hệ thống Hỗ trợ Nghiệp vụ Số - Lực lượng Quản lý thị trường Thanh Hoá <br>
<i>Được phát triển bởi Trần Lê</i>
</p>
""", unsafe_allow_html=True)
