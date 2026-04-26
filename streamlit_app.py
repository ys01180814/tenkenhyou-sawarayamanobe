import streamlit as st
from datetime import datetime
import PIL.Image as Image
import PIL.ImageDraw as ImageDraw
import PIL.ImageFont as ImageFont
import io
import os

# --- 0. 設定とフォントの読み込み ---
FONT_PATH = "NotoSansJP-Regular.ttf"

def get_font(size):
    if os.path.exists(FONT_PATH):
        return ImageFont.truetype(FONT_PATH, size)
    return ImageFont.load_default()

# --- 1. アプリの基本設定と視認性向上CSS ---
st.set_page_config(page_title="佐原山之辺店 点検表", layout="centered")

st.markdown("""
    <style>
    .stApp { background-color: white !important; color: #000000 !important; }
    input, textarea, [data-baseweb="select"] > div {
        background-color: #ffffff !important;
        color: #000000 !important;
        border: 2px solid #000000 !important;
    }
    label, p, span, .stMarkdown {
        color: #000000 !important;
        font-weight: 900 !important;
    }
    div[data-testid="stRadio"] label p {
        color: #000000 !important;
        font-weight: bold !important;
    }
    .button-row { display: flex; gap: 10px; margin-top: 10px; margin-bottom: 20px; }
    .stButton button { width: 100%; height: 3em; font-weight: bold; border-radius: 10px; }
    .add-btn button { background-color: #FF8C00 !important; color: white !important; }
    .edit-btn button { background-color: #4CAF50 !important; color: white !important; }
    .del-btn button { background-color: #FF4B4B !important; color: white !important; height: 2.2em !important; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. データの保持設定 ---
if 'map_data' not in st.session_state: st.session_state['map_data'] = None
if 'item_data' not in st.session_state: st.session_state['item_data'] = {}
if 'items_ext' not in st.session_state: 
    st.session_state['items_ext'] = ["駐車場・駐輪場", "サイバービジョン", "店外照明", "幟"]
if 'items_int' not in st.session_state: 
    st.session_state['items_int'] = ["風除室", "店内照明", "カウンター", "喫煙ルーム", "休憩コーナー", "トイレ", "空調設備", "音響設備", "バックヤード", "誘導灯", "消火器"]
if 'items_food' not in st.session_state: 
    st.session_state['items_food'] = ["六九", "その他 設備"]
if 'edit_mode' not in st.session_state: st.session_state['edit_mode'] = False

# --- 3. ヘッダー ---
now_date = datetime.now().strftime("%Y/%m/%d")
col_h1, col_h2 = st.columns([2, 1])
with col_h1:
    shop_name = st.text_input("店舗名", value="佐原山之辺店")
with col_h2:
    inspector = st.text_input("点検者", value="伊藤 康規")

st.title("店舗点検表")

# --- 4. 配置図 ---
st.subheader("店舗配置図")
uploaded_map = st.file_uploader("配置図をアップロード", type=['png', 'jpg', 'jpeg'])
if uploaded_map:
    st.session_state['map_data'] = uploaded_map.read()

if st.session_state['map_data']:
    st.image(st.session_state['map_data'], caption="店舗配置図", use_container_width=True)

# --- 5. 点検項目入力用関数 ---
def render_check_item(label, key, is_voice=False, section_list=None, idx=None):
    st.markdown(f"---")
    
    col_label, col_keep = st.columns([3, 1])
    with col_label:
        st.write(f"### ■ {label}")
    with col_keep:
        # 保存チェック（データ保持用）
        st.checkbox("データを保持", key=f"keep_{key}", value=True)

    # 削除ボタン（修正モード時かつ追加項目の場合のみ表示）
    if st.session_state['edit_mode'] and section_list is not None and idx is not None:
        st.markdown('<div class="del-btn">', unsafe_allow_html=True)
        if st.button(f"「{label}」を削除", key=f"del_{key}"):
            section_list.pop(idx)
            if key in st.session_state['item_data']: del st.session_state['item_data'][key]
            st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

    options = ["お声なし", "お声あり"] if is_voice else ["異常なし", "異常あり", "要清掃"]
    
    if key not in st.session_state['item_data']:
        st.session_state['item_data'][key] = {"status": options[0], "image": None, "detail": "", "pos": ""}
    
    curr_status = st.session_state['item_data'][key]["status"]
    default_idx = options.index(curr_status) if curr_status in options else 0
    status = st.radio("状態", options, index=default_idx, key=f"r_{key}", horizontal=True, label_visibility="collapsed")
    st.session_state['item_data'][key]["status"] = status
    
    if status in ["異常あり", "要清掃", "お声あり"]:
        img_file = st.file_uploader(f"{label}の写真を添付", type=['png', 'jpg', 'jpeg'], key=f"img_{key}")
        if img_file:
            st.session_state['item_data'][key]["image"] = img_file.read()
        
        detail = st.text_area(f"詳細内容", value=st.session_state['item_data'][key].get("detail", ""), key=f"t_{key}")
        st.session_state['item_data'][key]["detail"] = detail
        
        if not is_voice:
            pos = st.text_input(f"{label}の位置メモ", value=st.session_state['item_data'][key].get("pos", ""), key=f"p_{key}")
            st.session_state['item_data'][key]["pos"] = pos

# 追加と修正ボタンの並列表示用
def render_action_buttons(section_name, section_list, input_key):
    col1, col2 = st.columns(2)
    with col1:
        st.markdown('<div class="add-btn">', unsafe_allow_html=True)
        new_name = st.text_input(f"{section_name}項目名を入力", key=input_key)
        if st.button(f"＋ {section_name}に追加", key=f"btn_add_{input_key}"):
            if new_name:
                section_list.append(new_name)
                st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)
    with col2:
        st.markdown('<div class="edit-btn">', unsafe_allow_html=True)
        st.write("") 
        st.write("") 
        if st.button("修正（削除）モード", key=f"btn_edit_{input_key}"):
            st.session_state['edit_mode'] = not st.session_state['edit_mode']
            st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

# セクション表示
st.subheader("🗣️ お客様の声")
render_check_item("お客様の声", "voice", is_voice=True)

st.header("【店外設備】")
for i, item in enumerate(st.session_state['items_ext']):
    render_check_item(item, f"ext_{item}", section_list=st.session_state['items_ext'] if i >= 4 else None, idx=i)
render_action_buttons("店外", st.session_state['items_ext'], "add_ext")

st.header("【店内設備】")
for i, item in enumerate(st.session_state['items_int']):
    render_check_item(item, f"int_{item}", section_list=st.session_state['items_int'] if i >= 11 else None, idx=i)
render_action_buttons("店内", st.session_state['items_int'], "add_int")

st.header("【食堂・その他】")
for i, item in enumerate(st.session_state['items_food']):
    render_check_item(item, f"food_{item}")

# --- 6. 報告書生成ロジック（修正済み） ---
st.divider()
split_option = st.radio("報告書の生成方法", ["1枚にまとめる", "2枚に分ける"], horizontal=True)

def draw_report_content(draw, start_y, item_keys, report_img):
    curr_y = start_y
    f_text = get_font(28)
    for k in item_keys:
        if k not in st.session_state['item_data']: continue
        v = st.session_state['item_data'][k]
        
        is_err = v["status"] in ["異常あり", "要清掃", "お声あり"]
        
        # 【重要ルール】「その他 設備」だけは異常がない時はスキップ
        if "その他 設備" in k and not is_err:
            continue
        
        # それ以外の項目は、異常なしでもチェック外していても記載する
        label = k.replace("ext_","").replace("int_","").replace("food_","").replace("voice","お客様の声")
        draw.text((50, curr_y), f"■ {label}", fill="black", font=f_text)
        color = "red" if is_err else "green"
        draw.text((800, curr_y), f"[{v['status']}]", fill=color, font=f_text)
        curr_y += 35
        
        if is_err:
            info_txt = f"詳細: {v.get('detail','')} ({v.get('pos','')})"
            draw.text((80, curr_y), info_txt, fill="black", font=f_text)
            curr_y += 40
            if v.get("image"):
                try:
                    photo = Image.open(io.BytesIO(v["image"]))
                    photo.thumbnail((350, 350))
                    report_img.paste(photo, (80, curr_y))
                    curr_y += photo.height + 20
                except: pass
        draw.line([(50, curr_y), (950, curr_y)], fill="#eee")
        curr_y += 30
    return curr_y

def create_base_report(map_data, title_suffix=""):
    map_img = Image.open(io.BytesIO(map_data)).convert("RGB")
    report = Image.new('RGB', (1000, 5000), color='white')
    d = ImageDraw.Draw(report)
    f_title, f_text = get_font(60), get_font(28)
    d.text((500, 80), f"店舗点検報告書{title_suffix}", fill="black", font=f_title, anchor="ms")
    d.text((50, 160), f"店舗名：{shop_name}  点検者：{inspector}  日：{now_date}", fill="black", font=f_text)
    mw = 900
    mh = int(mw * map_img.height / map_img.width)
    report.paste(map_img.resize((mw, mh)), (50, 250))
    return report, d, 300 + mh

if st.button("👉 報告書を生成"):
    if not st.session_state['map_data']:
        st.error("配置図をアップロードしてください")
    else:
        with st.spinner("画像を生成中..."):
            ext_keys = ["voice"] + [f"ext_{i}" for i in st.session_state['items_ext']]
            int_food_keys = [f"int_{i}" for i in st.session_state['items_int']] + [f"food_{i}" for i in st.session_state['items_food']]
            
            if split_option == "1枚にまとめる":
                report, d, y = create_base_report(st.session_state['map_data'])
                y = draw_report_content(d, y, ext_keys + int_food_keys, report)
                final = report.crop((0, 0, 1000, y + 50))
                st.image(final, use_container_width=True)
                buf = io.BytesIO(); final.save(buf, format="PNG")
                st.download_button("画像を保存", buf.getvalue(), "report.png", "image/png")
            else:
                # 前半
                report1, d1, y1 = create_base_report(st.session_state['map_data'], " (前半)")
                y1 = draw_report_content(d1, y1, ext_keys, report1)
                final1 = report1.crop((0, 0, 1000, y1 + 50))
                st.image(final1, use_container_width=True)
                buf1 = io.BytesIO(); final1.save(buf1, format="PNG")
                st.download_button("前半を保存", buf1.getvalue(), "report_1.png", "image/png")
                # 後半
                report2 = Image.new('RGB', (1000, 4000), color='white')
                d2 = ImageDraw.Draw(report2)
                d2.text((500, 80), "店舗点検報告書 (後半)", fill="black", font=get_font(60), anchor="ms")
                y2 = draw_report_content(d2, 150, int_food_keys, report2)
                final2 = report2.crop((0, 0, 1000, y2 + 50))
                st.image(final2, use_container_width=True)
                buf2 = io.BytesIO(); final2.save(buf2, format="PNG")
                st.download_button("後半を保存", buf2.getvalue(), "report_2.png", "image/png")
