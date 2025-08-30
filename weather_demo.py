class WeatherDemo(BaseDemo):
    """OpenWeatherMap APIを使用した天気デモ（改修版・ボタン実行対応）"""

    @error_handler_ui
    @timer_ui
    def run(self):
        """デモの実行（改修版）"""
        self.initialize()
        st.write("サブアプリ：WeatherDemo")
        st.header("構造化出力: 天気デモ")
        st.write(
            "外部API連携デモ（改修版）。都市選択後、「APIを実行」ボタンでOpenWeatherMap APIを呼び出し、"
            "天気情報を表示します。実世界データ統合とUI操作フローの実装例。"
        )
        with st.expander("利用：OpenWeatherMap API(比較用)", expanded=False):
            st.code("""
            df_jp = self._load_japanese_cities(cities_json)
            # def _get_current_weather
            url = "http://api.openweathermap.org/data/2.5/weather"
                params = {
                    "lat"  : lat,
                    "lon"  : lon,
                    "appid": api_key,
                    "units": unit,
                    "lang" : "ja"  # 日本語での天気説明
                }
            response = requests.get(url, params=params, timeout=config.get("api.timeout", 30))
            """)

        # 都市データの読み込み（JSONから日本都市のみ）
        cities_json = config.get("paths.cities_json", "data/city_jp.list.json")
        if not Path(cities_json).exists():
            st.error(f"都市データファイルが見つかりません: {cities_json}")
            return

        df_jp = self._load_japanese_cities(cities_json)

        # 都市選択UI
        city, lat, lon = self._select_city(df_jp)

        # APIを実行ボタンの追加
        col1, col2, col3 = st.columns([2, 1, 2])
        with col2:
            api_execute = st.button(
                "🌤️ APIを実行",
                key=f"weather_api_{self.safe_key}",
                use_container_width=True,
                type="primary",
                help=f"選択した都市（{city}）の天気情報を取得します"
            )

        # 選択された都市の情報表示
        if city and lat and lon:
            with st.expander("📍 選択された都市情報", expanded=False):
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("都市名", city)
                with col2:
                    st.metric("緯度", f"{lat:.4f}")
                with col3:
                    st.metric("経度", f"{lon:.4f}")

        # APIキーの確認
        api_key = os.getenv("OPENWEATHER_API_KEY")
        if not api_key:
            st.warning("⚠️ OPENWEATHER_API_KEY環境変数が設定されていません")
            st.info("天気APIを利用するには、OpenWeatherMapのAPIキーが必要です。")
            st.code("export OPENWEATHER_API_KEY='your-api-key'", language="bash")
            return

        # APIを実行ボタンが押された場合
        if api_execute:
            if city and lat and lon:
                st.info(f"🔍 {city}の天気情報を取得中...")
                self._display_weather(lat, lon, city)
            else:
                st.error("❌ 都市が正しく選択されていません。都市を選択してから再実行してください。")

    def _load_japanese_cities(self, json_path: str) -> pd.DataFrame:
        """日本の都市データを city_jp.list.json から読み込み"""
        try:
            with open(json_path, "r", encoding="utf-8") as f:
                cities_list = json.load(f)
            # 必要なカラムのみ抽出
            df = pd.DataFrame([
                {
                    "name": city["name"],
                    "lat" : city["coord"]["lat"],
                    "lon" : city["coord"]["lon"],
                    "id"  : city["id"]
                }
                for city in cities_list
            ])
            # 都市名でソート
            return df.sort_values("name").reset_index(drop=True)
        except Exception as e:
            st.error(f"都市データの読み込みに失敗しました: {e}")
            return pd.DataFrame()

    def _select_city(self, df: pd.DataFrame) -> tuple:
        """都市選択UI（改修版）"""
        if df.empty:
            st.error("都市データが空です")
            return "Tokyo", 35.6895, 139.69171

        # 都市選択の説明
        st.subheader("🏙️ 都市選択")
        st.write("天気情報を取得したい都市を選択してください：")

        # 都市選択ボックス
        city = st.selectbox(
            "都市を選択してください",
            df["name"].tolist(),
            key=f"city_{self.safe_key}",
            help="日本国内の主要都市から選択できます"
        )

        row = df[df["name"] == city].iloc[0]

        return city, row["lat"], row["lon"]

    def _display_weather(self, lat: float, lon: float, city_name: str = None):
        """天気情報の表示（改修版）"""
        try:
            # 実行時間の計測開始
            start_time = time.time()

            # 現在の天気
            with st.spinner(f"🌤️ {city_name or '選択した都市'}の現在の天気を取得中..."):
                today = self._get_current_weather(lat, lon)

            if today:
                st.success("✅ 現在の天気情報を取得しました")

                # 現在の天気表示
                with st.container():
                    st.write("### 📍 本日の天気")

                    # メトリクス表示
                    col1, col2, col3, col4 = st.columns(4)
                    with col1:
                        st.metric("🏙️ 都市", today['city'])
                    with col2:
                        st.metric("🌡️ 気温", f"{today['temperature']}℃")
                    with col3:
                        st.metric("💨 天気", today['description'])
                    with col4:
                        # 座標情報
                        coord = today.get('coord', {})
                        st.metric("📍 座標", f"{coord.get('lat', 'N/A'):.2f}, {coord.get('lon', 'N/A'):.2f}")

            # 週間予報
            with st.spinner("📊 5日間予報を取得中..."):
                forecast = self._get_weekly_forecast(lat, lon)

            if forecast:
                st.success("✅ 週間予報を取得しました")

                # 5日間予報表示
                with st.container():
                    st.write("### 📅 5日間予報 （3時間毎データの日別平均）")

                    # テーブル形式で表示
                    forecast_df = pd.DataFrame(forecast)

                    # データフレームのカラム名を日本語に変更
                    forecast_df = forecast_df.rename(columns={
                        'date'    : '日付',
                        'temp_avg': '平均気温(℃)',
                        'weather' : '天気'
                    })

                    st.dataframe(
                        forecast_df,
                        use_container_width=True,
                        hide_index=True
                    )

                    # グラフ表示
                    if len(forecast) > 1:
                        st.write("### 📈 気温推移")
                        temp_data = pd.DataFrame({
                            '日付'    : [item['date'] for item in forecast],
                            '平均気温': [item['temp_avg'] for item in forecast]
                        })
                        st.line_chart(temp_data.set_index('日付'))

            # 実行時間の表示
            end_time = time.time()
            execution_time = end_time - start_time

            with st.expander("🔧 API実行詳細", expanded=False):
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("実行時間", f"{execution_time:.2f}秒")
                with col2:
                    st.metric("API呼び出し数", "2回")  # 現在天気 + 5日間予報
                with col3:
                    st.metric("データ形式", "JSON")

                st.write("**API詳細:**")
                st.write("- 現在の天気: OpenWeatherMap Current Weather API")
                st.write("- 5日間予報: OpenWeatherMap 5 Day Weather Forecast API")
                st.write("- データ更新頻度: リアルタイム")

        except Exception as e:
            st.error(f"❌ 天気情報の取得に失敗しました: {str(e)}")
            logger.error(f"Weather API error: {e}")

            # エラーの詳細表示（デバッグモード時）
            if config.get("experimental.debug_mode", False):
                with st.expander("🔧 エラー詳細", expanded=False):
                    st.exception(e)

    def _get_current_weather(self, lat: float, lon: float, unit: str = "metric") -> dict[str, Any] | None:
        """現在の天気を取得（改修版）"""
        api_key = os.getenv("OPENWEATHER_API_KEY")
        if not api_key:
            st.error("❌ OPENWEATHER_API_KEY環境変数が設定されていません")
            return None

        try:
            url = "http://api.openweathermap.org/data/2.5/weather"
            params = {
                "lat"  : lat,
                "lon"  : lon,
                "appid": api_key,
                "units": unit,
                "lang" : "ja"  # 日本語での天気説明
            }

            response = requests.get(url, params=params, timeout=config.get("api.timeout", 30))
            response.raise_for_status()
            data = response.json()

            return {
                "city"       : data["name"],
                "temperature": round(data["main"]["temp"], 1),
                "description": data["weather"][0]["description"],
                "coord"      : data["coord"],
                "humidity"   : data["main"]["humidity"],
                "pressure"   : data["main"]["pressure"],
                "wind_speed" : data.get("wind", {}).get("speed", 0)
            }
        except requests.exceptions.RequestException as e:
            st.error(f"❌ 天気API呼び出しエラー: {e}")
            logger.error(f"Weather API request error: {e}")
            return None
        except Exception as e:
            st.error(f"❌ 天気データ処理エラー: {e}")
            logger.error(f"Weather data processing error: {e}")
            return None

    def _get_weekly_forecast(self, lat: float, lon: float, unit: str = "metric") -> List[dict]:
        """週間予報を取得（改修版）"""
        api_key = os.getenv("OPENWEATHER_API_KEY")
        if not api_key:
            return []

        try:
            url = "http://api.openweathermap.org/data/2.5/forecast"
            params = {
                "lat"  : lat,
                "lon"  : lon,
                "units": unit,
                "appid": api_key,
                "lang" : "ja"  # 日本語での天気説明
            }

            response = requests.get(url, params=params, timeout=config.get("api.timeout", 30))
            response.raise_for_status()
            data = response.json()

            # 日別に集計
            daily = {}
            for item in data["list"]:
                date = item["dt_txt"].split(" ")[0]
                temp = item["main"]["temp"]
                weather = item["weather"][0]["description"]

                if date not in daily:
                    daily[date] = {"temps": [], "weather": weather}
                daily[date]["temps"].append(temp)

            # 平均気温を計算
            result = []
            for date, info in daily.items():
                avg_temp = round(sum(info["temps"]) / len(info["temps"]), 1)
                result.append({
                    "date"    : date,
                    "temp_avg": avg_temp,
                    "weather" : info["weather"]
                })

            return result

        except requests.exceptions.RequestException as e:
            st.error(f"❌ 予報API呼び出しエラー: {e}")
            logger.error(f"Forecast API request error: {e}")
            return []
        except Exception as e:
            st.error(f"❌ 予報データ処理エラー: {e}")
            logger.error(f"Forecast data processing error: {e}")
            return []
