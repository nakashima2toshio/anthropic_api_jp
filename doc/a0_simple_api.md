# a0_simple_api.ipynb 設計資料

## 概要

`a0_simple_api.ipynb` は Anthropic API の基本的な使用方法を学習するためのJupyterノートブックです。初心者向けにAPIの主要機能を体験できるサンプルコードを提供しています。

## 目的

- Anthropic API の基本的な使い方を学習
- Claude モデルの基本的な応答生成機能の体験
- 構造化出力（Pydantic + JSON Schema）の実装方法の理解
- Claude Vision（画像解析）機能の利用方法の学習
- APIの制限事項と代替手段の理解

## ファイル構成

### セクション構成

1. **環境セットアップ**
   - 必要なライブラリのインストール（anthropic, pydantic, python-dotenv）
   - Python環境とSDKバージョンの確認
   - API_KEY の存在確認

2. **基本的なメッセージ作成 (`messages.create`)**
   - 単純なテキスト生成
   - モデル: `claude-3-5-haiku-20241022`
   - 学習者向けの簡潔な応答例

3. **構造化出力（Pydantic + JSON Schema）**
   - Pydanticモデルの定義（`TodoItem`, `TodoPlan`）
   - JSON Schemaの自動生成
   - 構造化データの検証とパース

4. **API制限事項の説明**
   - 音声生成（TTS）機能なし - 代替手段の提示
   - 音声認識（STT）機能なし - 代替手段の提示
   - 音声翻訳機能なし - 代替手段の提示

5. **画像処理（Claude Vision）**
   - 画像生成機能なし - 代替手段の提示
   - 画像解析機能のサンプル実装
   - Base64エンコーディングによる画像データの送信

6. **詳細なメッセージ作成**
   - システムプロンプトの使用
   - 温度パラメーターの調整

## 技術仕様

### 使用モデル
- **Primary**: `claude-3-5-haiku-20241022` (基本的な応答生成用)
- **Vision**: `claude-3-5-sonnet-20241125` (画像解析用)

### 依存関係
```python
anthropic >= latest
pydantic >= latest  
python-dotenv >= latest
```

### 環境変数
- `ANTHROPIC_API_KEY`: 必須
- `ANTHROPIC_MODEL`: オプション（デフォルト: claude-3-5-haiku-20241022）

### データモデル設計

#### TodoItem
```python
class TodoItem(BaseModel):
    title: str = Field(..., description="やることのタイトル")
    priority: int = Field(..., ge=1, le=5, description="1(低)〜5(高)")
    tags: List[str] = Field(default_factory=list)
```

#### TodoPlan
```python
class TodoPlan(BaseModel):
    owner: str
    items: List[TodoItem]
```

## 主要機能

### 1. 基本テキスト生成
- シンプルなプロンプト→レスポンス
- 学習者向けの箇条書き回答生成

### 2. 構造化出力
- PydanticモデルによるJSONスキーマ定義
- 厳密なJSON出力の生成と検証
- マークダウンコードブロックの自動除去処理

### 3. 画像解析
- PNG/JPEG画像のBase64エンコーディング
- Claude Visionによる画像内容の詳細分析
- ファイルサイズ制限（5MB以下）の考慮

### 4. エラーハンドリング
- JSONパースエラーの捕捉
- ファイル不存在エラーの処理
- Pydanticバリデーションエラーの処理

## 制限事項と代替手段

### Anthropic API で利用できない機能
1. **音声生成（TTS）**
   - 代替: Google Cloud Text-to-Speech, Azure Speech, Amazon Polly, ElevenLabs

2. **音声認識（STT）**
   - 代替: Google Cloud Speech-to-Text, Azure Speech, Amazon Transcribe, OpenAI Whisper

3. **音声翻訳**
   - 代替: OpenAI Whisper + Google Translate, Azure Translator

4. **画像生成**
   - 代替: DALL-E, Midjourney, Stable Diffusion, Adobe Firefly

## 設計パターン

### エラーハンドリングパターン
```python
try:
    # API呼び出し処理
    response = client.messages.create(...)
    # 応答処理
except (json.JSONDecodeError, ValueError) as e:
    # パース系エラー処理
except Exception as e:
    # 一般エラー処理
```

### 構造化出力パターン
```python
# 1. Pydanticモデル定義
# 2. JSON Schema生成
# 3. プロンプト内でスキーマ指定
# 4. 応答のパース・検証
```

### 画像処理パターン
```python
# 1. ファイル読み込み
# 2. Base64エンコーディング
# 3. メッセージ内でmultipart形式で送信
# 4. 応答の処理
```

## 学習目標

このノートブックを通じて以下のスキルを習得できます：

1. Anthropic API の基本的な使用方法
2. 構造化出力の実装と検証
3. 画像解析機能の活用
4. エラーハンドリングの実装
5. API制限の理解と代替手段の検討

## 拡張可能性

- より複雑なPydanticモデルの実装
- 複数画像の同時解析
- 会話履歴の管理
- 非同期処理の実装
- カスタムエラーハンドラーの作成