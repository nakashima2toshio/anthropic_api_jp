# CLAUDE_jp.md

このファイルは、リポジトリでコードを操作する際に Claude Code (claude.ai/code) にガイダンスを提供します。

## プロジェクト概要

これは、Anthropic API のデモンストレーションと学習プロジェクトで、Claude API のさまざまな機能を包括的に紹介する Python サンプル集です。テキスト生成、構造化出力、画像処理、音声処理、会話管理、思考の連鎖推論を実演するインタラクティブな Streamlit アプリケーションが含まれています。

## 開発コマンド

### アプリケーションの実行
```bash
# メイン統合デモ
streamlit run a00_responses_api.py --server.port=8501

# 構造化出力デモ
streamlit run a01_structured_outputs_parse_schema.py --server.port=8501

# Tools・Pydantic Parse デモ
streamlit run a02_responses_tools_pydantic_parse.py --server.port=8502

# 画像・ビジョンデモ
streamlit run a03_images_and_vision.py --server.port=8503

# 音声処理デモ
streamlit run a04_audio_speeches.py --server.port=8504

# 会話状態管理デモ
streamlit run a05_conversation_state.py --server.port=8505

# Chain of Thought デモ
streamlit run a06_reasoning_chain_of_thought.py --server.port=8506
```

### テスト実行　（注）テストは、また、実装されていません。
```bash
# 詳細表示ですべてのテストを実行
pytest -v

# カバレッジ付きでテストを実行
pytest --cov

# 特定のテストカテゴリを実行（pytest.ini で定義）
pytest -m unit      # 単体テスト
pytest -m api       # API テスト
pytest -m slow      # 実行時間の長いテスト
pytest -m integration  # 統合テスト
pytest -m ui           # UI テスト
pytest -m functional   # 機能テスト
pytest -m performance  # パフォーマンステスト
```

### 環境セットアップ
```bash
# 依存関係のインストール
pip install -r requirements.txt

# 必須の環境変数
export ANTHROPIC_API_KEY='your-anthropic-api-key'

# オプション（特定のデモで使用）
export OPENWEATHER_API_KEY='your-openweather-api-key'
export EXCHANGERATE_API_KEY='your-exchangerate-api-key'
```

## コードアーキテクチャ

### コアヘルパーモジュール
- **`helper_api.py`**: クライアント管理、トークン数カウント、レスポンス処理、設定管理を含む統一 Anthropic API ラッパー
- **`helper_st.py`**: 全デモで一貫したユーザーインターフェースを提供する Streamlit UI コンポーネントとセッション状態管理

### 設定システム
- **`config.yml`**: 以下を含む中央設定ファイル：
  - モデル定義とカテゴリ分類（flagship、balanced、fast、vision、coding）
  - コスト追跡のための料金情報
  - API設定（タイムアウト、リトライ、制限）
  - UI設定と国際化
  - ログ設定

### デモアプリケーション構造
各デモは一貫したパターンに従います：
1. 統一ヘルパーモジュール（`helper_api.py`、`helper_st.py`）のインポート
2. セッション状態と設定の初期化
3. ヘルパークラスを使用した UI コンポーネントのレンダリング
4. 中央集約クライアント経由での API 呼び出し処理
5. 一貫したフォーマットでの結果表示

### 主要クラスとコンポーネント

#### ConfigManager (helper_api.py)
- 設定管理のためのシングルトンパターン
- 環境変数サポート付きの YAML ベース設定
- モデルカテゴリ分類と料金情報

#### AnthropicClient (helper_api.py)
- リトライロジックとエラーハンドリングを含む中央集約 API クライアント
- トークンカウントとコスト見積もり
- レスポンス処理とキャッシング

#### UIHelper クラス (helper_st.py)
- `MessageManagerUI`: 会話履歴表示
- `ResponseProcessorUI`: API レスポンスフォーマット
- `SessionStateManager`: 永続状態管理
- `InfoPanelManager`: 標準化された情報パネル

### データ管理
- **`data/`**: テスト用サンプルファイル（画像、音声、テキスト、JSON データ）
- **`utils/`**: データ処理、ウェブスクレイピング、API インタラクション用のユーティリティスクリプト

### ドキュメント
- **`doc/`**: API 使用パターン、テスト計画、ヘルパー関数リファレンスを含む包括的なドキュメント
- **`README.md`**: 機能説明とセットアップ手順を含むプロジェクト概要

## 開発パターン

### エラーハンドリング
すべての API 呼び出しは、フォールバック機能と日本語・英語両対応のユーザーフレンドリーなエラーメッセージを含む一貫したエラーハンドリングパターンを使用します。

### セッション状態管理
Streamlit のセッション状態は `SessionStateManager` を通じて中央管理され、ページリフレッシュ間での会話履歴、API レスポンス、ユーザー設定を維持します。

### API レスポンス処理
レスポンスは以下を処理する `ResponseProcessor` クラスを通じて処理されます：
- トークンカウントとコスト計算
- レスポンスフォーマットと検証
- 重複リクエストのキャッシング
- 構造化出力パース

### 設定駆動開発
モデル、API 設定、UI 設定は `config.yml` で設定され、以下が容易になります：
- 異なる Claude モデル間の切り替え
- コード変更なしでの API パラメータ調整
- 環境ごとの UI 動作カスタマイズ
- 異なるモデル間での使用コスト追跡

## テストインフラストラクチャ

プロジェクトは異なるテストカテゴリ用のカスタムマーカーを持つ pytest を使用します：
- `unit`: 基本機能テスト
- `integration`: マルチコンポーネントテスト
- `api`: API 呼び出しが必要なテスト
- `ui`: ユーザーインターフェーステスト
- `functional`: エンドツーエンド機能テスト
- `performance`: パフォーマンスベンチマークテスト
- `slow`: 時間集約型テスト

テスト設定は特定のテストパスと出力フォーマットで `pytest.ini` を通じて管理されます。

## 日本語対応機能

### 国際化設定
- `config.yml` の `i18n` セクションでデフォルト言語を「ja」に設定
- エラーメッセージの日本語対応（`error_messages.ja`）
- UI ラベルとメッセージの日本語表示

### サンプルデータ
- 日本語テキストファイル（竹取物語、月の沙漠など）
- 日本の都市リスト（`city_jp.list.json`）
- 日本語レビューデータ（`reviews_1k.csv`）

### プロンプト例
設定ファイルには日本語プロンプトの例が含まれています：
- `creative_writing`: "日本語で創作的な物語を書いてください。"
- `coding_help`: "Pythonでデータ分析のコードを書いてください。"
- `analysis`: "この画像を分析して説明してください。"