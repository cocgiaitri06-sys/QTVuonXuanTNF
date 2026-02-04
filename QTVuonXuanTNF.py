import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime, date
import io
import time
import re
from fpdf import FPDF

# --- 1. CẤU HÌNH KẾT NỐI ---
# Thay link Sheets của bạn vào đây
URL_SHEET = "https://docs.google.com/spreadsheets/d/1Q1JmyrwjySDpoaUcjc1Wr5S40Oju9lHGK_Q9rv58KAg/edit?usp=sharing"


def load_data(worksheet_name):
    try:
        # Không cần truyền URL vào đây, nó sẽ tự đọc trong Secrets
        conn = st.connection("gsheets", type=GSheetsConnection)
        df = conn.read(worksheet=worksheet_name, ttl=0)
        return df.dropna(how='all')
    except Exception:
        # Trả về DF trống như cũ nếu có lỗi
        ...

def save_data(df, worksheet_name):
    conn = st.connection("gsheets", type=GSheetsConnection)
    # Lệnh update bây giờ sẽ chạy được vì đã có Service Account xác thực
    conn.update(worksheet=worksheet_name, data=df)
    st.cache_data.clear()


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


def get_current_stock(ma_qua, df_trans):
    if df_trans.empty: return 0
    return df_trans[df_trans["MaQua"].astype(str) == str(ma_qua)]["SoLuong"].sum()


def export_pdf(df):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", 'B', 14)
    pdf.cell(190, 10, txt="BAO CAO XUAT NHAP TON", ln=True, align='C')
    pdf.ln(10)
    cols = ["Ma", "Ten Qua", "Ton Dau", "Nhap", "Xuat", "Ton Cuoi"]
    widths = [20, 65, 25, 25, 25, 30]
    pdf.set_fill_color(200, 220, 255)
    for i, col in enumerate(cols):
        pdf.cell(widths[i], 8, col, border=1, fill=True, align='C')
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


# --- 2. GIAO DIỆN CHÍNH ---
st.set_page_config(page_title="Quản Lý Kho TNF", layout="wide")

# ĐĂNG NHẬP & TỰ ĐIỀN TÊN (Tra cứu từ Sheets)
if 'user_info' not in st.session_state:
    with st.container(border=True):
        st.subheader("🔐 Đăng nhập hệ thống")
        u_id = st.text_input("Mã nhân viên *", key='login_id')

        # Logic tự điền tên từ dữ liệu cũ
        temp_name = ""
        if u_id:
            df_check = load_data("trans")
            if not df_check.empty:
                match = df_check[df_check['NguoiThucHien'].str.contains(f"^{u_id} - ", na=False)]
                if not match.empty:
                    temp_name = match.iloc[0]['NguoiThucHien'].split(" - ")[1]

        u_name = st.text_input("Họ và Tên *", value=temp_name, key='login_name')

        if st.button("BẮT ĐẦU", type="primary", use_container_width=True):
            if u_id and u_name:
                st.session_state['user_info'] = {"id": u_id, "name": u_name}
                st.rerun()
            else:
                st.error("Vui lòng nhập đủ Mã và Tên")
    st.stop()

# LOAD DỮ LIỆU
df_gifts = load_data("gifts")
df_trans = load_data("trans")

with st.sidebar:
    st.success(f"👤 {st.session_state['user_info']['name']}")
    if st.button("Đăng xuất"):
        del st.session_state['user_info']
        st.rerun()

tabs = st.tabs(["📤 Xuất kho", "📥 Nhập kho", "📊 Báo cáo XNT", "📜 Nhật ký"])


def render_form(type_form="XUẤT"):
    global df_gifts, df_trans
    for key in [f"in_ma_{type_form}", f"in_ten_{type_form}", f"is_new_{type_form}"]:
        if key not in st.session_state: st.session_state[key] = "" if "in_" in key else False

    st.markdown(f"🔍 **Tìm quà tặng ({type_form}):**")
    search_term = st.text_input("Gõ để tìm...", key=f"src_{type_form}")

    filtered = df_gifts[df_gifts['MaQua'].astype(str).str.contains(search_term, case=False, na=False) |
                        df_gifts['TenQua'].str.contains(search_term, case=False,
                                                        na=False)] if search_term else pd.DataFrame()

    if not filtered.empty:
        opts = filtered.apply(lambda x: f"{x['MaQua']} - {x['TenQua']}", axis=1).tolist()
        sel = st.radio("Chọn món quà:", opts, key=f"rad_{type_form}")
        if sel:
            m, t = sel.split(" - ")
            st.session_state[f"in_ma_{type_form}"], st.session_state[f"in_ten_{type_form}"] = m, t
            st.session_state[f"is_new_{type_form}"] = False
    elif search_term != "" and type_form == "NHẬP":
        if st.button("➕ Tạo quà mới", use_container_width=True):
            st.session_state[f"in_ma_{type_form}"], st.session_state[f"in_ten_{type_form}"] = "", search_term
            st.session_state[f"is_new_{type_form}"] = True

    with st.container(border=True):
        st.markdown(f"📝 **Phiếu {type_form}**")
        so_ct = st.text_input("Số chứng từ *", key=f"c_{type_form}")

        is_locked = True if type_form == "XUẤT" or (type_form == "NHẬP" and not st.session_state[
            f"is_new_{type_form}"] and not df_gifts.empty) else False

        c1, c2 = st.columns(2)
        with c1:
            ma = st.text_input("Mã Quà *", key=f"in_ma_{type_form}", disabled=is_locked)
        with c2:
            ten = st.text_input("Tên Quà *", key=f"in_ten_{type_form}", disabled=is_locked)

        sl = st.number_input(f"Số lượng *", min_value=1, step=1, key=f"l_{type_form}")
        if ma:
            st.info(f"📊 Tồn kho hiện tại: **{get_current_stock(ma, df_trans)}**")

        note = st.text_input("Ghi chú", key=f"n_{type_form}")

        if st.button(f"XÁC NHẬN {type_form}", type="primary", use_container_width=True):
            cur_stk = get_current_stock(ma, df_trans)
            if type_form == "XUẤT" and (not ma or sl > cur_stk):
                st.error("Kho không đủ hoặc chưa chọn quà!")
            elif ma and ten and so_ct:
                new_trans = {
                    "Loai": type_form, "Ngay": date.today().strftime("%Y-%m-%d"),
                    "Gio": datetime.now().strftime("%H:%M:%S"), "SoChungTu": so_ct,
                    "MaQua": ma, "TenQua": ten, "SoLuong": sl if type_form == "NHẬP" else -sl,
                    "NguoiThucHien": f"{st.session_state['user_info']['id']} - {st.session_state['user_info']['name']}",
                    "GhiChu": note
                }
                df_trans = pd.concat([df_trans, pd.DataFrame([new_trans])], ignore_index=True)
                save_data(df_trans, "trans")

                if type_form == "NHẬP" and str(ma) not in df_gifts["MaQua"].astype(str).values:
                    df_gifts = pd.concat([df_gifts, pd.DataFrame([{"MaQua": ma, "TenQua": ten}])], ignore_index=True)
                    save_data(df_gifts, "gifts")

                st.success("✅ Thành công!");
                time.sleep(1);
                st.rerun()
            else:
                st.error("Điền thiếu thông tin!")


with tabs[0]: render_form("XUẤT")
with tabs[1]: render_form("NHẬP")

with tabs[2]:
    st.subheader("Báo cáo Xuất - Nhập - Tồn")
    c1, c2 = st.columns(2)
    d1 = c1.date_input("Từ ngày", date(date.today().year, date.today().month, 1))
    d2 = c2.date_input("Đến ngày", date.today())

    if st.button("📊 Xem báo cáo", use_container_width=True):
        if not df_trans.empty:
            df_t = df_trans.copy()
            df_t['Ngay'] = pd.to_datetime(df_t['Ngay']).dt.date
            rpt = []
            for _, item in df_gifts.iterrows():
                m, t = item['MaQua'], item['TenQua']
                t_dau = df_t[(df_t['MaQua'] == m) & (df_t['Ngay'] < d1)]['SoLuong'].sum()
                nhap = \
                df_t[(df_t['MaQua'] == m) & (df_t['Loai'] == "NHẬP") & (df_t['Ngay'] >= d1) & (df_t['Ngay'] <= d2)][
                    'SoLuong'].sum()
                xuat = abs(
                    df_t[(df_t['MaQua'] == m) & (df_t['Loai'] == "XUẤT") & (df_t['Ngay'] >= d1) & (df_t['Ngay'] <= d2)][
                        'SoLuong'].sum())
                rpt.append(
                    {"Mã": m, "Tên": t, "Tồn đầu": t_dau, "Nhập": nhap, "Xuất": xuat, "Tồn cuối": t_dau + nhap - xuat})
            st.session_state['res'] = pd.DataFrame(rpt)
            st.dataframe(st.session_state['res'], use_container_width=True, hide_index=True)

    if 'res' in st.session_state:
        ce, cp = st.columns(2)
        out = io.BytesIO()
        with pd.ExcelWriter(out, engine='xlsxwriter') as wr: st.session_state['res'].to_excel(wr, index=False)
        ce.download_button("📥 Excel", out.getvalue(), "XNT.xlsx", use_container_width=True)
        cp.download_button("📄 PDF", export_pdf(st.session_state['res']), "XNT.pdf", use_container_width=True)

with tabs[3]:
    st.subheader("Lịch sử giao dịch")
    if not df_trans.empty:
        st.dataframe(df_trans.iloc[::-1], use_container_width=True, hide_index=True)
    else:
        st.info("Chưa có dữ liệu.")