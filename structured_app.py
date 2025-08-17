# app.py
# Single-file Streamlit demo:
# Anthropic Messages API (tools) × Pydantic structured output for Event extraction

import os
import json
from typing import List, Optional, Tuple

import streamlit as st

# --- Optional: read .env if present (safe no-op when missing) ---
try:
    from dotenv import load_dotenv  # type: ignore
    load_dotenv()
except Exception:
    pass

# --- Pydantic model (v2) ---
try:
    from pydantic import BaseModel, Field
except ImportError as e:
    st.stop()
    raise

class Event(BaseModel):
    """自由文から抽出するイベント情報"""
    name: str = Field(..., description="イベント名。短い固有名詞")
    date: str = Field(..., description="日付（例: 2025-09-01 や 'Sep 1, 2025' など自由形式でOK）")
    participants: List[str] = Field(..., description="参加者名の配列")

def pydantic_to_tool_schema(model) -> dict:
    # Anthropic tools.input_schema は JSON Schema 準拠の object を想定
    return model.model_json_schema()

def build_tools_schema():
    return [
        {
            "name": "extract_event",
            "description": (
                "自由記述からイベント情報を抽出し、厳密に指定スキーマで返す。"
                "必ず 'name'(文字列), 'date'(文字列), 'participants'(文字列配列) を含める。"
            ),
            "input_schema": pydantic_to_tool_schema(Event),
        }
    ]

# --- Anthropic wrapper ---
class EventExtractor:
    def __init__(self, model: str = "claude-sonnet-4-20250514"):
        # Import inside to avoid import error before UI renders
        try:
            from anthropic import Anthropic  # type: ignore
        except Exception as e:
            raise RuntimeError(
                "anthropic パッケージが見つかりません。`pip install anthropic` を実行してください。"
            ) from e

        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            raise RuntimeError(
                "環境変数 ANTHROPIC_API_KEY が未設定です。.env か環境に設定してください。"
            )

        self.client = Anthropic(api_key=api_key)
        self.model = model
        self.tools = build_tools_schema()

        # ---- tool_choice の型安全な生成（新SDK/旧SDK両対応）----
        try:
            # 新しめのSDKでは「type を明示」しないと 400 になるケースがある
            from anthropic.types import ToolChoiceToolParam  # type: ignore
            self.tool_choice_param = ToolChoiceToolParam(type="tool", name="extract_event")
        except Exception:
            # 旧SDK向けフォールバック（辞書でも受け付ける版）
            self.tool_choice_param = {"type": "tool", "name": "extract_event"}

    def extract(self, text: str) -> Tuple[Optional[Event], dict]:
        """
        テキストから Event を抽出。
        戻り値: (Event or None, usage_dict)
        """
        # 生成系設定
        system_prompt = (
            "あなたは情報抽出ボットです。与えられた自由記述からイベント情報を抽出し、"
            "必ずツール 'extract_event' を使って JSON Schema に完全準拠した入力を返してください。"
            "名前の余分な空白や括弧は取り除き、参加者は重複を排除してください。"
        )

        msg = self.client.messages.create(
            model=self.model,
            max_tokens=512,
            system=system_prompt,
            tools=self.tools,
            tool_choice=self.tool_choice_param,  # ← type="tool" を明示
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": (
                                "次の文章からイベント情報を抽出して。"
                                "ツール 'extract_event' を必ず使い、正確なスキーマで返すこと。\n\n"
                                f"{text}"
                            ),
                        }
                    ],
                }
            ],
        )

        # usage（トークン数）
        usage = getattr(msg, "usage", None)
        usage_dict = {
            "input_tokens": getattr(usage, "input_tokens", None),
            "output_tokens": getattr(usage, "output_tokens", None),
        }

        # content から tool_use ブロックを探す（SDKの型差異に耐えるように dict/obj 両対応）
        tool_input = None
        for block in getattr(msg, "content", []) or []:
            btype = getattr(block, "type", None) or (isinstance(block, dict) and block.get("type"))
            bname = getattr(block, "name", None) or (isinstance(block, dict) and block.get("name"))
            if btype == "tool_use" and bname == "extract_event":
                tool_input = getattr(block, "input", None) or (isinstance(block, dict) and block.get("input"))
                break

        if not tool_input:
            # ツールが呼ばれなかった／フォーマット逸脱
            return None, {**usage_dict, "validation_error": "tool_use 'extract_event' の応答が見つかりませんでした。"}

        try:
            event = Event(**tool_input)
            return event, usage_dict
        except Exception as e:
            return None, {**usage_dict, "validation_error": str(e)}

# --- Streamlit UI ---
st.set_page_config(page_title="Event Extractor (Anthropic + Pydantic)", layout="centered")
st.title("📅 Event Extractor (Anthropic + Pydantic)")
st.caption("Anthropic Messages API のツール機能 × Pydantic 検証 / Streamlit 1ファイル・デモ")

with st.sidebar:
    st.header("設定")
    model_id = st.text_input(
        "モデルID",
        value="claude-sonnet-4-20250514",
        help="例: claude-sonnet-4-20250514（利用可能なモデルを指定）",
    )
    st.text_input("ANTHROPIC_API_KEY（未設定ならここに一時入力可）", type="password", key="key_input")
    apply_key = st.button("このセッションだけ環境変数を上書き")
    st.markdown(
        "[公式ドキュメント（ツール機能）](https://docs.anthropic.com/en/docs/agents-and-tools/tool-use/implement-tool-use)"
    )

if apply_key and st.session_state.get("key_input"):
    os.environ["ANTHROPIC_API_KEY"] = st.session_state["key_input"]
    st.success("セッション環境に ANTHROPIC_API_KEY を設定しました。")

default_text = """来週の火曜(9/2) 19:00 から「Python関西もくもく会#58」を開催します。
会場は大阪駅前第3ビルの会議室。参加予定は、中島 太郎、田中 花子、Lee Minho です。"""

st.subheader("入力テキスト")
text = st.text_area(
    "イベントの自由記述を貼り付け",
    value=default_text,
    height=180,
    placeholder="ここにテキストを入力..."
)

col1, col2 = st.columns(2)
with col1:
    run = st.button("抽出する", type="primary")
with col2:
    clear = st.button("クリア")

if clear:
    st.session_state.clear()
    try:
        st.rerun()
    except Exception:
        st.experimental_rerun()

if run and text.strip():
    # 準備チェック
    try:
        extractor = EventExtractor(model=model_id)
    except Exception as e:
        st.error(str(e))
    else:
        with st.spinner("抽出中..."):
            event, usage = extractor.extract(text)

        st.subheader("抽出結果")
        if event:
            st.success("Pydantic 検証に成功しました！")
            # JSON と Python オブジェクト表示
            st.json(json.loads(event.model_dump_json()))
            st.markdown("**Pythonオブジェクトとして:**")
            st.code(repr(event), language="python")
        else:
            st.error("抽出または検証に失敗しました。")
            if usage and isinstance(usage, dict) and usage.get("validation_error"):
                st.exception(Exception(usage["validation_error"]))

        st.subheader("トークン使用量")
        st.write(usage or {"input_tokens": None, "output_tokens": None})

st.markdown("---")
st.caption(
    "仕組み: Pydantic→JSON Schema→Anthropic tools.input_schema として指定。"
    "tool_choice でツール呼び出しを強制し、返ってきた tool_use.input を Pydantic で検証。"
)

