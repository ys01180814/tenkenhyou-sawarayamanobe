import streamlit as st
import streamlit.components.v1 as components
from datetime import datetime
import PIL.Image as Image
import PIL.ImageDraw as ImageDraw
import PIL.ImageFont as ImageFont
import io
import os

# --- 0. 設定とフォントの読み込み ---
FONT_PATH = "NotoSansJP-Regular.ttf"

def get_font(size):
    if os.path.exists(FONT_PATH):
        return ImageFont.truetype(FONT_PATH, size)
    return ImageFont.load_default()

# --- 1. アプリの基本設定とCSS ---
st.set_page_config(page_title="店舗点検表", layout="centered")

st.markdown("""
    <style>
    .stApp { background-color: white !important; color: #000000 !important; }
    input, textarea, [data-baseweb="select"] > div {
        background-color: #ffffff !important;
        color: #000000 !important;
        border: 2px solid #000000 !important;
    }
    label, p, span, .stMarkdown {
        color: #000000 !important;
        font-weight: 900 !important;
    }
    .stButton button {
        width: 100%;
        background-color: #ffffff !important;
        color: #000000 !important;
        border: 2px solid #000000 !important;
        font-weight: bold !important;
        border-radius: 8px !important;
    }
    .speech-btn {
        background-color: #ffffff;
        border: 2px solid #000000;
        border-radius: 8px;
        padding: 5px 15px;
        font-weight: bold;
        cursor: pointer;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 2. データの保持と項目設定 ---
if 'map_data' not in st.session_state: st.session_state['map_data'] = None
if 'item_data' not in st.session_state: st.session_state['item_data'] = {}
if 'items_ext' not in st.session_state: 
    st.session_state['items_ext'] = ["駐車場・駐輪場", "サイバービジョン", "店外照明", "幟"]
if 'items_int' not in st.session_state: 
    st.session_state['items_int'] = ["風除室", "店内照明", "カウンター", "喫煙ルーム", "休憩コーナー", "トイレ", "空調設備", "音響設備", "バックヤード", "誘導灯", "消火器"]
if 'items_food' not in st.session_state: 
    st.session_state['items_food'] = ["六九", "その他 設備"]

# モード管理フラグ
for key in ['show_add_ext', 'show_edit_ext', 'show_add_int', 'show_edit_int']:
    if key not in st.session_state: st.session_state[key] = False

# --- 3. 音声認識JavaScript ---
def speech_to_text_js(key):
    js_code = f"""
    <div id="speech-container-{key}">
        <button class="speech-btn" onclick="startRecognition('{key}')">🎤 声で詳細を入力</button>
        <p id="status-{key}" style="font-size:11px; color:gray; margin-top:5px;">タップして話すと詳細欄に入力されます</p>
    </div>
    <script>
    function startRecognition(key) {{
        const status = document.getElementById('status-' + key);
        const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
        if (!SpeechRecognition) {{ status.innerText = "ブラウザ非対応です"; return; }}

        const recognition = new SpeechRecognition();
        recognition.lang = 'ja-JP';
        recognition.onstart = () => {{ status.innerText = "音声認識中..."; status.style.color = "red"; }};
        recognition.onresult = (event) => {{
            const text = event.results[0][0].transcript;
            // 親フレームのTextareaを探して値をセット（StreamlitのDOM構造に依存）
            const textareas = window.parent.document.querySelectorAll('textarea');
            for (let ta of textareas) {{
                // 非常に簡易的な特定方法ですが、現在アクティブなセクションの入力を補助します
                if (ta.offsetParent !== null) {{
                    const start = ta.selectionStart;
                    const end = ta.selectionEnd;
                    ta.value = ta.value.substring(0, start) + text + ta.value.substring(end);
                    ta.dispatchEvent(new Event('input', {{ bubbles: true }}));
                    break;
                }}
            }}
            status.innerText = "入力完了: " + text;
            status.style.color = "green";
        }};
        recognition.onerror = () => {{ status.innerText = "エラーが発生しました"; }};
        recognition.start();
    }}
    </script>
    """
    components.html(js_code, height=80)

# --- 4. ヘッダー ---
now_date = datetime.now().strftime("%Y/%m/%d")
col_h1, col_h2 = st.columns([2, 1])
with col_h1:
    shop_name = st.text_input("店舗名", value="佐原山之辺店")
with col_h2:
    inspector = st.text_input("点検者", value="伊藤 康規")

st.title("店舗点検表")

# --- 5. 入力UI関数 ---
def render_check_item(label, key, is_voice=False, section_list=None, idx=None, is_edit_mode=False):
    st.markdown(f"---")
    col_label, col_keep = st.columns([3, 1])
    with col_label: st.write(f"### ■ {label}")
    with col_keep: st.checkbox("データを保持", key=f"keep_{key}", value=False)

    if is_edit_mode and section_list is not None and idx is not None:
        if st.button(f"「{label}」を削除", key=f"del_{key}"):
            section_list.pop(idx)
            if key in st.session_state['item_data']: del st.session_state['item_data'][key]
            st.rerun()

    options = ["お声なし", "お声あり"] if is_voice else ["異常なし", "異常あり", "要清掃"]
    if key not in st.session_state['item_data']:
        st.session_state['item_data'][key] = {"status": options[0], "image": None, "detail": "", "pos": ""}
    
    status = st.radio("状態", options, index=options.index(st.session_state['item_data'][key]["status"]), key=f"r_{key}", horizontal=True, label_visibility="collapsed")
    st.session_state['item_data'][key]["status"] = status
    
    if status in ["異常あり", "要清掃", "お声あり"]:
        img_file = st.file_uploader(f"{label}の写真を添付", type=['png', 'jpg', 'jpeg'], key=f"img_{key}")
        if img_file: st.session_state['item_data'][key]["image"] = img_file.read()

        # 音声入力
        speech_to_text_js(key)
        
        detail = st.text_area(f"詳細内容", value=st.session_state['item_data'][key].get("detail", ""), key=f"t_{key}")
        st.session_state['item_data'][key]["detail"] = detail
        
        # 「その他 設備」および「お客様の声」以外は位置メモを表示
        if not is_voice and label != "その他 設備":
            pos = st.text_input(f"{label}の位置メモ", value=st.session_state['item_data'][key].get("pos", ""), key=f"p_{key}")
            st.session_state['item_data'][key]["pos"] = pos

def render_action_area(section_list, add_flag_key, edit_flag_key, input_key):
    col1, col2 = st.columns(2)
    with col1:
        if st.button("項目追加", key=f"btn_add_ui_{input_key}"):
            st.session_state[add_flag_key] = not st.session_state[add_flag_key]
    with col2:
        if st.button("項目修正", key=f"btn_edit_ui_{input_key}"):
            st.session_state[edit_flag_key] = not st.session_state[edit_flag_key]
    if st.session_state[add_flag_key]:
        new_name = st.text_input("項目名を入力", key=f"input_{input_key}")
        if st.button("確定", key=f"confirm_{input_key}"):
            if new_name:
                section_list.append(new_name)
                st.session_state[add_flag_key] = False
                st.rerun()

# 各セクション描画
st.subheader("🗣️ お客様の声")
render_check_item("お客様の声", "voice", is_voice=True)

st.header("【店外設備】")
for i, item in enumerate(st.session_state['items_ext']):
    render_check_item(item, f"ext_{item}", section_list=st.session_state['items_ext'] if i >= 4 else None, idx=i, is_edit_mode=st.session_state['show_edit_ext'])
render_action_area(st.session_state['items_ext'], 'show_add_ext', 'show_edit_ext', 'ext')

st.header("【店内設備】")
for i, item in enumerate(st.session_state['items_int']):
    render_check_item(item, f"int_{item}", section_list=st.session_state['items_int'] if i >= 11 else None, idx=i, is_edit_mode=st.session_state['show_edit_int'])
render_action_area(st.session_state['items_int'], 'show_add_int', 'show_edit_int', 'int')

st.header("【食堂・その他】")
for i, item in enumerate(st.session_state['items_food']):
    render_check_item(item, f"food_{item}")

# --- 6. 報告書生成ロジック ---
st.divider()
split_option = st.radio("生成方法", ["1枚にまとめる", "2枚に分ける"], horizontal=True)

def draw_report_content(draw, start_y, item_keys, report_img):
    curr_y = start_y
    f_text = get_font(28)
    for k in item_keys:
        if k not in st.session_state['item_data']: continue
        v = st.session_state['item_data'][k]
        is_err = v["status"] in ["異常あり", "要清掃", "お声あり"]
        
        # タイトル・項目を戻す：異常なしでも全項目を記載する
        label = k.replace("ext_","").replace("int_","").replace("food_","").replace("voice","お客様の声")
        draw.text((50, curr_y), f"■ {label}", fill="black", font=f_text)
        draw.text((800, curr_y), f"[{v['status']}]", fill=("red" if is_err else "green"), font=f_text)
        curr_y += 35
        
        if is_err:
            info_txt = f"詳細: {v.get('detail','')} ({v.get('pos','')})"
            draw.text((80, curr_y), info_txt, fill="black", font=f_text)
            curr_y += 40
            if v.get("image"):
                try:
                    photo = Image.open(io.BytesIO(v["image"]))
                    photo.thumbnail((350, 350))
                    report_img.paste(photo, (80, curr_y))
                    curr_y += photo.height + 20
                except: pass
        draw.line([(50, curr_y), (950, curr_y)], fill="#eee")
        curr_y += 30
    return curr_y

def create_base_report(map_data, title_suffix=""):
    map_img = Image.open(io.BytesIO(map_data)).convert("RGB")
    report = Image.new('RGB', (1000, 6000), color='white')
    d = ImageDraw.Draw(report)
    d.text((500, 80), f"{shop_name} 点検報告書{title_suffix}", fill="black", font=get_font(60), anchor="ms")
    d.text((50, 160), f"点検者：{inspector}    点検日：{now_date}", fill="black", font=get_font(28))
    mw = 900
    mh = int(mw * map_img.height / map_img.width)
    report.paste(map_img.resize((mw, mh)), (50, 250))
    return report, d, 300 + mh

if st.button("👉 報告書を生成"):
    if not st.session_state['map_data']: st.error("配置図をアップロードしてください")
    else:
        with st.spinner("生成中..."):
            ext_keys = ["voice"] + [f"ext_{i}" for i in st.session_state['items_ext']]
            int_food_keys = [f"int_{i}" for i in st.session_state['items_int']] + [f"food_{i}" for i in st.session_state['items_food']]
            if split_option == "1枚にまとめる":
                report, d, y = create_base_report(st.session_state['map_data'])
                y = draw_report_content(d, y, ext_keys + int_food_keys, report)
                final = report.crop((0, 0, 1000, y + 50))
                st.image(final, use_container_width=True)
                buf = io.BytesIO(); final.save(buf, format="PNG")
                st.download_button("保存", buf.getvalue(), "report.png", "image/png")
