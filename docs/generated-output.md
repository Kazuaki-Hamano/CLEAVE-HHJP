# 生成物の保存場所

`output/` はGit管理対象外です。正規の保存場所は `V:\Projects\CLEAVE-HHJP\output` です。

| 場所 | 内容 |
|---|---|
| `output/firmware/9b4ba539/` | 現行の実機確認済みDYA対応UF2。Runtime Macro割り当てを含む。埋込ビルドID `e377a35a` |
| `output/firmware/025d2c68/` | 戻し用の直前のmain由来UF2。埋込ビルドID `d76ea2d0`。Runtime Macro割り当て追加前 |
| `output/battery/dist/CLEAVE-Battery.exe` | Windows常駐アプリ。現行ファームウェアでは残量表示・診断・更新用途。旧トラックパッド設定は使用しない |
| `output/battery/dist/CLEAVE-Battery-Diagnostics.exe` | 読み取り専用のバッテリー記録ツール |
| `output/battery/build-env/` | EXE再作成・hidapi依存の検証用Python環境 |
| `output/battery/` のログ・補助依存 | 既存の測定記録・ビルド補助。今回のDYA整理では変更しない |
| `output/case-design/`、`output/imagegen/` | ケース・画像の設計素材と生成物。保持 |
| `output/dya-investigation-archive.zip` | 中止したクライアント再接続修正の未コミット差分。回復用で、現行ファームウェアには含めない |
| `output/dya-local-web-archive.zip` | 不要になったローカルDYA試験配布物の復元用ZIP |
| `output/cleanup-dya-20261020.json` | 今回の整理対象と結果 |

現行UF2は [Actions Run 39358929004](https://github.com/Kazuaki-Hamano/CLEAVE-HHJP/actions/runs/39358929004) で生成しました。左右UF2、settings_reset、左右の完全なビルドログ、チェックサム、検証結果を同じフォルダに保持します。`settings_reset` は通常の更新には使いません。

2026年10月20日にDYA試験用チェックアウト、重複UF2、古いDYA成果物を整理しました。ごみ箱へ移したものは空にするまでディスク容量を消費します。ローカルWeb配布物は、復元用ZIPを検証し、ログを使用していた試験サーバーを停止した後でごみ箱へ移しました。試験中に使ったlocalhost:8766のページは今後使用しません。

ファームウェアの取得は[取得・検証手順](../tools/battery/firmware-tools.md)、設定は[DYA Studio](dya-studio.md)、アプリは[バッテリーアプリ](../tools/battery/README.md)を参照してください。
