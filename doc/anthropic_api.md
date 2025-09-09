# Anthropic API サンプル・カタログ（`anthropic_api_jp`）

本資料は GitHub リポジトリ `nakashima2toshio/anthropic_api_jp` に含まれるプログラムと、対応ドキュメントからの情報をもとに、**API 機能別の索引**と**サブプログラム（クラス／デモ）一覧**、および **UI 内 `st.expander` → `st.code` のコード例抜粋**（取得できたもの）をまとめた Markdown です。

> 参照元（README 由来）に基づく要約のため、ドキュメント本文と差分がある場合はドキュメント本文を優先してください。

---

## 目次（プログラム一覧）

| 区分 | プログラム | 対応ドキュメント |
|---|---|---|
| Anthropic API | `a10_00_responses_api.py` | `doc/a10_00_responses_api.md` |
| Anthropic API | `a10_01_structured_outputs_parse_schema.py` | `doc/a10_01_structured_outputs_parse_schema.md` |
| Anthropic API | `a10_02_responses_tools_pydantic_parse.py` | `doc/a10_02_responses_tools_pydantic_parse.md` |
| Anthropic API | `a10_03_images_and_vision.py` | `doc/a10_03_images_and_vision.md` |
| Anthropic API | `a10_04_audio_speeches.py` | `doc/a10_04_audio_speeches.md` |
| Anthropic API | `a10_05_conversation_state.py` | `doc/a10_05_conversation_state.md` |
| Anthropic API | `a10_06_reasoning_chain_of_thought.py` | `doc/a10_06_reasoning_chain_of_thought.md` |
| utilities | `utils/web_search.py` | （該当ドキュメント未確認） |
| utilities | `utils/data_processor.py` | （該当ドキュメント未確認） |
| common | `helper_api.py` | `doc/helper_api.md` |
| common | `helper_st.py` | `doc/helper_st.md` |

---

## a10_00_responses_api.py

- **プログラム**: `a10_00_responses_api.py`
- **対応ドキュメント**: `doc/a10_00_responses_api.md`

### サブプログラム（クラス／デモ）一覧
| クラス／関数 | 概要 |
|---|---|
| `BaseDemo` | デモ機能の基底クラス（統一化版） |
| `TextResponseDemo` | 基本テキスト応答 |
| `MemoryResponseDemo` | 会話履歴付き応答 |
| `ImageResponseDemo` | 画像入力（URL・Base64対応） |
| `StructuredOutputDemo` | 構造化出力（messages.create対応） |
| `WeatherDemo` | OpenWeatherMap API 連携 |
| `ConversationDemo` | 複数ターン会話管理 |
| `StreamingDemo` | ストリーミング応答 |
| `DemoManager` | デモ統合管理・実行制御 |

### コード例（`def run(self)` 内 `with st.expander` → `st.code(...)` 抜粋）

#### TextResponseDemo - 基本テキスト応答
```python
from anthropic import Anthropic

client = Anthropic()
message = client.messages.create(
    model="claude-3-5-sonnet-20241022",
    max_tokens=1024,
    temperature=temperature,
    messages=[
        {"role": "user", "content": user_input}
    ]
)
ResponseProcessorUI.display_response(message)
```

#### MemoryResponseDemo - 会話履歴付き応答
```python
# 1回目: 初回質問
messages = [{"role": "user", "content": user_input_1}]
response_1 = client.messages.create(
    model=model,
    max_tokens=1024,
    temperature=temperature,
    messages=messages
)

# 2回目以降: 履歴 + 新しい質問
messages.append({"role": "assistant", "content": response_1.content[0].text})
messages.append({"role": "user", "content": user_input_2})
response_2 = client.messages.create(
    model=model,
    max_tokens=1024,
    temperature=temperature,
    messages=messages
)
```

#### ImageResponseDemo - 画像入力対応
```python
import base64
from anthropic import Anthropic

client = Anthropic()

# 画像をBase64エンコード
with open(image_path, "rb") as image_file:
    image_data = base64.b64encode(image_file.read()).decode('utf-8')

message = client.messages.create(
    model="claude-3-5-sonnet-20241022",
    max_tokens=1024,
    messages=[
        {
            "role": "user",
            "content": [
                {"type": "text", "text": question},
                {
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": "image/jpeg",
                        "data": image_data
                    }
                }
            ]
        }
    ]
)
```

#### StructuredOutputDemo - 構造化出力
```python
from anthropic import Anthropic

client = Anthropic()

# JSONスキーマ定義
schema = {
    "type": "object",
    "properties": {
        "name": {"type": "string", "description": "イベントの名前"},
        "date": {"type": "string", "description": "イベントの開催日（YYYY-MM-DD形式）"},
        "participants": {
            "type": "array",
            "items": {"type": "string"},
            "description": "参加者リスト"
        },
    },
    "required": ["name", "date", "participants"],
    "additionalProperties": False,
}

message = client.messages.create(
    model="claude-3-5-sonnet-20241022",
    max_tokens=1024,
    messages=[
        {"role": "user", "content": f"Extract event details: {user_input}"}
    ],
    response_format={
        "type": "json_schema",
        "json_schema": schema
    }
)
```

#### StreamingDemo - ストリーミング応答
```python
from anthropic import Anthropic

client = Anthropic()

with client.messages.stream(
    model="claude-3-5-sonnet-20241022",
    max_tokens=1024,
    messages=[
        {"role": "user", "content": user_input}
    ]
) as stream:
    for chunk in stream:
        if chunk.type == "content_block_delta":
            print(chunk.delta.text, end="")
```

---

## a10_01_structured_outputs_parse_schema.py

- **プログラム**: `a10_01_structured_outputs_parse_schema.py`
- **対応ドキュメント**: `doc/a10_01_structured_outputs_parse_schema.md`

### サブプログラム（クラス／デモ）一覧
| クラス／関数 | 概要 |
|---|---|
| `BaseDemo` | デモ機能の基底クラス（統一化版） |
| `EventExtractionDemo` | イベント情報抽出デモ |
| `MathReasoningDemo` | 数学的思考ステップデモ |
| `UIGenerationDemo` | UI コンポーネント生成デモ |
| `EntityExtractionDemo` | エンティティ抽出デモ |
| `ConditionalSchemaDemo` | 条件分岐スキーマデモ |
| `ChainedExtractionDemo` | 連鎖的情報抽出デモ |
| `DemoManager` | デモの管理クラス（統一化版） |

### コード例

#### EventExtractionDemo - イベント情報抽出
```python
from pydantic import BaseModel, Field
from anthropic import Anthropic

# Pydanticモデル定義
class EventInfo(BaseModel):
    name: str = Field(..., description="イベント名")
    date: str = Field(..., description="開催日")
    participants: List[str] = Field(..., description="参加者一覧")

client = Anthropic()

# Tool使用による構造化出力
tools = [{
    "name": "extract_event",
    "description": "Extract event information",
    "input_schema": EventInfo.model_json_schema()
}]

message = client.messages.create(
    model="claude-3-5-sonnet-20241022",
    max_tokens=1024,
    tools=tools,
    messages=[
        {"role": "user", "content": user_text}
    ]
)
```

#### MathReasoningDemo - 数学的思考ステップ
```python
from pydantic import BaseModel, Field
from typing import List

# Pydanticモデル定義
class Step(BaseModel):
    explanation: str = Field(..., description="このステップでの説明")
    output: str = Field(..., description="このステップの計算結果")

class MathReasoning(BaseModel):
    steps: List[Step] = Field(..., description="逐次的な解法ステップ")
    final_answer: str = Field(..., description="最終解")

# Tool定義とAPI呼び出し
tools = [{
    "name": "solve_math",
    "description": "Solve mathematical problems step by step",
    "input_schema": MathReasoning.model_json_schema()
}]

message = client.messages.create(
    model="claude-3-5-sonnet-20241022",
    max_tokens=1024,
    tools=tools,
    messages=[
        {"role": "user", "content": f"Solve: {expression}"}
    ]
)
```

#### UIGenerationDemo - UI コンポーネント生成
```python
from pydantic import BaseModel, Field
from typing import List, Optional

# Pydanticモデル定義（再帰構造）
class UIAttribute(BaseModel):
    name: str = Field(..., description="属性名")
    value: str = Field(..., description="属性値")

class UIComponent(BaseModel):
    type: str = Field(..., description="コンポーネント種類")
    label: str = Field(..., description="表示ラベル")
    children: List["UIComponent"] = Field(default_factory=list)
    attributes: List[UIAttribute] = Field(default_factory=list)

# Tool定義とAPI呼び出し
tools = [{
    "name": "generate_ui",
    "description": "Generate UI component tree",
    "input_schema": UIComponent.model_json_schema()
}]

message = client.messages.create(
    model="claude-3-5-sonnet-20241022",
    max_tokens=1024,
    tools=tools,
    messages=[
        {"role": "user", "content": f"Generate UI: {request}"}
    ]
)
```

#### EntityExtractionDemo - エンティティ抽出
```python
from pydantic import BaseModel, Field
from typing import List

# Pydanticモデル定義
class Entities(BaseModel):
    attributes: List[str] = Field(default_factory=list, description="形容詞・特徴")
    colors: List[str] = Field(default_factory=list, description="色")
    animals: List[str] = Field(default_factory=list, description="動物")

# Tool定義とAPI呼び出し
tools = [{
    "name": "extract_entities",
    "description": "Extract various entities from text",
    "input_schema": Entities.model_json_schema()
}]

message = client.messages.create(
    model="claude-3-5-sonnet-20241022",
    max_tokens=1024,
    tools=tools,
    messages=[
        {"role": "user", "content": f"Extract entities from: {text}"}
    ]
)
```

---

## a10_02_responses_tools_pydantic_parse.py

- **プログラム**: `a10_02_responses_tools_pydantic_parse.py`
- **対応ドキュメント**: `doc/a10_02_responses_tools_pydantic_parse.md`

### サブプログラム（クラス／デモ）一覧
| クラス／関数 | 概要 |
|---|---|
| `BaseDemo` | デモ機能の基底クラス |
| `BasicToolCallDemo` | 基本的な Tool Call のデモ |
| `MultipleToolsDemo` | 複数ツール登録・複数関数呼び出し |
| `AdvancedMultipleToolsDemo` | 高度な複数ツール呼び出し |
| `NestedStructureDemo` | 入れ子構造のデモ |
| `EnumTypeDemo` | Enum 型のデモ |
| `SimpleDataExtractionDemo` | シンプルなデータ抽出 |
| `MultipleEntityExtractionDemo` | 複数エンティティ抽出 |
| `ComplexQueryDemo` | 複雑なクエリパターン |
| `DynamicEnumDemo` | 動的な列挙型 |
| `ChainOfToolsDemo` | ツールの連鎖実行 |
| `ConversationWithToolsDemo` | ツール使用会話 |
| `DemoManager` | デモ管理クラス |

### コード例

#### BasicToolCallDemo - 基本的な Tool Call
```python
from anthropic import Anthropic
from pydantic import BaseModel

class WeatherRequest(BaseModel):
    city: str
    date: str

class NewsRequest(BaseModel):
    topic: str
    date: str

client = Anthropic()

tools = [
    {
        "name": "get_weather",
        "description": "Get weather information",
        "input_schema": WeatherRequest.model_json_schema()
    },
    {
        "name": "get_news",
        "description": "Get news information",
        "input_schema": NewsRequest.model_json_schema()
    }
]

message = client.messages.create(
    model="claude-3-5-sonnet-20241022",
    max_tokens=1024,
    tools=tools,
    messages=[
        {"role": "user", "content": user_input}
    ]
)
```

#### SimpleDataExtractionDemo - シンプルなデータ抽出
```python
from anthropic import Anthropic
from pydantic import BaseModel

class PersonInfo(BaseModel):
    name: str
    age: int

client = Anthropic()

tools = [{
    "name": "extract_person",
    "description": "Extract person information",
    "input_schema": PersonInfo.model_json_schema()
}]

message = client.messages.create(
    model="claude-3-5-sonnet-20241022",
    max_tokens=1024,
    tools=tools,
    messages=[
        {"role": "user", "content": user_input}
    ]
)

# Tool呼び出し結果の処理
if message.content[0].type == "tool_use":
    person_data = message.content[0].input
```

---

## a10_03_images_and_vision.py

- **プログラム**: `a10_03_images_and_vision.py`
- **対応ドキュメント**: `doc/a10_03_images_and_vision.md`

### サブプログラム（クラス／デモ）一覧
| クラス／関数 | 概要 |
|---|---|
| `BaseDemo` | ベースデモクラス（統一化版） |
| `URLImageToTextDemo` | URL 画像からテキスト生成 |
| `Base64ImageToTextDemo` | Base64 画像からテキスト生成 |
| `MultiImageAnalysisDemo` | 複数画像の比較分析 |
| `ImageWithToolsDemo` | 画像解析とツール使用 |
| `DemoManager` | デモ管理クラス（統一化版） |

### コード例

#### URLImageToTextDemo - URL画像からテキスト生成
```python
# 画像URLからテキスト生成の実装例
from anthropic import Anthropic

client = Anthropic()

message = client.messages.create(
    model="claude-3-5-sonnet-20241022",
    max_tokens=1024,
    messages=[
        {
            "role": "user",
            "content": [
                {"type": "text", "text": "この画像を日本語で説明してください"},
                {
                    "type": "image",
                    "source": {
                        "type": "url",
                        "url": image_url
                    }
                }
            ]
        }
    ]
)
```

#### Base64ImageToTextDemo - Base64画像からテキスト生成
```python
# Base64画像からテキスト生成の実装例
import base64
from anthropic import Anthropic

# 画像をBase64エンコード
with open(image_path, "rb") as image_file:
    image_base64 = base64.b64encode(image_file.read()).decode('utf-8')

client = Anthropic()

message = client.messages.create(
    model="claude-3-5-sonnet-20241022",
    max_tokens=1024,
    messages=[
        {
            "role": "user",
            "content": [
                {"type": "text", "text": prompt},
                {
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": "image/png",
                        "data": image_base64
                    }
                }
            ]
        }
    ]
)
```

#### MultiImageAnalysisDemo - 複数画像の比較分析
```python
# 複数画像の比較分析の実装例
from anthropic import Anthropic

client = Anthropic()

message = client.messages.create(
    model="claude-3-5-sonnet-20241022",
    max_tokens=1024,
    messages=[
        {
            "role": "user",
            "content": [
                {"type": "text", "text": "これらの画像を比較して違いを説明してください"},
                {
                    "type": "image",
                    "source": {"type": "url", "url": image_url_1}
                },
                {
                    "type": "image",
                    "source": {"type": "url", "url": image_url_2}
                }
            ]
        }
    ]
)
```

---

## a10_04_audio_speeches.py

- **プログラム**: `a10_04_audio_speeches.py`
- **対応ドキュメント**: `doc/a10_04_audio_speeches.md`

### サブプログラム（クラス／デモ）一覧
| クラス／関数 | 概要 |
|---|---|
| `BaseDemo` | デモ機能の基底クラス（音声用統一化版） |
| `AudioTranscriptionDemo` | 音声文字起こしデモ |
| `AudioAnalysisDemo` | 音声分析デモ |
| `ConversationWithAudioDemo` | 音声付き会話デモ |
| `AudioDemoManager` | 音声デモの管理クラス（統一化版） |

### コード例
> 注: Anthropic API は現在、音声の直接処理をサポートしていないため、音声ファイルは外部サービス（Whisper API等）で文字起こしした後、テキストとして処理されます。

#### AudioTranscriptionDemo - 音声文字起こし処理フロー
```python
# 音声を外部サービスで文字起こし後、Claudeで処理
import openai
from anthropic import Anthropic

# Step 1: Whisper APIで音声を文字起こし
openai_client = openai.OpenAI()
with open(audio_file, "rb") as f:
    transcription = openai_client.audio.transcriptions.create(
        model="whisper-1",
        file=f
    )

# Step 2: 文字起こし結果をClaudeで処理
anthropic_client = Anthropic()
message = anthropic_client.messages.create(
    model="claude-3-5-sonnet-20241022",
    max_tokens=1024,
    messages=[
        {
            "role": "user",
            "content": f"次の文字起こしテキストを要約してください: {transcription.text}"
        }
    ]
)
```

---

## a10_05_conversation_state.py

- **プログラム**: `a10_05_conversation_state.py`
- **対応ドキュメント**: `doc/a10_05_conversation_state.md`

### サブプログラム（クラス／デモ）一覧
| クラス／関数 | 概要 |
|---|---|
| `BaseDemo` | ベースデモクラス（統一化版） |
| `StatefulConversationDemo` | ステートフルな会話継続デモ |
| `ConversationSummaryDemo` | 会話要約デモ |
| `ContextWindowManagementDemo` | コンテキストウィンドウ管理 |
| `DemoManager` | デモ管理クラス（統一化版） |

### コード例

#### StatefulConversationDemo - ステートフルな会話継続
```python
# ステートフルな会話継続の実装例
from anthropic import Anthropic

client = Anthropic()

# 会話履歴を保持
conversation = []

# 初回質問
conversation.append({"role": "user", "content": "Anthropic APIの使い方を教えて"})
initial_response = client.messages.create(
    model="claude-3-5-sonnet-20241022",
    max_tokens=1024,
    messages=conversation
)
conversation.append({"role": "assistant", "content": initial_response.content[0].text})

# フォローアップ質問
conversation.append({"role": "user", "content": "具体的なコード例も教えて"})
follow_up_response = client.messages.create(
    model="claude-3-5-sonnet-20241022",
    max_tokens=1024,
    messages=conversation
)
```

#### ConversationSummaryDemo - 会話要約
```python
# 会話要約の実装例
from anthropic import Anthropic

client = Anthropic()

# 長い会話履歴
long_conversation = [
    {"role": "user", "content": "質問1..."},
    {"role": "assistant", "content": "回答1..."},
    # ... 多数のメッセージ
]

# 会話を要約
summary_prompt = f"""
以下の会話を簡潔に要約してください:
{long_conversation}
"""

summary = client.messages.create(
    model="claude-3-5-sonnet-20241022",
    max_tokens=500,
    messages=[
        {"role": "user", "content": summary_prompt}
    ]
)

# 要約を使って新しい会話を開始
new_conversation = [
    {"role": "system", "content": f"前回の会話の要約: {summary.content[0].text}"},
    {"role": "user", "content": "前回の続きから..."}
]
```

#### ContextWindowManagementDemo - コンテキストウィンドウ管理
```python
# コンテキストウィンドウ管理の実装例
from anthropic import Anthropic
import tiktoken

client = Anthropic()

def manage_context_window(messages, max_tokens=100000):
    """コンテキストウィンドウのサイズを管理"""
    # トークン数を推定（簡易版）
    total_tokens = sum(len(m["content"]) // 4 for m in messages)
    
    if total_tokens > max_tokens:
        # 古いメッセージを削除または要約
        # システムメッセージは保持
        system_messages = [m for m in messages if m.get("role") == "system"]
        recent_messages = messages[-10:]  # 最新10件を保持
        
        return system_messages + recent_messages
    
    return messages

# 使用例
conversation = manage_context_window(long_conversation)
response = client.messages.create(
    model="claude-3-5-sonnet-20241022",
    max_tokens=1024,
    messages=conversation
)
```

---

## a10_06_reasoning_chain_of_thought.py

- **プログラム**: `a10_06_reasoning_chain_of_thought.py`
- **対応ドキュメント**: `doc/a10_06_reasoning_chain_of_thought.md`

### サブプログラム（クラス／デモ）一覧
| クラス／関数 | 概要 |
|---|---|
| `BaseDemo` | ベースデモクラス（統一化版） |
| `StepByStepReasoningDemo` | 段階的推論（Step-by-Step） |
| `HypothesisTestDemo` | 仮説検証推論 |
| `TreeOfThoughtDemo` | 思考の木（Tree of Thought） |
| `ProsConsDecisionDemo` | 賛否比較決定（Pros-Cons-Decision） |
| `PlanExecuteReflectDemo` | 計画→実行→振り返り |
| `SelfConsistencyDemo` | 自己一貫性推論 |
| `DemoManager` | デモ管理クラス（統一化版） |

### コード例

#### StepByStepReasoningDemo - 段階的推論
```python
# Step-by-Step 推論の実装例
from anthropic import Anthropic

client = Anthropic()

system_prompt = '''あなたは段階的に問題を解く methodical なチューターです。
質問が与えられたら：
1. 問題を明確で順序立ったステップに分解してください
2. 各ステップに番号を付けてください（Step 1:, Step 2: など）
3. 作業を明確に示してください
4. 最後に "Answer:" に続けて最終的な答えを記載してください
5. 解答の信頼度を0-1で評価してください

推論において正確で論理的にしてください。'''

message = client.messages.create(
    model="claude-3-5-sonnet-20241022",
    max_tokens=1024,
    system=system_prompt,
    messages=[
        {"role": "user", "content": "2X + 1 = 5のとき、Xはいくつ？"}
    ]
)
```

#### HypothesisTestDemo - 仮説検証推論
```python
# 仮説検証推論の実装例
from anthropic import Anthropic

client = Anthropic()

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

message = client.messages.create(
    model="claude-3-5-sonnet-20241022",
    max_tokens=2048,
    system=system_prompt,
    messages=[
        {
            "role": "user",
            "content": "Problem: Webアプリの初回表示が3秒以上かかる\nHypothesis: 画像ファイルのサイズが大きすぎて読み込み時間を圧迫している"
        }
    ]
)
```

#### TreeOfThoughtDemo - 思考の木
```python
# Tree of Thought 推論の実装例
from anthropic import Anthropic

client = Anthropic()

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

message = client.messages.create(
    model="claude-3-5-sonnet-20241022",
    max_tokens=2048,
    system=system_prompt,
    messages=[
        {
            "role": "user",
            "content": "Goal: 4, 9, 10, 13 の数字を使って24を作る（四則演算のみ使用）"
        }
    ]
)
```

#### ProsConsDecisionDemo - 賛否比較決定
```python
# Pros-Cons-Decision 推論の実装例
from anthropic import Anthropic

client = Anthropic()

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

message = client.messages.create(
    model="claude-3-5-sonnet-20241022",
    max_tokens=2048,
    system=system_prompt,
    messages=[
        {
            "role": "user",
            "content": "Topic: リモートワークとオフィス出社、どちらを選ぶべきか？\nPerspective: 一般的"
        }
    ]
)
```

#### PlanExecuteReflectDemo - 計画・実行・振り返り
```python
# Plan-Execute-Reflect 推論の実装例
from anthropic import Anthropic

client = Anthropic()

system_prompt = '''あなたはPlan-Execute-Reflect改善ループを実装するAIです。

プロセス：
1. PLAN: 目標のための3-5個の具体的で実行可能なステップを作成
2. EXECUTE: 実行をシミュレートし、現実的な結果/課題を文書化
3. REFLECT: 何がうまくいき、何がうまくいかず、なぜかを分析
4. IMPROVE: 振り返りに基づいて改善された計画を作成
5. LEARN: 将来の応用のための重要な教訓を抽出'''

message = client.messages.create(
    model="claude-3-5-sonnet-20241022",
    max_tokens=2048,
    system=system_prompt,
    messages=[
        {
            "role": "user",
            "content": "Goal: 新しいプログラミング言語を学ぶ\nContext: Python経験者がRustを学ぼうとしている"
        }
    ]
)
```

#### SelfConsistencyDemo - 自己一貫性推論
```python
# Self-Consistency 推論の実装例
from anthropic import Anthropic

client = Anthropic()

# 同じ問題を複数回解いて一貫性を確認
problem = "ある商品が20%引きで800円でした。元の価格はいくらですか？"

responses = []
for i in range(3):
    message = client.messages.create(
        model="claude-3-5-sonnet-20241022",
        max_tokens=500,
        temperature=0.7,  # 多様性のため少し高めの温度
        messages=[
            {
                "role": "user",
                "content": f"次の問題を解いてください（解法{i+1}）: {problem}"
            }
        ]
    )
    responses.append(message.content[0].text)

# 最終的な答えを統合
final_message = client.messages.create(
    model="claude-3-5-sonnet-20241022",
    max_tokens=500,
    messages=[
        {
            "role": "user",
            "content": f"""以下の3つの解法を比較し、最も信頼できる答えを決定してください:
            
解法1: {responses[0]}
解法2: {responses[1]}
解法3: {responses[2]}

最終的な答えと、その理由を説明してください。"""
        }
    ]
)
```

---

## utilities

### utils/web_search.py
- **対応ドキュメント**: （未確認）
- **概要**: Web検索機能のユーティリティ（外部API連携）
- **サブプログラム一覧**: （未記載）

### utils/data_processor.py
- **対応ドキュメント**: （未確認）
- **概要**: データ処理・変換ユーティリティ
- **サブプログラム一覧**: （未記載）

---

## common

### helper_api.py
- **対応ドキュメント**: `doc/helper_api.md`
- **概要（README 由来）**: Anthropic Python SDK 呼び出しや共通ユーティリティの集約（クライアント初期化・共通呼び出し・トークンカウント等）。
- **主要クラス**:
  - `ConfigManager`: 設定管理（YAML読み込み、環境変数）
  - `AnthropicClient`: API クライアントラッパー（リトライ、エラーハンドリング）
  - `TokenCounter`: トークン数計算・コスト推定
  - `ResponseProcessor`: レスポンス処理・フォーマット

### helper_st.py
- **対応ドキュメント**: `doc/helper_st.md`
- **概要（README 由来）**: Streamlit UI 用の共通部品（レイアウト／入力／表示）。
- **主要クラス**:
  - `MessageManagerUI`: 会話履歴表示
  - `ResponseProcessorUI`: API レスポンス表示
  - `SessionStateManager`: セッション状態管理
  - `InfoPanelManager`: 情報パネル表示