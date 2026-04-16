import streamlit as st
import pandas as pd
from datetime import datetime
import PIL.Image as Image
import PIL.ImageDraw as ImageDraw
from streamlit_clickable_images import clickable_images
import io
import base64

# アプリの基本設定（明るいテーマを強制）
st.set_page_config(page_title="佐原山之辺店 点検表", layout="centered")

# カスタムCSS（白ベース、大きなボタン、明るい配色）
st.markdown("""
    <style>
    /* 全体の背景を白に */
    .stApp { background-color: white; color: black; }
    /* 入力ウィジェットの文字色を黒に */
    .stTextInput input, .stTextArea textarea, .stSelectbox div { color: black !important; }
    /* タイトルやサブヘッダーの色 */
    h1, h2, h3 { color: #333; }
    /* ボタンを大きく、明るい緑に */
    .stButton button { width: 100%; height: 3.5em; font-size: 1.2em; background-color: #4CAF50; color: white; border: none; border-radius: 8px; margin-bottom: 15px; }
    .stButton button:hover { background-color: #45a049; }
    /* ラジオボタン（〇△×）を横並びで大きく */
    div[data-testid="stMarkdownContainer"] p { font-weight: bold; margin-bottom: 5px; }
    /* セクションごとの区切り線 */
    hr { border: 1px solid #ddd; }
    /* 画像コピー用の隠しエリア */
    #ststreamlit_app { background-color: white; padding: 20px; }
    </style>
    """, unsafe_allow_html=True)

# --- 1. タイトルと自動日時 ---
now = datetime.now().strftime("%Y/%m/%d %H:%M:%S")
st.title("佐原山之辺店 点検表")
st.subheader(f"点検日時：{now}")

# --- 2. 基本情報の管理（自動記憶） ---
if 'inspector' not in st.session_state:
    st.session_state['inspector'] = ""
inspector_name = st.text_input("点検者氏名", value=st.session_state['inspector'])
st.session_state['inspector'] = inspector_name

# --- 3. 店舗配置図の管理（自動保持） ---
st.subheader("店舗配置図")
if 'map_image' not in st.session_state:
    st.session_state['map_image'] = None
if 'pins' not in st.session_state:
    st.session_state['pins'] = {} # 項目ごとのピン位置を保存

uploaded_map = st.file_uploader("配置図をアップロード（横型、一度行うと保持されます）", type=['png', 'jpg', 'jpeg'])
if uploaded_map:
    st.session_state['map_image'] = uploaded_map

# 配置図を表示する関数（ピン付き）
def get_map_with_pins():
    if not st.session_state['map_image']:
        return None
    img = Image.open(st.session_state['map_image']).convert("RGB")
    draw = ImageDraw.Draw(img)
    # 登録されているすべてのピンを描画
    for item_key, pin in st.session_state['pins'].items():
        if pin:
            x, y = pin
            r = 15 # ピンの半径
            draw.ellipse((x-r, y-r, x+r, y+r), fill="red", outline="white", width=3)
    return img

# 表示用のマップ
mapped_img = get_map_with_pins()
if mapped_img:
    st.image(mapped_img, caption="現在の配置状況（赤い●が異常箇所）", use_container_width=True)

# --- 4. 点検項目の定義（動的追加に対応） ---
if 'items_ext' not in st.session_state:
    st.session_state['items_ext'] = ["駐車場・駐輪場", "サイバービジョン", "店外照明", "幟"]
if 'items_int' not in st.session_state:
    st.session_state['items_int'] = ["風除室", "店内照明", "カウンター", "喫煙ルーム", "休憩コーナー", "トイレ", "空調設備", "音響設備", "バックヤード", "誘導灯", "消火器"]
if 'items_food' not in st.session_state:
    st.session_state['items_food'] = ["六九"]

results = {}

# --- 5. お客様の声 ---
st.markdown("### 🗣️ お客様の声")
col_v1, col_v2 = st.columns([1, 3])
with col_v1:
    voice_res = st.radio("お客様の声", ["なし", "あり"], horizontal=False, label_visibility="collapsed", key="v_radio")
results["お客様の声"] = {"status": voice_res}
with col_v2:
    if voice_res == "あり":
        results["お客様の声"]["image"] = st.file_uploader("画像を添付", type=['png', 'jpg', 'jpeg'], key="voice_img")

st.divider()

# --- 6. 点検入力関数 ---
def render_check_item(label, section_key, show_clean=True):
    st.markdown(f"**{label}**")
    opts = ["異常なし", "異常あり", "要清掃"] if show_clean else ["異常なし", "異常あり"]
    
    # 3rd imageのイメージに合わせてボタン（radio）を配置
    col_r, col_d = st.columns([1, 2])
    with col_r:
        res = st.radio(label, opts, horizontal=False, label_visibility="collapsed", key=f"r_{label}")
    
    data = {"status": res}
    
    if res in ["異常あり", "要清掃"]:
        with col_d:
            data["detail"] = st.text_area(f"詳細（音声入力可）", key=f"text_{label}", height=68)
            
            # 写真添付の選択
            if st.checkbox("写真を添付する", key=f"check_img_{label}"):
                data["image"] = st.file_uploader(f"写真を撮影/選択", type=['png', 'jpg', 'jpeg'], key=f"img_{label}")
            
            # ★配置図へのピン立て機能（ clickable_images ライブラリ風の簡易実装）
            if st.session_state['map_image']:
                st.caption("👇配置図の該当箇所をタップしてピンを立ててください")
                # 画像をbase64に変換してクリック可能にする
                buffered = io.BytesIO()
                st.session_state['map_image'].seek(0)
                img_base64 = base64.b64encode(st.session_state['map_image'].read()).decode()
                
                # HTMLとJSを使ってクリック座標を取得する特殊な実装
                click_html = f"""
                    <img src="data:image/png;base64,{img_base64}" id="map_{label}" style="width:100%; cursor:crosshair;">
                    <script>
                    document.getElementById('map_{label}').onclick = function(e) {{
                        var rect = e.target.getBoundingClientRect();
                        var x = (e.clientX - rect.left) / rect.width * e.target.naturalWidth;
                        var y = (e.clientY - rect.top) / rect.height * e.target.naturalHeight;
                        window.parent.postMessage({{type: 'streamlit:set_widget_value', key: 'pin_{label}', value: [x, y]}}, '*');
                    }};
                    </script>
                """
                st.components.v1.html(click_html, height=150)
                
                # JSから受け取った座標をsession_stateに保存
                pin_pos = st.session_state.get(f'pin_{label}')
                if pin_pos:
                    st.session_state['pins'][label] = pin_pos
                    st.success(f"ピンを立てました (X:{int(pin_pos[0])}, Y:{int(pin_pos[1])})")
    else:
        # 異常なしになったらピンを消す
        if label in st.session_state['pins']:
            del st.session_state['pins'][label]
            
    return data

# --- 7. 各セクションの表示 ---
st.markdown("### 🚗 店外（店舗外観）")
for item in st.session_state['items_ext']:
    opts_clean = item not in ["幟", "サイバービジョン", "店外照明"]
    results[item] = render_check_item(item, "ext", show_clean=opts_clean)
# 項目追加ボタン（店外）
with st.expander("➕ 店外に項目を追加"):
    new_ext = st.text_input("新しい項目名（例：景品カウンター裏）", key="new_ext_text")
    if st.button("店外に追加", key="new_ext_btn"):
        if new_ext and new_ext not in st.session_state['items_ext']:
            st.session_state['items_ext'].append(new_ext)
            st.rerun()

st.divider()

st.markdown("### 🎰 店内設備")
for item in st.session_state['items_int']:
    opts_clean = item not in ["誘導灯", "消火器"]
    results[item] = render_check_item(item, "int", show_clean=opts_clean)
# 項目追加ボタン（店内）
with st.expander("➕ 店内に項目を追加"):
    new_int = st.text_input("新しい項目名（例：スロット島）", key="new_int_text")
    if st.button("店内に追加", key="new_int_btn"):
        if new_int and new_int not in st.session_state['items_int']:
            st.session_state['items_int'].append(new_int)
            st.rerun()

st.divider()

st.markdown("### 🍴 食堂")
for item in st.session_state['items_food']:
    results[item] = render_check_item(item, "food", show_clean=True)

st.divider()

# --- 8. 報告書作成（画像化）セクション ---
st.subheader("報告書の作成")
if st.button("👉 点検表を画像として保存（報告用）"):
    # ここでHTML/CSSを使って、3rd imageのような綺麗な報告書画面をレンダリングし、
    # それを画像に変換する処理を行います。
    # (Streamlit単体での完全な画像化は高度なため、ここでは報告書内容を綺麗に表示し、
    #  店長がスクショを撮りやすい画面を作成します)
    
    st.balloons()
    st.success("報告書画面を作成しました。この画面をスクリーンショットして報告してください。")
    
    # 報告書エリア（白ベースで整形）
    report_area = st.container()
    with report_area:
        st.markdown(f"""
        <div style="background-color:white; padding:20px; border:2px solid #333; color:black;">
            <h2 style="text-align:center; color:black;">佐原山之辺店 点検報告書</h2>
            <p style="text-align:right; color:black;">日 時：{now}<br>点検者：{inspector_name}</p>
            <hr style="border:1px solid black;">
        </div>
        """, unsafe_allow_html=True)
        
        # ピン付き配置図をトップに配置
        if mapped_img:
            st.image(mapped_img, caption="店舗配置図（異常箇所：赤い●）", use_container_width=True)
            st.markdown("<hr style='border:1px solid black;'>", unsafe_allow_html=True)
            
        # 点検結果のレンダリング
        for k, v in results.items():
            status_color = "#f44336" if v['status'] in ["異常あり", "要清掃"] else "#4CAF50"
            st.markdown(f"""
            <div style="margin-bottom:15px; padding:10px; border-bottom:1px solid #eee; color:black;">
                <span style="font-size:1.1em; font-weight:bold; color:black;">■ {k}</span>
                <span style="float:right; background-color:{status_color}; color:white; padding:2px 10px; border-radius:10px;">{v['status']}</span>
            </div>
            """, unsafe_allow_html=True)
            
            # 詳細と写真がある場合
            if "detail" in v and v["detail"]:
                st.markdown(f"<div style='margin-left:20px; color:black; background-color:#f9f9f9; padding:5px;'>詳細: {v['detail']}</div>", unsafe_allow_html=True)
            if "image" in v and v["image"]:
                img_attached = Image.open(v["image"])
                st.image(img_attached, width=200) # 画像は少し小さめに表示
