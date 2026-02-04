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

# --- 1. CẤU HÌNH FILE ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FILE_PATH = {
    "gifts": os.path.join(BASE_DIR, "danhmuc_qua.csv"),
    "trans": os.path.join(BASE_DIR, "nhatky_xuatnhap.csv")
}


def init_csv():
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


def generate_new_gift_code():
    df_g = pd.read_csv(FILE_PATH["gifts"])
    if df_g.empty: return "QT0001"
    codes = [c for c in df_g['MaQua'].astype(str).tolist() if c.startswith("QT") and len(c) == 6]
    if not codes: return "QT0001"
    nums = [int(c[2:]) for c in codes if c[2:].isdigit()]
    return f"QT{(max(nums) + 1):04d}" if nums else "QT0001"


def get_current_stock(ma_qua):
    df_t = pd.read_csv(FILE_PATH["trans"])
    if df_t.empty: return 0
    return df_t[df_t["MaQua"].astype(str) == str(ma_qua)]["SoLuong"].sum()


# --- HÀM XUẤT PDF MỚI (REPORTLAB) ---
def export_pdf_reportlab(df, date_range):
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    width, height = A4

    # Tiêu đề
    c.setFont("Helvetica-Bold", 16)
    c.drawCentredString(width / 2, height - 50, "BAO CAO XUAT NHAP TON")
    c.setFont("Helvetica", 10)
    c.drawCentredString(width / 2, height - 70,
                        f"Thoi gian: {date_range} | Ngay xuat: {datetime.now().strftime('%d/%m/%Y')}")

    # Vẽ Header Bảng
    y = height - 110
    c.setFont("Helvetica-Bold", 10)
    c.setFillColor(colors.grey)
    c.rect(40, y - 5, 520, 20, fill=1)
    c.setFillColor(colors.whitesmoke)

    headers = ["Ma", "Ten Qua", "Ton Dau", "Nhap", "Xuat", "Ton Cuoi"]
    x_pos = [50, 110, 300, 360, 420, 480]
    for i, txt in enumerate(headers):
        c.drawString(x_pos[i], y, txt)

    # Vẽ Dữ liệu
    y -= 25
    c.setFillColor(colors.black)
    c.setFont("Helvetica", 9)

    for _, row in df.iterrows():
        if y < 50:  # Ngắt trang nếu hết chỗ
            c.showPage()
            y = height - 50
            c.setFont("Helvetica", 9)

        c.drawString(x_pos[0], y, no_accent_vietnamese(row['Mã']))
        c.drawString(x_pos[1], y, no_accent_vietnamese(row['Tên'])[:35])
        c.drawRightString(x_pos[2] + 30, y, str(row['Tồn đầu']))
        c.drawRightString(x_pos[3] + 25, y, str(row['Nhập']))
        c.drawRightString(x_pos[4] + 25, y, str(row['Xuất']))
        c.drawRightString(x_pos[5] + 30, y, str(row['Tồn cuối']))

        c.setStrokeColor(colors.lightgrey)
        c.line(40, y - 5, 560, y - 5)
        y -= 20

    c.save()
    buf.seek(0)
    return buf.getvalue()


# --- 2. GIAO DIỆN ---
st.set_page_config(page_title="Kho TNF - ReportLab Edition", layout="wide")
init_csv()

if 'user_info' not in st.session_state:
    with st.container(border=True):
        st.subheader("🔐 Đăng nhập")
        u_id = st.text_input("Mã NV")
        u_name = st.text_input("Họ Tên")
        if st.button("BẮT ĐẦU", use_container_width=True, type="primary"):
            if u_id and u_name:
                st.session_state['user_info'] = {"id": u_id, "name": u_name}
                st.rerun()
    st.stop()

tabs = st.tabs(["📤 Xuất kho", "📥 Nhập kho", "📊 Báo cáo XNT", "📜 Nhật ký"])


def render_form(type_f="XUẤT"):
    df_g = pd.read_csv(FILE_PATH["gifts"])

    # Khởi tạo state
    for key in [f"ma_{type_f}", f"ten_{type_f}", f"new_{type_f}"]:
        if key not in st.session_state:
            st.session_state[key] = "" if "new" not in key else False

    st.markdown(f"🔍 **Tìm kiếm nhanh ({type_f}):**")

    # Khi người dùng gõ, Streamlit sẽ tự động rerun và cập nhật src ngay lập tức
    src = st.text_input(f"Gõ mã hoặc tên quà...", key=f"src_{type_f}")

    # Logic lọc dữ liệu tức thì
    disable_f = False

    if src:
        # Lọc dữ liệu ngay khi 'src' có giá trị
        filtered = df_g[df_g['MaQua'].astype(str).str.contains(src, case=False) |
                        df_g['TenQua'].str.contains(src, case=False)]

        if not filtered.empty:
            # Hiển thị danh sách lựa chọn ngay bên dưới ô nhập
            sel = st.radio(
                f"Kết quả phù hợp cho '{src}':",
                filtered.apply(lambda x: f"{x['MaQua']} - {x['TenQua']}", axis=1),
                key=f"rad_{type_f}"
            )
            if sel:
                m, t = sel.split(" - ")
                st.session_state[f"ma_{type_f}"], st.session_state[f"ten_{type_f}"] = m, t
                st.session_state[f"new_{type_f}"] = False
        else:
            if type_f == "XUẤT":
                st.error(f"❌ Không tìm thấy quà nào khớp với: '{src}'")
                disable_f = True
            else:
                st.info(f"💡 Không có '{src}' trong danh mục. Bạn có muốn tạo mới?")
                if st.button("➕ Tạo quà mới", use_container_width=True):
                    st.session_state[f"ma_{type_f}"] = generate_new_gift_code()
                    st.session_state[f"ten_{type_f}"] = src
                    st.session_state[f"new_{type_f}"] = True
    else:
        # Nếu để trống ô tìm kiếm, mặc định khóa form Xuất
        if type_f == "XUẤT": disable_f = True

    # --- PHẦN FORM NHẬP LIỆU BÊN DƯỚI (Giữ nguyên logic cũ) ---

    with st.container(border=True):
        so_ct = st.text_input("Số chứng từ *", key=f"ct_{type_f}", disabled=disable_f)
        c1, c2 = st.columns(2)
        with c1:
            st.text_input("Mã", key=f"ma_{type_f}", disabled=True)
        with c2:
            st.text_input("Tên", key=f"ten_{type_f}",
                          disabled=not (type_f == "NHẬP" and st.session_state[f"new_{type_f}"]) or disable_f)
        sl = st.number_input("Số lượng *", min_value=1, step=1, key=f"sl_{type_f}", disabled=disable_f)
        if st.session_state[f"ma_{type_f}"] and not disable_f:
            st.info(f"📊 Tồn kho: {get_current_stock(st.session_state[f'ma_{type_f}'])}")
        note = st.text_input("Ghi chú", key=f"n_{type_f}", disabled=disable_f)

        if st.button(f"LƯU PHIẾU {type_f}", type="primary", use_container_width=True, disabled=disable_f):
            ma, ten = st.session_state[f"ma_{type_f}"], st.session_state[f"ten_{type_f}"]
            if ma and ten and so_ct:
                df_t = pd.read_csv(FILE_PATH["trans"])
                new_row = {"Loai": type_f, "Ngay": date.today().strftime("%Y-%m-%d"),
                           "Gio": datetime.now().strftime("%H:%M:%S"),
                           "SoChungTu": so_ct, "MaQua": ma, "TenQua": ten, "SoLuong": sl if type_f == "NHẬP" else -sl,
                           "NguoiThucHien": f"{st.session_state['user_info']['id']} - {st.session_state['user_info']['name']}",
                           "GhiChu": note}
                pd.concat([df_t, pd.DataFrame([new_row])], ignore_index=True).to_csv(FILE_PATH["trans"], index=False,
                                                                                     encoding='utf-8-sig')
                if type_f == "NHẬP" and st.session_state[f"new_{type_f}"]:
                    df_g_now = pd.read_csv(FILE_PATH["gifts"])
                    pd.concat([df_g_now, pd.DataFrame([{"MaQua": ma, "TenQua": ten}])], ignore_index=True).to_csv(
                        FILE_PATH["gifts"], index=False, encoding='utf-8-sig')
                st.success("Đã lưu!");
                time.sleep(0.5)
                for k in [f"src_{type_f}", f"ct_{type_f}", f"ma_{type_f}", f"ten_{type_f}", f"sl_{type_f}",
                          f"n_{type_f}", f"new_{type_f}", f"rad_{type_f}"]:
                    if k in st.session_state: del st.session_state[k]
                st.rerun()

with tabs[0]: render_form("XUẤT")
with tabs[1]: render_form("NHẬP")

# --- TAB BÁO CÁO (FIXED) ---
with tabs[2]:
    st.subheader("Báo cáo XNT")
    c1, c2 = st.columns(2)
    d1 = c1.date_input("Từ ngày", date(date.today().year, date.today().month, 1))
    d2 = c2.date_input("Đến ngày", date.today())

    if st.button("📊 Truy xuất dữ liệu", use_container_width=True):
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
            st.session_state['report_df'] = pd.DataFrame(r_list)

    if 'report_df' in st.session_state:
        st.dataframe(st.session_state['report_df'], use_container_width=True, hide_index=True)
        ce, cp = st.columns(2)
        # Excel
        buf_ex = io.BytesIO()
        with pd.ExcelWriter(buf_ex, engine='xlsxwriter') as wr: st.session_state['report_df'].to_excel(wr, index=False)
        ce.download_button("📥 Tải Excel", buf_ex.getvalue(), "Bao_cao.xlsx", use_container_width=True)
        # PDF (ReportLab)
        pdf_bytes = export_pdf_reportlab(st.session_state['report_df'], f"{d1} den {d2}")
        cp.download_button("📄 Tải PDF", pdf_bytes, "Bao_cao.pdf", mime="application/pdf", use_container_width=True)

with tabs[3]:
    st.subheader("Nhật ký")
    st.dataframe(pd.read_csv(FILE_PATH["trans"]).iloc[::-1], use_container_width=True, hide_index=True)