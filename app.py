import streamlit as st
from openai import OpenAI
import gspread
from google.oauth2.service_account import Credentials
import pandas as pd
import json
import requests
import base64
from io import BytesIO
from datetime import datetime
from PIL import Image

# --- 1. CẤU HÌNH HỆ THỐNG ---
st.set_page_config(page_title="Hệ thống QLTT Thanh Hoá v4.0", layout="wide", page_icon="🛡️")

# Khởi tạo OpenAI
if "OPENAI_API_KEY" in st.secrets:
    client_ai = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])
else:
    st.error("❌ Thiếu OPENAI_API_KEY trong Secrets!")

# Hàm kết nối Google Sheets
def connect_gsheet():
    try:
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds_dict = json.loads(st.secrets["GCP_SERVICE_ACCOUNT"])
        creds = Credentials.from_service_account_info(creds_dict, scopes=scope)
        gc = gspread.authorize(creds)
        return gc.open_by_url(st.secrets["GSHEET_URL"])
    except Exception as e:
        st.error(f"Lỗi kết nối Google Sheets: {e}")
        return None

# Hàm xử lý nén ảnh tối ưu 4G
def process_image(image_file):
    img = Image.open(image_file)
    img.thumbnail((1200, 1200)) # Giảm kích thước ảnh để upload nhanh
    buffered = BytesIO()
    img.save(buffered, format="JPEG", quality=80) # Nén chất lượng 80%
    return buffered

def encode_image(image_bytes):
    return base64.b64encode(image_bytes).decode('utf-8')

# Hàm tra cứu trạng thái thuế VietQR
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

# --- 2. THANH BÊN (SIDEBAR) ---
st.sidebar.image("https://itst.gov.vn/storage/news/2021/05/18/60a32439d5050.png", width=100) # Logo QLTT
st.sidebar.title("DANH MỤC QUẢN LÝ")
danh_sach_doi = [f"Đội QLTT số {i}" for i in range(1, 16)]
selected_doi = st.sidebar.selectbox("🚩 Chọn Đội công tác", danh_sach_doi)

st.sidebar.divider()
st.sidebar.write("📂 **Cơ sở dữ liệu:**")
if "GSHEET_URL" in st.secrets:
    st.sidebar.link_button("👁️ Mở Google Sheet Tổng", st.secrets["GSHEET_URL"], use_container_width=True)

# --- 3. GIAO DIỆN CHÍNH ---
st.title("🛡️ Hệ thống Tác nghiệp Số - QLTT Thanh Hoá")
st.info(f"Đang ghi nhận dữ liệu cho: **{selected_doi}**")

col_in, col_out = st.columns([1, 1.2])

with col_in:
    source = st.camera_input("Chụp ảnh Giấy phép")
    if not source:
        source = st.file_uploader("Hoặc tải ảnh lên", type=["jpg","jpeg","png"])

if source:
    if st.button("🚀 BẮT ĐẦU PHÂN TÍCH 16 TRƯỜNG"):
        with st.spinner("AI đang bóc tách dữ liệu..."):
            try:
                # Nén và Encode ảnh
                compressed_img = process_image(source)
                base64_img = encode_image(compressed_img.getvalue())
                
                # Gọi OpenAI GPT-4o-mini
                response = client_ai.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[{
                        "role": "user",
                        "content": [
                            {"type": "text", "text": "Trích xuất JSON (không số thứ tự): Mã số hộ kinh doanh, Tên hộ kinh doanh, Mã số thuế, Địa chỉ trụ sở chính, Họ tên người đại diện, Số điện thoại, Giới tính, Ngày sinh, Số CCCD, Ngày cấp CCCD, Nơi cấp CCCD, Chỗ ở hiện nay, Ngành nghề kinh doanh, Cơ quan cấp phép, Ngày đăng ký đầu, Thay đổi gần nhất."},
                            {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_img}"}}
                        ]
                    }],
                    response_format={"type": "json_object"}
                )
                st.session_state.raw_data = json.loads(response.choices[0].message.content)
            except Exception as e:
                st.error(f"Lỗi AI: {e}")

# --- 4. HIỆN THỊ & CHỈNH SỬA (DATA VALIDATION) ---
if "raw_data" in st.session_state:
    with col_out:
        st.subheader("📝 Kiểm tra & Chỉnh sửa dữ liệu")
        
        # Tra cứu thuế ngay lập tức
        mst_target = st.session_state.raw_data.get('Mã số thuế') or st.session_state.raw_data.get('Mã số hộ kinh doanh')
        status, name_tax = check_mst_status(mst_target)
        
        if "Hoạt động" in status: st.success(f"{status} | {name_tax}")
        else: st.warning(status)

        # Form chỉnh sửa 16 trường
        edited_final = {}
        keys = list(st.session_state.raw_data.keys())
        
        # Nhóm 1: Thông tin pháp lý
        with st.expander("📌 Thông tin chung", expanded=True):
            for i in range(0, 6):
                edited_final[keys[i]] = st.text_input(keys[i], st.session_state.raw_data[keys[i]])
        
        # Nhóm 2: Thông tin cá nhân
        with st.expander("👤 Thông tin Người đại diện"):
            for i in range(6, 12):
                edited_final[keys[i]] = st.text_input(keys[i], st.session_state.raw_data[keys[i]])
        
        # Nhóm 3: Ngành nghề & Giấy phép
        with st.expander("📂 Chi tiết Ngành nghề & Cấp phép"):
            for i in range(12, 16):
                edited_final[keys[i]] = st.text_area(keys[i], st.session_state.raw_data[keys[i]])

        # --- 5. LƯU VÀO GOOGLE SHEET ---
        st.divider()
        if st.button("💾 XÁC NHẬN LƯU VÀO CSDL CHI CỤC"):
            with st.spinner("Đang đồng bộ lên Google Sheets..."):
                sh = connect_gsheet()
                if sh:
                    try:
                        # Tìm hoặc tạo Tab cho Đội
                        try:
                            ws = sh.worksheet(selected_doi)
                        except gspread.WorksheetNotFound:
                            ws = sh.add_worksheet(title=selected_doi, rows="1000", cols="20")
                            headers = list(edited_final.keys()) + ["Trạng thái thuế", "Ngày thực hiện"]
                            ws.append_row(headers)
                        
                        # Chèn dữ liệu
                        row = list(edited_final.values()) + [status, datetime.now().strftime("%d/%m/%Y %H:%M")]
                        ws.append_row(row)
                        
                        st.balloons()
                        st.success(f"✅ Đã lưu dữ liệu vào Tab: {selected_doi}")
                        st.markdown(f"🔗 [Mở file xem ngay]({st.secrets['GSHEET_URL']})")
                    except Exception as e:
                        st.error(f"Lỗi ghi dữ liệu: {e}")

        # Nút xuất Excel dự phòng (Không đánh số thứ tự)
        df_excel = pd.DataFrame([edited_final])
        excel_out = BytesIO()
        with pd.ExcelWriter(excel_out, engine='openpyxl') as writer:
            df_excel.to_excel(writer, index=False)
        
        st.download_button(
            label="📥 Tải file Excel riêng (Dự phòng)",
            data=excel_out.getvalue(),
            file_name=f"QLTT_{mst_target}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
