from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import pandas as pd
import re
import time

def parse_address(addr_str):
    """
    例: "〒860-0808 熊本県熊本市中央区手取本町5-1"  
    郵便番号を除去した後、正規表現で
      都道府県, 市区町村, 番地
    を抽出する。
    """
    addr_str = re.sub(r"〒\d{3}-\d{4}", "", addr_str).strip()
    pattern = r"^(?P<pref>.+?[県府都道])(?P<city>.+?[市])(?P<district>.*?[区])?(?P<addr>.*)$"
    m = re.match(pattern, addr_str)
    if m:
        pref = m.group("pref").strip()
        city = m.group("city").strip()
        district = m.group("district").strip() if m.group("district") else ""
        city_full = city + district if district else city
        addr_rest = m.group("addr").strip()
        return pref, city_full, addr_rest
    else:
        pattern2 = r'^(?P<pref>.+?[県府都道])(?P<city>.+?[市])(?P<addr>.*)$'
        m2 = re.match(pattern2, addr_str)
        if m2:
            pref = m2.group("pref").strip()
            city = m2.group("city").strip()
            addr = m2.group("addr").strip()
            return pref, city, addr
    return "", "", addr_str

# Selenium の設定（Chrome, ヘッドレスモード, ユーザーエージェントの指定）
options = Options()
options.add_argument("--headless")
options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                     "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
# driver = webdriver.Chrome(options=options)
service = Service(executable_path="Exercise_for_pool/python/ex1_web-scraping/chromedriver")
driver = webdriver.Chrome(service=service, options=options)


data_list = []
page = 1
base_url = "https://r.gnavi.co.jp/city/kumamoto/cwtav8620100/rs/"
driver.get(base_url)

while len(data_list) < 50:
    print(f"ページ {page} の読み込み")
    
    try:
        WebDriverWait(driver, 10).until(
            EC.presence_of_all_elements_located((By.CLASS_NAME, "style_restaurant__SeIVn"))
        )
    except Exception as e:
        print("店舗カード読み込み待機エラー:", e)
        break
    
    restaurant_cards = driver.find_elements(By.CLASS_NAME, "style_restaurant__SeIVn")
    print(f"ページ {page} で取得したカード数: {len(restaurant_cards)}")
    if not restaurant_cards:
        print("店舗カードが見つからなかったためループ終了")
        break
    
    # 各店舗カードを処理
    for i, card in enumerate(restaurant_cards, start=1):
        try:
            link_tag = card.find_element(By.CSS_SELECTOR, "a.style_titleLink__oiHVJ")
        except Exception as e:
            print(f"[ページ{page} カード{i}] リンクタグが見つかりません")
            continue
        detail_url = link_tag.get_attribute("href")
        print(f"[ページ{page} カード{i}] 詳細ページURL: {detail_url}")
        
        # 負荷対策
        time.sleep(3)
        driver.execute_script("window.open(arguments[0]);", detail_url)
        driver.switch_to.window(driver.window_handles[-1])
        
        try:
            info_div = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.ID, "info"))
            )
        except Exception as e:
            print(f"[ページ{page} カード{i}] infoブロック読み込み失敗: {detail_url}, {e}")
            driver.close()
            driver.switch_to.window(driver.window_handles[0])
            continue
        
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
        
        # (1) 店舗名抽出：<th>が「店名」→隣の<td>内の<p id="info-name">
        try:
            th_name = driver.find_element(By.XPATH, "//div[@id='info']//th[contains(text(),'店名')]")
            td_name = th_name.find_element(By.XPATH, "following-sibling::td")
            p_name = td_name.find_element(By.ID, "info-name")
            shop["店舗名"] = p_name.text.strip()
            print(f"[ページ{page} カード{i}] 店舗名: {shop['店舗名']}")
        except Exception as e:
            print(f"[ページ{page} カード{i}] 店舗名抽出エラー: {detail_url}, {e}")
        
        # (2) 電話番号抽出：<th>が「電話番号」→隣の<td>内の<span class="number">
        try:
            th_tel = driver.find_element(By.XPATH, "//div[@id='info']//th[contains(text(),'電話番号')]")
            td_tel = th_tel.find_element(By.XPATH, "following-sibling::td")
            span_tel = td_tel.find_element(By.XPATH, ".//span[contains(@class,'number')]")
            shop["電話番号"] = span_tel.text.strip()
            print(f"[ページ{page} カード{i}] 電話番号: {shop['電話番号']}")
        except Exception as e:
            print(f"[ページ{page} カード{i}] 電話番号抽出エラー: {detail_url}, {e}")
        
        # (3) メールアドレスは仕様上存在しないので空
        shop["メールアドレス"] = ""
        
        # (4) 住所抽出：<th>が「住所」→隣の<td>内の<span class="region">および<span class="locality">
        try:
            th_addr = driver.find_element(By.XPATH, "//div[@id='info']//th[contains(text(),'住所')]")
            td_addr = th_addr.find_element(By.XPATH, "following-sibling::td")
            try:
                region_span = td_addr.find_element(By.XPATH, ".//span[contains(@class,'region')]")
                region_text = region_span.text.strip()
                pref, city, addr = parse_address(region_text)
                shop["都道府県"] = pref
                shop["市区町村"] = city
                shop["番地"] = addr
                print(f"[ページ{page} カード{i}] 住所: {pref}, {city}, {addr}")
            except Exception as e:
                print(f"[ページ{page} カード{i}] region情報抽出エラー: {e}")
            try:
                locality_span = td_addr.find_element(By.XPATH, ".//span[contains(@class,'locality')]")
                shop["建物名"] = locality_span.text.strip()
                print(f"[ページ{page} カード{i}] 建物名: {shop['建物名']}")
            except Exception as e:
                shop["建物名"] = ""
        except Exception as e:
            print(f"[ページ{page} カード{i}] 住所抽出エラー: {detail_url}, {e}")
        
        # (5) 公式サイトの抽出：<th>が「お店のホームページ」→隣の<td>内の<a>のhref属性
        try:
            th_site = driver.find_element(By.XPATH, "//div[@id='info']//th[contains(text(),'お店のホームページ')]")
            td_site = th_site.find_element(By.XPATH, "following-sibling::td")
            a_site = td_site.find_element(By.XPATH, ".//a")
            site_url = a_site.get_attribute("href").strip()
            shop["URL"] = site_url
            shop["SSL"] = "TRUE" if site_url.startswith("https://") else "FALSE"
            print(f"[ページ{page} カード{i}] 公式サイト: {shop['URL']}, SSL: {shop['SSL']}")
        except Exception as e:
            print(f"[ページ{page} カード{i}] 公式サイトのURLを抽出できませんでした")
            shop["URL"] = ""
            shop["SSL"] = ""
        
        data_list.append(shop)
        print(f"累計レコード数: {len(data_list)}")
        
        driver.close()
        driver.switch_to.window(driver.window_handles[0])
        
        if len(data_list) >= 50:
            break

    # 次のページ(「>」ボタン)をクリック
    try:
        next_button = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, "//a[.//img[contains(@alt, '次')]]"))
        )
        driver.execute_script("arguments[0].click();", next_button)
        time.sleep(3)
        page += 1
    except Exception as e:
        print("次ページボタンが見つからない、またはクリックできない:", e)
        break

df = pd.DataFrame(data_list, columns=["店舗名", "電話番号", "メールアドレス", "都道府県", "市区町村", "番地", "建物名", "URL", "SSL"])
df.to_csv("1-2.csv", index=False, encoding="utf-8-sig")
driver.quit()