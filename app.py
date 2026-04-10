import streamlit as st
import google.generativeai as genai
from PIL import Image
import pandas as pd
import json
from io import BytesIO

# 1. Cấu hình API Key bảo mật từ Streamlit Secrets
try:
    GOOGLE_API_KEY = st.secrets["GOOGLE_API_KEY"]
    genai.configure(api_key=GOOGLE_API_KEY)
except Exception:
    st.error("Lỗi: Chưa cấu hình GOOGLE_API_KEY trong phần Settings > Secrets của Streamlit.")

# 2. Thiết lập giao diện ứng dụng
st.set_page_config(page_title="AI OCR Pháp Quy - Quản Lý Thị Trường", layout="wide")

st.title("🔍 Hệ Thống Tách Dữ Liệu Đăng Ký Kinh Doanh")
st.markdown("---")

# 3. Thành phần tải ảnh lên
uploaded_file = st.file_uploader("Tải ảnh Giấy phép hộ kinh doanh hoặc Doanh nghiệp...", type=["jpg", "jpeg", "png"])

if uploaded_file is not None:
    # Chia giao diện làm 2 cột: Trái hiện ảnh, Phải hiện bảng dữ liệu
    col1, col2 = st.columns([1, 1.2])
    
    image = Image.open(uploaded_file)
    with col1:
        st.image(image, caption='Hình ảnh đã tải lên', use_container_width=True)
    
    if st.button('🚀 Bắt đầu phân tích dữ liệu'):
        with st.spinner('AI đang quét và bóc tách thông tin, vui lòng đợi...'):
            try:
                # Sử dụng model Gemini 3 Flash mới nhất
                model = genai.GenerativeModel('gemini-3-flash-preview')
                
                # Prompt tối ưu để lấy đầy đủ thông tin theo yêu cầu của bạn
                prompt = """
                Bạn là một chuyên gia OCR chuyên nghiệp về tài liệu pháp lý Việt Nam. 
                Hãy đọc ảnh và trả về kết quả DUY NHẤT dưới dạng JSON (không có lời dẫn, không có markdown ```json) với các trường sau:
                {
                    "Số giấy chứng nhận/Mã số hộ": "",
                    "Tên hộ/Doanh nghiệp": "",
                    "Mã số thuế": "",
                    "Địa chỉ trụ sở chính": "",
                    "Họ tên người đại diện": "",
                    "Số điện thoại": "",
                    "Giới tính": "",
                    "Ngày sinh": "",
                    "Số CCCD/Hộ chiếu": "",
                    "Ngày cấp CCCD": "",
                    "Nơi cấp CCCD": "",
                    "Chỗ ở hiện nay": "",
                    "Ngành nghề kinh doanh": "",
                    "Nơi cấp": "",
                    "Ngày cấp đăng ký KD lần đầu": "",
                    "Ngày thay đổi gần nhất": ""
                }
                Quy tắc:
                1. Nếu thông tin không có trong ảnh, để giá trị là "".
                2. 'Số giấy chứng nhận' thường nằm sau chữ 'Số:' ở đầu văn bản.
                3. Đảm bảo các con số (MST, CCCD, Ngày tháng) chính xác 100%.
                """
                
                # Gửi yêu cầu đến AI
                response = model.generate_content([prompt, image])
                
                # Xử lý văn bản thô từ AI để lấy đúng định dạng JSON
                raw_text = response.text.strip()
                if raw_text.startswith("```"):
                    raw_text = raw_text.split("\n", 1)[1].rsplit("\n", 1)[0]
                
                data_dict = json.loads(raw_text)
                
                with col2:
                    st.success("✅ Đã trích xuất dữ liệu thành công!")
                    
                    # Tạo DataFrame và hiển thị bảng xoay dọc để dễ nhìn
                    df = pd.DataFrame([data_dict])
                    st.table(df.T)
                    
                    # 4. Tính năng Xuất file Excel
                    output = BytesIO()
                    with pd.ExcelWriter(output, engine='openpyxl') as writer:
                        df.to_excel(writer, index=False, sheet_name='DuLieuTrichXuat')
                    
                    excel_data = output.getvalue()
                    
                    st.download_button(
                        label="📥 Tải về file Excel kết quả",
                        data=excel_data,
                        file_name=f"ket_qua_{data_dict.get('Số giấy chứng nhận/Mã số hộ', 'khong_ten')}.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                    )
                
            except json.JSONDecodeError:
                st.error("Lỗi: AI trả về dữ liệu không đúng cấu hình. Bạn hãy thử nhấn lại nút phân tích.")
            except Exception as e:
                st.error(f"Đã xảy ra lỗi hệ thống: {e}")

st.markdown("---")
st.info("💡 Lưu ý: Kết quả tốt nhất khi ảnh chụp rõ nét, không bị lóa đèn hoặc bị che khuất các dòng chữ.")
