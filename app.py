import streamlit as st
import google.generativeai as genai
from PIL import Image
import pandas as pd
import json
from io import BytesIO

# 1. Cấu hình API Key
GOOGLE_API_KEY = st.secrets["GOOGLE_API_KEY"]
genai.configure(api_key=GOOGLE_API_KEY)

st.set_page_config(page_title="AI Extractor Pro", layout="wide")
st.title("🚀 AI Tách Dữ Liệu & Xuất Excel")

uploaded_file = st.file_uploader("Tải ảnh giấy phép lên...", type=["jpg", "jpeg", "png"])

if uploaded_file is not None:
    col1, col2 = st.columns(2)
    
    image = Image.open(uploaded_file)
    with col1:
        st.image(image, caption='Ảnh gốc', use_container_width=True)
    
    if st.button('Bắt đầu phân tích'):
        with st.spinner('AI đang đọc dữ liệu và lập bảng...'):
            try:
                # Sử dụng model Gemini 3 Flash cho độ chính xác cao nhất
                model = genai.GenerativeModel('gemini-3-flash-preview')
                
                # Prompt yêu cầu trả về JSON để dễ xử lý vào Excel
                prompt = """
                Bạn là một chuyên gia bóc tách dữ liệu. Hãy đọc ảnh và trả về kết quả duy nhất dưới dạng JSON (không kèm lời dẫn) với các trường sau:
                {
                    "Tên hộ kinh doanh/Doanh nghiệp": "",
                    "Mã số thuế/Mã số hộ": "",
                    "Địa chỉ trụ sở": "",
                    "Người đại diện": "",
                    "Ngành nghề kinh doanh": "",
                    "Ngày cấp": ""
                }
                Lưu ý: Nếu thông tin ngành nghề dài, hãy tóm tắt đầy đủ các ý chính.
                """
                
                response = model.generate_content([prompt, image])
                
                # Xử lý kết quả trả về (loại bỏ markdown nếu AI có kèm vào)
                clean_json = response.text.replace('```json', '').replace('```', '').strip()
                data_dict = json.loads(clean_json)
                
                with col2:
                    st.success("Đã trích xuất xong!")
                    # Hiển thị kết quả lên màn hình dưới dạng bảng
                    df = pd.DataFrame([data_dict])
                    st.table(df.T) # Xoay bảng để dễ nhìn trên điện thoại/máy tính
                    
                    # --- Xử lý xuất file Excel ---
                    output = BytesIO()
                    with pd.ExcelWriter(output, engine='openpyxl') as writer:
                        df.to_excel(writer, index=False, sheet_name='DuLieuKinhDoanh')
                    
                    excel_data = output.getvalue()
                    
                    st.download_button(
                        label="📥 Tải về file Excel",
                        data=excel_data,
                        file_name=f"du_lieu_{data_dict['Mã số thuế/Mã số hộ']}.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                    )
                
            except Exception as e:
                st.error(f"Có lỗi xảy ra: {e}. Vui lòng thử lại hoặc kiểm tra lại ảnh.")

st.divider()
st.info("Mẹo: Để kết quả ngành nghề chính xác nhất, bạn nên chụp rõ phần 'Ngành, nghề kinh doanh' trên giấy phép.")
