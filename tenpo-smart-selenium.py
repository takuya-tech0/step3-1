from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager
import time

# スクレイピングするページ数
max_page = 10

# TemposmartのベースURL
base_url = "https://www.temposmart.jp/estates"

# 相対URLにページ番号を追加するプレースホルダを含む
relative_url = "?prefecture_ids%5B0%5D=13&child_current_purpose%5B0%5D=194&child_current_purpose%5B1%5D=198&child_available_purpose%5B0%5D=41&page={}"

# WebDriverの設定
options = Options()
options.headless = True  # ヘッドレスモード（ブラウザを表示しない）
service = Service(ChromeDriverManager().install())
driver = webdriver.Chrome(service=service, options=options)

# ヘッダー行を定義
headers = ["最寄り駅", "徒歩", "住所", "階", "賃料", "坪単価", "補償金/敷金", "面積", "現況", "URL"]

# スプレッドシートに書き込むためのデータリスト
data_samples = [headers]  # ヘッダー行を最初に追加
unique_samples = {}  # 重複チェック用の辞書

for page in range(1, max_page + 1):
    # 完全なURLを生成
    full_url = base_url + relative_url.format(page)
    driver.get(full_url)
    time.sleep(2)  # ページが完全に読み込まれるまで待機

    estate_items = driver.find_elements(By.CLASS_NAME, 'estateItem')

    for item in estate_items:
        # 建物情報の取得
        # 以下のコードは適宜修正してください
        station_name = item.find_element(By.CLASS_NAME, 'stationInfo__name--link').text.strip() if len(item.find_elements(By.CLASS_NAME, 'stationInfo__name--link')) > 0 else ''
        station_near = item.find_element(By.CLASS_NAME, 'stationInfo__near--value').text.strip() if len(item.find_elements(By.CLASS_NAME, 'stationInfo__near--value')) > 0 else ''
        address = item.find_element(By.CLASS_NAME, 'estateItem__estateAddress').text.strip() if len(item.find_elements(By.CLASS_NAME, 'estateItem__estateAddress')) > 0 else ''
        floor = item.find_element(By.CLASS_NAME, 'estateItem__estateFloor').text.strip() if len(item.find_elements(By.CLASS_NAME, 'estateItem__estateFloor')) > 0 else ''
        price = item.   find_element(By.CLASS_NAME, 'estateItem__estatePrice--value').text.strip() if len(item.find_elements(By.CLASS_NAME, 'estateItem__estatePrice--value')) > 0 else ''
        price_sub = item.find_element(By.CLASS_NAME, 'estateItem__estateSubPrice--value').text.strip() if len(item.find_elements(By.CLASS_NAME, 'estateItem__estateSubPrice--value')) > 0 else ''
        deposit = item.find_element(By.CLASS_NAME, 'estateItem__estateDeposit').text.strip() if len(item.find_elements(By.CLASS_NAME, 'estateItem__estateDeposit')) > 0 else ''
        area = item.find_element(By.CLASS_NAME, 'estateItem__estateArea').text.strip() if len(item.find_elements(By.CLASS_NAME, 'estateItem__estateArea')) > 0 else ''
        purpose = item.find_element(By.CLASS_NAME, 'estateItem__estatePurpose--link').text.strip() if len(item.find_elements(By.CLASS_NAME, 'estateItem__estatePurpose--link')) > 0 else ''
        # 各項目をリストに追加
        data_sample = [station_name, station_near, address, floor, price, price_sub, deposit, area, purpose]
        dedup_key = (address, floor, area)  # 住所、階、面積で重複チェック
        if dedup_key not in unique_samples:
            unique_samples[dedup_key] = data_sample
            data_samples.append(data_sample)# 以降の Google Sheets への書き込み処理は変更なし

import gspread
from google.oauth2.service_account import Credentials

# GoogleSheetsAPI、GoogleDriveAPI、及び認証鍵の指定
SCOPES = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']

# jsonファイル名指定
SERVICE_ACCOUNT_FILE = "/Users/takuya/Downloads/suumo-406823-d340d67b6742.json"

# Service Accountの認証情報を取得
credentials = Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE, scopes=SCOPES)

# 認証情報を用いてGoogleSheetsにアクセス
gs = gspread.authorize(credentials)

# 新しいスプレッドシートURLを指定
SPREADSHEET_URL = "https://docs.google.com/spreadsheets/d/1jq_SAH4J3rpagJryPzsSzhz5I3HNdJG0OOxAqx6Lxow/edit#gid=0"

# URLを使用してスプレッドシートを開く
workbook = gs.open_by_url(SPREADSHEET_URL)
worksheet = workbook.worksheet("シート1")

# ここにデータ書き込みのロジックを入れる
# スプレッドシートに書き込むためのデータ
values = [headers] + list(unique_samples.values())

# スプレッドシートの1行目（A1セル）からデータを追加
worksheet.update("A1", values)

driver.quit()  # WebDriverを終了
