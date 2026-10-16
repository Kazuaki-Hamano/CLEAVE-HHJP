# 開発・検証用補助スクリプト

リポジトリのルートから実行します。

- `build_current.py`：現在のHEADに一致するActionsを確認。`download`を付けると成功済み成果物を取得
- `verify_current.py <firmware folder>`：生成DTSのINT5/Fn・INT4/Fn・KanaとUF2識別子を確認
- `test_tray.py`：トレイとウィンドウの開閉を自動確認（GUIを使用）
- `test_update_ui.py [firmware folder]`：更新UIのmock確認。実機へは書き込まない。省略時は`output/firmware/bc546789`
- `capture_raw.py`、`preview.py`：以前の調査・プレビュー用。通常の記録には`../battery_diagnostics.py`を使用

通常のユニットテストは親ディレクトリの `test_*.py` です。
