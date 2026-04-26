import streamlit as st
import streamlit.components.v1 as components
from datetime import datetime
import PIL.Image as Image
import PIL.ImageDraw as ImageDraw
import PIL.ImageFont as ImageFont
import io
import os

# --- 0. フォント設定 ---
FONT_PATH = "NotoSansJP-Regular.ttf"
def get_font(size):
    if os.path.exists(FONT_PATH):
        return ImageFont.truetype(FONT_PATH, size)
    return ImageFont.load_default()

# --- 1. アプリ設定とセッション初期化 (エラー対策) ---
st.set_page_config(page_title="佐原山之辺店 点検表", layout="centered")

def init_session():
    # 配置図
    if 'map_data' not in st.session_state: st.session_state['map_data'] = None
    # 各点検項目のデータ
    if 'item_data' not in st.session_state: st.session_state['item_data'] = {}
    # カテゴリ項目リスト
    if 'items_ext' not in st.session_state: 
        st.session_state['items_ext'] = ["駐車場・駐輪場", "サイバービジョン", "店外照明", "幟"]
    if 'items_int' not in st.session_state: 
        st.session_state['items_int'] = ["風除室", "店内照明", "カウンター", "喫煙ルーム", "休憩コーナー", "トイレ", "空調設備", "音響設備", "バックヤード", "誘導灯", "消火器"]
    if 'items_food' not in st.session_state: 
        st.session_state['items_food'] = ["六九", "その他 設備"]
    # フラグ類の初期化 (KeyError防止)
    flags = ['show_add_ext', 'show_edit_ext', 'show_add_int', 'show_edit_int']
    for f in flags:
        if f not in st.session_state: st.session_state[f] = False

init_session()

# --- 2. デザインCSS ---
st.markdown("""
    <style>
    .stApp { background-color: white !important; color: #000000 !important; }
    input, textarea, [data-baseweb="select"] > div {
        background-color: #ffffff !important; color: #000000 !important; border: 2px solid #000000 !important;
    }
    label, p, span, .stMarkdown { color: #000000 !important; font-weight: 900 !important; }
    .stButton button {
        width: 100%; background-color: #ffffff !important; color: #000000 !important;
        border: 2px solid #000000 !important; font-weight: bold !important; border-radius: 8px !important;
    }
    .speech-btn {
        background-color: #ffffff; border: 2px solid #000000; border-radius: 8px;
        padding: 8px 16px; font-weight: bold; cursor: pointer; width: 100%; margin-bottom: 10px;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 3. 音声認識JS ---
def speech_to_text_js(key):
    js_code = f"""
    <div id="speech-container-{key}">
        <button class="speech-btn" onclick="startRecognition('{key}')">🎤 音声入力（開始）</button>
        <p id="status-{key}" style="font-size:11px; color:gray;">タップして詳細を入力</p>
    </div>
    <script>
    function startRecognition(key) {{
        const status = document.getElementById('status-' + key);
        const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
        if (!SpeechRecognition) return;
        const recognition = new SpeechRecognition();
        recognition.lang = 'ja-JP';
        recognition.onstart = () => {{ status.innerText = "認識中..."; }};
        recognition.onresult = (event) => {{
            const text = event.results[0][0].transcript;
            const textareas = window.parent.document.querySelectorAll('textarea');
            for (let ta of textareas) {{
                if (ta.offsetParent !== null) {{
                    ta.value += text;
                    ta.dispatchEvent(new Event('input', {{ bubbles: true }}));
                    break;
                }}
            }}
            status.innerText = "完了";
        }};
        recognition.start();
    }}
    </script>
    """
    components.html(js_code, height=80)

# --- 4. ヘッダー ---
now_date = datetime.now().strftime("%Y/%m/%d")
col_h1, col_h2 = st.columns([2, 1])
with col_h1: shop_name = st.text_input("店舗名", value="佐原山之辺店")
with col_h2: inspector = st.text_input("点検者", value="伊藤 康規")
st.title("店舗点検表")

# --- 5. 配置図 ---
if st.session_state['map_data'] is None:
    uploaded_map = st.file_uploader("配置図をアップロード", type=['png', 'jpg', 'jpeg'])
    if uploaded_map:
        st.session_state['map_data'] = uploaded_map.read()
        st.rerun()
else:
    st.image(st.session_state['map_data'], caption="店舗配置図", use_container_width=True)
    if st.button("配置図をリセット"):
        st.session_state['map_data'] = None
        st.rerun()

# --- 6. 点検項目入力用関数 ---
def render_check_item(label, key, is_voice=False, section_list=None, idx=None, is_edit_mode=False):
    st.markdown("---")
    
    col_label, col_keep = st.columns([3, 1])
    with col_label: st.write(f"### ■ {label}")
    with col_keep: 
        # 「データを保持」は初期値オフ(False)に変更
        is_keep = st.checkbox("データを保持", key=f"keep_{key}", value=False)

    # 項目削除ボタン
    if is_edit_mode and section_list is not None and idx is not None:
        if st.button(f"「{label}」を削除", key=f"btn_del_{key}"):
            section_list.pop(idx)
            if key in st.session_state['item_data']:
                del st.session_state['item_data'][key]
            st.rerun()

    options = ["お声なし", "お声あり"] if is_voice else ["異常なし", "異常あり", "要清掃"]
    
    # セッションデータの読み込みと「保持」の判定
    if key not in st.session_state['item_data'] or not is_keep:
        st.session_state['item_data'][key] = {"status": options[0], "image": None, "detail": ""}

    saved_data = st.session_state['item_data'][key]
    default_idx = options.index(saved_data["status"]) if saved_data["status"] in options else 0
    
    status = st.radio("状態", options, index=default_idx, key=f"r_{key}", horizontal=True, label_visibility="collapsed")
    st.session_state['item_data'][key]["status"] = status
    
    if status in ["異常あり", "要清掃", "お声あり"]:
        img_file = st.file_uploader(f"{label}の写真を添付", type=['png', 'jpg', 'jpeg'], key=f"img_{key}")
        if img_file:
            st.session_state['item_data'][key]["image"] = img_file.read()
        
        speech_to_text_js(key)
        detail = st.text_area("詳細内容", value=st.session_state['item_data'][key]["detail"], key=f"t_{key}")
        st.session_state['item_data'][key]["detail"] = detail

def render_action_area(section_list, add_flag_key, edit_flag_key, input_key):
    col1, col2 = st.columns(2)
    with col1:
        if st.button("項目追加", key=f"ui_add_{input_key}"):
            st.session_state[add_flag_key] = not st.session_state[add_flag_key]
            st.rerun()
    with col2:
        if st.button("項目修正", key=f"ui_edit_{input_key}"):
            st.session_state[edit_flag_key] = not st.session_state[edit_flag_key]
            st.rerun()
    
    if st.session_state.get(add_flag_key):
        new_name = st.text_input("追加する項目名を入力", key=f"input_{input_key}")
        if st.button("確定して追加", key=f"confirm_{input_key}"):
            if new_name:
                section_list.append(new_name)
                st.session_state[add_flag_key] = False
                st.rerun()

# --- 各セクション描画 ---
st.subheader("🗣️ お客様の声")
render_check_item("お客様の声", "voice", is_voice=True)

st.header("【店外設備】")
for i, item in enumerate(list(st.session_state['items_ext'])):
    render_check_item(item, f"ext_{item}", section_list=st.session_state['items_ext'] if i >= 4 else None, idx=i, is_edit_mode=st.session_state.get('show_edit_ext', False))
render_action_area(st.session_state['items_ext'], 'show_add_ext', 'show_edit_ext', 'ext')

st.header("【店内設備】")
for i, item in enumerate(list(st.session_state['items_int'])):
    render_check_item(item, f"int_{item}", section_list=st.session_state['items_int'] if i >= 11 else None, idx=i, is_edit_mode=st.session_state.get('show_edit_int', False))
render_action_area(st.session_state['items_int'], 'show_add_int', 'show_edit_int', 'int')

st.header("【食堂・その他】")
for i, item in enumerate(st.session_state['items_food']):
    render_check_item(item, f"food_{item}")

# --- 報告書生成 ---
st.divider()
if st.button("👉 報告書を生成"):
    if not st.session_state['map_data']:
        st.error("配置図をアップロードしてください")
    else:
        with st.spinner("画像を生成中..."):
            map_img = Image.open(io.BytesIO(st.session_state['map_data'])).convert("RGB")
            report = Image.new('RGB', (1000, 8000), color='white')
            d = ImageDraw.Draw(report)
            f_text = get_font(28)
            d.text((500, 80), f"{shop_name} 点検報告書", fill="black", font=get_font(60), anchor="ms")
            d.text((50, 160), f"点検者：{inspector}    点検日：{now_date}", fill="black", font=f_text)
            mw, mh = 900, int(900 * map_img.height / map_img.width)
            report.paste(map_img.resize((mw, mh)), (50, 250))
            
            curr_y = 300 + mh
            all_keys = ["voice"] + [f"ext_{i}" for i in st.session_state['items_ext']] + [f"int_{i}" for i in st.session_state['items_int']] + [f"food_{i}" for i in st.session_state['items_food']]
            
            for k in all_keys:
                if k not in st.session_state['item_data']: continue
                v = st.session_state['item_data'][k]
                is_err = v["status"] in ["異常あり", "要清掃", "お声あり"]
                if "その他 設備" in k and not is_err: continue
                label = k.replace("ext_","").replace("int_","").replace("food_","").replace("voice","お客様の声")
                d.text((50, curr_y), f"■ {label}", fill="black", font=f_text)
                d.text((800, curr_y), f"[{v['status']}]", fill=("red" if is_err else "green"), font=f_text)
                curr_y += 35
                if is_err:
                    d.text((80, curr_y), f"詳細: {v['detail']}", fill="black", font=f_text)
                    curr_y += 40
                    if v.get("image"):
                        try:
                            photo = Image.open(io.BytesIO(v["image"])); photo.thumbnail((350, 350))
                            report.paste(photo, (80, curr_y)); curr_y += photo.height + 20
                        except: pass
                d.line([(50, curr_y), (950, curr_y)], fill="#eee"); curr_y += 30
            
            final = report.crop((0, 0, 1000, curr_y + 50))
            st.image(final, use_container_width=True)
            buf = io.BytesIO(); final.save(buf, format="PNG")
            st.download_button("報告書を保存", buf.getvalue(), "report.png", "image/png")
