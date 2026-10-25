# 生成物の保存場所

`output/` はGit管理対象外です。正規の保存場所は `V:\Projects\CLEAVE-HHJP\output` です。

| 場所 | 内容 |
|---|---|
| `output/firmware/648c54f4/` | 現行のDYA対応UF2。LEDのPWM調光・左右同期を含み、左右の明るさ変更と保存を実機確認済み。埋込ビルドID `c94fa28a` |
| `output/firmware/9b4ba539/` | 過去の実機確認済みDYA対応UF2。Runtime Macro割り当てを含む。埋込ビルドID `e377a35a` |
| `output/firmware/025d2c68/` | 過去のmain由来UF2。埋込ビルドID `d76ea2d0`。Runtime Macro割り当て追加前 |
| `output/battery/build-env/` | hidapi依存の診断・検証用Python環境。EXE作成は廃止 |
| `output/battery/` のログ・補助依存 | 既存の測定記録・検証補助。アプリの配布・ビルド成果物は削除済み |
| `output/case-design/`、`output/imagegen/` | ケース・画像の設計素材と生成物。保持 |
| `output/dya-investigation-archive.zip` | 中止したクライアント再接続修正の未コミット差分。回復用で、現行ファームウェアには含めない |
| `output/dya-local-web-archive.zip` | 不要になったローカルDYA試験配布物の復元用ZIP |
| `output/cleanup-dya-20261020.json` | 今回の整理対象と結果 |

現行UF2は [Actions Run 40158279533](https://github.com/Kazuaki-Hamano/CLEAVE-HHJP/actions/runs/40158279533) で生成しました。左右UF2、settings_reset、左右の完全なビルドログ、チェックサム、検証結果を同じフォルダに保持します。`settings_reset` は通常の更新には使いません。

2026年10月20日にDYA試験用チェックアウト、重複UF2、古いDYA成果物を整理しました。ごみ箱へ移したものは空にするまでディスク容量を消費します。ローカルWeb配布物は、復元用ZIPを検証し、ログを使用していた試験サーバーを停止した後でごみ箱へ移しました。試験中に使ったlocalhost:8766のページは今後使用しません。

ファームウェアの取得は[取得・検証手順](../tools/battery/firmware-tools.md)、設定は[DYA Studio](dya-studio.md)、診断CLIは[検証・診断ツール](../tools/battery/README.md)を参照してください。

2026年10月21日に独自Windowsアプリを廃止しました。常駐・診断EXE、退避EXE、アプリ専用ビルドフォルダーと旧GUIテストを削除しました。ローカル成果物はごみ箱へ移しており、空にするまでは復元可能です。測定JSONL、検証画像、ファームウェア成果物、CLI検証用Python環境は保持します。
