import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import extra_streamlit_components as stx
from datetime import datetime, date, timedelta
import io
import time
import re
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib import colors

# --- 1. CẤU HÌNH HỆ THỐNG ---
SHEET_ID = "1Q1JmyrwjySDpoaUcjc1Wr5S40Oju9lHGK_Q9rv58KAg"
ADMIN_PASSWORD = "2605"
SCOPE = ["https://www.googleapis.com/auth/spreadsheets"]

st.set_page_config(page_title="Kho Quà Vườn Xuân TNF", layout="wide")


# --- 2. QUẢN LÝ ĐĂNG NHẬP (COOKIE) ---
@st.cache_resource
def get_cookie_manager():
    return stx.CookieManager()


cookie_manager = get_cookie_manager()


def check_login():
    if 'user_info' in st.session_state:
        return True
    # Thử lấy từ Cookie trình duyệt
    saved_user = cookie_manager.get(cookie="saved_user_tnf")
    if saved_user and isinstance(saved_user, dict):
        st.session_state['user_info'] = saved_user
        return True
    return False


# --- 3. KẾT NỐI GOOGLE SHEETS ---
@st.cache_resource
def get_gsheet_client():
    # Ưu tiên đọc từ Secrets (Cloud), nếu không thấy thì đọc file nội bộ (Local)
    try:
        if "gcp_service_account" in st.secrets:
            creds_info = st.secrets["gcp_service_account"]
            creds = Credentials.from_service_account_info(creds_info, scopes=SCOPE)
        else:
            creds = Credentials.from_service_account_file("credentials.json", scopes=SCOPE)
        return gspread.authorize(creds)
    except Exception as e:
        st.error(f"Lỗi kết nối Google: {e}")
        return None


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

        df = pd.DataFrame(data[1:], columns=[str(c).strip() for c in data[0]])
        df = df.loc[:, ~df.columns.duplicated()].copy()

        if "MaQua" in df.columns:
            df = df[df["MaQua"].str.strip() != ""]

        available_cols = [c for c in target_cols if c in df.columns]
        return df[available_cols].reset_index(drop=True)
    except Exception:
        return pd.DataFrame()


def save_data_to_gsheet(df, sheet_name):
    client = get_gsheet_client()
    sh = client.open_by_key(SHEET_ID)
    worksheet = sh.worksheet(sheet_name)
    df_save = df.reset_index(drop=True).astype(str)
    worksheet.clear()
    worksheet.update([df_save.columns.values.tolist()] + df_save.values.tolist())
    st.cache_data.clear()


# --- 4. HÀM TIỆN ÍCH ---
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
    codes = [c for c in df_g['MaQua'].astype(str) if c.startswith("QT") and c[2:].isdigit()]
    nums = [int(c[2:]) for c in codes] if codes else [0]
    return f"QT{(max(nums) + 1):04d}"


def get_current_stock(ma_qua):
    df_t = load_data_from_gsheet("nhatky_xuatnhap")
    if df_t.empty: return 0
    df_t['SoLuong'] = pd.to_numeric(df_t['SoLuong'], errors='coerce').fillna(0)
    return df_t[df_t["MaQua"].astype(str) == str(ma_qua)]["SoLuong"].sum()


# --- 5. GIAO DIỆN ĐĂNG NHẬP ---
if not check_login():
    st.markdown("<h2 style='text-align: center;'>🌸 Kho Quà Vườn Xuân TNF</h2>", unsafe_allow_html=True)
    with st.container(border=True):
        u_id = st.text_input("Mã nhân viên")
        u_name = st.text_input("Họ và tên")
        if st.button("ĐĂNG NHẬP", use_container_width=True, type="primary"):
            if u_id and u_name:
                user_data = {"id": u_id, "name": u_name}
                st.session_state['user_info'] = user_data
                cookie_manager.set("saved_user_tnf", user_data, expires_at=datetime.now() + timedelta(days=30))
                st.rerun()
    st.stop()

# --- 6. GIAO DIỆN CHÍNH ---
with st.sidebar:
    st.subheader("🌸 Vườn Xuân TNF")
    st.write(f"Chào: **{st.session_state['user_info']['name']}**")
    if st.button("Đăng xuất"):
        cookie_manager.delete("saved_user_tnf")
        st.session_state.clear()
        st.rerun()
    st.divider()
    with st.expander("🛠️ QUẢN TRỊ"):
        pwd = st.text_input("Mật khẩu", type="password")
        if pwd == ADMIN_PASSWORD:
            dg, dt = load_data_from_gsheet("danhmuc_qua"), load_data_from_gsheet("nhatky_xuatnhap")
            buf = io.BytesIO()
            with pd.ExcelWriter(buf) as wr:
                dg.to_excel(wr, sheet_name='DM', index=False);
                dt.to_excel(wr, sheet_name='NK', index=False)
            st.download_button("📤 Tải Backup Excel", buf.getvalue(), "backup_vuonxuan.xlsx")

tabs = st.tabs(["📤 Xuất kho", "📥 Nhập kho", "📊 Báo cáo XNT", "📜 Nhật ký"])


def render_form(type_f="XUẤT"):
    df_g = load_data_from_gsheet("danhmuc_qua")
    if f"ma_{type_f}" not in st.session_state: st.session_state[f"ma_{type_f}"] = ""
    if f"ten_{type_f}" not in st.session_state: st.session_state[f"ten_{type_f}"] = ""

    st.markdown(f"🔍 **Tìm quà ({type_f}):**")
    search_term = st.text_input("Gõ mã hoặc tên...", key=f"src_{type_f}", label_visibility="collapsed")

    if search_term:
        f = df_g[
            df_g['MaQua'].str.contains(search_term, case=False) | df_g['TenQua'].str.contains(search_term, case=False)]
        if not f.empty:
            for idx, row in f.head(3).iterrows():
                if st.button(f"📍 {row['MaQua']} - {row['TenQua']}", key=f"q_{type_f}_{row['MaQua']}_{idx}",
                             use_container_width=True):
                    st.session_state[f"ma_{type_f}"], st.session_state[f"ten_{type_f}"] = row['MaQua'], row['TenQua'];
                    st.rerun()
        elif type_f == "NHẬP":
            if st.button(f"➕ Tạo quà mới: '{search_term}'", type="primary", use_container_width=True):
                st.session_state[f"ma_{type_f}"], st.session_state[
                    f"ten_{type_f}"] = generate_new_gift_code(), search_term;
                st.rerun()
        else:
            st.error("❌ Không tìm thấy quà tặng này trong kho!")

    curr_ma, curr_ten = st.session_state[f"ma_{type_f}"], st.session_state[f"ten_{type_f}"]
    if curr_ma:
        is_new = curr_ma not in df_g['MaQua'].tolist()
        ton = get_current_stock(curr_ma) if not is_new else 0
        st.info(f"🎁 {curr_ten} ({curr_ma}) | 📊 Tồn: {ton}")

        with st.form(f"form_{type_f}"):
            so_ct = st.text_input("Số chứng từ *")
            sl = st.number_input("Số lượng *", min_value=1, step=1)
            note = st.text_input("Ghi chú")
            if st.form_submit_button(f"XÁC NHẬN {type_f}", use_container_width=True):
                if so_ct:
                    df_t = load_data_from_gsheet("nhatky_xuatnhap")
                    new_t = pd.DataFrame([{"Loai": type_f, "Ngay": date.today().strftime("%Y-%m-%d"), "MaQua": curr_ma,
                                           "TenQua": curr_ten, "SoLuong": sl if type_f == "NHẬP" else -sl,
                                           "SoChungTu": so_ct, "NguoiThucHien": st.session_state['user_info']['name'],
                                           "GhiChu": note}])
                    save_data_to_gsheet(pd.concat([df_t.reset_index(drop=True), new_t], ignore_index=True),
                                        "nhatky_xuatnhap")
                    if is_new:
                        df_g_now = load_data_from_gsheet("danhmuc_qua")
                        save_data_to_gsheet(pd.concat(
                            [df_g_now.reset_index(drop=True), pd.DataFrame([{"MaQua": curr_ma, "TenQua": curr_ten}])],
                            ignore_index=True), "danhmuc_qua")
                    st.success("✅ Đã lưu thành công!");
                    time.sleep(1)
                    st.session_state[f"ma_{type_f}"] = "";
                    st.rerun()


with tabs[0]: render_form("XUẤT")
with tabs[1]: render_form("NHẬP")

with tabs[2]:
    st.subheader("📊 Báo cáo Xuất - Nhập - Tồn")
    c1, c2 = st.columns(2)
    d1 = c1.date_input("Từ ngày", date(date.today().year, date.today().month, 1), key="d1")
    d2 = c2.date_input("Đến ngày", date.today(), key="d2")
    if st.button("Chạy báo cáo", type="primary", use_container_width=True):
        df_t, df_g = load_data_from_gsheet("nhatky_xuatnhap"), load_data_from_gsheet("danhmuc_qua")
        if not df_t.empty:
            df_t['Ngay'] = pd.to_datetime(df_t['Ngay']).dt.date
            df_t['SoLuong'] = pd.to_numeric(df_t['SoLuong'], errors='coerce').fillna(0)
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
        buf = io.BytesIO()
        with pd.ExcelWriter(buf) as wr: st.session_state['report_df'].to_excel(wr, index=False)
        st.download_button("📥 Tải file Báo cáo (Excel)", buf.getvalue(), "bao_cao_XNT.xlsx")

with tabs[3]:
    st.subheader("📜 Nhật ký xuất nhập")
    st.dataframe(load_data_from_gsheet("nhatky_xuatnhap").iloc[::-1], use_container_width=True, hide_index=True)