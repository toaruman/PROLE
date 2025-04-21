import requests
from bs4 import BeautifulSoup
import re

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
}

# テスト対象のURL
test_url = "https://www.rakuten.co.jp/pelote/info.html"

print(f"🔍 アクセス中: {test_url}")
try:
    r = requests.get(test_url, headers=HEADERS, timeout=15)
    r.encoding = 'euc-jp'  # ← 明示的に文字コード指定
    r.raise_for_status()
    soup = BeautifulSoup(r.text, 'html.parser')
    print("✅ HTML取得 & パース成功")

    dl_tag = soup.find("dl")
    if dl_tag:
        print("✅ <dl> タグが見つかりました")
        dt_tags = dl_tag.find_all("dt")
        for i, dt in enumerate(dt_tags[:5]):  # 上位5個まで
            print(f"📦 dt[{i}] = {dt.get_text(' ', strip=True)}")
    else:
        print("❌ <dl> タグが見つかりません")

except Exception as e:
    print(f"❌ エラー発生: {e}")
