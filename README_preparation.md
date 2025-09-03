### Preparation for development

#### この開発環境
- (1) Macbook M2 - 24Gメモリ
- (2) 開発環境 - PyCharm professional
              - Github
- (3) AI - Anthropic - Claude Code, Anthropic API, Claude for Macbook  
- (4) AI - OpenAI API, ChatGPT Pro（参考比較用）


#### (1) Pay for Anthropic API key

- Credit balance: anthropicのAPIを利用するため(Tier2の権限で、$40支払う)
- https://console.anthropic.com/settings/billing

### (2) anthropic API key を取得する

- https://console.anthropic.com/settings/keys

#### (3) Set environment variables for Anthropic API key

```bash
# 1) .zshrc に追記（手でキーを入れる簡単版）
cat >> ~/.zshrc <<'EOF'
# Anthropic API key
export ANTHROPIC_API_KEY="sk-ant-ここにキー"
EOF

# 2) 反映
source ~/.zshrc   # または  exec zsh -l
# 3) 確認
echo "$ANTHROPIC_API_KEY"
```

### (4) セットアップ

```bash
# 1. リポジトリクローン
git clone https://github.com/nakashima2toshio/anthropic_api_jp.git
cd anthropic_api_jp

# 2. 依存関係インストール
pip install -r requirements.txt

# 3. 環境変数設定
export ANTHROPIC_API_KEY='your-api-key'

# 4. 実行
streamlit run a00_responses_api.py
```
