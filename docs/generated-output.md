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
| `output/firmware/c70aa041/` | 最新試用UF2。Sleep Intervalを255→50へ変更。左右UF2を更新、アプリ更新不要 |
| `output/firmware/fdff9be9/` |右端スクロール量の独立設定・HID設定version 3。左UF2とアプリを更新 |
| `output/firmware/f0c97f61/` |右パッドのチップ内蔵スクロール。直前版からは右UF2のみ更新 |
| `output/firmware/502000da/` |Fn中の右カーソル移動、Fn＋Q/Eの左右クリック。Actionsログ・チェックサム・キー設定検証結果を含む |
| `output/firmware/89ab7a5c/` | 旧LANG1位置の長押しFn復活版 |
| `output/firmware/bc546789/` | スクロール量設定追加版（HID設定version 2） |
| `output/firmware/a281e739/` | 左パッド追加版。左パッドの通常動作は実機確認済み。導入は左UF2のみで可 |
| `output/firmware/0e0ac9d6/` | 左の通常時縦横スクロール・Fn戻る／進む版。左UF2のみで導入 |
| `output/firmware/5fedfa36/` | 直前の標準split設定同期版（HID設定version 1） |
| `output/case-design/` | ケース解析、STEP・DXF・FeatureScriptなどの設計成果物 |
| `output/imagegen/` | キーマップ画像の原本・編集素材 |

最新試用UF2は`c70aa041`（[Actions Run 38977116745](https://github.com/Kazuaki-Hamano/CLEAVE-HHJP/actions/runs/38977116745)）で、埋込ビルドIDは左右とも`4ccbb607`です。Gitコミット先頭8桁とは異なります。現在のアプリはHID設定version 3用です。旧版へ戻す場合は対応するアプリも必要です。`settings_reset`は通常の更新には使いません。

左右パッド対応済みの構成から、左パッドの役割変更・旧LANG1位置の長押しFnを導入する場合は、最新の左UF2のみを書き込みます。右UF2とアプリの更新は不要です。初回導入は左右両方を更新してください。Studio保存済み配置がある場合は、該当キーをINT4/Fnへ変更するか、Restore Stock Settingsで初期配置を反映します（他の保存済み割り当ても初期化されます）。

旧試作アプリ、PyInstaller中間物、重複UF2、古いActions成果物はごみ箱へ移しました。対象とサイズは`output/cleanup-20261017.json`に記録しています。ディスク空き容量が増えるのは、ごみ箱を空にした後です。ケース・画像素材と調査ログは残しています。

再作成は[アプリのビルド手順](../tools/battery/README.md)と[ファームウェア取得手順](../tools/battery/firmware-tools.md)を参照してください。

`502000da`は左UF2のみの更新で反映できます。Studio保存済み配置がある場合はFnレイヤーのQを左クリック、Eを右クリックに変更してください。キーを保持している間はクリックも保持します。右のFn縦スクロールは廃止し、スクロール量の設定は左パッドへ適用します。

内蔵スクロールの試用は、Fn中も右カーソルが使える`502000da`からなら右UF2のみ更新します。左を`502000da`のまま使う場合、左右のビルドIDは異なりますが入力プロトコルは共通です。アプリの更新は不要です。元へ戻す場合は右に`502000da`のUF2を書き戻します。

右端スクロール量の設定版は左UF2と`output/battery/dist/CLEAVE-Battery.exe`を更新します。右側は内蔵スクロール対応の`f0c97f61`を継続使用できます。アプリのSHA256は`0B703983E3B09DF639C636C6837AABE5C716D80D1361CC20F193713090322256`です。旧アプリは`output/battery/verification/native-scroll/CLEAVE-Battery-before-v3.exe`へ退避しました。設定UIのテスト画像・記録も同フォルダーです。旧保存設定は読み込み時に移行しますが、v3で保存した後に旧ファームウェアへ戻すと設定を読み込めないため、旧版で再調整が必要です。

Sleep Interval比較版`c70aa041`は左右で共通の変更です。両側のUF2を更新し、放置後の復帰時間を左右別々に確認します。右端スクロール倍率を含むHID設定version 3を維持し、現在のアプリ・保存設定はそのまま使用します。復帰時間の改善は実機確認待ちです。
