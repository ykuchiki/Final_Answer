import requests
import pandas as pd
import re
from bs4 import BeautifulSoup
import time

# ユーザーエージェントの設定
headers = {
    "User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                   "AppleWebKit/537.36 (KHTML, like Gecko) "
                   "Chrome/120.0.0.0 Safari/537.36")
}

# 一覧ページの基本URL（1ページ目）
base_url = "https://r.gnavi.co.jp/city/kumamoto/cwtav8620100/rs/"

# 出力用データリスト
data_list = []
page = 1

while len(data_list) < 50:
    res = requests.get(base_url, headers=headers)
    
    soup = BeautifulSoup(res.text, "html.parser")
    # 店舗カードの抽出（class="style_restaurant__SeIVn"）
    restaurant_cards = soup.find_all("div", class_="style_restaurant__SeIVn")
    print("ページ", page, "で取得したカード数:", len(restaurant_cards))
    
    if not restaurant_cards:
        print("店舗カードが見つからなかったため、ループを終了します。")
        break

    # 各店舗カードから、一覧ページに表示されている情報を抽出する
    for i, card in enumerate(restaurant_cards, start=1):
        # 出力用辞書（CSVのカラムに対応）
        shop = {
            "店舗名": "",
            "電話番号": "",
            "メールアドレス": "",
            "都道府県": "",
            "市区町村": "",
            "番地": "",
            "建物名": "",
            "URL": "",
            "SSL": ""
        }
        # (1) 店舗名は、カード内の <h2 class="style_restaurantNameWrap__wvXSR"> にある
        name_tag = card.find("h2", class_="style_restaurantNameWrap__wvXSR")
        if name_tag:
            # 「PR」などのプレフィックスが含まれる場合は除去
            shop["店舗名"] = re.sub(r'^PR\s*', '', name_tag.get_text(strip=True))
            print(f"[ページ{page} カード{i}] 店舗名: {shop['店舗名']}")
        else:
            print(f"[ページ{page} カード{i}] 店舗名が見つかりませんでした。")
        
        # (2) その他の情報は一覧カード上には表示されていないため空
        shop["電話番号"] = ""
        shop["メールアドレス"] = ""
        shop["都道府県"] = ""
        shop["市区町村"] = ""
        shop["番地"] = ""
        shop["建物名"] = ""
        shop["URL"] = ""
        shop["SSL"] = ""
        
        data_list.append(shop)
        print(f"累計レコード数: {len(data_list)}")
        if len(data_list) >= 50:
            break
        
    # 「次ページ」ボタンを取得する（alt属性に「次」が含まれているかで判定）
    next_page_img = soup.find("img", class_="style_nextIcon__M_Me_", alt=re.compile("次"))
    if next_page_img:
        next_page_tag = next_page_img.find_parent("a")
        if next_page_tag and "href" in next_page_tag.attrs:
            next_page_url = next_page_tag["href"]
            base_url = "https://r.gnavi.co.jp" + next_page_url
            page += 1
            time.sleep(3)
        else:
            print("次ページリンクが見つからなかったため終了します。")
            break
    else:
        print("次ページのボタンが見つからなかったため終了します。")
        break
        

df = pd.DataFrame(data_list, columns=["店舗名", "電話番号", "メールアドレス", "都道府県", "市区町村", "番地", "建物名", "URL", "SSL"])
df.to_csv("1-1.csv", index=False, encoding="utf-8-sig")