import streamlit as st
import pandas as pd
import os
from datetime import datetime, date
import io
import time
import re
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib import colors

# --- 1. CẤU HÌNH HỆ THỐNG & FILE ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FILE_PATH = {
    "gifts": os.path.join(BASE_DIR, "danhmuc_qua.csv"),
    "trans": os.path.join(BASE_DIR, "nhatky_xuatnhap.csv"),
    "session": os.path.join(BASE_DIR, "user_session.txt")
}


def init_csv():
    if not os.path.exists(FILE_PATH["gifts"]):
        pd.DataFrame(columns=["MaQua", "TenQua"]).to_csv(FILE_PATH["gifts"], index=False, encoding='utf-8-sig')
    if not os.path.exists(FILE_PATH["trans"]):
        pd.DataFrame(columns=["Loai", "Ngay", "Gio", "SoChungTu", "MaQua", "TenQua", "SoLuong", "NguoiThucHien",
                              "GhiChu"]).to_csv(FILE_PATH["trans"], index=False, encoding='utf-8-sig')


# --- 2. QUẢN LÝ PHIÊN ĐĂNG NHẬP ---
def save_session(u_id, u_name):
    with open(FILE_PATH["session"], "w", encoding="utf-8") as f:
        f.write(f"{u_id}|{u_name}")


def load_session():
    if os.path.exists(FILE_PATH["session"]):
        with open(FILE_PATH["session"], "r", encoding="utf-8") as f:
            data = f.read().split("|")
            if len(data) == 2: return {"id": data[0], "name": data[1]}
    return None


def clear_session():
    if os.path.exists(FILE_PATH["session"]):
        os.remove(FILE_PATH["session"])


# --- 3. TIỆN ÍCH PDF & MÃ QUÀ ---
def no_accent_vietnamese(s):
    s = str(s)
    s = re.sub(r'[àáạảãâầấậẩẫăằắặẳẵ]', 'a', s);
    s = re.sub(r'[ÀÁẠẢÃÂẦẤẬẨẪĂẰẮẶẲẴ]', 'A', s)
    s = re.sub(r'[èéẹẻẽêềếệểễ]', 'e', s);
    s = re.sub(r'[ÈÉẸẺẼÊỀẾỆỂỄ]', 'E', s)
    s = re.sub(r'[òóọỏõôồốộổỗơờớợởỡ]', 'o', s);
    s = re.sub(r'[ÒÓỌỎÕÔỒỐỘỔỖƠỜỚỢỞỠ]', 'O', s)
    s = re.sub(r'[ìíịỉĩ]', 'i', s);
    s = re.sub(r'[ÌÍỊỈĨ]', 'I', s)
    s = re.sub(r'[ùúụủũưừứựửữ]', 'u', s);
    s = re.sub(r'[ÙÚỤỦŨƯỪỨỰỬỮ]', 'U', s)
    s = re.sub(r'[ỳýỵỷỹ]', 'y', s);
    s = re.sub(r'[ỲÝỴỶỸ]', 'Y', s)
    s = re.sub(r'[đ]', 'd', s);
    s = re.sub(r'[Đ]', 'D', s)
    return s


def generate_new_gift_code():
    df_g = pd.read_csv(FILE_PATH["gifts"])
    if df_g.empty: return "QT0001"
    codes = [c for c in df_g['MaQua'].astype(str).tolist() if c.startswith("QT") and len(c) == 6]
    if not codes: return "QT0001"
    nums = [int(c[2:]) for c in codes if c[2:].isdigit()]
    return f"QT{(max(nums) + 1):04d}"


def get_current_stock(ma_qua):
    df_t = pd.read_csv(FILE_PATH["trans"])
    if df_t.empty: return 0
    return df_t[df_t["MaQua"].astype(str) == str(ma_qua)]["SoLuong"].sum()


def export_pdf_reportlab(df, date_range):
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    width, height = A4
    c.setFont("Helvetica-Bold", 16)
    c.drawCentredString(width / 2, height - 50, "BAO CAO XUAT NHAP TON")
    c.setFont("Helvetica", 10)
    c.drawCentredString(width / 2, height - 70, f"Thoi gian: {date_range}")
    y = height - 110
    c.setFont("Helvetica-Bold", 10)
    c.setFillColor(colors.grey)
    c.rect(40, y - 5, 520, 20, fill=1)
    c.setFillColor(colors.whitesmoke)
    headers = ["Ma", "Ten Qua", "Ton Dau", "Nhap", "Xuat", "Ton Cuoi"]
    x_pos = [50, 110, 300, 360, 420, 480]
    for i, txt in enumerate(headers): c.drawString(x_pos[i], y, txt)
    y -= 25
    c.setFillColor(colors.black);
    c.setFont("Helvetica", 9)
    for _, row in df.iterrows():
        if y < 50: c.showPage(); y = height - 50; c.setFont("Helvetica", 9)
        c.drawString(x_pos[0], y, no_accent_vietnamese(row['Mã']))
        c.drawString(x_pos[1], y, no_accent_vietnamese(row['Tên'])[:35])
        c.drawRightString(x_pos[2] + 30, y, str(row['Tồn đầu']))
        c.drawRightString(x_pos[3] + 25, y, str(row['Nhập']))
        c.drawRightString(x_pos[4] + 25, y, str(row['Xuất']))
        c.drawRightString(x_pos[5] + 30, y, str(row['Tồn cuối']))
        c.setStrokeColor(colors.lightgrey);
        c.line(40, y - 5, 560, y - 5);
        y -= 20
    c.save();
    buf.seek(0)
    return buf.getvalue()


# --- 4. GIAO DIỆN CHÍNH ---
st.set_page_config(page_title="Hệ Thống Kho Quà TNF", layout="wide")
init_csv()

if 'user_info' not in st.session_state:
    saved_user = load_session()
    if saved_user:
        st.session_state['user_info'] = saved_user
    else:
        with st.container(border=True):
            st.subheader("🔐 Đăng nhập")
            u_id = st.text_input("Mã nhân viên")
            u_name = st.text_input("Họ và tên")
            if st.button("ĐĂNG NHẬP", use_container_width=True, type="primary"):
                if u_id and u_name:
                    st.session_state['user_info'] = {"id": u_id, "name": u_name}
                    save_session(u_id, u_name)
                    st.rerun()
        st.stop()

with st.sidebar:
    st.write(f"👤: **{st.session_state['user_info']['name']}**")
    if st.button("Đăng xuất & Xóa nhớ"):
        clear_session()
        st.session_state.clear()
        st.rerun()

tabs = st.tabs(["📤 Xuất kho", "📥 Nhập kho", "📊 Báo cáo XNT", "📜 Nhật ký"])


def render_form(type_f="XUẤT"):
    df_g = pd.read_csv(FILE_PATH["gifts"])

    # Khởi tạo state để lưu trữ quà đang chọn
    if f"ma_{type_f}" not in st.session_state: st.session_state[f"ma_{type_f}"] = ""
    if f"ten_{type_f}" not in st.session_state: st.session_state[f"ten_{type_f}"] = ""
    if f"show_list_{type_f}" not in st.session_state: st.session_state[f"show_list_{type_f}"] = False

    # 1. KHU VỰC TÌM KIẾM VÀ CHỌN NHANH
    st.markdown(f"🔍 **Tìm kiếm quà tặng ({type_f}):**")

    col_search, col_list = st.columns([3, 1])
    with col_search:
        search_term = st.text_input("Nhập mã/tên...", key=f"search_{type_f}", label_visibility="collapsed",
                                    placeholder="Gõ để tìm nhanh...")
    with col_list:
        if st.button("📋 Danh sách", key=f"btn_list_{type_f}", use_container_width=True):
            st.session_state[f"show_list_{type_f}"] = not st.session_state[f"show_list_{type_f}"]

    # HIỂN THỊ DANH SÁCH QUÀ TẶNG (Khi nhấn nút Danh sách)
    if st.session_state[f"show_list_{type_f}"]:
        with st.expander("📂 Danh mục quà tặng đầy đủ", expanded=True):
            if not df_g.empty:
                # Tạo bảng có thêm cột nút bấm để chọn
                for _, row in df_g.iterrows():
                    c_info, c_btn = st.columns([4, 1])
                    c_info.write(f"**{row['MaQua']}** - {row['TenQua']}")
                    if c_btn.button("Chọn", key=f"sel_{type_f}_{row['MaQua']}", use_container_width=True):
                        st.session_state[f"ma_{type_f}"] = row['MaQua']
                        st.session_state[f"ten_{type_f}"] = row['TenQua']
                        st.session_state[f"show_list_{type_f}"] = False  # Đóng danh sách sau khi chọn
                        st.rerun()
            else:
                st.write("Danh mục trống.")

    # 2. XỬ LÝ KẾT QUẢ TÌM KIẾM NHANH (Gõ phím)
    if search_term and not st.session_state[f"show_list_{type_f}"]:
        filtered = df_g[df_g['MaQua'].astype(str).str.contains(search_term, case=False) |
                        df_g['TenQua'].str.contains(search_term, case=False)]

        if not filtered.empty:
            st.caption("Kết quả gợi ý:")
            for _, row in filtered.head(3).iterrows():
                if st.button(f"📍 {row['MaQua']} - {row['TenQua']}", key=f"btn_quick_{row['MaQua']}_{type_f}",
                             use_container_width=True):
                    st.session_state[f"ma_{type_f}"] = row['MaQua']
                    st.session_state[f"ten_{type_f}"] = row['TenQua']
                    st.rerun()
        elif type_f == "NHẬP":
            if st.button(f"➕ Tạo quà mới: {search_term}", use_container_width=True):
                st.session_state[f"ma_{type_f}"] = generate_new_gift_code()
                st.session_state[f"ten_{type_f}"] = search_term
                st.rerun()

    # 3. HIỂN THỊ TỒN KHO VÀ FORM CHI TIẾT
    curr_ma = st.session_state[f"ma_{type_f}"]
    curr_ten = st.session_state[f"ten_{type_f}"]

    if curr_ma:
        all_codes = df_g['MaQua'].astype(str).tolist()
        is_new = curr_ma not in all_codes

        # Hiển thị Tồn kho nổi bật
        if not is_new:
            ton = get_current_stock(curr_ma)
            clr = "#28a745" if ton > 5 else "#dc3545"
            st.markdown(f"""
                <div style="background-color: {clr}15; padding: 12px; border-radius: 10px; border: 1px solid {clr}; text-align: center; margin: 10px 0;">
                    <span style="color: {clr}; font-size: 16px;">Đang chọn: <b>{curr_ten}</b></span><br>
                    <span style="color: {clr}; font-size: 20px;">📊 Tồn kho: <b>{ton}</b></span>
                </div>
            """, unsafe_allow_html=True)

        with st.container(border=True):
            st.write(f"📝 **Phiếu {type_f}**")
            so_ct = st.text_input("Số chứng từ *", key=f"ct_{type_f}")

            c1, c2 = st.columns(2)
            # Dùng key cố định cho widget hiển thị, lấy giá trị từ session_state
            st.session_state[f"d_ma_{type_f}"] = curr_ma
            st.session_state[f"d_ten_{type_f}"] = curr_ten

            with c1:
                st.text_input("Mã Quà", key=f"d_ma_{type_f}", disabled=True)
            with c2:
                st.text_input("Tên Quà", key=f"d_ten_{type_f}", disabled=not is_new)

            sl = st.number_input("Số lượng *", min_value=1, step=1, key=f"sl_{type_f}")
            note = st.text_input("Ghi chú / Lý do", key=f"note_{type_f}")

            if st.button(f"💾 LƯU PHIẾU {type_f}", type="primary", use_container_width=True):
                if so_ct and curr_ma and curr_ten:
                    df_t = pd.read_csv(FILE_PATH["trans"])
                    new_t = {
                        "Loai": type_f, "Ngay": date.today().strftime("%Y-%m-%d"),
                        "Gio": datetime.now().strftime("%H:%M:%S"),
                        "SoChungTu": so_ct, "MaQua": curr_ma, "TenQua": curr_ten,
                        "SoLuong": sl if type_f == "NHẬP" else -sl,
                        "NguoiThucHien": f"{st.session_state['user_info']['id']} - {st.session_state['user_info']['name']}",
                        "GhiChu": note
                    }
                    pd.concat([df_t, pd.DataFrame([new_t])], ignore_index=True).to_csv(FILE_PATH["trans"], index=False,
                                                                                       encoding='utf-8-sig')

                    if is_new:
                        df_g_now = pd.read_csv(FILE_PATH["gifts"])
                        pd.concat([df_g_now, pd.DataFrame([{"MaQua": curr_ma, "TenQua": curr_ten}])],
                                  ignore_index=True).to_csv(FILE_PATH["gifts"], index=False, encoding='utf-8-sig')

                    st.success("✅ Thành công!");
                    time.sleep(0.5)
                    # Reset Form hoàn toàn
                    for k in [f"search_{type_f}", f"ct_{type_f}", f"sl_{type_f}", f"note_{type_f}", f"ma_{type_f}",
                              f"ten_{type_f}", f"d_ma_{type_f}", f"d_ten_{type_f}"]:
                        if k in st.session_state: del st.session_state[k]
                    st.rerun()
    else:
        st.info("👆 Tìm kiếm hoặc bấm nút 'Danh sách' để chọn quà.")

with tabs[0]: render_form("XUẤT")
with tabs[1]: render_form("NHẬP")

# BÁO CÁO XNT (Giữ nguyên logic cũ đã ổn định)
with tabs[2]:
    st.subheader("Báo cáo tồn kho")
    c1, c2 = st.columns(2)
    d1 = c1.date_input("Từ ngày", date(date.today().year, date.today().month, 1), key="rep_d1")
    d2 = c2.date_input("Đến ngày", date.today(), key="rep_d2")

    if st.button("📊 Chạy báo cáo", use_container_width=True):
        df_t = pd.read_csv(FILE_PATH["trans"])
        if not df_t.empty:
            df_t['Ngay'] = pd.to_datetime(df_t['Ngay']).dt.date
            df_g, r_list = pd.read_csv(FILE_PATH["gifts"]), []
            for _, item in df_g.iterrows():
                m, t = item['MaQua'], item['TenQua']
                t_dau = df_t[(df_t['MaQua'] == m) & (df_t['Ngay'] < d1)]['SoLuong'].sum()
                nhap = \
                df_t[(df_t['MaQua'] == m) & (df_t['Loai'] == "NHẬP") & (df_t['Ngay'] >= d1) & (df_t['Ngay'] <= d2)][
                    'SoLuong'].sum()
                xuat = abs(
                    df_t[(df_t['MaQua'] == m) & (df_t['Loai'] == "XUẤT") & (df_t['Ngay'] >= d1) & (df_t['Ngay'] <= d2)][
                        'SoLuong'].sum())
                r_list.append(
                    {"Mã": m, "Tên": t, "Tồn đầu": t_dau, "Nhập": nhap, "Xuất": xuat, "Tồn cuối": t_dau + nhap - xuat})
            st.session_state['report_final'] = pd.DataFrame(r_list)

    if 'report_final' in st.session_state:
        st.dataframe(st.session_state['report_final'], use_container_width=True, hide_index=True)
        ce, cp = st.columns(2)
        buf_ex = io.BytesIO()
        with pd.ExcelWriter(buf_ex, engine='xlsxwriter') as wr: st.session_state['report_final'].to_excel(wr,
                                                                                                          index=False)
        ce.download_button("📥 Excel", buf_ex.getvalue(), "Bao_cao.xlsx", use_container_width=True)
        pdf_bytes = export_pdf_reportlab(st.session_state['report_final'], f"{d1} - {d2}")
        cp.download_button("📄 PDF", pdf_bytes, "Bao_cao.pdf", mime="application/pdf", use_container_width=True)

with tabs[3]:
    st.subheader("Lịch sử giao dịch")
    st.dataframe(pd.read_csv(FILE_PATH["trans"]).iloc[::-1], use_container_width=True, hide_index=True)