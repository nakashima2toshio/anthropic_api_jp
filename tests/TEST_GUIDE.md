# Anthropic APIデモ テスト実行ガイド

## 📚 目次
1. [概要](#概要)
2. [クイックスタート](#クイックスタート)
3. [テスト対象モジュール](#テスト対象モジュール)
4. [環境準備](#環境準備)
5. [テスト実行方法](#テスト実行方法)
6. [カバレージ測定](#カバレージ測定)
7. [個別モジュールテスト](#個別モジュールテスト)
8. [トラブルシューティング](#トラブルシューティング)
9. [CI/CD統合](#cicd統合)
10. [ベストプラクティス](#ベストプラクティス)

## 概要

このドキュメントは、Anthropic APIデモアプリケーションの単体テスト実行とカバレージ測定に関する包括的なガイドです。

### テスト構成
- **テストフレームワーク**: pytest
- **カバレージツール**: pytest-cov
- **モックライブラリ**: unittest.mock
- **テスト対象**: 7つのAnthropic APIデモモジュール
- **総テスト数**: 129テスト
- **実装済みテスト**: 全7モジュール（a00～a06）
- **目標カバレージ**: 40%以上

## クイックスタート

### 🚀 最速でテストを実行する

```bash
# 1. 全テスト実行（簡単）
pytest

# 2. カバレージ付きテスト（推奨）
pytest --cov --cov-report=term-missing

# 3. 個別モジュールテスト
pytest tests/unit/test_a00_responses_api.py -v

# 4. HTMLカバレージレポート
pytest --cov --cov-report=html
open htmlcov/index.html
```

### 📊 現在のテスト状況

| ステータス | 数値 |
|-----------|------|
| ✅ 実装済みモジュール | 7/7 |
| 📝 総テスト数 | 129 |
| 🎯 目標カバレージ | 40%+ |
| 📈 現在のカバレージ | 測定中 |

## テスト対象モジュール

| モジュール | 説明 | テストファイル | テスト数 | 状態 |
|-----------|------|---------------|---------|------|
| `a00_responses_api.py` | 基本的なMessages API | `test_a00_responses_api.py` | 24 | ✅ 実装済み |
| `a01_structured_outputs_parse_schema.py` | 構造化出力とスキーマ検証 | `test_a01_structured_outputs_parse_schema.py` | 19 | ✅ 実装済み |
| `a02_responses_tools_pydantic_parse.py` | PydanticツールとTool Use | `test_a02_responses_tools_pydantic_parse.py` | 18 | ✅ 実装済み |
| `a03_images_and_vision.py` | 画像処理とVision API | `test_a03_images_and_vision.py` | 17 | ✅ 実装済み |
| `a04_audio_speeches.py` | 音声処理（将来対応） | `test_a04_audio_speeches.py` | 17 | ✅ 実装済み |
| `a05_conversation_state.py` | 会話状態管理 | `test_a05_conversation_state.py` | 18 | ✅ 実装済み |
| `a06_reasoning_chain_of_thought.py` | Chain of Thought推論 | `test_a06_reasoning_chain_of_thought.py` | 16 | ✅ 実装済み |

## 環境準備

### 1. 必要なパッケージのインストール

```bash
# テスト関連パッケージのインストール
pip install pytest pytest-cov pytest-mock pytest-benchmark

# または requirements.txt から
pip install -r requirements.txt
```

### 2. 環境変数の設定

```bash
# Anthropic APIキー（テストではモックされるため任意）
export ANTHROPIC_API_KEY='your-api-key-here'

# その他のAPI（オプション）
export OPENWEATHER_API_KEY='your-weather-api-key'
export EXCHANGERATE_API_KEY='your-exchange-api-key'
```

### 3. プロジェクト構造の確認

```
anthropic_api_jp/
├── a00_responses_api.py
├── a01_structured_outputs_parse_schema.py
├── a02_responses_tools_pydantic_parse.py
├── a03_images_and_vision.py
├── a04_audio_speeches.py
├── a05_conversation_state.py
├── a06_reasoning_chain_of_thought.py
├── helper_api.py
├── helper_st.py
├── config.yml
├── pytest.ini
└── tests/
    ├── TEST_GUIDE.md
    ├── INDIVIDUAL_TEST_GUIDE.md
    └── unit/
        ├── test_a00_responses_api.py
        ├── test_a01_structured_outputs_parse_schema.py
        ├── test_a02_responses_tools_pydantic_parse.py
        ├── test_a03_images_and_vision.py
        ├── test_a04_audio_speeches.py
        ├── test_a05_conversation_state.py
        └── test_a06_reasoning_chain_of_thought.py
```

## テスト実行方法

### 方法1: 基本的なコマンドライン実行

#### 全テスト実行
```bash
# 詳細出力付き
python -m pytest tests/unit/test_a0*.py -v

# 簡潔な出力
python -m pytest tests/unit/test_a0*.py -q

# エラー詳細表示なし
python -m pytest tests/unit/test_a0*.py --tb=no
```

#### 特定パターンのテスト実行
```bash
# a00-a06のテストのみ
python -m pytest tests/unit/test_a0[0-6]*.py -v

# 特定のテストクラス
python -m pytest tests/unit/test_a00_responses_api.py::TestTextResponseDemo -v

# 特定のテストメソッド
python -m pytest tests/unit/test_a00_responses_api.py::TestTextResponseDemo::test_text_response_demo_run -v
```

### 方法2: Makefileを使用（推奨）

Makefileを作成して使用：

```makefile
# Makefile.test
.PHONY: test test-coverage test-html test-a00 clean

test:
	pytest tests/unit/ -v

test-coverage:
	pytest tests/unit/ --cov --cov-report=term-missing

test-html:
	pytest tests/unit/ --cov --cov-report=html
	open htmlcov/index.html

test-a00:
	pytest tests/unit/test_a00_responses_api.py -v

clean:
	rm -rf .pytest_cache
	rm -rf htmlcov
	rm -f .coverage
	find . -type d -name __pycache__ -exec rm -rf {} +
```

```bash
# 使用例
make -f Makefile.test test
make -f Makefile.test test-coverage
make -f Makefile.test test-html
```

### 方法3: pytest.iniを活用

`pytest.ini`ファイルで設定済みのオプション：
```ini
[pytest]
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
addopts = -v --tb=short --strict-markers
markers =
    unit: Unit tests
    integration: Integration tests
    slow: Slow running tests
    api: API tests
    ui: UI tests
    functional: Functional tests
    performance: Performance tests
```

マーカーを使用したテスト:
```bash
# 単体テストのみ
pytest -m unit

# 統合テストのみ
pytest -m integration

# APIテストのみ
pytest -m api
```

## カバレージ測定

### 基本的なカバレージ測定

```bash
# ターミナルにカバレージ表示
python -m pytest tests/unit/test_a00_responses_api.py \
  --cov=a00_responses_api \
  --cov-report=term
```

### 詳細なカバレージレポート

```bash
# 未カバー行を表示
python -m pytest tests/unit/test_a00_responses_api.py \
  --cov=a00_responses_api \
  --cov-report=term-missing
```

### HTMLカバレージレポート

```bash
# HTMLレポート生成
python -m pytest tests/unit/test_a00_responses_api.py \
  --cov=a00_responses_api \
  --cov-report=html

# レポートを開く
open htmlcov/index.html  # macOS
xdg-open htmlcov/index.html  # Linux
start htmlcov/index.html  # Windows
```

### XMLカバレージレポート（CI/CD用）

```bash
python -m pytest tests/unit/test_a00_responses_api.py \
  --cov=a00_responses_api \
  --cov-report=xml
```

### カバレージ閾値の設定

```bash
# 最低80%のカバレージを要求
python -m pytest tests/unit/test_a00_responses_api.py \
  --cov=a00_responses_api \
  --cov-fail-under=80
```

## 個別モジュールテスト

### a00_responses_api.py

```bash
# テスト実行
python -m pytest tests/unit/test_a00_responses_api.py -v

# カバレージ付き
python -m pytest tests/unit/test_a00_responses_api.py \
  --cov=a00_responses_api \
  --cov-report=term-missing

# 特定のデモクラスのみ
python -m pytest tests/unit/test_a00_responses_api.py::TestTextResponseDemo -v
```

### 他のモジュール（実装済み）

```bash
# a01_structured_outputs_parse_schema.py
python -m pytest tests/unit/test_a01_structured_outputs_parse_schema.py -v

# a02_responses_tools_pydantic_parse.py
python -m pytest tests/unit/test_a02_responses_tools_pydantic_parse.py -v

# a03_images_and_vision.py
python -m pytest tests/unit/test_a03_images_and_vision.py -v

# a04_audio_speeches.py
python -m pytest tests/unit/test_a04_audio_speeches.py -v

# a05_conversation_state.py
python -m pytest tests/unit/test_a05_conversation_state.py -v

# a06_reasoning_chain_of_thought.py
python -m pytest tests/unit/test_a06_reasoning_chain_of_thought.py -v
```

## トラブルシューティング

### よくある問題と解決方法

#### 1. ImportError: モジュールが見つからない

```bash
# PYTHONPATHを設定
export PYTHONPATH=$PYTHONPATH:$(pwd)

# または pytest実行時に指定
python -m pytest tests/unit/ --import-mode=importlib
```

#### 2. StreamlitAPIException

```python
# テストではStreamlitのページ設定が重複してエラーになる場合がある
# setup_page_config()の実装で既にtry-exceptで処理済み
```

#### 3. セッション状態のエラー

```python
# st.session_stateに必要なキーを事前に設定
mock_streamlit.session_state = {
    "performance_metrics": {},
    "messages_demo_name": []
}
```

#### 4. カバレージが低い

```bash
# 詳細な未カバー行を確認
python -m pytest tests/unit/test_a00_responses_api.py \
  --cov=a00_responses_api \
  --cov-report=term-missing

# HTMLレポートで視覚的に確認
python -m pytest tests/unit/test_a00_responses_api.py \
  --cov=a00_responses_api \
  --cov-report=html
```

### デバッグオプション

```bash
# デバッグ出力を有効化
python -m pytest tests/unit/ -vv -s

# 最初のエラーで停止
python -m pytest tests/unit/ -x

# 失敗したテストのみ再実行
python -m pytest tests/unit/ --lf

# pdbデバッガを起動
python -m pytest tests/unit/ --pdb
```

## CI/CD統合

### GitHub Actions設定例

`.github/workflows/test.yml`:
```yaml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    
    steps:
    - uses: actions/checkout@v2
    
    - name: Set up Python
      uses: actions/setup-python@v2
      with:
        python-version: '3.12'
    
    - name: Install dependencies
      run: |
        pip install -r requirements.txt
    
    - name: Run tests with coverage
      run: |
        python -m pytest tests/unit/ \
          --cov=a00_responses_api \
          --cov=a01_structured_outputs_parse_schema \
          --cov=a02_responses_tools_pydantic_parse \
          --cov=a03_images_and_vision \
          --cov=a04_audio_speeches \
          --cov=a05_conversation_state \
          --cov=a06_reasoning_chain_of_thought \
          --cov-report=xml \
          --cov-report=term
    
    - name: Upload coverage to Codecov
      uses: codecov/codecov-action@v2
      with:
        file: ./coverage.xml
```

### GitLab CI設定例

`.gitlab-ci.yml`:
```yaml
test:
  stage: test
  script:
    - pip install -r requirements.txt
    - python -m pytest tests/unit/ --cov --cov-report=xml
  coverage: '/TOTAL.*\s+(\d+%)$/'
  artifacts:
    reports:
      coverage_report:
        coverage_format: cobertura
        path: coverage.xml
```

## 現在のテストステータス

| モジュール | テスト数 | 実装状態 | 目標カバレージ |
|-----------|---------|----------|---------------|
| a00_responses_api | 24 | ✅ 実装済み | 40% |
| a01_structured_outputs_parse_schema | 19 | ✅ 実装済み | 50% |
| a02_responses_tools_pydantic_parse | 18 | ✅ 実装済み | 45% |
| a03_images_and_vision | 17 | ✅ 実装済み | 60% |
| a04_audio_speeches | 17 | ✅ 実装済み | 40% |
| a05_conversation_state | 18 | ✅ 実装済み | 50% |
| a06_reasoning_chain_of_thought | 16 | ✅ 実装済み | 85% |
| **合計** | **129** | **7/7** | **40%+** |

## ベストプラクティス

### 1. テスト実行前の確認
- 環境変数が設定されているか確認
- 依存パッケージがインストールされているか確認
- プロジェクトルートディレクトリから実行

### 2. 定期的なテスト実行
- コード変更前後でテスト実行
- プルリクエスト前に全テスト実行
- カバレージレポートの定期確認

### 3. テストの保守
- 新機能追加時は必ずテスト追加
- テスト失敗時は即座に修正
- カバレージ低下を防ぐ

### 4. モック使用のガイドライン
- 外部APIは必ずモック
- ファイルI/Oは適切にモック
- Streamlitコンポーネントは完全モック
- デコレータを含む関数は慎重にモック

### 5. テスト作成のポイント
- 単一責任の原則に従う
- 各テストは独立して実行可能に
- テスト名は明確で説明的に
- アサーションは明確で具体的に

## 参考リンク

- [pytest公式ドキュメント](https://docs.pytest.org/)
- [pytest-cov公式ドキュメント](https://pytest-cov.readthedocs.io/)
- [unittest.mock公式ドキュメント](https://docs.python.org/3/library/unittest.mock.html)
- [Streamlitテストガイド](https://docs.streamlit.io/library/advanced-features/testing)
- [Anthropic API ドキュメント](https://docs.anthropic.com/claude)

---

最終更新: 2025年1月14日