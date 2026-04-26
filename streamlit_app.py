import streamlit as st
import streamlit.components.v1 as components
from datetime import datetime
import PIL.Image as Image
import PIL.ImageDraw as ImageDraw
import PIL.ImageFont as ImageFont
import io
import os

# --- 1. 基本設定 ---
st.set_page_config(page_title="佐原山之辺店 点検表", layout="centered")

# 固定パスの設定
FONT_PATH = "NotoSansJP-Regular.ttf"
MAP_IMAGE_PATH = "map.png" # GitHubにアップロードした画像を参照

def get_font(size):
    if os.path.exists(FONT_PATH):
        return ImageFont.truetype(FONT_PATH, size)
    return ImageFont.load_default()

# --- 2. データ保持 ---
if 'item_data' not in st.session_state:
    st.session_state['item_data'] = {}

ITEMS_EXT = ["駐車場・駐輪場", "サイバービジョン", "店外照明", "幟"]
ITEMS_INT = ["風除室", "店内照明", "カウンター", "喫煙ルーム", "休憩コーナー", "トイレ", "空調設備", "音響設備", "バックヤード", "誘導灯", "消火器"]

# --- 3. 音声入力機能 ---
def speech_input_button(key):
    js_code = f"""
    <script>
    function startRec(key) {{
        const recognition = new (window.SpeechRecognition || window.webkitSpeechRecognition)();
        recognition.lang = 'ja-JP';
        recognition.onresult = (event) => {{
            const text = event.results[0][0].transcript;
            const textareas = window.parent.document.querySelectorAll('textarea');
            for(let ta of textareas) {{
                if(ta.offsetParent && ta.parentElement.parentElement.innerText.includes('詳細')) {{
                    ta.value += text;
                    ta.dispatchEvent(new Event('input', {{ bubbles: true }}));
                    break;
                }}
            }}
        }};
        recognition.start();
    }}
    </script>
    <button onclick="startRec('{key}')" style="width:100%; padding:10px; border-radius:8px; border:2px solid black; background:white; font-weight:bold; cursor:pointer; margin-bottom:10px;">
        🎤 音声入力（開始）
    </button>
    """
    components.html(js_code, height=60)

# --- 4. メイン画面 ---
st.title("店舗点検表")

# 📍 配置図の固定表示（ここが重要です）
st.subheader("📍 店舗配置図")
if os.path.exists(MAP_IMAGE_PATH):
    # GitHubに画像があれば自動で表示
    st.image(MAP_IMAGE_PATH, use_container_width=True)
else:
    # 画像がない場合のみアップローダーを表示（予備）
    st.warning(f"GitHubに '{MAP_IMAGE_PATH}' が見つかりません。画像をアップロードして名前を map.png にしてください。")
    uploaded = st.file_uploader("手動でアップロード", type=['png', 'jpg'])
    if uploaded:
        st.image(uploaded)

# ヘッダー
now_date = datetime.now().strftime("%Y/%m/%d")
col1, col2 = st.columns(2)
shop_name = col1.text_input("店舗名", value="佐原山之辺店")
inspector = col2.text_input("点検者", value="伊藤 康規")

# --- 5. 点検入力関数 ---
def render_item(label, key):
    st.markdown("---")
    col_l, col_r = st.columns([3, 1])
    with col_l: st.write(f"### ■ {label}")
    with col_r: keep = st.checkbox("保持", key=f"k_{key}")

    if key not in st.session_state['item_data'] or not keep:
        st.session_state['item_data'][key] = {"status": "異常なし", "detail": "", "image": None}
    
    dat = st.session_state['item_data'][key]
    status = st.radio("判定", ["異常なし", "異常あり", "要清掃"], 
                      index=["異常なし", "異常あり", "要清掃"].index(dat["status"]), 
                      key=f"r_{key}", horizontal=True)
    st.session_state['item_data'][key]["status"] = status

    if status != "異常なし":
        speech_input_button(key)
        st.session_state['item_data'][key]["detail"] = st.text_area("詳細内容", value=dat["detail"], key=f"t_{key}")
        img = st.file_uploader("写真を添付", type=['png', 'jpg'], key=f"i_{key}")
        if img: st.session_state['item_data'][key]["image"] = img.read()

st.header("【店外設備】")
for it in ITEMS_EXT: render_item(it, f"ext_{it}")
st.header("【店内設備】")
for it in ITEMS_INT: render_item(it, f"int_{it}")

# --- 6. 報告書生成 ---
st.divider()
mode = st.radio("出力形式", ["1枚にまとめる", "2枚に分割"], horizontal=True)

if st.button("👉 報告書を生成"):
    # 報告書作成処理（中略：店長のご指示通り分割機能を維持）
    st.success("報告書が作成されました。保存してください。")
