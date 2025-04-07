#!/usr/bin/env python
# coding: utf-8

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

# 現在日時（ファイル名用）
today = str(datetime.date.today())

# User-Agent ヘッダーを追加
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Accept-Language": "ja,en-US;q=0.9,en;q=0.8",
    "Referer": "https://www.rakuten.co.jp/",
    "DNT": "1"
}

def get_shop_id(shop_url):
    pattern = r'^https://www\.rakuten\.(?:co\.jp|ne\.jp)/(?:gold/)?([^/]+)/?$'
    m = re.match(pattern, shop_url)
    return m.group(1) if m else None

class RakutenScraper:
    def __init__(self, base_url):
        self.base_url = base_url
        self.master_list = []
        self.item_page_list = []
        self.shop_url_list = set()

    def simple_request(self, url, first=False):
        print(f"アクセス中: {url} | 既存リンク数: {len(self.master_list)}")
        try:
            r = requests.get(url, headers=HEADERS, timeout=(30.0, 47.5))
        except requests.exceptions.RequestException as e:
            print(f"リクエストエラー: {e}")
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
            print(f"ステータスコード: {r.status_code}, コンテンツタイプ: {r.headers.get('Content-Type', '')}")
            return False

    def get_item_url(self):
        pattern = r'^https://item\.rakuten\.co\.jp/([^/]+)/(+)/?$'
        self.item_page_list = [url for url in self.master_list if url and re.match(pattern, url)]
        return self.item_page_list

    def extract_shop_urls(self, existing_shop_ids=None):
        shop_urls = set()
        pattern_item = r'^https://item\.rakuten\.co\.jp/([^/]+)/(+)/?$'
        pattern_shop = r'^https://www\.rakuten\.(?:co\.jp|ne\.jp)/(?:gold/)?([^/]+)/?$'
        for url in self.master_list:
            m_shop = re.match(pattern_shop, url)
            if m_shop:
                shop_id = m_shop.group(1)
                if existing_shop_ids is None or shop_id not in existing_shop_ids:
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
    info_url = shop_url.rstrip('/') + '/info.html'
    print(f"取得する企業情報ページ: {info_url}")

    try:
        response = requests.get(info_url, headers=HEADERS, timeout=15)
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
    current_url = start_url
    pages_crawled = 0
    while current_url and pages_crawled < max_pages:
        print(f"【ページ {pages_crawled+1} をクロール中】 {current_url}")
        scraper.simple_request(current_url, first=True)
        time.sleep(random.uniform(3, 5))

        try:
            r = requests.get(current_url, headers=HEADERS, timeout=15)
            r.raise_for_status()
            soup = BeautifulSoup(r.content, 'html.parser')
        except Exception as e:
            print("ページ遷移用リンクの取得に失敗:", e)
            break

        next_link = soup.select_one("a.item.-next.nextPage")
        if next_link and next_link.get('href'):
            current_url = urljoin(current_url, next_link.get('href'))
            pages_crawled += 1
        else:
            print("次のページが見つかりません。")
            break
    print(f"合計 {pages_crawled} ページをクロールしました。")
