import streamlit as st
import pandas as pd
import time
import re
import requests
from bs4 import BeautifulSoup

st.title("楽天 info.html 抽出ツール")

uploaded_file = st.file_uploader("楽天ショップリストCSVをアップロード", type="csv")

if uploaded_file is not None:
    df = pd.read_csv(uploaded_file)
    st.success(f"読み込まれた件数: {len(df)} 件")

    if st.button("抽出開始"):
        results = []
        progress_bar = st.progress(0)
        status_text = st.empty()

        for i, row in enumerate(df.itertuples(), 1):
            info_url = getattr(row, 'info_url', '')
            company_name, phone_number = "Not Found", "Not Found"

            try:
                r = requests.get(info_url, timeout=10, headers={
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
                })
                r.encoding = r.apparent_encoding
                soup = BeautifulSoup(r.text, 'html.parser')

                dl_tag = soup.find("dl")
                if dl_tag:
                    dt_tags = dl_tag.find_all("dt")
                    for dt in dt_tags:
                        dt_text = dt.get_text(" ", strip=True)
                        pattern = r'([\s\S]{0,30}株式会社[\s\S]{0,30})(?=〒|TEL:|FAX:|代表者:|店舗運営責任者:|店舗セキュリティ責任者:|購入履歴|$)'
                        match = re.search(pattern, dt_text)
                        if match:
                            company_name = match.group(1).strip()
                            break

                tel_elem = soup.find(string=re.compile("TEL:"))
                if tel_elem:
                    match = re.search(r'TEL:\s*([\d\-]+)', tel_elem)
                    if match:
                        phone_number = match.group(1)

            except Exception as e:
                pass

            results.append({
                "shop_url": getattr(row, 'shop_url', ''),
                "info_url": info_url,
                "company_name": company_name,
                "telephone": phone_number
            })

            progress_bar.progress(i / len(df))
            status_text.text(f"{i} / {len(df)} 件処理中…")

        status_text.success("✅ 全件処理が完了しました")
        result_df = pd.DataFrame(results)
        st.dataframe(result_df)

        csv = result_df.to_csv(index=False).encode('utf-8-sig')
        st.download_button(
            label="CSVをダウンロード",
            data=csv,
            file_name="extracted_info.csv",
            mime="text/csv"
        )