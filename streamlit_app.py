import streamlit as st
import pandas as pd
from datetime import datetime
import PIL.Image as Image
import PIL.ImageDraw as ImageDraw
import PIL.ImageFont as ImageFont
import io
import os

# --- 0. 設定とフォントの読み込み ---
# フォントファイルがあるか確認（ステップ1でアップロードしたもの）
FONT_PATH = "NotoSansCJKjp-Regular.otf"

def get_font(size):
    if os.path.exists(FONT_PATH):
        return ImageFont.truetype(FONT_PATH, size)
    return ImageFont.load_default()

# --- 1. アプリの基本設定 ---
st.set_page_config(page_title="佐原山之辺店 点検表", layout="centered")

# カスタムCSS：背景を白、文字を黒、入力枠をグレーで囲む
st.markdown("""
    <style>
    .stApp { background-color: white; color: black !important; }
    /* 入力欄：背景白、文字黒、枠線をハッキリ */
    .stTextInput input, .stTextArea textarea, .stSelectbox div {
        background-color: white !important;
        color: black !important;
        border: 1px solid #333 !important;
    }
    /* ラベル文字を黒に */
    label, .stMarkdown p, .stRadio label { color: black !important; font-weight: bold !important; }
    /* ボタン */
    .stButton button { width: 100%; background-color: #1E90FF; color: white; font-weight: bold; }
    </style>
    """, unsafe_allow_html=True)

# データの保持
if 'map_data' not in st.session_state: st.session_state['map_data'] = None
if 'items_ext' not in st.session_state: st.session_state['items_ext'] = ["駐車場・駐輪場", "サイバービジョン", "店外照明", "幟"]
if 'items_int' not in st.session_state: st.session_state['items_int'] = ["風除室", "店内照明", "カウンター", "喫煙ルーム", "休憩コーナー", "トイレ", "空調設備", "音響設備", "バックヤード", "誘導灯", "消火器"]

# --- 2. ヘッダー（横一列） ---
now_date = datetime.now().strftime("%m月%d日")
col_h1, col_h2, col_h3 = st.columns([2, 1, 2])
with col_h1:
    shop_name = st.text_input("店舗名", value="佐原山之辺店")
with col_h2:
    st.write(f"📅 **{now_date}**")
with col_h3:
    inspector = st.text_input("点検者", value="伊藤 康規")

st.title("点検表")

# --- 3. 配置図のアップロードと表示 ---
st.subheader("店舗配置図")
uploaded_map = st.file_uploader("配置図をアップロード（一度行うと保持されます）", type=['png', 'jpg', 'jpeg'])

if uploaded_map:
    st.session_state['map_data'] = uploaded_map.read()

# 画像が読み込まれている場合に表示
if st.session_state['map_data']:
    st.image(st.session_state['map_data'], caption="店舗配置図", use_container_width=True)
else:
    st.warning("配置図がアップロードされていません。")

# --- 4. 点検項目入力 ---
results = {}

def render_item(label, key):
    st.markdown(f"### ■ {label}")
    res = st.radio(label, ["異常なし", "異常あり", "要清掃"], horizontal=True, key=f"r_{key}", label_visibility="collapsed")
    detail = ""
    if res in ["異常あり", "要清掃"]:
        detail = st.text_area("詳細（位置や内容）", key=f"t_{key}", placeholder="例：右奥の電球切れ")
    return {"status": res, "detail": detail}

st.subheader("【店外】")
for item in st.session_state['items_ext']:
    results[item] = render_item(item, f"ext_{item}")
if st.button("店外に項目を追加"):
    st.session_state['items_ext'].append("新規項目")
    st.rerun()

st.divider()

st.subheader("【店内】")
for item in st.session_state['items_int']:
    results[item] = render_item(item, f"int_{item}")
if st.button("店内に項目を追加"):
    st.session_state['items_int'].append("新規項目")
    st.rerun()

# --- 5. 報告書（画像）の生成 ---
if st.button("報告書(画像)を生成して保存"):
    if not st.session_state['map_data']:
        st.error("配置図がないため画像を生成できません。")
    else:
        # 画像生成ロジック
        map_img = Image.open(io.BytesIO(st.session_state['map_data'])).convert("RGB")
        w, h = 1000, 1500 + map_img.height
        report = Image.new('RGB', (w, h), color='white')
        draw = ImageDraw.Draw(report)
        
        f_title = get_font(60)
        f_text = get_font(30)
        
        # テキスト描画
        draw.text((w//2, 50), "点検報告書", fill="black", font=f_title, anchor="ms")
        draw.text((50, 150), f"店舗名：{shop_name}", fill="black", font=f_text)
        draw.text((50, 200), f"点検者：{inspector}   日時：{now_date}", fill="black", font=f_text)
        
        # 配置図を貼り付け
        report.paste(map_img.resize((900, int(900 * map_img.height / map_img.width))), (50, 280))
        
        # 項目描画
        curr_y = 350 + int(900 * map_img.height / map_img.width)
        for k, v in results.items():
            color = "red" if v["status"] != "異常なし" else "black"
            text = f"■ {k}: {v['status']} {v['detail']}"
            draw.text((50, curr_y), text, fill=color, font=f_text)
            curr_y += 50
        
        # プレビューと保存
        st.image(report, use_container_width=True)
        buf = io.BytesIO()
        report.save(buf, format="PNG")
        st.download_button("報告用画像をダウンロード", buf.getvalue(), "report.png", "image/png")
