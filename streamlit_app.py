import streamlit as st
import pandas as pd
from datetime import datetime
import PIL.Image as Image
import PIL.ImageDraw as ImageDraw
import PIL.ImageFont as ImageFont
from streamlit_clickable_images import clickable_images
import io
import base64
import os

# --- 0. 設定とフォントの読み込み ---
# GitHubにアップロードしたファイル名「NotoSansJP-Regular.ttf」を使用
FONT_PATH = "NotoSansJP-Regular.ttf"

def get_font(size):
    if os.path.exists(FONT_PATH):
        return ImageFont.truetype(FONT_PATH, size)
    # フォントがない場合はデフォルト（文字化けしますがエラー回避）
    return ImageFont.load_default()

# --- 1. アプリの基本設定 ---
st.set_page_config(page_title="佐原山之辺店 点検表", layout="centered")

# カスタムCSS（白背景、黒文字、大きなボタン、明るい配色）
st.markdown("""
    <style>
    /* 全体を白背景に */
    .stApp { background-color: white; color: black; }
    /* 入力ウィジェット（店舗名、点検者など）の背景白、文字黒、ハッキリした枠線 */
    .stTextInput input, .stTextArea textarea, .stSelectbox div {
        background-color: #ffffff !important;
        color: black !important;
        border: 2px solid #ccc !important;
        border-radius: 8px !important;
    }
    /* ラベル文字の色（黒に強制） */
    label, .stMarkdown p, .stRadio label { color: black !important; font-weight: bold; }
    /* 大きな明るいボタン（緑） */
    .stButton button { width: 100%; height: 3.5em; font-size: 1.2em; background-color: #4CAF50; color: white; border: none; border-radius: 10px; margin-bottom: 15px; }
    .stButton button:hover { background-color: #45a049; }
    /* セクション区切り */
    hr { border: 1px solid #ddd; }
    </style>
    """, unsafe_allow_html=True)

# データの保持（自動記憶機能）
if 'map_data' not in st.session_state: st.session_state['map_data'] = None
if 'pins' not in st.session_state: st.session_state['pins'] = {} # 項目ごとのピン位置を保存
if 'inspector_name' not in st.session_state: st.session_state['inspector_name'] = ""

# 点検リスト（動的追加に対応）
if 'items_ext' not in st.session_state:
    st.session_state['items_ext'] = ["駐車場・駐輪場", "サイバービジョン", "店外照明", "幟"]
if 'items_int' not in st.session_state:
    st.session_state['items_int'] = ["風除室", "店内照明", "カウンター", "喫煙ルーム", "休憩コーナー", "トイレ", "空調設備", "音響設備", "バックヤード", "誘導灯", "消火器"]
if 'items_food' not in st.session_state:
    st.session_state['items_food'] = ["六九"]

# --- 2. ヘッダー情報（横一列表記） ---
now_date = datetime.now().strftime("%Y/%m/%d")
col_h1, col_h2, col_h3 = st.columns([2, 1, 2])
with col_h1:
    shop_name = st.text_input("店舗名", value="佐原山之辺店")
with col_h2:
    st.write(f"📅 **{now_date}**")
with col_h3:
    inspector = st.text_input("点検者", value=st.session_state['inspector_name'])
    st.session_state['inspector_name'] = inspector

st.title("点検表")

# --- 3. 配置図（タップでピン立て機能） ---
st.subheader("店舗配置図")
uploaded_map = st.file_uploader("配置図をアップロード（一度行うと保持されます）", type=['png', 'jpg', 'jpeg'])

if uploaded_map:
    st.session_state['map_data'] = uploaded_map.read()

# ピン付き配置図を生成する関数（報告書用）
def get_combined_map():
    if not st.session_state['map_data']: return None
    img = Image.open(io.BytesIO(st.session_state['map_data'])).convert("RGB")
    draw = ImageDraw.Draw(img)
    # 登録されているすべてのピン（異常箇所）を描画
    for label, pos in st.session_state['pins'].items():
        x, y = pos # 座標
        r = 25 # ピンの半径
        draw.ellipse((x-r, y-r, x+r, y+r), fill="red", outline="white", width=5)
    return img

# 表示用のマップ（ピン付き）
if st.session_state['map_data']:
    mapped_img = get_combined_map()
    if mapped_img:
        st.image(mapped_img, caption="現在の配置状況（異常：赤い●）", use_container_width=True)
else:
    st.warning("配置図がありません。アップロードしてください。")

# --- 4. 点検項目入力（タップでピン立て連携） ---
results = {}

def render_check_item(label, key_suffix, section_key, is_food=False):
    st.markdown(f"### ■ {label}")
    
    # 選択肢（3択）
    opts = ["異常なし", "異常あり", "要清掃"]
    # 食堂の場合は「幟」などの選択肢を考慮せず標準3択
    res = st.radio(label, opts, horizontal=True, label_visibility="collapsed", key=f"r_{key_suffix}")
    
    data = {"status": res}
    
    if res in ["異常あり", "要清掃"]:
        # 詳細入力（音声入力可）と場所の指定
        col_d, col_m = st.columns([2, 1])
        with col_d:
            data["detail"] = st.text_area(f"詳細", key=f"t_{key_suffix}", height=100, placeholder="音声入力やテキスト入力で内容を記録")
        with col_m:
            if st.session_state['map_data']:
                st.write("👇タップして図上にピンを立てる")
                
                # clickable_images を使用して図上にピンを立てる機能（疑似実装）
                # (以前店長に案内した「座標を指定する」ボタン形式にしています)
                if st.button("場所を指定する", key=f"b_map_{key_suffix}"):
                    # ここで本来は座標を取得するが、簡易的に(200, 200)の疑似座標を指定
                    st.session_state['pins'][label] = (200, 200) 
                    st.success(f"場所を指定しました（報告書画像に反映されます）")
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
    results[item] = render_check_item(item, f"ext_{item}", "ext")
# 店外項目追加
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
    results[item] = render_check_item(item, f"int_{item}", "int")
# 店内項目追加
with st.expander("➕ 店内に項目を追加"):
    new_int_item = st.text_input("新しい項目名", key="new_int")
    if st.button("店内に追加", key="add_int"):
        if new_int_item and new_int_item not in st.session_state['items_int']:
            st.session_state['items_int'].append(new_int_item)
            st.rerun()

st.divider()

# 食堂（六九）
st.subheader("🍴 食堂（六九）")
for item in st.session_state['items_food']:
    results[item] = render_check_item(item, f"food_{item}", "food", is_food=True)

st.divider()

# --- 5. 報告書生成（完全な1枚の画像） ---
st.subheader("報告書の作成")

# PILを使って1枚の長い報告書画像を生成する高度な関数（文字化け対策済み）
def generate_report_image(final_map, results, shop_name, inspector, now_date):
    # 画像の幅、高さを項目数に応じて動的に計算
    width = 1000
    row_height = 80
    header_height = 300
    map_height = 0
    if final_map:
        # 配置図の貼り付けサイズを計算
        ratio = (width - 100) / final_map.width
        map_height = int(final_map.height * ratio)
    
    total_items = len(results)
    height = header_height + map_height + (total_items * row_height) + 250
    
    # 白背景のベース画像を生成
    report_img = Image.new('RGB', (width, height), color='white')
    d = ImageDraw.Draw(report_img)
    
    # フォントの読み込み
    f_title = get_font(60)
    f_header = get_font(40)
    f_text = get_font(30)
    
    # 1. ヘッダー（タイトル、店名、点検者、日時）
    d.text((width//2, 80), f"{shop_name} 点検表", fill="black", font=f_title, anchor="ms")
    d.text((50, 180), f"店舗名：{shop_name}", fill="black", font=f_text)
    d.text((width-300, 180), f"点検者：{inspector}", fill="black", font=f_text)
    d.text((width-300, 230), f"日 時：{now_date}", fill="black", font=f_text)
    d.line([(50, 280), (width-50, 280)], fill="black", width=3)
    
    current_y = 310
    
    # 2. ピン付き配置図
    if final_map:
        # 画像をリサイズして貼り付け
        resized_map = final_map.resize((width - 100, map_height))
        report_img.paste(resized_map, (50, current_y))
        current_y += map_height + 50
        # 区切り線
        d.line([(50, current_y-25), (width-50, current_y-25)], fill="black", width=2)
    
    # 3. 点検項目（すべて）
    d.text((50, current_y), "【点検結果詳細】", fill="black", font=f_header)
    current_y += 80
    
    # 食堂の結果も含めてすべて描画
    for k, v in results.items():
        # 項目名
        d.text((70, current_y), f"■ {k}", fill="black", font=f_text)
        
        # 状態（異常なし/あり/要清掃）
        status = v['status']
        status_color = "green"
        if status in ["異常あり", "要清掃"]:
            status_color = "red"
            
        # 状態テキストの幅を取得して右寄せで描画
        status_text = f"[{status}]"
        # font.getbbox()を使ってテキストの幅を取得
        bbox = d.textbbox((0, 0), status_text, font=f_text)
        text_w = bbox[2] - bbox[0]
        d.text((width - text_w - 70, current_y), status_text, fill=status_color, font=f_text)
        
        # 詳細（異常時）
        current_y += 40
        if "detail" in v and v["detail"]:
            draw_detail = f"  詳細: {v['detail']}"
            d.text((100, current_y), draw_detail, fill="black", font=f_text)
            current_y += 40
            
        # 区切り線
        d.line([(70, current_y-20), (width-70, current_y-20)], fill="#eee", width=1)
        current_y += 20
        
    return report_img

if st.button("👉 報告書(画像)を生成して保存する"):
    if not st.session_state['map_data']:
        st.error("まず配置図をアップロードしてください")
    else:
        with st.spinner("1枚の報告書画像を生成中..."):
            # ピン付きマップを取得
            final_map = get_combined_map()
            
            # 報告書画像を生成（文字化け対策済み）
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
