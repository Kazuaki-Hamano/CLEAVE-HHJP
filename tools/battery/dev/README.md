# 開発・検証用補助スクリプト

リポジトリのルートから実行します。WindowsアプリのGUI・トレイテストは廃止しました。

- `build_current.py`：現在のHEADに一致するActionsを確認。`download`で成功済み成果物を取得。
- `verify_current.py <firmware folder>`：生成キーマップとUF2識別子を確認。
- `test_pinnacle_packet.py`：ドライバーのパケット処理をWSL gccで検証。
- `capture_raw.py`：以前の生HID記録用。通常の記録は`../battery_diagnostics.py`を使用。

Pythonの回帰テストは`python -m unittest discover -s tools/battery -p "test_*.py"`で実行します。
