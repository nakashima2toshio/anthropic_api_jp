# streamlit run a10_02_responses_tools_pydantic_parse.py --server.port=8502
# pip install --upgrade openai
# ---------------------------------------------------- 情報：
# https://cookbook.openai.com/examples/structured_outputs_intro
# 基本的には、Responses.parseを利用するのがおすすめ
# ----------------------------------------------------
# [Cookbook ] https://cookbook.openai.com/
# [API      ]  https://github.com/openai/openai-python
# [Agent SDK] https://github.com/openai/openai-agents-python
# --- --------------
# [Model] https://platform.openai.com/docs/pricing
# ----------------------------------------------------

import os
import sys
from pathlib import Path
from typing import List, Dict, Any, Union
from enum import Enum
import requests
import pprint
import logging

import streamlit as st
from pydantic import BaseModel
from openai import OpenAI, pydantic_function_tool

# プロジェクトディレクトリの設定
BASE_DIR = Path(__file__).resolve().parent.parent
THIS_DIR = Path(__file__).resolve().parent
DATASETS_DIR = os.path.join(BASE_DIR, 'datasets')

# PYTHONPATHに親ディレクトリを追加
sys.path.insert(0, str(BASE_DIR))

# 改修されたヘルパーモジュールをインポート
try:
    from helper_st import (
        UIHelper, MessageManagerUI, ResponseProcessorUI,
        SessionStateManager, error_handler_ui, timer_ui,
        init_page, select_model, InfoPanelManager
    )
    from helper_api import (
        config, logger, TokenManager, OpenAIClient,
        EasyInputMessageParam, ResponseInputTextParam,
        ConfigManager, MessageManager, sanitize_key,
        error_handler, timer
    )
except ImportError as e:
    st.error(f"ヘルパーモジュールのインポートに失敗しました: {e}")
    st.stop()

# ページ設定（一度だけ実行）
st.set_page_config(
    page_title=config.get("ui.page_title", "OpenAI Tools & Pydantic Parse Demo"),
    page_icon=config.get("ui.page_icon", "🛠️"),
    layout=config.get("ui.layout", "wide")
)


# ==================================================
# Pydantic モデル定義
# ==================================================

# 01系デモ用のモデル
class WeatherRequest(BaseModel):
    city: str
    date: str


class NewsRequest(BaseModel):
    topic: str
    date: str


class CalculatorRequest(BaseModel):
    """計算式を受け取るツール"""
    exp: str  # 例: "2+2"


class FAQSearchRequest(BaseModel):
    """FAQ 検索クエリを受け取るツール"""
    query: str


class Task(BaseModel):
    name: str
    deadline: str


class ProjectRequest(BaseModel):
    project_name: str
    tasks: List[Task]


class Unit(str, Enum):
    celsius = "celsius"
    fahrenheit = "fahrenheit"


class WeatherRequestWithUnit(BaseModel):
    city: str
    date: str
    unit: Unit


class Step(BaseModel):
    explanation: str
    output: str


class MathResponse(BaseModel):
    steps: List[Step]
    final_answer: str


# 02系デモ用のモデル
class PersonInfo(BaseModel):
    name: str
    age: int


class BookInfo(BaseModel):
    title: str
    author: str
    year: int


class ExtractedData(BaseModel):
    persons: List[PersonInfo]
    books: List[BookInfo]


class Operator(str, Enum):
    eq = "="
    ne = "!="
    gt = ">"
    lt = "<"


class Condition(BaseModel):
    column: str
    operator: Operator
    value: Union[str, int]


class Query(BaseModel):
    table: str
    conditions: List[Condition]
    sort_by: str
    ascending: bool


class Priority(str, Enum):
    high = "高"
    medium = "中"
    low = "低"


class TaskWithPriority(BaseModel):
    description: str
    priority: Priority


class MathSolution(BaseModel):
    steps: List[Step]
    answer: str


class QAResponse(BaseModel):
    question: str
    answer: str


# ==================================================
# 基底クラス（改修版）
# ==================================================
class BaseDemo:
    """デモ機能の基底クラス（情報パネル機能付き）"""

    def __init__(self, demo_name: str):
        self.demo_name = demo_name
        self.config = ConfigManager("config.yml")
        self.client = OpenAI()
        self.safe_key = sanitize_key(demo_name)
        self.message_manager = MessageManagerUI(f"messages_{self.safe_key}")

    def initialize(self):
        """共通の初期化処理"""
        st.write(f"#### {self.demo_name}")

    def select_model(self) -> str:
        """モデル選択UI"""
        return UIHelper.select_model(f"model_{self.safe_key}")

    def setup_sidebar(self, selected_model: str):
        """左サイドバーの情報パネル設定"""
        st.sidebar.write("### 📋 情報パネル")

        # 各情報パネルを表示（モデル情報のみ閉じた状態で開始）
        self._show_model_info_collapsed(selected_model)
        InfoPanelManager.show_session_info()
        InfoPanelManager.show_performance_info()
        InfoPanelManager.show_cost_info(selected_model)
        InfoPanelManager.show_debug_panel()
        InfoPanelManager.show_settings()

    def _show_model_info_collapsed(self, selected_model: str):
        """モデル情報パネル（閉じた状態で開始）"""
        with st.sidebar.expander("📊 モデル情報", expanded=False):
            # 基本情報
            limits = TokenManager.get_model_limits(selected_model)
            pricing = config.get("model_pricing", {}).get(selected_model, {})

            col1, col2 = st.columns(2)
            with col1:
                st.write("最大入力", f"{limits['max_tokens']:,}")
            with col2:
                st.write("最大出力", f"{limits['max_output']:,}")

            # 料金情報
            if pricing:
                st.write("**料金（1000トークンあたり）**")
                st.write(f"- 入力: ${pricing.get('input', 0):.5f}")
                st.write(f"- 出力: ${pricing.get('output', 0):.5f}")

            # モデル特性
            if selected_model.startswith("o"):
                st.info("🧠 推論特化モデル")
            elif "audio" in selected_model:
                st.info("🎵 音声対応モデル")
            elif "gpt-4o" in selected_model:
                st.info("👁️ 視覚対応モデル")

    def handle_error(self, e: Exception):
        """エラーハンドリング"""
        error_msg = config.get("error_messages.network_error", "エラーが発生しました")
        st.error(f"{error_msg}: {str(e)}")
        if st.checkbox("詳細を表示", key=f"error_detail_{self.safe_key}"):
            st.exception(e)

    def get_default_messages(self) -> List[EasyInputMessageParam]:
        """デフォルトメッセージの取得"""
        return self.message_manager.get_default_messages()

    def run(self):
        """各デモの実行処理（サブクラスで実装）"""
        raise NotImplementedError("Subclasses must implement run method")


# --------------------------------------------------
# BasicFunctionCallDemo
# --------------------------------------------------
class BasicFunctionCallDemo(BaseDemo):
    """基本的なfunction callのデモ"""

    @error_handler
    def run(self):
        self.initialize()
        model = self.select_model()
        st.write(f"[選択したモデル: {model}]")

        # 情報パネルの設定
        self.setup_sidebar(model)

        st.markdown("#### 基本的な function call の構造化出力例")
        st.code("""
        class WeatherRequest(BaseModel):
            city: str
            date: str
        
        class NewsRequest(BaseModel):
            topic: str
            date: str

        response = self.client.responses.parse(
                    model=model,
                    input=messages,
                    tools=[
                        pydantic_function_tool(WeatherRequest),
                        pydantic_function_tool(NewsRequest)
                    ]
                )""")

        example_query = "東京と大阪の明日の天気と、AIの最新ニュースを教えて"
        # st.write(f"質問例: {example_query}")

        with st.form(key=f"basic_function_form_{self.safe_key}"):
            user_input = st.text_area(
                "質問を入力してください:",
                value=example_query,
                height=config.get("ui.text_area_height", 100)
            )
            submitted = st.form_submit_button("送信")

        if submitted and user_input:
            self._process_query(model, user_input)

    @timer
    def _process_query(self, model: str, user_input: str):
        """クエリの処理"""
        try:
            UIHelper.show_token_info(user_input, model, position="sidebar")

            messages = self.get_default_messages()
            messages.append(EasyInputMessageParam(role="user", content=user_input))

            with st.spinner("処理中..."):
                response = self.client.responses.parse(
                    model=model,
                    input=messages,
                    tools=[
                        pydantic_function_tool(WeatherRequest),
                        pydantic_function_tool(NewsRequest)
                    ]
                )

            st.success("応答を取得しました")

            # Function callsの処理
            self._handle_function_calls(response)

            ResponseProcessorUI.display_response(response)

        except Exception as e:
            self.handle_error(e)

    def _handle_function_calls(self, response):
        """Function callsの処理"""
        city_coords = {
            "東京": {"lat": 35.6895, "lon": 139.69171},
            "大阪": {"lat": 34.6937, "lon": 135.5023}
        }

        for function_call in response.output:
            st.write("**関数呼び出し結果:**")
            st.write(f"関数名: {function_call.name}")
            st.write(f"引数: {function_call.parsed_arguments}")

            if hasattr(function_call.parsed_arguments, "city") and hasattr(function_call.parsed_arguments, "date"):
                city = function_call.parsed_arguments.city
                date = function_call.parsed_arguments.date

                if city in city_coords:
                    self._fetch_weather_data(city, city_coords[city])

    def _fetch_weather_data(self, city: str, coords: Dict[str, float]):
        """天気データの取得"""
        API_key = os.getenv("OPENWEATHER_API_KEY")
        if not API_key:
            st.warning("OPENWEATHER_API_KEY環境変数が設定されていません")
            return

        lat, lon = coords["lat"], coords["lon"]
        url = f"https://api.openweathermap.org/data/2.5/weather?lat={lat}&lon={lon}&appid={API_key}"

        try:
            res = requests.get(url)
            if res.status_code == 200:
                weather_data = res.json()
                st.write(f"**{city}の天気情報:**")
                with st.expander("天気データを表示", expanded=False):
                    st.json(weather_data)
            else:
                st.error(f"天気データの取得に失敗: {res.status_code}")
        except Exception as e:
            st.error(f"天気API呼び出しエラー: {e}")

# --------------------------------------------------
# MultipleToolsDemo
# --------------------------------------------------
class MultipleToolsDemo(BaseDemo):
    """複数ツールの登録・複数関数呼び出しデモ"""

    @error_handler
    def run(self):
        self.initialize()
        model = self.select_model()
        self.setup_sidebar(model)

        st.code("""
class WeatherRequest(BaseModel):
    city: str
    date: str

class NewsRequest(BaseModel):
    topic: str
    date: str
    
response = self.client.responses.parse(
        model=model,
        input=messages,
        tools=[
            pydantic_function_tool(WeatherRequest),
            pydantic_function_tool(NewsRequest)
        ]
    )""")
        st.markdown("##### 複数ツールの同時利用")
        st.write("天気情報とニュース検索を同時に利用")

        example_query = "東京の明日の天気と、AIの最新ニュースを教えて"

        with st.form(key=f"multiple_tools_form_{self.safe_key}"):
            user_input = st.text_area(
                "質問を入力してください:",
                value=example_query,
                height=100
            )
            submitted = st.form_submit_button("送信")

        if submitted and user_input:
            self._process_query(model, user_input)

    @timer
    def _process_query(self, model: str, user_input: str):
        try:
            messages = self.get_default_messages()
            messages.append(EasyInputMessageParam(role="user", content=user_input))

            with st.spinner("処理中..."):
                response = self.client.responses.parse(
                    model=model,
                    input=messages,
                    tools=[
                        pydantic_function_tool(WeatherRequest),
                        pydantic_function_tool(NewsRequest)
                    ]
                )

            st.success("応答を取得しました")

            for function_call in response.output:
                st.write("**関数呼び出し:**")
                st.write(f"関数名: {function_call.name}")
                st.write(f"引数: {function_call.parsed_arguments}")

            ResponseProcessorUI.display_response(response)

        except Exception as e:
            self.handle_error(e)

# --------------------------------------------------
# AdvancedMultipleToolsDemo
# --------------------------------------------------
class AdvancedMultipleToolsDemo(BaseDemo):
    """高度な複数ツール呼び出しデモ"""

    @error_handler
    def run(self):
        self.initialize()
        model = self.select_model()
        self.setup_sidebar(model)

        st.code("""
    messages = self.get_default_messages()
    messages.append(EasyInputMessageParam(role="user", content=user_input))
    
        response = self.client.responses.parse(
            model=model,
            input=messages,
            tools=[
                pydantic_function_tool(CalculatorRequest, name="calculator"),
                pydantic_function_tool(FAQSearchRequest, name="faq_search"),
            ]
        )
        """)

        st.markdown("##### 高度な複数ツール呼び出し")
        st.markdown("##### 計算機とFAQ検索を組み合わせた例")

        example_query = "2.35+2 はいくつですか？"

        with st.form(key=f"advanced_tools_form_{self.safe_key}"):
            user_input = st.text_area(
                "質問を入力してください:",
                value=example_query,
                height=75
            )
            submitted = st.form_submit_button("送信")

        if submitted and user_input:
            self._process_query(model, user_input)

    @timer
    def _process_query(self, model: str, user_input: str):
        try:
            messages = self.get_default_messages()
            messages.append(EasyInputMessageParam(role="user", content=user_input))

            with st.spinner("処理中..."):
                response = self.client.responses.parse(
                    model=model,
                    input=messages,
                    tools=[
                        pydantic_function_tool(CalculatorRequest, name="calculator"),
                        pydantic_function_tool(FAQSearchRequest, name="faq_search"),
                    ]
                )

            st.success("応答を取得しました")

            # Function callsの実行
            for function_call in response.output:
                st.write("**関数呼び出し結果:**")
                st.write(f"関数名: {function_call.name}")

                args = function_call.parsed_arguments
                st.write(f"引数: {args}")

                if function_call.name == "calculator":
                    result = self._calculator(args.exp)
                    st.write(f"計算結果: {result}")
                elif function_call.name == "faq_search":
                    result = self._faq_search(args.query)
                    st.write(f"FAQ検索結果: {result}")

            ResponseProcessorUI.display_response(response)

        except Exception as e:
            self.handle_error(e)

    def _calculator(self, exp: str) -> str:
        """計算式を安全に評価"""
        try:
            return str(eval(exp))
        except Exception as e:
            return f"計算エラー: {e}"

    def _faq_search(self, query: str) -> str:
        """FAQ検索のダミー実装"""
        return f"FAQ回答: {query} ...（ここに検索結果が入る）"

# --------------------------------------------------
# NestedStructureDemo
# --------------------------------------------------
class NestedStructureDemo(BaseDemo):
    """入れ子構造のデモ"""

    @error_handler
    def run(self):
        self.initialize()
        model = self.select_model()
        self.setup_sidebar(model)

        st.markdown("##### 複雑な入れ子構造の処理")
        st.markdown("##### プロジェクトとタスクの階層構造を扱います")
        st.code("""
class ProjectRequest(BaseModel):
    project_name: str
    tasks: List[Task]
                        
response = self.client.responses.parse(
    model=model,
    input=messages,
    tools=[pydantic_function_tool(ProjectRequest)]
)""")

        example_query = "プロジェクト『AI開発』には「設計（明日まで）」「実装（来週まで）」というタスクがある"

        with st.form(key=f"nested_form_{self.safe_key}"):
            user_input = st.text_area(
                "プロジェクト情報を入力してください:",
                value=example_query,
                height=75
            )
            submitted = st.form_submit_button("送信")

        if submitted and user_input:
            self._process_query(model, user_input)

    @timer
    def _process_query(self, model: str, user_input: str):
        try:
            messages = self.get_default_messages()
            messages.append(EasyInputMessageParam(role="user", content=user_input))

            with st.spinner("処理中..."):
                response = self.client.responses.parse(
                    model=model,
                    input=messages,
                    tools=[pydantic_function_tool(ProjectRequest)]
                )

            st.success("応答を取得しました")

            function_call = response.output[0]
            st.write("**プロジェクト情報:**")
            st.write(f"関数名: {function_call.name}")

            project_data = function_call.parsed_arguments
            st.write(f"プロジェクト名: {project_data.project_name}")
            st.write("**タスク一覧:**")
            for i, task in enumerate(project_data.tasks, 1):
                st.write(f"{i}. {task.name} (期限: {task.deadline})")

            ResponseProcessorUI.display_response(response)

        except Exception as e:
            self.handle_error(e)

# --------------------------------------------------
# EnumTypeDemo
# --------------------------------------------------
class EnumTypeDemo(BaseDemo):
    """Enum型のデモ"""

    @error_handler
    def run(self):
        self.initialize()
        model = self.select_model()
        self.setup_sidebar(model)

        st.code("""
    messages = self.get_default_messages()
    messages.append(EasyInputMessageParam(role="user", content=user_input))

    
    response = self.client.responses.parse(
        model=model,
        input=messages,
        tools=[pydantic_function_tool(WeatherRequestWithUnit)]
    )
        """)

        st.write("### Enum型と型安全なパラメータ")
        st.write("温度単位を指定した天気取得")

        example_query = "ニューヨークの明日の天気を華氏で教えて"

        with st.form(key=f"enum_form_{self.safe_key}"):
            user_input = st.text_area(
                "天気の質問を入力してください:",
                value=example_query,
                height=75
            )
            submitted = st.form_submit_button("送信")

        if submitted and user_input:
            self._process_query(model, user_input)

    @timer
    def _process_query(self, model: str, user_input: str):
        try:
            messages = self.get_default_messages()
            messages.append(EasyInputMessageParam(role="user", content=user_input))

            with st.spinner("処理中..."):
                response = self.client.responses.parse(
                    model=model,
                    input=messages,
                    tools=[pydantic_function_tool(WeatherRequestWithUnit)]
                )

            st.success("応答を取得しました")

            function_call = response.output[0]
            st.write("**天気リクエスト情報:**")
            st.write(f"関数名: {function_call.name}")

            weather_req = function_call.parsed_arguments
            st.write(f"都市: {weather_req.city}")
            st.write(f"日付: {weather_req.date}")
            st.write(f"温度単位: {weather_req.unit}")

            ResponseProcessorUI.display_response(response)

        except Exception as e:
            self.handle_error(e)

# --------------------------------------------------
# NaturalTextStructuredOutputDemo
# --------------------------------------------------
class NaturalTextStructuredOutputDemo(BaseDemo):
    """自然文での構造化出力デモ"""

    @error_handler
    def run(self):
        self.initialize()
        model = self.select_model()
        self.setup_sidebar(model)

        st.code("""
    messages = self.get_default_messages()
    messages.append(EasyInputMessageParam(role="user", content=user_input))
    
    response = self.client.responses.parse(
        model=model,
        input=messages,
        text_format=MathResponse
    )
        """)

        st.write("### 自然文での構造化出力")
        st.write("text_format引数を使用した段階的な解答")

        example_query = "8x + 31 = 2 を解いてください。途中計算も教えて"

        with st.form(key=f"natural_text_form_{self.safe_key}"):
            user_input = st.text_area(
                "数学の問題を入力してください:",
                value=example_query,
                height=75
            )
            submitted = st.form_submit_button("送信")

        if submitted and user_input:
            self._process_query(model, user_input)

    @timer
    def _process_query(self, model: str, user_input: str):
        try:
            messages = self.get_default_messages()
            messages.append(EasyInputMessageParam(role="user", content=user_input))

            with st.spinner("処理中..."):
                response = self.client.responses.parse(
                    model=model,
                    input=messages,
                    text_format=MathResponse
                )

            st.success("応答を取得しました")

            for output in response.output:
                if output.type == "message":
                    for item in output.content:
                        if item.type == "output_text" and item.parsed:
                            math_result = item.parsed
                            st.write("**段階的解答:**")
                            for i, step in enumerate(math_result.steps, 1):
                                st.write(f"**手順 {i}:** {step.explanation}")
                                st.write(f"結果: {step.output}")
                            st.write(f"**最終答:** {math_result.final_answer}")

            ResponseProcessorUI.display_response(response)

        except Exception as e:
            self.handle_error(e)


# --------------------------------------------------
# SimpleDataExtractionDemo
# --------------------------------------------------
class SimpleDataExtractionDemo(BaseDemo):
    """シンプルなデータ抽出デモ"""

    @error_handler
    def run(self):
        self.initialize()
        model = self.select_model()
        self.setup_sidebar(model)

        st.code("""
    class PersonInfo(BaseModel):
        name: str
        age: int

    messages = self.get_default_messages()
    messages.append(EasyInputMessageParam(role="user", content=user_input))
    
    response = self.client.responses.parse(
        model=model,
        input=messages,
        text_format=PersonInfo
    )
        """)
        st.write("### シンプルな構造化データ抽出")
        st.write("人物情報を抽出します")

        example_query = "彼女の名前は中島美咲で年齢は27歳です。"

        with st.form(key=f"simple_extraction_form_{self.safe_key}"):
            user_input = st.text_area(
                "人物情報を含むテキストを入力してください:",
                value=example_query,
                height=75
            )
            submitted = st.form_submit_button("送信")

        if submitted and user_input:
            self._process_query(model, user_input)

    @timer
    def _process_query(self, model: str, user_input: str):
        try:
            messages = self.get_default_messages()
            messages.append(EasyInputMessageParam(role="user", content=user_input))

            with st.spinner("処理中..."):
                response = self.client.responses.parse(
                    model=model,
                    input=messages,
                    text_format=PersonInfo
                )

            st.success("応答を取得しました")

            person = response.output[0].content[0].parsed
            st.write("**抽出された人物情報:**")
            st.write(f"名前: {person.name}")
            st.write(f"年齢: {person.age}")

            ResponseProcessorUI.display_response(response)

        except Exception as e:
            self.handle_error(e)

# --------------------------------------------------
# MultipleEntityExtractionDemo
# --------------------------------------------------
class MultipleEntityExtractionDemo(BaseDemo):
    """複数エンティティ抽出デモ"""

    @error_handler
    def run(self):
        self.initialize()
        model = self.select_model()
        self.setup_sidebar(model)

        st.write("### 複数エンティティの同時抽出")
        st.write("人物と書籍の情報を同時に抽出")

        example_text = """登場人物:
- 中島美嘉 (27歳)
- 田中亮 (34歳)

おすすめ本:
1. 『Pythonプロフェッショナル大全』   著者: 酒井 潤  (2022年)
2. 『LangChainとLangGraphによるRAG・AIエージェント［実践］入門』   著者: 西見 公宏, 吉田 真吾, 大嶋 勇樹  (2024年)"""

        with st.form(key=f"multiple_entity_form_{self.safe_key}"):
            user_input = st.text_area(
                "人物と書籍の情報を含むテキストを入力してください:",
                value=example_text,
                height=150
            )
            submitted = st.form_submit_button("送信")

        if submitted and user_input:
            self._process_query(model, user_input)

    @timer
    def _process_query(self, model: str, user_input: str):
        try:
            messages = self.get_default_messages()
            messages.append(EasyInputMessageParam(role="user", content=user_input))

            with st.spinner("処理中..."):
                response = self.client.responses.parse(
                    model=model,
                    input=messages,
                    text_format=ExtractedData
                )

            st.success("応答を取得しました")

            extracted = response.output[0].content[0].parsed

            st.write("### 抽出結果")

            col1, col2 = st.columns(2)

            with col1:
                st.write("**人物一覧**")
                for person in extracted.persons:
                    st.write(f"- {person.name} ({person.age}歳)")

            with col2:
                st.write("**書籍一覧**")
                for book in extracted.books:
                    st.write(f"- 『{book.title}』")
                    st.write(f"  著者: {book.author} ({book.year}年)")

            ResponseProcessorUI.display_response(response)

        except Exception as e:
            self.handle_error(e)

# --------------------------------------------------
# ComplexQueryDemo
# --------------------------------------------------
class ComplexQueryDemo(BaseDemo):
    """複雑なクエリパターンデモ"""

    @error_handler
    def run(self):
        self.initialize()
        model = self.select_model()
        self.setup_sidebar(model)

        st.write("### 複雑なクエリパターン")
        st.write("SQL風の条件指定とソート")

        example_query = "ユーザーテーブルから年齢が20歳以上で東京在住の人を名前で昇順にソートして"

        with st.form(key=f"complex_query_form_{self.safe_key}"):
            user_input = st.text_area(
                "クエリ条件を入力してください:",
                value=example_query,
                height=75
            )
            submitted = st.form_submit_button("送信")

        if submitted and user_input:
            self._process_query(model, user_input)

    @timer
    def _process_query(self, model: str, user_input: str):
        try:
            messages = self.get_default_messages()
            messages.append(EasyInputMessageParam(role="user", content=user_input))

            with st.spinner("処理中..."):
                response = self.client.responses.parse(
                    model=model,
                    input=messages,
                    text_format=Query
                )

            st.success("応答を取得しました")

            query = response.output[0].content[0].parsed

            st.write("**クエリ情報:**")
            st.write(f"テーブル: {query.table}")
            st.write(f"ソート列: {query.sort_by}")
            st.write(f"昇順: {query.ascending}")

            st.write("**条件一覧:**")
            for i, condition in enumerate(query.conditions, 1):
                st.write(f"{i}. {condition.column} {condition.operator} {condition.value}")

            ResponseProcessorUI.display_response(response)

        except Exception as e:
            self.handle_error(e)

# --------------------------------------------------
# ComplexQueryDemo
# --------------------------------------------------
class DynamicEnumDemo(BaseDemo):
    """動的な列挙型デモ"""

    @error_handler
    def run(self):
        self.initialize()
        model = self.select_model()
        self.setup_sidebar(model)

        st.write("### 動的な列挙型の利用")
        st.write("優先度付きタスクの管理")

        example_query = "サーバーの再起動を最優先でお願い"

        with st.form(key=f"dynamic_enum_form_{self.safe_key}"):
            user_input = st.text_area(
                "タスクの依頼を入力してください:",
                value=example_query,
                height=75
            )
            submitted = st.form_submit_button("送信")

        if submitted and user_input:
            self._process_query(model, user_input)

    @timer
    def _process_query(self, model: str, user_input: str):
        try:
            messages = self.get_default_messages()
            messages.append(EasyInputMessageParam(role="user", content=user_input))

            with st.spinner("処理中..."):
                response = self.client.responses.parse(
                    model=model,
                    input=messages,
                    text_format=TaskWithPriority
                )

            st.success("応答を取得しました")

            task = response.output[0].content[0].parsed

            st.write("**タスク情報:**")
            st.write(f"説明: {task.description}")
            st.write(f"優先度: {task.priority}")

            # 優先度に応じた表示色
            if task.priority == Priority.high:
                st.error(f"🚨 高優先度: {task.description}")
            elif task.priority == Priority.medium:
                st.warning(f"⚠️ 中優先度: {task.description}")
            else:
                st.info(f"ℹ️ 低優先度: {task.description}")

            ResponseProcessorUI.display_response(response)

        except Exception as e:
            self.handle_error(e)

# --------------------------------------------------
# ChainOfThoughtDemo
# --------------------------------------------------
class ChainOfThoughtDemo(BaseDemo):
    """思考の連鎖デモ"""

    @error_handler
    def run(self):
        self.initialize()
        model = self.select_model()
        self.setup_sidebar(model)

        st.write("### 思考の連鎖（Chain of Thought）")
        st.write("段階的な問題解決過程を表示")

        example_query = "美味しいチョコレートケーキを作りたい。"

        with st.form(key=f"chain_of_thought_form_{self.safe_key}"):
            user_input = st.text_area(
                "解決したい問題を入力してください:",
                value=example_query,
                height=75
            )
            submitted = st.form_submit_button("送信")

        if submitted and user_input:
            self._process_query(model, user_input)

    @timer
    def _process_query(self, model: str, user_input: str):
        try:
            messages = self.get_default_messages()
            messages.append(EasyInputMessageParam(role="user", content=user_input))

            with st.spinner("処理中..."):
                response = self.client.responses.parse(
                    model=model,
                    input=messages,
                    text_format=MathSolution
                )

            st.success("応答を取得しました")

            solution = response.output[0].content[0].parsed

            st.write("### 解決手順")
            for i, step in enumerate(solution.steps, 1):
                with st.expander(f"手順 {i}: {step.explanation}", expanded=True):
                    st.write(f"**説明:** {step.explanation}")
                    st.write(f"**実行内容:** {step.output}")

            st.success(f"**最終解:** {solution.answer}")

            ResponseProcessorUI.display_response(response)

        except Exception as e:
            self.handle_error(e)

# --------------------------------------------------
# ConversationHistoryDemo
# --------------------------------------------------
class ConversationHistoryDemo(BaseDemo):
    """会話履歴デモ"""

    @error_handler
    def run(self):
        self.initialize()
        model = self.select_model()
        self.setup_sidebar(model)

        st.write("### 会話履歴を持った連続した構造化出力")
        st.write("前の質問を記憶した連続対話")

        # 会話履歴の初期化
        if f"qa_history_{self.safe_key}" not in st.session_state:
            st.session_state[f"qa_history_{self.safe_key}"] = []

        with st.form(key=f"conversation_form_{self.safe_key}"):
            user_input = st.text_area(
                "質問を入力してください:",
                placeholder="例: Pythonの用途を教えてください",
                height=75
            )
            submitted = st.form_submit_button("送信")

        if submitted and user_input:
            self._process_query(model, user_input)

        # 会話履歴の表示
        history = st.session_state[f"qa_history_{self.safe_key}"]
        if history:
            st.write("### 会話履歴")
            for i, qa in enumerate(history, 1):
                with st.expander(f"会話 {i}: {qa.question[:50]}...", expanded=False):
                    st.write(f"**質問:** {qa.question}")
                    st.write(f"**回答:** {qa.answer}")

        if st.button("会話履歴をクリア", key=f"clear_history_{self.safe_key}"):
            st.session_state[f"qa_history_{self.safe_key}"] = []
            st.rerun()

    @timer
    def _process_query(self, model: str, user_input: str):
        try:
            messages = self.get_default_messages()
            messages.append(EasyInputMessageParam(role="user", content=user_input))

            with st.spinner("処理中..."):
                response = self.client.responses.parse(
                    model=model,
                    input=messages,
                    text_format=QAResponse
                )

            st.success("応答を取得しました")

            qa = response.output[0].content[0].parsed

            # 履歴に追加
            st.session_state[f"qa_history_{self.safe_key}"].append(qa)

            st.write("### 最新の回答")
            st.write(f"**質問:** {qa.question}")
            st.write(f"**回答:** {qa.answer}")

            ResponseProcessorUI.display_response(response)

        except Exception as e:
            self.handle_error(e)


# ==================================================
# デモマネージャー（改修版）
# ==================================================
class DemoManager:
    """デモの管理クラス（改修版）"""

    def __init__(self):
        self.config = ConfigManager("config.yml")
        self.demos = self._initialize_demos()

    def _initialize_demos(self) -> Dict[str, BaseDemo]:
        """デモインスタンスの初期化"""
        return {
            "シンプルデータ抽出": SimpleDataExtractionDemo("SimpleDataExtraction"),
            "基本的なFunction Call": BasicFunctionCallDemo("BasicFunctionCall"),
            "入れ子構造"           : NestedStructureDemo("NestedStructure"),
            "Enum型"               : EnumTypeDemo("EnumType"),
            "自然文構造化出力"     : NaturalTextStructuredOutputDemo("NaturalTextStructured"),

            "複数エンティティ抽出" : MultipleEntityExtractionDemo("MultipleEntityExtraction"),
            "複雑なクエリ"         : ComplexQueryDemo("ComplexQuery"),
            "動的Enum"             : DynamicEnumDemo("DynamicEnum"),
            "思考の連鎖(CoT)"           : ChainOfThoughtDemo("ChainOfThought"),
            "会話履歴"             : ConversationHistoryDemo("ConversationHistory"),
        }

    def run(self):
        """アプリケーションの実行"""
        UIHelper.init_page()

        # デモ選択
        demo_name = st.sidebar.radio(
            "デモを選択",
            list(self.demos.keys()),
            key="demo_selection"
        )

        # セッション状態の更新
        if "current_demo" not in st.session_state:
            st.session_state.current_demo = demo_name
        elif st.session_state.current_demo != demo_name:
            st.session_state.current_demo = demo_name

        # 選択されたデモの実行
        demo = self.demos.get(demo_name)
        if demo:
            try:
                demo.run()
            except Exception as e:
                st.error(f"デモの実行中にエラーが発生しました: {str(e)}")
                if st.checkbox("詳細なエラー情報を表示"):
                    st.exception(e)
        else:
            st.error(f"デモ '{demo_name}' が見つかりません")

        # フッター情報
        self._display_footer()

    def _display_footer(self):
        """フッター情報の表示"""
        st.sidebar.markdown("---")
        st.sidebar.markdown("### 情報")

        # 現在の設定情報
        with st.sidebar.expander("現在の設定"):
            st.json({
                "default_model": self.config.get("models.default"),
                "api_timeout"  : self.config.get("api.timeout"),
                "ui_layout"    : self.config.get("ui.layout"),
            })

        # バージョン情報
        st.sidebar.markdown("### バージョン")
        st.sidebar.markdown("- OpenAI Tools & Pydantic Parse Demo v1.0")
        st.sidebar.markdown("- Streamlit " + st.__version__)

        # リンク
        st.sidebar.markdown("### リンク")
        st.sidebar.markdown("[OpenAI API ドキュメント](https://platform.openai.com/docs)")
        st.sidebar.markdown("[Streamlit ドキュメント](https://docs.streamlit.io)")


# ==================================================
# メイン関数（改修版）
# ==================================================
def main():
    """アプリケーションのエントリーポイント（改修版）"""

    # (1) ロギングの設定
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    # (2) 環境変数のチェック
    if not os.getenv("OPENAI_API_KEY"):
        st.error("環境変数 OPENAI_API_KEY が設定されていません。")
        st.info("export OPENAI_API_KEY='your-api-key' を実行してください。")
        st.stop()

    # OPENWEATHER_API_KEY の警告（オプション）
    if not os.getenv("OPENWEATHER_API_KEY"):
        st.sidebar.warning("OPENWEATHER_API_KEY が未設定です。天気機能は制限されます。")

    # (3) セッション状態の初期化
    SessionStateManager.init_session_state()

    # (4) デモマネージャーの作成と実行
    try:
        manager = DemoManager()
        manager.run()
    except Exception as e:
        st.error(f"アプリケーションの起動に失敗しました: {str(e)}")
        st.exception(e)


if __name__ == "__main__":
    main()

# streamlit run a10_02_responses_tools_pydantic_parse.py --server.port=8502
