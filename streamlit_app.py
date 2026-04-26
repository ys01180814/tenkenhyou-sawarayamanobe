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

# 固定パス
FONT_PATH = "NotoSansJP-Regular.ttf"
MAP_IMAGE_PATH = "map.png"

def get_font(size):
    if os.path.exists(FONT_PATH):
        return ImageFont.truetype(FONT_PATH, size)
    return ImageFont.load_default()

# --- 2. データ保持 ---
if 'item_data' not in st.session_state:
    st.session_state['item_data'] = {}

# 点検項目（「その他 設備」を追加）
ITEMS_EXT = ["駐車場・駐輪場", "サイバービジョン", "店外照明", "幟"]
ITEMS_INT = ["風除室", "店内照明", "カウンター", "喫煙ルーム", "休憩コーナー", "トイレ", "空調設備", "音響設備", "バックヤード", "誘導灯", "消火器", "その他 設備"]

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

# 📍 配置図
st.subheader("📍 店舗配置図")
if os.path.exists(MAP_IMAGE_PATH):
    st.image(MAP_IMAGE_PATH, use_container_width=True)
else:
    st.info("GitHubに 'map.png' をアップロードするとここに自動表示されます。")

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
    with col_r: keep = st.checkbox("データを保持", key=f"k_{key}")

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
        # 画像については一旦シンプルに
        img_file = st.file_uploader("写真を添付", type=['png', 'jpg'], key=f"i_{key}")
        if img_file:
            st.session_state['item_data'][key]["image"] = img_file.read()

st.header("【店外設備】")
for it in ITEMS_EXT: render_item(it, f"ext_{it}")
st.header("【店内設備】")
for it in ITEMS_INT: render_item(it, f"int_{it}")

# --- 6. 報告書生成 ---
st.divider()
mode = st.radio("生成モード", ["1枚にまとめる", "2枚に分割"], horizontal=True)

def draw_rows(draw, y, keys, img):
    f = get_font(28)
    for k in keys:
        if k not in st.session_state['item_data']: continue
        v = st.session_state['item_data'][k]
        is_err = v["status"] != "異常なし"
        label = k.split("_")[-1]
        draw.text((50, y), f"■ {label}", fill="black", font=f)
        draw.text((800, y), f"[{v['status']}]", fill=("red" if is_err else "green"), font=f)
        y += 40
        if is_err:
            draw.text((80, y), f"詳細: {v['detail']}", fill="black", font=f); y += 40
            if v["image"]:
                try:
                    p = Image.open(io.BytesIO(v["image"])); p.thumbnail((400, 400))
                    img.paste(p, (80, y)); y += p.height + 20
                except: pass
        draw.line([(50, y), (950, y)], fill="#eee"); y += 30
    return y

if st.button("👉 報告書を生成"):
    m_img = Image.open(MAP_IMAGE_PATH).convert("RGB") if os.path.exists(MAP_IMAGE_PATH) else Image.new('RGB', (900, 500), 'white')
    e_k = [f"ext_{i}" for i in ITEMS_EXT]
    i_k = [f"int_{i}" for i in ITEMS_INT]
    
    if mode == "1枚にまとめる":
        rep = Image.new('RGB', (1000, 8000), 'white'); d = ImageDraw.Draw(rep)
        d.text((50, 50), f"{shop_name} 報告書 ({now_date})", fill="black", font=get_font(40))
        mw, mh = 900, int(900 * m_img.height / m_img.width); rep.paste(m_img.resize((mw, mh)), (50, 120))
        y = draw_rows(d, 150 + mh, e_k + i_k, rep)
        res = rep.crop((0, 0, 1000, y + 50)); st.image(res)
        buf = io.BytesIO(); res.save(buf, "PNG"); st.download_button("報告書を保存", buf.getvalue(), "report.png")
    else:
        # 前半
        r1 = Image.new('RGB', (1000, 4000), 'white'); d1 = ImageDraw.Draw(r1)
        d1.text((50, 50), f"{shop_name} 報告書(1/2)", fill="black", font=get_font(40))
        mw, mh = 900, int(900 * m_img.height / m_img.width); r1.paste(m_img.resize((mw, mh)), (50, 120))
        y1 = draw_rows(d1, 150 + mh, e_k, r1); res1 = r1.crop((0, 0, 1000, y1 + 50)); st.image(res1)
        b1 = io.BytesIO(); res1.save(b1, "PNG"); st.download_button("前半を保存", b1.getvalue(), "p1.png")
        # 後半
        r2 = Image.new('RGB', (1000, 4000), 'white'); d2 = ImageDraw.Draw(r2)
        d2.text((50, 50), f"{shop_name} 報告書(2/2)", fill="black", font=get_font(40))
        y2 = draw_rows(d2, 120, i_k, r2); res2 = r2.crop((0, 0, 1000, y2 + 50)); st.image(res2)
        b2 = io.BytesIO(); res2.save(b2, "PNG"); st.download_button("後半を保存", b2.getvalue(), "p2.png")
