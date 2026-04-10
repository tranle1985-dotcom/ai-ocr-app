# --- UI STYLE ---
st.markdown("""
<style>
.main {
    background-color: #f5f7fa;
}

h1 {
    text-align: center;
    color: #0b3d91;
    font-weight: bold;
}

.block-container {
    padding-top: 2rem;
}

.stButton>button {
    background-color: #d90429;
    color: white;
    border-radius: 10px;
    height: 50px;
    font-size: 16px;
    font-weight: bold;
}

.stTextInput>div>div>input {
    border-radius: 8px;
}

.css-1d391kg {
    background-color: #0b3d91;
}

.card {
    background-color: white;
    padding: 15px;
    border-radius: 12px;
    box-shadow: 0 2px 8px rgba(0,0,0,0.1);
    margin-bottom: 10px;
}
</style>
""", unsafe_allow_html=True)

# --- HEADER ---
st.markdown("""
<h1>🛡️ HỆ THỐNG NGHIỆP VỤ QUẢN LÝ THỊ TRƯỜNG THANH HOÁ</h1>
<hr>
""", unsafe_allow_html=True)

# --- SIDEBAR ---
st.sidebar.markdown("## ⚙️ Cấu hình")
danh_sach_doi = [f"Đội QLTT số {i}" for i in range(1, 14)]
selected_doi = st.sidebar.selectbox("🚩 Chọn Đội", danh_sach_doi)

user = st.sidebar.text_input("👤 Người nhập")

st.sidebar.markdown("---")
st.sidebar.info("Hệ thống AI hỗ trợ bóc tách dữ liệu giấy phép kinh doanh")

# --- MAIN LAYOUT ---
col1, col2 = st.columns([1, 1])

with col1:
    st.markdown("### 📷 Nguồn ảnh")

    source = st.camera_input("Chụp ảnh")

    if not source:
        source = st.file_uploader("Tải ảnh lên", type=["jpg","jpeg","png"])

    if source:
        st.success("✅ Đã nhận ảnh")

with col2:
    st.markdown("### 🖼️ Xem trước")

    if source:
        st.image(source, use_container_width=True)
    else:
        st.info("Chưa có ảnh")

# --- AI BUTTON ---
if source:
    st.markdown("---")
    if st.button("🚀 PHÂN TÍCH GIẤY PHÉP", use_container_width=True):
        with st.spinner("🤖 AI đang phân tích dữ liệu..."):
            try:
                mime_type = source.type
                img_base64 = base64.b64encode(source.getvalue()).decode()

                response = client_ai.chat.completions.create(
                    model="gpt-4.1-mini",
                    messages=[
                        {
                            "role": "system",
                            "content": "Trích xuất dữ liệu giấy phép kinh doanh Việt Nam. Trả JSON chuẩn, không giải thích."
                        },
                        {
                            "role": "user",
                            "content": [
                                {"type": "text", "text": "Trích xuất đầy đủ thông tin giấy phép kinh doanh."},
                                {"type": "image_url", "image_url": {"url": f"data:{mime_type};base64,{img_base64}"}}
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

# --- DATA DISPLAY ---
if "data" in st.session_state:
    st.markdown("---")
    st.markdown(f"## 📝 KIỂM TRA DỮ LIỆU - {selected_doi}")

    cols = st.columns(2)
    edited = {}

    for i, key in enumerate(st.session_state.data.keys()):
        with cols[i % 2]:
            st.markdown(f"<div class='card'><b>{key}</b></div>", unsafe_allow_html=True)
            edited[key] = st.text_input("", st.session_state.data[key])

            if edited[key] == "Không có":
                st.warning(f"⚠️ Thiếu {key}")

    # --- JSON VIEW ---
    with st.expander("🔍 Xem dữ liệu AI gốc"):
        st.json(st.session_state.data)

    # --- SAVE BUTTON ---
    if st.button("💾 GHI NHẬN DỮ LIỆU", use_container_width=True):
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

                st.success("✅ Đã lưu dữ liệu thành công!")

                # Excel export
                df = pd.DataFrame([edited])
                output = BytesIO()

                with pd.ExcelWriter(output, engine='openpyxl') as writer:
                    df.to_excel(writer, index=False)

                st.download_button(
                    "📥 Tải file Excel",
                    output.getvalue(),
                    file_name="dulieu.xlsx"
                )

            except:
                st.error("❌ Lỗi lưu dữ liệu")

# --- FOOTER ---
st.markdown("""
<hr>
<p style='text-align:center; color:gray'>
QLTT Thanh Hoá - Hệ thống AI v3.3
</p>
""", unsafe_allow_html=True)
