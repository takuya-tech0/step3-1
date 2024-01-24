import streamlit as st
import sqlite3
import pandas as pd
import folium
from streamlit_folium import folium_static
from folium import IFrame

# データベースからデータを読み込む関数
def load_data():
    conn = sqlite3.connect('estate.db')
    query = '''
    SELECT
        建物名, 住所, 区, 
        最寄り駅1_沿線, 最寄り駅1_駅名, 最寄り駅1_徒歩, 
        最寄り駅2_沿線, 最寄り駅2_駅名, 最寄り駅2_徒歩, 
        最寄り駅3_沿線, 最寄り駅3_駅名, 最寄り駅3_徒歩, 
        築年数, 築年数カテゴリ, 階, 家賃, 管理費, 間取り, URL, 緯度, 経度, 画像URL, 合計家賃
    FROM properties
    '''
    df = pd.read_sql(query, conn)
    conn.close()

    # 徒歩時間を数値型で取得し、NULLの場合はデフォルト値を設定する
    df['最寄り駅1_徒歩'] = pd.to_numeric(df['最寄り駅1_徒歩'], errors='coerce').fillna(999)
    df['最寄り駅2_徒歩'] = pd.to_numeric(df['最寄り駅2_徒歩'], errors='coerce').fillna(999)
    df['最寄り駅3_徒歩'] = pd.to_numeric(df['最寄り駅3_徒歩'], errors='coerce').fillna(999)

    return df

# Streamlit アプリのメイン関数
def main():
    st.title('不動産情報')

    df = load_data()

    # サイドバーにフィルタオプションを追加
    unique_stations = pd.unique(df[['最寄り駅1_駅名', '最寄り駅2_駅名', '最寄り駅3_駅名']].values.ravel('K'))
    unique_districts = pd.unique(df['区'])
    unique_layouts = pd.unique(df['間取り'])
    unique_age_categories = pd.unique(df['築年数カテゴリ'])

    filter_type = st.sidebar.radio("駅/エリアを選択", ["駅名", "エリア"])

    if filter_type == "駅名":
        selected_stations = st.sidebar.multiselect('駅名を選択', unique_stations)
    else:
        selected_districts = st.sidebar.multiselect('エリアを選択', unique_districts)

    selected_layouts = st.sidebar.multiselect('間取りを選択', unique_layouts)
    selected_age_categories = st.sidebar.multiselect('築年数カテゴリを選択', unique_age_categories)
    rent_range = st.sidebar.slider("家賃(管理費込み)の範囲（円）", 0, 150000, (0, 500000))

    max_walk_time = st.sidebar.slider("最寄り駅までの徒歩時間（分）", 0, 30, 10)

    # 検索ボタン
    search = st.sidebar.button('検索')

    # 検索ボタンが押された場合
    if search:
        if filter_type == "駅名" and selected_stations:
            df = df[(df['最寄り駅1_駅名'].isin(selected_stations)) | 
                    (df['最寄り駅2_駅名'].isin(selected_stations)) | 
                    (df['最寄り駅3_駅名'].isin(selected_stations))]
        elif filter_type == "区" and selected_districts:
            df = df[df['区'].isin(selected_districts)]

        df = df[df['間取り'].isin(selected_layouts) & 
                df['築年数カテゴリ'].isin(selected_age_categories) & 
                (df['合計家賃'] >= rent_range[0]) & 
                (df['合計家賃'] <= rent_range[1]) &
                ((df['最寄り駅1_徒歩'] <= max_walk_time) | 
                (df['最寄り駅2_徒歩'] <= max_walk_time) | 
                (df['最寄り駅3_徒歩'] <= max_walk_time))]

        # 地図表示
        if '緯度' in df.columns and '経度' in df.columns:
            map_data = df[['建物名', '住所', 'URL', '画像URL', '緯度', '経度']].dropna()
            map_data['緯度'] = map_data['緯度'].astype(float)
            map_data['経度'] = map_data['経度'].astype(float)
            m = folium.Map(location=[35.689487, 139.691706], zoom_start=10)
            for _, row in map_data.iterrows():
                html = f"<a href='{row['URL']}' target='_blank'>{row['建物名']}</a><br>{row['住所']}<br><img src='{row['画像URL']}' width='150'>"
                iframe = IFrame(html, width=300, height=200)
                popup = folium.Popup(iframe, max_width=2650)
                folium.Marker(
                    location=[row['緯度'], row['経度']],
                    popup=popup
                ).add_to(m)
            folium_static(m)

        # テーブル表示
        st.write(df)

if __name__ == "__main__":
    main()
