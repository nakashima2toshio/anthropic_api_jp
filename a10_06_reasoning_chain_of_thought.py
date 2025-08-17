# streamlit run a10_06_reasoning_chain_of_thought.py --server.port=8506
# --------------------------------------------------
# OpenAI Chain of Thought 推論パターンデモアプリケーション（統一化版）
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
            page_title=config.get("ui.page_title", "OpenAI Chain of Thought 推論パターンデモ"),
            page_icon=config.get("ui.page_icon", "🧠"),
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
# CoTパターン結果データモデル（統一化版）
# ==================================================
class StepByStepResult(BaseModel):
    """Step-by-Stepパターンの結果"""
    question: str = Field(..., description="質問")
    steps: List[str] = Field(..., description="解決ステップ")
    answer: str = Field(..., description="最終的な答え")
    confidence: Optional[float] = Field(None, description="信頼度")


class HypothesisTestResult(BaseModel):
    """Hypothesis-Testパターンの結果"""
    problem: str = Field(..., description="問題")
    hypothesis: str = Field(..., description="仮説")
    evidence: List[str] = Field(default_factory=list, description="証拠・実験")
    evaluation: str = Field(..., description="評価")
    conclusion: str = Field(..., description="結論")
    confidence_score: Optional[float] = Field(None, description="信頼度スコア")


class TreeOfThoughtResult(BaseModel):
    """Tree-of-Thoughtパターンの結果"""
    goal: str = Field(..., description="目標")
    exploration_paths: List[str] = Field(default_factory=list, description="探索パス")
    best_solution: str = Field(..., description="最適解")
    evaluation_score: Optional[float] = Field(None, description="評価スコア")


class ProsConsDecisionResult(BaseModel):
    """Pros-Cons-Decisionパターンの結果"""
    topic: str = Field(..., description="トピック")
    pros: List[str] = Field(default_factory=list, description="メリット")
    cons: List[str] = Field(default_factory=list, description="デメリット")
    decision: str = Field(..., description="決定")
    rationale: str = Field(..., description="根拠")
    confidence: Optional[float] = Field(None, description="決定への信頼度")


class PlanExecuteReflectResult(BaseModel):
    """Plan-Execute-Reflectパターンの結果"""
    objective: str = Field(..., description="目標")
    initial_plan: List[str] = Field(default_factory=list, description="初期計画")
    execution_results: List[str] = Field(default_factory=list, description="実行結果")
    reflections: List[str] = Field(default_factory=list, description="振り返り")
    improved_plan: List[str] = Field(default_factory=list, description="改善された計画")
    lessons_learned: List[str] = Field(default_factory=list, description="学んだ教訓")
    success_probability: Optional[float] = Field(None, description="成功確率")


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
# Chain of Thought デモクラス（統一化版）
# ==================================================
class StepByStepReasoningDemo(BaseDemo):
    """段階的推論（Step-by-Step）デモ"""

    def run_demo(self):
        """段階的推論デモの実行"""
        st.write("## 実装例: Step-by-Step 推論")
        st.write("問題を段階的に分解し、順序立てて解決する推論パターンを実装します。")
        
        # 実装例サンプル表示
        with st.expander("📋 実装例コード", expanded=False):
            st.code("""
# Step-by-Step 推論の実装例
from openai import OpenAI
from openai.types.responses import EasyInputMessageParam, ResponseInputTextParam

client = OpenAI()

system_prompt = '''あなたは段階的に問題を解く methodical なチューターです。
質問が与えられたら：
1. 問題を明確で順序立ったステップに分解してください
2. 各ステップに番号を付けてください（Step 1:, Step 2: など）
3. 作業を明確に示してください
4. 最後に "Answer:" に続けて最終的な答えを記載してください
5. 解答の信頼度を0-1で評価してください

推論において正確で論理的にしてください。'''

messages = [
    EasyInputMessageParam(role="system", content=system_prompt),
    EasyInputMessageParam(
        role="user",
        content=[
            ResponseInputTextParam(
                type="input_text", 
                text="2X + 1 = 5のとき、Xはいくつ？"
            )
        ]
    )
]

response = client.responses.create(model=model, input=messages)
            """, language="python")
        
        # 入力エリア
        st.subheader("📤 入力")
        
        question = st.text_area(
            "質問を入力してください",
            value="2X + 1 = 5のとき、Xはいくつ？",
            height=config.get("ui.text_area_height", 75),
            key=f"question_{self.safe_key}"
        )
        
        if st.button("🚀 段階的推論を実行", key=f"submit_{self.safe_key}"):
            if question:
                self._process_step_by_step_reasoning(question)
        
        # 結果表示
        self._display_reasoning_results()
    
    def _process_step_by_step_reasoning(self, question: str):
        """段階的推論の処理"""
        try:
            system_prompt = """あなたは段階的に問題を解く methodical なチューターです。
質問が与えられたら：
1. 問題を明確で順序立ったステップに分解してください
2. 各ステップに番号を付けてください（Step 1:, Step 2: など）
3. 作業を明確に示してください
4. 最後に "Answer:" に続けて最終的な答えを記載してください
5. 解答の信頼度を0-1で評価してください

推論において正確で論理的にしてください。"""
            
            messages = [
                EasyInputMessageParam(role="system", content=system_prompt),
                EasyInputMessageParam(
                    role="user",
                    content=[
                        ResponseInputTextParam(
                            type="input_text",
                            text=question
                        )
                    ]
                )
            ]
            
            with st.spinner("段階的推論中..."):
                response = self.client.responses.create(
                    model=self.model,
                    input=messages
                )
            
            # セッション状態に保存
            st.session_state[f"reasoning_response_{self.safe_key}"] = response
            st.success("✅ 段階的推論完了")
            st.rerun()
            
        except Exception as e:
            st.error(f"エラーが発生しました: {e}")
            if config.get("experimental.debug_mode", False):
                st.exception(e)
    
    def _display_reasoning_results(self):
        """推論結果の表示"""
        if f"reasoning_response_{self.safe_key}" in st.session_state:
            response = st.session_state[f"reasoning_response_{self.safe_key}"]
            st.subheader("🤖 段階的推論結果")
            ResponseProcessorUI.display_response(response)


class HypothesisTestDemo(BaseDemo):
    """仮説検証推論デモ"""

    def run_demo(self):
        """仮説検証推論デモの実行"""
        st.write("## 実装例: 仮説検証推論")
        st.write("仮説を立てて証拠で検証する推論パターンを実装します。")
        
        # 実装例サンプル表示
        with st.expander("📋 実装例コード", expanded=False):
            st.code("""
# 仮説検証推論の実装例
from openai import OpenAI
from openai.types.responses import EasyInputMessageParam, ResponseInputTextParam

client = OpenAI()

system_prompt = '''あなたは仮説検証方法論に従う上級エンジニアです。
問題と仮説が与えられたら：
1. 証拠として少なくとも3つの具体的なテストまたは測定を生成
2. 証拠が仮説を支持するか反証するかを評価
3. 仮説を受け入れるか拒否するかの明確な結論を提供
4. 結論への信頼度を評価（0-1）

以下の明確なセクションで構造化された出力を返してください：
- Evidence（テスト/測定の番号付きリスト）
- Evaluation（証拠の分析）
- Conclusion（理由付きで受諾/拒否）
- Confidence Score（0-1）'''

messages = [
    EasyInputMessageParam(role="system", content=system_prompt),
    EasyInputMessageParam(
        role="user",
        content=[
            ResponseInputTextParam(
                type="input_text", 
                text="Problem: Webアプリの初回表示が3秒以上かかる\\nHypothesis: 画像ファイルのサイズが大きすぎて読み込み時間を圧迫している"
            )
        ]
    )
]

response = client.responses.create(model=model, input=messages)
            """, language="python")
        
        # 入力エリア
        st.subheader("📤 入力")
        
        problem = st.text_area(
            "問題（バグ・実験目的）",
            value="Webアプリの初回表示が3秒以上かかる",
            height=config.get("ui.text_area_height", 75),
            key=f"problem_{self.safe_key}"
        )
        
        hypothesis = st.text_input(
            "仮説（原因・改善案）",
            value="画像ファイルのサイズが大きすぎて読み込み時間を圧迫している",
            key=f"hypothesis_{self.safe_key}"
        )
        
        if st.button("🧪 仮説検証を実行", key=f"submit_{self.safe_key}"):
            if problem and hypothesis:
                self._process_hypothesis_test(problem, hypothesis)
        
        # 結果表示
        self._display_hypothesis_results()
    
    def _process_hypothesis_test(self, problem: str, hypothesis: str):
        """仮説検証の処理"""
        try:
            system_prompt = """あなたは仮説検証方法論に従う上級エンジニアです。
問題と仮説が与えられたら：
1. 証拠として少なくとも3つの具体的なテストまたは測定を生成
2. 証拠が仮説を支持するか反証するかを評価
3. 仮説を受け入れるか拒否するかの明確な結論を提供
4. 結論への信頼度を評価（0-1）

以下の明確なセクションで構造化された出力を返してください：
- Evidence（テスト/測定の番号付きリスト）
- Evaluation（証拠の分析）
- Conclusion（理由付きで受諾/拒否）
- Confidence Score（0-1）

アプローチにおいて体系的で科学的にしてください。"""
            
            user_content = f"Problem: {problem}\nHypothesis: {hypothesis}"
            
            messages = [
                EasyInputMessageParam(role="system", content=system_prompt),
                EasyInputMessageParam(
                    role="user",
                    content=[
                        ResponseInputTextParam(
                            type="input_text",
                            text=user_content
                        )
                    ]
                )
            ]
            
            with st.spinner("仮説検証中..."):
                response = self.client.responses.create(
                    model=self.model,
                    input=messages
                )
            
            # セッション状態に保存
            st.session_state[f"hypothesis_response_{self.safe_key}"] = response
            st.success("✅ 仮説検証完了")
            st.rerun()
            
        except Exception as e:
            st.error(f"エラーが発生しました: {e}")
            if config.get("experimental.debug_mode", False):
                st.exception(e)
    
    def _display_hypothesis_results(self):
        """仮説検証結果の表示"""
        if f"hypothesis_response_{self.safe_key}" in st.session_state:
            response = st.session_state[f"hypothesis_response_{self.safe_key}"]
            st.subheader("🤖 仮説検証結果")
            ResponseProcessorUI.display_response(response)


class TreeOfThoughtDemo(BaseDemo):
    """思考の木（Tree of Thought）デモ"""

    def run_demo(self):
        """思考の木デモの実行"""
        st.write("## 実装例: Tree of Thought 推論")
        st.write("複数の思考経路を探索して最適解を発見する推論パターンを実装します。")
        
        # 実装例サンプル表示
        with st.expander("📋 実装例コード", expanded=False):
            st.code("""
# Tree of Thought 推論の実装例
from openai import OpenAI
from openai.types.responses import EasyInputMessageParam, ResponseInputTextParam

client = OpenAI()

system_prompt = '''あなたはTree-of-Thoughts探索を実行するAIです。
体系的な分岐推論で問題を解決します。

各問題に対して：
1. 各ステップで複数の候補思考を生成（分岐）
2. 各分岐を0-1のスコアで評価
3. 有望な分岐をさらなる探索のために選択
4. 探索ツリー構造を追跡
5. 解決への最適パスを特定

以下を含む構造化された出力を返してください：
- 複数の分岐とその評価スコア
- 分岐間の関係性
- 最適パスの特定
- 最終的な解決策

単なる線形思考ではなく、体系的な探索を使用してください。'''

messages = [
    EasyInputMessageParam(role="system", content=system_prompt),
    EasyInputMessageParam(
        role="user",
        content=[
            ResponseInputTextParam(
                type="input_text", 
                text="Goal: 4, 9, 10, 13 の数字を使って24を作る（四則演算のみ使用）"
            )
        ]
    )
]

response = client.responses.create(model=model, input=messages)
            """, language="python")
        
        # 入力エリア
        st.subheader("📤 入力")
        
        goal = st.text_area(
            "目標（達成したいタスク）",
            value="4, 9, 10, 13 の数字を使って24を作る（四則演算のみ使用）",
            height=config.get("ui.text_area_height", 75),
            key=f"goal_{self.safe_key}"
        )
        
        if st.button("🌳 Tree of Thought を実行", key=f"submit_{self.safe_key}"):
            if goal:
                self._process_tree_of_thought(goal)
        
        # 結果表示
        self._display_tree_results()
    
    def _process_tree_of_thought(self, goal: str):
        """Tree of Thought の処理"""
        try:
            system_prompt = """あなたはTree-of-Thoughts探索を実行するAIです。
体系的な分岐推論で問題を解決します。

各問題に対して：
1. 各ステップで複数の候補思考を生成（分岐）
2. 各分岐を0-1のスコアで評価
3. 有望な分岐をさらなる探索のために選択
4. 探索ツリー構造を追跡
5. 解決への最適パスを特定

以下を含む構造化された出力を返してください：
- 複数の分岐とその評価スコア
- 分岐間の関係性
- 最適パスの特定
- 最終的な解決策

単なる線形思考ではなく、体系的な探索を使用してください。"""
            
            user_content = f"Goal: {goal}"
            
            messages = [
                EasyInputMessageParam(role="system", content=system_prompt),
                EasyInputMessageParam(
                    role="user",
                    content=[
                        ResponseInputTextParam(
                            type="input_text",
                            text=user_content
                        )
                    ]
                )
            ]
            
            with st.spinner("Tree of Thought 探索中..."):
                response = self.client.responses.create(
                    model=self.model,
                    input=messages
                )
            
            # セッション状態に保存
            st.session_state[f"tree_response_{self.safe_key}"] = response
            st.success("✅ Tree of Thought 探索完了")
            st.rerun()
            
        except Exception as e:
            st.error(f"エラーが発生しました: {e}")
            if config.get("experimental.debug_mode", False):
                st.exception(e)
    
    def _display_tree_results(self):
        """Tree of Thought 結果の表示"""
        if f"tree_response_{self.safe_key}" in st.session_state:
            response = st.session_state[f"tree_response_{self.safe_key}"]
            st.subheader("🤖 Tree of Thought 結果")
            ResponseProcessorUI.display_response(response)


class ProsConsDecisionDemo(BaseDemo):
    """賛否比較決定（Pros-Cons-Decision）デモ"""

    def run_demo(self):
        """賛否比較決定デモの実行"""
        st.write("## 実装例: Pros-Cons-Decision 推論")
        st.write("メリット・デメリットを比較して合理的に決定する推論パターンを実装します。")
        
        # 実装例サンプル表示
        with st.expander("📋 実装例コード", expanded=False):
            st.code("""
# Pros-Cons-Decision 推論の実装例
from openai import OpenAI
from openai.types.responses import EasyInputMessageParam, ResponseInputTextParam

client = OpenAI()

system_prompt = '''あなたはバランスの取れた意思決定支援アシスタントです。
メリットとデメリットを体系的にリストアップしてトピックを分析し、理性的な決定を下します。

プロセス：
1. 少なくとも3つの具体的な利点（メリット）をリスト
2. 少なくとも3つの具体的な欠点（デメリット）をリスト
3. 各ポイントの重要度を重み付け
4. 明確な推奨を行う
5. 決定の詳細な根拠を提供
6. 決定への信頼度を評価（0-1）

明確なセクションでレスポンスを構造化してください：
- Pros:（番号付きリスト）
- Cons:（番号付きリスト）
- Decision:（明確な推奨）
- Rationale:（詳細な推論）
- Confidence:（0-1スコア）'''

messages = [
    EasyInputMessageParam(role="system", content=system_prompt),
    EasyInputMessageParam(
        role="user",
        content=[
            ResponseInputTextParam(
                type="input_text", 
                text="Topic: リモートワークとオフィス出社、どちらを選ぶべきか？\\nPerspective: 一般的"
            )
        ]
    )
]

response = client.responses.create(model=model, input=messages)
            """, language="python")
        
        # 入力エリア
        st.subheader("📤 入力")
        
        topic = st.text_area(
            "意思決定したいトピック",
            value="リモートワークとオフィス出社、どちらを選ぶべきか？",
            height=config.get("ui.text_area_height", 75),
            key=f"topic_{self.safe_key}"
        )
        
        perspective = st.selectbox(
            "視点",
            ["一般的", "経営者", "従業員", "技術者"],
            help="どの立場から判断するか",
            key=f"perspective_{self.safe_key}"
        )
        
        if st.button("⚖️ 賛否比較決定を実行", key=f"submit_{self.safe_key}"):
            if topic:
                self._process_pros_cons_decision(topic, perspective)
        
        # 結果表示
        self._display_decision_results()
    
    def _process_pros_cons_decision(self, topic: str, perspective: str):
        """賛否比較決定の処理"""
        try:
            system_prompt = """あなたはバランスの取れた意思決定支援アシスタントです。
メリットとデメリットを体系的にリストアップしてトピックを分析し、理性的な決定を下します。

プロセス：
1. 少なくとも3つの具体的な利点（メリット）をリスト
2. 少なくとも3つの具体的な欠点（デメリット）をリスト
3. 各ポイントの重要度を重み付け
4. 明確な推奨を行う
5. 決定の詳細な根拠を提供
6. 決定への信頼度を評価（0-1）

明確なセクションでレスポンスを構造化してください：
- Pros:（番号付きリスト）
- Cons:（番号付きリスト）
- Decision:（明確な推奨）
- Rationale:（詳細な推論）
- Confidence:（0-1スコア）

客観的で、複数の視点を考慮し、証拠に基づいて決定してください。"""
            
            user_content = f"Topic: {topic}\nPerspective: {perspective}"
            
            messages = [
                EasyInputMessageParam(role="system", content=system_prompt),
                EasyInputMessageParam(
                    role="user",
                    content=[
                        ResponseInputTextParam(
                            type="input_text",
                            text=user_content
                        )
                    ]
                )
            ]
            
            with st.spinner("賛否比較決定中..."):
                response = self.client.responses.create(
                    model=self.model,
                    input=messages
                )
            
            # セッション状態に保存
            st.session_state[f"decision_response_{self.safe_key}"] = response
            st.success("✅ 賛否比較決定完了")
            st.rerun()
            
        except Exception as e:
            st.error(f"エラーが発生しました: {e}")
            if config.get("experimental.debug_mode", False):
                st.exception(e)
    
    def _display_decision_results(self):
        """決定結果の表示"""
        if f"decision_response_{self.safe_key}" in st.session_state:
            response = st.session_state[f"decision_response_{self.safe_key}"]
            st.subheader("🤖 賛否比較決定結果")
            ResponseProcessorUI.display_response(response)


class PlanExecuteReflectDemo(BaseDemo):
    """計画実行振り返り（Plan-Execute-Reflect）デモ"""

    def run_demo(self):
        """計画実行振り返りデモの実行"""
        st.write("## 実装例: Plan-Execute-Reflect 推論")
        st.write("計画・実行・振り返りのループで継続改善する推論パターンを実装します。")
        
        # 実装例サンプル表示
        with st.expander("📋 実装例コード", expanded=False):
            st.code("""
# Plan-Execute-Reflect 推論の実装例
from openai import OpenAI
from openai.types.responses import EasyInputMessageParam, ResponseInputTextParam

client = OpenAI()

system_prompt = '''あなたはPlan-Execute-Reflect改善ループを実装するAIです。

プロセス：
1. PLAN: 目標のための3-5個の具体的で実行可能なステップを作成
2. EXECUTE: 実行をシミュレートし、現実的な結果/課題を文書化
3. REFLECT: 何がうまくいき、何がうまくいかず、なぜかを分析
4. IMPROVE: 振り返りに基づいて改善された計画を作成
5. LEARN: 将来の応用のための重要な教訓を抽出

明確なセクションでレスポンスを構造化してください：
- Initial Plan:（番号付きの実行可能ステップ）
- Execution Results:（結果の現実的なシミュレーション）
- Reflections:（成功と失敗の分析）
- Improved Plan:（学習に基づく修正されたステップ）
- Lessons Learned:（将来のための重要な洞察）
- Success Probability:（改善された計画の0-1推定）

課題について現実的で、改善について具体的にしてください。'''

messages = [
    EasyInputMessageParam(role="system", content=system_prompt),
    EasyInputMessageParam(
        role="user",
        content=[
            ResponseInputTextParam(
                type="input_text", 
                text="Objective: 3週間以内にプログラミングスキルを向上させてWebアプリを完成させる\\nComplexity Level: 標準"
            )
        ]
    )
]

response = client.responses.create(model=model, input=messages)
            """, language="python")
        
        # 入力エリア
        st.subheader("📤 入力")
        
        objective = st.text_area(
            "目標（達成したいこと）",
            value="3週間以内にプログラミングスキルを向上させてWebアプリを完成させる",
            height=config.get("ui.text_area_height", 75),
            key=f"objective_{self.safe_key}"
        )
        
        complexity = st.selectbox(
            "複雑さ",
            ["シンプル", "標準", "複雑"],
            index=1,
            help="目標の複雑さレベル",
            key=f"complexity_{self.safe_key}"
        )
        
        if st.button("🔄 Plan-Execute-Reflect を実行", key=f"submit_{self.safe_key}"):
            if objective:
                self._process_plan_execute_reflect(objective, complexity)
        
        # 結果表示
        self._display_reflect_results()
    
    def _process_plan_execute_reflect(self, objective: str, complexity: str):
        """Plan-Execute-Reflect の処理"""
        try:
            system_prompt = """あなたはPlan-Execute-Reflect改善ループを実装するAIです。

プロセス：
1. PLAN: 目標のための3-5個の具体的で実行可能なステップを作成
2. EXECUTE: 実行をシミュレートし、現実的な結果/課題を文書化
3. REFLECT: 何がうまくいき、何がうまくいかず、なぜかを分析
4. IMPROVE: 振り返りに基づいて改善された計画を作成
5. LEARN: 将来の応用のための重要な教訓を抽出

明確なセクションでレスポンスを構造化してください：
- Initial Plan:（番号付きの実行可能ステップ）
- Execution Results:（結果の現実的なシミュレーション）
- Reflections:（成功と失敗の分析）
- Improved Plan:（学習に基づく修正されたステップ）
- Lessons Learned:（将来のための重要な洞察）
- Success Probability:（改善された計画の0-1推定）

課題について現実的で、改善について具体的にしてください。"""
            
            user_content = f"Objective: {objective}\nComplexity Level: {complexity}"
            
            messages = [
                EasyInputMessageParam(role="system", content=system_prompt),
                EasyInputMessageParam(
                    role="user",
                    content=[
                        ResponseInputTextParam(
                            type="input_text",
                            text=user_content
                        )
                    ]
                )
            ]
            
            with st.spinner("Plan-Execute-Reflect 実行中..."):
                response = self.client.responses.create(
                    model=self.model,
                    input=messages
                )
            
            # セッション状態に保存
            st.session_state[f"reflect_response_{self.safe_key}"] = response
            st.success("✅ Plan-Execute-Reflect 完了")
            st.rerun()
            
        except Exception as e:
            st.error(f"エラーが発生しました: {e}")
            if config.get("experimental.debug_mode", False):
                st.exception(e)
    
    def _display_reflect_results(self):
        """振り返り結果の表示"""
        if f"reflect_response_{self.safe_key}" in st.session_state:
            response = st.session_state[f"reflect_response_{self.safe_key}"]
            st.subheader("🤖 Plan-Execute-Reflect 結果")
            ResponseProcessorUI.display_response(response)


# ==================================================
# デモ管理クラス（統一化版）
# ==================================================
class DemoManager:
    """デモ管理クラス（統一化版）"""
    
    def __init__(self):
        self.demos = {
            "段階的推論（Step-by-Step）": StepByStepReasoningDemo,
            "仮説検証推論（Hypothesis-Test）": HypothesisTestDemo,
            "思考の木（Tree of Thought）": TreeOfThoughtDemo,
            "賛否比較決定（Pros-Cons-Decision）": ProsConsDecisionDemo,
            "計画実行振り返り（Plan-Execute-Reflect）": PlanExecuteReflectDemo,
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

# streamlit run a10_06_reasoning_chain_of_thought.py --server.port=8506