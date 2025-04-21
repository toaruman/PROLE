import requests
from bs4 import BeautifulSoup
import re

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:110.0) Gecko/20100101 Firefox/110.0"
}

def test_html_parsing(shop_url):
    info_url = shop_url.rstrip("/") + "/info.html"
    print(f"🔍 アクセス中: {info_url}")

    try:
        r = requests.get(info_url, headers=HEADERS, timeout=15)
        r.raise_for_status()
        r.encoding = "euc-jp"  # 🔧 ここでエンコーディングを指定
        soup = BeautifulSoup(r.text, "html.parser")  # content → text に変更

        print("✅ HTML取得 & パース成功")

        # HTML先頭1000文字を表示（不要ならコメントアウト可）
        preview = soup.prettify()[:1000]
        print(f"📝 HTMLプレビュー（先頭1000文字）:\n{preview}")

        # dlタグが存在するか確認
        dl_tag = soup.find("dl")
        if dl_tag:
            print("✅ <dl> タグが見つかりました")
        else:
            print("❌ <dl> タグが見つかりません")
    except Exception as e:
        print(f"❌ 取得エラー: {e}")

if __name__ == "__main__":
    test_html_parsing("https://www.rakuten.co.jp/pelote")
