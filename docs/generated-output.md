# 生成物の保存場所

`output/`はGit管理対象外です。現行の成果物と、設計・調査の記録を保持しています。

| 場所 | 内容 |
|---|---|
| `output/battery/dist/CLEAVE-Battery.exe` | 現行の常駐アプリ。残量・更新・タッチパッド設定を統合 |
| `output/battery/dist/CLEAVE-Battery-Diagnostics.exe` | 読取専用のバッテリー記録ツール |
| `output/battery/build-env/` | EXE再作成用のPython環境 |
| `output/battery/python-packages/` | Python実行時の補助依存パッケージ |
| `output/battery/*.jsonl` | 電圧・残量・スイッチ状態の実測ログ |
| `output/battery/verification/` | 現行設定画面の確認画像と通信調査記録 |
| `output/firmware/bc546789/` | 現行UF2、Actionsログ、チェックサム、検証結果 |
| `output/firmware/a281e739/` | 左パッド追加版。左右ビルド済み・左パッド実機確認待ち。導入は左UF2のみで可 |
| `output/firmware/0e0ac9d6/` | 左の通常時縦横スクロール・Fn戻る／進む版。左UF2のみで導入 |
| `output/firmware/5fedfa36/` | 直前の標準split設定同期版（HID設定version 1） |
| `output/case-design/` | ケース解析、STEP・DXF・FeatureScriptなどの設計成果物 |
| `output/imagegen/` | キーマップ画像の原本・編集素材 |

現行UF2の埋込ビルドIDは左右とも`6cd2bf9d`です。Gitコミット先頭8桁とは異なります。現在のアプリはHID設定version 2用です。旧版へ戻す場合は対応するアプリも必要です。`settings_reset`は通常の更新には使いません。

旧試作アプリ、PyInstaller中間物、重複UF2、古いActions成果物はごみ箱へ移しました。対象とサイズは`output/cleanup-20261017.json`に記録しています。ディスク空き容量が増えるのは、ごみ箱を空にした後です。ケース・画像素材と調査ログは残しています。

再作成は[アプリのビルド手順](../tools/battery/README.md)と[ファームウェア取得手順](../tools/battery/firmware-tools.md)を参照してください。
