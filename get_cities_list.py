# get_cities_list.py
import gzip
import json

# 入力ファイルと出力ファイルのパス
input_file = 'data/city.list.json.gz'
output_file = 'data/city_jp.list.json'
output_csv_file = 'data/city_jp.list.csv'

# city.list.json.gzを開いて、内容を読み込む
with gzip.open(input_file, 'rt', encoding='utf-8') as f:
    cities = json.load(f)

# "country": "JP" の都市データのみ抽出
jp_cities = [city for city in cities if city.get("country") == "JP"]

# 結果を city_jp.list.json として保存
with open(output_file, 'w', encoding='utf-8') as f:
    json.dump(jp_cities, f, ensure_ascii=False, indent=2)

print(f"日本の都市データを {output_file} に保存しました。件数: {len(jp_cities)}")

# data/cities_list.csv

