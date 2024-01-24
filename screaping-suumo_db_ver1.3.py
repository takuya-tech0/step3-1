import requests
from bs4 import BeautifulSoup
import urllib.parse
import re
import gspread
from google.oauth2.service_account import Credentials

def calculate_total_rent(rent, management_fee):
    # 家賃を数値に変換（例: "22.5万円" -> 225000）
    rent_value = float(rent.replace("万円", "")) * 10000

    # 管理費が「-」の場合は0円として扱う
    if management_fee == '-':
        management_fee_value = 0
    else:
        management_fee_value = int(management_fee.replace("円", ""))

    # 合計を計算し、「万円」単位で戻す
    total = rent_value + management_fee_value
    return total / 10000  # 合計を万円単位で戻す

# 駅情報の抽出関数
def extract_station_info(info):
    if ' ' in info:
        line_station, walk_time = info.split(' ', 1)
        line, station = line_station.split('/', 1)
        walk_time = int(re.search(r'\d+', walk_time).group())
    else:
        line = station = walk_time = None
    return line, station, walk_time

# 築年数をカテゴリに分類する関数
def categorize_year(year):
    if year <= 1:
        return '1年以内'
    elif year <= 3:
        return '3年以内'
    elif year <= 5:
        return '5年以内'
    elif year <= 7:
        return '7年以内'
    elif year <= 10:
        return '10年以内'
    elif year <= 15:
        return '15年以内'
    elif year <= 20:
        return '20年以内'
    elif year <= 25:
        return '25年以内'
    elif year <= 30:
        return '30年以内'
    else:
        return '30年超'

# 階数をカテゴリに分類する関数
def categorize_floor(floor):
    try:
        floor = int(floor)
    except ValueError:
        return '階数不明'

    if floor == 1:
        return '1階以下'
    elif floor >= 2:
        return '2階以上'
    else:
        return '階数不明'

def extract_district(address):
    # 東京都23区の区を抽出する正規表現パターン
    pattern = r'(?:東京都)?(.*区)'
    match = re.search(pattern, address)
    if match:
        # '区'を含む抽出結果を返す
        return match.group(1)
    else:
        # マッチしない場合はNoneを返す
        return None

def extract_rent_value(rent):
    # 家賃から「万円」を取り除き、数値に変換する
    return float(rent.replace("万円", ""))

def extract_maintenance_fee_value(maintenance_fee):
    # 管理費から「円」を取り除き、数値に変換する
    # 管理費が「-」の場合は0として扱う
    return int(maintenance_fee.replace("円", "")) / 10000 if maintenance_fee != "-" else 0

# スクレイピングするページ数と基本URLの設定
max_page = 10
base_url = "https://suumo.jp"
relative_url = "/jj/chintai/ichiran/FR301FC001/?ar=030&bs=040&ta=13&sc=13101&sc=13102&sc=13103&sc=13104&sc=13105&sc=13113&sc=13109&sc=13110&sc=13111&sc=13112&sc=13114&sc=13115&sc=13120&cb=0.0&ct=25.0&co=1&et=9999999&md=05&md=06&md=07&md=08&md=09&md=10&ts=1&ts=2&cn=9999999&mb=0&mt=9999999&shkr1=03&shkr2=03&shkr3=03&shkr4=03&fw2=&pn={}"

def load_page(url):
    html = requests.get(url)
    soup = BeautifulSoup(html.content, 'html.parser')
    return soup

data_samples = []
unique_samples = {}

headers = ["セグメント", "建物名", "住所", "区", "最寄り駅1_沿線", "最寄り駅1_駅名", "最寄り駅1_徒歩", "最寄り駅2_沿線", "最寄り駅2_駅名", "最寄り駅2_徒歩", "最寄り駅3_沿線", "最寄り駅3_駅名", "最寄り駅3_徒歩", "築年数", "築年数カテゴリ", "最大階数", "階", "階カテゴリ", "家賃", "家賃(数値)", "管理費", "管理費(数値)", "合計家賃", "敷金", "礼金", "間取り", "面積", "URL"]

for page in range(1, max_page + 1):
    full_url = base_url + relative_url.format(page)
    soup = load_page(full_url)
    mother = soup.find_all(class_='cassetteitem')

    for child in mother:
        segment = child.find(class_='ui-pct ui-pct--util1').text
        name = child.find(class_='cassetteitem_content-title').text
        address = child.find(class_='cassetteitem_detail-col1').text
        district = extract_district(address)  # '〜区'を抽出
        station_info = [item.text for item in child.find(class_='cassetteitem_detail-col2').find_all(class_='cassetteitem_detail-text')]
        year, maxfloor = [item.text for item in child.find(class_='cassetteitem_detail-col3').find_all('div')]
        year = int(re.search(r'\d+', year).group()) if re.search(r'\d+', year) else 0
        year_category = categorize_year(year)

        processed_station_info = []
        for info in station_info:
            line, station, walk_time = extract_station_info(info)
            if line and station and walk_time is not None:
                processed_station_info.extend([line, station, walk_time])

        # 最寄駅情報が足りない場合は「-」で埋める
        while len(processed_station_info) < 9:
            processed_station_info.extend(['-', '-', '-'])

        rooms = child.find(class_='cassetteitem_other')
        for room in rooms.find_all(class_='js-cassette_link'):
            floor, rent_fee, maintenance_fee, deposit_fee, gratuity_fee, layout, area, url = '', '', '', '', '', '', '', ''

            for id_, grandchild in enumerate(room.find_all('td')):
                if id_ == 2:
                    floor_text = grandchild.text.strip()
                    if "新築" in floor_text:
                        floor = 1
                    else:
                        match = re.search(r'\d+', floor_text)
                        floor = int(match.group()) if match else 0
                elif id_ == 3:
                    rent_fee = grandchild.find(class_='cassetteitem_other-emphasis ui-text--bold').text
                    rent_value = extract_rent_value(rent_fee)  # 家賃の数値部分を抽出
                    maintenance_fee = grandchild.find(class_='cassetteitem_price cassetteitem_price--administration').text
                    maintenance_fee_value = extract_maintenance_fee_value(maintenance_fee)  # 管理費の数値部分を抽出
                elif id_ == 4:
                    deposit_fee = grandchild.find(class_='cassetteitem_price cassetteitem_price--deposit').text
                    gratuity_fee = grandchild.find(class_='cassetteitem_price cassetteitem_price--gratuity').text
                elif id_ == 5:
                    layout = grandchild.find(class_='cassetteitem_madori').text
                    area = grandchild.find(class_='cassetteitem_menseki').text
                elif id_ == 8:
                    get_url = grandchild.find(class_='js-cassette_link_href cassetteitem_other-linktext').get('href')
                    url = urllib.parse.urljoin(url, get_url)
                floor_category = categorize_floor(floor)

            # 家賃と管理費の合計を計算
            total_rent = calculate_total_rent(rent_fee, maintenance_fee)

            data_sample = [segment, name, address, district] + processed_station_info + [year, year_category, maxfloor, floor, floor_category, rent_fee, rent_value, maintenance_fee, maintenance_fee_value, total_rent, deposit_fee, gratuity_fee, layout, area, url]

            dedup_key = (data_sample[2], data_sample[5], data_sample[6], data_sample[7], data_sample[11], data_sample[12])
            if dedup_key not in unique_samples:
                unique_samples[dedup_key] = data_sample
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
values = [headers] + list(unique_samples.values())

# スプレッドシートの1行目（A1セル）からデータを追加
worksheet.update(range_name="A1", values=values)