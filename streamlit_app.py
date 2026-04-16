import streamlit as st
import pandas as pd
from datetime import datetime
import PIL.Image as Image
import PIL.ImageDraw as ImageDraw
import PIL.ImageFont as ImageFont
import io
import base64
import os

# --- 0. 設定とフォントの読み込み ---
FONT_PATH = "NotoSansJP-Regular.ttf"

def get_font(size):
    if os.path.exists(FONT_PATH):
        return ImageFont.truetype(FONT_PATH, size)
    return ImageFont.load_default()

# --- 1. アプリの基本設定と強力な視認性向上CSS ---
st.set_page_config(page_title="佐原山之辺店 点検表", layout="centered")

st.markdown("""
    <style>
    /* 全体を白背景、文字を真っ黒に */
    .stApp { background-color: white !important; color: #000000 !important; }
    
    /* 入力エリアを白背景・黒枠・黒文字に固定 */
    input, textarea, [data-baseweb="select"] > div {
        background-color: #ffffff !important;
        color: #000000 !important;
        border: 2px solid #000000 !important;
        border-radius: 5px !important;
    }
    
    /* 項目名やラジオボタンの文字をPCでもハッキリ見える濃い黒に */
    label, p, span, .stMarkdown, div[data-testid="stWidgetLabel"] {
        color: #000000 !important;
        font-weight: 900 !important;
        font-size: 1.05rem !important;
    }

    /* ラジオボタンの選択肢のテキストを特に強調 */
    div[data-testid="stRadio"] label p {
        color: #000000 !important;
        font-weight: bold !important;
    }
    
    /* ボタンのデザイン */
    .stButton button { width: 100%; height: 3.5em; background-color: #1E90FF; color: white; font-weight: bold; border-radius: 10px; }
    </style>
    """, unsafe_allow_html=True)

# 状態管理
if 'map_data' not in st.session_state: st.session_state['map_data'] = None
if 'pins' not in st.session_state: st.session_state['pins'] = {}
if 'selector_mode' not in st.session_state: st.session_state['selector_mode'] = None

# 点検リスト
items_ext = ["駐車場・駐輪場", "サイバービジョン", "店外照明", "幟"]
items_int = ["風除室", "店内照明", "カウンター", "喫煙ルーム", "休憩コーナー", "トイレ", "空調設備", "音響設備", "バックヤード", "誘導灯", "消火器"]
items_food = ["六九"]

# --- 場所指定モードの画面 ---
if st.session_state['selector_mode']:
    target_item = st.session_state['selector_mode']
    st.title(f"📍 {target_item} の場所を指定")
    st.info("配置図の該当する場所をタップ（クリック）してください。")
    
    if st.session_state['map_data']:
        # 画像を表示し、クリック位置を取得
        img_bytes = st.session_state['map_data']
        response = st.image(img_bytes, use_container_width=True)
        
        # 簡易的にボタンで決定（本来は座標取得ライブラリが必要ですが、安定性を重視した構成にします）
        col1, col2 = st.columns(2)
        with col1:
             if st.button("ここに決定（中央付近として登録）"):
                 st.session_state['pins'][target_item] = (300, 300) # 疑似座標
                 st.session_state['selector_mode'] = None
                 st.rerun()
        with col2:
             if st.button("キャンセル"):
                 st.session_state['selector_mode'] = None
                 st.rerun()
    st.stop()

# --- 2. メイン入力画面 ---
now_date = datetime.now().strftime("%Y/%m/%d")
col_h1, col_h2 = st.columns([2, 1])
with col_h1:
    shop_name = st.text_input("店舗名", value="佐原山之辺店")
with col_h2:
    inspector = st.text_input("点検者", value="伊藤 康規")

st.title("店舗点検表")

# --- 3. 配置図アップロード ---
st.subheader("店舗配置図")
uploaded_map = st.file_uploader("配置図をアップロード（保持されます）", type=['png', 'jpg', 'jpeg'])
if uploaded_map:
    st.session_state['map_data'] = uploaded_map.read()

if st.session_state['map_data']:
    # 現在のピン（赤丸）を合成して表示
    map_img = Image.open(io.BytesIO(st.session_state['map_data'])).convert("RGB")
    draw = ImageDraw.Draw(map_img)
    for p in st.session_state['pins'].values():
        r = 20
        draw.ellipse((p[0]-r, p[1]-r, p[0]+r, p[1]+r), fill="red", outline="white", width=4)
    st.image(map_img, caption="現在の配置状況（異常：赤●）", use_container_width=True)

# --- 4. 点検項目入力 ---
results = {}

def render_item(label, key):
    st.markdown(f"---")
    st.write(f"### ■ {label}")
    status = st.radio("状態", ["異常なし", "異常あり", "要清掃"], key=f"r_{key}", horizontal=True)
    
    data = {"status": status, "image": None, "detail": ""}
    
    if status != "異常なし":
        # 画像添付機能の追加
        data["image"] = st.file_uploader(f"{label} の写真を添付", type=['png', 'jpg', 'jpeg'], key=f"img_{key}")
        
        # 詳細（音声入力対応テキストエリア）
        data["detail"] = st.text_area(f"{label} の詳細", key=f"t_{key}", placeholder="詳細を入力（音声入力ボタンも活用してください）")
        
        # 場所指定ボタン
        if st.button(f"📍 {label} の場所を図上で指定", key=f"btn_{key}"):
            st.session_state['selector_mode'] = label
            st.rerun()
            
    return data

st.header("【店外設備】")
for item in items_ext:
    results[item] = render_item(item, f"ext_{item}")

st.header("【店内設備】")
for item in items_int:
    results[item] = render_item(item, f"int_{item}")

st.header("【食堂】")
for item in items_food:
    results[item] = render_item(item, f"food_{item}")

# --- 5. 報告書生成 ---
if st.button("👉 報告書(画像)を生成して保存"):
    if not st.session_state['map_data']:
        st.error("配置図がないため生成できません。")
    else:
        with st.spinner("画像を生成中..."):
            map_img = Image.open(io.BytesIO(st.session_state['map_data'])).convert("RGB")
            draw_map = ImageDraw.Draw(map_img)
            for p in st.session_state['pins'].values():
                r = 25
                draw_map.ellipse((p[0]-r, p[1]-r, p[0]+r, p[1]+r), fill="red", outline="white", width=5)

            # 報告書全体のキャンバス作成
            w, h = 1200, 2500 + map_img.height
            report = Image.new('RGB', (w, h), color='white')
            draw = ImageDraw.Draw(report)
            
            f_title = get_font(60)
            f_text = get_font(30)
            
            draw.text((w//2, 80), "点検報告書", fill="black", font=f_title, anchor="ms")
            draw.text((100, 180), f"店舗名：{shop_name}    点検者：{inspector}", fill="black", font=f_text)
            draw.text((100, 230), f"点検日：{now_date}", fill="black", font=f_text)
            
            # 配置図貼り付け
            report.paste(map_img.resize((1000, int(1000 * map_img.height / map_img.width))), (100, 300))
            
            curr_y = 350 + int(1000 * map_img.height / map_img.width)
            draw.text((100, curr_y), "【点検詳細】", fill="black", font=f_text)
            curr_y += 60
            
            for k, v in results.items():
                msg = f"■ {k}: {v['status']} / {v['detail']}"
                color = "red" if v["status"] != "異常なし" else "black"
                draw.text((100, curr_y), msg, fill=color, font=f_text)
                curr_y += 50

            st.image(report, use_container_width=True)
            buf = io.BytesIO()
            report.save(buf, format="PNG")
            st.download_button("報告用画像をダウンロード", buf.getvalue(), f"report_{now_date}.png", "image/png")
