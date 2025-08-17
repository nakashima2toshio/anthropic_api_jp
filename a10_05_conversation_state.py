# streamlit run a10_05_conversation_state.py --server.port=8505
# --------------------------------------------------
# OpenAI 会話状態管理デモアプリケーション（統一化版）
# Streamlitを使用したインタラクティブなAPIテストツール
# 統一化版: a10_00_responses_api.pyの構成・構造・ライブラリ・エラー処理の完全統一
# --------------------------------------------------
import os
import sys
import json
import requests
import logging
from datetime import datetime
import time
from abc import ABC, abstractmethod
from typing import Optional, List, Dict, Any, Union
from pathlib import Path

import streamlit as st
import pandas as pd
from pydantic import BaseModel, Field, ValidationError

from openai import OpenAI
from openai.types.responses import (
    EasyInputMessageParam,
    ResponseInputTextParam,
    ResponseInputImageParam,
    ResponseFormatTextJSONSchemaConfigParam,
    ResponseTextConfigParam,
    FileSearchToolParam,
    WebSearchToolParam,
    ComputerToolParam,
    FunctionToolParam,
    Response,
)

# プロジェクトディレクトリの設定
BASE_DIR = Path(__file__).resolve().parent.parent
THIS_DIR = Path(__file__).resolve().parent

# PYTHONPATHに親ディレクトリを追加
sys.path.insert(0, str(BASE_DIR))

# ヘルパーモジュールをインポート（統一化）
try:
    from helper_st import (
        UIHelper, MessageManagerUI, ResponseProcessorUI,
        SessionStateManager, error_handler_ui, timer_ui,
        InfoPanelManager, safe_streamlit_json
    )
    from helper_api import (
        config, logger, TokenManager, OpenAIClient,
        EasyInputMessageParam, ResponseInputTextParam,
        ConfigManager, MessageManager, sanitize_key,
        error_handler, timer, get_default_messages,
        ResponseProcessor, format_timestamp
    )
except ImportError as e:
    st.error(f"ヘルパーモジュールのインポートに失敗しました: {e}")
    st.info("必要なファイルが存在することを確認してください: helper_st.py, helper_api.py")
    st.stop()


# ページ設定
def setup_page_config():
    """ページ設定（重複実行エラー回避）"""
    try:
        st.set_page_config(
            page_title=config.get("ui.page_title", "OpenAI 会話状態管理デモ"),
            page_icon=config.get("ui.page_icon", "🔄"),
            layout=config.get("ui.layout", "wide"),
            initial_sidebar_state="expanded"
        )
    except st.errors.StreamlitAPIException:
        # 既に設定済みの場合は無視
        pass


# ページ設定の実行
setup_page_config()


# ==================================================
# 共通UI関数（統一化版）
# ==================================================
def setup_common_ui(demo_name: str, selected_model: str):
    """共通UI設定（統一化版）"""
    # ヘッダー表示
    st.write(f"# {demo_name}")
    st.write("選択したモデル:", selected_model)


def setup_sidebar_panels(selected_model: str):
    """サイドバーパネルの統一設定（helper_st.pyのInfoPanelManagerを使用）"""
    st.sidebar.write("### 📋 情報パネル")
    
    # InfoPanelManagerを使用した統一パネル設定
    InfoPanelManager.show_model_info(selected_model)
    InfoPanelManager.show_session_info()
    InfoPanelManager.show_cost_info(selected_model)
    InfoPanelManager.show_performance_info()
    InfoPanelManager.show_debug_panel()
    InfoPanelManager.show_settings()


# ==================================================
# ベースデモクラス（統一化版）
# ==================================================
class BaseDemo(ABC):
    """ベースデモクラス（統一化版）"""
    
    def __init__(self, demo_name: str):
        self.demo_name = demo_name
        self.safe_key = sanitize_key(demo_name)
        self.model = None
        self.client = None
    
    @abstractmethod
    def run_demo(self):
        """デモの実行（サブクラスで実装）"""
        pass
    
    @error_handler_ui
    @timer_ui
    def execute(self, selected_model: str):
        """デモの実行（統一エラーハンドリング）"""
        # 選択されたモデルを設定
        self.model = selected_model
        
        # 共通UI設定
        setup_common_ui(self.demo_name, selected_model)
        
        # OpenAIクライアントの初期化
        try:
            self.client = OpenAI()
        except Exception as e:
            st.error(f"OpenAIクライアントの初期化に失敗しました: {e}")
            return
        
        # デモ実行
        self.run_demo()


# ==================================================
# 会話状態管理デモクラス（統一化版）
# ==================================================
class StatefulConversationDemo(BaseDemo):
    """ステートフルな会話継続デモ"""

    def run_demo(self):
        """ステートフルな会話継続デモの実行"""
        st.write("## 実装例: previous_response_idを使用した会話継続")
        st.write("前の会話コンテキストを保持したまま会話を継続する方法を示します。")
        
        # 実装例サンプル表示
        with st.expander("📋 実装例コード", expanded=False):
            st.code("""
# ステートフルな会話継続の実装例
from openai import OpenAI
from openai.types.responses import EasyInputMessageParam, ResponseInputTextParam

client = OpenAI()

# 初回質問
initial_response = client.responses.create(
    model=model,
    input=[
        EasyInputMessageParam(
            role="user",
            content=[
                ResponseInputTextParam(
                    type="input_text", 
                    text="OpenAI APIの使い方を教えて"
                )
            ]
        )
    ]
)

# 会話の継続（previous_response_idを使用）
follow_up_response = client.responses.create(
    model=model,
    input="具体的なコード例も教えて",
    previous_response_id=initial_response.id
)
            """, language="python")
        
        # 入力エリア
        st.subheader("📤 入力")
        
        # 初回質問
        initial_question = st.text_area(
            "初回の質問",
            value="OpenAI APIの使い方を教えて",
            height=config.get("ui.text_area_height", 75),
            key=f"initial_question_{self.safe_key}"
        )
        
        if st.button("🚀 初回質問を送信", key=f"initial_submit_{self.safe_key}"):
            if initial_question:
                self._process_initial_question(initial_question)
        
        # 追加質問（初回回答がある場合のみ表示）
        if f"initial_response_{self.safe_key}" in st.session_state:
            st.write("---")
            follow_up = st.text_area(
                "追加質問（前の会話を引き継ぎます）",
                value="具体的なコード例も教えて",
                height=config.get("ui.text_area_height", 75),
                key=f"follow_up_{self.safe_key}"
            )
            
            if st.button("📝 追加質問を送信", key=f"follow_up_submit_{self.safe_key}"):
                if follow_up:
                    self._process_follow_up_question(follow_up)
        
        # 結果表示
        self._display_conversation_results()
    
    def _process_initial_question(self, question: str):
        """初回質問の処理"""
        try:
            # デフォルトメッセージを取得
            messages = get_default_messages()
            messages.append(
                EasyInputMessageParam(
                    role="user",
                    content=[
                        ResponseInputTextParam(
                            type="input_text",
                            text=question
                        )
                    ]
                )
            )
            
            with st.spinner("処理中..."):
                response = self.client.responses.create(
                    model=self.model,
                    input=messages
                )
            
            # セッション状態に保存
            st.session_state[f"initial_response_{self.safe_key}"] = response
            st.success(f"✅ Response ID: `{response.id}` を保存しました")
            st.rerun()
            
        except Exception as e:
            st.error(f"エラーが発生しました: {e}")
            if config.get("experimental.debug_mode", False):
                st.exception(e)
    
    def _process_follow_up_question(self, question: str):
        """追加質問の処理"""
        try:
            initial_response = st.session_state[f"initial_response_{self.safe_key}"]
            
            with st.spinner("処理中（前の会話を引き継ぎ中）..."):
                response = self.client.responses.create(
                    model=self.model,
                    input=question,
                    previous_response_id=initial_response.id
                )
            
            # セッション状態に保存
            st.session_state[f"follow_up_response_{self.safe_key}"] = response
            st.success(f"✅ 会話を継続しました - Response ID: `{response.id}`")
            st.rerun()
            
        except Exception as e:
            st.error(f"エラーが発生しました: {e}")
            if config.get("experimental.debug_mode", False):
                st.exception(e)
    
    def _display_conversation_results(self):
        """会話結果の表示"""
        # 初回回答
        if f"initial_response_{self.safe_key}" in st.session_state:
            response = st.session_state[f"initial_response_{self.safe_key}"]
            st.subheader("🤖 初回の回答")
            ResponseProcessorUI.display_response(response)
        
        # 追加質問への回答
        if f"follow_up_response_{self.safe_key}" in st.session_state:
            response = st.session_state[f"follow_up_response_{self.safe_key}"]
            st.subheader("🤖 追加質問への回答")
            ResponseProcessorUI.display_response(response)


class WebSearchParseDemo(BaseDemo):
    """Web検索と構造化パースデモ"""

    def run_demo(self):
        """Web検索と構造化パースデモの実行"""
        st.write("## 実装例: Web検索と構造化パース")
        st.write("Web検索を実行し、その結果を構造化されたフォーマット（JSON）にパースします。")
        
        # 実装例サンプル表示
        with st.expander("📋 実装例コード", expanded=False):
            st.code("""
# Web検索と構造化パースの実装例
from openai import OpenAI
from openai.types.responses import WebSearchToolParam
from pydantic import BaseModel, Field

client = OpenAI()

# Web検索の実行
tool = {"type": "web_search_preview"}
search_response = client.responses.create(
    model=model,
    input="最新のOpenAI APIの情報は？",
    tools=[tool]
)

# 構造化パースのためのスキーマ定義
class APIInfo(BaseModel):
    title: str = Field(..., description="記事のタイトル")
    url: str = Field(..., description="記事のURL")

# 構造化パース実行
structured_response = client.responses.parse(
    model="gpt-4.1",
    input="上の回答をtitleとurlだけJSON で返して",
    previous_response_id=search_response.id,
    text_format=APIInfo
)
            """, language="python")
        
        # 入力エリア
        st.subheader("📤 入力")
        
        search_query = st.text_input(
            "検索クエリ",
            value="東京の明日の天気と明日のイベントを教えて。",
            key=f"search_query_{self.safe_key}"
        )
        
        if st.button("🔍 検索実行", key=f"search_submit_{self.safe_key}"):
            if search_query:
                self._execute_web_search(search_query)
        
        # 構造化パースボタン（検索結果がある場合のみ表示）
        if f"search_response_{self.safe_key}" in st.session_state:
            if st.button("🔄 構造化実行", key=f"parse_submit_{self.safe_key}"):
                self._execute_structured_parse()
        
        # 結果表示
        self._display_search_results()
    
    def _execute_web_search(self, query: str):
        """Web検索の実行"""
        try:
            tool: WebSearchToolParam = {"type": "web_search_preview"}
            
            with st.spinner("Web検索中..."):
                response = self.client.responses.create(
                    model=self.model,
                    input=query,
                    tools=[tool]
                )
            
            st.session_state[f"search_response_{self.safe_key}"] = response
            st.success(f"✅ Web検索完了 - Response ID: `{response.id}`")
            st.rerun()
            
        except Exception as e:
            st.error(f"Web検索エラー: {e}")
            if config.get("experimental.debug_mode", False):
                st.exception(e)
    
    def _execute_structured_parse(self):
        """構造化パースの実行"""
        try:
            search_response = st.session_state[f"search_response_{self.safe_key}"]
            
            # スキーマ定義
            class APIInfo(BaseModel):
                title: str = Field(..., description="記事のタイトル")
                url: str = Field(..., description="記事のURL")
            
            with st.spinner("構造化パース中..."):
                structured_response = self.client.responses.parse(
                    model="gpt-4.1",
                    input="上の回答をtitleとurlだけJSON で返して",
                    previous_response_id=search_response.id,
                    text_format=APIInfo
                )
            
            st.session_state[f"structured_response_{self.safe_key}"] = structured_response
            st.success("✅ 構造化パース完了")
            st.rerun()
            
        except Exception as e:
            st.error(f"構造化パースエラー: {e}")
            if config.get("experimental.debug_mode", False):
                st.exception(e)
    
    def _display_search_results(self):
        """検索結果の表示"""
        # 検索結果
        if f"search_response_{self.safe_key}" in st.session_state:
            response = st.session_state[f"search_response_{self.safe_key}"]
            st.subheader("🤖 検索結果")
            ResponseProcessorUI.display_response(response)
        
        # 構造化データ
        if f"structured_response_{self.safe_key}" in st.session_state:
            response = st.session_state[f"structured_response_{self.safe_key}"]
            st.subheader("🤖 構造化データ")
            ResponseProcessorUI.display_response(response)


class FunctionCallingDemo(BaseDemo):
    """Function Callingデモ"""

    def run_demo(self):
        """Function Callingデモの実行"""
        st.write("## 実装例: Function Calling (天気API)")
        st.write("Function Callingを使用して外部APIと統合する方法を示します。")
        
        # 実装例サンプル表示
        with st.expander("📋 実装例コード", expanded=False):
            st.code("""
# Function Callingの実装例
from openai import OpenAI
from openai.types.responses import FunctionToolParam
from pydantic import BaseModel, Field
import requests

client = OpenAI()

# パラメータスキーマの定義
class WeatherParams(BaseModel):
    latitude: float = Field(..., description="緯度（10進）")
    longitude: float = Field(..., description="経度（10進）")

# 天気取得関数
def get_weather(latitude: float, longitude: float) -> dict:
    url = f"https://api.open-meteo.com/v1/forecast?latitude={latitude}&longitude={longitude}&current=temperature_2m"
    response = requests.get(url)
    return response.json()

# Function toolの定義
weather_tool = {
    "type": "function",
    "name": "get_weather", 
    "description": "現在の天気情報を取得",
    "parameters": WeatherParams.model_json_schema(),
    "strict": True
}

# Function Calling実行
response = client.responses.create(
    model="gpt-4.1",
    input="東京の今日の天気は？",
    tools=[weather_tool]
)
            """, language="python")
        
        # 入力エリア
        st.subheader("📤 入力")
        
        # 都市データ
        cities = {
            "東京": {"lat": 35.6762, "lon": 139.6503},
            "パリ": {"lat": 48.8566, "lon": 2.3522},
            "ニューヨーク": {"lat": 40.7128, "lon": -74.0060},
            "ロンドン": {"lat": 51.5074, "lon": -0.1278},
            "シドニー": {"lat": -33.8688, "lon": 151.2093}
        }
        
        selected_city = st.selectbox(
            "都市を選択",
            options=list(cities.keys()),
            key=f"city_select_{self.safe_key}"
        )
        
        query = st.text_input(
            "質問",
            value=f"今日の{selected_city}の天気は？",
            key=f"weather_query_{self.safe_key}"
        )
        
        if st.button("🌡️ 天気を取得", key=f"weather_submit_{self.safe_key}"):
            if query:
                self._execute_function_calling(query, selected_city, cities)
        
        # 結果表示
        self._display_weather_results()
    
    def _execute_function_calling(self, query: str, selected_city: str, cities: dict):
        """Function Callingの実行"""
        try:
            # パラメータスキーマの定義
            class WeatherParams(BaseModel):
                latitude: float = Field(..., description="緯度（10進）")
                longitude: float = Field(..., description="経度（10進）")
            
            # 天気取得関数
            def get_weather(latitude: float, longitude: float) -> dict:
                """Open-Meteo APIで現在の天気情報を取得"""
                url = (
                    "https://api.open-meteo.com/v1/forecast"
                    f"?latitude={latitude}&longitude={longitude}"
                    "&current=temperature_2m,relative_humidity_2m,wind_speed_10m"
                )
                try:
                    r = requests.get(url, timeout=10)
                    r.raise_for_status()
                    data = r.json()
                    return {
                        "temperature": data["current"]["temperature_2m"],
                        "humidity": data["current"]["relative_humidity_2m"],
                        "wind_speed": data["current"]["wind_speed_10m"],
                        "units": {
                            "temperature": "°C",
                            "humidity": "%",
                            "wind_speed": "km/h"
                        }
                    }
                except Exception as e:
                    return {"error": str(e)}
            
            # JSON Schema生成
            schema = WeatherParams.model_json_schema()
            schema["additionalProperties"] = False
            
            # FunctionToolParam構築
            weather_tool: FunctionToolParam = {
                "type": "function",
                "name": "get_weather",
                "description": get_weather.__doc__,
                "parameters": schema,
                "strict": True,
            }
            
            with st.spinner("Function Calling 実行中..."):
                response = self.client.responses.create(
                    model="gpt-4.1",
                    input=query,
                    tools=[weather_tool]
                )
            
            # 実際の天気データを取得
            coords = cities[selected_city]
            weather_data = get_weather(coords["lat"], coords["lon"])
            
            # セッション状態に保存
            st.session_state[f"function_response_{self.safe_key}"] = response
            st.session_state[f"weather_data_{self.safe_key}"] = weather_data
            st.session_state[f"selected_city_{self.safe_key}"] = selected_city
            
            st.success(f"✅ Function Calling完了 - Response ID: `{response.id}`")
            st.rerun()
            
        except Exception as e:
            st.error(f"Function Calling エラー: {e}")
            if config.get("experimental.debug_mode", False):
                st.exception(e)
    
    def _display_weather_results(self):
        """天気結果の表示"""
        # Function Call結果
        if f"function_response_{self.safe_key}" in st.session_state:
            response = st.session_state[f"function_response_{self.safe_key}"]
            selected_city = st.session_state.get(f"selected_city_{self.safe_key}", "")
            weather_data = st.session_state.get(f"weather_data_{self.safe_key}", {})
            
            st.subheader(f"🤖 Function Call 結果 - {selected_city}")
            ResponseProcessorUI.display_response(response)
            
            # リアルタイム天気データ
            if weather_data and "error" not in weather_data:
                st.subheader(f"🌡️ リアルタイム天気データ - {selected_city}")
                
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("🌡️ 気温", f"{weather_data['temperature']}°C")
                with col2:
                    st.metric("💧 湿度", f"{weather_data['humidity']}%")
                with col3:
                    st.metric("💨 風速", f"{weather_data['wind_speed']} km/h")
            
            elif weather_data:
                st.error(f"天気データ取得エラー: {weather_data.get('error', 'Unknown error')}")


# ==================================================
# デモ管理クラス（統一化版）
# ==================================================
class DemoManager:
    """デモ管理クラス（統一化版）"""
    
    def __init__(self):
        self.demos = {
            "ステートフルな会話継続": StatefulConversationDemo,
            "Web検索と構造化パース": WebSearchParseDemo,
            "Function Calling (天気API)": FunctionCallingDemo,
        }
    
    def get_demo_list(self) -> List[str]:
        """デモリストの取得"""
        return list(self.demos.keys())
    
    def run_demo(self, demo_name: str, selected_model: str):
        """選択されたデモの実行"""
        if demo_name in self.demos:
            demo_class = self.demos[demo_name]
            demo_instance = demo_class(demo_name)
            demo_instance.execute(selected_model)
        else:
            st.error(f"不明なデモ: {demo_name}")


# ==================================================
# メイン関数（統一化版）
# ==================================================
def main():
    """メインアプリケーション（統一化版）"""
    # セッション状態の初期化
    SessionStateManager.init_session_state()
    
    # デモマネージャーの初期化
    demo_manager = DemoManager()
    
    # サイドバー: a10_00の順序に統一（デモ選択 → モデル選択 → 情報パネル）
    with st.sidebar:
        # 1. デモ選択
        demo_name = st.radio(
            "デモを選択",
            demo_manager.get_demo_list(),
            key="demo_selection"
        )
        
        # 2. モデル選択（デモ選択の直後）
        selected_model = UIHelper.select_model("model_selection")
        
        # 3. 情報パネル
        setup_sidebar_panels(selected_model)
    
    # メインエリア（1段構成に統一）
    # 選択されたデモを実行
    try:
        demo_manager.run_demo(demo_name, selected_model)
    except Exception as e:
        st.error(f"デモの実行中にエラーが発生しました: {e}")
        if config.get("experimental.debug_mode", False):
            st.exception(e)


if __name__ == "__main__":
    main()

# streamlit run a10_05_conversation_state.py --server.port=8505