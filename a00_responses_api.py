# streamlit run a00_responses_api.py --server.port=8510
# --------------------------------------------------
# Anthropic API デモアプリケーション（統一化版）
# Streamlitを使用したインタラクティブなAPIテストツール
# 統一化版: 構成・構造・ライブラリ・エラー処理の完全統一
# --------------------------------------------------
import os
import sys
import json
import base64
import glob
import logging
from datetime import datetime
import time
from abc import ABC, abstractmethod
from typing import Optional, List, Dict, Any, Literal, Tuple
from pathlib import Path

import streamlit as st
import pandas as pd
import requests
from pydantic import BaseModel, ValidationError
from PIL import Image
import io

from anthropic import Anthropic
from anthropic.types import Message, MessageParam, ContentBlock, TextBlock, TextBlockParam

# Web Search Tools用の型定義
class UserLocation(BaseModel):
    """ユーザーの位置情報"""
    country: str = "JP"
    region: str = "Tokyo"
    city: str = "Shibuya"
    timezone: str = "Asia/Tokyo"

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
        InfoPanelManager, safe_streamlit_json, EasyInputMessageParam
    )
    from helper_api import (
        config, logger, TokenManager, AnthropicClient,
        MessageParam, ConfigManager, MessageManager, sanitize_key,
        error_handler, timer, get_default_messages, get_system_prompt,
        ResponseProcessor, format_timestamp
    )
except ImportError as e:
    st.error(f"ヘルパーモジュールのインポートに失敗しました: {e}")
    st.info("必要なファイルが存在することを確認してください: helper_st.py, helper_api.py")
    # フォールバック: ローカルでEasyInputMessageParamを定義
    EasyInputMessageParam = MessageParam
    st.stop()


# ページ設定
def setup_page_config():
    """ページ設定（重複実行エラー回避）"""
    try:
        st.set_page_config(
            page_title=config.get("ui.page_title", "Anthropic API デモ"),
            page_icon=config.get("ui.page_icon", "🤖"),
            layout=config.get("ui.layout", "wide"),
            initial_sidebar_state="expanded"
        )
    except st.errors.StreamlitAPIException:
        # 既に設定済みの場合は無視
        pass


# ページ設定の実行
setup_page_config()

# サンプル画像 URL（config.ymlから取得）
image_path_sample = config.get(
    "samples.images.nature",
    "https://upload.wikimedia.org/wikipedia/commons/thumb/d/dd/"
    "Gfp-wisconsin-madison-the-nature-boardwalk.jpg/2560px-"
    "Gfp-wisconsin-madison-the-nature-boardwalk.jpg"
)

# https://upload.wikimedia.org/wikipedia/commons/thumb/d/dd/Gfp-wisconsin-madison-the-nature-boardwalk.jpg/2560px-Gfp-wisconsin-madison-the-nature-boardwalk.jpg

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
# 基底クラス
# ==================================================
class BaseDemo(ABC):
    """デモ機能の基底クラス（統一化版）"""

    def __init__(self, demo_name: str):
        self.demo_name = demo_name
        self.config = ConfigManager("config.yml")

        # Anthropicクライアントの初期化（統一されたエラーハンドリング）
        try:
            self.client = AnthropicClient()
        except Exception as e:
            st.error(f"Anthropicクライアントの初期化に失敗しました: {e}")
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
                'model'          : self.config.get("models.default", "claude-sonnet-4-20250514"),
                'execution_count': 0
            }

    def get_model(self) -> str:
        """選択されたモデルを取得（統一化）"""
        return st.session_state.get(f"model_{self.safe_key}",
                                    config.get("models.default", "claude-sonnet-4-20250514"))

    def is_reasoning_model(self, model: str = None) -> bool:
        """推論系モデルかどうかを判定（統一化）"""
        if model is None:
            model = self.get_model()

        # Anthropicモデルは全てtemperatureをサポート
        return False

    def create_temperature_control(self, default_temp: float = 0.3, help_text: str = None) -> Optional[float]:
        """Temperatureコントロールを作成（統一化・推論系モデル・GPT-5系では無効化）"""
        model = self.get_model()

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
    def call_api_unified(self, messages: List[MessageParam], temperature: Optional[float] = None, **kwargs):
        """統一されたAPI呼び出し（Anthropic API対応）"""
        model = self.get_model()
        system_prompt = get_system_prompt()

        # API呼び出しパラメータの準備
        api_params = {
            "messages": messages,
            "model": model,
            "system": system_prompt,
            "max_tokens": 4096
        }

        # temperatureサポート
        if temperature is not None:
            api_params["temperature"] = temperature

        # その他のパラメータ
        api_params.update(kwargs)

        # create_message を使用（Anthropic API）
        return self.client.create_message(**api_params)

    @abstractmethod
    def run(self):
        """各デモの実行処理（サブクラスで実装）"""
        pass


# ==================================================
# テキスト応答デモ
# ==================================================
class TextResponseDemo(BaseDemo):
    """基本的なテキスト応答のデモ（統一化版）"""

    @error_handler_ui
    @timer_ui
    def run(self):
        """デモの実行（統一化版）"""
        self.initialize()
        
        # 実装例の説明セクション
        st.write("## 実装例: Anthropic Messages API基本応答")
        st.write("Anthropic Messages APIを使用した基本的なテキスト応答の実装方法を示します。")
        
        # APIメモセクション（a05のパターンを適用）
        with st.expander("📝 Anthropic API メモ", expanded=False):
            st.code("""
# Anthropic Messages APIについて

Anthropic APIの基本的な使い方：

1. **メッセージ形式**
   - role: "user" または "assistant"
   - content: メッセージの内容
   
2. **API呼び出し**
   ```python
   response = client.messages.create(
       model="claude-3-opus-20240229",
       messages=[
           {"role": "user", "content": "質問内容"}
       ],
       max_tokens=4096
   )
   ```
   
3. **システムプロンプト**
   - systemパラメータで指定
   - AIの振る舞いを制御
            """, language="python")
        
        # API互換性情報（既存コンテンツを整理）
        with st.expander("🔄 OpenAI APIとの互換性", expanded=False):
            text_compatibility = """
### 要点比較：

| 目的 | OpenAI 側 | Anthropic ネイティブ | Anthropic の OpenAI SDK 互換（ベータ） |
|---|---|---|---|
| 呼び出し | `client.responses.create(...)` | `client.messages.create(...)` | `client.chat.completions.create(...)` |
| エンドポイント | `/v1/responses` | `/v1/messages` | （SDKは Chat Completions 形だが実体は Claude の `/v1/messages` にマップ） |
| 入力形 | `input`（＋`instructions`） | `messages` 配列（＋`system`） | `messages` 配列（OpenAI 形式） |
| ツール | `tools=[...]`（ホスト型ツール等が統合） | `tools` を JSON Schema で定義。`tool_use` → クライアント側実行（サーバー Web search tool もあり） | function-calling 系は概ね通るが `response_format` など一部は無視される |
| ストリーミング | 可（`stream=True`） | 可（`stream`） | 可 |
| 備考 | Responses は状態管理や内蔵ツールを統合 | Claude はコンテンツブロック（`text`/`tool_use` など）で返す | **テスト用途向け**。本番はネイティブ `Messages API` 推奨 |

- 補足: 互換レイヤーは *Chat Completions 互換であり、Responses API のフル互換ではありません。
"""
            st.markdown(text_compatibility)
            st.info("""
資料： https://docs.anthropic.com/en/api/openai-sdk  
OpenAI APIから、Anthropic APIへ移植が可能です。
            """)
        
        # 実装例コード（a05のパターンで整理）
        with st.expander("📋 実装例コード", expanded=False):
            st.code("""
# 基本的なテキスト応答の実装例
from anthropic import Anthropic

client = Anthropic()

# メッセージの準備
messages = [
    {"role": "user", "content": "Anthropic APIの使い方を教えて"}
]

# API呼び出し
response = client.messages.create(
    model="claude-3-opus-20240229",
    messages=messages,
    system="You are a helpful assistant.",
    max_tokens=4096,
    temperature=0.3
)

# 応答の取得
print(response.content[0].text)
            """, language="python")
        
        # セパレーター
        st.write("---")
        
        # 入力セクション（a05のパターンを適用）
        st.subheader("📤 入力")
        
        example_query = config.get("samples.prompts.responses_query",
                                   "Anthropic APIのmessages.createメソッドを説明しなさい。")
        st.info(f"💡 質問の例: {example_query}")
        
        with st.form(key=f"text_form_{self.safe_key}"):
            user_input = st.text_area(
                "質問を入力してください:",
                value="",
                height=config.get("ui.text_area_height", 75),
                placeholder=example_query
            )

            # パラメータセクション
            col1, col2 = st.columns([2, 1])
            with col1:
                # 統一されたtemperatureコントロール
                temperature = self.create_temperature_control(
                    default_temp=0.3,
                    help_text="低い値ほど一貫性のある回答"
                )
            with col2:
                max_tokens = st.number_input(
                    "最大トークン数",
                    min_value=100,
                    max_value=8192,
                    value=4096,
                    step=100
                )

            submitted = st.form_submit_button("🚀 送信", use_container_width=True)

        if submitted and user_input:
            self._process_query(user_input, temperature, max_tokens)
        
        # 結果表示セクション
        self._display_results()
        
        self.show_debug_info()

    def _process_query(self, user_input: str, temperature: Optional[float], max_tokens: int = 4096):
        """クエリの処理（統一化版）"""
        # 実行回数を更新
        session_key = f"demo_state_{self.safe_key}"
        if session_key in st.session_state:
            st.session_state[session_key]['execution_count'] += 1

        # トークン情報の表示
        UIHelper.show_token_info(user_input, self.model, position="sidebar")

        # デフォルトメッセージを取得（config.ymlから）
        messages = get_default_messages()
        messages.append(
            {"role": "user", "content": user_input}
        )

        with st.spinner("処理中..."):
            response = self.call_api_unified(messages, temperature=temperature, max_tokens=max_tokens)

        # セッション状態に保存
        st.session_state[f"last_response_{self.safe_key}"] = response
        st.session_state[f"last_query_{self.safe_key}"] = user_input
        st.success("✅ 応答を取得しました")
    
    def _display_results(self):
        """結果の表示（a05のパターンを適用）"""
        if f"last_response_{self.safe_key}" in st.session_state:
            st.write("---")
            st.subheader("🤖 AIの回答")
            
            response = st.session_state[f"last_response_{self.safe_key}"]
            query = st.session_state.get(f"last_query_{self.safe_key}", "")
            
            # 質問の表示
            with st.expander("💬 質問内容", expanded=False):
                st.markdown(f"> {query}")
            
            # 応答の表示
            ResponseProcessorUI.display_response(response)


# ==================================================
# 必要なインポートの追加（エラー修正）
# ==================================================
import pandas as pd

# ==================================================
# メモリ応答デモ（改修版・エラー修正版）- 連続会話対応
# ==================================================
class MemoryResponseDemo(BaseDemo):
    """連続会話を管理するデモ（改修版・エラー修正版）"""

    def __init__(self, demo_name: str):
        super().__init__(demo_name)
        # 会話ステップの管理
        self.conversation_steps = []
        self._initialize_conversation_state()

    def _initialize_conversation_state(self):
        """会話状態の初期化"""
        session_key = f"conversation_steps_{self.safe_key}"
        if session_key not in st.session_state:
            st.session_state[session_key] = []

        self.conversation_steps = st.session_state[session_key]

    @error_handler_ui
    @timer_ui
    def run(self):
        """デモの実行（改修版）"""
        self.initialize()
        
        # 実装例の説明セクション（a05パターンを適用）
        st.write("## 実装例: 連続会話管理")
        st.write("会話履歴を保持しながら連続した対話を実現します。各ステップで「プロンプト + 回答」の履歴を保持し、文脈を踏まえた応答を生成します。")
        
        # APIメモセクション（a05パターンを適用）
        with st.expander("📝 Anthropic API メモ", expanded=False):
            st.code("""
# Anthropic APIでの連続会話について

会話履歴の管理方法：

1. **メッセージ履歴の構築**
   - userとassistantの交互のメッセージを配列で管理
   - 各ターンでメッセージを追加

2. **実装パターン**
   ```python
   # 会話履歴
   messages = [
       {"role": "user", "content": "初回の質問"},
       {"role": "assistant", "content": "初回の回答"},
       {"role": "user", "content": "追加の質問"}
   ]
   
   # API呼び出し（履歴を含めて送信）
   response = client.messages.create(
       model=model,
       messages=messages,
       max_tokens=1024
   )
   ```

3. **メリット**
   - 完全な会話コンテキストの制御
   - 必要に応じて会話履歴を編集可能
   - 複数ターンの会話を簡単に管理
            """, language="python")

        # 実装例コード（a05パターンで整理）
        with st.expander("📋 実装例コード", expanded=False):
            st.code("""
# 連続会話の実装例
from anthropic import Anthropic

client = Anthropic()

# 会話履歴の初期化
conversation_history = []

# 1回目: 初回質問
conversation_history.append({"role": "user", "content": "Pythonとは何ですか？"})
response_1 = client.messages.create(
    model=model,
    messages=conversation_history,
    max_tokens=1024
)
conversation_history.append({"role": "assistant", "content": response_1.content[0].text})

# 2回目: 追加質問（履歴を含めて送信）
conversation_history.append({"role": "user", "content": "具体的な使用例を教えて"})
response_2 = client.messages.create(
    model=model,
    messages=conversation_history,
    max_tokens=1024
)
conversation_history.append({"role": "assistant", "content": response_2.content[0].text})
            """, language="python")
        
        # セパレーター
        st.write("---")
        
        # 会話履歴セクション
        if self.conversation_steps:
            st.subheader("💬 会話履歴")
            self._display_conversation_history()
            st.write("---")
        
        # 入力セクション
        st.subheader("📤 新しい質問")
        self._create_input_form()
        
        # 会話管理セクション
        if self.conversation_steps:
            st.write("---")
            st.subheader("⚙️ 会話管理")
            self._create_conversation_controls()
        
        self.show_debug_info()

    def _display_conversation_history(self):
        """会話履歴の表示"""
        if not self.conversation_steps:
            st.info("💬 会話を開始してください。質問を入力すると会話履歴が表示されます。")
            return

        # 会話統計の表示
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("🔢 会話ステップ数", len(self.conversation_steps))
        with col2:
            total_tokens = sum(step.get('total_tokens', 0) for step in self.conversation_steps)
            st.metric("📊 累計トークン数", f"{total_tokens:,}")
        with col3:
            if self.conversation_steps:
                latest_step = self.conversation_steps[-1]
                latest_time = latest_step.get('timestamp', 'N/A')
                st.metric("🕐 最新質問時刻", latest_time[-8:] if len(latest_time) > 8 else latest_time)  # 時刻部分のみ表示

        # 各会話ステップの表示
        for i, step in enumerate(self.conversation_steps, 1):
            with st.expander(
                    f"🔄 ステップ {i}: {step['user_input'][:50]}{'...' if len(step['user_input']) > 50 else ''}",
                    expanded=(i == len(self.conversation_steps))):

                # ステップ詳細情報
                col1, col2 = st.columns([3, 1])
                with col1:
                    st.write(f"**質問時刻**: {step.get('timestamp', 'N/A')}")
                    st.write(f"**使用モデル**: {step.get('model', 'N/A')}")
                with col2:
                    if 'usage' in step and step['usage']:
                        usage = step['usage']
                        st.write(f"**トークン使用**")
                        st.write(f"入力: {usage.get('prompt_tokens', 0)}")
                        st.write(f"出力: {usage.get('completion_tokens', 0)}")
                        st.write(f"合計: {usage.get('total_tokens', 0)}")

                # ユーザーの質問
                st.write("**👤 ユーザーの質問:**")
                st.markdown(f"> {step['user_input']}")

                # AIの回答
                st.write("**🤖 AIの回答:**")
                with st.chat_message("assistant", avatar="🤖"):
                    st.markdown(step['assistant_response'])

                # この時点でのメッセージ履歴
                if st.checkbox(f"メッセージ履歴を表示 (ステップ {i})", key=f"show_messages_{i}_{self.safe_key}"):
                    st.write("**📋 この時点でのメッセージ履歴:**")
                    messages = step.get('messages_at_step', [])
                    for j, msg in enumerate(messages):
                        role = msg.get('role', 'unknown')
                        content = msg.get('content', '')
                        content_preview = content[:100] + '...' if len(content) > 100 else content
                        st.write(f"{j + 1}. **{role}**: {content_preview}")

    def _create_input_form(self):
        """入力フォームの作成（a05パターンを適用）"""
        # 現在の会話コンテキスト情報
        if self.conversation_steps:
            st.info(
                f"ℹ️ 現在 {len(self.conversation_steps)} ステップの会話履歴があります。新しい質問はこの履歴を踏まえて回答されます。")
        else:
            st.info("ℹ️ 最初の質問です。会話を開始してください。")

        # セッション状態でユーザー入力を管理
        input_key = f"user_input_{self.safe_key}"
        temp_key = f"temperature_{self.safe_key}"

        # 初期化
        if input_key not in st.session_state:
            st.session_state[input_key] = ""
        if temp_key not in st.session_state:
            st.session_state[temp_key] = 0.3

        # 質問例の表示（expanderに収納）
        example_questions = self._get_example_questions()
        if example_questions:
            with st.expander("💡 質問例", expanded=False):
                for i, question in enumerate(example_questions[:3]):
                    if st.button(f"📝 {question}", key=f"example_{i}_{self.safe_key}", use_container_width=True):
                        st.session_state[input_key] = question
                        st.rerun()

        # 入力エリア（セッション状態と連動）
        user_input = st.text_area(
            "質問を入力してください:",
            value=st.session_state[input_key],
            height=config.get("ui.text_area_height", 75),
            key=f"text_area_{self.safe_key}",
            placeholder="前回の会話を踏まえた質問をしてください...",
            on_change=self._on_text_change
        )

        # ユーザー入力の同期
        st.session_state[input_key] = user_input

        # パラメータ設定セクション
        col1, col2, col3 = st.columns([2, 1, 1])
        with col1:
            if not self.is_reasoning_model(self.model):
                temperature = st.slider(
                    "Temperature",
                    0.0, 1.0, st.session_state[temp_key], 0.05,
                    help="低い値ほど一貫性のある回答",
                    key=f"temp_slider_{self.safe_key}"
                )
                st.session_state[temp_key] = temperature
            else:
                st.info("ℹ️ 推論系モデルではtemperatureパラメータは使用されません")
                temperature = None
        
        with col2:
            max_tokens = st.number_input(
                "最大トークン数",
                min_value=100,
                max_value=8192,
                value=4096,
                step=100,
                key=f"max_tokens_{self.safe_key}"
            )

        # 送信ボタン
        with col3:
            st.write("")  # スペーサー
            st.write("")  # スペーサー
            submitted = st.button(
                "🚀 送信",
                key=f"submit_{self.safe_key}",
                use_container_width=True,
                type="primary"
            )

        # クリアボタン（別行に配置）
        if st.button("🔄 入力をクリア", key=f"clear_{self.safe_key}"):
            st.session_state[input_key] = ""
            st.rerun()

        # 送信処理
        if submitted and user_input.strip():
            self._process_conversation_step(user_input, temperature)
        elif submitted and not user_input.strip():
            st.warning("⚠️ 質問を入力してください。")

    def _on_text_change(self):
        """テキストエリアの変更時コールバック"""
        # このメソッドは必要に応じて処理を追加
        pass

    def _get_example_questions(self):
        """会話ステップに応じた質問例を取得"""
        if not self.conversation_steps:
            # 初回質問の例
            return [
                "Anthropic APIで、messages.createの使い方を説明したください",
                "Anthropic APIの音声、翻訳処理と画像処理関連について説明してください。",
                "Anthropic APIとOpenAI APIとの互換性について対比して説明してください。"
            ]
        else:
            # 継続質問の例
            return [
                "もう少し具体的なコードで対比して詳しく説明してください",
                "関連する技術やライブラリも教えてください",
                "実際のプロジェクトではどのように活用しますか？",
                "これの注意点やベストプラクティスはありますか？"
            ]

    def _process_conversation_step(self, user_input: str, temperature: Optional[float]):
        """会話ステップの処理"""
        # 実行回数を更新
        session_key = f"demo_state_{self.safe_key}"
        if session_key in st.session_state:
            st.session_state[session_key]['execution_count'] += 1

        # トークン情報の表示
        UIHelper.show_token_info(user_input, self.model, position="sidebar")

        # メッセージ履歴の構築
        messages = self._build_conversation_messages(user_input)

        # APIコール
        with st.spinner("🤖 AIが思考中..."):
            response = self.call_api_unified(messages, temperature=temperature)

        # レスポンスからテキストを抽出
        assistant_texts = ResponseProcessor.extract_text(response)
        assistant_response = assistant_texts[0] if assistant_texts else "応答を取得できませんでした"

        # 会話ステップの記録
        step_data = {
            'step_number'       : len(self.conversation_steps) + 1,
            'timestamp'         : format_timestamp(),
            'model'             : self.model,
            'user_input'        : user_input,
            'assistant_response': assistant_response,
            'messages_at_step'  : [dict(msg) for msg in messages],  # EasyInputMessageParamを辞書に変換
            'temperature'       : temperature,
            'usage'             : self._extract_usage_info(response),
            'total_tokens'      : self._calculate_total_tokens(response)
        }

        # セッション状態に保存
        self.conversation_steps.append(step_data)
        st.session_state[f"conversation_steps_{self.safe_key}"] = self.conversation_steps

        # 成功メッセージと即座の表示更新
        st.success(f"✅ ステップ {step_data['step_number']} の応答を取得しました")

        # レスポンスの表示
        st.subheader("🤖 最新の回答")
        ResponseProcessorUI.display_response(response)

        # フォームの再描画（入力フィールドがクリアされる）
        st.rerun()

    def _build_conversation_messages(self, new_user_input: str) -> List[MessageParam]:
        """会話履歴を基にメッセージリストを構築"""
        # デフォルトメッセージから開始
        messages = get_default_messages()

        # 過去の会話ステップを追加
        for step in self.conversation_steps:
            messages.append({"role": "user", "content": step['user_input']})
            messages.append({"role": "assistant", "content": step['assistant_response']})

        # 新しいユーザー入力を追加
        messages.append({"role": "user", "content": new_user_input})

        return messages

    def _extract_usage_info(self, response: Message) -> Dict[str, Any]:
        """レスポンスから使用量情報を抽出"""
        try:
            if hasattr(response, 'usage') and response.usage:
                usage_obj = response.usage

                # Pydantic モデルの場合
                if hasattr(usage_obj, 'model_dump'):
                    return usage_obj.model_dump()
                elif hasattr(usage_obj, 'dict'):
                    return usage_obj.dict()
                else:
                    # 手動で属性を抽出
                    return {
                        'input_tokens' : getattr(usage_obj, 'input_tokens', 0),
                        'output_tokens': getattr(usage_obj, 'output_tokens', 0),
                        'total_tokens' : getattr(usage_obj, 'input_tokens', 0) + getattr(usage_obj, 'output_tokens', 0)
                    }
            return {}
        except Exception as e:
            logger.error(f"使用量情報の抽出エラー: {e}")
            return {}

    def _calculate_total_tokens(self, response: Message) -> int:
        """総トークン数の計算"""
        usage_info = self._extract_usage_info(response)
        return usage_info.get('total_tokens', 0)

    def _create_conversation_controls(self):
        """会話管理コントロール"""
        st.subheader("🛠️ 会話管理")

        col1, col2, col3, col4 = st.columns(4)

        with col1:
            if st.button("🗑️ 会話履歴クリア", key=f"clear_conv_{self.safe_key}"):
                self.conversation_steps.clear()
                st.session_state[f"conversation_steps_{self.safe_key}"] = []
                st.success("会話履歴をクリアしました")
                st.rerun()

        with col2:
            if st.button("📥 会話履歴エクスポート", key=f"export_conv_{self.safe_key}"):
                self._export_conversation()

        with col3:
            uploaded_file = st.file_uploader(
                "📤 会話履歴インポート",
                type=['json'],
                key=f"import_conv_{self.safe_key}",
                help="過去にエクスポートした会話履歴をインポート"
            )
            if uploaded_file is not None:
                self._import_conversation(uploaded_file)

        with col4:
            if self.conversation_steps and st.button("📊 会話統計", key=f"stats_conv_{self.safe_key}"):
                self._show_conversation_statistics()

    def _export_conversation(self):
        """会話履歴のエクスポート"""
        if not self.conversation_steps:
            st.warning("エクスポートする会話履歴がありません")
            return

        export_data = {
            "export_info"       : {
                "timestamp"   : format_timestamp(),
                "total_steps" : len(self.conversation_steps),
                "model_used"  : self.model,
                "demo_version": "MemoryResponseDemo_v2.0"
            },
            "conversation_steps": self.conversation_steps
        }

        try:
            UIHelper.create_download_button(
                export_data,
                f"conversation_history_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                "application/json",
                "📥 会話履歴JSONダウンロード"
            )
        except Exception as e:
            st.error(f"エクスポートエラー: {e}")

    def _import_conversation(self, uploaded_file):
        """会話履歴のインポート"""
        try:
            content = uploaded_file.read()
            data = json.loads(content)

            if "conversation_steps" in data:
                imported_steps = data["conversation_steps"]

                # 現在の履歴に追加 or 置換
                replace_option = st.radio(
                    "インポート方法",
                    ["現在の履歴に追加", "現在の履歴を置換"],
                    key=f"import_option_{self.safe_key}"
                )

                if st.button("インポート実行", key=f"execute_import_{self.safe_key}"):
                    if replace_option == "現在の履歴を置換":
                        self.conversation_steps = imported_steps
                    else:
                        self.conversation_steps.extend(imported_steps)

                    st.session_state[f"conversation_steps_{self.safe_key}"] = self.conversation_steps
                    st.success(f"{len(imported_steps)}ステップの会話履歴をインポートしました")
                    st.rerun()
            else:
                st.error("有効な会話履歴データが見つかりません")

        except Exception as e:
            st.error(f"インポートエラー: {e}")
            logger.error(f"Conversation import error: {e}")

    def _show_conversation_statistics(self):
        """会話統計の表示"""
        if not self.conversation_steps:
            return

        with st.expander("📊 詳細統計", expanded=True):
            # 基本統計
            total_steps = len(self.conversation_steps)
            total_user_chars = sum(len(step['user_input']) for step in self.conversation_steps)
            total_assistant_chars = sum(len(step['assistant_response']) for step in self.conversation_steps)
            total_tokens = sum(step.get('total_tokens', 0) for step in self.conversation_steps)

            col1, col2 = st.columns(2)
            with col1:
                st.metric("総会話ステップ", total_steps)
                st.metric("ユーザー入力文字数", f"{total_user_chars:,}")
                st.metric("AI応答文字数", f"{total_assistant_chars:,}")
            with col2:
                st.metric("総トークン数", f"{total_tokens:,}")
                if total_steps > 0:
                    avg_tokens = total_tokens / total_steps
                    st.metric("平均トークン/ステップ", f"{avg_tokens:.1f}")

                # コスト推定
                try:
                    estimated_cost = TokenManager.estimate_cost(
                        total_tokens // 2,  # 概算で半分を入力トークンと仮定
                        total_tokens // 2,  # 半分を出力トークンと仮定
                        self.model
                    )
                    st.metric("推定総コスト", f"${estimated_cost:.6f}")
                except Exception as e:
                    st.warning(f"コスト推定エラー: {e}")

            # 時系列グラフ（簡易版）
            st.write("**ステップ別トークン使用量**")
            step_tokens = [step.get('total_tokens', 0) for step in self.conversation_steps]
            if step_tokens:
                try:
                    df = pd.DataFrame({
                        'ステップ'  : range(1, len(step_tokens) + 1),
                        'トークン数': step_tokens
                    })
                    st.bar_chart(df.set_index('ステップ'))
                except Exception as e:
                    st.warning(f"グラフ表示エラー: {e}")

            # 質問の傾向分析（簡易版）
            st.write("**質問の長さ分布**")
            question_lengths = [len(step['user_input']) for step in self.conversation_steps]
            if question_lengths:
                avg_length = sum(question_lengths) / len(question_lengths)
                max_length = max(question_lengths)
                min_length = min(question_lengths)

                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("平均質問長", f"{avg_length:.1f}文字")
                with col2:
                    st.metric("最長質問", f"{max_length}文字")
                with col3:
                    st.metric("最短質問", f"{min_length}文字")

# ==================================================
# 画像応答デモ
# ==================================================
class ImageResponseDemo(BaseDemo):
    """画像入力のデモ（統一化版）"""

    def __init__(self, demo_name: str, use_base64: bool = False):
        super().__init__(demo_name)
        self.use_base64 = use_base64

    @error_handler_ui
    @timer_ui
    def run(self):
        """デモの実行（統一化版）"""
        self.initialize()
        with st.expander("Anthropic API実装例", expanded=False):
            st.write(
                "マルチモーダル対応のAnthropic Messages APIデモ。URL・Base64形式の画像入力に対応。Claudeの視覚機能を活用した画像解析例。")
            st.code("""
            # URL画像の場合
            messages = get_default_messages()
            messages.append({
                "role": "user",
                "content": [
                    {"type": "text", "text": question},
                    {
                        "type": "image",
                        "source": {
                            "type": "url",
                            "url": image_url
                        }
                    }
                ]
            })
            
            # Base64画像の場合
            messages.append({
                "role": "user",
                "content": [
                    {"type": "text", "text": question},
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": "image/jpeg",  # または image/png, image/webp など
                            "data": base64_encoded_data
                        }
                    }
                ]
            })
            
            response = self.call_api_unified(messages, temperature=temperature)
            ResponseProcessorUI.display_response(response)
            """)

        if self.use_base64:
            self._run_base64_demo()
        else:
            self._run_url_demo()

    def _run_url_demo(self):
        """URL画像のデモ（統一化版）"""
        st.write("例: このイメージを日本語で説明しなさい。")

        image_url = st.text_input(
            "画像URLを入力してください",
            value=image_path_sample,
            key=f"img_url_{self.safe_key}"
        )

        if image_url:
            try:
                st.image(image_url, caption="入力画像", use_container_width=True)
            except Exception as e:
                st.error(f"画像の表示に失敗しました: {e}")

        with st.form(key=f"img_form_{self.safe_key}"):
            question = st.text_input("質問", value="このイメージを日本語で説明しなさい。")

            # 統一されたtemperatureコントロール
            temperature = self.create_temperature_control(
                default_temp=0.3,
                help_text="低い値ほど一貫性のある回答"
            )

            submitted = st.form_submit_button("画像で質問")

        if submitted and image_url and question:
            self._process_image_question(question, image_url, temperature)

    def _run_base64_demo(self):
        """Base64画像のデモ（Anthropic API対応版）"""
        st.write("**📁 ローカル画像ファイルからBase64エンコード**")
        st.info("💡 Anthropic APIはbase64エンコード後最大5MBまでの画像を処理できます")
        
        images_dir = config.get("paths.images_dir", "images")
        
        # imagesディレクトリが存在しない場合はdataディレクトリを試す
        if not Path(images_dir).exists():
            images_dir = "data"
            if not Path(images_dir).exists():
                # 最後の手段として現在のディレクトリを試す
                images_dir = "."
            
        files = self._get_image_files(images_dir)

        if not files:
            st.warning(f"📂 {images_dir} ディレクトリに画像ファイルが見つかりません")
            st.info("💡 サポート形式: PNG, JPG, JPEG, WebP, GIF")
            
            # ファイルアップロード機能を追加
            st.write("**または画像ファイルをアップロード:**")
            uploaded_file = st.file_uploader(
                "画像ファイルを選択", 
                type=['png', 'jpg', 'jpeg', 'webp', 'gif'],
                key=f"img_upload_{self.safe_key}"
            )
            
            if uploaded_file is not None:
                # 一時ファイルとして保存
                temp_path = f"/tmp/{uploaded_file.name}"
                with open(temp_path, "wb") as f:
                    f.write(uploaded_file.getbuffer())
                files = [temp_path]
            else:
                return

        if files:
            # ファイル選択UI
            if len(files) == 1:
                file_path = files[0]
                st.write(f"**選択されたファイル:** {Path(file_path).name}")
            else:
                file_options = [f"{Path(f).name} ({self._get_file_size_info(f)})" for f in files]
                selected_idx = st.selectbox(
                    "📷 画像ファイルを選択", 
                    range(len(file_options)),
                    format_func=lambda x: file_options[x],
                    key=f"img_select_{self.safe_key}"
                )
                file_path = files[selected_idx]
            
            # ファイル情報表示
            if file_path and Path(file_path).exists():
                self._display_file_info(file_path)
                
                # プレビュー表示
                try:
                    st.image(file_path, caption=f"プレビュー: {Path(file_path).name}", width=300)
                except Exception as e:
                    st.warning(f"プレビュー表示エラー: {e}")

                # 質問入力と実行
                with st.form(key=f"img_b64_form_{self.safe_key}"):
                    question = st.text_input(
                        "🤔 画像について質問してください:",
                        value="この画像を詳しく説明してください。",
                        help="画像の内容について知りたいことを入力してください"
                    )
                    
                    # 統一されたtemperatureコントロール
                    temperature = self.create_temperature_control(
                        default_temp=0.3,
                        help_text="低い値ほど一貫性のある回答"
                    )

                    submitted = st.form_submit_button("🚀 画像解析を実行", type="primary")

                if submitted and file_path and question.strip():
                    self._process_base64_image(file_path, question, temperature)
                elif submitted and not question.strip():
                    st.warning("⚠️ 質問を入力してください")

    def _display_file_info(self, file_path: str):
        """ファイル情報の表示"""
        try:
            file_stats = Path(file_path).stat()
            size_mb = file_stats.st_size / (1024 * 1024)
            
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("📁 ファイル名", Path(file_path).name)
            with col2:
                st.metric("📊 ファイルサイズ", f"{size_mb:.2f}MB")
            with col3:
                estimated_base64_mb = size_mb * 1.37
                max_size_mb = config.get("limits.max_image_size_mb", 5)
                status = "✅" if estimated_base64_mb <= max_size_mb else "⚠️"
                st.metric("📈 推定base64サイズ", f"{status} {estimated_base64_mb:.2f}MB")
                
        except Exception as e:
            st.warning(f"ファイル情報取得エラー: {e}")

    def _get_image_files(self, images_dir: str) -> List[str]:
        """画像ファイルのリストを取得"""
        patterns = ["*.png", "*.jpg", "*.jpeg", "*.webp", "*.gif"]
        files = []
        for pattern in patterns:
            files.extend(glob.glob(f"{images_dir}/{pattern}"))
        return sorted(files)
        
    def _get_file_size_info(self, file_path: str) -> str:
        """ファイルサイズ情報を取得（Anthropic API制限対応）"""
        try:
            size_bytes = os.path.getsize(file_path)
            size_mb = size_bytes / (1024 * 1024)
            
            # base64エンコード後の推定サイズ（約137%増加）
            estimated_base64_mb = size_mb * 1.37
            max_size_mb = config.get("limits.max_image_size_mb", 5)  # Anthropic APIの制限
            
            if estimated_base64_mb <= max_size_mb:
                status = "✅"
            elif estimated_base64_mb <= max_size_mb * 1.5:  # リサイズで対応可能
                status = "🔄"
            else:
                status = "⚠️"  # 大幅なリサイズが必要
                
            return f"{status} {size_mb:.2f}MB → ~{estimated_base64_mb:.1f}MB"
        except Exception:
            return "❓ サイズ不明"

    def _encode_image(self, path: str) -> Tuple[str, str]:
        """画像をBase64エンコード（Anthropic API対応）
        
        Returns:
            Tuple[str, str]: (base64_encoded_data, media_type)
        """
        try:
            # ファイル拡張子からメディアタイプを判定
            ext = Path(path).suffix.lower()
            media_type_map = {
                '.jpg': 'image/jpeg',
                '.jpeg': 'image/jpeg', 
                '.png': 'image/png',
                '.webp': 'image/webp',
                '.gif': 'image/gif'
            }
            original_media_type = media_type_map.get(ext, 'image/jpeg')
            
            # Anthropic APIの制限: 5MB (base64エンコード後)
            max_base64_size_mb = config.get("limits.max_image_size_mb", 5)
            max_base64_bytes = max_base64_size_mb * 1024 * 1024
            
            # ファイルサイズをチェック
            file_size = os.path.getsize(path)
            file_size_mb = file_size / (1024 * 1024)
            
            # base64エンコード後の推定サイズ（約133%増加）
            estimated_base64_size = file_size * 1.37
            
            st.info(f"📂 ファイル: {Path(path).name}")
            st.info(f"📊 元サイズ: {file_size_mb:.2f}MB, 推定base64サイズ: {estimated_base64_size/(1024*1024):.2f}MB")
            
            # サイズが制限を超える場合はリサイズ
            if estimated_base64_size > max_base64_bytes:
                st.warning(f"⚠️ 推定base64サイズが制限({max_base64_size_mb}MB)を超過するため、リサイズします")
                return self._resize_and_encode_image(path, max_base64_bytes)
            
            # サイズが問題なければそのままエンコード
            with open(path, 'rb') as image_file:
                image_bytes = image_file.read()
                encoded_data = base64.b64encode(image_bytes).decode('utf-8')
                
            # 実際のbase64サイズをチェック
            actual_base64_size = len(encoded_data.encode('utf-8'))
            actual_size_mb = actual_base64_size / (1024 * 1024)
            
            if actual_base64_size > max_base64_bytes:
                st.warning(f"⚠️ 実際のbase64サイズ({actual_size_mb:.2f}MB)が制限を超過するため、リサイズします")
                return self._resize_and_encode_image(path, max_base64_bytes)
            
            st.success(f"✅ エンコード完了: {actual_size_mb:.2f}MB (base64)")
            return encoded_data, original_media_type
            
        except Exception as e:
            st.error(f"画像エンコードエラー: {e}")
            return "", "image/jpeg"
            
    def _resize_and_encode_image(self, path: str, max_base64_bytes: int) -> Tuple[str, str]:
        """画像をリサイズしてBase64エンコード（Anthropic API制限対応）
        
        Returns:
            Tuple[str, str]: (base64_encoded_data, media_type)
        """
        try:
            st.info("🔄 リサイズ処理を開始...")
            
            # 元の拡張子からメディアタイプを判定
            ext = Path(path).suffix.lower()
            preserve_format = ext in ['.png', '.webp']  # 透明度を保持したい形式
            
            with Image.open(path) as img:
                original_size = img.size
                original_mode = img.mode
                
                st.info(f"📐 元画像: {original_size[0]}x{original_size[1]}, モード: {original_mode}")
                
                # フォーマット決定
                if preserve_format and ext == '.png':
                    save_format = 'PNG'
                    media_type = 'image/png'
                elif preserve_format and ext == '.webp':
                    save_format = 'WebP'
                    media_type = 'image/webp'
                else:
                    save_format = 'JPEG'
                    media_type = 'image/jpeg'
                    # JPEGの場合はRGBに変換
                    if img.mode in ('RGBA', 'LA', 'P'):
                        # 透明度がある場合は白背景で合成
                        if img.mode == 'P':
                            img = img.convert('RGBA')
                        if 'transparency' in img.info or img.mode in ('RGBA', 'LA'):
                            background = Image.new('RGB', img.size, (255, 255, 255))
                            if img.mode == 'RGBA':
                                background.paste(img, mask=img.split()[-1])
                            else:
                                background.paste(img)
                            img = background
                        else:
                            img = img.convert('RGB')
                
                # 段階的リサイズ処理
                quality = 90 if save_format == 'JPEG' else None
                scale_factor = 0.9
                attempt = 0
                max_attempts = 15
                
                while attempt < max_attempts:
                    # 画像を保存してbase64エンコード
                    buffer = io.BytesIO()
                    
                    if save_format == 'JPEG':
                        img.save(buffer, format=save_format, quality=quality, optimize=True)
                    elif save_format == 'PNG':
                        img.save(buffer, format=save_format, optimize=True)
                    else:  # WebP
                        img.save(buffer, format=save_format, quality=quality or 90, optimize=True)
                    
                    # base64エンコード
                    buffer.seek(0)
                    image_bytes = buffer.read()
                    encoded_data = base64.b64encode(image_bytes).decode('utf-8')
                    encoded_size = len(encoded_data.encode('utf-8'))
                    
                    size_mb = encoded_size / (1024 * 1024)
                    
                    if encoded_size <= max_base64_bytes:
                        st.success(f"✅ リサイズ完了: {img.size[0]}x{img.size[1]} → {size_mb:.2f}MB (base64)")
                        return encoded_data, media_type
                    
                    # サイズがまだ大きい場合の調整
                    attempt += 1
                    
                    if attempt <= 5:
                        # 最初は品質を下げる（JPEGとWebPのみ）
                        if save_format in ['JPEG', 'WebP'] and quality:
                            quality = max(60, quality - 10)
                    else:
                        # サイズを縮小
                        new_width = int(img.width * scale_factor)
                        new_height = int(img.height * scale_factor)
                        
                        # 最小サイズチェック
                        if new_width < 100 or new_height < 100:
                            st.error("❌ 最小サイズ(100x100)を下回るため、リサイズを中止")
                            return "", media_type
                        
                        img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
                        
                        # 品質もさらに下げる
                        if save_format in ['JPEG', 'WebP'] and quality:
                            quality = max(40, quality - 5)
                    
                    if attempt % 3 == 0:
                        st.info(f"🔄 リサイズ中 ({attempt}/{max_attempts}): {img.size[0]}x{img.size[1]}, {size_mb:.2f}MB")
                
                st.error(f"❌ 最大試行回数({max_attempts})を超過。最終サイズ: {size_mb:.2f}MB")
                return "", media_type
                            
        except Exception as e:
            st.error(f"❌ 画像リサイズエラー: {e}")
            return "", "image/jpeg"

    def _process_image_question(self, question: str, image_url: str, temperature: Optional[float]):
        """画像質問の処理（統一化版）"""
        messages = get_default_messages()
        messages.append({
            "role": "user",
            "content": [
                {"type": "text", "text": question},
                {
                    "type": "image",
                    "source": {
                        "type": "url",
                        "url": image_url
                    }
                }
            ]
        })

        with st.spinner("処理中..."):
            response = self.call_api_unified(messages, temperature=temperature)

        st.subheader("回答:")
        ResponseProcessorUI.display_response(response)

    def _process_base64_image(self, file_path: str, question: str, temperature: Optional[float]):
        """Base64画像の処理（Anthropic API対応版）"""
        # 画像エンコード
        with st.spinner("🔄 画像をエンコード中..."):
            b64_data, media_type = self._encode_image(file_path)
            
        if not b64_data:
            st.error("❌ 画像のエンコードに失敗しました")
            return

        # エンコード結果の表示
        st.success(f"✅ エンコード完了: {media_type}")
        
        # メッセージ構築（Anthropic API形式）
        messages = get_default_messages()
        messages.append({
            "role": "user",
            "content": [
                {"type": "text", "text": question},
                {
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": media_type,
                        "data": b64_data
                    }
                }
            ]
        })

        # API呼び出し
        with st.spinner("🤖 Claude が画像を解析中..."):
            try:
                response = self.call_api_unified(messages, temperature=temperature)
                
                st.success("✅ 画像解析が完了しました")
                st.subheader("🎯 解析結果:")
                ResponseProcessorUI.display_response(response)
                
            except Exception as e:
                st.error(f"❌ API呼び出しエラー: {str(e)}")
                if "image too large" in str(e).lower():
                    st.info("💡 画像サイズが大きすぎる可能性があります。より小さな画像をお試しください。")


# ==================================================
# 構造化出力デモ（修正版・左ペインモデル選択統一）
# ==================================================
class StructuredOutputDemo(BaseDemo):
    """構造化出力のデモ"""

    class Event(BaseModel):
        """イベント情報のPydanticモデル"""
        name: str
        date: str
        participants: List[str]

    def __init__(self, demo_name: str, use_parse: bool = False):
        super().__init__(demo_name)
        self.use_parse = use_parse

    @error_handler_ui
    @timer_ui
    def run(self):
        """デモの実行（修正版・左ペインモデル選択統一）"""
        self.initialize()  # 左ペインにモデル選択が作成される
        st.write(
            "構造化出力特化のAnthropic Messages APIデモ。PydanticモデルとJSON Schemaによる型安全な出力抽出。"
            "イベント情報の構造化抽出例を通じて、データ処理アプリでのAPI活用を学習。"
        )
        with st.expander("Anthropic API実装例", expanded=False):
            st.code("""
            # イベント情報のPydanticモデル
            class Event(BaseModel):
                name: str
                date: str
                participants: List[str]
            
            # Anthropicでは構造化出力を直接サポートしていないため、
            # JSON形式で回答を要求し、後でPydanticでパースする
            
            system_prompt = "あなたはイベント情報を抽出するアシスタントです。\\n以下のJSON形式で必ず回答してください：\\n{\\n  \\"name\\": \\"イベント名\\",\\n  \\"date\\": \\"YYYY-MM-DD形式の日付\\",\\n  \\"participants\\": [\\"参加者名のリスト\\"]\\n}"
            
            messages = [
                {"role": "user", "content": text}
            ]
            
            api_params = {
                "messages": messages,
                "model": model,
                "system": system_prompt,
                "max_tokens": 4096
            }
            response = self.client.messages.create(**api_params)
            
            # JSONレスポンスをPydanticモデルでパース
            json_text = response.content[0].text
            event = Event.model_validate_json(json_text)
            
            """)

        # 選択されたモデルの表示（情報として）
        st.info(f"🤖 使用モデル: **{self.model}**")

        # モデルの推奨事項
        if "claude-3-5-sonnet" in self.model:
            st.success("✅ 構造化出力に適したモデルが選択されています")
        elif "claude-3-5-haiku" in self.model:
            st.info("ℹ️ Haikuモデルでも構造化出力は可能ですが、Sonnetが推奨されます")
        else:
            st.info("ℹ️ 構造化出力には claude-3-5-sonnet モデルが推奨されます")

        # イベント情報入力
        default_event = config.get("samples.prompts.event_example",
                                   "台湾フェス2025-08-21 ～あつまれ！究極の台湾グルメ～")

        st.subheader("📝 イベント情報入力")
        text = st.text_input(
            "イベント詳細を入力",
            value=default_event,
            key=f"struct_input_{self.safe_key}",
            help="イベント名、日付、参加者情報を含むテキストを入力してください"
        )

        # 統一されたtemperatureコントロール
        temperature = self.create_temperature_control(
            default_temp=0.1,
            help_text="構造化出力では低い値を推奨"
        )

        # 実行方式の選択
        st.subheader("⚙️ 実行方式")
        use_parse_option = st.radio(
            "実行方式を選択",
            ["messages.create() を使用", "Pydanticパース を使用"],
            index=0 if not self.use_parse else 1,
            key=f"parse_option_{self.safe_key}",
            help="messages.create()は汎用的、Pydanticパースは構造化データ特化"
        )

        # 選択に基づいてuse_parseを更新
        self.use_parse = (use_parse_option == "Pydanticパース を使用")

        # 実行ボタン
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            execute_button = st.button(
                "🚀 イベント抽出を実行",
                key=f"struct_btn_{self.safe_key}",
                use_container_width=True,
                type="primary"
            )

        # 実行処理
        if execute_button and text.strip():
            if self.use_parse:
                self._run_with_parse(self.model, text, temperature)
            else:
                self._run_with_create(self.model, text, temperature)
        elif execute_button and not text.strip():
            st.warning("⚠️ イベント詳細を入力してください。")

        # サンプル表示
        self._show_sample_output()

    def _run_with_create(self, model: str, text: str, temperature: Optional[float]):
        """responses.createを使用した実行（修正版）"""
        try:
            st.info("🔄 responses.create() でイベント情報を抽出中...")

            schema = {
                "type"                : "object",
                "properties"          : {
                    "name"        : {
                        "type"       : "string",
                        "description": "イベントの名前"
                    },
                    "date"        : {
                        "type"       : "string",
                        "description": "イベントの開催日（YYYY-MM-DD形式）"
                    },
                    "participants": {
                        "type"       : "array",
                        "items"      : {"type": "string"},
                        "description": "参加者リスト"
                    },
                },
                "required"            : ["name", "date", "participants"],
                "additionalProperties": False,
            }

            messages = [
                EasyInputMessageParam(
                    role="user",
                    content="Extract event details from the text. Extract name, date, and participants."
                ),
                EasyInputMessageParam(
                    role="user",
                    content=[{"type": "text", "text": text}]
                ),
            ]

            # Anthropic APIでは構造化出力の設定方法が異なる
            # システムメッセージで構造化出力を指定
            system_msg = f"""以下のJSONスキーマに従って応答してください：

{json.dumps(schema, indent=2, ensure_ascii=False)}

必ずこの形式でJSONを返してください。"""

            with st.spinner("🤖 AI がイベント情報を抽出しています..."):
                # Anthropic APIの標準的な呼び出し方法
                api_params = {
                    "model": model,
                    "system": system_msg,
                    "messages": messages,
                    "max_tokens": 4096
                }

                # temperatureサポートチェック
                if not self.is_reasoning_model(model) and temperature is not None:
                    api_params["temperature"] = temperature

                response = self.call_api_unified(
                    messages=messages,
                    model=model,
                    temperature=temperature,
                    system=system_msg
                )

            # 結果の表示
            st.success("✅ イベント情報の抽出が完了しました")

            # レスポンスからJSON部分を抽出してPydanticモデルで検証
            try:
                response_text = response.content[0].text if hasattr(response, 'content') else str(response)
                # JSON部分を抽出（```json ブロックがある場合の処理）
                if '```json' in response_text:
                    json_start = response_text.find('```json') + 7
                    json_end = response_text.find('```', json_start)
                    json_text = response_text[json_start:json_end].strip()
                else:
                    # JSON形式のテキストをそのまま使用
                    json_text = response_text.strip()
                
                event = self.Event.model_validate_json(json_text)
            except (json.JSONDecodeError, ValueError) as json_err:
                # JSONパースに失敗した場合、文字列から辞書形式で抽出を試行
                st.warning("JSON形式での解析に失敗したため、文字列から抽出を試行します...")
                try:
                    # 簡易的な辞書型抽出（この部分は改善の余地あり）
                    event = self.Event(
                        event_name="解析エラー",
                        date="未設定",
                        location="未設定", 
                        description=response_text[:200] + "..." if len(response_text) > 200 else response_text
                    )
                except Exception as e:
                    st.error(f"構造化データの解析に完全に失敗しました: {e}")
                    return

            st.subheader("📋 抽出結果 (messages.create)")
            self._display_extracted_event(event, response)

        except (ValidationError, json.JSONDecodeError) as e:
            st.error("❌ 構造化データの解析に失敗しました")
            with st.expander("🔧 エラー詳細", expanded=False):
                st.exception(e)
        except Exception as e:
            self.handle_error(e)

    def _run_with_parse(self, model: str, text: str, temperature: Optional[float]):
        """responses.parseを使用した実行"""
        try:
            st.info("🔄 responses.parse() でイベント情報を抽出中...")

            # Responses API用のメッセージ形式に変更
            # Anthropic APIで構造化出力を行うためのシステムメッセージ
            schema = self.Event.model_json_schema()
            system_msg = f"""以下のJSONスキーマに従ってイベント情報を抽出してください：

{json.dumps(schema, indent=2, ensure_ascii=False)}

必ずこの形式でJSONのみを返してください。他のテキストは含めないでください。"""

            messages = [
                {
                    "role": "user",
                    "content": f"次のテキストからイベント情報を抽出してください: {text}"
                }
            ]

            with st.spinner("🔄 responses.parse() でイベント情報を抽出中..."):
                try:
                    response = self.call_api_unified(
                        messages=messages,
                        model=model,
                        temperature=temperature,
                        system=system_msg
                    )

                    # レスポンスからJSON部分を抽出
                    response_text = response.content[0].text if hasattr(response, 'content') else str(response)
                    
                    # JSON部分のみを抽出
                    json_text = response_text.strip()
                    if json_text.startswith('```json'):
                        json_start = json_text.find('\n') + 1
                        json_end = json_text.rfind('```')
                        json_text = json_text[json_start:json_end].strip()
                    
                    # Pydanticモデルで検証
                    event = self.Event.model_validate_json(json_text)
                    
                    # 結果の表示
                    st.success("✅ イベント情報の抽出が完了しました")
                    st.subheader("📋 抽出結果 (Pydanticパース)")
                    self._display_extracted_event(event, response)
                    
                except json.JSONDecodeError as json_err:
                    st.error(f"❌ JSON解析エラー: {json_err}")
                    st.info("レスポンス内容:")
                    st.text(response_text[:500] + "..." if len(response_text) > 500 else response_text)
                except ValidationError as val_err:
                    st.error(f"❌ バリデーションエラー: {val_err}")
                except Exception as api_err:
                    st.error(f"❌ API呼び出しエラー: {api_err}")

        except Exception as e:
            st.error(f"❌ responses.parse実行エラー: {str(e)}")
            self.handle_error(e)

    def _display_extracted_event(self, event: Event, response):
        """抽出されたイベント情報の表示（エクスパンダー入れ子修正版）"""
        # メインの結果表示
        col1, col2 = st.columns([2, 1])

        with col1:
            # イベント情報を見やすく表示
            st.write("**🎉 イベント名**")
            st.success(event.name)

            st.write("**📅 開催日**")
            st.info(event.date)

            st.write("**👥 参加者**")
            if event.participants:
                for i, participant in enumerate(event.participants, 1):
                    st.write(f"{i}. {participant}")
            else:
                st.write("参加者情報なし")

        with col2:
            # 統計情報
            st.metric("参加者数", len(event.participants))
            if hasattr(response, 'usage') and response.usage:
                usage = response.usage
                if hasattr(usage, 'total_tokens'):
                    st.metric("使用トークン数", getattr(usage, 'total_tokens', 0))

        # 構造化データの表示（エクスパンダーなしで直接表示）
        st.write("---")
        st.write("**🔧 構造化データ (Pydantic):**")

        # Pydanticモデルとして表示
        safe_streamlit_json(event.model_dump())

        # Pythonオブジェクトとして表示
        st.write("**Python オブジェクト:**")
        st.code(repr(event), language="python")

        # レスポンス詳細（エクスパンダーなしで簡潔に表示）
        st.write("---")
        st.write("**📊 API レスポンス概要:**")

        # 基本情報のみ表示
        info_cols = st.columns(3)
        with info_cols[0]:
            model_name = getattr(response, 'model', 'N/A')
            st.write(f"**モデル**: {model_name}")
        with info_cols[1]:
            response_id = getattr(response, 'id', 'N/A')
            st.write(f"**ID**: {response_id[:10]}..." if len(str(response_id)) > 10 else f"**ID**: {response_id}")
        with info_cols[2]:
            st.write(f"**形式**: Structured JSON")

    def _show_sample_output(self):
        """サンプル出力の表示（修正版）"""
        with st.expander("📖 サンプル出力例", expanded=False):
            st.write("**入力例:**")
            st.code('台湾フェス2025 ～あつまれ！究極の台湾グルメ～ in Kawasaki Spark', language="text")

            st.write("**期待される出力:**")
            sample_event = {
                "name"        : "台湾フェス2025 ～あつまれ！究極の台湾グルメ～",
                "date"        : "2025-08-15",
                "participants": ["グルメ愛好家", "台湾料理ファン", "地域住民"]
            }
            safe_streamlit_json(sample_event)

            st.write("**実行方式の違い:**")
            st.write("- **responses.create()**: JSON Schemaを使用した汎用的な構造化出力")
            st.write("- **responses.parse()**: Pydanticモデルを直接使用した型安全な出力")

            st.write("**Pydantic モデル定義:**")
            st.code('''
class Event(BaseModel):
    """イベント情報のPydanticモデル"""
    name: str
    date: str
    participants: List[str]
            ''', language="python")


# ==================================================
# 天気デモ
# ==================================================
class WeatherDemo(BaseDemo):
    """OpenWeatherMap APIを使用した天気デモ（改修版・ボタン実行対応）"""

    @error_handler_ui
    @timer_ui
    def run(self):
        """デモの実行（改修版）"""
        self.initialize()
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

# ==================================================
# FileSearchデモ
# ==================================================
# 作成: POST /v1/vector_stores
# 一覧取得: GET /v1/vector_stores
# 詳細取得: GET /v1/vector_stores/{vector_store_id}
# 更新: POST /v1/vector_stores/{vector_store_id}
# 削除: DELETE /v1/vector_stores/{vector_store_id}
# 検索: POST /v1/vector_stores/{vector_store_id}/search
# ==================================================
class FileSearchVectorStoreDemo(BaseDemo):
    """FileSearch専用デモ（正しいOpenAI API対応版）"""

    def __init__(self, demo_name: str):
        super().__init__(demo_name)
        self._vector_stores_cache = None
        self._cache_timestamp = None
        self._cache_ttl = 300  # 5分間キャッシュ

    @error_handler_ui
    @timer_ui
    def run(self):
        """デモの実行（正しいAPI対応版）"""
        self.initialize()
        st.header("FileSearchデモ")
        with st.expander("利用：OpenWeatherMap API(比較用)", expanded=False):
            st.code("""
            Anthropic APIにEmbedding, RAGの機能は、実装されていません。
            以下のレポジトリーに、cloud版、Local版のRAGシステムの例（デモ）があります。
            https://github.com/nakashima2toshio/openai_rag_jp
            
            """)


# ==================================================
# WebSearch Toolsデモ
# ==================================================
class WebSearchToolsDemo(BaseDemo):
    """自然言語による天気検索デモ（AI + OpenWeatherMap API連携）"""
    
    # 都市エリア→都市名マッピング辞書
    AREA_TO_CITY_MAPPING = {
        "新宿": "Tokyo", "渋谷": "Tokyo", "池袋": "Tokyo", "銀座": "Tokyo", 
        "品川": "Tokyo", "秋葉原": "Tokyo", "浅草": "Tokyo", "上野": "Tokyo",
        "六本木": "Tokyo", "恵比寿": "Tokyo", "原宿": "Tokyo", "表参道": "Tokyo",
        "梅田": "Osaka", "なんば": "Osaka", "心斎橋": "Osaka", "天王寺": "Osaka",
        "神戸": "Kobe", "三宮": "Kobe", "元町": "Kobe",
        "みなとみらい": "Yokohama", "関内": "Yokohama", "中華街": "Yokohama",
        "博多": "Fukuoka", "天神": "Fukuoka",
        "すすきの": "Sapporo", "大通": "Sapporo",
        "栄": "Nagoya", "名駅": "Nagoya"
    }

    @error_handler_ui
    @timer_ui
    def run(self):
        """自然言語天気検索デモの実行"""
        self.initialize()
        st.write("サブアプリ：WeatherSearchDemo (改修版)")
        st.header("自然言語対応: 天気検索デモ")
        st.write(
            "自然言語で天気を検索できます。例：『明日の東京の天気は？』『新宿の天気を教えて』等の文章から"
            "都市を抽出し、OpenWeather APIで天気情報を取得します。AI + 外部API連携の実装例。"
        )
        with st.expander("利用技術：Anthropic AI + OpenWeatherMap API", expanded=False):
            st.code("""
            # 必要な環境変数
            export ANTHROPIC_API_KEY='your-anthropic-key'
            export OPENWEATHER_API_KEY='your-openweather-key'
            
            # Step 1: AI による都市名抽出
            messages = [MessageParam(
                role="user",
                content=f"以下の文章から都市名を抽出してください: {user_input}"
            )]
            
            # Step 2: 都市データマッチング
            matched_city = self._find_matching_city(extracted_city)
            
            # Step 3: OpenWeather API 呼び出し
            weather_data = self._get_current_weather(lat, lon)
            """)

        # 自然言語入力UI
        user_input = self._input_natural_language()
        
        # 天気検索ボタン
        col1, col2, col3 = st.columns([2, 1, 2])
        with col2:
            weather_search = st.button(
                "🌤️ 天気を検索",
                key=f"weather_search_btn_{self.safe_key}",
                use_container_width=True,
                type="primary",
                help="入力された文章から都市を抽出して天気を検索します"
            )

        # APIキーの確認
        if not self._check_required_api_keys():
            return

        # 天気検索ボタンが押された場合
        if weather_search and user_input:
            st.info(f"🔍 『{user_input}』を解析中...")
            self._process_weather_search(user_input)
    
    def _input_natural_language(self) -> str:
        """自然言語入力UI"""
        st.subheader("📝 天気を知りたい場所を教えてください")
        st.write("例：『明日の東京の天気は？』『新宿の天気を教えて』『大阪は雨が降る？』等")
        
        # 自然言語入力
        user_input = st.text_area(
            "天気を知りたい場所を自由に入力してください",
            value=config.get("samples.prompts.search_query", "明日の東京の新宿の天気は？"),
            key=f"weather_input_{self.safe_key}",
            help="日本の都市名やエリア名を含む文章を入力してください",
            height=100
        )
        
        return user_input.strip()
    
    def _check_required_api_keys(self) -> bool:
        """APIキーの確認"""
        # Anthropic APIキー確認
        anthropic_key = os.getenv("ANTHROPIC_API_KEY")
        if not anthropic_key:
            st.warning("⚠️ ANTHROPIC_API_KEY環境変数が設定されていません")
            st.info("AIによる都市名抽出には、Anthropic APIキーが必要です。")
            st.code("export ANTHROPIC_API_KEY='your-anthropic-key'", language="bash")
            return False
            
        # OpenWeather APIキー確認
        weather_key = os.getenv("OPENWEATHER_API_KEY")
        if not weather_key:
            st.warning("⚠️ OPENWEATHER_API_KEY環境変数が設定されていません")
            st.info("天気情報の取得には、OpenWeatherMap APIキーが必要です。")
            st.code("export OPENWEATHER_API_KEY='your-openweather-key'", language="bash")
            st.info("**登録URL:** https://openweathermap.org/api")
            return False
            
        return True
    
    def _process_weather_search(self, user_input: str):
        """天気検索の処理メインロジック"""
        try:
            # 実行時間の計測開始
            start_time = time.time()

            # Step 1: AIで都市名を抽出
            with st.spinner("🤖 AIで都市名を抽出中..."):
                extracted_city = self._extract_city_with_ai(user_input)

            if not extracted_city:
                st.error("❌ 都市名を抽出できませんでした。日本の都市名やエリア名を含む文章で再度お試しください。")
                return

            st.success(f"✅ 抽出された都市: {extracted_city}")

            # Step 2: 都市データマッチング
            with st.spinner("🗺️ 都市データでマッチング中..."):
                matched_city_data = self._find_matching_city(extracted_city)

            if not matched_city_data:
                st.error(f"❌ '{extracted_city}'に一致する都市が見つかりませんでした。")
                return

            city_name, lat, lon = matched_city_data
            st.success(f"✅ マッチした都市: {city_name} ({lat:.4f}, {lon:.4f})")

            # マッチ情報表示
            with st.expander("🗺️ マッチした都市情報", expanded=True):
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    st.metric("入力文", user_input[:20] + "..." if len(user_input) > 20 else user_input)
                with col2:
                    st.metric("抽出都市", extracted_city)
                with col3:
                    st.metric("マッチ都市", city_name)
                with col4:
                    st.metric("座標", f"{lat:.2f}, {lon:.2f}")

            # Step 3: OpenWeather APIで天気取得
            with st.spinner(f"🌤️ {city_name}の天気情報を取得中..."):
                weather_data = self._get_weather_data(lat, lon, city_name)

            if weather_data:
                st.success("✅ 天気情報を取得しました")
                self._display_weather_results(weather_data, user_input, extracted_city, city_name)

            # 実行時間の表示
            end_time = time.time()
            execution_time = end_time - start_time

            with st.expander("🔧 処理詳細", expanded=False):
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("実行時間", f"{execution_time:.2f}秒")
                with col2:
                    st.metric("API呼び出し数", "3回")  # AI抽出 + 現在天気 + 5日間予報
                with col3:
                    st.metric("データ形式", "JSON")

                st.write("**処理ステップ:**")
                st.write("1. Anthropic AI: 自然言語から都市名抽出")
                st.write("2. ローカル処理: 都市データマッチング")
                st.write("3. OpenWeatherMap API: 天気情報取得")
                st.write("- データ更新頻度: リアルタイム")

        except Exception as e:
            st.error(f"❌ 天気検索処理に失敗しました: {str(e)}")
            logger.error(f"Weather search error: {e}")

            # エラーの詳細表示（デバッグモード時）
            if config.get("experimental.debug_mode", False):
                with st.expander("🔧 エラー詳細", expanded=False):
                    st.exception(e)
    
    def _execute_search(self, search_api: str, query: str, results_count: int, api_params: dict) -> List[dict]:
        """検索の実行（改修版）"""
        if search_api == "ダミーデータ":
            # ダミーデータを返す
            return [
                {
                    'title': f'ダミー検索結果 {i+1}: {query}に関する情報',
                    'url': f'https://example.com/result{i+1}',
                    'snippet': f'これは{query}に関するダミーの検索結果です。実際の検索APIを使用する場合は、適切なAPIキーを設定してください。'
                }
                for i in range(results_count)
            ]
        
        elif search_api == "Google Custom Search":
            return self._google_search(query, results_count)
        
        elif search_api == "Bing Search":
            return self._bing_search(query, results_count)
            
        elif search_api == "SerpAPI":
            return self._serp_search(query, results_count)
        
        else:
            raise ValueError(f"サポートされていない検索API: {search_api}")
    
    def _extract_city_with_ai(self, user_input: str) -> str:
        """自然言語からAIで都市名を抽出"""
        try:
            messages = [
                EasyInputMessageParam(
                    role="user",
                    content=f"""
以下の文章から日本の都市名やエリア名を抽出してください。

入力文: {user_input}

条件:
- 日本の都市名やエリア名のみ抽出してください
- 一番重要で明確な都市名・エリア名を一つだけ選んでください
- 都市名のみを答えてください（説明は不要）
- 見つからない場合は「NOT_FOUND」と答えてください

例:
- 「明日の東京の天気は？」→ 東京
- 「新宿の天気を教えて」→ 新宿  
- 「大阪は雨が降る？」→ 大阪
                    """
                )
            ]
            
            response = self.call_api_unified(messages=messages)
            if response and hasattr(response, 'content'):
                extracted_text = response.content[0].text.strip() if response.content else ""
                return extracted_text if extracted_text != "NOT_FOUND" else None
            return None
            
        except Exception as e:
            st.error(f"❌ AIでの都市名抽出エラー: {e}")
            logger.error(f"City extraction error: {e}")
            return None
    
    def _find_matching_city(self, extracted_city: str) -> tuple:
        """抽出された都市名を都市データでマッチング"""
        try:
            # city_jp.list.jsonを読み込み
            cities_json = config.get("paths.cities_json", "data/city_jp.list.json")
            if not Path(cities_json).exists():
                st.error(f"都市データファイルが見つかりません: {cities_json}")
                return None
            
            # 日本の都市データ読み込み（WeatherDemoと同じロジック）
            with open(cities_json, "r", encoding="utf-8") as f:
                cities_list = json.load(f)
            
            cities_df = pd.DataFrame([
                {
                    "name": city["name"],
                    "lat" : city["coord"]["lat"],
                    "lon" : city["coord"]["lon"],
                    "id"  : city["id"]
                }
                for city in cities_list
            ])
            
            # 1. エリア→都市マッピングをチェック
            if extracted_city in self.AREA_TO_CITY_MAPPING:
                target_city = self.AREA_TO_CITY_MAPPING[extracted_city]
                st.info(f"🗺️ エリア '{extracted_city}' を都市 '{target_city}' にマッピングしました")
            else:
                target_city = extracted_city
            
            # 2. 完全一致検索
            exact_match = cities_df[cities_df["name"].str.contains(target_city, case=False, na=False)]
            if not exact_match.empty:
                row = exact_match.iloc[0]
                return row["name"], row["lat"], row["lon"]
            
            # 3. 部分一致検索
            partial_match = cities_df[cities_df["name"].str.contains(target_city, case=False, na=False)]
            if not partial_match.empty:
                row = partial_match.iloc[0]
                return row["name"], row["lat"], row["lon"]
            
            # 4. 類似度マッチング（difflib使用）
            import difflib
            city_names = cities_df["name"].tolist()
            close_matches = difflib.get_close_matches(target_city, city_names, n=1, cutoff=0.6)
            if close_matches:
                matched_name = close_matches[0]
                row = cities_df[cities_df["name"] == matched_name].iloc[0]
                st.info(f"🔍 類似マッチング: '{target_city}' → '{matched_name}'")
                return row["name"], row["lat"], row["lon"]
            
            return None
            
        except Exception as e:
            st.error(f"❌ 都市マッチングエラー: {e}")
            logger.error(f"City matching error: {e}")
            return None
    
    def _get_weather_data(self, lat: float, lon: float, city_name: str) -> dict:
        """OpenWeather APIで天気データを取得（WeatherDemoと統合）"""
        try:
            # 現在の天気取得
            current_weather = self._get_current_weather(lat, lon)
            
            # 5日間予報取得
            forecast_data = self._get_weekly_forecast(lat, lon)
            
            return {
                "current": current_weather,
                "forecast": forecast_data,
                "city_name": city_name,
                "coordinates": {"lat": lat, "lon": lon}
            }
            
        except Exception as e:
            st.error(f"❌ 天気データ取得エラー: {e}")
            logger.error(f"Weather data error: {e}")
            return None
    
    def _get_current_weather(self, lat: float, lon: float, unit: str = "metric") -> dict:
        """現在の天気を取得（WeatherDemoから流用）"""
        api_key = os.getenv("OPENWEATHER_API_KEY")
        if not api_key:
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
        except Exception as e:
            logger.error(f"Current weather API error: {e}")
            return None
    
    def _get_weekly_forecast(self, lat: float, lon: float, unit: str = "metric") -> list:
        """5日間予報を取得（WeatherDemoから流用）"""
        api_key = os.getenv("OPENWEATHER_API_KEY")
        if not api_key:
            return []

        try:
            url = "http://api.openweathermap.org/data/2.5/forecast"
            params = {
                "lat"  : lat,
                "lon"  : lon,
                "appid": api_key,
                "units": unit,
                "lang" : "ja"
            }

            response = requests.get(url, params=params, timeout=config.get("api.timeout", 30))
            response.raise_for_status()
            data = response.json()

            # 3時間毎データを日別に集約
            daily_data = {}
            for item in data.get("list", []):
                date_str = datetime.fromtimestamp(item["dt"]).strftime("%Y-%m-%d")
                if date_str not in daily_data:
                    daily_data[date_str] = []
                daily_data[date_str].append({
                    "temp": item["main"]["temp"],
                    "weather": item["weather"][0]["description"]
                })

            # 日別平均を計算
            forecast = []
            for date_str in sorted(daily_data.keys()):
                temps = [d["temp"] for d in daily_data[date_str]]
                avg_temp = sum(temps) / len(temps) if temps else 0
                weather_desc = daily_data[date_str][0]["weather"]  # 最初の天気を代表とする

                forecast.append({
                    "date": date_str,
                    "temp_avg": round(avg_temp, 1),
                    "weather": weather_desc
                })

            return forecast[:5]  # 5日分のみ
        except Exception as e:
            logger.error(f"Weekly forecast API error: {e}")
            return []
    
    def _display_weather_results(self, weather_data: dict, user_input: str, extracted_city: str, matched_city: str):
        """天気検索結果の表示"""
        try:
            current = weather_data.get("current", {})
            forecast = weather_data.get("forecast", [])
            
            # 現在の天気表示
            if current:
                with st.container():
                    st.write("### 🌤️ 現在の天気")
                    
                    col1, col2, col3, col4 = st.columns(4)
                    with col1:
                        st.metric("🏙️ 都市", current.get('city', matched_city))
                    with col2:
                        st.metric("🌡️ 気温", f"{current.get('temperature', 0)}℃")
                    with col3:
                        st.metric("💨 天気", current.get('description', 'N/A'))
                    with col4:
                        coord = current.get('coord', {})
                        st.metric("📍 座標", f"{coord.get('lat', 0):.2f}, {coord.get('lon', 0):.2f}")
            
            # 5日間予報表示
            if forecast:
                with st.container():
                    st.write("### 📅 5日間予報")
                    
                    forecast_df = pd.DataFrame(forecast)
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
                    
                    # 気温推移グラフ
                    if len(forecast) > 1:
                        st.write("### 📈 気温推移")
                        temp_data = pd.DataFrame({
                            '日付': [item['date'] for item in forecast],
                            '平均気温': [item['temp_avg'] for item in forecast]
                        })
                        st.line_chart(temp_data.set_index('日付'))
                        
        except Exception as e:
            st.error(f"❌ 天気結果表示エラー: {e}")
            logger.error(f"Weather display error: {e}")


# ==================================================
# Computer Useデモ（統一化版）
# ==================================================
class ComputerUseDemo(BaseDemo):
    """Computer Use Tool のデモ（統一化版）"""
    pass

# ==================================================
# デモマネージャー
# ==================================================
class DemoManager:
    """デモの管理クラス（統一化版）"""

    def __init__(self):
        self.config = ConfigManager("config.yml")
        self.demos = self._initialize_demos()

    def _initialize_demos(self) -> Dict[str, BaseDemo]:
        """デモインスタンスの初期化（統一化版）"""
        return {
            "Text Responses (One Shot)"  : TextResponseDemo("Anthropic API-Text Responses(one shot)"),
            "Text Responses (Memory)"    : MemoryResponseDemo("Text Responses(memory)"),
            "Image to Text 画像入力(URL)"   : ImageResponseDemo("Image_URL", use_base64=False),
            "Image to Text 画像入力(base64)": ImageResponseDemo("Image_Base64", use_base64=True),
            "Structured Output 構造化出力" : StructuredOutputDemo("Structured_Output_create", use_parse=False),
            "Open Weather API(比較用)" : WeatherDemo("OpenWeatherAPI"),
            "File Search-Tool vector store": FileSearchVectorStoreDemo("FileSearch_vsid"),
            "Tools - Weather Search (AI + API)": WebSearchToolsDemo("WeatherSearch"),
        }

    @error_handler_ui
    @timer_ui
    def run(self):
        """アプリケーションの実行（統一化版）"""
        # セッション状態の初期化（統一化）
        SessionStateManager.init_session_state()

        # デモ選択
        demo_name = st.sidebar.radio(
            "[a00_responses_api.py] デモを選択",
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
        st.sidebar.markdown("- Anthropic Responses API Demo v3.0 (統一化版)")
        st.sidebar.markdown("- Streamlit " + st.__version__)

        # リンク
        st.sidebar.markdown("### リンク")
        st.sidebar.markdown("[Anthropic API ドキュメント](https://docs.anthropic.com/claude)")
        st.sidebar.markdown("[Streamlit ドキュメント](https://docs.streamlit.io)")

        # 統計情報
        with st.sidebar.expander("📊 統計情報"):
            st.metric("利用可能デモ数", len(self.demos))
            st.metric("現在のデモ", st.session_state.get("current_demo", "未選択"))


# ==================================================
# メイン関数
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
        if not os.getenv("ANTHROPIC_API_KEY"):
            st.error("環境変数 ANTHROPIC_API_KEY が設定されていません。")
            st.info("export ANTHROPIC_API_KEY='your-api-key' を実行してください。")
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

# streamlit run a00_responses_api.py --server.port=8510

