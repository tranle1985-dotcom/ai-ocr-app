import streamlit as st
from openai import OpenAI
import base64
import pandas as pd
import json
import requests
from io import BytesIO
from datetime import datetime

# --- 1. CẤU HÌNH HỆ THỐNG ---
st.set_page_config(page_title="QLTT Thanh Hoá v2.1", layout="wide", page_icon="🛡️")

# Khởi tạo OpenAI
if "OPENAI_API_KEY" in st.secrets:
    client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])
else:
    st.error("❌ Thiếu OPENAI_API_KEY trong mục Secrets!")

def encode_image(image_file):
    return base64.b64encode(image_file.getvalue()).decode('utf-8')

# --- 2. HÀM TRA CỨU THUẾ CHÍNH XÁC ---
def check_mst_status(mst):
    # Làm sạch MST (chỉ giữ lại số)
    mst_clean = "".join(filter(str.isdigit, str(mst)))
    if not mst_clean or len(mst_clean) < 10: 
        return "MST không hợp lệ ⚠️", ""
    
    try:
        # Gọi API VietQR để đối soát dữ liệu thuế
        url = f"https://api.vietqr.io/v2/business/{mst_clean}"
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            res = response.json()
            if res.get('code') == '00':
                return "Đang hoạt động ✅", res.get('data', {}).get('name', '')
            else:
                return "Ngừng hoạt động hoặc không tồn tại ❌", ""
        return "Lỗi kết nối máy chủ thuế ⚠️", ""
    except:
        return "Sự cố đường truyền API ⚠️", ""

# --- 3. GIAO DIỆN ---
st.title("🛡️ Hệ thống Quét dữ liệu ĐKKD - QLTT Thanh Hoá")
st.caption("Phiên bản v2.1: Tối ưu Excel & Đối soát Thuế chính xác")

col_in, col_out = st.columns([1, 1.2])

with col_in:
    source = st.camera_input("Chụp ảnh Giấy phép")
    if not source:
        source = st.file_uploader("Hoặc chọn ảnh từ máy", type=["jpg","jpeg","png"])

if source:
    img_base64 = encode_image(source)
    with col_in: 
        st.image(source, use_container_width=True)
    
    if st.button("🚀 PHÂN TÍCH & ĐỐI SOÁT"):
        with st.spinner("Đang xử lý dữ liệu nghiệp vụ..."):
            try:
                # Gọi GPT-4o-mini
                response = client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[
                        {
                            "role": "user",
                            "content": [
                                {
                                    "type": "text", 
                                    "text": """Bạn là chuyên gia bóc tách hồ sơ pháp lý Việt Nam. Hãy trích xuất thông tin từ ảnh sang JSON. 
                                    KHÔNG đánh số thứ tự trong tên trường. Hãy điền đủ các trường sau:
                                    {
                                        "Mã số hộ kinh doanh": "",
                                        "Tên hộ kinh doanh": "",
                                        "Mã số thuế": "",
                                        "Địa chỉ trụ sở chính": "",
                                        "Người đại diện": "",
                                        "Số điện thoại": "",
                                        "Giới tính": "",
                                        "Ngày sinh": "",
                                        "Số CCCD": "",
                                        "Ngày cấp CCCD": "",
                                        "Nơi cấp CCCD": "",
                                        "Chỗ ở hiện nay": "",
                                        "Ngành nghề kinh doanh": "",
                                        "Cơ quan cấp phép": "",
                                        "Ngày đăng ký đầu": "",
                                        "Thay đổi gần nhất": ""
                                    }. Chỉ trả về duy nhất mã JSON."""
                                },
                                {
                                    "type": "image_url", 
                                    "image_url": {"url": f"data:image/jpeg;base64,{img_base64}"}
                                }
                            ],
                        }
                    ],
                    response_format={"type": "json_object"}
                )
                
                # 1. Lấy dữ liệu từ AI
                data = json.loads(response.choices[0].message.content)
                
                # 2. Liên kết trạng thái thuế (Ưu tiên lấy từ trường Mã số thuế, nếu trống thì lấy Số GCN)
                mst_target = data.get('Mã số thuế') or data.get('Mã số hộ kinh doanh')
                status, name_tax = check_mst_status(mst_target)

                with col_out:
                    st.subheader("📋 Kết quả trích xuất")
                    
                    # Hiển thị trạng thái thuế nổi bật
                    if "Hoạt động" in status:
                        st.success(f"Trạng thái: {status}")
                    else:
                        st.warning(f"Trạng thái: {status}")

                    if name_tax:
                        st.info(f"Dữ liệu thuế khớp với: **{name_tax}**")

                    # Hiển thị bảng dữ liệu (không có số thứ tự ở đầu trường)
                    df_view = pd.DataFrame(list(data.items()), columns=["Hạng mục", "Dữ liệu"])
                    st.table(df_view)

                    # --- XỬ LÝ EXCEL ---
                    # Tạo file Excel chứa 1 dòng dữ liệu đầy đủ
                    df_excel = pd.DataFrame([data])
                    df_excel['Trạng thái thuế'] = status
                    df_excel['Tên đăng ký hệ thống thuế'] = name_tax
                    
                    output = BytesIO()
                    with pd.ExcelWriter(output, engine='openpyxl') as writer:
                        df_excel.to_excel(writer, index=False)
                    
                    st.divider()
                    st.download_button(
                        label="📥 TẢI FILE EXCEL NGHIỆP VỤ",
                        data=output.getvalue(),
                        file_name=f"QLTT_{mst_target}_{datetime.now().strftime('%H%M%S')}.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                    )

            except Exception as e:
                st.error(f"Lỗi hệ thống: {e}")
