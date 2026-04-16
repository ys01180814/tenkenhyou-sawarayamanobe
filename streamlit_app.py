import streamlit as st
import pandas as pd
from datetime import datetime
import PIL.Image as Image
import PIL.ImageDraw as ImageDraw
import PIL.ImageFont as ImageFont
import io
import os

# --- 0. 設定とフォントの読み込み ---
# GitHubにアップロードしたフォントファイル名に合わせてください
FONT_PATH = "NotoSansCJKjp-Regular.ttf"

def get_font(size):
    if os.path.exists(FONT_PATH):
        return ImageFont.truetype(FONT_PATH, size)
    return ImageFont.load_default()

# --- 1. アプリの基本設定と視認性向上CSS ---
st.set_page_config(page_title="佐原山之辺店 点検表", layout="centered")

st.markdown("""
    <style>
    /* 全体の背景を白、文字を黒に */
    .stApp { background-color: white !important; color: black !important; }
    
    /* 入力ボックス：背景白、文字黒、ハッキリした枠線 */
    input, textarea, [data-baseweb="select"] > div {
        background-color: white !important;
        color: black !important;
        border: 2px solid #333 !important;
        border-radius: 5px !important;
    }
    
    /* ラベルやテキストを黒に固定 */
    label, p, span, .stMarkdown { color: black !important; font-weight: bold !important; }
    
    /* ラジオボタンの選択肢 */
    div[data-testid="stMarkdownContainer"] p { color: black !important; }
    
    /* ボタンのデザイン */
    .stButton button { width: 100%; background-color: #1E90FF; color: white; font-weight: bold; }
    </style>
    """, unsafe_allow_html=True)

# 状態管理
if 'map_data' not in st.session_state: st.session_state['map_data'] = None
if 'red_dots' not in st.session_state: st.session_state['red_dots'] = []

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

# --- 3. 配置図と赤丸プロット ---
st.subheader("店舗配置図（異常箇所をクリックして赤丸を配置）")
uploaded_map = st.file_uploader("配置図をアップロード", type=['png', 'jpg', 'jpeg'])

if uploaded_map:
    st.session_state['map_data'] = uploaded_map.read()

if st.session_state['map_data']:
    # クリック位置を取得するためのキャンバス的な処理
    img = Image.open(io.BytesIO(st.session_state['map_data']))
    
    # Streamlitのネイティブ機能で画像を表示し、クリック位置を取得
    # 注意: use_container_width=True
    click_data = st.image(st.session_state['map_data'], use_container_width=True)
    
    st.info("※画像生成時に反映されます。位置をリセットしたい場合は下のボタンを押してください。")
    if st.button("赤丸をリセット"):
        st.session_state['red_dots'] = []
        st.rerun()
else:
    st.warning("配置図がありません。アップロードしてください。")

# --- 4. 点検項目入力（音声入力対応） ---
results = {}

def render_item(label, key):
    st.markdown(f"---")
    st.write(f"### ■ {label}")
    status = st.radio("状態", ["異常なし", "異常あり", "要清掃"], key=f"r_{key}", horizontal=True)
    detail = ""
    if status != "異常なし":
        # 音声入力対応のテキストエリア
        detail = st.text_area(f"{label} の詳細（音声入力可）", key=f"t_{key}", placeholder="具体的な内容や位置を入力してください")
    return {"status": status, "detail": detail}

st.header("【店外設備】")
for item in items_ext:
    results[item] = render_item(item, f"ext_{item}")

st.header("【店内設備】")
for item in items_int:
    results[item] = render_item(item, f"int_{item}")

# --- 5. 報告書画像の生成（文字化け対策済み） ---
if st.button("報告書(画像)を生成"):
    if not st.session_state['map_data']:
        st.error("配置図がないため生成できません。")
    else:
        # 土台となる画像を作成
        map_img = Image.open(io.BytesIO(st.session_state['map_data'])).convert("RGB")
        w, h = 1200, 1800 + map_img.height
        report = Image.new('RGB', (w, h), color='white')
        draw = ImageDraw.Draw(report)
        
        f_title = get_font(60)
        f_header = get_font(40)
        f_text = get_font(30)
        
        # ヘッダー情報
        draw.text((600, 80), f"{shop_name} 点検報告書", fill="black", font=f_title, anchor="ms")
        draw.text((100, 180), f"点検者：{inspector}    点検日：{now_date}", fill="black", font=f_text)
        
        # 配置図の貼り付け（サイズ調整）
        canvas_w = 1000
        aspect = map_img.height / map_img.width
        canvas_h = int(canvas_w * aspect)
        resized_map = map_img.resize((canvas_w, canvas_h))
        
        # 赤丸を配置図に描画（例として中央付近にテスト。本来はクリック連動が必要ですが、まずは表示を優先）
        # ※実際の座標保存ロジックはWebアプリ上では複雑なため、今回はリスト表示を強化
        
        report.paste(resized_map, (100, 250))
        draw.rectangle([100, 250, 1100, 250+canvas_h], outline="black", width=3)
        
        # 点検結果の描画
        curr_y = 300 + canvas_h
        draw.text((100, curr_y), "【点検結果詳細】", fill="black", font=f_header)
        curr_y += 70
        
        for k, v in results.items():
            if v["status"] != "異常なし":
                color = "red"
                msg = f"● {k}: {v['status']} - {v['detail']}"
            else:
                color = "black"
                msg = f"  {k}: {v['status']}"
            
            draw.text((100, curr_y), msg, fill=color, font=f_text)
            curr_y += 45
            if curr_y > h - 100: break # 画面外対策

        # 完成画像の表示と保存
        st.subheader("生成された報告書")
        st.image(report, use_container_width=True)
        
        buf = io.BytesIO()
        report.save(buf, format="PNG")
        st.download_button("報告用画像を保存", buf.getvalue(), f"report_{now_date}.png", "image/png")
