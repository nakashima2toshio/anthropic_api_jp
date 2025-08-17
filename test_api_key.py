#!/usr/bin/env python3
"""
Anthropic API Key Test Script
APIキーの動作確認とクレジット状況をテストするスクリプト
"""

import os
from anthropic import Anthropic

def test_anthropic_api():
    """Anthropic APIキーの動作テスト"""
    
    # 環境変数からAPIキー取得
    api_key = os.getenv('ANTHROPIC_API_KEY')
    
    if not api_key:
        print("❌ ANTHROPIC_API_KEY environment variable not found")
        print("設定方法: export ANTHROPIC_API_KEY='your-key-here'")
        return False
    
    print(f"🔑 APIキー確認: {api_key[:10]}...{api_key[-10:]}")
    
    try:
        # Anthropicクライアント初期化
        client = Anthropic(api_key=api_key)
        
        # 最小限のテストメッセージ
        print("📡 API接続テスト中...")
        response = client.messages.create(
            model="claude-3-5-haiku-20241022",
            max_tokens=10,
            messages=[
                {"role": "user", "content": "Hello"}
            ]
        )
        
        print("✅ API接続成功!")
        print(f"📝 レスポンス: {response.content[0].text}")
        
        # 使用量情報
        if hasattr(response, 'usage'):
            usage = response.usage
            print(f"💰 トークン使用量:")
            print(f"   入力: {usage.input_tokens}")
            print(f"   出力: {usage.output_tokens}")
            print(f"   合計: {usage.input_tokens + usage.output_tokens}")
        
        return True
        
    except Exception as e:
        error_msg = str(e)
        print(f"❌ API呼び出し失敗: {error_msg}")
        
        if "invalid x-api-key" in error_msg.lower():
            print("\n🔧 解決方法:")
            print("1. Anthropic Console (https://console.anthropic.com/) にアクセス")
            print("2. Billing ページでクレジット残高を確認")
            print("3. クレジットが不足している場合は購入 (最小$10程度)")
            print("4. 新しいAPIキーを生成して環境変数を更新")
            
        elif "credit" in error_msg.lower() or "billing" in error_msg.lower():
            print("\n💳 クレジット不足の可能性:")
            print("Anthropic Console の Billing ページでクレジットを購入してください")
            
        return False

if __name__ == "__main__":
    print("🧪 Anthropic API Key Test Script")
    print("=" * 50)
    
    success = test_anthropic_api()
    
    if success:
        print("\n🎉 APIキーは正常に動作しています！")
    else:
        print("\n⚠️  APIキーの設定に問題があります")
        print("上記の解決方法を試してください")