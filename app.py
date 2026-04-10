import streamlit as st
import google.generativeai as genai
from PIL import Image
import pandas as pd
import json
from io import BytesIO

# 1. Cấu hình API Key từ Secrets
try:
    GOOGLE_API_KEY = st.secrets["GOOGLE_API_KEY"]
    genai.configure(api_key=GOOGLE_API_KEY)
except:
    st.error("Chưa cấu hình API Key trong Secrets!")

st.set_page_config(page_title="AI Extractor Pro V2", layout="wide")
st.title("🚀 AI Tách Dữ Liệu Chuyên Sâu")

uploaded_file = st.file_uploader("Tải ảnh giấy phép hoặc CCCD lên...", type=["jpg", "jpeg", "png"])

if uploaded_file is not None:
    col1, col2 = st.columns([1, 1.5]) # Chia tỷ lệ cột để bảng hiển thị rộng hơn
    
    image = Image.open(uploaded_file)
    with col1:
        st.image(image, caption='Ảnh gốc', use_container_width=True)
    
    if st.button('Bắt đầu phân tích'):
        with st.spinner('AI đang quét toàn bộ thông tin...'):
            try:
                model = genai.GenerativeModel('gemini-3-flash-preview')
                
                # Prompt đã được nâng cấp để lấy thêm các thông tin cá nhân
                prompt = """
                Bạn là một chuyên gia OCR. Hãy đọc ảnh và trả về kết quả duy nhất dưới dạng JSON (không kèm lời dẫn) với các trường sau:
                {
                    "Tên hộ/Doanh nghiệp": "",
                    "Mã số thuế": "",
                    "Địa chỉ trụ sở": "",
                    "Người đại diện": "",
                    "Số điện thoại": "",
                    "Giới tính": "",
                    "Ngày sinh": "",
                    "Số giấy tờ định danh": "",
                    "Ngày cấp": "",
                    "Nơi cấp": "",
                    "Chỗ ở hiện nay": "",
                    "Ngành nghề kinh doanh": "",
                    "Ngày cấp đăng ký KD": ""
                }
                Lưu ý: Nếu thông tin nào không có trong ảnh, hãy để trống "". 
                Đặc biệt chú ý phần thông tin cá nhân của người đại diện/chủ hộ.
                """
                
                response = model.generate_content([prompt, image])
                
                # Làm sạch kết quả JSON
                clean_json = response.text.replace('```json', '').replace('```', '').strip()
                data_dict = json.loads(clean_json)
                
                with col2:
                    st.success("Trích xuất hoàn tất!")
                    
                    # Tạo DataFrame và hiển thị dạng bảng đứng cho dễ đọc
                    df = pd.DataFrame([data_dict])
                    st.table(df.T) 
                    
                    # --- Xử lý xuất file Excel ---
                    output = BytesIO()
                    with pd.ExcelWriter(output, engine='openpyxl') as writer:
                        df.to_excel(writer, index=False, sheet_name='DuLieuChiTiet')
                    
                    excel_data = output.getvalue()
                    
                    st.download_button(
                        label="📥 Tải về file Excel chi tiết",
                        data=excel_data,
                        file_name=f"thong_tin_{data_dict.get('Mã số thuế', 'moi')}.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                    )
                
            except Exception as e:
                st.error(f"Lỗi: {e}. Hãy thử lại hoặc kiểm tra độ rõ nét của ảnh.")

st.divider()
st.caption("Phiên bản cập nhật: Hỗ trợ trích xuất thông tin cá nhân và doanh nghiệp.")
