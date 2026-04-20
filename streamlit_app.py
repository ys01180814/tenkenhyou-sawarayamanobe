import streamlit as st
from datetime import datetime
import PIL.Image as Image
import PIL.ImageDraw as ImageDraw
import PIL.ImageFont as ImageFont
import io
import os
import textwrap

# --- 0. 設定とフォントの読み込み ---
FONT_PATH = "NotoSansJP-Regular.ttf"

def get_font(size):
    if os.path.exists(FONT_PATH):
        return ImageFont.truetype(FONT_PATH, size)
    return ImageFont.load_default()

# --- 文字折り返し描画用 ---
def draw_multiline_text(draw, text, x, y, font, fill="black", max_chars=38, line_spacing=12):
    if not text:
        return y

    lines = []
    for paragraph in str(text).split("\n"):
        wrapped = textwrap.wrap(paragraph, width=max_chars) if paragraph else [""]
        lines.extend(wrapped)

    for line in lines:
        draw.text((x, y), line, fill=fill, font=font)
        bbox = draw.textbbox((x, y), line, font=font)
        line_height = bbox[3] - bbox[1]
        y += line_height + line_spacing

    return y

# --- 1. アプリの基本設定とCSS ---
st.set_page_config(page_title="佐原山之辺店 点検表", layout="centered")

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
    div[data-testid="stRadio"] label p {
        color: #000000 !important;
        font-weight: bold !important;
    }
    .stButton button {
        width: 100%;
        height: 3em;
        background-color: #1E90FF;
        color: white;
        font-weight: bold;
        border-radius: 10px;
        margin-top: 10px;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 2. データの保持 ---
if 'map_data' not in st.session_state:
    st.session_state['map_data'] = None

if 'item_data' not in st.session_state:
    st.session_state['item_data'] = {}

if 'items_ext' not in st.session_state:
    st.session_state['items_ext'] = ["駐車場・駐輪場", "サイバービジョン", "店外照明", "幟"]

if 'items_int' not in st.session_state:
    st.session_state['items_int'] = [
        "風除室", "店内照明", "カウンター", "喫煙ルーム",
        "休憩コーナー", "トイレ", "空調設備", "音響設備",
        "バックヤード", "誘導灯", "消火器"
    ]

if 'items_food' not in st.session_state:
    st.session_state['items_food'] = ["六九"]

if 'other_issue' not in st.session_state:
    st.session_state['other_issue'] = {
        "defect": "",
        "action": "",
        "image": None
    }

# --- 3. ヘッダー ---
now_date = datetime.now().strftime("%Y/%m/%d")
col_h1, col_h2 = st.columns([2, 1])

with col_h1:
    shop_name = st.text_input("店舗名", value="佐原山之辺店")

with col_h2:
    inspector = st.text_input("点検者", value="伊藤 康規")

st.title("店舗点検表")

# --- 4. 配置図 ---
st.subheader("店舗配置図")
uploaded_map = st.file_uploader("配置図をアップロード", type=['png', 'jpg', 'jpeg'])

if uploaded_map:
    st.session_state['map_data'] = uploaded_map.read()

if st.session_state['map_data']:
    st.image(st.session_state['map_data'], caption="店舗配置図", use_container_width=True)

# --- 5. 通常点検項目入力関数 ---
def render_check_item(label, key, is_voice=False):
    st.markdown("---")
    st.write(f"### ■ {label}")

    options = ["お声なし", "お声あり"] if is_voice else ["異常なし", "異常あり", "要清掃"]
    status = st.radio("状態", options, key=f"r_{key}", horizontal=True, label_visibility="collapsed")

    if key not in st.session_state['item_data']:
        st.session_state['item_data'][key] = {
            "status": options[0],
            "image": None,
            "detail": "",
            "pos": ""
        }

    st.session_state['item_data'][key]["status"] = status

    if status in ["異常あり", "要清掃", "お声あり"]:
        img_file = st.file_uploader(
            f"{label}の写真を添付",
            type=['png', 'jpg', 'jpeg'],
            key=f"img_{key}"
        )
        if img_file:
            st.session_state['item_data'][key]["image"] = img_file.read()

        detail = st.text_area(
            "詳細内容",
            value=st.session_state['item_data'][key].get("detail", ""),
            key=f"t_{key}",
            placeholder="詳細を入力（音声入力可）"
        )
        st.session_state['item_data'][key]["detail"] = detail

        if not is_voice:
            pos = st.text_input(
                f"{label}の位置メモ",
                value=st.session_state['item_data'][key].get("pos", ""),
                key=f"p_{key}",
                placeholder="例：スロット側入口付近"
            )
            st.session_state['item_data'][key]["pos"] = pos

# --- 6. その他 設備不備入力関数 ---
def render_other_issue():
    st.markdown("---")
    st.header("【その他 設備不備】")

    defect = st.text_area(
        "不備内容",
        value=st.session_state['other_issue'].get("defect", ""),
        key="other_defect",
        placeholder="設備不備の内容を入力"
    )
    st.session_state['other_issue']["defect"] = defect

    action = st.text_area(
        "対応状況",
        value=st.session_state['other_issue'].get("action", ""),
        key="other_action",
        placeholder="対応状況を入力"
    )
    st.session_state['other_issue']["action"] = action

    img_file = st.file_uploader(
        "その他 設備不備の写真を添付",
        type=['png', 'jpg', 'jpeg'],
        key="other_issue_img"
    )
    if img_file:
        st.session_state['other_issue']["image"] = img_file.read()

# --- 入力セクション ---

# ① お客様の声
st.subheader("🗣️ お客様の声")
render_check_item("お客様の声", "voice", is_voice=True)

# ② 店外設備
st.header("【店外設備】")
for item in st.session_state['items_ext']:
    render_check_item(item, f"ext_{item}")

# ③ 店内設備
st.header("【店内設備】")
for item in st.session_state['items_int']:
    render_check_item(item, f"int_{item}")

# ④ 食堂
st.header("【食堂】")
for item in st.session_state['items_food']:
    render_check_item(item, f"food_{item}")

# ⑤ その他 設備不備
render_other_issue()

# --- 7. 報告書生成 ---
st.divider()

if st.button("👉 報告書(画像)を生成して保存"):
    if not st.session_state['map_data']:
        st.error("配置図をアップロードしてください。")
    else:
        with st.spinner("画像を生成中..."):
            map_img = Image.open(io.BytesIO(st.session_state['map_data'])).convert("RGB")

            # まずは大きめキャンバスを作成し、最後に必要な高さでcrop
            base_h = 7000
            w, h = 1000, base_h + map_img.height
            report = Image.new('RGB', (w, h), color='white')
            d = ImageDraw.Draw(report)

            f_title = get_font(60)
            f_text = get_font(28)
            f_bold = get_font(35)

            # ヘッダー
            d.text((500, 80), "店舗点検報告書", fill="black", font=f_title, anchor="ms")
            d.text((50, 160), f"店舗名：{shop_name}", fill="black", font=f_text)
            d.text((50, 200), f"点検者：{inspector}    点検日：{now_date}", fill="black", font=f_text)

            # 配置図貼り付け
            mw = 900
            mh = int(mw * map_img.height / map_img.width)
            report.paste(map_img.resize((mw, mh)), (50, 250))

            curr_y = 300 + mh
            d.text((50, curr_y), "【点検詳細結果】", fill="black", font=f_bold)
            curr_y += 70

            # 通常項目一覧
            for k, v in st.session_state['item_data'].items():
                label = k.replace("ext_", "").replace("int_", "").replace("food_", "").replace("voice", "お客様の声")

                d.text((50, curr_y), f"■ {label}", fill="black", font=f_text)

                is_err = v["status"] in ["異常あり", "要清掃", "お声あり"]
                color = "red" if is_err else "green"
                d.text((800, curr_y), f"[{v['status']}]", fill=color, font=f_text)
                curr_y += 42

                if is_err:
                    detail_text = v.get("detail", "").strip()
                    pos_text = v.get("pos", "").strip()

                    if detail_text:
                        curr_y = draw_multiline_text(
                            d,
                            f"詳細: {detail_text}",
                            80,
                            curr_y,
                            f_text,
                            fill="black",
                            max_chars=38,
                            line_spacing=8
                        )

                    if (not label == "お客様の声") and pos_text:
                        curr_y = draw_multiline_text(
                            d,
                            f"位置: {pos_text}",
                            80,
                            curr_y,
                            f_text,
                            fill="black",
                            max_chars=38,
                            line_spacing=8
                        )

                    if v.get("image"):
                        try:
                            photo = Image.open(io.BytesIO(v["image"])).convert("RGB")
                            photo.thumbnail((350, 350))
                            report.paste(photo, (80, curr_y + 5))
                            curr_y += photo.height + 25
                        except Exception:
                            pass

                d.line([(50, curr_y), (950, curr_y)], fill="#dddddd")
                curr_y += 30

            # その他 設備不備
            other_defect = st.session_state['other_issue'].get("defect", "").strip()
            other_action = st.session_state['other_issue'].get("action", "").strip()
            other_image = st.session_state['other_issue'].get("image")

            if other_defect or other_action or other_image:
                d.text((50, curr_y), "■ その他 設備不備", fill="black", font=f_text)
                d.text((800, curr_y), "[記載あり]", fill="red", font=f_text)
                curr_y += 42

                if other_defect:
                    curr_y = draw_multiline_text(
                        d,
                        f"不備内容: {other_defect}",
                        80,
                        curr_y,
                        f_text,
                        fill="black",
                        max_chars=38,
                        line_spacing=8
                    )

                if other_action:
                    curr_y = draw_multiline_text(
                        d,
                        f"対応状況: {other_action}",
                        80,
                        curr_y,
                        f_text,
                        fill="black",
                        max_chars=38,
                        line_spacing=8
                    )

                if other_image:
                    try:
                        photo = Image.open(io.BytesIO(other_image)).convert("RGB")
                        photo.thumbnail((350, 350))
                        report.paste(photo, (80, curr_y + 5))
                        curr_y += photo.height + 25
                    except Exception:
                        pass

                d.line([(50, curr_y), (950, curr_y)], fill="#dddddd")
                curr_y += 30

            # 最後の記載位置に合わせて下余白をカット
            final_height = min(curr_y + 20, h)
            report = report.crop((0, 0, w, final_height))

            st.image(report, use_container_width=True)

            buf = io.BytesIO()
            report.save(buf, format="PNG")
            st.download_button(
                "この点検画像を保存",
                buf.getvalue(),
                f"点検表_{now_date}.png",
                "image/png"
            )
