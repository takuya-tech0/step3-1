import requests
from bs4 import BeautifulSoup
from retry import retry
import urllib

# 複数ページの情報をまとめて取得
data_samples = []

# スクレイピングするページ数
max_page = 2
# SUUMOを東京都23区のみ指定して検索して出力した画面のurl(ページ数フォーマットが必要)
base_url = "https://suumo.jp"
relative_url = "/chintai/jnc_000086594399/?bc=100355231068"
absolute_url = urllib.parse.urljoin(base_url, relative_url)
url = absolute_url

# リクエストがうまく行かないパターンを回避するためのやり直し
def load_page(url):
    html = requests.get(url)
    soup = BeautifulSoup(html.content, 'html.parser')
    return soup

data_samples = []

# ヘッダー行を定義
headers = ["セグメント", "建物名", "住所", "最寄り駅1", "最寄り駅2", "最寄り駅3", "築年数", "最大階数", "階", "家賃", "管理費", "敷金", "礼金", "間取り", "面積", "URL"]

# スプレッドシートに書き込むためのデータリスト
data_samples = [headers]  # ヘッダー行を最初に追加

for page in range(1, max_page + 1):
    soup = load_page(url.format(page))
    mother = soup.find_all(class_='cassetteitem')
    
    for child in mother:
        # 建物情報
        segment = child.find(class_='ui-pct ui-pct--util1').text
        name = child.find(class_='cassetteitem_content-title').text
        address = child.find(class_='cassetteitem_detail-col1').text
        station_info = [item.text for item in child.find(class_='cassetteitem_detail-col2').find_all(class_='cassetteitem_detail-text')]
        year, maxfloor = [item.text for item in child.find(class_='cassetteitem_detail-col3').find_all('div')]

        # 部屋情報
        rooms = child.find(class_='cassetteitem_other')
        for room in rooms.find_all(class_='js-cassette_link'):
            floor, rent_fee, maintenance_fee, deposit_fee, gratuity_fee, layout, area, url = '', '', '', '', '', '', '', ''
            
            # 部屋情報の取得
            for id_, grandchild in enumerate(room.find_all('td')):
                if id_ == 2:
                    floor = grandchild.text.strip()
                elif id_ == 3:
                    rent_fee = grandchild.find(class_='cassetteitem_other-emphasis ui-text--bold').text
                    maintenance_fee = grandchild.find(class_='cassetteitem_price cassetteitem_price--administration').text
                elif id_ == 4:
                    deposit_fee = grandchild.find(class_='cassetteitem_price cassetteitem_price--deposit').text
                    gratuity_fee = grandchild.find(class_='cassetteitem_price cassetteitem_price--gratuity').text
                elif id_ == 5:
                    layout = grandchild.find(class_='cassetteitem_madori').text
                    area = grandchild.find(class_='cassetteitem_menseki').text
                elif id_ == 8:
                    get_url = grandchild.find(class_='js-cassette_link_href cassetteitem_other-linktext').get('href')
                    url = urllib.parse.urljoin(url, get_url)
            
            # データの組み合わせ
            data_sample = [segment, name, address] + station_info + [year, maxfloor, floor, rent_fee, maintenance_fee, deposit_fee, gratuity_fee, layout, area, url]
            data_samples.append(data_sample)

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

# 対象のスプレッドシートとワークシートを指定
SPREADSHEET_KEY = "1PJTcCQ2QB3pq6aJTJAopK_bf6dwmtjhaTf9GUvejix0"
workbook = gs.open_by_key(SPREADSHEET_KEY)
worksheet = workbook.worksheet("シート1")

# スプレッドシートに書き込むためのデータ
values = data_samples

# スプレッドシートの1行目（A1セル）からデータを追加
worksheet.update("A1", values)
