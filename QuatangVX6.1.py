import streamlit as st
import pandas as pd
import os
from datetime import datetime, date
import io
import time
import re
from fpdf import FPDF

# --- 1. THIẾT LẬP FILE CSV ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FILE_PATH = {
    "gifts": os.path.join(BASE_DIR, "danhmuc_qua.csv"),
    "trans": os.path.join(BASE_DIR, "nhatky_xuatnhap.csv")
}


def init_csv():
    """Khởi tạo file nếu chưa tồn tại"""
    if not os.path.exists(FILE_PATH["gifts"]):
        pd.DataFrame(columns=["MaQua", "TenQua"]).to_csv(FILE_PATH["gifts"], index=False, encoding='utf-8-sig')
    if not os.path.exists(FILE_PATH["trans"]):
        pd.DataFrame(columns=["Loai", "Ngay", "Gio", "SoChungTu", "MaQua", "TenQua", "SoLuong", "NguoiThucHien",
                              "GhiChu"]).to_csv(FILE_PATH["trans"], index=False, encoding='utf-8-sig')


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


def get_current_stock(ma_qua):
    df_t = pd.read_csv(FILE_PATH["trans"])
    if df_t.empty: return 0
    return df_t[df_t["MaQua"].astype(str) == str(ma_qua)]["SoLuong"].sum()


def export_pdf(df):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", 'B', 14)
    pdf.cell(190, 10, txt="BAO CAO XUAT NHAP TON", ln=True, align='C')
    pdf.ln(10)
    cols = ["Ma", "Ten Qua", "Ton Dau", "Nhap", "Xuat", "Ton Cuoi"]
    widths = [20, 65, 25, 25, 25, 30]
    for i, col in enumerate(cols):
        pdf.cell(widths[i], 8, col, border=1, align='C')
    pdf.ln()
    pdf.set_font("Arial", '', 9)
    for _, row in df.iterrows():
        pdf.cell(widths[0], 8, no_accent_vietnamese(row['Mã']), border=1)
        pdf.cell(widths[1], 8, no_accent_vietnamese(row['Tên']), border=1)
        pdf.cell(widths[2], 8, str(row['Tồn đầu']), border=1, align='C')
        pdf.cell(widths[3], 8, str(row['Nhập']), border=1, align='C')
        pdf.cell(widths[4], 8, str(row['Xuất']), border=1, align='C')
        pdf.cell(widths[5], 8, str(row['Tồn cuối']), border=1, align='C')
        pdf.ln()
    return pdf.output(dest='S').encode('latin1', errors='replace')


# --- 2. GIAO DIỆN & LOGIN ---
st.set_page_config(page_title="Kho Quà TNF", layout="wide")
init_csv()


def lookup_user():
    m_id = st.session_state.get('temp_id', '')
    if m_id:
        df_t = pd.read_csv(FILE_PATH["trans"])
        if not df_t.empty:
            match = df_t[df_t['NguoiThucHien'].str.startswith(f"{m_id} - ")]
            if not match.empty:
                st.session_state['temp_name'] = match.iloc[0]['NguoiThucHien'].split(" - ")[1]


if 'user_info' not in st.session_state:
    with st.container(border=True):
        st.subheader("🔐 Đăng nhập hệ thống")
        u_id = st.text_input("Mã nhân viên *", key='temp_id', on_change=lookup_user)
        u_name = st.text_input("Họ và Tên *", key='temp_name')
        if st.button("BẮT ĐẦU LÀM VIỆC", type="primary", use_container_width=True):
            if u_id and u_name:
                st.session_state['user_info'] = {"id": u_id, "name": u_name}
                st.rerun()
            else:
                st.warning("Vui lòng nhập đầy đủ.")
    st.stop()

# --- 3. MAIN APP ---
with st.sidebar:
    st.success(f"👤 {st.session_state['user_info']['name']}")
    if st.button("Đăng xuất"):
        del st.session_state['user_info']
        st.rerun()

tabs = st.tabs(["📤 Xuất kho", "📥 Nhập kho", "📊 Báo cáo XNT", "📜 Nhật ký"])


def render_form(type_f="XUẤT"):
    df_g = pd.read_csv(FILE_PATH["gifts"])
    for key in [f"ma_{type_f}", f"ten_{type_f}", f"new_{type_f}"]:
        if key not in st.session_state: st.session_state[key] = "" if "new" not in key else False

    st.markdown(f"🔍 **Tìm kiếm quà ({type_f}):**")
    src = st.text_input("Nhập mã hoặc tên...", key=f"src_{type_f}")

    filtered = df_g[df_g['MaQua'].astype(str).str.contains(src, case=False) |
                    df_g['TenQua'].str.contains(src, case=False)] if src else pd.DataFrame()

    if not filtered.empty:
        sel = st.radio("Kết quả:", filtered.apply(lambda x: f"{x['MaQua']} - {x['TenQua']}", axis=1),
                       key=f"rad_{type_f}")
        if sel:
            m, t = sel.split(" - ")
            st.session_state[f"ma_{type_f}"], st.session_state[f"ten_{type_f}"] = m, t
            st.session_state[f"new_{type_f}"] = False
    elif src != "" and type_f == "NHẬP":
        if st.button("➕ Thêm quà mới vào danh mục"):
            st.session_state[f"ma_{type_f}"], st.session_state[f"ten_{type_f}"] = "", src
            st.session_state[f"new_{type_f}"] = True

    with st.container(border=True):
        st.markdown(f"📝 **Phiếu {type_f} kho**")
        so_ct = st.text_input("Số chứng từ *", key=f"ct_{type_f}")

        lock = True if type_f == "XUẤT" or (
                    type_f == "NHẬP" and not st.session_state[f"new_{type_f}"] and not df_g.empty) else False
        c1, c2 = st.columns(2)
        with c1:
            ma = st.text_input("Mã Quà *", key=f"ma_{type_f}", disabled=lock)
        with c2:
            ten = st.text_input("Tên Quà *", key=f"ten_{type_f}", disabled=lock)

        sl = st.number_input("Số lượng *", min_value=1, step=1, key=f"sl_{type_f}")
        if ma: st.info(f"📊 Tồn kho hiện tại: **{get_current_stock(ma)}**")

        note = st.text_input("Ghi chú", key=f"n_{type_f}")

        if st.button(f"LƯU PHIẾU {type_f}", type="primary", use_container_width=True):
            stk = get_current_stock(ma) if ma else 0
            if type_f == "XUẤT" and (not ma or sl > stk):
                st.error("Lỗi: Quà không tồn tại hoặc không đủ tồn kho!")
            elif ma and ten and so_ct:
                # Ghi nhật ký
                df_t = pd.read_csv(FILE_PATH["trans"])
                new_row = {"Loai": type_f, "Ngay": date.today().strftime("%Y-%m-%d"),
                           "Gio": datetime.now().strftime("%H:%M:%S"),
                           "SoChungTu": so_ct, "MaQua": ma, "TenQua": ten, "SoLuong": sl if type_f == "NHẬP" else -sl,
                           "NguoiThucHien": f"{st.session_state['user_info']['id']} - {st.session_state['user_info']['name']}",
                           "GhiChu": note}
                pd.concat([df_t, pd.DataFrame([new_row])], ignore_index=True).to_csv(FILE_PATH["trans"], index=False,
                                                                                     encoding='utf-8-sig')

                # Cập nhật danh mục nếu là nhập mới
                if type_f == "NHẬP":
                    df_g_now = pd.read_csv(FILE_PATH["gifts"])
                    if str(ma) not in df_g_now["MaQua"].astype(str).values:
                        pd.concat([df_g_now, pd.DataFrame([{"MaQua": ma, "TenQua": ten}])], ignore_index=True).to_csv(
                            FILE_PATH["gifts"], index=False, encoding='utf-8-sig')

                st.success("Đã lưu!");
                time.sleep(0.5);
                st.rerun()


with tabs[0]: render_form("XUẤT")
with tabs[1]: render_form("NHẬP")

with tabs[2]:
    st.subheader("Báo cáo Xuất - Nhập - Tồn")
    c1, c2 = st.columns(2)
    d1 = c1.date_input("Từ ngày", date(date.today().year, date.today().month, 1))
    d2 = c2.date_input("Đến ngày", date.today())

    if st.button("📊 Xem dữ liệu", use_container_width=True):
        df_t = pd.read_csv(FILE_PATH["trans"])
        if not df_t.empty:
            df_t['Ngay'] = pd.to_datetime(df_t['Ngay']).dt.date
            df_g = pd.read_csv(FILE_PATH["gifts"])
            res = []
            for _, item in df_g.iterrows():
                m, t = item['MaQua'], item['TenQua']
                t_dau = df_t[(df_t['MaQua'] == m) & (df_t['Ngay'] < d1)]['SoLuong'].sum()
                nhap = \
                df_t[(df_t['MaQua'] == m) & (df_t['Loai'] == "NHẬP") & (df_t['Ngay'] >= d1) & (df_t['Ngay'] <= d2)][
                    'SoLuong'].sum()
                xuat = abs(
                    df_t[(df_t['MaQua'] == m) & (df_t['Loai'] == "XUẤT") & (df_t['Ngay'] >= d1) & (df_t['Ngay'] <= d2)][
                        'SoLuong'].sum())
                res.append(
                    {"Mã": m, "Tên": t, "Tồn đầu": t_dau, "Nhập": nhap, "Xuất": xuat, "Tồn cuối": t_dau + nhap - xuat})
            st.session_state['report'] = pd.DataFrame(res)
            st.dataframe(st.session_state['report'], use_container_width=True, hide_index=True)

    if 'report' in st.session_state:
        c_ex, c_pdf = st.columns(2)
        buf = io.BytesIO()
        with pd.ExcelWriter(buf, engine='xlsxwriter') as wr: st.session_state['report'].to_excel(wr, index=False)
        c_ex.download_button("📥 Tải Excel", buf.getvalue(), "Bao_cao_XNT.xlsx", use_container_width=True)
        c_pdf.download_button("📄 Tải PDF", export_pdf(st.session_state['report']), "Bao_cao_XNT.pdf",
                              use_container_width=True)

with tabs[3]:
    st.subheader("Nhật ký chi tiết")
    st.dataframe(pd.read_csv(FILE_PATH["trans"]).iloc[::-1], use_container_width=True, hide_index=True)