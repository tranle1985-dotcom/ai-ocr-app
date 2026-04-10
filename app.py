import streamlit as st
import google.generativeai as genai
from PIL import Image
import pandas as pd
from datetime import datetime
import json
import requests
from io import BytesIO

# --- 1. CẤU HÌNH GIAO DIỆN ---
st.set_page_config(page_title="AI QLTT - Trích xuất dữ liệu ĐKKD", layout="wide", page_icon="⚖️")

# Kết nối API từ Secrets
try:
    genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
except:
    st.error("❌ Lỗi: Chưa cấu hình API Key trong Secrets!")

# Sử dụng model 1.5 Flash để đảm bảo tốc độ và hạn mức sử dụng (Quota)
MODEL_NAME = 'gemini-1.5-flash'

# --- 2. HÀM ĐỐI SOÁT THUẾ ---
def check_mst_status(mst):
    mst_clean = "".join(filter(str.isdigit, str(mst)))
    if not mst_clean: return "Không xác định", ""
    try:
        url = f"https://api.vietqr.io/v2/business/{mst_clean}"
        res = requests.get(url, timeout=5).json()
        if res.get('code') == '00':
            return "Đang hoạt động ✅", res.get('data', {}).get('name', '')
        return "Ngừng hoạt động/Đóng MST ❌", ""
    except:
        return "Lỗi tra cứu API ⚠️", ""

# --- 3. GIAO DIỆN SIDEBAR ---
with st.sidebar:
    st.header("🛡️ Đội QLTT số 10")
    st.write("**Cán bộ:** Trần Lê")
    st.write("**Địa bàn:** Nga Sơn - Thanh Hóa")
    st.divider()
    st.info("Bản cập nhật v3.5: Trích xuất 15 trường dữ liệu chi tiết.")

# --- 4. GIAO DIỆN CHÍNH ---
st.title("🛡️ Hệ thống Trích xuất & Đối soát Pháp lý")

col_in, col_out = st.columns([1, 1.2])

with col_in:
    st.subheader("📸 Nguồn dữ liệu")
    source = st.camera_input("Chụp ảnh giấy phép")
    if not source:
        source = st.file_uploader("Hoặc tải ảnh lên", type=["jpg","jpeg","png"])

if source:
    img = Image.open(source)
    with col_in:
        st.image(img, caption="Ảnh gốc từ hiện trường", use_container_width=True)
    
    if st.button("🚀 BẮT ĐẦU PHÂN TÍCH CHI TIẾT"):
        with st.spinner("AI đang bóc tách từng dòng dữ liệu..."):
            try:
                model = genai.GenerativeModel(MODEL_NAME)
                # Prompt yêu cầu bóc tách 15 trường thông tin cụ thể
                prompt = """
                Bạn là chuyên gia đọc hồ sơ pháp lý Việt Nam. Hãy trích xuất thông tin từ ảnh sang JSON chính xác. 
                Nếu không có thông tin nào, hãy để trống "".
                JSON trả về gồm các trường:
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
                    "nganh_nghe": "Ngành nghề kinh doanh (chi tiết mã ngành)",
                    "ngay_cap_dau": "Ngày đăng ký lần đầu",
                    "ngay_thay_doi": "Ngày thay đổi gần nhất"
                }
                Chỉ trả về mã JSON, không thêm văn bản khác.
                """
                
                response = model.generate_content([prompt, img])
                res_text = response.text.strip()
                
                # Làm sạch dữ liệu JSON
                if "```json" in res_text:
                    res_text = res_text.split("```json")[1].split("```")[0].strip()
                elif "```" in res_text:
                    res_text = res_text.split("```")[1].strip()
                
                data = json.loads(res_text)
                
                # Đối soát trạng thái hoạt động của MST
                status, name_tax = check_mst_status(data.get('mst', data.get('so_gcn')))

                with col_out:
                    st.subheader("📋 Báo cáo dữ liệu pháp lý")
                    if "Hoạt động" in status: st.success(status)
                    else: st.error(status)
                    
                    # Trình bày bảng hiển thị chuyên nghiệp
                    table_data = {
                        "Hạng mục thông tin": [
                            "🏢 Tên cơ sở", "🆔 Mã số (GCN/MST)", "📍 Địa chỉ trụ sở",
                            "👤 Người đại diện", "📞 Số điện thoại", "⚤ Giới tính/Ngày sinh",
                            "🪪 CCCD & Nơi cấp", "🏠 Chỗ ở hiện nay", "📝 Ngành nghề kinh doanh",
                            "📅 Ngày cấp/Thay đổi"
                        ],
                        "Dữ liệu trích xuất": [
                            data.get('ten_hkd'),
                            data.get('mst') or data.get('so_gcn'),
                            data.get('dia_chi'),
                            data.get('dai_dien'),
                            data.get('phone'),
                            f"{data.get('gioi_tinh')} | {data.get('ngay_sinh')}",
                            f"{data.get('cccd')} (Cấp ngày {data.get('ngay_cap_cccd')} tại {data.get('noi_cap_cccd')})",
                            data.get('cho_o'),
                            data.get('nganh_nghe'),
                            f"Lần đầu: {data.get('ngay_cap_dau')} | Thay đổi: {data.get('ngay_thay_doi')}"
                        ]
                    }
                    st.table(pd.DataFrame(table_data))

                    # --- XỬ LÝ XUẤT EXCEL ---
                    df_full = pd.DataFrame([data])
                    df_full['Trạng thái thuế'] = status
                    df_full['Thời gian kiểm tra'] = datetime.now().strftime("%d/%m/%Y %H:%M")
                    
                    output = BytesIO()
                    with pd.ExcelWriter(output, engine='openpyxl') as writer:
                        df_full.to_excel(writer, index=False, sheet_name='DuLieuChiTiet')
                    
                    st.divider()
                    st.download_button(
                        label="📥 XUẤT BÁO CÁO EXCEL (FULL)",
                        data=output.getvalue(),
                        file_name=f"QLTT_NgaSon_{data.get('mst') or data.get('so_gcn')}.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                    )

            except Exception as e:
                st.error(f"⚠️ Có sự cố xảy ra: {e}")
                st.info("Mẹo: Kiểm tra lại API Key hoặc chất lượng ảnh chụp.")
