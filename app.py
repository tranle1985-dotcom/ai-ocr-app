import datetime
# Hoặc chính xác hơn nếu code bạn dùng datetime.now():
from datetime import datetime
import streamlit as st
from openai import OpenAI
import base64
from PIL import Image
import pandas as pd
import json
import requests
from io import BytesIO

# --- 1. CẤU HÌNH HỆ THỐNG ---
st.set_page_config(page_title="Hệ thống QLTT v2.0 - OpenAI Mini", layout="wide", page_icon="🛡️")

# Khởi tạo OpenAI (Dùng gpt-4o-mini để tiết kiệm 50 lần chi phí)
if "OPENAI_API_KEY" in st.secrets:
    client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])
else:
    st.error("❌ Chưa nhập OPENAI_API_KEY vào mục Secrets!")

def encode_image(image_file):
    return base64.b64encode(image_file.getvalue()).decode('utf-8')

# --- 2. HÀM TRA CỨU THUẾ (VIETQR) ---
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

# --- 3. GIAO DIỆN CHÍNH ---
st.title("🛡️ Hệ thống Quét dữ liệu ĐKKD QLTT Thanh Hoá (v2.0)")
st.info("💡 Sử dụng model GPT-4o-mini: Chi phí cực thấp (~10 đồng/tờ), độ chính xác cao.")

col_in, col_out = st.columns([1, 1.3])

with col_in:
    source = st.camera_input("Chụp ảnh Giấy chứng nhận")
    if not source:
        source = st.file_uploader("Hoặc tải ảnh lên", type=["jpg","jpeg","png"])

if source:
    img_base64 = encode_image(source)
    with col_in: st.image(source, use_container_width=True)
    
    if st.button("🚀 PHÂN TÍCH ĐẦY ĐỦ"):
        with st.spinner("Đang bóc tách dữ liệu nghiệp vụ..."):
            try:
                # Gọi OpenAI với model gpt-4o-mini
                response = client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[
                        {
                            "role": "user",
                            "content": [
                                {
                                    "type": "text", 
                                    "text": """Bạn là chuyên gia bóc tách hồ sơ pháp lý Việt Nam. Hãy trích xuất thông tin từ ảnh sang JSON. 
                                    PHẢI TÌM VÀ ĐIỀN ĐỦ 16 TRƯỜNG SAU:
                                    {
                                        "1. Số GCN/Mã số hộ": "so_gcn",
                                        "2. Tên hộ kinh doanh/DN": "ten_hkd",
                                        "3. Mã số thuế": "mst",
                                        "4. Địa chỉ trụ sở chính": "dia_chi",
                                        "5. Họ tên người đại diện": "dai_dien",
                                        "6. Số điện thoại": "phone",
                                        "7. Giới tính": "gioi_tinh",
                                        "8. Ngày sinh": "ngay_sinh",
                                        "9. Số CCCD/Hộ chiếu": "cccd",
                                        "10. Ngày cấp CCCD": "ngay_cap_cccd",
                                        "11. Nơi cấp CCCD": "noi_cap_cccd",
                                        "12. Chỗ ở hiện nay": "cho_o",
                                        "13. Ngành nghề kinh doanh": "nganh_nghe",
                                        "14. Cơ quan cấp Giấy phép": "co_quan_cap_gcn",
                                        "15. Ngày đăng ký đầu": "ngay_cap_dau",
                                        "16. Thay đổi gần nhất": "ngay_thay_doi"
                                    }. Chỉ trả về duy nhất mã JSON, không thêm văn bản khác."""
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
                
                # Xử lý kết quả
                data = json.loads(response.choices[0].message.content)
                status, name_tax = check_mst_status(data.get('3. Mã số thuế') or data.get('1. Số GCN/Mã số hộ'))

                with col_out:
                    st.subheader("📋 Kết quả trích xuất chi tiết")
                    if "Hoạt động" in status: st.success(status)
                    else: st.error(status)
                    
                    # Hiển thị bảng 16 trường
                    df_view = pd.DataFrame(list(data.items()), columns=["Hạng mục thông tin", "Dữ liệu trích xuất"])
                    st.table(df_view)

                    if name_tax:
                        st.caption(f"🔍 Đối soát hệ thống thuế: **{name_tax}**")

                    # XUẤT FILE EXCEL
                    df_excel = pd.DataFrame([data])
                    df_excel['Trạng thái thuế'] = status
                    output = BytesIO()
                    with pd.ExcelWriter(output, engine='openpyxl') as writer:
                        df_excel.to_excel(writer, index=False)
                    
                    st.divider()
                    st.download_button(
                        label="📥 TẢI EXCEL FULL 16 TRƯỜNG",
                        data=output.getvalue(),
                        file_name=f"QLTT_ThanhHoa_{datetime.now().strftime('%H%M%S')}.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                    )

            except Exception as e:
                st.error(f"Sự cố OpenAI: {e}")
