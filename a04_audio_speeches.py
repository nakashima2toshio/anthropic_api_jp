# streamlit run a04_audio_speeches.py --server.port=8504
# --------------------------------------------------
# OpenAI Audio & Speech API デモアプリケーション（統一化改修版）
# Streamlitを使用したインタラクティブな音声APIテストツール
# 統一化改修版: a10_00_responses_api.pyの構成・構造・ライブラリ・エラー処理の完全統一
# --------------------------------------------------
import os
import sys
import asyncio
import base64
import time
import random
from io import BytesIO
from pathlib import Path
from abc import ABC, abstractmethod
from typing import Optional, List, Dict, Any, Union
import logging
import textwrap

import streamlit as st

# プロジェクトディレクトリの設定
BASE_DIR = Path(__file__).resolve().parent.parent
THIS_DIR = Path(__file__).resolve().parent

# PYTHONPATHに親ディレクトリを追加
sys.path.insert(0, str(BASE_DIR))

# ヘルパーモジュールをインポート（統一化）
try:
    from helper_st import (
        UIHelper as BaseUIHelper,
        MessageManagerUI, ResponseProcessorUI,
        SessionStateManager, error_handler_ui, timer_ui,
        InfoPanelManager as BaseInfoPanelManager,
        safe_streamlit_json,
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

from openai import OpenAI, AsyncOpenAI
from openai.types.chat import (
    ChatCompletionSystemMessageParam,
    ChatCompletionUserMessageParam,
    ChatCompletionMessageParam,
)

# ページ設定
def setup_page_config():
    """ページ設定（重複実行エラー回避）"""
    try:
        st.set_page_config(
            page_title=config.get("ui.page_title", "OpenAI Audio & Speech API Demo"),
            page_icon=config.get("ui.page_icon", "🎵"),
            layout=config.get("ui.layout", "wide"),
            initial_sidebar_state="expanded"
        )
    except st.errors.StreamlitAPIException:
        pass

setup_page_config()

# データディレクトリの設定
DATA_DIR = Path(config.get("paths.data", "data"))
DATA_DIR.mkdir(exist_ok=True)

# ==================================================
# 共通UI関数（統一化版）
# ==================================================
def setup_common_ui(demo_name: str) -> str:
    """共通UI設定（統一化版）"""
    safe_key = sanitize_key(demo_name)
    st.write(f"# {demo_name}")

    # モデル選択（音声用モデル選択）
    model = UIHelper.select_audio_model(f"model_{safe_key}")
    st.write("選択したモデル:", model)
    return model

def setup_sidebar_panels(selected_model: str):
    """サイドバーパネルの統一設定（音声API用）"""
    st.sidebar.markdown("### 🎵 Audio API 情報")  # ← expanded=False を削除
    InfoPanelManager.show_audio_model_info(selected_model)
    InfoPanelManager.show_session_info()
    InfoPanelManager.show_performance_info()
    InfoPanelManager.show_audio_cost_info(selected_model)
    InfoPanelManager.show_debug_panel()
    InfoPanelManager.show_settings()

# ==================================================
# UIHelper拡張（音声用）
# ==================================================
class UIHelper(BaseUIHelper):
    """UIHelper拡張（音声API用）"""

    @staticmethod
    def select_audio_model(key: str = "audio_model_selection") -> str:
        """音声API用モデル選択"""
        audio_models = config.get("models.categories.audio", [
            "tts-1", "tts-1-hd", "gpt-4o-mini-tts",
            "whisper-1", "gpt-4o-transcribe"
        ])
        default_model = config.get("models.audio_default", "tts-1")
        default_index = audio_models.index(default_model) if default_model in audio_models else 0

        selected = st.sidebar.selectbox(
            "音声モデルを選択",
            audio_models,
            index=default_index,
            key=key,
            help="利用するOpenAI音声モデルを選択してください",
        )
        SessionStateManager.set_user_preference("selected_audio_model", selected)
        return selected

    @staticmethod
    def select_voice(key: str = "voice_selection") -> str:
        """音声選択UI"""
        voices = config.get("audio.voices", ["alloy", "nova", "echo", "onyx", "shimmer"])
        return st.selectbox(
            "Voice",
            voices,
            index=0,
            key=key,
            help="音声の種類を選択してください"
        )

    @staticmethod
    def create_audio_download_button(audio_data: bytes, filename: str, label: str = "📥 音声ダウンロード"):
        """音声ダウンロードボタンの作成"""
        try:
            st.download_button(
                label=label,
                data=audio_data,
                file_name=filename,
                mime="audio/mp3",
                help=f"{filename}をダウンロードします"
            )
        except Exception as e:
            st.error(f"音声ダウンロードボタン作成エラー: {e}")
            logger.error(f"Audio download button error: {e}")

# ==================================================
# InfoPanelManager拡張（音声用）
# ==================================================
class InfoPanelManager(BaseInfoPanelManager):
    """InfoPanelManager拡張（音声API用）"""

    @staticmethod
    def show_audio_model_info(selected_model: str):
        with st.sidebar.expander("🎵 音声モデル情報", expanded=False):
            if selected_model.startswith("tts-") or selected_model.startswith("gpt-4o-mini-tts"):
                st.info("🎤 Text-to-Speech モデル")
                model_info = {
                    "tts-1": "速度最適化モデル",
                    "tts-1-hd": "高品質モデル",
                    "gpt-4o-mini-tts": "GPT-4o搭載TTS"
                }
                st.write(f"**特徴**: {model_info.get(selected_model, '不明')}")
                st.write("**出力**: MP3")
                st.write("**最大文字数**: 4,096文字")
            else:
                st.info("🎧 Speech-to-Text モデル")
                model_info = {
                    "whisper-1": "標準音声認識",
                    "gpt-4o-transcribe": "高精度音声認識"
                }
                st.write(f"**特徴**: {model_info.get(selected_model, '不明')}")
                st.write("**入力**: MP3, WAV, M4A")
                st.write("**最大ファイルサイズ**: 25MB")

    @staticmethod
    def show_audio_cost_info(selected_model: str):
        with st.sidebar.expander("💰 音声API料金", expanded=False):
            if "tts" in selected_model:
                st.write("**TTS料金 (1000文字あたり)**")
                tts_pricing = {"tts-1": "$0.015", "tts-1-hd": "$0.030", "gpt-4o-mini-tts": "$0.025"}
                current_price = tts_pricing.get(selected_model, "不明")
                st.write(f"- {selected_model}: {current_price}")
                char_count = st.number_input("文字数", min_value=1, value=100, step=10, key="tts_char_count")
                if selected_model in tts_pricing:
                    price = float(tts_pricing[selected_model].replace("$", ""))
                    cost = (char_count / 1000) * price
                    st.write(f"**推定コスト**: ${cost:.6f}")
            else:
                st.write("**STT料金 (分あたり)**")
                st.write("- whisper-1: $0.006")
                st.write("- gpt-4o-transcribe: $0.010")
                duration_minutes = st.number_input("音声時間（分）", min_value=0.1, value=1.0, step=0.1, key="stt_duration")
                stt_pricing = {"whisper-1": 0.006, "gpt-4o-transcribe": 0.010}
                if selected_model in stt_pricing:
                    cost = duration_minutes * stt_pricing[selected_model]
                    st.write(f"**推定コスト**: ${cost:.6f}")

# ==================================================
# 基底クラス（統一化版）
# ==================================================
class BaseDemo(ABC):
    """デモ機能の基底クラス（音声用統一化版）"""

    def __init__(self, demo_name: str):
        self.demo_name = demo_name
        self.config = ConfigManager("config.yml")
        try:
            self.client = OpenAIClient()
            self.openai_client = OpenAI()
            self.async_client = AsyncOpenAI()
        except Exception as e:
            st.error(f"OpenAIクライアントの初期化に失敗しました: {e}")
            st.stop()

        self.safe_key = sanitize_key(demo_name)
        self.message_manager = MessageManagerUI(f"messages_{self.safe_key}")
        self.model = None

        SessionStateManager.init_session_state()
        self._initialize_session_state()

    def _initialize_session_state(self):
        session_key = f"demo_state_{self.safe_key}"
        if session_key not in st.session_state:
            st.session_state[session_key] = {
                'initialized': True,
                'model': self.config.get("models.audio_default", "tts-1"),
                'execution_count': 0,
                'last_audio_file': None
            }

    def get_model(self) -> str:
        return st.session_state.get(f"model_{self.safe_key}", config.get("models.audio_default", "tts-1"))

    def initialize(self):
        self.model = setup_common_ui(self.demo_name)
        setup_sidebar_panels(self.model)

    def handle_error(self, e: Exception):
        lang = config.get("i18n.default_language", "ja")
        error_msg = config.get(f"error_messages.{lang}.general_error", "エラーが発生しました")
        st.error(f"{error_msg}: {str(e)}")
        if config.get("experimental.debug_mode", False):
            with st.expander("🔧 詳細エラー情報", expanded=False):
                st.exception(e)

    @error_handler_ui
    @timer_ui
    def safe_audio_api_call(self, api_func: callable, *args, **kwargs):
        max_retries = config.get("api.max_retries", 3)
        delay = config.get("api.retry_delay", 1)
        for attempt in range(max_retries):
            try:
                return api_func(*args, **kwargs)
            except Exception as e:
                if attempt == max_retries - 1:
                    raise e
                logger.warning(f"音声API呼び出し失敗 (試行 {attempt + 1}/{max_retries}): {e}")
                time.sleep(delay)
                delay *= 2 + random.random()

    @abstractmethod
    def run(self):
        pass

# ==================================================
# Text to Speech デモ（統一化版）
# ==================================================
class TextToSpeechDemo(BaseDemo):
    """Text to Speech API のデモ（統一化版）"""

    @error_handler_ui
    @timer_ui
    def run(self):
        self.initialize()

        with st.expander("OpenAI Audio API:実装例", expanded=False):
            st.write("テキストを音声に変換するTTSデモ。ストリーミング保存でMP3出力。")
            st.code(textwrap.dedent("""\
        # Text to Speech API 使用例
        with client.audio.speech.with_streaming_response.create(
            model=model, voice=voice, input=text
        ) as response:
            response.stream_to_file(output_path)
        # 保存したMP3を再生
        st.audio(str(output_path), format="audio/mp3")
            """), language="python")

        col1, col2 = st.columns([2, 1])
        with col1:
            voice = UIHelper.select_voice(f"voice_{self.safe_key}")
        with col2:
            stream = st.checkbox("ストリーミング転送", help="リアルタイム音声生成", key=f"stream_{self.safe_key}", value=True)

        input_method = st.radio("入力方法", ["テキスト直接入力", "txtファイル選択"], key=f"input_method_{self.safe_key}")
        if input_method == "テキスト直接入力":
            self._run_direct_text_input(voice, stream)
        else:
            self._run_file_input(voice, stream)

    def _run_direct_text_input(self, voice: str, stream: bool):
        example_text = config.get("samples.audio.tts_example", "こんにちは、これはテキスト読み上げのテストです。")
        with st.form(key=f"tts_form_{self.safe_key}"):
            text_input = st.text_area("変換するテキストを入力してください",
                                      height=config.get("ui.text_area_height", 100),
                                      placeholder=example_text)
            submitted = st.form_submit_button("🎵 音声生成")
        if submitted and text_input:
            self._process_tts(text_input, voice, stream, "direct_input")

    def _run_file_input(self, voice: str, stream: bool):
        txt_files = sorted(DATA_DIR.glob("*.txt"))
        if not txt_files:
            st.warning(f"{DATA_DIR} に .txt ファイルがありません")
            st.info("サンプルテキストファイルを作成してください")
            return
        txt_name = st.selectbox("テキストファイルを選択してください",
                                [f.name for f in txt_files],
                                key=f"txt_select_{self.safe_key}")
        txt_file = DATA_DIR / txt_name
        if st.button(f"🎵 {txt_name} を音声変換", key=f"convert_{self.safe_key}"):
            try:
                text = txt_file.read_text(encoding="utf-8")
                self._process_tts(text, voice, stream, txt_name)
            except Exception as e:
                st.error(f"ファイル読み込みエラー: {e}")

    def _process_tts(self, text: str, voice: str, stream: bool, source: str):
        try:
            session_key = f"demo_state_{self.safe_key}"
            if session_key in st.session_state:
                st.session_state[session_key]['execution_count'] += 1

            max_chars = config.get("audio.tts_max_chars", 4096)
            if len(text) > max_chars:
                st.warning(f"⚠️ テキストが長すぎます（{len(text)}文字 > {max_chars}文字制限）")
                text = text[:max_chars]
                st.info(f"テキストを{max_chars}文字に切り詰めました")

            ts = int(time.time())
            suffix = "_stream" if stream else ""
            output_name = f"tts_{source}_{ts}{suffix}.mp3"
            output_path = DATA_DIR / output_name

            with st.spinner("🎵 音声生成中..."):
                if stream:
                    def tts_stream_call():
                        return self.openai_client.audio.speech.with_streaming_response.create(
                            model=self.model,
                            voice=voice,
                            input=text,
                        )
                    with self.safe_audio_api_call(tts_stream_call) as response:
                        response.stream_to_file(output_path)
                else:
                    def tts_call():
                        return self.openai_client.audio.speech.create(
                            model=self.model,
                            voice=voice,
                            input=text,
                        )
                    resp = self.safe_audio_api_call(tts_call)
                    output_path.write_bytes(resp.content)

            st.success("✅ 音声生成完了")
            st.audio(str(output_path), format="audio/mp3")
            with open(output_path, "rb") as f:
                UIHelper.create_audio_download_button(f.read(), output_name)

            st.session_state[session_key]['last_audio_file'] = str(output_path)
        except Exception as e:
            self.handle_error(e)

# ==================================================
# Speech to Text デモ（統一化版）
# ==================================================
class SpeechToTextDemo(BaseDemo):
    """Speech to Text API のデモ（統一化版）"""

    @error_handler_ui
    @timer_ui
    def run(self):
        self.initialize()

        with st.expander("OpenAI Audio API:実装例", expanded=False):
            st.write("音声ファイルをテキストに変換するSTTデモ。")
            st.code(textwrap.dedent("""\
                # Speech to Text API 使用例
                with open(audio_file, "rb") as f:
                    transcript = client.audio.transcriptions.create(
                        model=model,
                        file=f,
                        response_format="text",
                    )
                st.write(transcript)
            """), language="python")

        audio_files = self._get_audio_files()
        if not audio_files:
            st.warning(f"{DATA_DIR} に音声ファイル(.mp3, .wav)がありません")
            st.info("TTSデモで生成した音声ファイルを使用するか、音声ファイルをアップロードしてください")
            return

        selected_file = st.selectbox("音声ファイルを選択",
                                     [f.name for f in audio_files],
                                     key=f"audio_select_{self.safe_key}")
        audio_file_path = DATA_DIR / selected_file
        st.audio(str(audio_file_path), format="audio/mp3")

        stt_model = st.selectbox("STTモデル", ["whisper-1", "gpt-4o-transcribe"], key=f"stt_model_{self.safe_key}")
        if st.button("🎤 文字起こし実行", key=f"transcribe_{self.safe_key}"):
            self._process_transcription(audio_file_path, selected_file, stt_model)

        self._display_transcription_result(selected_file)

    def _get_audio_files(self) -> List[Path]:
        patterns = config.get("audio.supported_formats", ["*.mp3", "*.wav", "*.m4a"])
        files: List[Path] = []
        for pattern in patterns:
            files.extend(DATA_DIR.glob(pattern))
        return sorted(files)

    def _process_transcription(self, audio_file: Path, filename: str, stt_model: str):
        try:
            session_key = f"transcription_{filename}"
            with st.spinner("🎤 文字起こし中..."):
                with audio_file.open("rb") as f:
                    def transcribe_call():
                        return self.openai_client.audio.transcriptions.create(
                            model=stt_model,
                            file=f,
                            response_format="text",
                        )
                    result = self.safe_audio_api_call(transcribe_call)

            text = result if isinstance(result, str) else getattr(result, "text", str(result))
            st.session_state[session_key] = {
                "transcript": text,
                "model": stt_model,
                "timestamp": time.time(),
                "filename": filename,
            }
            st.success("✅ 文字起こし完了")
            st.rerun()
        except Exception as e:
            self.handle_error(e)

    def _display_transcription_result(self, filename: str):
        session_key = f"transcription_{filename}"
        if session_key in st.session_state:
            result = st.session_state[session_key]
            st.subheader("📝 文字起こし結果")
            col1, col2, col3 = st.columns(3)
            with col1:
                st.write(f"**ファイル**: {result['filename']}")
            with col2:
                st.write(f"**モデル**: {result['model']}")
            with col3:
                timestamp = format_timestamp(result['timestamp'])
                st.write(f"**処理時刻**: {timestamp}")
            transcript = result['transcript']
            st.write("**内容**:")
            st.markdown(f"> {transcript}")
            c1, c2 = st.columns(2)
            with c1:
                if st.button("📋 テキストコピー", key=f"copy_transcript_{filename}"):
                    st.write("📋 コピーしました（手動でコピーしてください）")
                    st.code(transcript)
            with c2:
                UIHelper.create_audio_download_button(
                    transcript.encode("utf-8"),
                    f"transcript_{filename}_{int(result['timestamp'])}.txt",
                    "📥 テキストダウンロード",
                )

# ==================================================
# 音声翻訳デモ（英訳フォールバック付き）
# ==================================================
class SpeechTranslationDemo(BaseDemo):
    """Speech Translation API のデモ（統一化版）"""

    @error_handler_ui
    @timer_ui
    def run(self):
        self.initialize()

        with st.expander("OpenAI Audio API:実装例", expanded=False):
            st.write("音声ファイルを英語テキストに翻訳。英訳されない場合はChatで英訳フォールバック。")
            st.code(textwrap.dedent("""\
                # Speech Translation API 使用例
                with open(audio_file, "rb") as f:
                    translation = client.audio.translations.create(
                        model="whisper-1",
                        file=f,
                        response_format="text",
                    )
                # 万一英語化されないときは Chat で英訳フォールバック
            """), language="python")

        audio_files = self._get_audio_files()
        if not audio_files:
            st.warning(f"{DATA_DIR} に音声ファイルがありません")
            return

        selected_file = st.selectbox("音声ファイルを選択",
                                     [f.name for f in audio_files],
                                     key=f"audio_select_{self.safe_key}")
        audio_file_path = DATA_DIR / selected_file
        st.audio(str(audio_file_path), format="audio/mp3")

        tr_model = st.selectbox("翻訳用の音声モデル（まずはここで英訳を試行）",
                                ["whisper-1", "gpt-4o-transcribe"],
                                key=f"tr_model_{self.safe_key}")

        if st.button("🌐 英語翻訳実行", key=f"translate_{self.safe_key}"):
            self._process_translation(audio_file_path, selected_file, tr_model)

        self._display_translation_result(selected_file)

    def _get_audio_files(self) -> List[Path]:
        patterns = config.get("audio.supported_formats", ["*.mp3", "*.wav", "*.m4a"])
        files: List[Path] = []
        for pattern in patterns:
            files.extend(DATA_DIR.glob(pattern))
        return sorted(files)

    def _process_translation(self, audio_file: Path, filename: str, tr_model: str):
        try:
            session_key = f"translation_{filename}"
            with st.spinner("🌐 英語翻訳中..."):
                with audio_file.open("rb") as f:
                    if tr_model == "whisper-1":
                        def translate_call():
                            return self.openai_client.audio.translations.create(
                                model="whisper-1",
                                file=f,
                                response_format="text",
                            )
                        raw = self.safe_audio_api_call(translate_call)
                        first_text = raw if isinstance(raw, str) else getattr(raw, "text", str(raw))
                    else:
                        def transcribe_call():
                            return self.openai_client.audio.transcriptions.create(
                                model=tr_model,
                                file=f,
                                response_format="text",
                            )
                        raw = self.safe_audio_api_call(transcribe_call)
                        first_text = raw if isinstance(raw, str) else getattr(raw, "text", str(raw))

                english_text = self._force_translate_to_english(first_text)

            st.session_state[session_key] = {
                "translation": english_text,
                "model": tr_model,
                "timestamp": time.time(),
                "filename": filename,
            }
            st.success("✅ 翻訳完了")
            st.rerun()
        except Exception as e:
            self.handle_error(e)

    def _force_translate_to_english(self, source_text: str) -> str:
        """
        Chat を使って英語に強制変換。
        すでに英語ならそのまま返す / 説明は返さない
        """
        sys_prompt = (
            "You are a professional translator. "
            "If the user's text is not English, translate it into natural, fluent English. "
            "If it is already English, return it unchanged. "
            "Preserve names and style. Return only the English text without explanations."
        )
        try:
            resp = self.openai_client.chat.completions.create(
                model=config.get("models.translate_fallback", "gpt-4o-mini"),
                temperature=0,
                messages=[
                    {"role": "system", "content": sys_prompt},
                    {"role": "user", "content": source_text},
                ],
            )
            return resp.choices[0].message.content.strip()
        except Exception as e:
            logger.error(f"Translate fallback failed: {e}")
            return source_text

    def _display_translation_result(self, filename: str):
        session_key = f"translation_{filename}"
        if session_key in st.session_state:
            result = st.session_state[session_key]
            st.subheader("🌐 英語翻訳結果")
            col1, col2, col3 = st.columns(3)
            with col1:
                st.write(f"**ファイル**: {result['filename']}")
            with col2:
                st.write(f"**モデル**: {result['model']}")
            with col3:
                timestamp = format_timestamp(result['timestamp'])
                st.write(f"**処理時刻**: {timestamp}")
            translation = result["translation"]
            st.write("**English**:")
            st.markdown(f"> {translation}")
            c1, c2 = st.columns(2)
            with c1:
                if st.button("📋 翻訳コピー", key=f"copy_translation_{filename}"):
                    st.write("📋 コピーしました（手動でコピーしてください）")
                    st.code(translation)
            with c2:
                st.download_button(
                    "📥 翻訳ダウンロード",
                    data=translation,
                    file_name=f"translation_{filename}_{int(result['timestamp'])}.txt",
                    mime="text/plain",
                )

# ==================================================
# Realtime API デモ
# ==================================================
class RealtimeApiDemo(BaseDemo):
    """Realtime API のデモ（統一化版）"""

    @error_handler_ui
    @timer_ui
    def run(self):
        self.initialize()

        with st.expander("OpenAI Realtime API:実装例", expanded=False):
            st.write("リアルタイム音声対話デモ（要 pyaudio/simpleaudio）")
            st.code('''# Realtime API使用例
async with async_client.beta.realtime.connect(model="gpt-4o-realtime-preview") as conn:
    await conn.session.update(session={
        "voice": "alloy",
        "input_audio_format": "pcm16",
        "turn_detection": {"type": "server_vad"},
    })
# マイク→WebSocket→音声出力のリアルタイム処理''', language="python")

        st.warning("⚠️ このデモは実験的機能です。マイクとスピーカーが必要です。")

        if not self._check_dependencies():
            return

        self._show_settings()

        if st.button("🎤 リアルタイム対話開始", key=f"realtime_{self.safe_key}"):
            self._run_realtime_demo()

    def _check_dependencies(self) -> bool:
        missing = []
        try:
            import pyaudio  # noqa
        except ImportError:
            missing.append("pyaudio")
        try:
            import simpleaudio  # noqa
        except ImportError:
            missing.append("simpleaudio")
        if missing:
            st.error(f"❌ 必要なライブラリが不足: {', '.join(missing)}")
            st.info("`pip install " + " ".join(missing) + "`")
            return False
        st.success("✅ 必要なライブラリが利用可能です")
        return True

    def _show_settings(self):
        with st.expander("⚙️ Realtime API 設定", expanded=False):
            st.selectbox("音声選択",
                         config.get("audio.voices", ["alloy", "nova", "echo", "onyx", "shimmer"]),
                         key=f"realtime_voice_{self.safe_key}")
            st.selectbox("音声フォーマット", ["pcm16", "g711_ulaw", "g711_alaw"], key=f"audio_format_{self.safe_key}")
            st.checkbox("音声検出 (VAD) 有効", value=True, key=f"vad_{self.safe_key}")
            st.info("設定完了後、「リアルタイム対話開始」ボタンを押してください")

    def _run_realtime_demo(self):
        try:
            with st.spinner("🎤 リアルタイム対話セッション開始中..."):
                st.info("🔴 録音開始: マイクに向かって話してください")
                st.info("⏹️ 終了するには、ページを更新してください")
                asyncio.run(self._run_realtime_session())
        except Exception as e:
            self.handle_error(e)

    async def _run_realtime_session(self):
        try:
            import pyaudio
            import simpleaudio
            async with self.async_client.beta.realtime.connect(model="gpt-4o-realtime-preview") as conn:
                await conn.session.update(session={
                    "voice": "alloy",
                    "input_audio_format": "pcm16",
                    "input_audio_transcription": {"model": "gpt-4o-transcribe"},
                    "turn_detection": {"type": "server_vad"},
                })
                pa = pyaudio.PyAudio()
                stream = pa.open(format=pyaudio.paInt16, channels=1, rate=16_000, input=True, frames_per_buffer=1024)

                async def sender():
                    while True:
                        pcm = stream.read(1024, exception_on_overflow=False)
                        await conn.input_audio_buffer.append(audio=base64.b64encode(pcm).decode())

                async def receiver():
                    async for event in conn:
                        if event.type == "response.audio.delta":
                            wav = base64.b64decode(event.audio)
                            simpleaudio.play_buffer(wav, 1, 2, 24_000)
                        elif event.type == "response.done":
                            break

                await asyncio.gather(sender(), receiver())
        except Exception as e:
            logger.error(f"Realtime API error: {e}")
            raise e

# ==================================================
# Chained Voice Agent デモ（統一化版）
# ==================================================
class ChainedVoiceAgentDemo(BaseDemo):
    """Chained Voice Agent のデモ（統一化版）"""

    @error_handler_ui
    @timer_ui
    def run(self):
        self.initialize()

        with st.expander("OpenAI Audio API:実装例", expanded=False):
            st.write("音声→テキスト→Chat→音声の連鎖処理デモ。")
            st.code('''# Chained Voice Agent処理例
def voice_agent_chain(audio_bytes):
    # 1. STT: 音声→テキスト
    transcript = client.audio.transcriptions.create(
        model=stt_model,
        file=BytesIO(audio_bytes),
        response_format="text"
    )
    # 2. Chat: テキスト→応答テキスト
    chat_response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=build_chat_messages(transcript)
    )
    # 3. TTS: 応答テキスト→音声
    tts_response = client.audio.speech.create(
        model=tts_model,
        voice=voice,
        input=assistant_text
    )
    return tts_response.content''', language="python")

        col1, col2 = st.columns(2)
        with col1:
            stt_model = st.selectbox("STTモデル", ["whisper-1", "gpt-4o-transcribe"], key=f"stt_model_{self.safe_key}")
        with col2:
            tts_model = st.selectbox("TTSモデル", ["tts-1", "tts-1-hd", "gpt-4o-mini-tts"], key=f"tts_model_{self.safe_key}")
        voice = UIHelper.select_voice(f"voice_agent_{self.safe_key}")

        st.write("### 🎤 音声入力")
        uploaded_file = st.file_uploader("音声ファイルをアップロード (WAV/MP3 ≤25MB)",
                                         type=["wav", "mp3"],
                                         key=f"voice_upload_{self.safe_key}")
        if uploaded_file:
            st.audio(uploaded_file)  # 形式は自動判定
            if st.button("🤖 Voice Agent 実行", key=f"agent_{self.safe_key}"):
                self._process_voice_agent(uploaded_file, stt_model, tts_model, voice)

        st.write("### 📁 既存ファイルから選択")
        audio_files = self._get_audio_files()
        if audio_files:
            selected_file = st.selectbox("音声ファイルを選択",
                                         [f.name for f in audio_files],
                                         key=f"existing_audio_{self.safe_key}")
            audio_file_path = DATA_DIR / selected_file
            st.audio(str(audio_file_path), format="audio/mp3")
            if st.button("🤖 既存ファイルでAgent実行", key=f"agent_existing_{self.safe_key}"):
                with audio_file_path.open("rb") as f:
                    audio_bytes = f.read()
                self._process_voice_agent(audio_bytes, stt_model, tts_model, voice)

    def _get_audio_files(self) -> List[Path]:
        patterns = config.get("audio.supported_formats", ["*.mp3", "*.wav", "*.m4a"])
        files: List[Path] = []
        for pattern in patterns:
            files.extend(DATA_DIR.glob(pattern))
        return sorted(files)

    def _process_voice_agent(self, audio_input: Union[bytes, Any], stt_model: str, tts_model: str, voice: str):
        try:
            session_key = f"demo_state_{self.safe_key}"
            if session_key in st.session_state:
                st.session_state[session_key]['execution_count'] += 1

            if hasattr(audio_input, 'read'):
                audio_bytes = audio_input.read()
            else:
                audio_bytes = audio_input

            with st.spinner("🤖 Voice Agent 処理中..."):
                status_placeholder = st.empty()
                status_placeholder.info("🎤 Step 1: 音声認識中...")
                transcript = self._voice_agent_stt(audio_bytes, stt_model)
                status_placeholder.info("💭 Step 2: 応答生成中...")
                assistant_text = self._voice_agent_chat(transcript)
                status_placeholder.info("🎵 Step 3: 音声合成中...")
                response_audio = self._voice_agent_tts(assistant_text, tts_model, voice)
                status_placeholder.success("✅ Voice Agent 処理完了")

            self._display_voice_agent_result(transcript, assistant_text, response_audio)
        except Exception as e:
            self.handle_error(e)

    def _voice_agent_stt(self, audio_bytes: bytes, model: str) -> str:
        try:
            def stt_call():
                return self.openai_client.audio.transcriptions.create(
                    model=model,
                    file=BytesIO(audio_bytes),
                    response_format="text",
                )
            result = self.safe_audio_api_call(stt_call)
            return result if isinstance(result, str) else getattr(result, "text", str(result))
        except Exception as e:
            logger.error(f"STT error: {e}")
            raise e

    def _voice_agent_chat(self, user_text: str) -> str:
        try:
            messages: List[ChatCompletionMessageParam] = [
                ChatCompletionSystemMessageParam(
                    role="system",
                    content="You are a helpful Japanese voice assistant. 返答は日本語で、2文以内。"
                ),
                ChatCompletionUserMessageParam(role="user", content=user_text),
            ]
            def chat_call():
                return self.openai_client.chat.completions.create(model="gpt-4o-mini", messages=messages)
            response = self.safe_audio_api_call(chat_call)
            return response.choices[0].message.content
        except Exception as e:
            logger.error(f"Chat error: {e}")
            raise e

    def _voice_agent_tts(self, text: str, model: str, voice: str) -> bytes:
        try:
            def tts_call():
                return self.openai_client.audio.speech.create(model=model, voice=voice, input=text)
            response = self.safe_audio_api_call(tts_call)
            return response.content
        except Exception as e:
            logger.error(f"TTS error: {e}")
            raise e

    def _display_voice_agent_result(self, transcript: str, assistant_text: str, response_audio: bytes):
        st.success("🤖 Voice Agent 応答完了")
        col1, col2 = st.columns(2)
        with col1:
            st.subheader("🎤 あなたの発話")
            st.markdown(f"> {transcript}")
        with col2:
            st.subheader("🤖 アシスタント応答")
            st.markdown(f"> {assistant_text}")

        st.subheader("🎵 応答音声")
        st.audio(response_audio, format="audio/mp3")

        ts = int(time.time())
        response_filename = f"voice_agent_response_{ts}.mp3"
        response_path = DATA_DIR / response_filename
        response_path.write_bytes(response_audio)
        st.info(f"📁 応答音声を保存しました: {response_filename}")
        UIHelper.create_audio_download_button(response_audio, response_filename, "📥 応答音声ダウンロード")

# ==================================================
# デモマネージャー（統一化版）
# ==================================================
class AudioDemoManager:
    """音声デモの管理クラス（統一化版）"""

    def __init__(self):
        self.config = ConfigManager("config.yml")
        self.demos = self._initialize_demos()

    def _initialize_demos(self) -> Dict[str, BaseDemo]:
        return {
            "Text to Speech": TextToSpeechDemo("Text to Speech"),
            "Speech to Text": SpeechToTextDemo("Speech to Text"),
            "Speech Translation": SpeechTranslationDemo("Speech Translation"),
            "Realtime API": RealtimeApiDemo("Realtime API"),
            "Chained Voice Agent": ChainedVoiceAgentDemo("Chained Voice Agent"),
        }

    @error_handler_ui
    @timer_ui
    def run(self):
        try:
            SessionStateManager.init_session_state()
            demo_name = st.sidebar.radio("🎵 Audio Demo を選択", list(self.demos.keys()), key="audio_demo_selection")

            if "current_audio_demo" not in st.session_state:
                st.session_state.current_audio_demo = demo_name
            elif st.session_state.current_audio_demo != demo_name:
                st.session_state.current_audio_demo = demo_name

            demo = self.demos.get(demo_name)
            if demo:
                demo.run()
            else:
                st.error(f"デモ '{demo_name}' が見つかりません")

            self._display_footer()
        except Exception as e:
            st.error(f"アプリケーションの実行中にエラーが発生しました: {str(e)}")
            logger.error(f"Audio application execution error: {e}")
            if config.get("experimental.debug_mode", False):
                with st.expander("🔧 詳細エラー情報", expanded=False):
                    st.exception(e)

    def _display_footer(self):
        st.sidebar.markdown("---")
        st.sidebar.markdown("### 🎵 Audio API 情報")
        with st.sidebar.expander("📁 ファイル情報"):
            audio_files = list(DATA_DIR.glob("*.mp3")) + list(DATA_DIR.glob("*.wav"))
            txt_files = list(DATA_DIR.glob("*.txt"))
            st.write(f"**データディレクトリ**: {DATA_DIR}")
            st.write(f"**音声ファイル数**: {len(audio_files)}")
            st.write(f"**テキストファイル数**: {len(txt_files)}")

        with st.sidebar.expander("現在の設定"):
            safe_streamlit_json({
                "data_directory": str(DATA_DIR),
                "audio_models": config.get("models.categories.audio"),
                "supported_formats": config.get("audio.supported_formats"),
                "debug_mode": config.get("experimental.debug_mode"),
            })

        st.sidebar.markdown("### バージョン")
        st.sidebar.markdown("- OpenAI Audio & Speech Demo v3.1 (統一化版)")
        st.sidebar.markdown("- Streamlit " + st.__version__)
        st.sidebar.markdown("### リンク")
        st.sidebar.markdown("[OpenAI Audio API](https://platform.openai.com/docs/guides/speech-to-text)")
        st.sidebar.markdown("[Realtime API](https://platform.openai.com/docs/guides/realtime)")

# ==================================================
# メイン関数（統一化版）
# ==================================================
def main():
    try:
        logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        if not os.getenv("OPENAI_API_KEY"):
            st.error("環境変数 OPENAI_API_KEY が設定されていません。")
            st.info("export OPENAI_API_KEY='your-api-key' を実行してください。")
            st.stop()

        SessionStateManager.init_session_state()
        manager = AudioDemoManager()
        manager.run()
    except Exception as e:
        st.error(f"アプリケーションの起動に失敗しました: {str(e)}")
        logger.error(f"Audio application startup error: {e}")
        if config.get("experimental.debug_mode", False):
            with st.expander("🔧 詳細エラー情報", expanded=False):
                st.exception(e)

if __name__ == "__main__":
    main()

# streamlit run a04_audio_speeches.py --server.port=8504
