import streamlit as st
from datetime import datetime
import PIL.Image as Image
import PIL.ImageDraw as ImageDraw
import PIL.ImageFont as ImageFont
import io
import os
import json
import textwrap
import base64
from streamlit.components.v1 import html

# =========================
# 0. 保存先設定
# =========================
APP_DIR = "app_data"
STATE_FILE = os.path.join(APP_DIR, "saved_state.json")
MAP_FILE = os.path.join(APP_DIR, "saved_map.bin")
FONT_PATH = "NotoSansJP-Regular.ttf"

os.makedirs(APP_DIR, exist_ok=True)

# =========================
# 1. 共通関数
# =========================
def get_font(size):
    if os.path.exists(FONT_PATH):
        return ImageFont.truetype(FONT_PATH, size)
    return ImageFont.load_default()

def image_bytes_to_b64(data):
    if not data:
        return None
    return base64.b64encode(data).decode("utf-8")

def b64_to_image_bytes(data):
    if not data:
        return None
    return base64.b64decode(data.encode("utf-8"))

def load_json_state():
    if not os.path.exists(STATE_FILE):
        return {}
    try:
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}

def save_json_state(data):
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def load_map_bytes():
    if os.path.exists(MAP_FILE):
        try:
            with open(MAP_FILE, "rb") as f:
                return f.read()
        except Exception:
            return None
    return None

def save_map_bytes(data):
    if data:
        with open(MAP_FILE, "wb") as f:
            f.write(data)

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

def paste_image_keep_orientation(base_img, image_bytes, x, y, max_w=350, max_h=350):
    if not image_bytes:
        return y
    try:
        photo = Image.open(io.BytesIO(image_bytes)).convert("RGB")
        original_w, original_h = photo.size
        ratio = min(max_w / original_w, max_h / original_h)
        new_w = max(1, int(original_w * ratio))
        new_h = max(1, int(original_h * ratio))
        photo = photo.resize((new_w, new_h))
        base_img.paste(photo, (x, y))
        return y + new_h + 25
    except Exception:
        return y

def default_item_record(default_status):
    return {
        "status": default_status,
        "save": False,
        "image": None,
        "detail": "",
        "pos": ""
    }

def default_other_issue_record():
    return {
        "save": False,
        "defect": "",
        "action": "",
        "image": None
    }

# =========================
# 2. 保存データ読み込み
# =========================
saved_data = load_json_state()

default_items_ext = ["駐車場・駐輪場", "サイバービジョン", "店外照明", "幟"]
default_items_int = [
    "風除室", "店内照明", "カウンター", "喫煙ルーム",
    "休憩コーナー", "トイレ", "空調設備", "音響設備",
    "バックヤード", "誘導灯", "消火器"
]
default_items_food = ["六九"]

# =========================
# 3. Streamlit基本設定
# =========================
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
.add-btn button {
    background-color: #FF8C00 !important;
    height: 2.5em !important;
}
.save-box {
    margin-top: -6px;
    margin-bottom: 8px;
}
</style>
""", unsafe_allow_html=True)

# =========================
# 4. session_state 初期化
# =========================
if "map_data" not in st.session_state:
    st.session_state["map_data"] = load_map_bytes()

if "item_data" not in st.session_state:
    st.session_state["item_data"] = {}

if "items_ext" not in st.session_state:
    st.session_state["items_ext"] = saved_data.get("items_ext", default_items_ext)

if "items_int" not in st.session_state:
    st.session_state["items_int"] = saved_data.get("items_int", default_items_int)

if "items_food" not in st.session_state:
    st.session_state["items_food"] = saved_data.get("items_food", default_items_food)

if "other_issue_list" not in st.session_state:
    loaded_other = saved_data.get("other_issue_list", [])
    restored_other = []
    for row in loaded_other:
        restored_other.append({
            "save": row.get("save", False),
            "defect": row.get("defect", ""),
            "action": row.get("action", ""),
            "image": b64_to_image_bytes(row.get("image"))
        })
    st.session_state["other_issue_list"] = restored_other if restored_other else [default_other_issue_record()]

if "show_add_ext" not in st.session_state:
    st.session_state["show_add_ext"] = False

if "show_add_int" not in st.session_state:
    st.session_state["show_add_int"] = False

if "last_report_png" not in st.session_state:
    st.session_state["last_report_png"] = None

if "last_report_image" not in st.session_state:
    st.session_state["last_report_image"] = None

# item_data 復元
if not st.session_state["item_data"]:
    loaded_item_data = saved_data.get("item_data", {})
    restored = {}
    for k, v in loaded_item_data.items():
        default_status = "お声なし" if k == "voice" else "異常なし"
        restored[k] = {
            "status": v.get("status", default_status),
            "save": v.get("save", False),
            "image": b64_to_image_bytes(v.get("image")),
            "detail": v.get("detail", ""),
            "pos": v.get("pos", "")
        }
    st.session_state["item_data"] = restored

# =========================
# 5. 永続化関数
# =========================
def persist_saved_content():
    persist_item_data = {}
    for key, value in st.session_state["item_data"].items():
        if value.get("save"):
            persist_item_data[key] = {
                "status": value.get("status"),
                "save": True,
                "image": image_bytes_to_b64(value.get("image")),
                "detail": value.get("detail", ""),
                "pos": value.get("pos", "")
            }

    persist_other_list = []
    for row in st.session_state["other_issue_list"]:
        if row.get("save"):
            persist_other_list.append({
                "save": True,
                "defect": row.get("defect", ""),
                "action": row.get("action", ""),
                "image": image_bytes_to_b64(row.get("image"))
            })

    data = {
        "items_ext": st.session_state["items_ext"],
        "items_int": st.session_state["items_int"],
        "items_food": st.session_state["items_food"],
        "item_data": persist_item_data,
        "other_issue_list": persist_other_list
    }
    save_json_state(data)

    if st.session_state.get("map_data"):
        save_map_bytes(st.session_state["map_data"])

# =========================
# 6. ヘッダー
# =========================
now_date = datetime.now().strftime("%Y/%m/%d")
col_h1, col_h2 = st.columns([2, 1])

with col_h1:
    shop_name = st.text_input("店舗名", value="佐原山之辺店")

with col_h2:
    inspector = st.text_input("点検者", value="伊藤 康規")

st.title("店舗点検表")

# =========================
# 7. 配置図
# =========================
st.subheader("店舗配置図")
uploaded_map = st.file_uploader("配置図をアップロード", type=["png", "jpg", "jpeg"], key="map_upload")

if uploaded_map:
    st.session_state["map_data"] = uploaded_map.read()
    save_map_bytes(st.session_state["map_data"])

if st.session_state["map_data"]:
    st.image(st.session_state["map_data"], caption="店舗配置図", use_container_width=True)

# =========================
# 8. 点検項目入力
# =========================
def render_check_item(label, key, is_voice=False):
    st.markdown("---")
    st.write(f"### ■ {label}")

    options = ["お声なし", "お声あり"] if is_voice else ["異常なし", "異常あり", "要清掃"]
    default_status = options[0]

    if key not in st.session_state["item_data"]:
        st.session_state["item_data"][key] = default_item_record(default_status)

    current = st.session_state["item_data"][key]

    status = st.radio(
        "状態",
        options,
        index=options.index(current.get("status", default_status)) if current.get("status", default_status) in options else 0,
        key=f"r_{key}",
        horizontal=True,
        label_visibility="collapsed"
    )
    st.session_state["item_data"][key]["status"] = status

    save_flag = st.checkbox(
        "保存",
        value=current.get("save", False),
        key=f"save_{key}"
    )
    st.session_state["item_data"][key]["save"] = save_flag

    if status in ["異常あり", "要清掃", "お声あり"]:
        img_file = st.file_uploader(
            f"{label}の写真を添付",
            type=["png", "jpg", "jpeg"],
            key=f"img_{key}"
        )
        if img_file:
            st.session_state["item_data"][key]["image"] = img_file.read()

        detail = st.text_area(
            "詳細内容",
            value=st.session_state["item_data"][key].get("detail", ""),
            key=f"t_{key}",
            placeholder="詳細を入力（音声入力可）"
        )
        st.session_state["item_data"][key]["detail"] = detail

        if not is_voice:
            pos = st.text_input(
                f"{label}の位置メモ",
                value=st.session_state["item_data"][key].get("pos", ""),
                key=f"p_{key}",
                placeholder="例：スロット側入口付近"
            )
            st.session_state["item_data"][key]["pos"] = pos

def render_other_issue(index):
    issue = st.session_state["other_issue_list"][index]

    st.markdown("---")
    st.write(f"### ■ その他 設備不備 {index + 1}")

    save_flag = st.checkbox(
        "保存",
        value=issue.get("save", False),
        key=f"other_save_{index}"
    )
    st.session_state["other_issue_list"][index]["save"] = save_flag

    defect = st.text_area(
        "不備内容",
        value=issue.get("defect", ""),
        key=f"other_defect_{index}",
        placeholder="設備不備の内容を入力"
    )
    st.session_state["other_issue_list"][index]["defect"] = defect

    action = st.text_area(
        "対応状況",
        value=issue.get("action", ""),
        key=f"other_action_{index}",
        placeholder="対応状況を入力"
    )
    st.session_state["other_issue_list"][index]["action"] = action

    img_file = st.file_uploader(
        "その他 設備不備の写真を添付",
        type=["png", "jpg", "jpeg"],
        key=f"other_issue_img_{index}"
    )
    if img_file:
        st.session_state["other_issue_list"][index]["image"] = img_file.read()

# =========================
# 9. 入力セクション
# =========================
st.subheader("🗣️ お客様の声")
render_check_item("お客様の声", "voice", is_voice=True)

st.header("【店外設備】")
for item in st.session_state["items_ext"]:
    render_check_item(item, f"ext_{item}")

with st.container():
    st.markdown('<div class="add-btn">', unsafe_allow_html=True)
    if st.button("＋ 店外に項目を追加", key="ext_add_btn"):
        st.session_state["show_add_ext"] = True
    st.markdown("</div>", unsafe_allow_html=True)

if st.session_state.get("show_add_ext", False):
    new_item = st.text_input("追加する項目名（店外）", key="add_ext_name")
    if st.button("店外項目を確定追加", key="add_ext_confirm"):
        if new_item and new_item not in st.session_state["items_ext"]:
            st.session_state["items_ext"].append(new_item)
            st.session_state["show_add_ext"] = False
            persist_saved_content()
            st.rerun()

st.header("【店内設備】")
for item in st.session_state["items_int"]:
    render_check_item(item, f"int_{item}")

with st.container():
    st.markdown('<div class="add-btn">', unsafe_allow_html=True)
    if st.button("＋ 店内に項目を追加", key="int_add_btn"):
        st.session_state["show_add_int"] = True
    st.markdown("</div>", unsafe_allow_html=True)

if st.session_state.get("show_add_int", False):
    new_item = st.text_input("追加する項目名（店内）", key="add_int_name")
    if st.button("店内項目を確定追加", key="add_int_confirm"):
        if new_item and new_item not in st.session_state["items_int"]:
            st.session_state["items_int"].append(new_item)
            st.session_state["show_add_int"] = False
            persist_saved_content()
            st.rerun()

st.header("【食堂】")
for item in st.session_state["items_food"]:
    render_check_item(item, f"food_{item}")

st.header("【その他 設備不備】")
for i in range(len(st.session_state["other_issue_list"])):
    render_other_issue(i)

with st.container():
    st.markdown('<div class="add-btn">', unsafe_allow_html=True)
    if st.button("＋ その他 設備不備を追加", key="other_issue_add_btn"):
        st.session_state["other_issue_list"].append(default_other_issue_record())
        persist_saved_content()
        st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)

# 入力内容を都度保存
persist_saved_content()

# =========================
# 10. 報告書生成
# =========================
def generate_report_png():
    map_img = Image.open(io.BytesIO(st.session_state["map_data"])).convert("RGB")

    base_h = 12000
    w, h = 1000, base_h + map_img.height
    report = Image.new("RGB", (w, h), color="white")
    d = ImageDraw.Draw(report)

    f_title = get_font(60)
    f_text = get_font(28)
    f_bold = get_font(35)

    d.text((500, 80), "店舗点検報告書", fill="black", font=f_title, anchor="ms")
    d.text((50, 160), f"店舗名：{shop_name}", fill="black", font=f_text)
    d.text((50, 200), f"点検者：{inspector}    点検日：{now_date}", fill="black", font=f_text)

    mw = 900
    mh = int(mw * map_img.height / map_img.width)
    report.paste(map_img.resize((mw, mh)), (50, 250))

    curr_y = 300 + mh
    d.text((50, curr_y), "【点検詳細結果】", fill="black", font=f_bold)
    curr_y += 70

    for k, v in st.session_state["item_data"].items():
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
                    d, f"詳細: {detail_text}", 80, curr_y, f_text,
                    fill="black", max_chars=38, line_spacing=8
                )

            if (label != "お客様の声") and pos_text:
                curr_y = draw_multiline_text(
                    d, f"位置: {pos_text}", 80, curr_y, f_text,
                    fill="black", max_chars=38, line_spacing=8
                )

            if v.get("image"):
                curr_y = paste_image_keep_orientation(
                    report, v["image"], 80, curr_y + 5, max_w=350, max_h=350
                )

        d.line([(50, curr_y), (950, curr_y)], fill="#dddddd")
        curr_y += 30

    for issue in st.session_state["other_issue_list"]:
        other_defect = issue.get("defect", "").strip()
        other_action = issue.get("action", "").strip()
        other_image = issue.get("image")

        if other_defect or other_action or other_image:
            d.text((50, curr_y), "■ その他 設備不備", fill="black", font=f_text)
            d.text((800, curr_y), "[記載あり]", fill="red", font=f_text)
            curr_y += 42

            if other_defect:
                curr_y = draw_multiline_text(
                    d, f"不備内容: {other_defect}", 80, curr_y, f_text,
                    fill="black", max_chars=38, line_spacing=8
                )

            if other_action:
                curr_y = draw_multiline_text(
                    d, f"対応状況:\n{other_action}", 80, curr_y, f_text,
                    fill="black", max_chars=38, line_spacing=8
                )

            if other_image:
                curr_y = paste_image_keep_orientation(
                    report, other_image, 80, curr_y + 5, max_w=350, max_h=350
                )

            d.line([(50, curr_y), (950, curr_y)], fill="#dddddd")
            curr_y += 30

    final_height = min(curr_y + 20, h)
    report = report.crop((0, 0, w, final_height))

    buf = io.BytesIO()
    report.save(buf, format="PNG")
    png_bytes = buf.getvalue()
    return report, png_bytes

# =========================
# 11. 生成してコピー
# =========================
st.divider()

if st.button("👉 報告書（画像）を生成してコピー"):
    if not st.session_state["map_data"]:
        st.error("配置図をアップロードしてください。")
    else:
        with st.spinner("画像を生成中..."):
            report_img, png_bytes = generate_report_png()
            st.session_state["last_report_image"] = report_img
            st.session_state["last_report_png"] = png_bytes

if st.session_state["last_report_image"] is not None:
    st.image(st.session_state["last_report_image"], use_container_width=True)

if st.session_state["last_report_png"] is not None:
    png_b64 = base64.b64encode(st.session_state["last_report_png"]).decode("utf-8")

    html(f"""
    <div style="margin-top:10px; margin-bottom:18px;">
      <button id="copyImageBtn"
        style="
          width:100%;
          height:3em;
          background:#16a34a;
          color:white;
          border:none;
          border-radius:10px;
          font-weight:bold;
          cursor:pointer;
        ">
        生成画像をクリップボードにコピー
      </button>
      <div id="copyMsg" style="margin-top:8px; font-weight:bold;"></div>
    </div>

    <script>
    const btn = document.getElementById("copyImageBtn");
    const msg = document.getElementById("copyMsg");
    const b64 = "{png_b64}";

    function b64toBlob(b64Data, contentType='image/png') {{
        const byteCharacters = atob(b64Data);
        const byteArrays = [];
        for (let offset = 0; offset < byteCharacters.length; offset += 512) {{
            const slice = byteCharacters.slice(offset, offset + 512);
            const byteNumbers = new Array(slice.length);
            for (let i = 0; i < slice.length; i++) {{
                byteNumbers[i] = slice.charCodeAt(i);
            }}
            const byteArray = new Uint8Array(byteNumbers);
            byteArrays.push(byteArray);
        }}
        return new Blob(byteArrays, {{type: contentType}});
    }}

    btn.addEventListener("click", async () => {{
        try {{
            const blob = b64toBlob(b64, 'image/png');
            await navigator.clipboard.write([
                new ClipboardItem({{'image/png': blob}})
            ]);
            msg.style.color = "green";
            msg.textContent = "コピーしました。別サイトでそのまま貼り付けできます。";
        }} catch (e) {{
            msg.style.color = "red";
            msg.textContent = "このブラウザ環境では自動コピーできません。別ブラウザ、または localhost / HTTPS 環境でお試しください。";
        }}
    }});
    </script>
    """, height=110)
