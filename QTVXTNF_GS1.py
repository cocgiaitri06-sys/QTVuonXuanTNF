import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import os
from datetime import datetime, date
import io
import time
import re
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib import colors

# --- 1. CẤU HÌNH GOOGLE SHEETS ---
SCOPE = ["https://www.googleapis.com/auth/spreadsheets"]
SHEET_ID = "1Q1JmyrwjySDpoaUcjc1Wr5S40Oju9lHGK_Q9rv58KAg"
ADMIN_PASSWORD = "2605"


@st.cache_resource
def get_gsheet_client():
    creds = Credentials.from_service_account_file("credentials.json", scopes=SCOPE)
    return gspread.authorize(creds)


@st.cache_data(ttl=15)
def load_data_from_gsheet(sheet_name):
    try:
        client = get_gsheet_client()
        sh = client.open_by_key(SHEET_ID)
        worksheet = sh.worksheet(sheet_name)
        data = worksheet.get_all_values()

        cols_map = {
            "danhmuc_qua": ["MaQua", "TenQua"],
            "nhatky_xuatnhap": ["Loai", "Ngay", "MaQua", "TenQua", "SoLuong", "SoChungTu", "NguoiThucHien", "GhiChu"]
        }
        target_cols = cols_map[sheet_name]

        if not data or len(data) < 1:
            return pd.DataFrame(columns=target_cols)

        # Tạo DF và làm sạch tiêu đề/index ngay từ đầu
        df = pd.DataFrame(data[1:], columns=[str(c).strip() for c in data[0]])
        df = df.loc[:, ~df.columns.duplicated()].copy()

        if "MaQua" in df.columns:
            df = df[df["MaQua"].str.strip() != ""]

        available_cols = [c for c in target_cols if c in df.columns]
        return df[available_cols].reset_index(drop=True)
    except Exception as e:
        st.error(f"Lỗi tải dữ liệu: {e}")
        return pd.DataFrame()


def save_data_to_gsheet(df, sheet_name):
    client = get_gsheet_client()
    sh = client.open_by_key(SHEET_ID)
    worksheet = sh.worksheet(sheet_name)
    df_save = df.reset_index(drop=True).astype(str)
    worksheet.clear()
    worksheet.update([df_save.columns.values.tolist()] + df_save.values.tolist())
    st.cache_data.clear()


# --- 2. HÀM TIỆN ÍCH (ĐỊNH NGHĨA TRƯỚC KHI DÙNG) ---
def no_accent_vietnamese(s):
    s = str(s)
    patterns = {'[àáạảãâầấậẩẫăằắặẳẵ]': 'a', '[èéẹẻẽêềếệểễ]': 'e', '[òóọỏõôồốộổỗơờớợởỡ]': 'o', '[ìíịỉĩ]': 'i',
                '[ùúụủũưừứựửữ]': 'u', '[ỳýỵỷỹ]': 'y', '[đ]': 'd'}
    for p, r in patterns.items():
        s = re.sub(p, r, s);
        s = re.sub(p.upper(), r.upper(), s)
    return s


def generate_new_gift_code():
    df_g = load_data_from_gsheet("danhmuc_qua")
    if df_g.empty: return "QT0001"
    # Lấy các mã có định dạng QTxxxx
    codes = [c for c in df_g['MaQua'].astype(str) if c.startswith("QT") and c[2:].isdigit()]
    if not codes: return "QT0001"
    nums = [int(c[2:]) for c in codes]
    return f"QT{(max(nums) + 1):04d}"


def get_current_stock(ma_qua):
    df_t = load_data_from_gsheet("nhatky_xuatnhap")
    if df_t.empty: return 0
    df_t['SoLuong'] = pd.to_numeric(df_t['SoLuong'], errors='coerce').fillna(0)
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
    headers = ["Ma", "Ten Qua", "Ton Dau", "Nhap", "Xuat", "Ton Cuoi"]
    x_pos = [50, 110, 300, 360, 420, 480]
    c.setFont("Helvetica-Bold", 10)
    for i, txt in enumerate(headers): c.drawString(x_pos[i], y, txt)
    y -= 20
    c.setFont("Helvetica", 9)
    for _, row in df.iterrows():
        if y < 50: c.showPage(); y = height - 50
        c.drawString(x_pos[0], y, no_accent_vietnamese(row['Mã']))
        c.drawString(x_pos[1], y, no_accent_vietnamese(row['Tên'])[:30])
        c.drawString(x_pos[2], y, str(row['Tồn đầu']))
        c.drawString(x_pos[3], y, str(row['Nhập']))
        c.drawString(x_pos[4], y, str(row['Xuất']))
        c.drawString(x_pos[5], y, str(row['Tồn cuối']))
        y -= 20
    c.save();
    buf.seek(0)
    return buf.getvalue()


# --- 3. GIAO DIỆN CHÍNH ---
st.set_page_config(page_title="Kho Quà Vườn Xuân TNF", layout="wide")

if 'user_info' not in st.session_state:
    with st.container(border=True):
        st.subheader("🔐 Đăng nhập")
        u_id = st.text_input("Mã nhân viên")
        u_name = st.text_input("Họ và tên")
        if st.button("ĐĂNG NHẬP", use_container_width=True, type="primary"):
            if u_id and u_name:
                st.session_state['user_info'] = {"id": u_id, "name": u_name};
                st.rerun()
    st.stop()

# --- SIDEBAR ---
with st.sidebar:
    st.write(f"👤: **{st.session_state['user_info']['name']}**")
    if st.button("Đăng xuất"): st.session_state.clear(); st.rerun()
    st.divider()
    with st.expander("🛠️ QUẢN TRỊ"):
        pwd = st.text_input("Mật khẩu", type="password")
        if pwd == ADMIN_PASSWORD:
            if st.button("📤 Tải Backup Excel", use_container_width=True):
                dg, dt = load_data_from_gsheet("danhmuc_qua"), load_data_from_gsheet("nhatky_xuatnhap")
                buf = io.BytesIO()
                with pd.ExcelWriter(buf) as wr:
                    dg.to_excel(wr, sheet_name='DM', index=False);
                    dt.to_excel(wr, sheet_name='NK', index=False)
                st.download_button("Download", buf.getvalue(), "backup.xlsx")

# --- TABS ---
tabs = st.tabs(["📤 Xuất kho", "📥 Nhập kho", "📊 Báo cáo XNT", "📜 Nhật ký"])


def render_form(type_f="XUẤT"):
    df_g = load_data_from_gsheet("danhmuc_qua")
    if f"ma_{type_f}" not in st.session_state: st.session_state[f"ma_{type_f}"] = ""
    if f"ten_{type_f}" not in st.session_state: st.session_state[f"ten_{type_f}"] = ""
    if f"show_list_{type_f}" not in st.session_state: st.session_state[f"show_list_{type_f}"] = False

    st.markdown(f"🔍 **Tìm quà ({type_f}):**")
    c1, c2 = st.columns([3, 1])
    with c1:
        search_term = st.text_input("Gõ mã/tên...", key=f"src_{type_f}", label_visibility="collapsed")
    with c2:
        if st.button("📋 List", key=f"l_{type_f}", use_container_width=True):
            st.session_state[f"show_list_{type_f}"] = not st.session_state[f"show_list_{type_f}"]

    # Hiển thị danh sách
    if st.session_state[f"show_list_{type_f}"]:
        with st.expander("📂 Danh mục", expanded=True):
            for idx, row in df_g.iterrows():
                ci, cb = st.columns([4, 1])
                ci.write(f"**{row['MaQua']}** - {row['TenQua']}")
                if cb.button("Chọn", key=f"s_{type_f}_{row['MaQua']}_{idx}"):
                    st.session_state[f"ma_{type_f}"], st.session_state[f"ten_{type_f}"] = row['MaQua'], row['TenQua']
                    st.session_state[f"show_list_{type_f}"] = False;
                    st.rerun()

    # Tìm kiếm & Tạo mới
    # 2. XỬ LÝ KẾT QUẢ TÌM KIẾM
    if search_term and not st.session_state[f"show_list_{type_f}"]:
        f = df_g[df_g['MaQua'].str.contains(search_term, case=False) | df_g['TenQua'].str.contains(search_term,
                                                                                                   case=False)]

        if not f.empty:
            # Nếu tìm thấy quà: Hiện danh sách gợi ý
            for idx, row in f.head(3).iterrows():
                if st.button(f"📍 {row['MaQua']} - {row['TenQua']}", key=f"q_{type_f}_{row['MaQua']}_{idx}",
                             use_container_width=True):
                    st.session_state[f"ma_{type_f}"], st.session_state[f"ten_{type_f}"] = row['MaQua'], row[
                        'TenQua']
                    st.rerun()
        else:
            # --- PHÂN TÁCH LOGIC CHO NHẬP VÀ XUẤT ---
            if type_f == "NHẬP":
                # Ở Tab Nhập: Cho phép tạo mới
                st.info(f"Không tìm thấy '{search_term}'. Bạn có muốn tạo mới không?")
                if st.button(f"➕ Tạo quà mới: '{search_term}'", type="primary", use_container_width=True):
                    st.session_state[f"ma_{type_f}"] = generate_new_gift_code()
                    st.session_state[f"ten_{type_f}"] = search_term
                    st.rerun()
            else:
                # Ở Tab Xuất: Cảnh báo không tìm thấy (Không cho tạo mới)
                st.error(f"❌ Không tìm thấy quà tặng '{search_term}' trong kho. Vui lòng kiểm tra lại mã hoặc tên!")

    curr_ma, curr_ten = st.session_state[f"ma_{type_f}"], st.session_state[f"ten_{type_f}"]
    if curr_ma:
        is_new = curr_ma not in df_g['MaQua'].tolist()
        if not is_new:
            ton = get_current_stock(curr_ma)
            st.info(f"🎁 {curr_ten} - 📊 Tồn: {ton}")

        with st.form(f"form_{type_f}"):
            so_ct = st.text_input("Số chứng từ *")
            sl = st.number_input("Số lượng *", min_value=1, step=1)
            note = st.text_input("Ghi chú")
            if st.form_submit_button(f"XÁC NHẬN {type_f}", use_container_width=True):
                if so_ct:
                    # Lưu nhật ký
                    df_t = load_data_from_gsheet("nhatky_xuatnhap")
                    new_t = pd.DataFrame([{"Loai": type_f, "Ngay": date.today().strftime("%Y-%m-%d"), "MaQua": curr_ma,
                                           "TenQua": curr_ten, "SoLuong": sl if type_f == "NHẬP" else -sl,
                                           "SoChungTu": so_ct, "NguoiThucHien": st.session_state['user_info']['name'],
                                           "GhiChu": note}])
                    save_data_to_gsheet(pd.concat([df_t.reset_index(drop=True), new_t], ignore_index=True),
                                        "nhatky_xuatnhap")
                    # Lưu danh mục nếu mới
                    if is_new:
                        df_g_now = load_data_from_gsheet("danhmuc_qua")
                        save_data_to_gsheet(pd.concat(
                            [df_g_now.reset_index(drop=True), pd.DataFrame([{"MaQua": curr_ma, "TenQua": curr_ten}])],
                            ignore_index=True), "danhmuc_qua")
                    st.success("✅ Thành công!");
                    time.sleep(1)
                    st.session_state[f"ma_{type_f}"] = "";
                    st.rerun()


with tabs[0]: render_form("XUẤT")
with tabs[1]: render_form("NHẬP")

with tabs[2]:
    st.subheader("📊 Báo cáo XNT")
    c1, c2 = st.columns(2)
    d1 = c1.date_input("Từ ngày", date(date.today().year, date.today().month, 1), key="d1")
    d2 = c2.date_input("Đến ngày", date.today(), key="d2")
    if st.button("Chạy báo cáo", type="primary"):
        df_t = load_data_from_gsheet("nhatky_xuatnhap")
        df_g = load_data_from_gsheet("danhmuc_qua")
        if not df_t.empty:
            df_t['Ngay'] = pd.to_datetime(df_t['Ngay']).dt.date
            df_t['SoLuong'] = pd.to_numeric(df_t['SoLuong'])
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
            st.session_state['report_df'] = pd.DataFrame(res)

    if 'report_df' in st.session_state:
        st.dataframe(st.session_state['report_df'], use_container_width=True, hide_index=True)
        cx, cp = st.columns(2)
        buf = io.BytesIO()
        with pd.ExcelWriter(buf) as wr: st.session_state['report_df'].to_excel(wr, index=False)
        cx.download_button("Excel", buf.getvalue(), "report.xlsx", use_container_width=True)
        cp.download_button("PDF", export_pdf_reportlab(st.session_state['report_df'], f"{d1}-{d2}"), "report.pdf",
                           use_container_width=True)

with tabs[3]:
    st.dataframe(load_data_from_gsheet("nhatky_xuatnhap").iloc[::-1], use_container_width=True)