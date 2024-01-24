import requests
from bs4 import BeautifulSoup
import urllib.parse
import re
import sqlite3
import gspread
from google.oauth2.service_account import Credentials

# スクレイピングするページ数と基本URLの設定
max_page = 2
base_url = "https://suumo.jp"
relative_url = "/jj/chintai/ichiran/FR301FC001/?ar=030&bs=040&ta=13&sc=13101&sc=13102&sc=13103&sc=13104&sc=13105&sc=13113&sc=13109&sc=13110&sc=13111&sc=13112&sc=13114&sc=13115&sc=13120&cb=0.0&ct=25.0&co=1&et=9999999&md=05&md=06&md=07&md=08&md=09&md=10&ts=1&ts=2&cn=9999999&mb=0&mt=9999999&shkr1=03&shkr2=03&shkr3=03&shkr4=03&fw2=&pn={}"

def load_page(url):
    html = requests.get(url)
    soup = BeautifulSoup(html.content, 'html.parser')
    return soup

data_samples = []
unique_samples = {}

# ヘッダー行を定義
headers = ["セグメント", "建物名", "住所", "最寄り駅1_沿線", "最寄り駅1_駅名", "最寄り駅1_徒歩","最寄り駅2_沿線", "最寄り駅2_駅名", "最寄り駅2_徒歩","最寄り駅3_沿線", "最寄り駅3_駅名", "最寄り駅3_徒歩", "築年数", "最大階数", "階", "家賃", "管理費", "敷金", "礼金", "間取り", "面積", "URL"]

for page in range(1, max_page + 1):
    full_url = base_url + relative_url.format(page)
    soup = load_page(full_url)
    mother = soup.find_all(class_='cassetteitem')

    for child in mother:
        # 建物情報
        segment = child.find(class_='ui-pct ui-pct--util1').text
        name = child.find(class_='cassetteitem_content-title').text
        address = child.find(class_='cassetteitem_detail-col1').text
        station_info = [item.text for item in child.find(class_='cassetteitem_detail-col2').find_all(class_='cassetteitem_detail-text')]
        year, maxfloor = [item.text for item in child.find(class_='cassetteitem_detail-col3').find_all('div')]

        # 駅情報の処理
        processed_station_info = []
        for info in station_info:
            line_station, walk_time = info.rsplit(' ', 1)
            line, station = line_station.split('/', 1)
            walk_time = int(re.search(r'\d+', walk_time).group())
            processed_station_info.extend([line, station, walk_time])

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

            # データサンプルの作成
            data_sample = [segment, name, address] + processed_station_info + [year, maxfloor, floor, rent_fee, maintenance_fee, deposit_fee, gratuity_fee, layout, area, url]
            
            # 重複チェックとデータの追加
            dedup_key = (data_sample[2], data_sample[5], data_sample[6], data_sample[7], data_sample[11], data_sample[12])
            if dedup_key not in unique_samples:
                unique_samples[dedup_key] = data_sample
                data_samples.append(data_sample)

# Google Sheets APIの設定と認証
SCOPES = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']
SERVICE_ACCOUNT_FILE = "/Users/takuya/Downloads/suumo-406823-d340d67b6742.json"
credentials = Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE, scopes=SCOPES)
gs = gspread.authorize(credentials)

# スプレッドシートとワークシートの設定
SPREADSHEET_KEY = "1PJTcCQ2QB3pq6aJTJAopK_bf6dwmtjhaTf9GUvejix0"
workbook = gs.open_by_key(SPREADSHEET_KEY)
worksheet = workbook.worksheet("シート1")

# スプレッドシートにデータを書き込む
values = [headers] + list(unique_samples.values())
worksheet.update(range_name="A1", values=values)
