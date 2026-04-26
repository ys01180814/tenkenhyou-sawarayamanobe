import streamlit as st
from datetime import datetime
import PIL.Image as Image
import PIL.ImageDraw as ImageDraw
import PIL.ImageFont as ImageFont
import io
import os

# --- 1. 基本設定 ---
st.set_page_config(page_title="佐原山之辺店 点検表", layout="centered")

# フォント設定
FONT_PATH = "NotoSansJP-Regular.ttf"
def get_font(size):
    if os.path.exists(FONT_PATH):
        return ImageFont.truetype(FONT_PATH, size)
    return ImageFont.load_default()

# --- 2. データの管理 (ここが以前の安定していた仕組みです) ---
if 'map_data' not in st.session_state: st.session_state['map_data'] = None
if 'item_data' not in st.session_state: st.session_state['item_data'] = {}

# 初期の点検項目リスト
if 'items_ext' not in st.session_state:
    st.session_state['items_ext'] = ["駐車場・駐輪場", "サイバービジョン", "店外照明", "幟"]
if 'items_int' not in st.session_state:
    st.session_state['items_int'] = ["風除室", "店内照明", "カウンター", "喫煙ルーム", "休憩コーナー", "トイレ", "空調設備", "音響設備", "バックヤード", "誘導灯", "消火器"]

# --- 3. メイン画面表示 ---
st.title("店舗点検表")

# ヘッダー情報
now_date = datetime.now().strftime("%Y/%m/%d")
col_h1, col_h2 = st.columns([2, 1])
with col_h1: shop_name = st.text_input("店舗名", value="佐原山之辺店")
with col_h2: inspector = st.text_input("点検者", value="伊藤 康規")

# 📍 配置図エリア (ここが消えないように最優先で処理)
st.subheader("📍 店舗配置図")
if st.session_state['map_data'] is None:
    uploaded = st.file_uploader("配置図をアップロードしてください", type=['png', 'jpg', 'jpeg'])
    if uploaded:
        st.session_state['map_data'] = uploaded.read()
        st.rerun()
else:
    st.image(st.session_state['map_data'], use_container_width=True)
    if st.button("配置図を変更する"):
        st.session_state['map_data'] = None
        st.rerun()

# --- 4. 点検入力関数 ---
def render_item(label, key):
    st.markdown("---")
    col_l, col_r = st.columns([3, 1])
    with col_l: st.write(f"### ■ {label}")
    with col_r: keep = st.checkbox("データを保持", key=f"k_{key}")

    # 初期値設定
    if key not in st.session_state['item_data']:
        st.session_state['item_data'][key] = {"status": "異常なし", "detail": "", "image": None}
    
    # 保持しない場合はリセット (以前の挙動)
    if not keep:
        st.session_state['item_data'][key] = {"status": "異常なし", "detail": "", "image": None}

    dat = st.session_state['item_data'][key]
    status = st.radio("判定", ["異常なし", "異常あり", "要清掃"], 
                      index=["異常なし", "異常あり", "要清掃"].index(dat["status"]), 
                      key=f"r_{key}", horizontal=True)
    st.session_state['item_data'][key]["status"] = status

    if status != "異常なし":
        st.session_state['item_data'][key]["detail"] = st.text_area("詳細内容", value=dat["detail"], key=f"t_{key}")
        img_file = st.file_uploader("写真を添付", type=['png', 'jpg'], key=f"i_{key}")
        if img_file:
            st.session_state['item_data'][key]["image"] = img_file.read()

# セクション描画
st.header("【店外設備】")
for it in st.session_state['items_ext']: render_item(it, f"ext_{it}")

st.header("【店内設備】")
for it in st.session_state['items_int']: render_item(it, f"int_{it}")

# --- 5. 報告書生成 (分割保存対応) ---
st.divider()
st.subheader("📋 報告書の出力")
split_option = st.radio("生成モード", ["1枚にまとめる", "2枚に分割（前半・後半）"], horizontal=True)

def draw_report_content(draw, y, keys, img):
    font = get_font(28)
    for k in keys:
        if k not in st.session_state['item_data']: continue
        v = st.session_state['item_data'][k]
        is_err = v["status"] != "異常なし"
        label = k.split("_")[-1]
        
        draw.text((50, y), f"■ {label}", fill="black", font=font)
        draw.text((800, y), f"[{v['status']}]", fill=("red" if is_err else "green"), font=font)
        y += 40
        if is_err:
            draw.text((80, y), f"詳細: {v['detail']}", fill="black", font=font); y += 40
            if v["image"]:
                try:
                    p = Image.open(io.BytesIO(v["image"])); p.thumbnail((400, 400))
                    img.paste(p, (80, y)); y += p.height + 20
                except: pass
        draw.line([(50, y), (950, y)], fill="#ccc"); y += 30
    return y

if st.button("👉 報告書を生成する"):
    if not st.session_state['map_data']:
        st.error("配置図がありません。")
    else:
        map_img = Image.open(io.BytesIO(st.session_state['map_data'])).convert("RGB")
        ext_keys = [f"ext_{i}" for i in st.session_state['items_ext']]
        int_keys = [f"int_{i}" for i in st.session_state['items_int']]
        
        if split_option == "1枚にまとめる":
            report = Image.new('RGB', (1000, 8000), 'white'); d = ImageDraw.Draw(report)
            d.text((50, 50), f"{shop_name} 点検報告書 ({now_date})", fill="black", font=get_font(40))
            # 配置図貼り付け
            mw, mh = 900, int(900 * map_img.height / map_img.width)
            report.paste(map_img.resize((mw, mh)), (50, 120))
            y = draw_report_content(d, 150 + mh, ext_keys + int_keys, report)
            final = report.crop((0, 0, 1000, y + 50))
            st.image(final)
            buf = io.BytesIO(); final.save(buf, format="PNG")
            st.download_button("報告書を保存 (1枚)", buf.getvalue(), "report.png")
            
        else:
            # 前半（店外）
            r1 = Image.new('RGB', (1000, 4000), 'white'); d1 = ImageDraw.Draw(r1)
            d1.text((50, 50), f"{shop_name} 点検報告書 (1/2)", fill="black", font=get_font(40))
            mw, mh = 900, int(900 * map_img.height / map_img.width)
            r1.paste(map_img.resize((mw, mh)), (50, 120))
            y1 = draw_report_content(d1, 150 + mh, ext_keys, r1)
            final1 = r1.crop((0, 0, 1000, y1 + 50))
            st.image(final1, caption="前半")
            buf1 = io.BytesIO(); final1.save(buf1, format="PNG")
            st.download_button("前半を保存", buf1.getvalue(), "report_p1.png")
            
            # 後半（店内）
            r2 = Image.new('RGB', (1000, 4000), 'white'); d2 = ImageDraw.Draw(r2)
            d2.text((50, 50), f"{shop_name} 点検報告書 (2/2)", fill="black", font=get_font(40))
            y2 = draw_report_content(d2, 120, int_keys, r2)
            final2 = r2.crop((0, 0, 1000, y2 + 50))
            st.image(final2, caption="後半")
            buf2 = io.BytesIO(); final2.save(buf2, format="PNG")
            st.download_button("後半を保存", buf2.getvalue(), "report_p2.png")
