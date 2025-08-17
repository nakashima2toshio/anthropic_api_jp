# streamlit run a10_03_images_and_vision.py --server.port=8503
# --------------------------------------------------
# OpenAI 画像＆ビジョンAPI デモアプリケーション（統一化版）
# Streamlitを使用したインタラクティブなAPIテストツール
# 統一化版: a10_00_responses_api.pyの構成・構造・ライブラリ・エラー処理の完全統一
# --------------------------------------------------
import os
import sys
import json
import base64
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
            page_title=config.get("ui.page_title", "OpenAI 画像＆ビジョンAPI デモ"),
            page_icon=config.get("ui.page_icon", "🖼️"),
            layout=config.get("ui.layout", "wide"),
            initial_sidebar_state="expanded"
        )
    except st.errors.StreamlitAPIException:
        # 既に設定済みの場合は無視
        pass


# ページ設定の実行
setup_page_config()

# サンプル画像 URL（config.ymlから取得）
image_url_default = config.get(
    "samples.images.nature",
    "https://upload.wikimedia.org/wikipedia/commons/thumb/d/dd/"
    "Gfp-wisconsin-madison-the-nature-boardwalk.jpg/2560px-"
    "Gfp-wisconsin-madison-the-nature-boardwalk.jpg"
)


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
# 画像＆ビジョンデモクラス（統一化版）
# ==================================================
class URLImageToTextDemo(BaseDemo):
    """URL画像からテキスト生成デモ"""

    def run_demo(self):
        """URL画像からテキスト生成デモの実行"""
        st.write("## 実装例: 画像URL解析")
        st.write("画像URLを入力して、その画像を解析します。")
        
        # 実装例サンプル表示
        with st.expander("📋 実装例コード", expanded=False):
            st.code("""
# 画像URLからテキスト生成の実装例
from openai import OpenAI
from openai.types.responses import EasyInputMessageParam, ResponseInputTextParam, ResponseInputImageParam

client = OpenAI()
messages = [
    EasyInputMessageParam(
        role="user",
        content=[
            ResponseInputTextParam(type="input_text", text="この画像を日本語で説明してください"),
            ResponseInputImageParam(type="input_image", image_url=image_url, detail="auto")
        ]
    )
]

response = client.responses.create(model=model, input=messages)
            """, language="python")
        
        # 入力エリア
        st.subheader("📤 入力")
        
        # 画像URL入力
        image_url = st.text_input(
            "画像URLを入力してください:",
            value=image_url_default,
            key=f"image_url_{self.safe_key}"
        )
        
        # 画像の表示
        if image_url:
            try:
                st.image(image_url, caption="入力画像", use_container_width=True)
            except Exception as e:
                st.error(f"画像の表示に失敗しました: {e}")
        
        # 質問入力
        with st.form(key=f"url_form_{self.safe_key}"):
            user_prompt = st.text_area(
                "質問を入力してください:",
                value="この画像を日本語で詳しく説明してください。何が写っていますか？",
                height=config.get("ui.text_area_height", 75),
                key=f"user_input_{self.safe_key}"
            )
            submit_button = st.form_submit_button(label="🚀 送信")
        
        if submit_button and user_prompt and image_url:
            self._process_image_with_text(user_prompt, image_url)
    
    def _process_image_with_text(self, prompt: str, image_url: str):
        """画像とテキストの処理"""
        try:
            # デフォルトメッセージを取得
            messages = get_default_messages()
            
            # ユーザーメッセージを追加
            messages.append(
                EasyInputMessageParam(
                    role="user",
                    content=[
                        ResponseInputTextParam(type="input_text", text=prompt),
                        ResponseInputImageParam(
                            type="input_image",
                            image_url=image_url,
                            detail="auto"
                        )
                    ]
                )
            )
            
            with st.spinner("処理中..."):
                response = self.client.responses.create(
                    model=self.model,
                    input=messages,
                )
            
            st.success("応答を取得しました")
            st.subheader("🤖 回答")
            ResponseProcessorUI.display_response(response)
            
        except Exception as e:
            st.error(f"エラーが発生しました: {e}")
            if config.get("experimental.debug_mode", False):
                st.exception(e)


class Base64ImageToTextDemo(BaseDemo):
    """Base64画像からテキスト生成デモ"""

    def run_demo(self):
        """Base64画像からテキスト生成デモの実行"""
        st.write("## 実装例: ローカル画像解析（Base64）")
        st.write("ローカルの画像ファイルを選択して解析します。")
        
        # 実装例サンプル表示
        with st.expander("📋 実装例コード", expanded=False):
            st.code("""
# Base64画像からテキスト生成の実装例
import base64
from openai import OpenAI
from openai.types.responses import EasyInputMessageParam, ResponseInputTextParam, ResponseInputImageParam

# 画像をBase64エンコード
with open(image_path, "rb") as image_file:
    image_base64 = base64.b64encode(image_file.read()).decode('utf-8')

client = OpenAI()
messages = [
    EasyInputMessageParam(
        role="user",
        content=[
            ResponseInputTextParam(type="input_text", text=prompt),
            ResponseInputImageParam(
                type="input_image",
                image_url=f"data:image/png;base64,{image_base64}",
                detail="auto"
            )
        ]
    )
]

response = client.responses.create(model=model, input=messages)
            """, language="python")
        
        # 入力エリア
        st.subheader("📤 入力")
        
        self._handle_image_selection()
    
    def _handle_image_selection(self):
        """画像選択の処理"""
        # 画像フォルダー内のファイル列挙
        image_folder = "images"
        
        # フォルダが存在しない場合は作成
        if not os.path.exists(image_folder):
            os.makedirs(image_folder)
            st.info(f"'{image_folder}'フォルダを作成しました。画像ファイルを配置してください。")
            return
        
        image_files = [
            f for f in os.listdir(image_folder)
            if f.lower().endswith(('png', 'jpg', 'jpeg', 'webp', 'gif'))
        ]
        
        if not image_files:
            st.warning("画像フォルダに画像ファイルがありません。")
            st.info("'images'フォルダに画像ファイル（PNG, JPG, JPEG, WEBP, GIF）を配置してください。")
            
            # ファイルアップロード機能を提供
            uploaded_file = st.file_uploader(
                "または、ここに画像をアップロード",
                type=['png', 'jpg', 'jpeg', 'webp', 'gif'],
                key=f"upload_{self.safe_key}"
            )
            
            if uploaded_file is not None:
                # アップロードされたファイルを保存
                file_path = os.path.join(image_folder, uploaded_file.name)
                with open(file_path, "wb") as f:
                    f.write(uploaded_file.getbuffer())
                st.success(f"画像を保存しました: {uploaded_file.name}")
                st.rerun()
            return
        
        # 画像選択
        selected_image_file = st.selectbox(
            "画像ファイルを選択してください",
            image_files,
            key=f"select_image_{self.safe_key}"
        )
        
        # 選択した画像を表示
        if selected_image_file:
            image_path = os.path.join(image_folder, selected_image_file)
            st.image(image_path, caption=f"選択画像: {selected_image_file}", width=400)
            
            # プロンプト入力（既定値付き）
            prompt_default = "画像に何が写っているか説明してください。何人いますか？日本語で答えてください。"
            user_prompt = st.text_area(
                "プロンプトを入力してください",
                value=prompt_default,
                height=config.get("ui.text_area_height", 75),
                key=f"prompt_{self.safe_key}"
            )
            
            # 解析ボタン
            if st.button("🚀 解析する", key=f"analyze_{self.safe_key}"):
                if selected_image_file:
                    self._process_base64_image(image_path, user_prompt)
    
    def _encode_image_to_base64(self, image_path: str) -> str:
        """画像をBase64エンコード"""
        try:
            with open(image_path, "rb") as image_file:
                return base64.b64encode(image_file.read()).decode('utf-8')
        except Exception as e:
            st.error(f"画像エンコードエラー: {e}")
            return ""
    
    def _process_base64_image(self, image_path: str, prompt: str):
        """Base64画像の処理"""
        try:
            # 画像をBase64エンコード
            image_base64 = self._encode_image_to_base64(image_path)
            
            if not image_base64:
                st.error("画像のエンコードに失敗しました")
                return
            
            # デフォルトメッセージを取得
            messages = get_default_messages()
            
            # Pydantic モデルを用いて入力メッセージを構築
            messages.append(
                EasyInputMessageParam(
                    role="user",
                    content=[
                        ResponseInputTextParam(type="input_text", text=prompt),
                        ResponseInputImageParam(
                            type="input_image",
                            image_url=f"data:image/png;base64,{image_base64}",
                            detail="auto"
                        ),
                    ],
                )
            )
            
            with st.spinner("処理中..."):
                response = self.client.responses.create(
                    model=self.model,
                    input=messages,
                )
            
            st.success("応答を取得しました")
            st.subheader("🤖 回答")
            ResponseProcessorUI.display_response(response)
            
        except Exception as e:
            st.error(f"エラーが発生しました: {e}")
            if config.get("experimental.debug_mode", False):
                st.exception(e)


class PromptToImageDemo(BaseDemo):
    """プロンプトから画像生成デモ"""

    def run_demo(self):
        """プロンプトから画像生成デモの実行"""
        st.write("## 実装例: DALL-E画像生成")
        st.write("テキストから画像を生成します（DALL-E 3使用）。")
        
        # 実装例サンプル表示
        with st.expander("📋 実装例コード", expanded=False):
            st.code("""
# DALL-E画像生成の実装例
from openai import OpenAI

client = OpenAI()
response = client.images.generate(
    model="dall-e-3",
    prompt="美しい日本庭園の風景、桜の花が咲いている、静かな池、石灯籠、写実的なスタイル",
    size="1024x1024",
    quality="standard",
    n=1
)

image_url = response.data[0].url
            """, language="python")
        
        # 入力エリア
        st.subheader("📤 入力")
        
        # 画像生成設定
        col1, col2, col3 = st.columns(3)
        with col1:
            model = st.selectbox(
                "モデル",
                ["dall-e-3", "dall-e-2"],
                key=f"dalle_model_{self.safe_key}"
            )
        with col2:
            size = st.selectbox(
                "サイズ",
                ["1024x1024", "1792x1024", "1024x1792"] if model == "dall-e-3" else ["256x256", "512x512", "1024x1024"],
                key=f"dalle_size_{self.safe_key}"
            )
        with col3:
            quality = st.selectbox(
                "品質",
                ["standard", "hd"] if model == "dall-e-3" else ["standard"],
                key=f"dalle_quality_{self.safe_key}"
            )
        
        # プロンプト入力
        prompt = st.text_area(
            "画像生成プロンプトを入力してください",
            value="美しい日本庭園の風景、桜の花が咲いている、静かな池、石灯籠、写実的なスタイル",
            height=100,
            key=f"dalle_prompt_{self.safe_key}"
        )
        
        # 生成ボタン
        if st.button("🚀 画像を生成", key=f"generate_{self.safe_key}"):
            if prompt:
                self._generate_image_from_prompt(model, prompt, size, quality)
    
    def _generate_image_from_prompt(self, model: str, prompt: str, size: str, quality: str):
        """DALL-Eで画像生成"""
        try:
            with st.spinner("画像を生成中...（数秒かかります）"):
                response = self.client.images.generate(
                    model=model,
                    prompt=prompt,
                    size=size,
                    quality=quality if model == "dall-e-3" else "standard",
                    n=1
                )
            
            # 生成された画像を表示
            image_url = response.data[0].url
            st.success("画像を生成しました")
            st.subheader("🤖 生成結果")
            st.image(image_url, caption="生成画像", use_container_width=True)
            
            # 画像URLを表示
            st.text_input("画像URL（ダウンロード用）", value=image_url, key="generated_url")
            
            # 詳細情報
            with st.expander("生成情報"):
                st.write(f"**モデル**: {model}")
                st.write(f"**サイズ**: {size}")
                st.write(f"**品質**: {quality}")
                st.write(f"**プロンプト**: {prompt}")
                if hasattr(response.data[0], 'revised_prompt'):
                    st.write(f"**修正されたプロンプト**: {response.data[0].revised_prompt}")
            
        except Exception as e:
            st.error(f"画像生成エラー: {e}")
            if config.get("experimental.debug_mode", False):
                st.exception(e)


# ==================================================
# デモ管理クラス（統一化版）
# ==================================================
class DemoManager:
    """デモ管理クラス（統一化版）"""
    
    def __init__(self):
        self.demos = {
            "URL画像 → テキスト生成": URLImageToTextDemo,
            "ローカル画像（Base64） → テキスト生成": Base64ImageToTextDemo,
            "プロンプト → 画像生成（DALL-E）": PromptToImageDemo,
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

# streamlit run a10_03_images_and_vision.py --server.port=8503