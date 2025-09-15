# streamlit run a05_conversation_state.py --server.port=8505
# --------------------------------------------------
# Anthropic 会話状態管理デモアプリケーション（統一化版）
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

from anthropic import Anthropic

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
        config, logger, TokenManager, AnthropicClient,
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
            page_title=config.get("ui.page_title", "Anthropic 会話状態管理デモ"),
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
# 会話管理ユーティリティクラス
# ==================================================
class ConversationContextManager:
    """会話コンテキスト管理クラス"""
    
    def __init__(self):
        self.context = {}
        self.metadata = {}
    
    def add_context(self, key: str, value: Any):
        """コンテキストを追加"""
        self.context[key] = value
    
    def get_context(self, key: str) -> Any:
        """コンテキストを取得"""
        return self.context.get(key)
    
    def clear_context(self):
        """コンテキストをクリア"""
        self.context.clear()
    
    def get_all_context(self) -> Dict[str, Any]:
        """全コンテキストを取得"""
        return self.context.copy()


class ConversationHistoryManager:
    """会話履歴管理クラス"""
    
    def __init__(self, max_length: Optional[int] = None):
        self.history = []
        self.max_history = max_length if max_length is not None else 100
        self.max_length = self.max_history  # エイリアス
    
    def add_message(self, role: str, content: str):
        """メッセージを追加"""
        self.history.append({
            "role": role,
            "content": content,
            "timestamp": datetime.now().isoformat()
        })
        
        # 最大履歴数を超えたら古いものから削除
        if len(self.history) > self.max_history:
            self.history = self.history[-self.max_history:]
    
    def get_history(self, limit: Optional[int] = None) -> List[Dict[str, str]]:
        """会話履歴を取得"""
        if limit:
            return self.history[-limit:]
        return self.history
    
    def clear_history(self):
        """履歴をクリア"""
        self.history.clear()
    
    def export_history(self) -> str:
        """履歴をJSON形式でエクスポート"""
        return json.dumps(self.history, ensure_ascii=False, indent=2)
    
    def import_history(self, json_str: str):
        """JSON形式から履歴をインポート"""
        try:
            self.history = json.loads(json_str)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON format: {e}")


class ConversationStateDemo:
    """会話状態管理デモクラス"""
    
    def __init__(self):
        self.demo_name = "Conversation State Demo"
        self.safe_key = sanitize_key(self.demo_name)
        self.client = None
        self.session_manager = SessionStateManager()
        self.context_manager = ConversationContextManager()
        self.history_manager = ConversationHistoryManager()
        self.conversation_manager = self.history_manager  # エイリアス
        self.message_manager = None
        self.model = "claude-3-haiku-20240307"
        
        # Anthropicクライアントの初期化を試みる
        try:
            self.client = AnthropicClient()
            self.message_manager = MessageManagerUI()
        except Exception as e:
            logger.warning(f"Failed to initialize client: {e}")
            if "API key not found" in str(e):
                if hasattr(st, '_is_running_with_streamlit') and st._is_running_with_streamlit:
                    st.error("APIキーが見つかりません。環境変数ANTHROPIC_API_KEYを設定してください。")
                    st.stop()
                else:
                    import sys
                    sys.exit(1)
    
    def process_message(self, message: str, model: Optional[str] = None) -> Dict[str, Any]:
        """メッセージを処理"""
        if not self.client:
            return {"error": "Client not initialized"}
        
        try:
            # 履歴にユーザーメッセージを追加
            self.history_manager.add_message("user", message)
            
            # メッセージを送信
            messages = self.history_manager.get_history(limit=10)
            response = self.client.client.messages.create(
                model=model or self.model,
                messages=messages,
                max_tokens=1024
            )
            
            # 履歴にアシスタントの応答を追加
            response_text = response.content[0].text if response.content else ""
            self.history_manager.add_message("assistant", response_text)
            
            return {
                "response": response,
                "text": response_text,
                "history": self.history_manager.get_history()
            }
            
        except Exception as e:
            return {"error": str(e)}
    
    def process_message_with_context(self, message: str, include_context: bool = False) -> Dict[str, Any]:
        """コンテキスト付きメッセージ処理"""
        if include_context:
            # コンテキストを追加
            context = self.context_manager.get_all_context()
            if context:
                message = f"[Context: {context}]\n{message}"
        
        return self.process_message(message)
    
    def run_basic_conversation_demo(self):
        """基本的な会話デモを実行"""
        st.write("### 基本的な会話デモ")
        self.run()
    
    def run_context_aware_conversation_demo(self):
        """コンテキスト認識会話デモを実行"""
        st.write("### コンテキスト認識会話デモ")
        # コンテキストを設定
        self.context_manager.add_context("mode", "context_aware")
        self.run()
    
    def run_conversation_history_management_demo(self):
        """会話履歴管理デモを実行"""
        st.write("### 会話履歴管理デモ")
        self.run()
    
    def run_multi_session_demo(self):
        """マルチセッションデモを実行"""
        st.write("### マルチセッションデモ")
        self.run()
    
    def save_state(self, filepath: str):
        """会話状態を保存"""
        state = {
            "history": self.history_manager.get_history(),
            "context": self.context_manager.get_all_context(),
            "timestamp": datetime.now().isoformat()
        }
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(state, f, ensure_ascii=False, indent=2)
    
    def save_conversation(self, filepath):
        """会話の保存（エイリアス）"""
        self.save_state(str(filepath))
    
    def load_state(self, filepath: str):
        """会話状態を読み込み"""
        with open(filepath, 'r', encoding='utf-8') as f:
            state = json.load(f)
        
        # 履歴を復元
        if "history" in state:
            self.history_manager.history = state["history"]
        
        # コンテキストを復元
        if "context" in state:
            self.context_manager.context = state["context"]
    
    def load_conversation(self, filepath):
        """会話の読み込み（エイリアス）"""
        self.load_state(str(filepath))
    
    def execute(self, selected_model: Optional[str] = None):
        """デモの実行（統一インターフェース）"""
        if selected_model:
            self.model = selected_model
        self.run()
    
    def run(self):
        """デモを実行"""
        st.write("## 会話状態管理デモ")
        
        # モデル選択
        model = UIHelper.select_model("conversation_model")
        self.model = model
        
        # 入力
        user_input = st.text_area(
            "メッセージを入力",
            height=100,
            key="conversation_input"
        )
        
        if st.button("送信", key="conversation_submit"):
            if user_input:
                result = self.process_message(user_input, self.model)
                
                if "error" in result:
                    st.error(f"エラー: {result['error']}")
                else:
                    st.success("メッセージを送信しました")
                    
                    # 応答を表示
                    if "text" in result:
                        st.write("### アシスタントの応答")
                        st.write(result["text"])
        
        # 履歴表示
        if st.button("履歴を表示", key="show_history"):
            history = self.history_manager.get_history()
            if history:
                st.write("### 会話履歴")
                for msg in history:
                    role = "👤 ユーザー" if msg["role"] == "user" else "🤖 アシスタント"
                    st.write(f"{role}: {msg['content']}")
            else:
                st.info("履歴はありません")


# 会話状態の保存・読み込み関数
def save_conversation_state(conversation_history: List[Dict[str, str]], filepath: str):
    """会話状態を保存"""
    state = {
        "history": conversation_history,
        "timestamp": datetime.now().isoformat()
    }
    
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(state, f, ensure_ascii=False, indent=2)


def load_conversation_state(filepath: str) -> Optional[List[Dict[str, str]]]:
    """会話状態を読み込み"""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            state = json.load(f)
        return state.get("history", [])
    except (FileNotFoundError, json.JSONDecodeError) as e:
        logger.warning(f"Failed to load conversation state: {e}")
        return None if isinstance(e, FileNotFoundError) else []


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
        
        # Anthropicクライアントの初期化
        try:
            self.client = AnthropicClient()
        except Exception as e:
            st.error(f"Anthropicクライアントの初期化に失敗しました: {e}")
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
        st.write("## 実装例: 会話履歴を使用した会話継続")
        st.write("前の会話コンテキストを保持したまま会話を継続する方法を示します。")
        
        # Anthropic APIのメモ
        with st.expander("📝 Anthropic API メモ", expanded=False):
            st.code("""
# Anthropic APIでの会話継続について

Anthropic APIには、OpenAI APIの previous_response_id に相当する
直接的な機能はありません。

代わりに、以下の方法で会話状態を管理します：

1. **会話履歴の管理**
   - メッセージ配列に過去の会話を含める
   - アシスタントとユーザーの交互のやり取りを保持

2. **実装パターン**
   ```python
   messages = [
       {"role": "user", "content": "初回の質問"},
       {"role": "assistant", "content": "初回の回答"},
       {"role": "user", "content": "追加の質問"}
   ]
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
        
        # 実装例サンプル表示
        with st.expander("📋 実装例コード", expanded=False):
            st.code("""
# ステートフルな会話継続の実装例
from anthropic import Anthropic

client = Anthropic()

# 初回質問
initial_response = client.messages.create(
    model=model,
    messages=[
        {"role": "user", "content": "Anthropic APIの使い方を教えて"}
    ],
    max_tokens=1024
)

# 会話履歴を保持
conversation_history = [
    {"role": "user", "content": "Anthropic APIの使い方を教えて"},
    {"role": "assistant", "content": initial_response.content[0].text}
]

# 会話の継続（履歴を含めて送信）
conversation_history.append(
    {"role": "user", "content": "具体的なコード例も教えて"}
)

follow_up_response = client.messages.create(
    model=model,
    messages=conversation_history,
    max_tokens=1024
)
            """, language="python")
        
        # 入力エリア
        st.subheader("📤 入力")
        
        # 初回質問
        initial_question = st.text_area(
            "初回の質問",
            value="Anthropic APIの使い方を教えて",
            height=config.get("ui.text_area_height", 75),
            key=f"initial_question_{self.safe_key}"
        )
        
        if st.button("🚀 初回質問を送信", key=f"initial_submit_{self.safe_key}"):
            if initial_question:
                self._process_initial_question(initial_question)
        
        # 追加質問（初回回答がある場合のみ表示）
        if f"conversation_history_{self.safe_key}" in st.session_state:
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
            messages = [
                {"role": "user", "content": question}
            ]
            
            with st.spinner("処理中..."):
                response = self.client.client.messages.create(
                    model=self.model,
                    messages=messages,
                    max_tokens=1024
                )
            
            # 会話履歴を保存
            conversation_history = [
                {"role": "user", "content": question},
                {"role": "assistant", "content": response.content[0].text}
            ]
            
            # セッション状態に保存
            st.session_state[f"conversation_history_{self.safe_key}"] = conversation_history
            st.session_state[f"initial_response_{self.safe_key}"] = response
            st.success(f"✅ 初回の質問を処理しました")
            st.rerun()
            
        except Exception as e:
            st.error(f"エラーが発生しました: {e}")
            if config.get("experimental.debug_mode", False):
                st.exception(e)
    
    def _process_follow_up_question(self, question: str):
        """追加質問の処理"""
        try:
            # 会話履歴を取得
            conversation_history = st.session_state[f"conversation_history_{self.safe_key}"]
            
            # 新しい質問を追加
            conversation_history.append({"role": "user", "content": question})
            
            with st.spinner("処理中（前の会話を引き継ぎ中）..."):
                response = self.client.client.messages.create(
                    model=self.model,
                    messages=conversation_history,
                    max_tokens=1024
                )
            
            # 会話履歴を更新
            conversation_history.append(
                {"role": "assistant", "content": response.content[0].text}
            )
            
            # セッション状態に保存
            st.session_state[f"conversation_history_{self.safe_key}"] = conversation_history
            st.session_state[f"follow_up_response_{self.safe_key}"] = response
            st.success(f"✅ 会話を継続しました")
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
        
        # 会話履歴の表示
        if f"conversation_history_{self.safe_key}" in st.session_state:
            with st.expander("💬 会話履歴", expanded=False):
                history = st.session_state[f"conversation_history_{self.safe_key}"]
                for msg in history:
                    if msg["role"] == "user":
                        st.markdown(f"👤 **ユーザー:** {msg['content']}")
                    else:
                        st.markdown(f"🤖 **アシスタント:** {msg['content']}")


class ToolUseDemo(BaseDemo):
    """ツール使用デモ"""

    def run_demo(self):
        """ツール使用デモの実行"""
        st.write("## 実装例: ツール使用と構造化出力")
        st.write("Anthropic APIのツール使用機能を使って外部ツールを呼び出し、構造化された出力を生成します。")
        
        # Anthropic APIのメモ
        with st.expander("📝 Anthropic API メモ", expanded=False):
            st.code("""
# Anthropic APIでのツール使用について

OpenAI APIの Web検索ツール (web_search_preview) に相当する
直接的な機能はAnthropicにはありません。

代わりに、以下の方法でツール使用を実装します：

1. **カスタムツールの定義**
   ```python
   tools = [{
       "name": "get_weather",
       "description": "Get the current weather",
       "input_schema": {
           "type": "object",
           "properties": {
               "location": {"type": "string"}
           },
           "required": ["location"]
       }
   }]
   ```

2. **ツール使用の実行**
   ```python
   response = client.messages.create(
       model=model,
       messages=messages,
       tools=tools,
       tool_choice="auto"
   )
   ```

3. **構造化出力の解析**
   - Pydanticモデルを使用した出力検証
   - JSONスキーマによる構造化
            """, language="python")
        
        # 実装例サンプル表示
        with st.expander("📋 実装例コード", expanded=False):
            st.code("""
# ツール使用の実装例
from anthropic import Anthropic
from pydantic import BaseModel, Field

client = Anthropic()

# 天気取得ツールの定義
weather_tool = {
    "name": "get_weather",
    "description": "Get current weather for a location",
    "input_schema": {
        "type": "object",
        "properties": {
            "location": {
                "type": "string",
                "description": "City name"
            }
        },
        "required": ["location"]
    }
}

# ツール使用の実行
response = client.messages.create(
    model=model,
    messages=[
        {"role": "user", "content": "東京の今日の天気は？"}
    ],
    tools=[weather_tool],
    tool_choice="auto",
    max_tokens=1024
)

# 構造化データのためのPydanticモデル
class WeatherInfo(BaseModel):
    location: str = Field(..., description="場所")
    temperature: float = Field(..., description="気温")
    condition: str = Field(..., description="天候状態")

# レスポンスの解析と構造化
if response.stop_reason == "tool_use":
    for content in response.content:
        if content.type == "tool_use":
            # ツール呼び出しの処理
            tool_input = content.input
            # 実際のツール実行（API呼び出しなど）
            weather_data = get_weather(tool_input["location"])
            # 構造化データとして返す
            weather_info = WeatherInfo(**weather_data)
            """, language="python")
        
        # 入力エリア
        st.subheader("📤 入力")
        
        query = st.text_input(
            "質問",
            value="東京の明日の天気とイベント情報を教えて",
            key=f"query_{self.safe_key}"
        )
        
        if st.button("🔧 ツール実行", key=f"tool_submit_{self.safe_key}"):
            if query:
                self._execute_tool_demo(query)
        
        # 結果表示
        self._display_tool_results()
    
    def _execute_tool_demo(self, query: str):
        """ツールデモの実行"""
        try:
            # シンプルな情報取得ツールの定義
            info_tool = {
                "name": "get_info",
                "description": "Get general information about a topic",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "topic": {
                            "type": "string",
                            "description": "The topic to get information about"
                        }
                    },
                    "required": ["topic"]
                }
            }
            
            messages = [
                {"role": "user", "content": query}
            ]
            
            with st.spinner("ツール実行中..."):
                # tool_choiceを適切な形式に設定
                response = self.client.client.messages.create(
                    model=self.model,
                    messages=messages,
                    tools=[info_tool],
                    max_tokens=1024
                )
            
            st.session_state[f"tool_response_{self.safe_key}"] = response
            st.success(f"✅ ツール実行完了")
            st.rerun()
            
        except Exception as e:
            st.error(f"ツール実行エラー: {e}")
            if config.get("experimental.debug_mode", False):
                st.exception(e)
    
    def _display_tool_results(self):
        """ツール結果の表示"""
        if f"tool_response_{self.safe_key}" in st.session_state:
            response = st.session_state[f"tool_response_{self.safe_key}"]
            st.subheader("🤖 ツール実行結果")
            ResponseProcessorUI.display_response(response)
            
            # ツール使用の詳細を表示
            if response.stop_reason == "tool_use":
                st.subheader("🔧 ツール使用詳細")
                for content in response.content:
                    if hasattr(content, 'type') and content.type == "tool_use":
                        st.json({
                            "tool_name": content.name,
                            "tool_input": content.input
                        })


class FunctionCallingDemo(BaseDemo):
    """Function Callingデモ"""

    def run_demo(self):
        """Function Callingデモの実行"""
        st.write("## 実装例: Function Calling (天気API)")
        st.write("Function Callingを使用して外部APIと統合する方法を示します。")
        
        # Anthropic APIのメモ
        with st.expander("📝 Anthropic API メモ", expanded=False):
            st.code("""
# Anthropic APIでのFunction Callingについて

Anthropic APIでは、OpenAIのFunction Callingと同様の機能を
ツール使用機能として実装します。

主な違い：
1. "functions" ではなく "tools" を使用
2. "function_call" ではなく "tool_choice" を使用
3. レスポンスは tool_use タイプのコンテンツとして返される

実装パターン：
```python
tools = [{
    "name": "get_weather",
    "description": "Get weather information",
    "input_schema": {
        "type": "object",
        "properties": {
            "latitude": {"type": "number"},
            "longitude": {"type": "number"}
        },
        "required": ["latitude", "longitude"]
    }
}]

response = client.messages.create(
    model=model,
    messages=messages,
    tools=tools,
    tool_choice="auto"
)
```
            """, language="python")
        
        # 実装例サンプル表示
        with st.expander("📋 実装例コード", expanded=False):
            st.code("""
# Function Callingの実装例
from anthropic import Anthropic
from pydantic import BaseModel, Field
import requests

client = Anthropic()

# パラメータスキーマの定義
class WeatherParams(BaseModel):
    latitude: float = Field(..., description="緯度（10進）")
    longitude: float = Field(..., description="経度（10進）")

# 天気取得関数
def get_weather(latitude: float, longitude: float) -> dict:
    url = f"https://api.open-meteo.com/v1/forecast?latitude={latitude}&longitude={longitude}&current=temperature_2m"
    response = requests.get(url)
    return response.json()

# ツール定義（Anthropic形式）
weather_tool = {
    "name": "get_weather",
    "description": "現在の天気情報を取得",
    "input_schema": WeatherParams.model_json_schema()
}

# Function Calling実行
response = client.messages.create(
    model=model,
    messages=[
        {"role": "user", "content": "東京の今日の天気は？"}
    ],
    tools=[weather_tool],
    tool_choice="auto",
    max_tokens=1024
)

# ツール呼び出しの処理
if response.stop_reason == "tool_use":
    for content in response.content:
        if content.type == "tool_use" and content.name == "get_weather":
            # 実際の天気データ取得
            weather_data = get_weather(**content.input)
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
            
            # ツール定義（Anthropic形式）
            weather_tool = {
                "name": "get_weather",
                "description": get_weather.__doc__,
                "input_schema": schema
            }
            
            messages = [
                {"role": "user", "content": query}
            ]
            
            with st.spinner("Function Calling 実行中..."):
                response = self.client.client.messages.create(
                    model=self.model,
                    messages=messages,
                    tools=[weather_tool],
                    max_tokens=1024
                )
            
            # 実際の天気データを取得
            coords = cities[selected_city]
            weather_data = get_weather(coords["lat"], coords["lon"])
            
            # セッション状態に保存
            st.session_state[f"function_response_{self.safe_key}"] = response
            st.session_state[f"weather_data_{self.safe_key}"] = weather_data
            st.session_state[f"selected_city_{self.safe_key}"] = selected_city
            
            st.success(f"✅ Function Calling完了")
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
            
            # ツール使用の詳細
            if response.stop_reason == "tool_use":
                st.subheader("🔧 ツール呼び出し詳細")
                for content in response.content:
                    if hasattr(content, 'type') and content.type == "tool_use":
                        st.json({
                            "tool_name": content.name,
                            "tool_input": content.input
                        })
            
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
            "ツール使用と構造化出力": ToolUseDemo,
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
            "[a05_conversation_state.py] デモを選択",
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

# streamlit run a05_conversation_state.py --server.port=8505