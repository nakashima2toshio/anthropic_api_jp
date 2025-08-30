# streamlit run agents_docs.py --server.port=8501
# data/agents_docs.py
import streamlit as st
import json
from pathlib import Path

# ページ設定はインポート直後
st.set_page_config(
    page_title="jsonデータ表示",
    page_icon="NT"
)

def init_page():
    st.header("Show agents_docs")
    st.sidebar.title("メニュー")

def demo_1(demo_name=None):
    import json  # ← モジュールとして使う前にインポート

    st.subheader("Demo 1: JSONデータ表示")

    json_path = Path(__file__).with_suffix(".json")
    if not json_path.exists():
        st.error(f"ファイルが見つかりません: {json_path}")
        return

    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    keys = list(data.keys())
    selected_key = st.selectbox("キーを選択してください", keys)

    if st.button("OK"):
        st.write("### 選択中のキー:")
        st.write(selected_key)

        value = data[selected_key]

        # st.write("#### [Debug] value の型")
        # st.write(type(value))

        st.write("#### [Debug] value の概要")
        if isinstance(value, dict):
            st.write(f"dict: キー数 = {len(value)}")
            st.write("キー一覧:", list(value.keys()))
        elif isinstance(value, list):
            st.write(f"list: 要素数 = {len(value)}")
        elif isinstance(value, str):
            st.write(f"str: 文字数 = {len(value)}")
            st.write("先頭 100 文字プレビュー:")
            st.code(value[:100])
        else:
            st.write("その他の型 repr:")
            st.code(repr(value))

        # 本来の表示
        st.write("### 本来の表示")
        st.write("対応する値：")

        if isinstance(value, (dict, list)):
            pretty_json = json.dumps(value, indent=2, ensure_ascii=False)
            st.text(pretty_json)
        else:
            # 長いテキストの場合はtext_areaを使って読みやすく表示
            if len(str(value)) > 500:
                st.text_area("内容", value=str(value), height=400, disabled=True)
            else:
                st.text(str(value))


def demo_2(demo_name=None):
    st.subheader("Demo 2 一括、ファイル作成")

def main():
    init_page()

    page_names_to_funcs = {
        "demo_1": demo_1,
        "demo_2": demo_2
    }
    demo_name = st.sidebar.radio("Choose a demo", list(page_names_to_funcs.keys()))
    page_names_to_funcs[demo_name](demo_name)

if __name__ == "__main__":
    main()
