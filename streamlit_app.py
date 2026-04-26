import streamlit as st
import os
import pandas as pd
from datetime import datetime
from PIL import Image

# 1. 保存用設定（アップロード画像用）
SAVE_DIR = "saved_images"
if not os.path.exists(SAVE_DIR):
    os.makedirs(SAVE_DIR)

# 2. 配置図のパス設定
MAP_FILE = "map.png"

# ページ設定
st.set_page_config(page_title="店舗点検アプリ", layout="centered")

# デザイン調整
st.markdown("""
    <style>
    .report-box {
        background-color: #ffffff;
        color: #000000;
        padding: 20px;
        border: 1px solid #ddd;
    }
    .status-normal { color: #28a745; font-weight: bold; }
    .status-error { color: #dc3545; font-weight: bold; }
    .stButton button { width: 100%; }
    </style>
    """, unsafe_allow_html=True)

def main():
    st.title("📋 店舗点検表")

    # --- 店舗配置図表示 ---
    st.subheader("📍 店舗配置図")
    if os.path.exists(MAP_FILE):
        st.image(MAP_FILE, use_container_width=True, caption="店舗配置図 (map.png)")
    else:
        st.error(f"エラー: {MAP_FILE} が見つかりません。リポジトリに画像があるか確認してください。")

    # 基本情報
    col1, col2 = st.columns(2)
    with col1:
        store_name = st.text_input("店舗名", value="佐原山之辺店")
    with col2:
        inspector = st.text_input("点検者", value="伊藤 康規")

    # --- 点検項目定義 ---
    sections = {
        "【お客様の声・その他】": ["お客様の声", "六九", "その他設備"],
        "【店外設備】": ["駐車場・駐輪場", "サイバービジョン", "店外照明", "幟"],
        "【店内設備】": ["風除室", "店内照明", "カウンター", "喫煙ルーム", "休憩コーナー", "トイレ", "空調設備", "音響設備", "バックヤード", "誘導灯", "消火器"]
    }

    results = {}

    for section, items in sections.items():
        st.markdown(f"### {section}")
        for item in items:
            # セッション状態を維持するためのユニークキー
            with st.container():
                st.write(f"**■ {item}**")
                
                # 判定選択
                options = ["異常なし", "異常あり", "要清掃", "お声あり"]
                # 「お客様の声」の場合は初期値を「お声あり」に寄せる等の調整が必要ならここで行う
                default_idx = 0
                res = st.radio(f"判定 ({item})", options, index=default_idx, horizontal=True, key=f"radio_{item}", label_visibility="collapsed")
                
                # 保持チェックボックス
                keep_data = st.checkbox("データを保持", key=f"keep_{item}", value=True)
                
                detail_text = ""
                image_path = os.path.join(SAVE_DIR, f"{item}.png")

                # 「異常なし」以外の場合の詳細入力
                if res != "異常なし":
                    st.button(f"🎤 音声入力（詳細欄へ書き込み）", key=f"mic_{item}")
                    detail_text = st.text_area("詳細内容", key=f"text_{item}", placeholder="具体的な状況を入力してください")
                    uploaded_file = st.file_uploader("写真を添付", type=['png', 'jpg', 'jpeg'], key=f"img_{item}")
                    
                    # 画像の保存処理
                    if uploaded_file:
                        with open(image_path, "wb") as f:
                            f.write(uploaded_file.getbuffer())
                        st.success(f"{item}の画像を保存しました")
                    
                    # 保持されている画像の表示
                    if os.path.exists(image_path):
                        st.image(image_path, caption=f"現在の{item}画像", width=300)
                
                # 保持チェックがない場合にファイルを削除する
                elif not keep_data and os.path.exists(image_path):
                    os.remove(image_path)

                results[item] = {
                    "status": res,
                    "detail": detail_text,
                    "image": image_path if os.path.exists(image_path) else None
                }
            st.divider()

    # --- 報告書生成 ---
    st.subheader("📤 報告書出力")
    if st.button("✨ 報告書を生成（コピー用画像イメージ）"):
        # 報告書プレビュー
        st.markdown(f"""
        <div class="report-box">
            <h2 style='text-align: center;'>{store_name} 点検報告書</h2>
            <p style='text-align: center;'>点検者：{inspector} 　 点検日：{datetime.now().strftime('%Y/%m/%d')}</p>
        """, unsafe_allow_html=True)
        
        # 報告書内にも配置図を表示
        if os.path.exists(MAP_FILE):
            st.image(MAP_FILE, use_container_width=True)
        
        st.markdown("<hr>", unsafe_allow_html=True)
        
        for item, data in results.items():
            # 色分け表示
            status_color = "#28a745" if data['status'] == "異常なし" else "#dc3545"
            st.markdown(f"""
            <div style='display: flex; justify-content: space-between; border-bottom: 1px solid #eee; padding: 5px 0;'>
                <span style='color: black;'>■ {item}</span>
                <span style='color: {status_color}; font-weight: bold;'>[{data['status']}]</span>
            </div>
            """, unsafe_allow_html=True)
            
            if data['status'] != "異常なし":
                if data['detail']:
                    st.markdown(f"<p style='color: #333; margin-left: 20px; font-size: 0.9em;'>詳細: {data['detail']}</p>", unsafe_allow_html=True)
                if data['image']:
                    st.image(data['image'], width=300)
        
        st.markdown("</div>", unsafe_allow_html=True)
        st.info("💡 上記の報告書範囲をスクリーンショットするか、画像を長押しして保存・貼り付けしてください。")

if __name__ == "__main__":
    main()
