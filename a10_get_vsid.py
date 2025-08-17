# streamlit run a10_get_vsid.py
# 最新Vector Store選択システム（作成日時順ソート）
# a30_30_rag_search.py から抜き出し・改良版
# ==================================================

import streamlit as st
import json
import logging
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
from pathlib import Path
from openai import OpenAI

# ログ設定
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class LatestVectorStoreSelector:
    """最新Vector Store選択管理クラス"""

    def __init__(self, openai_client: OpenAI = None):
        """
        初期化

        Args:
            openai_client: OpenAI APIクライアント
        """
        self.openai_client = openai_client or OpenAI()
        self.cache = {}
        self.cache_timestamp = None
        self.cache_ttl_seconds = 300  # 5分間キャッシュ

    def fetch_all_vector_stores(self) -> List[Dict[str, Any]]:
        """
        OpenAI APIから全Vector Store一覧を取得

        Returns:
            Vector Store一覧（詳細情報付き）
        """
        try:
            logger.info("📡 OpenAI APIからVector Store一覧を取得中...")

            # OpenAI APIから一覧取得
            stores_response = self.openai_client.vector_stores.list()

            if not stores_response.data:
                logger.warning("⚠️ Vector Storeが見つかりませんでした")
                return []

            # 詳細情報を含む辞書リストに変換
            stores_list = []
            for store in stores_response.data:
                store_info = {
                    "id"                  : store.id,
                    "name"                : store.name,
                    "created_at"          : getattr(store, 'created_at', 0),
                    "file_counts"         : getattr(store.file_counts, 'total', 0) if hasattr(store,
                                                                                              'file_counts') and store.file_counts else 0,
                    "usage_bytes"         : getattr(store, 'usage_bytes', 0),
                    "created_datetime"    : datetime.fromtimestamp(getattr(store, 'created_at', 0)),
                    "created_at_formatted": datetime.fromtimestamp(getattr(store, 'created_at', 0)).strftime(
                        "%Y-%m-%d %H:%M:%S")
                }
                stores_list.append(store_info)

            logger.info(f"✅ {len(stores_list)}個のVector Storeを取得")
            return stores_list

        except Exception as e:
            logger.error(f"❌ Vector Store一覧取得エラー: {e}")
            return []

    def sort_stores_by_creation_date(self, stores: List[Dict[str, Any]], reverse: bool = True) -> List[Dict[str, Any]]:
        """
        Vector Storeを作成日時でソート
        Args:
            stores: Vector Store一覧
            reverse: True=新しい順、False=古い順
        Returns:
            ソート済みVector Store一覧
        """
        try:
            # ★★★ 重要：作成日時でソート ★★★
            sorted_stores = sorted(
                stores,
                key=lambda x: x.get('created_at', 0),  # created_atタイムスタンプでソート
                reverse=reverse  # True=新しい順（降順）
            )

            # ソート結果をログ出力
            logger.info(f"📅 Vector Store作成日時ソート完了（{'新しい順' if reverse else '古い順'}）:")
            for i, store in enumerate(sorted_stores[:10]):  # 最初の10件のみログ
                logger.info(f"  {i + 1:2d}. {store['name']} - {store['created_at_formatted']} ({store['id']})")

            return sorted_stores

        except Exception as e:
            logger.error(f"❌ ソートエラー: {e}")
            return stores  # エラー時は元の順序を返す

    def get_latest_n_stores(self, n: int = 4, force_refresh: bool = False) -> List[Dict[str, Any]]:
        """
        最新のN個のVector Storeを取得
        Args:
            n: 取得する数（デフォルト4個）
            force_refresh: キャッシュを無視して強制更新
        Returns:
            最新N個のVector Store一覧
        """
        # キャッシュチェック
        now = datetime.now()
        if (not force_refresh and
                self.cache and
                self.cache_timestamp and
                (now - self.cache_timestamp).seconds < self.cache_ttl_seconds):
            logger.info("💾 キャッシュから最新Vector Store一覧を取得")
            return self.cache.get('latest_stores', [])[:n]

        try:
            # 1. 全Vector Store取得
            all_stores = self.fetch_all_vector_stores()

            if not all_stores:
                logger.warning("⚠️ 取得可能なVector Storeがありません")
                return []

            # 2. 作成日時でソート（新しい順）
            sorted_stores = self.sort_stores_by_creation_date(all_stores, reverse=True)

            # 3. 最新N個を選択
            latest_stores = sorted_stores[:n]

            logger.info(f"🎯 最新{n}個のVector Storeを選択:")
            for i, store in enumerate(latest_stores, 1):
                logger.info(f"  {i}. {store['name']} - {store['created_at_formatted']}")
                logger.info(f"     ID: {store['id']}")
                logger.info(f"     ファイル数: {store['file_counts']}, 使用量: {store['usage_bytes']} bytes")

            # キャッシュ更新
            self.cache = {
                'latest_stores': sorted_stores,
                'all_stores'   : all_stores
            }
            self.cache_timestamp = now

            return latest_stores

        except Exception as e:
            logger.error(f"❌ 最新Vector Store取得エラー: {e}")
            return []

    def create_selection_mapping(self, latest_stores: List[Dict[str, Any]]) -> Tuple[List[str], Dict[str, str]]:
        """
        選択用のマッピングを作成
        Args:
            latest_stores: 最新Vector Store一覧
        Returns:
            選択肢リスト, 名前→IDマッピング辞書
        """
        try:
            # 選択肢リスト（表示用）
            selection_options = []
            # 名前→IDマッピング
            name_to_id_mapping = {}

            for i, store in enumerate(latest_stores, 1):
                # 表示用の選択肢名
                display_name = f"{i}. {store['name']} ({store['created_at_formatted']})"
                selection_options.append(display_name)

                # マッピング（元の名前をキーにする）
                name_to_id_mapping[store['name']] = store['id']

            logger.info(f"✅ 選択肢作成完了: {len(selection_options)}個")
            return selection_options, name_to_id_mapping

        except Exception as e:
            logger.error(f"❌ 選択肢作成エラー: {e}")
            return [], {}

    def save_selected_stores(self, latest_stores: List[Dict[str, Any]], filepath: str = "latest_vector_stores.json"):
        """
        選択されたVector Store情報をファイルに保存
        Args:
            latest_stores: 最新Vector Store一覧
            filepath: 保存先ファイルパス
        """
        try:
            save_data = {
                "latest_vector_stores": latest_stores,
                "selection_metadata"  : {
                    "total_available": len(self.cache.get('all_stores', [])),
                    "selected_count" : len(latest_stores),
                    "updated_at"     : datetime.now().isoformat(),
                    "source"         : "LatestVectorStoreSelector",
                    "version"        : "1.0"
                }
            }

            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(save_data, f, indent=2, ensure_ascii=False, default=str)

            logger.info(f"✅ Vector Store情報を保存: {filepath}")
            return True

        except Exception as e:
            logger.error(f"❌ 保存エラー: {e}")
            return False


# ==================================================
# Streamlit UIコンポーネント
# ==================================================

def create_latest_store_selector_ui(
        selector: LatestVectorStoreSelector,
        max_stores: int = 4,
        key: str = "latest_vector_store_selection"
) -> Tuple[Optional[str], Optional[str]]:
    """
    最新Vector Store選択UI
    Args:
        selector: LatestVectorStoreSelector インスタンス
        max_stores: 最大表示数
        key: Streamlit要素のキー
    Returns:
        (選択された名前, 選択されたID)
    """
    st.subheader(f"🔗 最新Vector Store選択（上位{max_stores}個）")

    # 強制リフレッシュボタン
    col1, col2 = st.columns([3, 1])
    with col2:
        force_refresh = st.button("🔄 最新情報取得", type="secondary")

    try:
        # 最新Vector Store取得
        with st.spinner("最新Vector Store情報を取得中..."):
            latest_stores = selector.get_latest_n_stores(n=max_stores, force_refresh=force_refresh)

        if not latest_stores:
            st.error("❌ 利用可能なVector Storeが見つかりません")
            return None, None

        # 選択肢とマッピングを作成
        selection_options, name_to_id_mapping = selector.create_selection_mapping(latest_stores)

        if not selection_options:
            st.error("❌ 選択肢の作成に失敗しました")
            return None, None

        # selectboxで選択
        with col1:
            selected_display_name = st.selectbox(
                "Vector Storeを選択（新しい順）:",
                options=selection_options,
                key=key,
                help="最新の作成日時順に表示されています"
            )

        # 選択された項目から実際の名前とIDを取得
        if selected_display_name:
            # 表示名から元の名前を抽出（正規表現使用）
            import re
            match = re.match(r'\d+\.\s+(.+?)\s+\(\d{4}-\d{2}-\d{2}', selected_display_name)
            if match:
                selected_name = match.group(1)
                selected_id = name_to_id_mapping.get(selected_name)

                # 選択情報を表示
                st.success(f"✅ 選択中: **{selected_name}**")
                st.code(f"Vector Store ID: {selected_id}")

                return selected_name, selected_id

        return None, None

    except Exception as e:
        logger.error(f"❌ UI作成エラー: {e}")
        st.error(f"Vector Store選択UIのエラー: {e}")
        return None, None


def display_latest_stores_table(selector: LatestVectorStoreSelector, max_stores: int = 4):
    """
    最新Vector Store一覧をテーブル表示

    Args:
        selector: LatestVectorStoreSelector インスタンス
        max_stores: 最大表示数
    """
    st.subheader(f"📊 最新Vector Store一覧（上位{max_stores}個）")

    try:
        latest_stores = selector.get_latest_n_stores(n=max_stores)

        if not latest_stores:
            st.info("表示可能なVector Storeがありません")
            return

        # テーブル用データ作成
        table_data = []
        for i, store in enumerate(latest_stores, 1):
            table_data.append({
                "順位"      : i,
                "名前"      : store['name'],
                "ID"        : store['id'],
                "作成日時"  : store['created_at_formatted'],
                "ファイル数": f"{store['file_counts']:,}",
                "使用量(MB)": f"{store['usage_bytes'] / (1024 * 1024):.2f}" if store['usage_bytes'] > 0 else "0.00"
            })

        # DataFrameで表示
        import pandas as pd
        df = pd.DataFrame(table_data)
        st.dataframe(df, use_container_width=True, hide_index=True)

        # 統計情報
        col1, col2, col3 = st.columns(3)
        with col1:
            total_files = sum(store['file_counts'] for store in latest_stores)
            st.metric("総ファイル数", f"{total_files:,}")
        with col2:
            total_usage = sum(store['usage_bytes'] for store in latest_stores)
            st.metric("総使用量", f"{total_usage / (1024 * 1024):.2f} MB")
        with col3:
            latest_date = max(store['created_datetime'] for store in latest_stores)
            st.metric("最新作成日", latest_date.strftime("%Y-%m-%d"))

    except Exception as e:
        logger.error(f"❌ テーブル表示エラー: {e}")
        st.error(f"テーブル表示エラー: {e}")


def display_store_comparison(selector: LatestVectorStoreSelector, max_stores: int = 4):
    """
    Vector Store比較表示
    Args:
        selector: LatestVectorStoreSelector インスタンス
        max_stores: 最大表示数
    """
    st.subheader("🔄 Vector Store比較（新しい順）")

    try:
        latest_stores = selector.get_latest_n_stores(n=max_stores)

        if not latest_stores:
            st.info("比較可能なVector Storeがありません")
            return

        # 比較用タブ作成
        tabs = st.tabs(
            [f"{i + 1}. {store['name'][:20]}..." if len(store['name']) > 20 else f"{i + 1}. {store['name']}" for
             i, store in enumerate(latest_stores)])

        for tab, store in zip(tabs, latest_stores):
            with tab:
                col1, col2 = st.columns(2)

                with col1:
                    st.write("**基本情報**")
                    st.write(f"名前: {store['name']}")
                    st.write(f"ID: `{store['id']}`")
                    st.write(f"作成日時: {store['created_at_formatted']}")

                with col2:
                    st.write("**使用統計**")
                    st.write(f"ファイル数: {store['file_counts']:,}")
                    st.write(f"使用量: {store['usage_bytes'] / (1024 * 1024):.2f} MB")

                    # 作成からの経過時間
                    now = datetime.now()
                    elapsed = now - store['created_datetime']
                    elapsed_days = elapsed.days
                    elapsed_hours = elapsed.seconds // 3600
                    st.write(f"経過時間: {elapsed_days}日 {elapsed_hours}時間")

                # 詳細情報（エクスパンダー）
                with st.expander("詳細情報", expanded=False):
                    st.json(store)

    except Exception as e:
        logger.error(f"❌ 比較表示エラー: {e}")
        st.error(f"比較表示エラー: {e}")


# ==================================================
# 核心部分：ソート処理の詳細
# ==================================================

def core_sorting_logic_example():
    """
    核心的なソート処理の例（a30_30_rag_search.pyから抜き出し）
    """

    # ★★★ これが元のa30_30_rag_search.pyの核心コード ★★★
    def original_sorting_code(openai_client):
        """元のソート処理（参考）"""
        try:
            # OpenAI APIからVector Store一覧を取得
            stores_response = openai_client.vector_stores.list()

            # ★重要★ Vector Storeを作成日時でソート（新しい順）
            sorted_stores = sorted(
                stores_response.data,
                key=lambda x: x.created_at if hasattr(x, 'created_at') else 0,
                reverse=True  # True = 新しい順（降順）
            )

            # 結果処理
            api_stores = {}
            store_candidates = {}  # 同名Store候補を管理

            logger.info(f"📊 取得したVector Store数: {len(sorted_stores)}")

            for store in sorted_stores:
                store_name = store.name
                store_id = store.id
                created_at = getattr(store, 'created_at', 0)

                logger.info(f"🔍 処理中: '{store_name}' ({store_id}) - 作成日時: {created_at}")

                # 同名の場合は最新のもの（作成日時が新しい）を優先
                if store_name not in store_candidates:
                    store_candidates[store_name] = {
                        'id'        : store_id,
                        'name'      : store_name,
                        'created_at': created_at
                    }
                    logger.info(f"✅ 新規候補: '{store_name}' -> {store_id}")
                else:
                    # 既存候補と比較
                    existing = store_candidates[store_name]
                    if created_at > existing['created_at']:
                        logger.info(
                            f"🔄 更新: '{store_name}' -> {store_id} [新: {created_at} > 旧: {existing['created_at']}]")
                        store_candidates[store_name] = {
                            'id'        : store_id,
                            'name'      : store_name,
                            'created_at': created_at
                        }
                    else:
                        logger.info(f"⏭️ スキップ: '{store_name}' -> {store_id} [古い]")

            # 最終的なapi_storesを構築
            for display_name, candidate in store_candidates.items():
                api_stores[display_name] = candidate['id']
                logger.info(f"🎯 最終選択: '{display_name}' -> {candidate['id']}")

            return api_stores

        except Exception as e:
            logger.error(f"❌ ソート処理エラー: {e}")
            return {}

    # 改良版：最新N個を簡単に取得
    def improved_latest_n_selection(openai_client, n=4):
        """改良版：最新N個の簡単取得"""
        try:
            # Vector Store一覧取得
            stores_response = openai_client.vector_stores.list()

            if not stores_response.data:
                return []

            # ★核心処理★ 作成日時でソート（新しい順）
            sorted_stores = sorted(
                stores_response.data,
                key=lambda store: getattr(store, 'created_at', 0),
                reverse=True  # 新しい順（重要）
            )

            # 最新N個を選択
            latest_n_stores = sorted_stores[:n]

            # 詳細情報を含む辞書に変換
            result = []
            for i, store in enumerate(latest_n_stores, 1):
                store_info = {
                    "rank"                : i,
                    "name"                : store.name,
                    "id"                  : store.id,
                    "created_at"          : getattr(store, 'created_at', 0),
                    "created_at_formatted": datetime.fromtimestamp(getattr(store, 'created_at', 0)).strftime(
                        "%Y-%m-%d %H:%M:%S"),
                    "file_counts"         : getattr(store.file_counts, 'total', 0) if hasattr(store,
                                                                                              'file_counts') and store.file_counts else 0,
                    "usage_bytes"         : getattr(store, 'usage_bytes', 0)
                }
                result.append(store_info)

                # ログ出力
                print(f"{i}. {store.name} ({store.id}) - {store_info['created_at_formatted']}")

            return result

        except Exception as e:
            logger.error(f"❌ 改良版取得エラー: {e}")
            return []

    return original_sorting_code, improved_latest_n_selection


# ==================================================
# 使用例とメイン処理
# ==================================================

def example_usage():
    """使用例"""

    # OpenAIクライアント初期化
    try:
        openai_client = OpenAI()  # 環境変数からAPIキー取得
        selector = LatestVectorStoreSelector(openai_client)
    except Exception as e:
        st.error(f"OpenAI API初期化エラー: {e}")
        return

    # 最新4個のVector Storeを取得
    latest_4_stores = selector.get_latest_n_stores(n=4)

    if latest_4_stores:
        st.success(f"✅ 最新{len(latest_4_stores)}個のVector Storeを取得しました")

        # 選択UI
        selected_name, selected_id = create_latest_store_selector_ui(
            selector,
            max_stores=4,
            key="example_selection"
        )

        if selected_name and selected_id:
            st.write(f"**選択結果:**")
            st.write(f"- 名前: {selected_name}")
            st.write(f"- ID: `{selected_id}`")

            # 選択されたVector Storeの詳細表示
            selected_store = next((store for store in latest_4_stores if store['name'] == selected_name), None)
            if selected_store:
                with st.expander("選択されたVector Storeの詳細", expanded=True):
                    col1, col2 = st.columns(2)
                    with col1:
                        st.metric("ファイル数", f"{selected_store['file_counts']:,}")
                    with col2:
                        st.metric("使用量", f"{selected_store['usage_bytes'] / (1024 * 1024):.2f} MB")

                    st.info(f"作成日時: {selected_store['created_at_formatted']}")

        # テーブル表示
        display_latest_stores_table(selector, max_stores=4)

        # 比較表示
        display_store_comparison(selector, max_stores=4)

        # 保存機能
        if st.button("💾 最新Vector Store情報を保存"):
            success = selector.save_selected_stores(latest_4_stores)
            if success:
                st.success("✅ ファイルに保存されました: latest_vector_stores.json")
            else:
                st.error("❌ 保存に失敗しました")

    else:
        st.warning("⚠️ Vector Storeが見つかりませんでした")


# ==================================================
# セッション状態連携版
# ==================================================

def streamlit_session_integration():
    """Streamlitセッション状態との連携例"""

    # セッション状態の初期化
    if 'vector_store_selector' not in st.session_state:
        try:
            openai_client = OpenAI()
            st.session_state.vector_store_selector = LatestVectorStoreSelector(openai_client)
        except Exception as e:
            st.error(f"初期化エラー: {e}")
            return

    if 'selected_store_info' not in st.session_state:
        st.session_state.selected_store_info = {}

    selector = st.session_state.vector_store_selector

    # メイン選択UI
    st.title("🔗 最新Vector Store選択システム")
    st.caption("作成日時順（新しい順）で最新4個から選択")

    # 設定
    col1, col2 = st.columns(2)
    with col1:
        max_stores = st.slider("表示する最大数", min_value=1, max_value=10, value=4)
    with col2:
        auto_refresh = st.checkbox("自動リフレッシュ", value=False)

    # Vector Store選択
    selected_name, selected_id = create_latest_store_selector_ui(
        selector,
        max_stores=max_stores,
        key="session_store_selection"
    )

    # 選択結果をセッション状態に保存
    if selected_name and selected_id:
        st.session_state.selected_store_info = {
            "name"       : selected_name,
            "id"         : selected_id,
            "selected_at": datetime.now().isoformat()
        }

    # 現在の選択状況表示
    if st.session_state.selected_store_info:
        st.success("📌 現在の選択:")
        info = st.session_state.selected_store_info
        st.write(f"- **名前**: {info['name']}")
        st.write(f"- **ID**: `{info['id']}`")
        st.write(f"- **選択日時**: {info['selected_at']}")

    # 詳細表示
    with st.expander("🔍 詳細情報", expanded=False):
        display_latest_stores_table(selector, max_stores=max_stores)


# ==================================================
# メイン実行部分
# ==================================================

def main():
    """メイン処理"""

    # ページ設定
    st.set_page_config(
        page_title="最新Vector Store選択システム",
        page_icon="🔗",
        layout="wide"
    )

    # タブで機能分け
    tab1, tab2, tab3 = st.tabs(["🔗 Vector Store選択", "📊 一覧表示", "🔄 比較表示"])

    # OpenAIクライアント初期化
    try:
        openai_client = OpenAI()
        selector = LatestVectorStoreSelector(openai_client)
    except Exception as e:
        st.error(f"OpenAI API初期化エラー: {e}")
        st.code("export OPENAI_API_KEY='your-api-key-here'")
        return

    with tab1:
        # 選択機能
        example_usage()

    with tab2:
        # 一覧表示
        max_display = st.slider("表示数", min_value=1, max_value=20, value=4, key="display_count")
        display_latest_stores_table(selector, max_stores=max_display)

    with tab3:
        # 比較表示
        max_compare = st.slider("比較数", min_value=1, max_value=10, value=4, key="compare_count")
        display_store_comparison(selector, max_stores=max_compare)

    # フッター
    st.markdown("---")
    st.markdown("### 🔗 最新Vector Store選択システム")
    st.markdown("✨ **作成日時順ソート**: 最新のVector Storeを優先表示")
    st.markdown("🎯 **重複解決**: 同名Vector Storeの最新版を自動選択")
    st.markdown("⚡ **高速選択**: キャッシュ機能で快適な操作")


if __name__ == "__main__":
    main()

# ==================================================
# 重要なポイント解説
# ==================================================
"""
🔑 **重要な処理の核心部分:**

1. **OpenAI APIからVector Store一覧取得:**
   stores_response = openai_client.vector_stores.list()

2. **作成日時でソート（新しい順）:**
   sorted_stores = sorted(
       stores_response.data,
       key=lambda x: x.created_at if hasattr(x, 'created_at') else 0,
       reverse=True  # ★重要★ True=新しい順
   )

3. **最新N個を選択:**
   latest_n_stores = sorted_stores[:n]

4. **重複解決（同名Vector Store）:**
   - 作成日時でソートされているため、同名の場合は自動的に最新が優先
   - created_at値を比較して最新のIDを選択

5. **UIでの選択:**
   - selectboxで作成日時付きの名前を表示
   - 選択されたら対応するIDを取得

🎯 **このシステムの利点:**
- 常に最新のVector Storeが優先される
- 重複ID問題が自動解決される
- 作成日時が明確に表示される
- キャッシュ機能で高速動作
- エラーハンドリングが充実

📊 **活用場面:**
- a30_020_make_vsid.py で新しいVector Store作成後
- 複数の同名Vector Storeがある場合
- 最新のデータを確実に使いたい場合
- Vector Storeの管理・メンテナンス
"""

# streamlit run a10_get_vsid.py
