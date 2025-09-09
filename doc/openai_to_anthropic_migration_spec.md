# OpenAI API → Anthropic API 移植仕様書

## 1. エグゼクティブサマリー

本文書は、OpenAI API を使用したアプリケーションを Anthropic API (Claude) へ移植するための技術仕様書です。両APIの主要な差異と、移植に必要な変更点を体系的にまとめています。

### 移植難易度評価
- **全体難易度**: 中程度
- **推定工数**: 既存コードベースの規模により2-4週間
- **主要な変更箇所**: API呼び出し形式、モデル名、一部機能の代替実装

---

## 2. 基本的なAPI構造の比較

### 2.1 クライアント初期化

#### OpenAI
```python
from openai import OpenAI
client = OpenAI(api_key="sk-...")
```

#### Anthropic
```python
from anthropic import Anthropic
client = Anthropic(api_key="sk-ant-...")
```

**移植ポイント**: 
- ライブラリ名とクライアントクラス名の変更
- APIキーのプレフィックスが異なる（`sk-` → `sk-ant-`）

### 2.2 基本的なメッセージ送信

#### OpenAI
```python
response = client.chat.completions.create(
    model="gpt-4",
    messages=[
        {"role": "system", "content": "You are a helpful assistant"},
        {"role": "user", "content": "Hello"}
    ]
)
result = response.choices[0].message.content
```

#### Anthropic
```python
message = client.messages.create(
    model="claude-3-5-sonnet-20241022",
    system="You are a helpful assistant",  # システムメッセージは別パラメータ
    messages=[
        {"role": "user", "content": "Hello"}
    ],
    max_tokens=1024  # 必須パラメータ
)
result = message.content[0].text
```

**主要な違い**:
1. エンドポイント名: `chat.completions.create` → `messages.create`
2. システムメッセージの扱い: messages配列内 → 独立したsystemパラメータ
3. max_tokensが必須パラメータ
4. レスポンス構造: `choices[0].message.content` → `content[0].text`

---

## 3. 機能別移植ガイド

### 3.1 構造化出力 (Structured Outputs)

#### OpenAI - response_format使用
```python
response = client.chat.completions.create(
    model="gpt-4",
    messages=messages,
    response_format={
        "type": "json_schema",
        "json_schema": schema
    }
)
```

#### Anthropic - Tool使用による実装
```python
tools = [{
    "name": "extract_data",
    "description": "Extract structured data",
    "input_schema": schema  # Pydantic model.model_json_schema()
}]

message = client.messages.create(
    model="claude-3-5-sonnet-20241022",
    max_tokens=1024,
    tools=tools,
    messages=messages
)

# Tool呼び出し結果から構造化データを取得
if message.content[0].type == "tool_use":
    structured_data = message.content[0].input
```

**移植ポイント**:
- OpenAIのresponse_format → AnthropicのTool機能で代替
- スキーマ定義方法は類似（JSON Schema形式）
- レスポンス処理ロジックの変更が必要

### 3.2 Function Calling / Tool Use

#### OpenAI
```python
tools = [{
    "type": "function",
    "function": {
        "name": "get_weather",
        "description": "Get weather information",
        "parameters": {
            "type": "object",
            "properties": {
                "location": {"type": "string"}
            }
        }
    }
}]

response = client.chat.completions.create(
    model="gpt-4",
    messages=messages,
    tools=tools,
    tool_choice="auto"
)
```

#### Anthropic
```python
tools = [{
    "name": "get_weather",
    "description": "Get weather information",
    "input_schema": {
        "type": "object",
        "properties": {
            "location": {"type": "string"}
        }
    }
}]

message = client.messages.create(
    model="claude-3-5-sonnet-20241022",
    max_tokens=1024,
    tools=tools,
    messages=messages
)
```

**移植ポイント**:
- Tool定義構造の簡素化（functionラッパー不要）
- `parameters` → `input_schema`
- `tool_choice`パラメータは現在サポートされていない

### 3.3 画像処理 (Vision)

#### OpenAI
```python
messages = [{
    "role": "user",
    "content": [
        {"type": "text", "text": "What's in this image?"},
        {"type": "image_url", "image_url": {"url": image_url}}
    ]
}]
```

#### Anthropic
```python
messages = [{
    "role": "user",
    "content": [
        {"type": "text", "text": "What's in this image?"},
        {
            "type": "image",
            "source": {
                "type": "base64",  # または "url"
                "media_type": "image/jpeg",
                "data": base64_data  # または "url": image_url
            }
        }
    ]
}]
```

**移植ポイント**:
- 画像指定方法の変更: `image_url` → `image.source`
- media_typeの明示的な指定が必要
- Base64エンコーディングを推奨

### 3.4 ストリーミング

#### OpenAI
```python
stream = client.chat.completions.create(
    model="gpt-4",
    messages=messages,
    stream=True
)

for chunk in stream:
    if chunk.choices[0].delta.content:
        print(chunk.choices[0].delta.content, end="")
```

#### Anthropic
```python
with client.messages.stream(
    model="claude-3-5-sonnet-20241022",
    max_tokens=1024,
    messages=messages
) as stream:
    for chunk in stream:
        if chunk.type == "content_block_delta":
            print(chunk.delta.text, end="")
```

**移植ポイント**:
- ストリーミングメソッドが別: `create(stream=True)` → `stream()`
- コンテキストマネージャー（with文）の使用を推奨
- チャンクデータ構造の違い

### 3.5 音声処理

#### OpenAI
```python
# Text-to-Speech
response = client.audio.speech.create(
    model="tts-1",
    voice="alloy",
    input="Hello world"
)

# Speech-to-Text
transcription = client.audio.transcriptions.create(
    model="whisper-1",
    file=audio_file
)
```

#### Anthropic
```python
# Anthropic APIは音声処理を直接サポートしていない
# 代替案：外部サービス（Whisper API等）との組み合わせ

# Step 1: 外部サービスで音声処理
transcription = external_whisper_api.transcribe(audio_file)

# Step 2: テキストをClaude APIで処理
message = client.messages.create(
    model="claude-3-5-sonnet-20241022",
    max_tokens=1024,
    messages=[{"role": "user", "content": transcription}]
)
```

**移植ポイント**:
- **重要**: Anthropic APIは音声処理機能を持たない
- 外部音声処理サービスとの統合が必要
- アーキテクチャの再設計が必要な場合がある

---

## 4. モデル対応表

| 用途 | OpenAI | Anthropic | 備考 |
|------|--------|-----------|------|
| 高性能・複雑なタスク | gpt-4, gpt-4-turbo | claude-3-5-sonnet-20241022 | 最新・最高性能 |
| バランス型 | gpt-3.5-turbo | claude-3-haiku-20240307 | コスト効率重視 |
| 画像理解 | gpt-4-vision | claude-3-5-sonnet-20241022 | Claudeは全モデルで画像対応 |
| 長文処理 | gpt-4-32k | claude-3-5-sonnet-20241022 | Claude: 200kトークン対応 |
| コーディング | gpt-4 | claude-3-5-sonnet-20241022 | 両者とも高性能 |

---

## 5. 料金体系の比較

### トークン計算の違い
- **OpenAI**: 入力・出力トークンで課金
- **Anthropic**: 同様に入力・出力トークンで課金、ただし料金体系が異なる

### 参考料金（2024年時点、1Mトークンあたり）
| モデル | 入力料金 | 出力料金 |
|--------|----------|----------|
| GPT-4 | $30 | $60 |
| Claude-3-5-Sonnet | $3 | $15 |
| GPT-3.5-Turbo | $0.5 | $1.5 |
| Claude-3-Haiku | $0.25 | $1.25 |

**注意**: 料金は変動する可能性があるため、最新情報を確認すること

---

## 6. 移植時の注意事項

### 6.1 レート制限
- **OpenAI**: TPM（Tokens Per Minute）、RPM（Requests Per Minute）
- **Anthropic**: 同様の制限あり、ただし具体的な値は異なる
- 移植時はレート制限の再調整が必要

### 6.2 エラーハンドリング
```python
# OpenAI
from openai import OpenAIError, RateLimitError

# Anthropic
from anthropic import AnthropicError, RateLimitError
```

エラークラス名は類似しているが、インポート元が異なる

### 6.3 非同期処理
```python
# OpenAI
from openai import AsyncOpenAI
async_client = AsyncOpenAI()

# Anthropic
from anthropic import AsyncAnthropic
async_client = AsyncAnthropic()
```

両APIとも非同期クライアントをサポート

---

## 7. 移植チェックリスト

### Phase 1: 準備
- [ ] Anthropic APIキーの取得
- [ ] anthropic Pythonライブラリのインストール
- [ ] 既存のOpenAI API使用箇所の洗い出し
- [ ] テスト環境の構築

### Phase 2: 基本機能の移植
- [ ] クライアント初期化の変更
- [ ] 基本的なテキスト生成の移植
- [ ] システムプロンプトの移行
- [ ] エラーハンドリングの更新

### Phase 3: 高度な機能の移植
- [ ] 構造化出力の実装変更
- [ ] Function Calling → Tool Use への移行
- [ ] 画像処理の移植
- [ ] ストリーミング処理の更新

### Phase 4: 特殊機能の対応
- [ ] 音声処理の代替実装
- [ ] Embeddings機能の代替検討
- [ ] Fine-tuning依存部分の再設計

### Phase 5: 最適化とテスト
- [ ] レート制限の調整
- [ ] コスト最適化
- [ ] パフォーマンステスト
- [ ] 統合テスト

---

## 8. 不足情報と推奨事項

### 8.1 現時点で不足している情報

1. **Embeddings API**
   - Anthropic APIにはEmbeddings生成機能がない
   - 代替案: OpenAI Embeddings APIの継続使用、または他のEmbeddingサービス

2. **Fine-tuning**
   - Anthropic APIはFine-tuning未対応
   - 代替案: プロンプトエンジニアリング、Few-shot learning

3. **DALL-E相当の画像生成**
   - Anthropic APIは画像生成機能なし
   - 代替案: DALL-E APIの継続使用、Stable Diffusion等

4. **Assistants API**
   - Anthropic APIにAssistants API相当機能なし
   - 代替案: カスタム実装が必要

5. **Batch API**
   - 大量処理用のBatch APIが未実装
   - 代替案: 独自のバッチ処理実装

### 8.2 移植前の確認事項

1. **コンプライアンス要件**
   - データ保存ポリシーの違い
   - 地域制限の確認

2. **SLA（Service Level Agreement）**
   - 可用性保証の違い
   - サポート体制の違い

3. **SDK機能の完全性**
   - 使用している全機能のAnthropic API対応状況
   - サードパーティライブラリの互換性

### 8.3 推奨される移植アプローチ

1. **段階的移植**
   - 新規機能から順次Anthropic APIへ移行
   - 重要度の低い機能から試験的に移植

2. **ハイブリッド運用**
   - 音声・画像生成はOpenAI API継続
   - テキスト処理をAnthropic APIへ移行

3. **抽象化レイヤーの実装**
   ```python
   class LLMProvider:
       def __init__(self, provider="anthropic"):
           if provider == "anthropic":
               self.client = Anthropic()
           elif provider == "openai":
               self.client = OpenAI()
       
       def generate_text(self, prompt, **kwargs):
           # 統一インターフェース実装
           pass
   ```

---

## 9. サンプル移植コード

### 完全な移植例：会話型チャットボット

#### OpenAI版
```python
from openai import OpenAI

class OpenAIChatbot:
    def __init__(self):
        self.client = OpenAI()
        self.conversation = [
            {"role": "system", "content": "You are a helpful assistant"}
        ]
    
    def chat(self, user_input):
        self.conversation.append({"role": "user", "content": user_input})
        
        response = self.client.chat.completions.create(
            model="gpt-4",
            messages=self.conversation,
            temperature=0.7
        )
        
        assistant_message = response.choices[0].message.content
        self.conversation.append({"role": "assistant", "content": assistant_message})
        
        return assistant_message
```

#### Anthropic版
```python
from anthropic import Anthropic

class AnthropicChatbot:
    def __init__(self):
        self.client = Anthropic()
        self.system_prompt = "You are a helpful assistant"
        self.conversation = []
    
    def chat(self, user_input):
        self.conversation.append({"role": "user", "content": user_input})
        
        message = self.client.messages.create(
            model="claude-3-5-sonnet-20241022",
            max_tokens=1024,
            temperature=0.7,
            system=self.system_prompt,
            messages=self.conversation
        )
        
        assistant_message = message.content[0].text
        self.conversation.append({"role": "assistant", "content": assistant_message})
        
        return assistant_message
```

---

## 10. まとめ

OpenAI APIからAnthropic APIへの移植は、基本的な機能については比較的直接的な変換が可能ですが、以下の点に注意が必要です：

### 移植が容易な機能
- テキスト生成
- 構造化出力（実装方法は異なる）
- 画像理解
- ストリーミング

### 移植に工夫が必要な機能
- Function Calling → Tool Use
- システムメッセージの扱い
- レスポンス構造の処理

### 代替実装が必要な機能
- 音声処理（TTS/STT）
- 画像生成
- Embeddings
- Fine-tuning

移植を成功させるためには、段階的なアプローチと十分なテストが重要です。また、両APIの特性を理解し、それぞれの強みを活かしたハイブリッドアーキテクチャの検討も推奨されます。