# Anthropic API デモ 個別モジュールテストガイド

# 2. カバレージ付きテスト（ALL Test）

pytest --cov --cov-report=term-missing

## 🚀 クイックテストコマンド

### カバレージ付きテスト実行

```bash
# a00_responses_api.py
python -m pytest tests/unit/test_a00_responses_api.py \
  --cov=a00_responses_api \
  --cov-report=term-missing

# a01_structured_outputs_parse_schema.py
python -m pytest tests/unit/test_a01_structured_outputs_parse_schema.py \
  --cov=a01_structured_outputs_parse_schema \
  --cov-report=term-missing

# a02_responses_tools_pydantic_parse.py
python -m pytest tests/unit/test_a02_responses_tools_pydantic_parse.py \
  --cov=a02_responses_tools_pydantic_parse \
  --cov-report=term-missing

# a03_images_and_vision.py
python -m pytest tests/unit/test_a03_images_and_vision.py \
  --cov=a03_images_and_vision \
  --cov-report=term-missing

# a04_audio_speeches.py
python -m pytest tests/unit/test_a04_audio_speeches.py \
  --cov=a04_audio_speeches \
  --cov-report=term-missing

# a05_conversation_state.py
python -m pytest tests/unit/test_a05_conversation_state.py \
  --cov=a05_conversation_state \
  --cov-report=term-missing

# a06_reasoning_chain_of_thought.py
python -m pytest tests/unit/test_a06_reasoning_chain_of_thought.py \
  --cov=a06_reasoning_chain_of_thought \
  --cov-report=term-missing
```

## 📚 目次

1. [a00_responses_api.py テストガイド](#a00_responses_apipy-テストガイド)
2. [a01_structured_outputs_parse_schema.py テストガイド](#a01_structured_outputs_parse_schemapy-テストガイド)
3. [a02_responses_tools_pydantic_parse.py テストガイド](#a02_responses_tools_pydantic_parsepy-テストガイド)
4. [a03_images_and_vision.py テストガイド](#a03_images_and_visionpy-テストガイド)
5. [a04_audio_speeches.py テストガイド](#a04_audio_speechespy-テストガイド)
6. [a05_conversation_state.py テストガイド](#a05_conversation_statepy-テストガイド)
7. [a06_reasoning_chain_of_thought.py テストガイド](#a06_reasoning_chain_of_thoughtpy-テストガイド)

---

## a00_responses_api.py テストガイド

### モジュール概要

基本的なAnthropic Messages APIの使用例を実装したデモモジュール

### テスト構成

- **テストファイル**: `tests/unit/test_a00_responses_api.py`
- **テスト数**: 24
- **カバレージ**: 28%
- **成功率**: 58% (14/24)

### テストクラス一覧


| クラス名                 | テスト内容                 | テスト数 | 状態 |
| ------------------------ | -------------------------- | -------- | ---- |
| TestPageConfig           | ページ設定のテスト         | 2        | 1/2  |
| TestCommonUI             | 共通UI関数のテスト         | 2        | ✅   |
| TestBaseDemo             | 基底クラスのテスト         | 3        | 2/3  |
| TestTextResponseDemo     | テキスト応答デモのテスト   | 2        | ❌   |
| TestMemoryResponseDemo   | メモリ応答デモのテスト     | 2        | 1/2  |
| TestImageResponseDemo    | 画像応答デモのテスト       | 2        | 1/2  |
| TestStructuredOutputDemo | 構造化出力デモのテスト     | 2        | 1/2  |
| TestWeatherDemo          | 天気APIデモのテスト        | 3        | 1/3  |
| TestDemoManager          | デモマネージャーのテスト   | 3        | ✅   |
| TestMainApp              | メインアプリのテスト       | 1        | ✅   |
| TestErrorHandling        | エラーハンドリングのテスト | 1        | ✅   |
| TestIntegration          | 統合テスト                 | 1        | ❌   |

### 実行コマンド

```bash
# 基本実行
python -m pytest tests/unit/test_a00_responses_api.py -v

# カバレージ付き
python -m pytest tests/unit/test_a00_responses_api.py \
  --cov=a00_responses_api \
  --cov-report=term-missing

# 特定のクラスのみ
python -m pytest tests/unit/test_a00_responses_api.py::TestTextResponseDemo -v

# 特定のテストのみ
python -m pytest tests/unit/test_a00_responses_api.py::TestBaseDemo::test_base_demo_initialization -v
```

### 主要なモック対象

- Streamlitコンポーネント（st.button, st.text_area, st.write等）
- Anthropic APIクライアント（messages.create）
- 外部API（OpenWeatherMap, ExchangeRate）
- ヘルパーモジュール（helper_api, helper_st）

### テストのポイント

1. **API呼び出しの検証**: create_messageが正しいパラメータで呼ばれているか
2. **UI表示の検証**: Streamlitコンポーネントが適切に呼ばれているか
3. **エラーハンドリング**: API例外時の処理が適切か
4. **セッション管理**: Streamlitセッション状態が正しく管理されているか

### 既知の問題と改善点

- デコレータ（@error_handler_ui, @timer_ui）のモックが不完全
- 一部のデモクラスのrun()メソッドの複雑なロジックのテストが困難
- セッション状態のperformance_metricsへの依存

---

## a01_structured_outputs_parse_schema.py テストガイド

### モジュール概要

構造化出力とスキーマ検証を使用したデモモジュール（Anthropic API版）

### テスト構成

- **テストファイル**: `tests/unit/test_a01_structured_outputs_parse_schema.py`
- **テスト数**: 19
- **カバレージ**: 目標50%以上
- **状態**: ✅ 実装済み

### テストクラス一覧


| クラス名                 | テスト内容             | テスト数 | 状態 |
| ------------------------ | ---------------------- | -------- | ---- |
| TestPageConfig           | ページ設定のテスト     | 2        | ✅   |
| TestPydanticModels       | Pydanticモデルのテスト | 3        | ✅   |
| TestStructuredOutputDemo | 構造化出力デモのテスト | 4        | ✅   |
| TestDemoScenarios        | デモシナリオのテスト   | 3        | ✅   |
| TestMainApp              | メインアプリのテスト   | 2        | ✅   |
| TestIntegration          | 統合テスト             | 1        | ✅   |

### Pydanticモデル一覧

- ArticleAnalysis（記事分析）
- Product（製品情報）
- ProductCatalog（製品カタログ）
- Address（住所）
- UserInfo（ユーザー情報）

### 実行コマンド

```bash
# 基本実行
python -m pytest tests/unit/test_a01_structured_outputs_parse_schema.py -v

# カバレージ付き
python -m pytest tests/unit/test_a01_structured_outputs_parse_schema.py \
  --cov=a01_structured_outputs_parse_schema \
  --cov-report=term-missing

# Pydanticモデル関連のテストのみ
python -m pytest tests/unit/test_a01_structured_outputs_parse_schema.py -k "pydantic" -v

# スキーマ検証テストのみ
python -m pytest tests/unit/test_a01_structured_outputs_parse_schema.py -k "schema" -v
```

### Pydanticモデル一覧

- EventInfo（イベント情報）
- MathReasoning（数学的推論）
- DynamicUI（動的UI定義）
- EntityInfo（エンティティ情報）
- ConditionalOutput（条件付き出力）
- ModerationResult（モデレーション結果）

### テストのポイント

1. **Pydanticモデルの検証**: スキーマに従った構造化データの生成
2. **JSON解析**: 構造化レスポンスのJSON解析
3. **スキーマ適合性**: 出力がスキーマに適合しているか

---

## a02_responses_tools_pydantic_parse.py テストガイド

### モジュール概要

Pydanticツールと関数呼び出し（Tool Use）を使用したデモモジュール

### テスト構成

- **テストファイル**: `tests/unit/test_a02_responses_tools_pydantic_parse.py`
- **テスト数**: 18
- **カバレージ**: 目標45%以上
- **状態**: ✅ 実装済み

### テストクラス一覧


| クラス名            | テスト内容                 | テスト数 | 状態 |
| ------------------- | -------------------------- | -------- | ---- |
| TestPageConfig      | ページ設定のテスト         | 1        | ✅   |
| TestToolDefinitions | ツール定義のテスト         | 3        | ✅   |
| TestPydanticModels  | Pydanticモデルのテスト     | 3        | ✅   |
| TestToolHandlers    | ツールハンドラーのテスト   | 3        | ✅   |
| TestToolsDemo       | ToolsDemoクラスのテスト    | 2        | ✅   |
| TestDemoScenarios   | デモシナリオのテスト       | 4        | ✅   |
| TestErrorHandling   | エラーハンドリングのテスト | 2        | ✅   |
| TestMainApp         | メインアプリのテスト       | 2        | ✅   |
| TestIntegration     | 統合テスト                 | 1        | ✅   |

### ツール定義一覧

- weather_tool（天気情報取得）
- calculator_tool（計算機）
- search_tool（検索）

### Pydanticモデル一覧

- WeatherResponse（天気レスポンス）
- CalculationResult（計算結果）
- SearchResult（検索結果）
- SearchResults（検索結果リスト）

### テストのポイント

1. **Tool定義の検証**: Pydanticモデルからツール定義生成
2. **関数呼び出しの検証**: ツール実行とレスポンス処理
3. **ネスト構造の処理**: 複雑なデータ構造の検証

---

## a03_images_and_vision.py テストガイド

### モジュール概要

画像処理とVision機能を使用したデモモジュール（Anthropic Claude Vision）

### テスト構成

- **テストファイル**: `tests/unit/test_a03_images_and_vision.py`
- **テスト数**: 17
- **カバレージ**: 目標60%以上
- **状態**: ✅ 実装済み

### テストクラス一覧


| クラス名            | テスト内容                     | テスト数 | 状態 |
| ------------------- | ------------------------------ | -------- | ---- |
| TestPageConfig      | ページ設定のテスト             | 1        | ✅   |
| TestImageUtilities  | 画像処理ユーティリティのテスト | 3        | ✅   |
| TestImageVisionDemo | ImageVisionDemoクラスのテスト  | 2        | ✅   |
| TestDemoScenarios   | デモシナリオのテスト           | 4        | ✅   |
| TestErrorHandling   | エラーハンドリングのテスト     | 3        | ✅   |
| TestMainApp         | メインアプリのテスト           | 2        | ✅   |
| TestIntegration     | 統合テスト                     | 1        | ✅   |

### API使用一覧

- **Vision API**: 画像からテキスト生成（messages.create with image content）
- **画像入力形式**: URL、Base64エンコード、ローカルファイル
- **複数画像処理**: 複数画像の同時分析

### テストのポイント

1. **Base64エンコード**: 画像ファイルのBase64変換処理
2. **画像URL処理**: URL画像の取得と処理
3. **マルチモーダル入力**: テキストと画像の組み合わせ

---

## a04_audio_speeches.py テストガイド

### モジュール概要

音声処理機能のデモモジュール（将来的な音声機能対応準備）

### テスト構成

- **テストファイル**: `tests/unit/test_a04_audio_speeches.py`
- **テスト数**: 17
- **カバレージ**: 目標40%以上
- **状態**: ✅ 実装済み

### テストクラス一覧


| クラス名              | テスト内容                      | テスト数 | 状態 |
| --------------------- | ------------------------------- | -------- | ---- |
| TestPageConfig        | ページ設定のテスト              | 1        | ✅   |
| TestAudioUtilities    | 音声処理ユーティリティのテスト  | 3        | ✅   |
| TestAudioSpeechesDemo | AudioSpeechesDemoクラスのテスト | 2        | ✅   |
| TestDemoScenarios     | デモシナリオのテスト            | 4        | ✅   |
| TestErrorHandling     | エラーハンドリングのテスト      | 3        | ✅   |
| TestMainApp           | メインアプリのテスト            | 2        | ✅   |
| TestIntegration       | 統合テスト                      | 1        | ✅   |

### 機能一覧

- **音声入力処理**: 音声ファイルの処理準備
- **テキスト変換**: 音声からテキストへの変換準備
- **メディア処理**: 音声データの管理

### テストのポイント

1. **ファイル処理**: 音声ファイルのアップロードと検証
2. **データ変換**: 音声データの形式変換
3. **UI統合**: Streamlitでのメディア表示

---

## a05_conversation_state.py テストガイド

### モジュール概要

会話状態管理と継続的な会話を実装したデモモジュール

### テスト構成

- **テストファイル**: `tests/unit/test_a05_conversation_state.py`
- **テスト数**: 18
- **カバレージ**: 目標50%以上
- **状態**: ✅ 実装済み

### テストクラス一覧


| クラス名                  | テスト内容                          | テスト数 | 状態 |
| ------------------------- | ----------------------------------- | -------- | ---- |
| TestPageConfig            | ページ設定のテスト                  | 1        | ✅   |
| TestConversationUtilities | 会話状態管理ユーティリティのテスト  | 3        | ✅   |
| TestConversationStateDemo | ConversationStateDemoクラスのテスト | 2        | ✅   |
| TestDemoScenarios         | デモシナリオのテスト                | 4        | ✅   |
| TestStateManagement       | 状態管理機能のテスト                | 2        | ✅   |
| TestErrorHandling         | エラーハンドリングのテスト          | 2        | ✅   |
| TestMainApp               | メインアプリのテスト                | 2        | ✅   |
| TestIntegration           | 統合テスト                          | 1        | ✅   |

### 主要機能

- **会話履歴管理**: 複数ターンの会話保持
- **コンテキスト管理**: 会話コンテキストの維持
- **状態永続化**: セッション間での状態保存

### テストのポイント

1. **会話継続性**: メッセージ履歴が正しく維持されているか
2. **状態管理**: Streamlitセッション状態の確認
3. **メモリ管理**: 長い会話でのメモリ効率

---

## a06_reasoning_chain_of_thought.py テストガイド

### モジュール概要

Chain of Thought（CoT）推論パターンを実装したデモモジュール

### テスト構成

- **テストファイル**: `tests/unit/test_a06_reasoning_chain_of_thought.py`
- **テスト数**: 16
- **カバレージ**: 目標85%以上
- **状態**: ✅ 実装済み

### テストクラス一覧


| クラス名                    | テスト内容                       | テスト数 | 状態 |
| --------------------------- | -------------------------------- | -------- | ---- |
| TestPageConfig              | ページ設定のテスト               | 1        | ✅   |
| TestChainOfThoughtUtilities | CoT処理ユーティリティのテスト    | 3        | ✅   |
| TestChainOfThoughtDemo      | ChainOfThoughtDemoクラスのテスト | 2        | ✅   |
| TestDemoScenarios           | デモシナリオのテスト             | 4        | ✅   |
| TestErrorHandling           | エラーハンドリングのテスト       | 2        | ✅   |
| TestMainApp                 | メインアプリのテスト             | 2        | ✅   |
| TestIntegration             | 統合テスト                       | 1        | ✅   |

### 推論パターン一覧

1. **Step-by-Step Reasoning**: 段階的推論
2. **Hypothesis-Test**: 仮説検証推論
3. **Tree of Thought**: 思考の木（分岐探索）
4. **Pros-Cons-Decision**: 賛否比較決定
5. **Plan-Execute-Reflect**: 計画実行振り返り

### テストのポイント

1. **システムプロンプト検証**: 各推論パターンの指示内容確認
2. **構造化出力**: セクション分けされた出力形式
3. **推論の品質**: 論理的な推論が行われているか

---

## 共通テストパターン

### Streamlitコンポーネントのモック

```python
@patch('streamlit.button')
@patch('streamlit.text_area')
def test_ui_components(mock_text_area, mock_button):
    mock_text_area.return_value = "Test input"
    mock_button.return_value = True
    # テスト実行
```

### Anthropic APIのモック

```python
def test_api_call(demo_instance):
    mock_response = MagicMock()
    mock_response.id = "msg_test_id"
    demo_instance.client.create_message.return_value = mock_response
    # テスト実行
```

### エラーハンドリングのテスト

```python
@patch('streamlit.error')
def test_error_handling(mock_error):
    demo.client.create_message.side_effect = Exception("API Error")
    # エラー処理のテスト
    mock_error.assert_called()
```

## トラブルシューティング

### よくある問題

1. **ImportError**:

   - 解決: `export PYTHONPATH=$PYTHONPATH:$(pwd)`
2. **モックの不具合**:

   - 解決: `@patch`の順序を確認（下から上へ適用）
3. **セッション状態エラー**:

   - 解決: `st.session_state`に必要なキーを事前に設定
4. **デコレータのモック**:

   - 解決: デコレータを含む関数全体をモック
5. **カバレージが低い**:

   - 解決: `--cov-report=term-missing`で未カバー行を確認

## ベストプラクティス

1. **モックの階層化**: 必要最小限のモックから始めて段階的に追加
2. **フィクスチャの活用**: 共通のセットアップをフィクスチャ化
3. **アサーションの明確化**: 何をテストしているか明確にする
4. **エッジケースのカバー**: 正常系だけでなく異常系もテスト
5. **ドキュメントの充実**: テストの意図を明確に記述

## まとめ

各モジュールは独自の特徴とテスト要件を持っています：

- **a00**: 基本的なAPI使用（最も基礎的）
- **a01**: 構造化出力とスキーマ検証（JSON処理重視） ✅ 実装済み
- **a02**: Tool Use（関数呼び出し） ✅ 実装済み
- **a03**: 画像処理（マルチモーダル） ✅ 実装済み
- **a04**: 音声処理準備（将来対応） ✅ 実装済み
- **a05**: 会話管理（ステート管理） ✅ 実装済み
- **a06**: 推論パターン（高度な推論） ✅ 実装済み

各モジュールのテストは独立して実行可能で、特定の機能に焦点を当てたテストが可能です。

---

最終更新: 2025年1月14日
