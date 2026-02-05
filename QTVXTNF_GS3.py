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

# --- 1. CẤU HÌNH HỆ THỐNG ---
SHEET_ID = "1Q1JmyrwjySDpoaUcjc1Wr5S40Oju9lHGK_Q9rv58KAg"
ADMIN_PASSWORD = "2605"
SCOPE = ["https://www.googleapis.com/auth/spreadsheets"]

st.set_page_config(page_title="Kho Quà Vườn Xuân TNF", layout="wide")

# --- 2. XỬ LÝ CREDENTIALS ---
if "gcp_service_account" in st.secrets:
    CREDS_DATA = dict(st.secrets["gcp_service_account"])
else:
    import json

    try:
        with open("credentials.json") as f:
            CREDS_DATA = json.load(f)
    except:
        st.error("Thiếu cấu hình Secrets hoặc file credentials.json!")
        st.stop()


# --- 3. QUẢN LÝ KẾT NỐI ---
@st.cache_resource
def get_gsheet_client(creds_info):
    creds = Credentials.from_service_account_info(creds_info, scopes=SCOPE)
    return gspread.authorize(creds)


@st.cache_data(ttl=15)
def load_data_from_gsheet(sheet_name, creds_info):
    try:
        client = get_gsheet_client(creds_info)
        sh = client.open_by_key(SHEET_ID)
        worksheet = sh.worksheet(sheet_name)
        data = worksheet.get_all_values()
        if not data or len(data) < 1: return pd.DataFrame()
        df = pd.DataFrame(data[1:], columns=[str(c).strip() for c in data[0]])
        df = df.loc[:, ~df.columns.duplicated()].copy()
        if "MaQua" in df.columns: df = df[df["MaQua"].str.strip() != ""]
        return df.reset_index(drop=True)
    except:
        return pd.DataFrame()


def save_data_to_gsheet(df, sheet_name, creds_info):
    client = get_gsheet_client(creds_info)
    sh = client.open_by_key(SHEET_ID)
    worksheet = sh.worksheet(sheet_name)
    df_save = df.reset_index(drop=True).astype(str)
    worksheet.clear()
    worksheet.update([df_save.columns.values.tolist()] + df_save.values.tolist())
    st.cache_data.clear()


# --- 4. QUẢN LÝ ĐĂNG NHẬP ---
def get_cookie_manager():
    return stx.CookieManager()


cookie_manager = get_cookie_manager()


def check_login():
    if 'user_info' in st.session_state: return True
    saved_user = cookie_manager.get(cookie="saved_user_tnf")
    if saved_user and isinstance(saved_user, dict):
        st.session_state['user_info'] = saved_user
        return True
    return False


# --- 5. HÀM TIỆN ÍCH ---
def no_accent_vietnamese(s):
    s = str(s)
    patterns = {'[àáạảãâầấậẩẫăằắặẳẵ]': 'a', '[èéẹẻẽêềếệểễ]': 'e', '[òóọỏõôồốộổỗơờớợởỡ]': 'o', '[ìíịỉĩ]': 'i',
                '[ùúụủũưừứựửữ]': 'u', '[ỳýỵỷỹ]': 'y', '[đ]': 'd'}
    for p, r in patterns.items():
        s = re.sub(p, r, s);
        s = re.sub(p.upper(), r.upper(), s)
    return s


def generate_new_gift_code():
    df_g = load_data_from_gsheet("danhmuc_qua", CREDS_DATA)
    if df_g.empty: return "QT0001"
    codes = [c for c in df_g['MaQua'].astype(str) if c.startswith("QT") and c[2:].isdigit()]
    nums = [int(c[2:]) for c in codes] if codes else [0]
    return f"QT{(max(nums) + 1):04d}"


def get_current_stock(ma_qua):
    df_t = load_data_from_gsheet("nhatky_xuatnhap", CREDS_DATA)
    if df_t.empty: return 0
    df_t['SoLuong'] = pd.to_numeric(df_t['SoLuong'], errors='coerce').fillna(0)
    return df_t[df_t["MaQua"].astype(str) == str(ma_qua)]["SoLuong"].sum()


def export_pdf_report(df, d1, d2):
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    w, h = A4
    c.setFont("Helvetica-Bold", 16);
    c.drawCentredString(w / 2, h - 50, "BAO CAO XUAT NHAP TON")
    c.setFont("Helvetica", 10);
    c.drawCentredString(w / 2, h - 70, f"Tu {d1} den {d2}")
    y = h - 110;
    headers = ["Ma", "Ten Qua", "Ton Dau", "Nhap", "Xuat", "Ton Cuoi"]
    x_pos = [40, 100, 300, 360, 420, 480]
    for i, txt in enumerate(headers): c.drawString(x_pos[i], y, txt)
    y -= 20;
    c.setFont("Helvetica", 9)
    for _, r in df.iterrows():
        if y < 50: c.showPage(); y = h - 50
        c.drawString(x_pos[0], y, str(r['Mã']))
        c.drawString(x_pos[1], y, no_accent_vietnamese(r['Tên'])[:35])
        c.drawString(x_pos[2], y, str(r['Tồn đầu']))
        c.drawString(x_pos[3], y, str(r['Nhập']))
        c.drawString(x_pos[4], y, str(r['Xuất']))
        c.drawString(x_pos[5], y, str(r['Tồn cuối']))
        y -= 18
    c.save();
    return buf.getvalue()


# --- 6. GIAO DIỆN ĐĂNG NHẬP ---
if not check_login():
    st.markdown("<h2 style='text-align: center; color: #e67e22;'>🌸 Kho Quà Vườn Xuân TNF</h2>", unsafe_allow_html=True)
    with st.container(border=True):
        u_id = st.text_input("Mã nhân viên", key="l_id")
        u_name = st.text_input("Họ và tên", key="l_name")
        if st.button("ĐĂNG NHẬP", use_container_width=True, type="primary"):
            if u_id and u_name:
                u_data = {"id": str(u_id).strip(), "name": str(u_name).strip()}
                st.session_state['user_info'] = u_data
                cookie_manager.set("saved_user_tnf", u_data, expires_at=datetime.now() + timedelta(days=30))
                st.rerun()
    st.stop()

# --- 7. GIAO DIỆN CHÍNH ---
with st.sidebar:
    st.subheader("🌸 Vườn Xuân TNF")
    st.info(f"👤 **{st.session_state['user_info']['name']}**\n\n🆔 Mã NV: **{st.session_state['user_info']['id']}**")
    if st.button("Đăng xuất", use_container_width=True):
        cookie_manager.delete("saved_user_tnf");
        st.session_state.clear();
        st.rerun()
    st.divider()

    # --- PHẦN QUẢN TRỊ ---
    with st.expander("🛠️ QUẢN TRỊ"):
        pwd = st.text_input("Mật khẩu Admin", type="password")
        if pwd == ADMIN_PASSWORD:
            dg = load_data_from_gsheet("danhmuc_qua", CREDS_DATA)
            dt = load_data_from_gsheet("nhatky_xuatnhap", CREDS_DATA)

            # 1. Sao lưu
            st.write("📂 **Dữ liệu hệ thống**")
            buf = io.BytesIO()
            with pd.ExcelWriter(buf) as wr:
                dg.to_excel(wr, sheet_name='DM', index=False);
                dt.to_excel(wr, sheet_name='NK', index=False)
            st.download_button("📤 Tải Backup Excel", buf.getvalue(), "backup_vuonxuan.xlsx", use_container_width=True)

            st.divider()

            # 2. Reset Database
            st.warning("⚠️ **Vùng nguy hiểm**")
            confirm_reset = st.checkbox("Tôi xác nhận muốn xóa TOÀN BỘ dữ liệu")
            if confirm_reset:
                if st.button("🔥 RESET DATABASE", type="primary", use_container_width=True):
                    # Xóa danh mục quà (giữ lại header)
                    empty_dg = pd.DataFrame(columns=["MaQua", "TenQua"])
                    # Xóa nhật ký (giữ lại header)
                    empty_dt = pd.DataFrame(
                        columns=["Loai", "Ngay", "MaQua", "TenQua", "SoLuong", "SoChungTu", "NguoiThucHien", "GhiChu"])

                    save_data_to_gsheet(empty_dg, "danhmuc_qua", CREDS_DATA)
                    save_data_to_gsheet(empty_dt, "nhatky_xuatnhap", CREDS_DATA)

                    st.success("✅ Đã reset toàn bộ dữ liệu!")
                    time.sleep(2)
                    st.rerun()

tabs = st.tabs(["📤 Xuất kho", "📥 Nhập kho", "📊 Báo cáo XNT", "📜 Nhật ký"])


# --- RENDER CÁC TAB (GIỮ NGUYÊN NHƯ BẢN TRƯỚC) ---
def render_form(type_f="XUẤT"):
    df_g = load_data_from_gsheet("danhmuc_qua", CREDS_DATA)
    if f"ma_{type_f}" not in st.session_state: st.session_state[f"ma_{type_f}"] = ""
    if f"ten_{type_f}" not in st.session_state: st.session_state[f"ten_{type_f}"] = ""
    if f"show_list_{type_f}" not in st.session_state: st.session_state[f"show_list_{type_f}"] = False

    st.markdown(f"🔍 **Tìm quà ({type_f}):**")
    c1, c2 = st.columns([3, 1])
    with c1:
        search_term = st.text_input("Gõ mã hoặc tên...", key=f"src_{type_f}", label_visibility="collapsed")
    with c2:
        if st.button("📋 List", key=f"btn_l_{type_f}", use_container_width=True):
            st.session_state[f"show_list_{type_f}"] = not st.session_state[f"show_list_{type_f}"]

    if st.session_state[f"show_list_{type_f}"]:
        with st.expander("📂 Danh mục quà tặng", expanded=True):
            if df_g.empty:
                st.write("Danh mục hiện tại đang trống.")
            else:
                for i, r in df_g.iterrows():
                    ci, cb = st.columns([4, 1])
                    ci.write(f"**{r['MaQua']}** - {r['TenQua']}")
                    if cb.button("Chọn", key=f"sel_{type_f}_{i}"):
                        st.session_state[f"ma_{type_f}"], st.session_state[f"ten_{type_f}"] = r['MaQua'], r['TenQua']
                        st.session_state[f"show_list_{type_f}"] = False;
                        st.rerun()

    if search_term and not st.session_state[f"show_list_{type_f}"]:
        f = df_g[
            df_g['MaQua'].str.contains(search_term, case=False) | df_g['TenQua'].str.contains(search_term, case=False)]
        if not f.empty:
            for i, r in f.head(3).iterrows():
                if st.button(f"📍 {r['MaQua']} - {r['TenQua']}", key=f"res_{type_f}_{i}", use_container_width=True):
                    st.session_state[f"ma_{type_f}"], st.session_state[f"ten_{type_f}"] = r['MaQua'], r['TenQua'];
                    st.rerun()
        elif type_f == "NHẬP":
            if st.button(f"➕ Tạo quà mới: '{search_term}'", type="primary", use_container_width=True):
                st.session_state[f"ma_{type_f}"], st.session_state[
                    f"ten_{type_f}"] = generate_new_gift_code(), search_term;
                st.rerun()
        else:
            st.error("❌ Không tìm thấy quà!")

    m, t = st.session_state[f"ma_{type_f}"], st.session_state[f"ten_{type_f}"]
    if m:
        ton = get_current_stock(m) if not df_g.empty and m in df_g['MaQua'].values else 0
        st.success(f"Đang chọn: **{t}** | Tồn: **{ton}**")
        with st.form(f"f_{type_f}", clear_on_submit=True):
            so_ct = st.text_input("Số chứng từ *")
            sl = st.number_input("Số lượng *", min_value=1, step=1)
            note = st.text_input("Ghi chú")
            if st.form_submit_button(f"XÁC NHẬN {type_f}", use_container_width=True):
                if so_ct:
                    user_info = f"{st.session_state['user_info']['name']} ({st.session_state['user_info']['id']})"
                    df_t = load_data_from_gsheet("nhatky_xuatnhap", CREDS_DATA)
                    new_r = {"Loai": type_f, "Ngay": date.today().strftime("%Y-%m-%d"), "MaQua": m, "TenQua": t,
                             "SoLuong": sl if type_f == "NHẬP" else -sl, "SoChungTu": so_ct, "NguoiThucHien": user_info,
                             "GhiChu": note}
                    save_data_to_gsheet(pd.concat([df_t, pd.DataFrame([new_r])], ignore_index=True), "nhatky_xuatnhap",
                                        CREDS_DATA)
                    if df_g.empty or m not in df_g['MaQua'].values:
                        dg_now = load_data_from_gsheet("danhmuc_qua", CREDS_DATA)
                        save_data_to_gsheet(
                            pd.concat([dg_now, pd.DataFrame([{"MaQua": m, "TenQua": t}])], ignore_index=True),
                            "danhmuc_qua", CREDS_DATA)
                    st.success("✅ Giao dịch thành công!");
                    time.sleep(1);
                    st.session_state[f"ma_{type_f}"] = "";
                    st.rerun()


with tabs[0]: render_form("XUẤT")
with tabs[1]: render_form("NHẬP")
with tabs[2]:
    st.subheader("📊 Báo cáo Xuất - Nhập - Tồn")
    c1, c2 = st.columns(2)
    d1, d2 = c1.date_input("Từ ngày", date(date.today().year, date.today().month, 1), key="d1"), c2.date_input(
        "Đến ngày", date.today(), key="d2")
    if st.button("Chạy báo cáo", type="primary", use_container_width=True):
        df_t, df_g = load_data_from_gsheet("nhatky_xuatnhap", CREDS_DATA), load_data_from_gsheet("danhmuc_qua",
                                                                                                 CREDS_DATA)
        if not df_t.empty and not df_g.empty:
            df_t['Ngay'] = pd.to_datetime(df_t['Ngay']).dt.date
            df_t['SoLuong'] = pd.to_numeric(df_t['SoLuong'], errors='coerce').fillna(0)
            res = []
            for _, r in df_g.iterrows():
                m, q = r['MaQua'], r['TenQua']
                t_dau = df_t[(df_t['MaQua'] == m) & (df_t['Ngay'] < d1)]['SoLuong'].sum()
                nhap = \
                df_t[(df_t['MaQua'] == m) & (df_t['Loai'] == "NHẬP") & (df_t['Ngay'] >= d1) & (df_t['Ngay'] <= d2)][
                    'SoLuong'].sum()
                xuat = abs(
                    df_t[(df_t['MaQua'] == m) & (df_t['Loai'] == "XUẤT") & (df_t['Ngay'] >= d1) & (df_t['Ngay'] <= d2)][
                        'SoLuong'].sum())
                res.append(
                    {"Mã": m, "Tên": q, "Tồn đầu": t_dau, "Nhập": nhap, "Xuất": xuat, "Tồn cuối": t_dau + nhap - xuat})
            st.session_state['rep_df'] = pd.DataFrame(res)

    if 'rep_df' in st.session_state:
        df_rep = st.session_state['rep_df']
        st.dataframe(df_rep, use_container_width=True, hide_index=True)
        cx, cp = st.columns(2)
        buf_ex = io.BytesIO()
        with pd.ExcelWriter(buf_ex) as wr: df_rep.to_excel(wr, index=False)
        cx.download_button("📥 Xuất Excel", buf_ex.getvalue(), "bao_cao_XNT.xlsx", use_container_width=True)
        cp.download_button("📥 Xuất PDF", export_pdf_report(df_rep, d1, d2), "bao_cao_XNT.pdf", use_container_width=True)

with tabs[3]:
    st.subheader("📜 Nhật ký giao dịch")
    df_nk = load_data_from_gsheet("nhatky_xuatnhap", CREDS_DATA)
    if not df_nk.empty: st.dataframe(df_nk.iloc[::-1], use_container_width=True, hide_index=True)