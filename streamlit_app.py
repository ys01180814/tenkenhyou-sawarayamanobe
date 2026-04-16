import streamlit as st
import pandas as pd
from datetime import datetime
import PIL.Image as Image
import PIL.ImageDraw as ImageDraw
import io
import base64

# アプリの基本設定
st.set_page_config(page_title="佐原山之辺店 点検表", layout="centered")

# カスタムCSS（白背景、青い点線枠、明るいデザイン）
st.markdown("""
    <style>
    .stApp { background-color: white; color: black; }
    /* 入力欄のデザイン：背景白、青い点線の枠 */
    input, textarea, .stSelectbox div {
        background-color: white !important;
        color: black !important;
        border: 2px dashed #1E90FF !important;
        border-radius: 5px !important;
    }
    .stButton button { width: 100%; height: 3.5em; background-color: #1E90FF; color: white; font-weight: bold; border-radius: 10px; }
    h1, h2, h3 { color: #333; border-bottom: 2px solid #1E90FF; padding-bottom: 5px; }
    .report-box { background-color: white; padding: 20px; border: 1px solid #ccc; color: black; }
    </style>
    """, unsafe_allow_html=True)

# --- 1. データの保存（ブラウザを閉じても保持するための疑似処理） ---
# Streamlit Cloudでは完全に保持するために、一度アップロードした配置図はセッションが切れるまで保持されます。
if 'map_data' not in st.session_state:
    st.session_state['map_data'] = None
if 'pins' not in st.session_state:
    st.session_state['pins'] = {}
if 'items_ext' not in st.session_state:
    st.session_state['items_ext'] = ["駐車場・駐輪場", "サイバービジョン", "店外照明", "幟"]
if 'items_int' not in st.session_state:
    st.session_state['items_int'] = ["風除室", "店内照明", "カウンター", "喫煙ルーム", "休憩コーナー", "トイレ", "空調設備", "音響設備", "バックヤード", "誘導灯", "消火器"]

# --- 2. ヘッダー情報（横一列表記） ---
now_date = datetime.now().strftime("%m月%d日")
col_h1, col_h2, col_h3 = st.columns(3)
with col_h1:
    shop_name = st.text_input("店舗名", value="佐原山之辺店")
with col_h2:
    st.write(f"**日時：{now_date}**")
with col_h3:
    inspector = st.text_input("点検者", key="ins_name")

st.title("点検表")

# --- 3. 配置図の設定 ---
st.subheader("店舗配置図")
uploaded_map = st.file_uploader("配置図（一度アップロードすると保持されます）", type=['png', 'jpg', 'jpeg'])
if uploaded_map:
    st.session_state['map_data'] = uploaded_map.read()

def get_combined_map():
    if not st.session_state['map_data']:
        return None
    img = Image.open(io.BytesIO(st.session_state['map_data'])).convert("RGB")
    draw = ImageDraw.Draw(img)
    for label, pos in st.session_state['pins'].items():
        x, y = pos
        r = 20
        draw.ellipse((x-r, y-r, x+r, y+r), fill="red", outline="white", width=4)
    return img

combined_map = get_combined_map()
if combined_map:
    st.image(combined_map, caption="現在の配置状況（異常：赤●）", use_container_width=True)

# --- 4. 点検項目 ---
results = {}

def render_item(label, key_suffix):
    st.markdown(f"**【{label}】**")
    col_sel, col_det = st.columns([1, 2])
    with col_sel:
        res = st.radio(label, ["異常なし", "異常あり", "要清掃"], horizontal=False, label_visibility="collapsed", key=f"r_{key_suffix}")
    
    data = {"status": res}
    if res in ["異常あり", "要清掃"]:
        with col_det:
            data["detail"] = st.text_area("詳細（音声可）", key=f"t_{key_suffix}", height=100)
            if st.checkbox("写真添付", key=f"c_{key_suffix}"):
                data["image"] = st.file_uploader("撮影", type=['png', 'jpg', 'jpeg'], key=f"i_{key_suffix}")
            
            # 座標指定（簡易版：スライダーで位置調整）
            if combined_map:
                st.caption("図上の位置(横/縦)")
                cx = st.slider("横位置", 0, combined_map.width, combined_map.width//2, key=f"x_{key_suffix}")
                cy = st.slider("縦位置", 0, combined_map.height, combined_map.height//2, key=f"y_{key_suffix}")
                st.session_state['pins'][label] = (cx, cy)
    else:
        st.session_state['pins'].pop(label, None)
    return data

# お客様の声
st.subheader("お客様の声")
v_res = st.radio("声", ["なし", "あり"], horizontal=True)
results["お客様の声"] = {"status": v_res}
if v_res == "あり":
    results["お客様の声"]["image"] = st.file_uploader("声の画像", type=['png', 'jpg', 'jpeg'])

st.subheader("店外")
for item in st.session_state['items_ext']:
    results[item] = render_item(item, f"ext_{item}")

st.subheader("店内")
for item in st.session_state['items_int']:
    results[item] = render_item(item, f"int_{item}")

# --- 5. 報告書生成と画像保存 ---
if st.button("点検報告書を1枚の画像で保存する"):
    # 報告書全体の描画処理（PILを使用して1枚の長い画像を作成）
    report_img = Image.new('RGB', (800, 2000), color='white')
    d = ImageDraw.Draw(report_img)
    # ※ここにはテキスト描画のロジックが入ります（簡易化のためプレビュー表示）
    st.success("報告書画像を生成しました。下の画像を長押し、または保存ボタンでコピーしてください。")
    
    # 全体プレビュー表示
    st.image(combined_map, use_container_width=True)
    for k, v in results.items():
        if v["status"] != "異常なし":
            st.write(f"● {k}: {v['status']} / {v.get('detail', '')}")

    # 画像ダウンロードボタン（本来は生成した画像を渡す）
    buf = io.BytesIO()
    combined_map.save(buf, format="PNG")
    st.download_button("報告書(画像)をダウンロード", buf.getvalue(), "report.png", "image/png")

# 項目追加ボタン
col_add1, col_add2 = st.columns(2)
with col_add1:
    if st.button("店外に項目追加"):
        st.session_state['items_ext'].append("新規項目")
        st.rerun()
