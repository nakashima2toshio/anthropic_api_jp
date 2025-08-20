# streamlit run a01_structured_outputs_parse_schema.py --server.port=8501
# --------------------------------------------------
# OpenAI Structured Outputs Parse Schema デモアプリケーション（統一化版）
# Streamlitを使用したインタラクティブなAPIテストツール
# 統一化版: a10_00_responses_api.pyの構成・構造・ライブラリ・エラー処理の完全統一
# --------------------------------------------------
import os
import sys
import json
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
            page_title=config.get("ui.page_title", "OpenAI Structured Outputs Parse Schema デモ"),
            page_icon=config.get("ui.page_icon", "🗂️"),
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
def setup_common_ui(demo_name: str) -> str:
    """共通UI設定（統一化版）"""
    safe_key = sanitize_key(demo_name)

    # ヘッダー表示
    st.write(f"# {demo_name}")

    # モデル選択（統一されたUI）
    model = UIHelper.select_model(f"model_{safe_key}")
    st.write("選択したモデル:", model)

    return model


def setup_sidebar_panels(selected_model: str):
    """サイドバーパネルの統一設定（helper_st.pyのInfoPanelManagerを使用）"""
    st.sidebar.write("### 📋 情報パネル")

    InfoPanelManager.show_model_info(selected_model)
    InfoPanelManager.show_session_info()
    InfoPanelManager.show_performance_info()
    InfoPanelManager.show_cost_info(selected_model)
    InfoPanelManager.show_debug_panel()
    InfoPanelManager.show_settings()


# ==================================================
# 基底クラス（統一化版）
# ==================================================
class BaseDemo(ABC):
    """デモ機能の基底クラス（統一化版）"""

    def __init__(self, demo_name: str):
        self.demo_name = demo_name
        self.config = ConfigManager("config.yml")

        # OpenAIクライアントの初期化（統一されたエラーハンドリング）
        try:
            self.client = OpenAIClient()
        except Exception as e:
            st.error(f"OpenAIクライアントの初期化に失敗しました: {e}")
            st.stop()

        self.safe_key = sanitize_key(demo_name)
        self.message_manager = MessageManagerUI(f"messages_{self.safe_key}")
        self.model = None

        # セッション状態の初期化（統一化）
        SessionStateManager.init_session_state()
        self._initialize_session_state()

    def _initialize_session_state(self):
        """セッション状態の統一的初期化"""
        session_key = f"demo_state_{self.safe_key}"
        if session_key not in st.session_state:
            st.session_state[session_key] = {
                'initialized'    : True,
                'model'          : self.config.get("models.default", "gpt-4o-mini"),
                'execution_count': 0
            }

    def get_model(self) -> str:
        """選択されたモデルを取得（統一化）"""
        return st.session_state.get(f"model_{self.safe_key}",
                                    config.get("models.default", "gpt-4o-mini"))

    def is_reasoning_model(self, model: str = None) -> bool:
        """推論系モデルかどうかを判定（統一化）"""
        if model is None:
            model = self.get_model()

        # config.ymlから取得、フォールバックあり
        reasoning_models = config.get("models.categories.reasoning",
                                      ["o1", "o1-mini", "o3", "o3-mini", "o4", "o4-mini"])
        
        # GPT-5系モデルも推論系として扱う（temperatureサポートなし）
        frontier_models = config.get("models.categories.frontier",
                                    ["gpt-5", "gpt-5-mini", "gpt-5-nano"])

        # モデル名に推論系モデルの識別子が含まれているかチェック
        reasoning_indicators = ["o1", "o3", "o4", "gpt-5"]
        return any(indicator in model.lower() for indicator in reasoning_indicators) or \
            any(reasoning_model in model for reasoning_model in reasoning_models) or \
            any(frontier_model in model for frontier_model in frontier_models)

    def create_temperature_control(self, default_temp: float = 0.3, help_text: str = None) -> Optional[float]:
        """Temperatureコントロールを作成（統一化・推論系モデル・GPT-5系では無効化）"""
        model = self.get_model()

        if self.is_reasoning_model(model):
            st.info("ℹ️ 推論系モデル（o1, o3, o4, gpt-5系）ではtemperatureパラメータは使用されません")
            return None
        else:
            return st.slider(
                "Temperature",
                0.0, 1.0, default_temp, 0.05,
                help=help_text or "低い値ほど一貫性のある回答"
            )

    def initialize(self):
        """共通の初期化処理（統一化）"""
        self.model = setup_common_ui(self.demo_name)
        setup_sidebar_panels(self.model)

    def handle_error(self, e: Exception):
        """統一的エラーハンドリング"""
        # 多言語対応エラーメッセージ
        lang = config.get("i18n.default_language", "ja")
        error_msg = config.get(f"error_messages.{lang}.general_error", "エラーが発生しました")
        st.error(f"{error_msg}: {str(e)}")

        if config.get("experimental.debug_mode", False):
            with st.expander("🔧 詳細エラー情報", expanded=False):
                st.exception(e)

    def show_debug_info(self):
        """デバッグ情報の統一表示"""
        if st.sidebar.checkbox("🔧 デモ状態を表示", value=False, key=f"debug_{self.safe_key}"):
            with st.sidebar.expander("デモデバッグ情報", expanded=False):
                st.write(f"**デモ名**: {self.demo_name}")
                st.write(f"**選択モデル**: {self.model}")

                session_state = st.session_state.get(f"demo_state_{self.safe_key}", {})
                st.write(f"**実行回数**: {session_state.get('execution_count', 0)}")

    @error_handler_ui
    @timer_ui
    def call_api_parse(self, input_text: str, text_format: BaseModel, temperature: Optional[float] = None, **kwargs):
        """統一されたresponses.parse API呼び出し（temperatureパラメータ対応）"""
        model = self.get_model()

        # API呼び出しパラメータの準備
        api_params = {
            "input": input_text,
            "model": model,
            "text_format": text_format
        }

        # temperatureサポートチェック（reasoning系モデルは除外）
        if not self.is_reasoning_model(model) and temperature is not None:
            api_params["temperature"] = temperature

        # その他のパラメータ
        api_params.update(kwargs)

        # responses.parse を使用（統一されたAPI呼び出し）
        openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        return openai_client.responses.parse(**api_params)

    @abstractmethod
    def run(self):
        """各デモの実行処理（サブクラスで実装）"""
        pass


# ==================================================
# Pydantic モデル定義（統一化版）
# ==================================================

# 1. イベント情報抽出
class EventInfo(BaseModel):
    """イベント情報のPydanticモデル"""
    name: str = Field(..., description="イベント名")
    date: str = Field(..., description="開催日")
    participants: List[str] = Field(..., description="参加者一覧")


# 2. 数学的思考ステップ
class Step(BaseModel):
    """思考ステップの単位"""
    explanation: str = Field(..., description="このステップでの説明")
    output: str = Field(..., description="このステップの計算結果")


class MathReasoning(BaseModel):
    """数学的思考プロセス"""
    steps: List[Step] = Field(..., description="逐次的な解法ステップ")
    final_answer: str = Field(..., description="最終解")


# 3. UIコンポーネント生成
class UIAttribute(BaseModel):
    """UI属性"""
    name: str = Field(..., description="属性名")
    value: str = Field(..., description="属性値")


class UIComponent(BaseModel):
    """UIコンポーネント（再帰構造）"""
    type: str = Field(..., description="コンポーネント種類 (div/button など)")
    label: str = Field(..., description="表示ラベル")
    children: List["UIComponent"] = Field(default_factory=list, description="子要素")
    attributes: List[UIAttribute] = Field(default_factory=list, description="属性のリスト")

    model_config = {"extra": "forbid"}  # 余計なキーを拒否


UIComponent.model_rebuild()  # 再帰型を解決


# 4. エンティティ抽出
class Entities(BaseModel):
    """エンティティ抽出結果"""
    attributes: List[str] = Field(default_factory=list, description="形容詞・特徴")
    colors: List[str] = Field(default_factory=list, description="色")
    animals: List[str] = Field(default_factory=list, description="動物")


# 5. 条件分岐スキーマ
class UserInfo(BaseModel):
    """ユーザー情報"""
    name: str = Field(..., description="名前")
    age: int = Field(..., description="年齢")


class Address(BaseModel):
    """住所情報"""
    number: str = Field(..., description="番地")
    street: str = Field(..., description="通り")
    city: str = Field(..., description="市")


class ConditionalItem(BaseModel):
    """条件分岐アイテム"""
    item: Union[UserInfo, Address] = Field(..., description="ユーザー情報または住所")
    model_config = {"extra": "forbid"}


# 6. モデレーション＆拒否処理
class ModerationResult(BaseModel):
    """モデレーション結果"""
    refusal: str = Field(..., description="拒否する場合は理由、問題なければ空文字")
    content: Optional[str] = Field(None, description="許可された場合の応答コンテンツ")

    model_config = {"extra": "forbid"}


# ==================================================
# デモクラス実装（統一化版）
# ==================================================

class EventExtractionDemo(BaseDemo):
    """イベント情報抽出デモ（統一化版）"""

    @error_handler_ui
    @timer_ui
    def run(self):
        """デモの実行（統一化版）"""
        self.initialize()
        
        with st.expander("OpenAI API(responses.parse):実装例", expanded=False):
            st.write(
                "responses.parse()の構造化出力デモ。PydanticモデルのEventInfoに基づいてイベント情報を抽出。"
                "テキストから名前・日付・参加者を自動的に構造化データとして取得。"
            )
            st.code("""
            # Pydanticモデル定義
            class EventInfo(BaseModel):
                name: str = Field(..., description="イベント名")
                date: str = Field(..., description="開催日")
                participants: List[str] = Field(..., description="参加者一覧")

            # responses.parse API呼び出し
            response = self.call_api_parse(
                input_text=user_text,
                text_format=EventInfo,
                temperature=temperature
            )
            event_info = response.output_parsed
            """)

        # デフォルトテキスト
        default_text = config.get("samples.prompts.event_example",
                                 "台湾フェス2025 ～あつまれ！究極の台湾グルメ～ 開催日：5/3・5/4 参加者：王さん、林さん、佐藤さん")

        st.write(f"**質問例**: {default_text}")

        with st.form(key=f"event_form_{self.safe_key}"):
            user_text = st.text_area(
                "イベント詳細を入力してください:",
                value=default_text,
                height=config.get("ui.text_area_height", 75)
            )

            # 統一されたtemperatureコントロール
            temperature = self.create_temperature_control(
                default_temp=0.1,
                help_text="構造化出力では低い値を推奨"
            )

            submitted = st.form_submit_button("実行：イベント抽出")

        if submitted and user_text:
            self._process_extraction(user_text, temperature)

        self.show_debug_info()

    def _process_extraction(self, user_text: str, temperature: Optional[float]):
        """イベント抽出の処理（統一化版）"""
        # 実行回数を更新
        session_key = f"demo_state_{self.safe_key}"
        if session_key in st.session_state:
            st.session_state[session_key]['execution_count'] += 1

        # トークン情報の表示
        UIHelper.show_token_info(user_text, self.model, position="sidebar")

        try:
            with st.spinner("イベント情報を抽出中..."):
                response = self.call_api_parse(
                    input_text=user_text,
                    text_format=EventInfo,
                    temperature=temperature
                )

            st.success("✅ イベント情報の抽出が完了しました")
            
            # 結果表示
            event_info = response.output_parsed
            self._display_event_result(event_info, response)

        except (ValidationError, json.JSONDecodeError) as e:
            st.error("❌ 構造化データの解析に失敗しました")
            with st.expander("🔧 エラー詳細", expanded=False):
                st.exception(e)
        except Exception as e:
            self.handle_error(e)

    def _display_event_result(self, event_info: EventInfo, response):
        """イベント抽出結果の表示"""
        st.subheader("📋 抽出結果")
        
        col1, col2 = st.columns([2, 1])
        
        with col1:
            # イベント情報を見やすく表示
            st.write("**🎉 イベント名**")
            st.success(event_info.name)

            st.write("**📅 開催日**")
            st.info(event_info.date)

            st.write("**👥 参加者**")
            if event_info.participants:
                for i, participant in enumerate(event_info.participants, 1):
                    st.write(f"{i}. {participant}")
            else:
                st.write("参加者情報なし")

        with col2:
            # 統計情報
            st.metric("参加者数", len(event_info.participants))
            if hasattr(response, 'usage') and response.usage:
                usage = response.usage
                if hasattr(usage, 'total_tokens'):
                    st.metric("使用トークン数", getattr(usage, 'total_tokens', 0))

        # 構造化データの表示
        st.write("---")
        st.write("**🔧 構造化データ (Pydantic):**")
        safe_streamlit_json(event_info.model_dump())


class MathReasoningDemo(BaseDemo):
    """数学的思考ステップデモ（統一化版）"""

    @error_handler_ui
    @timer_ui
    def run(self):
        """デモの実行（統一化版）"""
        self.initialize()
        
        with st.expander("OpenAI API(responses.parse):実装例", expanded=False):
            st.write(
                "responses.parse()の数学的推論デモ。MathReasoningモデルで段階的な解法プロセスを構造化。"
                "複雑な数式を逐次的なステップに分解し、各段階の説明と計算結果を取得。"
            )
            st.code("""
            # Pydanticモデル定義
            class Step(BaseModel):
                explanation: str = Field(..., description="このステップでの説明")
                output: str = Field(..., description="このステップの計算結果")

            class MathReasoning(BaseModel):
                steps: List[Step] = Field(..., description="逐次的な解法ステップ")
                final_answer: str = Field(..., description="最終解")

            # responses.parse API呼び出し
            prompt = f"Solve the equation {expression} step by step..."
            response = self.call_api_parse(
                input_text=prompt,
                text_format=MathReasoning,
                temperature=temperature
            )
            """)

        default_expression = "8x + 7 = -23"
        st.write(f"**質問例**: {default_expression}")

        with st.form(key=f"math_form_{self.safe_key}"):
            expression = st.text_input(
                "解きたい式を入力してください:",
                value=default_expression
            )

            # 統一されたtemperatureコントロール
            temperature = self.create_temperature_control(
                default_temp=0.2,
                help_text="数学的推論では低めの値を推奨"
            )

            submitted = st.form_submit_button("実行：思考ステップ生成")

        if submitted and expression:
            self._process_math_reasoning(expression, temperature)

        self.show_debug_info()

    def _process_math_reasoning(self, expression: str, temperature: Optional[float]):
        """数学推論の処理（統一化版）"""
        # 実行回数を更新
        session_key = f"demo_state_{self.safe_key}"
        if session_key in st.session_state:
            st.session_state[session_key]['execution_count'] += 1

        prompt = (
            "You are a skilled math tutor. "
            f"Solve the equation {expression} step by step. "
            "Return the reasoning as a JSON that matches the MathReasoning schema. "
            "Provide clear explanations for each step in Japanese."
        )

        try:
            with st.spinner("数学的推論を実行中..."):
                response = self.call_api_parse(
                    input_text=prompt,
                    text_format=MathReasoning,
                    temperature=temperature
                )

            st.success("✅ 思考ステップの生成が完了しました")
            
            # 結果表示
            math_result = response.output_parsed
            self._display_math_result(math_result, response)

        except Exception as e:
            self.handle_error(e)

    def _display_math_result(self, math_result: MathReasoning, response):
        """数学推論結果の表示"""
        st.subheader("🧮 思考ステップ")
        
        # 各ステップの表示
        for i, step in enumerate(math_result.steps, 1):
            with st.expander(f"ステップ {i}: {step.output}", expanded=True):
                st.write("**説明:**")
                st.write(step.explanation)
                st.write("**計算結果:**")
                st.code(step.output)

        # 最終回答
        st.subheader("🎯 最終回答")
        st.success(math_result.final_answer)

        # 構造化データの表示
        st.write("---")
        st.write("**🔧 構造化データ (Pydantic):**")
        safe_streamlit_json(math_result.model_dump())


class UIGenerationDemo(BaseDemo):
    """UIコンポーネント生成デモ（統一化版）"""

    @error_handler_ui
    @timer_ui
    def run(self):
        """デモの実行（統一化版）"""
        self.initialize()
        
        with st.expander("OpenAI API(responses.parse):実装例", expanded=False):
            st.write(
                "responses.parse()のUI生成デモ。UIComponentモデルで再帰的なコンポーネント構造を生成。"
                "自然言語の要求からHTML/React風のコンポーネント階層を自動生成。"
            )
            st.code("""
            # Pydanticモデル定義（再帰構造）
            class UIComponent(BaseModel):
                type: str = Field(..., description="コンポーネント種類")
                label: str = Field(..., description="表示ラベル")
                children: List["UIComponent"] = Field(default_factory=list)
                attributes: List[UIAttribute] = Field(default_factory=list)

            # responses.parse API呼び出し
            prompt = f"Generate a recursive UI component tree: {request}"
            response = self.call_api_parse(
                input_text=prompt,
                text_format=UIComponent,
                temperature=temperature
            )
            """)

        default_request = "ログインフォーム（メールアドレスとパスワード入力欄、ログインボタン）"
        st.write(f"**質問例**: {default_request}")

        with st.form(key=f"ui_form_{self.safe_key}"):
            ui_request = st.text_area(
                "生成したいUIを説明してください:",
                value=default_request,
                height=config.get("ui.text_area_height", 75)
            )

            # 統一されたtemperatureコントロール
            temperature = self.create_temperature_control(
                default_temp=0.3,
                help_text="UI生成では適度なクリエイティビティを推奨"
            )

            submitted = st.form_submit_button("実行：UI生成")

        if submitted and ui_request:
            self._process_ui_generation(ui_request, temperature)

        self.show_debug_info()

    def _process_ui_generation(self, ui_request: str, temperature: Optional[float]):
        """UI生成の処理（統一化版）"""
        # 実行回数を更新
        session_key = f"demo_state_{self.safe_key}"
        if session_key in st.session_state:
            st.session_state[session_key]['execution_count'] += 1

        prompt = (
            "You are a front-end architect. "
            "Generate a recursive UI component tree in JSON that matches the UIComponent schema. "
            "Design the UI requested below, providing Japanese labels and appropriate component types:\n"
            f"{ui_request}"
        )

        try:
            with st.spinner("UIコンポーネントを生成中..."):
                response = self.call_api_parse(
                    input_text=prompt,
                    text_format=UIComponent,
                    temperature=temperature
                )

            st.success("✅ UIコンポーネントの生成が完了しました")
            
            # 結果表示
            ui_result = response.output_parsed
            self._display_ui_result(ui_result, response)

        except Exception as e:
            self.handle_error(e)

    def _display_ui_result(self, ui_result: UIComponent, response):
        """UI生成結果の表示"""
        st.subheader("🎨 生成されたUIスキーマ")
        
        # UIコンポーネントの可視化
        self._render_ui_component(ui_result, level=0)

        # 構造化データの表示
        st.write("---")
        st.write("**🔧 構造化データ (Pydantic):**")
        safe_streamlit_json(ui_result.model_dump())

    def _render_ui_component(self, component: UIComponent, level: int = 0):
        """UIコンポーネントの再帰的レンダリング"""
        indent = "  " * level
        
        # コンポーネント情報の表示
        with st.container():
            cols = st.columns([1, 3, 2])
            with cols[0]:
                st.write(f"{indent}📦")
            with cols[1]:
                st.write(f"**{component.type}**: {component.label}")
            with cols[2]:
                if component.attributes:
                    attr_str = ", ".join([f"{attr.name}={attr.value}" for attr in component.attributes])
                    st.caption(f"属性: {attr_str}")

        # 子コンポーネントの表示
        for child in component.children:
            self._render_ui_component(child, level + 1)


class EntityExtractionDemo(BaseDemo):
    """エンティティ抽出デモ（統一化版）"""

    @error_handler_ui
    @timer_ui
    def run(self):
        """デモの実行（統一化版）"""
        self.initialize()
        
        with st.expander("OpenAI API(responses.parse):実装例", expanded=False):
            st.write(
                "responses.parse()のエンティティ抽出デモ。Entitiesモデルで複数カテゴリの要素を抽出。"
                "自然言語テキストから属性・色・動物などの特定エンティティを分類・抽出。"
            )
            st.code("""
            # Pydanticモデル定義
            class Entities(BaseModel):
                attributes: List[str] = Field(default_factory=list, description="形容詞・特徴")
                colors: List[str] = Field(default_factory=list, description="色")
                animals: List[str] = Field(default_factory=list, description="動物")

            # responses.parse API呼び出し
            prompt = f"Extract entities from: {text}"
            response = self.call_api_parse(
                input_text=prompt,
                text_format=Entities,
                temperature=temperature
            )
            """)

        default_text = "The quick brown fox jumps over the lazy dog with piercing blue eyes."
        st.write(f"**質問例**: {default_text}")

        with st.form(key=f"entity_form_{self.safe_key}"):
            text = st.text_input(
                "抽出対象テキストを入力してください:",
                value=default_text
            )

            # 統一されたtemperatureコントロール
            temperature = self.create_temperature_control(
                default_temp=0.1,
                help_text="エンティティ抽出では低い値を推奨"
            )

            submitted = st.form_submit_button("実行：エンティティ抽出")

        if submitted and text:
            self._process_entity_extraction(text, temperature)

        self.show_debug_info()

    def _process_entity_extraction(self, text: str, temperature: Optional[float]):
        """エンティティ抽出の処理（統一化版）"""
        # 実行回数を更新
        session_key = f"demo_state_{self.safe_key}"
        if session_key in st.session_state:
            st.session_state[session_key]['execution_count'] += 1

        prompt = (
            "Extract three kinds of entities from the text below:\n"
            "- attributes (形容詞・特徴)\n"
            "- colors\n"
            "- animals\n\n"
            "Return the result as JSON that matches the Entities schema.\n\n"
            f"TEXT:\n{text}"
        )

        try:
            with st.spinner("エンティティを抽出中..."):
                response = self.call_api_parse(
                    input_text=prompt,
                    text_format=Entities,
                    temperature=temperature
                )

            st.success("✅ エンティティ抽出が完了しました")
            
            # 結果表示
            entities = response.output_parsed
            self._display_entity_result(entities, response)

        except Exception as e:
            self.handle_error(e)

    def _display_entity_result(self, entities: Entities, response):
        """エンティティ抽出結果の表示"""
        st.subheader("🏷️ 抽出結果")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.write("**📝 属性・特徴**")
            if entities.attributes:
                for attr in entities.attributes:
                    st.write(f"• {attr}")
            else:
                st.write("なし")

        with col2:
            st.write("**🎨 色**")
            if entities.colors:
                for color in entities.colors:
                    st.write(f"• {color}")
            else:
                st.write("なし")

        with col3:
            st.write("**🐾 動物**")
            if entities.animals:
                for animal in entities.animals:
                    st.write(f"• {animal}")
            else:
                st.write("なし")

        # 構造化データの表示
        st.write("---")
        st.write("**🔧 構造化データ (Pydantic):**")
        safe_streamlit_json(entities.model_dump())


class ConditionalSchemaDemo(BaseDemo):
    """条件分岐スキーマデモ（統一化版）"""

    @error_handler_ui
    @timer_ui
    def run(self):
        """デモの実行（統一化版）"""
        self.initialize()
        
        with st.expander("OpenAI API(responses.parse):実装例", expanded=False):
            st.write(
                "responses.parse()の条件分岐スキーマデモ。ConditionalItemモデルでUnion型による動的スキーマ選択。"
                "入力内容に応じてUserInfoまたはAddressスキーマを自動選択・適用。"
            )
            st.code("""
            # Pydanticモデル定義（Union型）
            class ConditionalItem(BaseModel):
                item: Union[UserInfo, Address] = Field(..., description="ユーザー情報または住所")

            # responses.parse API呼び出し
            prompt = f"Parse this input conditionally: {text}"
            response = self.call_api_parse(
                input_text=prompt,
                text_format=ConditionalItem,
                temperature=temperature
            )
            """)

        default_text = "Name: Alice, Age: 30"
        st.write(f"**質問例**: {default_text}")

        with st.form(key=f"conditional_form_{self.safe_key}"):
            text = st.text_input(
                "ユーザー情報または住所を入力してください:",
                value=default_text
            )

            # 統一されたtemperatureコントロール
            temperature = self.create_temperature_control(
                default_temp=0.1,
                help_text="条件分岐では低い値を推奨"
            )

            submitted = st.form_submit_button("実行：条件分岐出力")

        if submitted and text:
            self._process_conditional_schema(text, temperature)

        self.show_debug_info()

    def _process_conditional_schema(self, text: str, temperature: Optional[float]):
        """条件分岐スキーマの処理（統一化版）"""
        # 実行回数を更新
        session_key = f"demo_state_{self.safe_key}"
        if session_key in st.session_state:
            st.session_state[session_key]['execution_count'] += 1

        prompt = (
            "You will receive either a user profile or a postal address.\n"
            "If the input represents a person, parse it into the UserInfo schema.\n"
            "If it represents an address, parse it into the Address schema.\n"
            "Wrap the result in the field 'item' and return JSON that matches the ConditionalItem schema.\n\n"
            f"INPUT:\n{text}"
        )

        try:
            with st.spinner("条件分岐処理中..."):
                response = self.call_api_parse(
                    input_text=prompt,
                    text_format=ConditionalItem,
                    temperature=temperature
                )

            st.success("✅ 条件分岐処理が完了しました")
            
            # 結果表示
            conditional_result = response.output_parsed
            self._display_conditional_result(conditional_result, response)

        except Exception as e:
            self.handle_error(e)

    def _display_conditional_result(self, conditional_result: ConditionalItem, response):
        """条件分岐結果の表示"""
        st.subheader("🔀 条件分岐結果")
        
        item = conditional_result.item
        
        if isinstance(item, UserInfo):
            st.success("**👤 ユーザー情報として認識**")
            col1, col2 = st.columns(2)
            with col1:
                st.metric("名前", item.name)
            with col2:
                st.metric("年齢", f"{item.age}歳")
                
        elif isinstance(item, Address):
            st.success("**🏠 住所情報として認識**")
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("番地", item.number)
            with col2:
                st.metric("通り", item.street)
            with col3:
                st.metric("市", item.city)

        # 構造化データの表示
        st.write("---")
        st.write("**🔧 構造化データ (Pydantic):**")
        safe_streamlit_json(conditional_result.model_dump())


class ModerationDemo(BaseDemo):
    """モデレーション＆拒否処理デモ（統一化版）"""

    @error_handler_ui
    @timer_ui
    def run(self):
        """デモの実行（統一化版）"""
        self.initialize()
        
        with st.expander("OpenAI API(responses.parse):実装例", expanded=False):
            st.write(
                "responses.parse()のモデレーションデモ。ModerationResultモデルで安全性チェックと拒否処理。"
                "不適切コンテンツの検出・拒否理由の明示・安全コンテンツの許可を自動判定。"
            )
            st.code("""
            # Pydanticモデル定義
            class ModerationResult(BaseModel):
                refusal: str = Field(..., description="拒否理由、問題なければ空文字")
                content: Optional[str] = Field(None, description="許可された場合の応答")

            # responses.parse API呼び出し
            prompt = f"Moderate this content: {text}"
            response = self.call_api_parse(
                input_text=prompt,
                text_format=ModerationResult,
                temperature=temperature
            )
            """)

        default_text = "Hello, how can I help you today?"
        st.write(f"**質問例**: {default_text}")

        with st.form(key=f"moderation_form_{self.safe_key}"):
            text = st.text_input(
                "モデレーション対象テキストを入力してください:",
                value=default_text
            )

            # 統一されたtemperatureコントロール
            temperature = self.create_temperature_control(
                default_temp=0.0,
                help_text="モデレーションでは最低値を推奨"
            )

            submitted = st.form_submit_button("実行：モデレーションチェック")

        if submitted and text:
            self._process_moderation(text, temperature)

        self.show_debug_info()

    def _process_moderation(self, text: str, temperature: Optional[float]):
        """モデレーションの処理（統一化版）"""
        # 実行回数を更新
        session_key = f"demo_state_{self.safe_key}"
        if session_key in st.session_state:
            st.session_state[session_key]['execution_count'] += 1

        prompt = (
            "You are a strict content moderator. "
            "If the input violates policy (hate, sexual, violence, self-harm, etc.), "
            "set 'refusal' to a short reason and leave 'content' null. "
            "Otherwise set 'refusal' to an empty string and echo the safe content in 'content'.\n\n"
            f"INPUT:\n{text}"
        )

        try:
            with st.spinner("モデレーション中..."):
                response = self.call_api_parse(
                    input_text=prompt,
                    text_format=ModerationResult,
                    temperature=temperature
                )

            st.success("✅ モデレーションが完了しました")
            
            # 結果表示
            moderation_result = response.output_parsed
            self._display_moderation_result(moderation_result, response)

        except Exception as e:
            self.handle_error(e)

    def _display_moderation_result(self, moderation_result: ModerationResult, response):
        """モデレーション結果の表示"""
        st.subheader("🛡️ モデレーション結果")
        
        if moderation_result.refusal:
            # 拒否された場合
            st.error("❌ **コンテンツが拒否されました**")
            st.write("**拒否理由:**")
            st.warning(moderation_result.refusal)
        else:
            # 許可された場合
            st.success("✅ **コンテンツが許可されました**")
            if moderation_result.content:
                st.write("**許可されたコンテンツ:**")
                st.info(moderation_result.content)

        # 構造化データの表示
        st.write("---")
        st.write("**🔧 構造化データ (Pydantic):**")
        safe_streamlit_json(moderation_result.model_dump())


# ==================================================
# デモマネージャー（統一化版）
# ==================================================
class DemoManager:
    """デモの管理クラス（統一化版）"""

    def __init__(self):
        self.config = ConfigManager("config.yml")
        self.demos = self._initialize_demos()

    def _initialize_demos(self) -> Dict[str, BaseDemo]:
        """デモインスタンスの初期化（統一化版）"""
        return {
            "イベント情報抽出": EventExtractionDemo("イベント情報抽出"),
            "数学的思考ステップ": MathReasoningDemo("数学的思考ステップ"),
            "UIコンポーネント生成": UIGenerationDemo("UIコンポーネント生成"),
            "エンティティ抽出": EntityExtractionDemo("エンティティ抽出"),
            "条件分岐スキーマ": ConditionalSchemaDemo("条件分岐スキーマ"),
            "モデレーション＆拒否処理": ModerationDemo("モデレーション＆拒否処理")
        }

    @error_handler_ui
    @timer_ui
    def run(self):
        """アプリケーションの実行（統一化版）"""
        # セッション状態の初期化（統一化）
        SessionStateManager.init_session_state()

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
            demo.run()
        else:
            st.error(f"デモ '{demo_name}' が見つかりません")

        # フッター情報（統一化）
        self._display_footer()

    def _display_footer(self):
        """フッター情報の表示（統一化版）"""
        st.sidebar.markdown("---")
        st.sidebar.markdown("### 情報")

        # 現在の設定情報
        with st.sidebar.expander("現在の設定"):
            safe_streamlit_json({
                "default_model": config.get("models.default"),
                "api_timeout"  : config.get("api.timeout"),
                "ui_layout"    : config.get("ui.layout"),
            })

        # バージョン情報
        st.sidebar.markdown("### バージョン")
        st.sidebar.markdown("- OpenAI Structured Outputs Parse Schema Demo v2.0 (統一化版)")
        st.sidebar.markdown("- Streamlit " + st.__version__)

        # リンク
        st.sidebar.markdown("### リンク")
        st.sidebar.markdown("[OpenAI API ドキュメント](https://platform.openai.com/docs)")
        st.sidebar.markdown("[Streamlit ドキュメント](https://docs.streamlit.io)")

        # 統計情報
        with st.sidebar.expander("📊 統計情報"):
            st.metric("利用可能デモ数", len(self.demos))
            st.metric("現在のデモ", st.session_state.get("current_demo", "未選択"))


# ==================================================
# メイン関数（統一化版）
# ==================================================
def main():
    """アプリケーションのエントリーポイント（統一化版）"""

    try:
        # ロギングの設定
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )

        # 環境変数のチェック
        if not os.getenv("OPENAI_API_KEY"):
            st.error("環境変数 OPENAI_API_KEY が設定されていません。")
            st.info("export OPENAI_API_KEY='your-api-key' を実行してください。")
            st.stop()

        # セッション状態の初期化（統一化）
        SessionStateManager.init_session_state()

        # デモマネージャーの作成と実行
        manager = DemoManager()
        manager.run()

    except Exception as e:
        st.error(f"アプリケーションの起動に失敗しました: {str(e)}")
        logger.error(f"Application startup error: {e}")

        # デバッグ情報の表示
        if config.get("experimental.debug_mode", False):
            with st.expander("🔧 詳細エラー情報", expanded=False):
                st.exception(e)


if __name__ == "__main__":
    main()

# streamlit run a01_structured_outputs_parse_schema.py --server.port=8501