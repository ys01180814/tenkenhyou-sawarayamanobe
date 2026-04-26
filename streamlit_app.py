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
    .stButton button { width: 100%; height: 3em; background-color: #1E90FF; color: white; font-weight: bold; border-radius: 10px; margin-top: 10px; }
    .add-btn button { background-color: #FF8C00 !important; height: 2.5em !important; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. データの保持 ---
if 'map_data' not in st.session_state: st.session_state['map_data'] = None
if 'item_data' not in st.session_state: st.session_state['item_data'] = {}
if 'items_ext' not in st.session_state: 
    st.session_state['items_ext'] = ["駐車場・駐輪場", "サイバービジョン", "店外照明", "幟"]
if 'items_int' not in st.session_state: 
    st.session_state['items_int'] = ["風除室", "店内照明", "カウンター", "喫煙ルーム", "休憩コーナー", "トイレ", "空調設備", "音響設備", "バックヤード", "誘導灯", "消火器"]
if 'items_food' not in st.session_state: 
    st.session_state['items_food'] = ["六九"]

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
def render_check_item(label, key, is_voice=False):
    st.markdown(f"---")
    st.write(f"### ■ {label}")
    options = ["お声なし", "お声あり"] if is_voice else ["異常なし", "異常あり", "要清掃"]
    status = st.radio("状態", options, key=f"r_{key}", horizontal=True, label_visibility="collapsed")
    
    if key not in st.session_state['item_data']:
        st.session_state['item_data'][key] = {"status": options[0], "image": None, "detail": "", "pos": ""}
    
    st.session_state['item_data'][key]["status"] = status
    
    if status in ["異常あり", "要清掃", "お声あり"]:
        img_file = st.file_uploader(f"{label}の写真を添付", type=['png', 'jpg', 'jpeg'], key=f"img_{key}")
        if img_file:
            st.session_state['item_data'][key]["image"] = img_file.read()
        
        detail = st.text_area(f"詳細内容", value=st.session_state['item_data'][key].get("detail", ""), key=f"t_{key}", placeholder="詳細を入力（音声入力可）")
        st.session_state['item_data'][key]["detail"] = detail
        
        if not is_voice:
            pos = st.text_input(f"{label}の位置メモ", value=st.session_state['item_data'][key].get("pos", ""), key=f"p_{key}", placeholder="例：スロット側入口付近")
            st.session_state['item_data'][key]["pos"] = pos

# --- 入力セクション ---
st.subheader("🗣️ お客様の声")
render_check_item("お客様の声", "voice", is_voice=True)

st.header("【店外設備】")
for item in st.session_state['items_ext']:
    render_check_item(item, f"ext_{item}")

with st.container():
    st.markdown('<div class="add-btn">', unsafe_allow_html=True)
    if st.button("＋ 店外に項目を追加"):
        new_item = st.text_input("追加する項目名（店外）", key="add_ext_name")
        if new_item:
            st.session_state['items_ext'].append(new_item)
            st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

st.header("【店内設備】")
for item in st.session_state['items_int']:
    render_check_item(item, f"int_{item}")

with st.container():
    st.markdown('<div class="add-btn">', unsafe_allow_html=True)
    if st.button("＋ 店内に項目を追加"):
        new_item = st.text_input("追加する項目名（店内）", key="add_int_name")
        if new_item:
            st.session_state['items_int'].append(new_item)
            st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

st.header("【食堂】")
for item in st.session_state['items_food']:
    render_check_item(item, f"food_{item}")

# --- 6. 報告書生成（分割プレビュー対応） ---
st.divider()
st.subheader("報告書の生成設定")
split_option = st.radio("生成方法を選択してください", ["1枚にまとめる", "2枚に分ける"], horizontal=True)

def draw_report_content(draw, start_y, item_keys, report_img):
    curr_y = start_y
    f_text, f_bold = get_font(28), get_font(35)
    
    for k in item_keys:
        if k not in st.session_state['item_data']: continue
        v = st.session_state['item_data'][k]
        label = k.replace("ext_","").replace("int_","").replace("food_","").replace("voice","お客様の声")
        
        draw.text((50, curr_y), f"■ {label}", fill="black", font=f_text)
        is_err = v["status"] in ["異常あり", "要清掃", "お声あり"]
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
    w = 1000
    # 高さは余裕を持って設定
    report = Image.new('RGB', (w, 3000), color='white')
    d = ImageDraw.Draw(report)
    f_title, f_text = get_font(60), get_font(28)
    
    d.text((500, 80), f"店舗点検報告書{title_suffix}", fill="black", font=f_title, anchor="ms")
    d.text((50, 160), f"店舗名：{shop_name}", fill="black", font=f_text)
    d.text((50, 200), f"点検者：{inspector}    点検日：{now_date}", fill="black", font=f_text)
    
    mw = 900
    mh = int(mw * map_img.height / map_img.width)
    report.paste(map_img.resize((mw, mh)), (50, 250))
    
    return report, d, 300 + mh

if st.button("👉 報告書(画像)を生成"):
    if not st.session_state['map_data']:
        st.error("配置図をアップロードしてください。")
    else:
        with st.spinner("画像を生成中..."):
            all_keys = list(st.session_state['item_data'].keys())
            ext_keys = ["voice"] + [f"ext_{i}" for i in st.session_state['items_ext']]
            int_food_keys = [f"int_{i}" for i in st.session_state['items_int']] + [f"food_{i}" for i in st.session_state['items_food']]

            if split_option == "1枚にまとめる":
                report, d, y = create_base_report(st.session_state['map_data'])
                y = draw_report_content(d, y, all_keys, report)
                final_report = report.crop((0, 0, 1000, y + 50))
                st.image(final_report, use_container_width=True)
                buf = io.BytesIO()
                final_report.save(buf, format="PNG")
                st.download_button("この点検画像を保存", buf.getvalue(), f"点検表_一括_{now_date}.png", "image/png")
            
            else:
                # 前半の生成
                report1, d1, y1 = create_base_report(st.session_state['map_data'], " (前半)")
                y1 = draw_report_content(d1, y1, ext_keys, report1)
                final1 = report1.crop((0, 0, 1000, y1 + 50))
                
                # 後半の生成（後半は配置図なしでヘッダーのみ）
                report2 = Image.new('RGB', (1000, 3000), color='white')
                d2 = ImageDraw.Draw(report2)
                f_title, f_text = get_font(60), get_font(28)
                d2.text((500, 80), "店舗点検報告書 (後半)", fill="black", font=f_title, anchor="ms")
                d2.text((50, 160), f"店舗名：{shop_name}  点検者：{inspector}  点検日：{now_date}", fill="black", font=f_text)
                y2 = draw_report_content(d2, 220, int_food_keys, report2)
                final2 = report2.crop((0, 0, 1000, y2 + 50))
                
                col1, col2 = st.columns(2)
                with col1:
                    st.image(final1, caption="前半：配置図＋店外", use_container_width=True)
                    buf1 = io.BytesIO()
                    final1.save(buf1, format="PNG")
                    st.download_button("前半を保存", buf1.getvalue(), f"点検表_前半_{now_date}.png", "image/png")
                with col2:
                    st.image(final2, caption="後半：店内＋食堂", use_container_width=True)
                    buf2 = io.BytesIO()
                    final2.save(buf2, format="PNG")
                    st.download_button("後半を保存", buf2.getvalue(), f"点検表_後半_{now_date}.png", "image/png")
