# ================= IMPORT (BẮT BUỘC PHẢI CÓ) =================
import streamlit as st
from openai import OpenAI
import gspread
from google.oauth2.service_account import Credentials
import pandas as pd
import json
import base64
from io import BytesIO
from datetime import datetime

# ================= CONFIG =================
st.set_page_config(
    page_title="QLTT Thanh Hoá",
    layout="wide",
    page_icon="🛡️"
)

# ================= STYLE =================
st.markdown("""
<style>
.main {
    background-color: #f5f7fa;
}
h1 {
    text-align: center;
    color: #0b3d91;
}
.stButton>button {
    background-color: #d90429;
    color: white;
    border-radius: 10px;
    height: 45px;
    font-weight: bold;
}
.card {
    background-color: white;
    padding: 10px;
    border-radius: 10px;
    margin-bottom: 5px;
    box-shadow: 0 2px 5px rgba(0,0,0,0.1);
}
</style>
""", unsafe_allow_html=True)

# ================= OPENAI =================
if "OPENAI_API_KEY" not in st.secrets:
    st.error("❌ Thiếu OPENAI_API_KEY")
    st.stop()

client_ai = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

# ================= GOOGLE SHEETS =================
def connect_gsheet():
    try:
        scope = [
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive"
        ]
        creds_dict = json.loads(st.secrets["GCP_SERVICE_ACCOUNT"])
        creds = Credentials.from_service_account_info(creds_dict, scopes=scope)
        client = gspread.authorize(creds)
        return client.open_by_url(st.secrets["GSHEET_URL"])
    except:
        st.error("❌ Không kết nối được Google Sheets")
        return None

# ================= HEADER =================
st.markdown("""
<h1>🛡️ HỆ THỐNG QLTT THANH HOÁ</h1>
<hr>
""", unsafe_allow_html=True)

# ================= SIDEBAR =================
st.sidebar.title("⚙️ Cấu hình")

danh_sach_doi = [f"Đội QLTT số {i}" for i in range(1, 14)]
selected_doi = st.sidebar.selectbox("Chọn đội", danh_sach_doi)

user = st.sidebar.text_input("👤 Người nhập")

# ================= LAYOUT =================
col1, col2 = st.columns(2)

with col1:
    st.subheader("📷 Ảnh đầu vào")
    source = st.camera_input("Chụp ảnh")

    if not source:
        source = st.file_uploader("Upload ảnh", type=["jpg","jpeg","png"])

with col2:
    st.subheader("🖼️ Xem trước")
    if source:
        st.image(source, use_container_width=True)
    else:
        st.info("Chưa có ảnh")

# ================= AI =================
if source:
    if st.button("🚀 Phân tích", use_container_width=True):
        with st.spinner("AI đang xử lý..."):
            try:
                mime = source.type
                img_base64 = base64.b64encode(source.getvalue()).decode()

                response = client_ai.chat.completions.create(
                    model="gpt-4.1-mini",
                    messages=[
                        {
                            "role": "system",
                            "content": "Trích xuất dữ liệu giấy phép kinh doanh, trả JSON."
                        },
                        {
                            "role": "user",
                            "content": [
                                {"type": "text", "text": "Trích xuất toàn bộ thông tin."},
                                {"type": "image_url", "image_url": {"url": f"data:{mime};base64,{img_base64}"}}
                            ]
                        }
                    ],
                    response_format={"type": "json_object"}
                )

                st.session_state.data = json.loads(
                    response.choices[0].message.content
                )

            except:
                st.error("❌ Lỗi AI")

# ================= HIỂN THỊ =================
if "data" in st.session_state:
    st.markdown("---")
    st.subheader("📝 Kiểm tra dữ liệu")

    cols = st.columns(2)
    edited = {}

    for i, key in enumerate(st.session_state.data.keys()):
        with cols[i % 2]:
            st.markdown(f"<div class='card'><b>{key}</b></div>", unsafe_allow_html=True)
            edited[key] = st.text_input("", st.session_state.data[key])

    with st.expander("🔍 JSON gốc"):
        st.json(st.session_state.data)

    # ================= SAVE =================
    if st.button("💾 Lưu dữ liệu", use_container_width=True):
        sh = connect_gsheet()
        if sh:
            try:
                try:
                    ws = sh.worksheet(selected_doi)
                except:
                    ws = sh.add_worksheet(title=selected_doi, rows="1000", cols="30")

                if not ws.get_all_values():
                    ws.append_row(list(edited.keys()) + ["Người nhập", "Thời gian"])

                ws.append_row(
                    list(edited.values()) +
                    [user, datetime.now().strftime("%d/%m/%Y %H:%M:%S")]
                )

                st.success("✅ Đã lưu thành công")

                df = pd.DataFrame([edited])
                output = BytesIO()

                with pd.ExcelWriter(output, engine="openpyxl") as writer:
                    df.to_excel(writer, index=False)

                st.download_button(
                    "📥 Tải Excel",
                    output.getvalue(),
                    file_name="data.xlsx"
                )

            except:
                st.error("❌ Lỗi lưu")

# ================= FOOTER =================
st.markdown("""
<hr>
<p style='text-align:center;color:gray'>
QLTT Thanh Hoá - AI System v3.3
</p>
""", unsafe_allow_html=True)
