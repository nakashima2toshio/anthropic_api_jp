# OpenAI API サンプル・カタログ（`openai_api_jp`）

本資料は GitHub リポジトリ `nakashima2toshio/openai_api_jp` に含まれるプログラムと、対応ドキュメントからの情報をもとに、**API 機能別の索引**と**サブプログラム（クラス／デモ）一覧**、および **UI 内 `st.expander` → `st.code` のコード例抜粋**（取得できたもの）をまとめた Markdown です。

> 参照元（README 由来）に基づく要約のため、ドキュメント本文と差分がある場合はドキュメント本文を優先してください。

---

## 目次（プログラム一覧）

| 区分 | プログラム | 対応ドキュメント |
|---|---|---|
| OpenAI API | `a00_responses_api.py` | `doc/a00_responses_api.md` |
| OpenAI API | `a01_structured_outputs_parse_schema.py` | `doc/a01_structured_outputs_parse_schema.md` |
| OpenAI API | `a02_responses_tools_pydantic_parse.py` | `doc/a02_responses_tools_pydantic_parse.md` |
| OpenAI API | `a03_images_and_vision.py` | `doc/a03_images_and_vision.md` |
| OpenAI API | `a04_audio_speeches.py` | `doc/a04_audio_speeches.md` |
| OpenAI API | `a05_conversation_state.py` | `doc/a05_conversation_state.md` |
| OpenAI API | `a06_reasoning_chain_of_thought.py` | `doc/a06_reasoning_chain_of_thought.md` |
| utilities | `a10_get_vsid.py` | （該当ドキュメント未確認） |
| utilities | `get_cities_list.py` | （該当ドキュメント未確認） |
| ccommon | `helper_api.py` | `doc/helper_api.md` |
| ccommon | `helper_st.py` | `doc/helper_st.md` |

---

## a00_responses_api.py

- **プログラム**: `a00_responses_api.py`
- **対応ドキュメント**: `doc/a00_responses_api.md`

### サブプログラム（クラス／デモ）一覧
| クラス／関数 | 概要 |
|---|---|
| `BaseDemo` | デモ機能の基底クラス（統一化版） |
| `TextResponseDemo` | 基本テキスト応答 |
| `MemoryResponseDemo` | 会話履歴付き応答 |
| `ImageResponseDemo` | 画像入力（URL・Base64対応） |
| `StructuredOutputDemo` | 構造化出力（create・parse対応） |
| `WeatherDemo` | OpenWeatherMap API 連携 |
| `FileSearchVectorStoreDemo` | FileSearch 専用 |
| `WebSearchToolsDemo` | WebSearch 専用 |
| `DemoManager` | デモ統合管理・実行制御 |

### コード例（`def run(self)` 内 `with st.expander` → `st.code(...)` 抜粋）

#### TextResponseDemo - 基本テキスト応答
```python
messages = get_default_messages()
messages.append(
    EasyInputMessageParam(role="user", content=user_input)
)

# 統一されたAPI呼び出し（temperatureパラメータ対応）
response = self.call_api_unified(messages, temperature=temperature)
　┗ api_params = {
    "input": messages,
    "model": model
    }
    self.client.responses.create(**params)
ResponseProcessorUI.display_response(response)
```

#### MemoryResponseDemo - 会話履歴付き応答
```python
# 1回目: 初回質問
messages = get_default_messages()
messages.append(EasyInputMessageParam(role="user", content=user_input_1))
response_1 = self.call_api_unified(messages, temperature=temperature)

# 2回目以降: 履歴 + 新しい質問
messages.append(EasyInputMessageParam(role="assistant", content=response_1_text))
messages.append(EasyInputMessageParam(role="user", content=user_input_2))
response_2 = self.call_api_unified(messages, temperature=temperature)
```

#### ImageResponseDemo - 画像入力対応
```python
messages = get_default_messages()
messages.append(
    EasyInputMessageParam(
        role="user",
        content=[
            ResponseInputTextParam(type="input_text", text=question),
            ResponseInputImageParam(
                type="input_image",
                image_url=image_url,
                detail="auto"
            ),
        ],
    )
)
response = self.call_api_unified(messages, temperature=temperature)
```

#### StructuredOutputDemo - 構造化出力
```python
# イベント情報のPydanticモデル
class Event(BaseModel):
    name: str
    date: str
    participants: List[str]

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

messages = [
    EasyInputMessageParam(
        role="developer",
        content="Extract event details from the text."
    ),
    EasyInputMessageParam(role="user", content=user_input)
]
```

#### FileSearchVectorStoreDemo - ファイル検索
```python
# FileSearchツールパラメータの作成
fs_tool = FileSearchToolParam(
    type="file_search",
    vector_store_ids=[vector_store_id],
    max_num_results=max_results
)
messages = get_default_messages()
messages.append(EasyInputMessageParam(role="user", content=query))

response = self.call_api_unified(messages, tools=[fs_tool])
```

#### WebSearchToolsDemo - Web検索
```python
user_location = UserLocation(
    type="approximate",
    country="JP",
    city="Tokyo",
    region="Tokyo"
)

search_tool = WebSearchToolParam(
    type="web_search",
    user_location=user_location
)
messages = get_default_messages()
messages.append(EasyInputMessageParam(role="user", content=query))

# API呼び出し
response = self.call_api_unified(messages, tools=[search_tool])
```

---

## a01_structured_outputs_parse_schema.py

- **プログラム**: `a01_structured_outputs_parse_schema.py`
- **対応ドキュメント**: `doc/a01_structured_outputs_parse_schema.md`

### サブプログラム（クラス／デモ）一覧
| クラス／関数 | 概要 |
|---|---|
| `BaseDemo` | デモ機能の基底クラス（統一化版） |
| `EventExtractionDemo` | イベント情報抽出デモ |
| `MathReasoningDemo` | 数学的思考ステップデモ |
| `UIGenerationDemo` | UI コンポーネント生成デモ |
| `EntityExtractionDemo` | エンティティ抽出デモ |
| `ConditionalSchemaDemo` | 条件分岐スキーマデモ |
| `ModerationDemo` | モデレーション＆拒否処理デモ |
| `DemoManager` | デモの管理クラス（統一化版） |

### コード例

#### EventExtractionDemo - イベント情報抽出
```python
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
```

#### MathReasoningDemo - 数学的思考ステップ
```python
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
```

#### UIGenerationDemo - UI コンポーネント生成
```python
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
```

#### EntityExtractionDemo - エンティティ抽出
```python
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
```

#### ConditionalSchemaDemo - 条件分岐スキーマ
```python
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
```

#### ModerationDemo - モデレーション処理
```python
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
```

---

## a02_responses_tools_pydantic_parse.py

- **プログラム**: `a02_responses_tools_pydantic_parse.py`
- **対応ドキュメント**: `doc/a02_responses_tools_pydantic_parse.md`

### サブプログラム（クラス／デモ）一覧
| クラス／関数 | 概要 |
|---|---|
| `BaseDemo` | デモ機能の基底クラス |
| `BasicFunctionCallDemo` | 基本的な function call のデモ |
| `MultipleToolsDemo` | 複数ツール登録・複数関数呼び出し |
| `AdvancedMultipleToolsDemo` | 高度な複数ツール呼び出し |
| `NestedStructureDemo` | 入れ子構造のデモ |
| `EnumTypeDemo` | Enum 型のデモ |
| `NaturalTextStructuredOutputDemo` | 自然文での構造化出力 |
| `SimpleDataExtractionDemo` | シンプルなデータ抽出 |
| `MultipleEntityExtractionDemo` | 複数エンティティ抽出 |
| `ComplexQueryDemo` | 複雑なクエリパターン |
| `DynamicEnumDemo` | 動的な列挙型 |
| `ChainOfThoughtDemo` | 思考の連鎖デモ |
| `ConversationHistoryDemo` | 会話履歴デモ |
| `DemoManager` | デモ管理クラス |

### コード例

#### BasicFunctionCallDemo - 基本的な Function Call
```python
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
)
```

#### SimpleDataExtractionDemo - シンプルなデータ抽出
```python
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
```

---

## a03_images_and_vision.py

- **プログラム**: `a03_images_and_vision.py`
- **対応ドキュメント**: `doc/a03_images_and_vision.md`

### サブプログラム（クラス／デモ）一覧
| クラス／関数 | 概要 |
|---|---|
| `BaseDemo` | ベースデモクラス（統一化版） |
| `URLImageToTextDemo` | URL 画像からテキスト生成 |
| `Base64ImageToTextDemo` | Base64 画像からテキスト生成 |
| `PromptToImageDemo` | プロンプトから画像生成 |
| `DemoManager` | デモ管理クラス（統一化版） |

### コード例

#### URLImageToTextDemo - URL画像からテキスト生成
```python
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
```

#### Base64ImageToTextDemo - Base64画像からテキスト生成
```python
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
```

#### PromptToImageDemo - プロンプトから画像生成
```python
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
```

---

## a04_audio_speeches.py

- **プログラム**: `a04_audio_speeches.py`
- **対応ドキュメント**: `doc/a04_audio_speeches.md`

### サブプログラム（クラス／デモ）一覧
| クラス／関数 | 概要 |
|---|---|
| `BaseDemo` | デモ機能の基底クラス（音声用統一化版） |
| `TextToSpeechDemo` | Text to Speech API のデモ |
| `SpeechToTextDemo` | Speech to Text API のデモ |
| `SpeechTranslationDemo` | Speech Translation API のデモ |
| `RealtimeApiDemo` | Realtime API のデモ |
| `ChainedVoiceAgentDemo` | Chained Voice Agent のデモ |
| `AudioDemoManager` | 音声デモの管理クラス（統一化版） |

### コード例
> a04_audio_speeches.py では `st.expander` 内に `st.code` ブロックが見つかりませんでした。このファイルは音声処理を中心に実装されており、コード例の表示方法が異なるようです。

---

## a05_conversation_state.py

- **プログラム**: `a05_conversation_state.py`
- **対応ドキュメント**: `doc/a05_conversation_state.md`

### サブプログラム（クラス／デモ）一覧
| クラス／関数 | 概要 |
|---|---|
| `BaseDemo` | ベースデモクラス（統一化版） |
| `StatefulConversationDemo` | ステートフルな会話継続デモ |
| `WebSearchParseDemo` | Web 検索と構造化パース |
| `FunctionCallingDemo` | Function Calling デモ |
| `DemoManager` | デモ管理クラス（統一化版） |

### コード例

#### StatefulConversationDemo - ステートフルな会話継続
```python
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
```

#### WebSearchParseDemo - Web検索と構造化パース
```python
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
```

#### FunctionCallingDemo - Function Calling
```python
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
    # API呼び出し実装
    pass
```

---

## a06_reasoning_chain_of_thought.py

- **プログラム**: `a06_reasoning_chain_of_thought.py`
- **対応ドキュメント**: `doc/a06_reasoning_chain_of_thought.md`

### サブプログラム（クラス／デモ）一覧
| クラス／関数 | 概要 |
|---|---|
| `BaseDemo` | ベースデモクラス（統一化版） |
| `StepByStepReasoningDemo` | 段階的推論（Step-by-Step） |
| `HypothesisTestDemo` | 仮説検証推論 |
| `TreeOfThoughtDemo` | 思考の木（Tree of Thought） |
| `ProsConsDecisionDemo` | 賛否比較決定（Pros-Cons-Decision） |
| `PlanExecuteReflectDemo` | 計画→実行→振り返り |
| `DemoManager` | デモ管理クラス（統一化版） |

### コード例

#### StepByStepReasoningDemo - 段階的推論
```python
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
```

#### HypothesisTestDemo - 仮説検証推論
```python
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
```

#### TreeOfThoughtDemo - 思考の木
```python
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
```

#### ProsConsDecisionDemo - 賛否比較決定
```python
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
```

#### PlanExecuteReflectDemo - 計画・実行・振り返り
```python
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
5. LEARN: 将来の応用のための重要な教訓を抽出'''

messages = [
    EasyInputMessageParam(role="system", content=system_prompt),
    EasyInputMessageParam(
        role="user",
        content=[
            ResponseInputTextParam(
                type="input_text", 
                text="Goal: 新しいプログラミング言語を学ぶ\\nContext: Python経験者がRustを学ぼうとしている"
            )
        ]
    )
]

response = client.responses.create(model=model, input=messages)
```

---

## utilities

### a10_get_vsid.py
- **対応ドキュメント**: （未確認）
- **サブプログラム一覧**: （未記載）
- **コード例**: 自動抽出未取得。

### get_cities_list.py
- **対応ドキュメント**: （未確認）
- **サブプログラム一覧**: （未記載）
- **コード例**: 自動抽出未取得。

---

## ccommon

### helper_api.py
- **対応ドキュメント**: `doc/helper_api.md`
- **概要（README 由来）**: OpenAI Python SDK 呼び出しや共通ユーティリティの集約（クライアント初期化・共通呼び出し等）。
- **サブプログラム一覧**: （未記載）
- **コード例**: 自動抽出未取得。

### helper_st.py
- **対応ドキュメント**: `doc/helper_st.md`
- **概要（README 由来）**: Streamlit UI 用の共通部品（レイアウト／入力／表示）。
- **サブプログラム一覧**: （未記載）
- **コード例**: 自動抽出未取得。