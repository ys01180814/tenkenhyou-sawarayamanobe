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

# --- 0. 設定とフォントの読み込み（文字化け対策済み） ---
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

# --- 2. データの保持処理（自動記憶機能） ---
# 配置図データをsession_stateに保持
if 'map_data' not in st.session_state: st.session_state['map_data'] = None
# 各項目のピン（赤丸）位置を保持
if 'pins' not in st.session_state: st.session_state['pins'] = {}
# 各項目の点検データを保持
if 'item_data' not in st.session_state: st.session_state['item_data'] = {}

# --- 3. ヘッダー情報（横一列表記） ---
now_date = datetime.now().strftime("%Y/%m/%d")
col_h1, col_h2 = st.columns([2, 1])
with col_h1:
    shop_name = st.text_input("店舗名", value="佐原山之辺店")
with col_h2:
    inspector = st.text_input("点検者", value="伊藤 康規")
st.write(f"📅 点検日: {now_date}")

st.title("店舗点検表")

# --- 4. 配置図の設定 ---
st.subheader("店舗配置図")
uploaded_map = st.file_uploader("配置図をアップロード（一度行うと保持されます）", type=['png', 'jpg', 'jpeg'])

if uploaded_map:
    # 新しい配置図がアップロードされたら、古いピンを消す
    st.session_state['map_data'] = uploaded_map.read()
    st.session_state['pins'] = {} # ピンをリセット
    st.rerun()

# ピン付き配置図を生成する関数（報告書用）
def get_combined_map():
    if not st.session_state['map_data']: return None
    img = Image.open(io.BytesIO(st.session_state['map_data'])).convert("RGB")
    draw = ImageDraw.Draw(img)
    for pos in st.session_state['pins'].values():
        x, y = pos # 座標
        r = 25 # ピンの半径
        draw.ellipse((x-r, y-r, x+r, y+r), fill="red", outline="white", width=5)
    return img

# 表示用のマップ
if st.session_state['map_data']:
    mapped_img = get_combined_map()
    if mapped_img:
        st.image(mapped_img, caption="現在の配置状況（異常：赤●）", use_container_width=True)

# --- 5. 点検項目入力 ---
# 点検リスト
items_ext = ["駐車場・駐輪場", "サイバービジョン", "店外照明", "幟"]
items_int = ["風除室", "店内照明", "カウンター", "喫煙ルーム", "休憩コーナー", "トイレ", "空調設備", "音響設備", "バックヤード", "誘導灯", "消火器"]
items_food = ["六九"]

def render_check_item(label, key):
    st.markdown(f"---")
    st.write(f"### ■ {label}")
    
    # 選択肢（横並び）
    status = st.radio("状態", ["異常なし", "異常あり", "要清掃"], key=f"r_{key}", horizontal=True, label_visibility="collapsed")
    
    # 初期データを設定
    if key not in st.session_state['item_data']:
        st.session_state['item_data'][key] = {"status": "異常なし", "image": None, "detail": ""}
    
    st.session_state['item_data'][key]["status"] = status
    
    if status != "異常なし":
        # 1. 写真添付（復活）
        uploaded_file = st.file_uploader("写真を添付", type=['png', 'jpg', 'jpeg'], key=f"img_{key}")
        if uploaded_file:
            st.session_state['item_data'][key]["image"] = uploaded_file.read()
        
        # 2. 詳細入力（音声入力対応）
        detail = st.text_area(f"詳細", value=st.session_state['item_data'][key]["detail"], key=f"t_{key}", placeholder="詳細を入力（音声入力ボタンも活用してください）")
        st.session_state['item_data'][key]["detail"] = detail
        
        # 3. 図上で場所を指定（赤丸プロット）
        # Webアプリ上での座標取得は困難なため、ここでは詳細欄へのメモ入力に留めます
        detail_pos = st.text_input("図上の位置メモ（赤丸の代わり）", key=f"pos_{key}", placeholder="例：右奥スロットコーナー付近")
        st.session_state['item_data'][key]["detail_pos"] = detail_pos
            
# ② お客様の声（トップに復活）
st.subheader("🗣️ お客様の声")
render_check_item("お客様の声", "customer_voice")

st.divider()

# 店外設備
st.header("【店外設備】")
for item in items_ext:
    render_check_item(item, f"ext_{item}")

st.divider()

# 店内設備
st.header("【店内設備】")
for item in items_int:
    render_check_item(item, f"int_{item}")

st.divider()

# 食堂（六九）
st.header("【食堂（六九）】")
for item in items_food:
    render_check_item(item, f"food_{item}")

st.divider()

# --- 6. 報告書生成（完全な1枚の画像） ---
st.subheader("報告書の作成")

# PILを使って1枚の長い画像を生成する高度な関数（文字化け対策済み）
def generate_report_image(combined_map, shop_name, inspector, now_date):
    # 画像の幅、高さを項目数に応じて動的に計算
    width = 1000
    header_height = 300
    map_height = 0
    if combined_map:
        ratio = (width - 100) / combined_map.width
        map_height = int(combined_map.height * ratio)
    
    row_height = 100
    total_items = len(st.session_state['item_data'])
    height = header_height + map_height + (total_items * row_height) + 500
    
    # 白背景のベース画像
    report_img = Image.new('RGB', (width, height), color='white')
    d = ImageDraw.Draw(report_img)
    
    # フォントの読み込み
    f_title = get_font(60)
    f_header = get_font(40)
    f_text = get_font(30)
    f_bold = get_font(32)
    
    # 1. ヘッダー（タイトル、店名、点検者、日時）
    d.text((width//2, 80), "点検報告書", fill="black", font=f_title, anchor="ms")
    d.text((50, 180), f"店舗名：{shop_name}", fill="black", font=f_text)
    d.text((50, 230), f"点検者：{inspector}    日 時：{now_date}", fill="black", font=f_text)
    d.line([(50, 280), (width-50, 280)], fill="black", width=3)
    
    current_y = 310
    
    # 2. ピン付き配置図
    if combined_map:
        resized_map = combined_map.resize((width - 100, map_height))
        report_img.paste(resized_map, (50, current_y))
        current_y += map_height + 50
        d.line([(50, current_y-25), (width-50, current_y-25)], fill="black", width=2)
    
    # 3. 点検項目（レイアウト大幅改善）
    d.text((50, current_y), "【点検詳細】", fill="black", font=f_header)
    current_y += 80
    
    # セクションごとに表示する関数
    def draw_section_items(section_title, item_keys):
        nonlocal current_y
        d.text((70, current_y), f"▼ {section_title}", fill="black", font=f_bold)
        current_y += 50
        
        for key in item_keys:
            data = st.session_state['item_data'].get(key, {"status": "異常なし", "image": None, "detail": ""})
            label = key.replace("ext_", "").replace("int_", "").replace("food_", "").replace("customer_voice", "お客様の声")
            
            # [左側] 項目名
            d.text((90, current_y), f"■ {label}", fill="black", font=f_text)
            
            # [右側] 状態
            status = data['status']
            status_color = "red" if status != "異常なし" else "green"
            status_text = f"[{status}]"
            
            # 幅を取得して右寄せ
            bbox = d.textbbox((0, 0), status_text, font=f_text)
            text_w = bbox[2] - bbox[0]
            d.text((width - text_w - 90, current_y), status_text, fill=status_color, font=f_text)
            
            current_y += 40
            
            # [下] 詳細と写真（異常時）
            if status != "異常なし":
                if data['detail']:
                    # 詳細テキストを折り返して描画（簡易実装）
                    draw_detail = f"  詳細: {data['detail']} ({data.get('detail_pos', '')})"
                    d.text((120, current_y), draw_detail, fill="black", font=f_text)
                    current_y += 40
                
                # 写真の貼り付け（復活）
                if data['image']:
                    try:
                        photo = Image.open(io.BytesIO(data['image']))
                        photo_w = 200
                        photo_h = int(photo.height * (photo_w / photo.width))
                        report_img.paste(photo.resize((photo_w, photo_h)), (120, current_y))
                        current_y += photo_h + 20
                    except:
                        pass # 画像が壊れている場合はスキップ
            
            # 区切り線
            d.line([(90, current_y), (width-90, current_y)], fill="#eee", width=1)
            current_y += 20
        
        current_y += 30 # セクション間のマージン

    # 食堂 Result: "food_"
    draw_section_items("お客様の声", ["customer_voice"])
    draw_section_items("店外設備", [f"ext_{i}" for i in items_ext])
    draw_section_items("店内設備", [f"int_{i}" for i in items_int])
    draw_section_items("食堂（六九）", [f"food_{i}" for i in items_food])
        
    return report_img

if st.button("👉 この点検表(画像)をダウンロード"):
    if not st.session_state['map_data']:
        st.error("まず配置図をアップロードしてください")
    else:
        with st.spinner("1枚の長い画像を生成中..."):
            # ピン付きマップを取得
            final_map = get_combined_map()
            
            # 報告書画像を生成（レイアウト改善・写真入り）
            report_img = generate_report_image(final_map, shop_name, inspector, now_date)
            
            st.success("報告書画像を生成しました。長押しまたはボタンで保存してください。")
            
            # 完成画像を表示
            st.image(report_img, caption="生成された点検報告書(画像)", use_container_width=True)
            
            # ダウンロードボタン
            buf = io.BytesIO()
            report_img.save(buf, format="PNG")
            st.download_button(
                label="この点検表(画像)をダウンロード",
                data=buf.getvalue(),
                file_name=f"点検表_{now_date}_{shop_name}.png",
                mime="image/png"
            )
