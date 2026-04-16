import streamlit as st
from datetime import datetime
import PIL.Image as Image
import PIL.ImageDraw as ImageDraw
import PIL.ImageFont as ImageFont
import io
import os

# --- 0. 設定とフォントの読み込み ---
# 店長がアップロードしたファイル名「NotoSansJP-Regular.ttf」を使用
FONT_PATH = "NotoSansJP-Regular.ttf"

def get_font(size):
    if os.path.exists(FONT_PATH):
        return ImageFont.truetype(FONT_PATH, size)
    return ImageFont.load_default()

# --- 1. アプリの基本設定と強力な視認性向上CSS ---
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
    .stButton button { width: 100%; height: 3.5em; background-color: #1E90FF; color: white; font-weight: bold; border-radius: 10px; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. データの保持 ---
if 'map_data' not in st.session_state: st.session_state['map_data'] = None
if 'item_data' not in st.session_state: st.session_state['item_data'] = {}

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
uploaded_map = st.file_uploader("配置図をアップロード（消えた場合は再度お願いします）", type=['png', 'jpg', 'jpeg'])

if uploaded_map:
    st.session_state['map_data'] = uploaded_map.read()

if st.session_state['map_data']:
    st.image(st.session_state['map_data'], caption="店舗配置図", use_container_width=True)

# --- 5. 点検項目入力 ---
items_ext = ["駐車場・駐輪場", "サイバービジョン", "店外照明", "幟"]
items_int = ["風除室", "店内照明", "カウンター", "喫煙ルーム", "休憩コーナー", "トイレ", "空調設備", "音響設備", "バックヤード", "誘導灯", "消火器"]
items_food = ["六九"]

def render_check_item(label, key):
    st.markdown(f"---")
    st.write(f"### ■ {label}")
    status = st.radio("状態", ["異常なし", "異常あり", "要清掃"], key=f"r_{key}", horizontal=True)
    
    if key not in st.session_state['item_data']:
        st.session_state['item_data'][key] = {"status": "異常なし", "image": None, "detail": ""}
    
    st.session_state['item_data'][key]["status"] = status
    
    if status != "異常なし":
        # 写真添付
        img_file = st.file_uploader("写真を添付", type=['png', 'jpg', 'jpeg'], key=f"img_{key}")
        if img_file:
            st.session_state['item_data'][key]["image"] = img_file.read()
        
        # 詳細（音声入力対応）
        detail = st.text_area(f"詳細", value=st.session_state['item_data'][key].get("detail", ""), key=f"t_{key}")
        st.session_state['item_data'][key]["detail"] = detail
        
        # 位置メモ
        pos = st.text_input("位置（例：スロットコーナー奥）", key=f"p_{key}")
        st.session_state['item_data'][key]["pos"] = pos

# お客様の声
st.subheader("🗣️ お客様の声")
render_check_item("お客様の声", "voice")

st.header("【店外設備】")
for item in items_ext: render_check_item(item, f"ext_{item}")

st.header("【店内設備】")
for item in items_int: render_check_item(item, f"int_{item}")

st.header("【食堂】")
for item in items_food: render_check_item(item, f"food_{item}")

# --- 6. 報告書生成 ---
if st.button("👉 報告書(画像)を生成"):
    if not st.session_state['map_data']:
        st.error("配置図をアップロードしてください。")
    else:
        # 画像生成処理
        map_img = Image.open(io.BytesIO(st.session_state['map_data'])).convert("RGB")
        w, h = 1000, 2500 + map_img.height
        report = Image.new('RGB', (w, h), color='white')
        d = ImageDraw.Draw(report)
        f_title, f_text, f_bold = get_font(60), get_font(30), get_font(35)
        
        d.text((500, 80), "点検報告書", fill="black", font=f_title, anchor="ms")
        d.text((50, 180), f"店舗名：{shop_name}  点検者：{inspector}  日：{now_date}", fill="black", font=f_text)
        
        # 配置図
        mw = 900
        mh = int(mw * map_img.height / map_img.width)
        report.paste(map_img.resize((mw, mh)), (50, 250))
        
        curr_y = 300 + mh
        d.text((50, curr_y), "【点検詳細】", fill="black", font=f_bold)
        curr_y += 70
        
        for k, v in st.session_state['item_data'].items():
            label = k.replace("ext_","").replace("int_","").replace("food_","").replace("voice","お客様の声")
            # 項目と状態
            d.text((50, curr_y), f"■ {label}", fill="black", font=f_text)
            color = "red" if v["status"] != "異常なし" else "green"
            d.text((800, curr_y), f"[{v['status']}]", fill=color, font=f_text)
            curr_y += 40
            
            if v["status"] != "異常なし":
                if v.get("detail") or v.get("pos"):
                    d.text((80, curr_y), f"詳細: {v['detail']} ({v.get('pos','')})", fill="black", font=f_text)
                    curr_y += 40
                if v.get("image"):
                    photo = Image.open(io.BytesIO(v["image"]))
                    photo.thumbnail((300, 300))
                    report.paste(photo, (80, curr_y))
                    curr_y += photo.height + 20
            
            d.line([(50, curr_y), (950, curr_y)], fill="#eee")
            curr_y += 30
            if curr_y > h - 100: break

        st.image(report, use_container_width=True)
        buf = io.BytesIO()
        report.save(buf, format="PNG")
        st.download_button("画像を保存", buf.getvalue(), "report.png", "image/png")
