import requests
import time
import datetime
import random
from bs4 import BeautifulSoup
import os
import re
import csv

# === 初期設定 ===
today = datetime.date.today().strftime("%Y-%m-%d")
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
}
APPLICATION_ID = "1028443959571093347"
HITS_PER_PAGE = 30
MAX_PAGES = 100

# === ショップID抽出関数 ===
def get_shop_id(shop_url):
    pattern = r'^https://www\.rakuten\.(?:co\.jp|ne\.jp)/(?:gold/)?([^/]+)/?$'
    m = re.match(pattern, shop_url)
    return m.group(1) if m else None

# === info.htmlから会社名・電話番号抽出 ===
def get_company_info_from_info_page(shop_url):
    for base in ["https://www.rakuten.co.jp", "https://www.rakuten.ne.jp/gold"]:
        info_url = f"{base}/{get_shop_id(shop_url)}/info.html"
        print(f"🔍 アクセス中: {info_url}")
        try:
            r = requests.get(info_url, headers=HEADERS, timeout=15)
            r.raise_for_status()
            soup = BeautifulSoup(r.content, 'html.parser')

            company_name = "Not Found"
            phone_number = "Not Found"

            dl_tag = soup.find("dl")
            if dl_tag:
                dt_tags = dl_tag.find_all("dt")
                for dt in dt_tags:
                    dt_text = dt.get_text(" ", strip=True)
                    if not dt_text:
                        continue
                    # 「株式会社」を含み、前後30文字までに限定（有限会社などは除外）
                    pattern = r'([\s\S]{0,30}株式会社[\s\S]{0,30})(?=〒|TEL:|FAX:|代表者:|店舗運営責任者:|店舗セキュリティ責任者:|購入履歴|$)'
                    match = re.search(pattern, dt_text)
                    if match:
                        company_name = match.group(1).strip()
                        break



            tel_elem = soup.find(text=re.compile("TEL:"))
            if tel_elem:
                match = re.search(r'TEL:\s*([\d\-]+)', tel_elem)
                if match:
                    phone_number = match.group(1)

            return company_name, phone_number
        except Exception:
            continue
    return "Not Found", "Not Found"

# === 商品検索API実行 ===
def get_product_urls_from_keyword(keyword, existing_shop_ids):
    print(f"🔍 キーワード: {keyword} から商品URLを取得中...")
    unique_shop_ids = set()
    item_urls = []

    for page in range(1, MAX_PAGES + 1):
        params = {
            'applicationId': APPLICATION_ID,
            'keyword': keyword,
            'format': 'json',
            'hits': HITS_PER_PAGE,
            'page': page
        }
        try:
            response = requests.get(
                'https://app.rakuten.co.jp/services/api/IchibaItem/Search/20220601',
                params=params,
                headers=HEADERS,
                timeout=10
            )
            response.raise_for_status()
            data = response.json()
            for item in data.get("Items", []):
                item_url = item["Item"]["itemUrl"]
                shop_id = item["Item"]["shopCode"]
                if shop_id not in existing_shop_ids and shop_id not in unique_shop_ids:
                    item_urls.append((item_url, shop_id))
                    unique_shop_ids.add(shop_id)
        except Exception as e:
            print(f"❌ 商品取得失敗: {e}")
            break
    print(f"✅ 商品URL取得数: {len(item_urls)}")
    return item_urls

# === 実行 ===
if __name__ == "__main__":
    existing_file = "rakuten_scraping.csv"
    existing_shop_ids = set()
    if os.path.exists(existing_file):
        with open(existing_file, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            for row in reader:
                shop_id = get_shop_id(row.get("shop_url", ""))
                if shop_id:
                    existing_shop_ids.add(shop_id)
        print(f"📄 既存のショップID数: {len(existing_shop_ids)}")

    # urls.txt からキーワード取得
    with open("urls.txt", "r", encoding="utf-8") as f:
        keywords = [line.strip() for line in f if line.strip()]

    new_shops = []
    for kw in keywords:
        product_data = get_product_urls_from_keyword(kw, existing_shop_ids)
        for item_url, shop_id in product_data:
            shop_url = f"https://www.rakuten.co.jp/{shop_id}/"
            company_name, tel = get_company_info_from_info_page(shop_url)
            new_shops.append({
                "shop_url": shop_url,
                "info_url": shop_url.rstrip('/') + "/info.html",
                "company_name": company_name,
                "telephone": tel
            })
            existing_shop_ids.add(shop_id)
            time.sleep(random.uniform(1, 1.5))

    # 書き出し
    if new_shops:
        os.makedirs("csv_data", exist_ok=True)
        filename = f"csv_data/{today}_company_info.csv"
        with open(filename, "w", newline='', encoding="utf-8-sig") as f:
            writer = csv.DictWriter(f, fieldnames=["shop_url", "info_url", "company_name", "telephone"])
            writer.writeheader()
            writer.writerows(new_shops)
        print(f"💾 出力完了: {filename}")

        # 既存リスト更新
        with open(existing_file, 'a', newline='', encoding='utf-8-sig') as f:
            writer = csv.DictWriter(f, fieldnames=["shop_url"])
            for row in new_shops:
                writer.writerow({"shop_url": row["shop_url"]})
        print(f"🆕 既存リストを更新しました（追加件数: {len(new_shops)}件）")
    else:
        print("⚠️ 新しいショップは見つかりませんでした。")
