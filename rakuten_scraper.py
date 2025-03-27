#!/usr/bin/env python
# coding: utf-8

# In[31]:


import requests
import time
import datetime
import random
from bs4 import BeautifulSoup
import os
import sys
import re
import csv
from urllib.parse import urljoin

today = str(datetime.date.today())

def get_shop_id(shop_url):
    """
    ショップURL（例: https://www.rakuten.co.jp/SHOPID/ または https://www.rakuten.ne.jp/gold/SHOPID/）からSHOPIDを抽出します。
    """
    pattern = r'^https://www\.rakuten\.(?:co\.jp|ne\.jp)/(?:gold/)?([^/]+)/?$'
    m = re.match(pattern, shop_url)
    if m:
        return m.group(1)
    else:
        return None

class RakutenScraper:
    """
    楽天のカテゴリページや検索結果ページから再帰的にリンクを収集し、
    商品ページURLやショップページURLからショップURLを抽出するサンプルクラスです。
    """
    def __init__(self, base_url):
        self.base_url = base_url
        self.master_list = []        # 収集した全リンク
        self.item_page_list = []     # 楽天の商品ページURLのみ
        self.shop_url_list = set()   # 重複排除済みショップURL

    def simple_request(self, url, first=False):
        """
        指定されたURLのページから <a> タグの href を収集し、self.master_list に追加します。
        first=True の場合、初回に取得したリンクリストを返します。
        """
        print(f"アクセス中: {url} | 既存リンク数: {len(self.master_list)}")
        try:
            r = requests.get(url, timeout=(30.0, 47.5))
        except requests.exceptions.RequestException:
            return False

        if r.status_code == 200 and 'text/html' in r.headers.get('Content-Type', ''):
            soup = BeautifulSoup(r.content, 'html.parser')
            atag_list = soup.find_all('a')
            if first:
                unique_hrefs = []
                for a_tag in atag_list:
                    href = a_tag.get('href')
                    if href and (href not in self.master_list):
                        self.master_list.append(href)
                    if href and (href not in unique_hrefs):
                        unique_hrefs.append(href)
                return unique_hrefs
            else:
                for a_tag in atag_list:
                    href = a_tag.get('href')
                    if href and (href not in self.master_list):
                        self.master_list.append(href)
                return len(self.master_list)
        else:
            return False

    def get_item_url(self):
        """
        master_list の中から楽天の商品ページURL（例: https://item.rakuten.co.jp/SHOPID/商品ID/）を抽出し、
        self.item_page_list に再格納します。
        """
        pattern = r'^https://item\.rakuten\.co\.jp/([^/]+)/(\d+)/?$'
        self.item_page_list = []
        for url in self.master_list:
            if url and re.match(pattern, url):
                self.item_page_list.append(url)
        return self.item_page_list

    def extract_shop_urls(self, existing_shop_ids=None):
        """
        master_list の各URLからショップIDを抽出します。
        ショップURLとして利用可能なもの（例: https://www.rakuten.ne.jp/gold/SHOPID/）はそのまま、
        それ以外（例: 商品ページURLからの場合）は https://www.rakuten.co.jp/SHOPID/ の形式で生成します。
        既存のショップID（existing_shop_ids）に含まれていなければ追加します。
        """
        shop_urls = set()
        pattern_item = r'^https://item\.rakuten\.co\.jp/([^/]+)/(\d+)/?$'
        pattern_shop = r'^https://www\.rakuten\.(?:co\.jp|ne\.jp)/(?:gold/)?([^/]+)/?$'
        for url in self.master_list:
            m_shop = re.match(pattern_shop, url)
            if m_shop:
                shop_id = m_shop.group(1)
                if existing_shop_ids is None or shop_id not in existing_shop_ids:
                    # URL末尾のスラッシュを整形してそのまま利用
                    shop_urls.add(url.rstrip('/') + '/')
                continue
            m_item = re.match(pattern_item, url)
            if m_item:
                shop_id = m_item.group(1)
                shop_url = f"https://www.rakuten.co.jp/{shop_id}/"
                if existing_shop_ids is None or shop_id not in existing_shop_ids:
                    shop_urls.add(shop_url)
        self.shop_url_list = shop_urls
        return list(shop_urls)

def get_company_info_from_info_page(shop_url):
    """
    指定のショップURLに末尾の info.html を付与して企業情報ページにアクセスし、
    <dl> 内の <dt> タグからテキストを取得します。
    そのテキスト内で「株式会社」を含む部分を、余計な情報（〒, TEL, FAX, 代表者, etc.）が出現する直前まで抽出し企業名とします。
    ※「有限会社」が含まれるものは対象外です。
    また、TEL: に続く電話番号も抽出します。
    """
    info_url = shop_url.rstrip('/') + '/info.html'
    print(f"取得する企業情報ページ: {info_url}")
    
    try:
        response = requests.get(info_url, timeout=15)
        response.raise_for_status()
    except Exception as e:
        print("企業情報ページの取得に失敗しました:", e)
        return "Not Found", "Not Found"
    
    soup = BeautifulSoup(response.content, 'html.parser')
    company_name = "Not Found"
    phone_number = "Not Found"
    
    dl_tag = soup.find("dl")
    if dl_tag:
        dt_tags = dl_tag.find_all("dt")
        for dt in dt_tags:
            dt_text = dt.get_text(" ", strip=True)
            if not dt_text:
                continue
            # 正規表現で「株式会社」を含む部分を、〒やTEL等が出現する直前まで抽出
            pattern = r'(.*?株式会社.*?)(?=〒|TEL:|FAX:|代表者:|店舗運営責任者:|店舗セキュリティ責任者:|購入履歴|$)'
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

def crawl_pagination(scraper, start_url, max_pages=10):
    """
    start_url から始め、最大 max_pages ページまで巡回しながらリンクを収集します。
    HTML内の次ページリンクは、クラスが "item", "-next", "nextPage" を含む <a> タグで取得します。
    """
    current_url = start_url
    pages_crawled = 0
    while current_url and pages_crawled < max_pages:
        print(f"【ページ {pages_crawled+1} をクロール中】 {current_url}")
        # 現在のページのリンクを収集
        scraper.simple_request(current_url, first=True)
        time.sleep(random.uniform(1, 1.5))
        
        try:
            r = requests.get(current_url, timeout=15)
            r.raise_for_status()
            soup = BeautifulSoup(r.content, 'html.parser')
        except Exception as e:
            print("ページ遷移用リンクの取得に失敗:", e)
            break

        # 次ページリンクを CSS セレクターで取得 (クラス: item, -next, nextPage)
        next_link = soup.select_one("a.item.-next.nextPage")
        if next_link and next_link.get('href'):
            next_url = urljoin(current_url, next_link.get('href'))
            current_url = next_url
            pages_crawled += 1
        else:
            print("次のページが見つかりません。")
            break
    print(f"合計 {pages_crawled} ページをクロールしました。")

if __name__ == "__main__":
    # 既存の企業リスト（ショップURLのみ記載）CSVのファイルパス（相対パス）
    existing_companies_file = "./rakuten_scraping.csv"
    existing_shop_ids = set()
    if os.path.exists(existing_companies_file):
        print(f"既存の企業リスト {existing_companies_file} を読み込みます。")
        with open(existing_companies_file, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            for row in reader:
                shop_url = row.get("shop_url", "").strip()
                shop_id = get_shop_id(shop_url)
                if shop_id:
                    existing_shop_ids.add(shop_id)
        print(f"既存のショップID数: {len(existing_shop_ids)}")
    else:
        print("既存の企業リストが見つかりません。")

    print("例: https://www.rakuten.co.jp/category/110729/ または https://search.rakuten.co.jp/search/mall/レディースファッション")
    # urls.txt からURLを読み込んでループ処理
    with open("urls.txt", "r", encoding="utf-8") as f:
        url_list = [line.strip() for line in f if line.strip()]

    for input_url in url_list:
        print(f"\n==== {input_url} のスクレイピングを開始 ====")

        scraper = RakutenScraper(input_url)
        max_pages = 5  # 必要に応じて変更
        crawl_pagination(scraper, input_url, max_pages)

        item_urls = scraper.get_item_url()
        print(f"\n最終的な商品ページURL数: {len(item_urls)}")

        shop_urls = scraper.extract_shop_urls(existing_shop_ids)
        print(f"取得した新規ショップURLの数: {len(shop_urls)}")

        results = []
        for shop_url in shop_urls:
            info_url = shop_url.rstrip('/') + '/info.html'
            company_name, telephone = get_company_info_from_info_page(shop_url)
            results.append({
                "shop_url": shop_url,
                "info_url": info_url,
                "company_name": company_name,
                "telephone": telephone
            })
            time.sleep(random.uniform(1, 2))

        # CSV出力用ディレクトリ作成
        csv_dir = "./csv_data/"
        if not os.path.exists(csv_dir):
            os.makedirs(csv_dir)

        now = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        filename = f"{now}-company_info.csv"
        output_path = os.path.join(csv_dir, filename)

        with open(output_path, 'w', newline='', encoding='utf-8-sig') as f:
            fieldnames = ["shop_url", "info_url", "company_name", "telephone"]
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for row in results:
                writer.writerow(row)

        print(f"\n--- CSV出力完了 ---\nファイル: {output_path}")


        # 既存リストへの新規ショップURLの追記（ショップIDで重複チェック）
        new_shops = {res["shop_url"] for res in results if get_shop_id(res["shop_url"]) not in existing_shop_ids}
        if new_shops:
            with open(existing_companies_file, 'a', newline='', encoding='utf-8-sig') as f:
                writer = csv.DictWriter(f, fieldnames=["shop_url"])
                for shop in new_shops:
                    writer.writerow({"shop_url": shop})
            print(f"\n--- 新規ショップURLを既存企業リストに追加しました ---\nファイル: {existing_companies_file}")
        else:
            print("新しいショップURLは見つかりませんでした。")

        print("処理が完了しました。")
