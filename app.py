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

# --- 1. KẾT NỐI HỆ THỐNG ---
st.set_page_config(page_title="Hệ thống QLTT Thanh Hoá v3.2", layout="wide", page_icon="🛡️")

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
        client = gspread.authorize(creds)
        return client.open_by_url(st.secrets["GSHEET_URL"])
    except Exception as e:
        st.error(f"Lỗi kết nối Google Sheets: {e}")
        return None

# --- 2. GIAO DIỆN TÁC NGHIỆP ---
st.title("🛡️ Hệ thống Dữ liệu Nghiệp vụ QLTT Thanh Hoá")
st.sidebar.header("Cấu hình đơn vị")
danh_sach_doi = [f"Đội QLTT số {i}" for i in range(1, 16)]
selected_doi = st.sidebar.selectbox("🚩 Chọn Đội công tác", danh_sach_doi)

source = st.camera_input("Chụp ảnh Giấy phép")
if not source:
    source = st.file_uploader("Hoặc tải ảnh lên", type=["jpg","jpeg","png"])

if source:
    # Mã hóa ảnh sang Base64 để gửi cho OpenAI
    img_base64 = base64.b64encode(source.getvalue()).decode('utf-8')
    
    if st.button("🚀 TRÍCH XUẤT 16 TRƯỜNG"):
        with st.spinner("AI đang bóc tách dữ liệu kỹ lưỡng..."):
            try:
                response = client_ai.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[{
                        "role": "user",
                        "content": [
                            {"type": "text", "text": "Trích xuất JSON (không đánh số): Mã số hộ kinh doanh, Tên hộ kinh doanh, Mã số thuế, Địa chỉ trụ sở chính, Họ tên người đại diện, Số điện thoại, Giới tính, Ngày sinh, Số CCCD, Ngày cấp CCCD, Nơi cấp CCCD, Chỗ ở hiện nay, Ngành nghề kinh doanh, Cơ quan cấp phép, Ngày đăng ký đầu, Thay đổi gần nhất. Nếu không thấy ghi 'Không có'."},
                            {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{img_base64}"}}
                        ]
                    }],
                    response_format={"type": "json_object"}
                )
                st.session_state.data = json.loads(response.choices[0].message.content)
            except Exception as e:
                st.error(f"Lỗi AI: {e}")

    # --- 3. HIỆU CHỈNH & LƯU DỮ LIỆU ---
    if "data" in st.session_state:
        st.divider()
        st.subheader(f"📝 Kiểm tra dữ liệu - {selected_doi}")
        
        # Cho phép sửa trực tiếp
        edited = {}
        cols = st.columns(2)
        keys = list(st.session_state.data.keys())
        for i, key in enumerate(keys):
            with cols[i % 2]:
                edited[key] = st.text_input(key, st.session_state.data[key])
        
        if st.button("💾 XÁC NHẬN LƯU VÀO HỆ THỐNG"):
            sh = connect_gsheet()
            if sh:
                try:
                    # Tìm hoặc tạo Tab cho Đội
                    try:
                        ws = sh.worksheet(selected_doi)
                    except:
                        ws = sh.add_worksheet(title=selected_doi, rows="1000", cols="20")
                        ws.append_row(list(edited.keys()) + ["Thời gian lưu"])
                    
                    # Lưu dòng dữ liệu
                    ws.append_row(list(edited.values()) + [datetime.now().strftime("%d/%m/%Y %H:%M:%S")])
                    st.success(f"✅ Đã lưu thành công vào Tab của **{selected_doi}**!")

                    # Tạo file Excel dự phòng để tải về
                    df = pd.DataFrame([edited])
                    output = BytesIO()
                    with pd.ExcelWriter(output, engine='openpyxl') as writer:
                        df.to_excel(writer, index=False)
                    
                    st.download_button("📥 TẢI EXCEL DỰ PHÒNG", output.getvalue(), 
                                     file_name=f"{selected_doi}_{datetime.now().strftime('%H%M%S')}.xlsx")
                except Exception as e:
                    st.error(f"Lỗi khi ghi dữ liệu: {e}")
