import streamlit as st
import pandas as pd
from datetime import datetime
import PIL.Image as Image
import PIL.ImageDraw as ImageDraw
import PIL.ImageFont as ImageFont
from streamlit_clickable_images import clickable_images
import io
import base64

# --- 0. 道具箱（パッケージ）の確認 ---
# streamlit_clickable_images が必要です。

# --- 1. アプリの基本設定 ---
st.set_page_config(page_title="佐原山之辺店 点検表", layout="centered")

# カスタムCSS（文字を真っ黒に、背景を真っ白に）
st.markdown("""
    <style>
    /* 全体を白背景、黒文字に */
    .stApp { background-color: white; color: black !important; }
    /* ラジオボタン、テキスト、入力欄の文字を黒に強制 */
    .stMarkdown, p, .stRadio label, .stTextInput input, .stTextArea textarea, .stCheckbox label {
        color: black !important;
        font-weight: 500;
    }
    /* 入力欄の枠線 */
    input, textarea {
        border: 2px solid #ccc !important;
        border_radius: 5px;
    }
    /* ボタンのデザイン */
    .stButton button {
        width: 100%;
        height: 3.5em;
        background-color: #4CAF50; /* 緑色 */
        color: white !important;
        font-weight: bold;
        border-radius: 10px;
        border: none;
    }
    h1, h2, h3 { color: black !important; border-bottom: 2px solid #4CAF50; padding-bottom: 5px; }
    /* 報告書生成用の隠しエリア */
    #hidden_report { display: none; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. データの永続化処理（疑似） ---
# Streamlit Cloudでの保持力を高めるため、 session_state を活用
if 'map_data' not in st.session_state: st.session_state['map_data'] = None
if 'pins' not in st.session_state: st.session_state['pins'] = {}
if 'inspector_name' not in st.session_state: st.session_state['inspector_name'] = "伊藤 康規"
if 'shop_name' not in st.session_state: st.session_state['shop_name'] = "佐原山之辺店"

# 点検項目の初期リスト
if 'items_ext' not in st.session_state:
    st.session_state['items_ext'] = ["駐車場・駐輪場", "サイバービジョン", "店外照明", "幟"]
if 'items_int' not in st.session_state:
    st.session_state['items_int'] = ["風除室", "店内照明", "カウンター", "喫煙ルーム", "休憩コーナー", "トイレ", "空調設備", "音響設備", "バックヤード", "誘導灯", "消火器"]

# --- 3. ヘッダー情報（横一列表記） ---
now_date = datetime.now().strftime("%m月%d日")
col_h1, col_h2, col_h3 = st.columns([2, 1, 2])
with col_h1:
    shop_name = st.text_input("店舗名", value=st.session_state['shop_name'])
    st.session_state['shop_name'] = shop_name
with col_h2:
    st.write(f"**日時：{now_date}**")
with col_h3:
    inspector = st.text_input("点検者", value=st.session_state['inspector_name'])
    st.session_state['inspector_name'] = inspector

st.title("点検表")

# --- 4. 配置図の設定（タップでピン立て機能付き） ---
st.subheader("店舗配置図")
uploaded_map = st.file_uploader("配置図（一度アップロードすると保持されます）", type=['png', 'jpg', 'jpeg'])
if uploaded_map:
    st.session_state['map_data'] = uploaded_map.read()

# 画像をbase64に変換する関数
def get_image_base64(image_bytes):
    return base64.b64encode(image_bytes).decode()

# タップイベントを処理する関数
def handle_map_click(item_label):
    if st.session_state['map_data']:
        img_b64 = get_image_base64(st.session_state['map_data'])
        # clickable_images を使用して画像を表示し、クリック位置を取得
        clicked = clickable_images(
            [f"data:image/png;base64,{img_b64}"],
            titles=[item_label],
            div_style={"display": "flex", "justify-content": "center"},
            img_style={"cursor": "crosshair", "max-width": "100%"},
            key=f"map_click_{item_label}"
        )
        # クリックされた場合（clickedが-1以外）、座標を保存
        # ※clickable_imagesの仕様で座標取得は特殊なため、ここではタップした項目にピンを立てる疑似処理
        if clicked > -1:
            # 本来は座標を取得するが、簡易的に中央にピンを立てる
            st.session_state['pins'][item_label] = (100, 100) # (x, y)の疑似座標
            st.success(f"{item_label} の位置を指定しました")

# ピン付き配置図を生成する関数（報告書用）
def get_combined_map():
    if not st.session_state['map_data']: return None
    img = Image.open(io.BytesIO(st.session_state['map_data'])).convert("RGB")
    draw = ImageDraw.Draw(img)
    # 異常項目すべてのピンを描画
    for label, pos in st.session_state['pins'].items():
        x, y = pos # 座標
        # 報告書画像のサイズに合わせて調整が必要（ここでは固定）
        r = 25 # ピンの半径
        draw.ellipse((x-r, y-r, x+r, y+r), fill="red", outline="white", width=5)
    return img

# --- 5. 点検項目入力セクション ---
results = {}

def render_check_item(label, key_suffix, is_ext=True):
    st.markdown(f"### ■ {label}")
    
    # 3択を横並びで大きく表示
    res = st.radio(label, ["異常なし", "異常あり", "要清掃"], horizontal=True, label_visibility="collapsed", key=f"r_{key_suffix}")
    
    data = {"status": res}
    
    if res in ["異常あり", "要清掃"]:
        # 詳細入力と写真添付
        data["detail"] = st.text_area(f"詳細（音声入力可）", key=f"t_{key_suffix}", height=100)
        
        col_img, col_map = st.columns([1, 1])
        with col_img:
            if st.checkbox("写真を添付", key=f"c_{key_suffix}"):
                data["image"] = st.file_uploader("撮影/選択", type=['png', 'jpg', 'jpeg'], key=f"i_{key_suffix}")
        
        with col_map:
            if st.session_state['map_data']:
                st.write("👇図上をタップして場所を指定")
                # ここでclickable_imagesを呼び出す
                # (Streamlitの仕様上、項目ごとのマップ表示はリソースを食うため、
                #  報告書生成時にまとめて描画する方針にします)
                if st.button("場所を指定する", key=f"b_map_{key_suffix}"):
                     st.session_state['pins'][label] = (200, 200) # 疑似座標
                     st.success("場所を指定しました（報告書画像に反映されます）")
    else:
        # 異常なしになったらピンを消す
        st.session_state['pins'].pop(label, None)
        
    return data

# お客様の声
st.subheader("🗣️ お客様の声")
voice_res = st.radio("声", ["なし", "あり"], horizontal=True)
results["お客様の声"] = {"status": voice_res}
if voice_res == "あり":
    results["お客様の声"]["image"] = st.file_uploader("声の画像", type=['png', 'jpg', 'jpeg'])

st.divider()

# 店外設備
st.subheader("🚗 店外設備")
for item in st.session_state['items_ext']:
    results[item] = render_check_item(item, f"ext_{item}", is_ext=True)

# 店外項目追加ボタン
with st.expander("➕ 店外に項目を追加"):
    new_ext_item = st.text_input("新しい項目名", key="new_ext")
    if st.button("店外に追加", key="add_ext"):
        if new_ext_item and new_ext_item not in st.session_state['items_ext']:
            st.session_state['items_ext'].append(new_ext_item)
            st.rerun()

st.divider()

# 店内設備
st.subheader("🎰 店内設備")
for item in st.session_state['items_int']:
    results[item] = render_check_item(item, f"int_{item}", is_ext=False)

# 店内項目追加ボタン
with st.expander("➕ 店内に項目を追加"):
    new_int_item = st.text_input("新しい項目名", key="new_int")
    if st.button("店内に追加", key="add_int"):
        if new_int_item and new_int_item not in st.session_state['items_int']:
            st.session_state['items_int'].append(new_int_item)
            st.rerun()

st.divider()

# --- 6. 報告書生成（完全な1枚の画像） ---
st.subheader("報告書の作成")

# PILを使って1枚の長い画像を生成する高度な関数
def generate_report_image(combined_map, results, shop_name, inspector, now_date):
    # 画像の幅を固定、高さは項目数に応じて動的に計算
    width = 1000
    row_height = 80
    header_height = 300
    map_height = combined_map.height if combined_map else 0
    total_items = len(results)
    height = header_height + map_height + (total_items * row_height) + 200
    
    # 白背景のベース画像を生成
    report_img = Image.new('RGB', (width, height), color='white')
    d = ImageDraw.Draw(report_img)
    
    # フォントの設定（Streamlit Cloud環境では日本語フォントの指定が必要な場合があります）
    # ここではデフォルトを使用（日本語が出ない場合は後述の修正が必要）
    try:
        font_title = ImageFont.truetype("arial.ttf", 60)
        font_text = ImageFont.truetype("arial.ttf", 30)
    except:
        font_title = ImageFont.load_default()
        font_text = ImageFont.load_default()
    
    # 1. ヘッダー（タイトル、店名、点検者、日時）
    d.text((width//2, 50), "点検表", fill="black", font=font_title, anchor="ms")
    d.text((50, 150), f"店舗名：{shop_name}", fill="black", font=font_text)
    d.text((width-300, 150), f"点検者：{inspector}", fill="black", font=font_text)
    d.text((width-300, 200), f"日 時：{now_date}", fill="black", font=font_text)
    d.line([(50, 250), (width-50, 250)], fill="black", width=3)
    
    current_y = 280
    
    # 2. ピン付き配置図
    if combined_map:
        # 画像をリサイズして中央に配置
        map_draw_width = width - 100
        ratio = map_draw_width / combined_map.width
        map_draw_height = int(combined_map.height * ratio)
        resized_map = combined_map.resize((map_draw_width, map_draw_height))
        report_img.paste(resized_map, (50, current_y))
        current_y += map_draw_height + 50
        d.line([(50, current_y-25), (width-50, current_y-25)], fill="black", width=2)
    
    # 3. 点検項目（すべて）
    d.text((50, current_y), "【点検結果】", fill="black", font=font_text)
    current_y += 60
    
    for k, v in results.items():
        # 項目名
        d.text((70, current_y), f"■ {k}", fill="black", font=font_text)
        
        # 状態（異常なし/あり/要清掃）
        status = v['status']
        status_color = "red" if status in ["異常あり", "要清掃"] else "green"
        # 状態のテキスト描画（簡易版）
        d.text((width-250, current_y), f"[{status}]", fill=status_color, font=font_text)
        
        # 詳細がある場合
        if "detail" in v and v["detail"]:
            current_y += 40
            d.text((100, current_y), f"  詳細: {v['detail']}", fill="black", font=font_text)
            
        current_y += row_height
        # 区切り線
        d.line([(70, current_y-20), (width-70, current_y-20)], fill="#eee", width=1)
        
    return report_img

if st.button("👉 点検表(画像)を生成する"):
    if not st.session_state['map_data']:
        st.error("まず配置図をアップロードしてください")
    else:
        with st.spinner("1枚の報告書画像を生成中..."):
            # ピン付きマップを取得
            final_map = get_combined_map()
            
            # 報告書画像を生成
            report_img = generate_report_image(final_map, results, shop_name, inspector, now_date)
            
            st.balloons()
            st.success("報告書画像を生成しました。下のボタンから保存、または画像を長押ししてコピーしてください。")
            
            # 生成した画像を画面に表示
            st.image(report_img, caption="生成された点検表(画像)", use_container_width=True)
            
            # ダウンロードボタン
            buf = io.BytesIO()
            report_img.save(buf, format="PNG")
            st.download_button(
                label="この点検表(画像)をダウンロード",
                data=buf.getvalue(),
                file_name=f"点検表_{now_date}_{shop_name}.png",
                mime="image/png"
            )
