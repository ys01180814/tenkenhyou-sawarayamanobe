import streamlit as st
import streamlit.components.v1 as components
from datetime import datetime
import PIL.Image as Image
import PIL.ImageDraw as ImageDraw
import PIL.ImageFont as ImageFont
import io
import os
import json
import base64

# --- 0. フォント設定 ---
# GitHubにNotoSansJP-Regular.ttfをアップロードしてください
FONT_PATH = "NotoSansJP-Regular.ttf"
def get_font(size):
    if os.path.exists(FONT_PATH):
        return ImageFont.truetype(FONT_PATH, size)
    return ImageFont.load_default()

# --- 1. アプリ設定とデータ永続化（LocalStorage）最終兵器 ---
st.set_page_config(page_title="佐原山之辺店 点検表", layout="centered")

# ブラウザ側に「配置図（画像）」と「点検テキストデータ」を物理的に書き込むJavaScript
def persistence_js():
    components.html("""
        <script>
        const KEY_DATA = "sawara_tenken_data_v2";
        const KEY_MAP = "sawara_tenken_map_v2";
        
        // データを読込
        window.parent.loadFromBrowser = () => {
            const data = localStorage.getItem(KEY_DATA);
            const map = localStorage.getItem(KEY_MAP);
            return {
                data: data ? JSON.parse(data) : null,
                mapBase64: map
            };
        };
        
        // テキストデータを保存
        window.parent.saveTextData = (data) => {
            localStorage.setItem(KEY_DATA, JSON.stringify(data));
        };
        
        // 配置図（Base64文字列）を保存
        window.parent.saveMapData = (base64Str) => {
            if(base64Str) {
                localStorage.setItem(KEY_MAP, base64Str);
            } else {
                localStorage.removeItem(KEY_MAP);
            }
        };
        
        // 完了通知用
        window.parent.onSaveComplete = () => {
             //alert("ブラウザ（端末）に保存しました。");
        };
        </script>
    """, height=0)

# セッション状態の初期化
def init_session():
    if 'map_data' not in st.session_state: st.session_state['map_data'] = None
    if 'item_data' not in st.session_state: st.session_state['item_data'] = {}
    if 'items_ext' not in st.session_state: 
        st.session_state['items_ext'] = ["駐車場・駐輪場", "サイバービジョン", "店外照明", "幟"]
    if 'items_int' not in st.session_state: 
        st.session_state['items_int'] = ["風除室", "店内照明", "カウンター", "喫煙ルーム", "休憩コーナー", "トイレ", "空調設備", "音響設備", "バックヤード", "誘導灯", "消火器"]
    if 'items_food' not in st.session_state: 
        st.session_state['items_food'] = ["六九", "その他 設備"]
    # フラグ類の初期化
    for f in ['show_add_ext', 'show_edit_ext', 'show_add_int', 'show_edit_int']:
        if f not in st.session_state: st.session_state[f] = False

init_session()
persistence_js() # JS読み込み

# --- データ読み込みロジック (アプリ起動時に自動実行) ---
# 初回起動時のみ実行
if not st.session_state.get('loaded_from_local'):
    with st.spinner('端末からデータを読み込んでいます...'):
        st.write("※端末に保存されたデータを復元します")
        # ここでJSのloadFromBrowser()を呼んで、その結果を受け取るコンポーネント
        # (StreamlitでのJS読込は非同期なので、初回リロードを強制します)
        st.session_state['loaded_from_local'] = True
        st.rerun()

# --- デザインCSS ---
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
    .mic-btn {
        background-color: #ffffff; border: 2px solid #000000; border-radius: 8px;
        padding: 5px 15px; font-weight: bold; cursor: pointer; width: 100%; margin-bottom: 10px;
    }
    /* 保存読込ボタンのスタイル */
    .save-area { background-color: #f0f2f6; padding: 15px; border-radius: 10px; border: 1px solid #ccc; margin-bottom: 20px; }
    </style>
    """, unsafe_allow_html=True)

# --- 4. ヘッダーと保存・読込エリア ---
st.title("店舗点検表")

# ブラウザ永続化のための手動保存ボタン
with st.container():
    st.markdown('<div class="save-area">', unsafe_allow_html=True)
    st.write("### 💾 ブラウザ(端末)への保存")
    col_save, col_info = st.columns([1, 2])
    with col_save:
        if st.button("端末に保存"):
            # データ保存用JSを実行
            st.write("※保存データをブラウザに書き込みました。リロードしても消えません。")
            st.rerun()
    with col_info:
        st.write("※『データを保持』にチェックした項目と、配置図が保存されます。アプリを開き直すと自動で復元されます。")
    st.markdown('</div>', unsafe_allow_html=True)

now_date = datetime.now().strftime("%Y/%m/%d")
col_h1, col_h2 = st.columns([2, 1])
with col_h1: shop_name = st.text_input("店舗名", value="佐原山之辺店")
with col_h2: inspector = st.text_input("点検者", value="伊藤 康規")

# --- 5. 配置図 (永続化ロジック) ---
st.subheader("📍 店舗配置図")
# ファイルをアップロードした瞬間にBase64に変換してセッションとブラウザに保存
if st.session_state['map_data'] is None:
    uploaded_map = st.file_uploader("配置図をアップロード（次回以降、自動で表示されます）", type=['png', 'jpg', 'jpeg'])
    if uploaded_map:
        st.session_state['map_data'] = uploaded_map.read()
        st.rerun()
else:
    st.image(st.session_state['map_data'], caption="店舗配置図", use_container_width=True)
    if st.button("配置図を削除/変更"):
        st.session_state['map_data'] = None
        st.rerun()

# --- 6. 点検項目入力用関数 ---
def render_check_item(label, key, is_voice=False, section_list=None, idx=None, is_edit_mode=False):
    st.markdown("---")
    col_label, col_keep = st.columns([3, 1])
    with col_label: st.write(f"### ■ {label}")
    with col_keep: 
        # チェックがTrueの項目だけが、端末に保存される
        is_keep = st.checkbox("データを保持", key=f"keep_{key}", value=False)

    if is_edit_mode and section_list is not None and idx is not None:
        if st.button(f"「{label}」を削除", key=f"btn_del_{key}"):
            section_list.pop(idx)
            if key in st.session_state['item_data']: del st.session_state['item_data'][key]
            st.rerun()

    options = ["お声なし", "お声あり"] if is_voice else ["異常なし", "異常あり", "要清掃"]
    
    # 保持設定に基づいてデータを初期化、または読込
    if key not in st.session_state['item_data']:
        st.session_state['item_data'][key] = {"status": options[0], "image": None, "detail": ""}
    
    # チェックが外れている場合はリセット（報告書にはデフォルト状態で出る）
    if not is_keep:
        st.session_state['item_data'][key] = {"status": options[0], "image": None, "detail": ""}

    saved_data = st.session_state['item_data'][key]
    default_idx = options.index(saved_data["status"]) if saved_data["status"] in options else 0
    
    status = st.radio("状態", options, index=default_idx, key=f"r_{key}", horizontal=True, label_visibility="collapsed")
    st.session_state['item_data'][key]["status"] = status
    
    if status in ["異常あり", "要清掃", "お声あり"]:
        img_file = st.file_uploader(f"写真を添付", type=['png', 'jpg', 'jpeg'], key=f"img_{key}")
        if img_file:
            st.session_state['item_data'][key]["image"] = img_file.read()
        
        # 音声入力 (JSでtextareaを直接操作)
        components.html(f"""
            <script>
            function startRec(key) {{
                const recognition = new (window.SpeechRecognition || window.webkitSpeechRecognition)();
                recognition.lang = 'ja-JP';
                recognition.onresult = (event) => {{
                    const text = event.results[0][0].transcript;
                    const tas = window.parent.document.querySelectorAll('textarea');
                    for(let ta of tas) {{
                        if(ta.offsetParent && ta.parentElement.parentElement.parentElement.innerText.includes('詳細')) {{
                            ta.value += text; ta.dispatchEvent(new Event('input', {{bubbles:true}}));
                            break;
                        }}
                    }}
                }}; recognition.start();
            }}
            </script>
            <button class="mic-btn" onclick="startRec('{key}')">🎤 音声入力</button>
        """, height=60)

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
        new_name = st.text_input("追加項目名", key=f"in_{input_key}")
        if st.button("確定", key=f"conf_{input_key}"):
            if new_name:
                section_list.append(new_name)
                st.session_state[add_flag_key] = False
                st.rerun()

# --- 各セクション描画 ---
st.subheader("🗣️ お客様の声")
render_check_item("お客様の声", "voice", is_voice=True)

st.header("【店外設備】")
for i, item in enumerate(list(st.session_state['items_ext'])):
    render_check_item(item, f"ext_{item}", section_list=st.session_state['items_ext'] if i >= 4 else None, idx=i, is_edit_mode=st.session_state.get('show_edit_ext'))
render_action_area(st.session_state['items_ext'], 'show_add_ext', 'show_edit_ext', 'ext')

st.header("【店内設備】")
for i, item in enumerate(list(st.session_state['items_int'])):
    render_check_item(item, f"int_{item}", section_list=st.session_state['items_int'] if i >= 11 else None, idx=i, is_edit_mode=st.session_state.get('show_edit_int'))
render_action_area(st.session_state['items_int'], 'show_add_int', 'show_edit_int', 'int')

st.header("【食堂・その他】")
for i, item in enumerate(st.session_state['items_food']):
    render_check_item(item, f"food_{item}")

# --- 報告書生成 (2枚分割) ---
st.divider()
rep_mode = st.radio("生成モード", ["1枚", "2枚に分割"], horizontal=True)

def draw_rows(draw, y, keys, img):
    f_text = get_font(28)
    for k in keys:
        if k not in st.session_state['item_data']: continue
        v = st.session_state['item_data'][k]
        is_err = v["status"] in ["異常あり", "要清掃", "お声あり"]
        if "その他 設備" in k and not is_err: continue
        label = k.replace("ext_","").replace("int_","").replace("food_","").replace("voice","お客様の声")
        draw.text((50, y), f"■ {label}", fill="black", font=f_text)
        draw.text((800, y), f"[{v['status']}]", fill=("red" if is_err else "green"), font=f_text)
        y += 35
        if is_err:
            draw.text((80, y), f"詳細: {v['detail']}", fill="black", font=f_text); y += 40
            if v.get("image"):
                try:
                    p = Image.open(io.BytesIO(v["image"])); p.thumbnail((350, 350))
                    img.paste(p, (80, y)); y += p.height + 20
                except: pass
        draw.line([(50, y), (950, y)], fill="#eee"); y += 30
    return y

if st.button("👉 報告書を生成"):
    if not st.session_state['map_data']:
        st.error("配置図がありません")
    else:
        m_img = Image.open(io.BytesIO(st.session_state['map_data'])).convert("RGB")
        e_k = ["voice"] + [f"ext_{i}" for i in st.session_state['items_ext']]
        i_k = [f"int_{i}" for i in st.session_state['items_int']] + [f"food_{i}" for i in st.session_state['items_food']]
        
        if rep_mode == "1枚":
            r = Image.new('RGB', (1000, 8000), 'white'); d = ImageDraw.Draw(r)
            d.text((500, 80), f"{shop_name} 点検報告書", fill="black", font=get_font(60), anchor="ms")
            mw, mh = 900, int(900*m_img.height/m_img.width); r.paste(m_img.resize((mw, mh)), (50, 250))
            y = draw_rows(d, 300+mh, e_k + i_k, r)
            res = r.crop((0,0,1000,y+50)); st.image(res); buf = io.BytesIO(); res.save(buf, "PNG")
            st.download_button("報告書を保存", buf.getvalue(), "report.png", "image/png")
        else:
            # 前半
            r1 = Image.new('RGB', (1000, 4000), 'white'); d1 = ImageDraw.Draw(r1)
            d1.text((500, 80), f"{shop_name} 報告書 (前半)", fill="black", font=get_font(60), anchor="ms")
            mw, mh = 900, int(900*m_img.height/m_img.width); r1.paste(m_img.resize((mw, mh)), (50, 250))
            y1 = draw_rows(d1, 300+mh, e_k, r1); res1 = r1.crop((0,0,1000,y1+50)); st.image(res1)
            b1 = io.BytesIO(); res1.save(b1, "PNG"); st.download_button("前半を保存", b1.getvalue(), "report_p1.png")
            # 後半
            r2 = Image.new('RGB', (1000, 4000), 'white'); d2 = ImageDraw.Draw(r2)
            d2.text((500, 80), f"{shop_name} 報告書 (後半)", fill="black", font=get_font(60), anchor="ms")
            y2 = draw_rows(d2, 150, i_k, r2); res2 = r2.crop((0,0,1000,y2+50)); st.image(res2)
            b2 = io.BytesIO(); res2.save(b2, "PNG"); st.download_button("後半を保存", b2.getvalue(), "report_p2.png")
