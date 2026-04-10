import streamlit as st
from openai import OpenAI
import base64
import pandas as pd
import json
import requests
from io import BytesIO
from datetime import datetime
from PIL import Image

# --- 1. CẤU HÌNH ---
st.set_page_config(page_title="QLTT Thanh Hoá AI", layout="wide", page_icon="🛡️")

client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

def encode_image(image_file):
    return base64.b64encode(image_file.getvalue()).decode('utf-8')

# --- 2. HÀM TRA CỨU THUẾ ---
def check_mst_status(mst):
    mst_clean = "".join(filter(str.isdigit, str(mst)))
    if not mst_clean or len(mst_clean) < 10: return "MST/GCN không hợp lệ ⚠️", ""
    try:
        url = f"https://api.vietqr.io/v2/business/{mst_clean}"
        res = requests.get(url, timeout=10).json()
        if res.get('code') == '00':
            return "Đang hoạt động ✅", res.get('data', {}).get('name', '')
        return "Ngừng hoạt động ❌", ""
    except:
        return "Lỗi API Thuế ⚠️", ""

# --- 3. GIAO DIỆN ---
st.title("🛡️ Hệ thống Quét dữ liệu ĐKKD QLTT Thanh Hoá V2.0")

source = st.camera_input("Chụp ảnh Giấy phép")
if not source:
    source = st.file_uploader("Hoặc tải ảnh lên", type=["jpg","jpeg","png"])

if source:
    img_base64 = encode_image(source)
    
    if st.button("🚀 BẮT ĐẦU TRÍCH XUẤT ĐẦY ĐỦ"):
        with st.spinner("AI đang tìm kiếm kỹ lưỡng 16 trường dữ liệu..."):
            try:
                # PROMPT SIÊU CHI TIẾT ĐỂ ÉP AI LẤY ĐỦ DỮ LIỆU
                response = client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[{
                        "role": "user",
                        "content": [
                            {
                                "type": "text", 
                                "text": """Bạn là chuyên gia bóc tách hồ sơ pháp lý. Hãy trích xuất thông tin sang JSON.
                                KHÔNG ĐƯỢC BỎ SÓT BẤT CỨ TRƯỜNG NÀO TRONG 16 TRƯỜNG SAU:
                                {
                                    "Mã số hộ kinh doanh": "Tìm số GCN hoặc mã số hộ",
                                    "Tên hộ kinh doanh": "Tên đầy đủ",
                                    "Mã số thuế": "Mã số thuế 10 hoặc 13 số",
                                    "Địa chỉ trụ sở chính": "Địa chỉ ghi trên giấy phép",
                                    "Họ tên người đại diện": "Chủ hộ hoặc người đại diện",
                                    "Số điện thoại": "Nếu có",
                                    "Giới tính": "Nam/Nữ",
                                    "Ngày sinh": "dd/mm/yyyy",
                                    "Số CCCD hoặc Hộ chiếu": "Dãy số định danh",
                                    "Ngày cấp CCCD": "dd/mm/yyyy",
                                    "Nơi cấp CCCD": "Cục CSQLHC hoặc Công an tỉnh...",
                                    "Chỗ ở hiện nay": "Địa chỉ thường trú/tạm trú",
                                    "Ngành nghề kinh doanh": "Liệt kê đầy đủ",
                                    "Cơ quan cấp phép": "Phòng Tài chính - Kế hoạch huyện...",
                                    "Ngày đăng ký đầu": "dd/mm/yyyy",
                                    "Thay đổi gần nhất": "Ngày thay đổi (nếu có), nếu không có thì ghi 'Không'"
                                }. 
                                Yêu cầu: Không đánh số thứ tự ở tên trường. Nếu không thấy thông tin, ghi 'Không có'."""
                            },
                            {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{img_base64}"}}
                        ]
                    }],
                    response_format={"type": "json_object"}
                )
                st.session_state.full_data = json.loads(response.choices[0].message.content)
            except Exception as e:
                st.error(f"Lỗi: {e}")

    # --- 4. HIỂN THỊ VÀ CHỈNH SỬA ---
    if "full_data" in st.session_state:
        st.divider()
        st.subheader("📝 Kiểm tra & Hiệu chỉnh 16 trường nghiệp vụ")
        
        # Liên kết thuế
        mst_target = st.session_state.full_data.get('Mã số thuế') or st.session_state.full_data.get('Mã số hộ kinh doanh')
        status, name_tax = check_mst_status(mst_target)
        
        if "Hoạt động" in status: st.success(f"Trạng thái thuế: {status} | {name_tax}")
        else: st.warning(status)

        # Chia nhóm để hiển thị cho gọn trên điện thoại
        edited_final = {}
        
        with st.expander("📌 Thông tin chung (Tên, MST, Địa chỉ)", expanded=True):
            cols = st.columns(2)
            keys = list(st.session_state.full_data.keys())
            for i in range(0, 6): # 6 trường đầu
                with cols[i % 2]:
                    edited_final[keys[i]] = st.text_input(keys[i], st.session_state.full_data[keys[i]])

        with st.expander("👤 Thông tin cá nhân người đại diện"):
            cols = st.columns(2)
            for i in range(6, 12): # 6 trường tiếp theo
                with cols[i % 2]:
                    edited_final[keys[i]] = st.text_input(keys[i], st.session_state.full_data[keys[i]])

        with st.expander("📂 Thông tin Ngành nghề & Giấy phép"):
            for i in range(12, 16): # 4 trường cuối
                edited_final[keys[i]] = st.text_area(keys[i], st.session_state.full_data[keys[i]])

        # --- XUẤT EXCEL ---
        if st.button("✅ XÁC NHẬN VÀ TẠO EXCEL"):
            df = pd.DataFrame([edited_final])
            df['Trạng thái thuế'] = status
            
            output = BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                df.to_excel(writer, index=False)
            
            st.download_button(
                label="📥 TẢI FILE EXCEL FULL 16 TRƯỜNG",
                data=output.getvalue(),
                file_name=f"QLTT_FULL_{mst_target}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
