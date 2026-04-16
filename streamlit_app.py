import streamlit as st
import pandas as pd
from datetime import datetime
import PIL.Image as Image
import PIL.ImageDraw as ImageDraw
import PIL.ImageFont as ImageFont
import io
import os

# --- 0. 設定とフォントの読み込み ---
# 店長がアップロードしたファイル名「NotoSansJP-Regular.ttf」に合わせました
FONT_PATH = "NotoSansJP-Regular.ttf"

def get_font(size):
    if os.path.exists(FONT_PATH):
        return ImageFont.truetype(FONT_PATH, size)
    return ImageFont.load_default()

# --- 1. アプリの基本設定と視認性向上（超強力版） ---
st.set_page_config(page_title="佐原山之辺店 点検表", layout="centered")

st.markdown("""
    <style>
    /* 全体の背景を白、文字を黒に強制 */
    html, body, [data-testid="stAppViewContainer"] {
        background-color: white !important;
        color: black !important;
    }
    
    /* 入力エリア（店舗名、点検者など）を白背景・黒枠・黒文字に */
    input, textarea, [data-baseweb="select"] > div {
        background-color: #ffffff !important;
        color: #000000 !important;
        border: 2px solid #333333 !important;
        -webkit-text-fill-color: black !important;
    }
    
    /* ラベル文字（項目名など）を大きく黒く */
    label, p, span, .stMarkdown {
        color: black !important;
        font-weight: bold !important;
    }
    
    /* 音声入力後のテキストエリアも見やすく */
    .stTextArea textarea {
        background-color: #f9f9f9 !important;
        color: black !important;
    }
    
    /* ボタン */
    .stButton button {
        width: 100%;
        background-color: #1E90FF;
        color: white;
        font-weight: bold;
    }
    </style>
    """, unsafe_allow_html=True)

# 状態管理
if 'map_data' not in st.session_state: st.session_state['map_data'] = None

# 点検リスト
items_ext = ["駐車場・駐輪場", "サイバービジョン", "店外照明", "幟"]
items_int = ["風除室", "店内照明", "カウンター", "喫煙ルーム", "休憩コーナー", "トイレ", "空調設備", "音響設備", "バックヤード", "誘導灯", "消火器"]

# --- 2. ヘッダー ---
now_date = datetime.now().strftime("%Y/%m/%d")
col_h1, col_h2 = st.columns([2, 1])
with col_h1:
    shop_name = st.text_input("店舗名", value="佐原山之辺店")
with col_h2:
    inspector = st.text_input("点検者", value="伊藤 康規")
st.write(f"📅 点検日: {now_date}")

st.title("店舗点検表")

# --- 3. 配置図表示 ---
st.subheader("店舗配置図")
uploaded_map = st.file_uploader("配置図をアップロード", type=['png', 'jpg', 'jpeg'])

if uploaded_map:
    st.session_state['map_data'] = uploaded_map.read()

if st.session_state['map_data']:
    st.image(st.session_state['map_data'], use_container_width=True)
else:
    st.warning("配置図をアップロードしてください。")

# --- 4. 点検項目入力（音声入力・赤丸位置メモ対応） ---
results = {}

def render_item(label, key):
    st.markdown(f"---")
    st.write(f"### ■ {label}")
    status = st.radio("状態", ["異常なし", "異常あり", "要清掃"], key=f"r_{key}", horizontal=True)
    
    detail = ""
    pos_memo = ""
    if status != "異常なし":
        # 詳細（音声入力として利用）
        detail = st.text_area(f"{label} の詳細", key=f"t_{key}", placeholder="具体的な内容を話すか入力してください")
        # 図上の位置をテキストでメモ（赤丸プロットの代わり）
        pos_memo = st.text_input(f"{label} の図上の位置", key=f"p_{key}", placeholder="例：右上のスロットコーナー付近")
        
    return {"status": status, "detail": detail, "pos": pos_memo}

st.header("【店外設備】")
for item in items_ext:
    results[item] = render_item(item, f"ext_{item}")

st.header("【店内設備】")
for item in items_int:
    results[item] = render_item(item, f"int_{item}")

# --- 5. 報告書画像の生成（文字化け対策版） ---
if st.button("報告書(画像)を生成"):
    if not st.session_state['map_data']:
        st.error("配置図がないため生成できません。")
    else:
        map_img = Image.open(io.BytesIO(st.session_state['map_data'])).convert("RGB")
        
        # 縦長の画像を作成
        w, h = 1200, 2000 + map_img.height
        report = Image.new('RGB', (w, h), color='white')
        draw = ImageDraw.Draw(report)
        
        f_title = get_font(60)
        f_header = get_font(40)
        f_text = get_font(30)
        
        # タイトル
        draw.text((600, 80), f"{shop_name} 点検報告書", fill="black", font=f_title, anchor="ms")
        draw.text((100, 180), f"点検者：{inspector}    点検日：{now_date}", fill="black", font=f_text)
        
        # 配置図貼り付け
        canvas_w = 1000
        aspect = map_img.height / map_img.width
        canvas_h = int(canvas_w * aspect)
        resized_map = map_img.resize((canvas_w, canvas_h))
        report.paste(resized_map, (100, 250))
        draw.rectangle([100, 250, 1100, 250+canvas_h], outline="black", width=3)
        
        # 結果の描画
        curr_y = 320 + canvas_h
        draw.text((100, curr_y), "【点検結果詳細】", fill="black", font=f_header)
        curr_y += 80
        
        for k, v in results.items():
            if v["status"] != "異常なし":
                msg = f"● {k}: {v['status']} - {v['detail']} ({v['pos']})"
                draw.text((100, curr_y), msg, fill="red", font=f_text)
                curr_y += 50
            else:
                msg = f"  {k}: {v['status']}"
                draw.text((100, curr_y), msg, fill="black", font=f_text)
                curr_y += 45
            
            if curr_y > h - 100: break

        st.subheader("生成プレビュー（文字化けが直っているか確認してください）")
        st.image(report, use_container_width=True)
        
        buf = io.BytesIO()
        report.save(buf, format="PNG")
        st.download_button("報告用画像を保存", buf.getvalue(), f"report_{now_date}.png", "image/png")
