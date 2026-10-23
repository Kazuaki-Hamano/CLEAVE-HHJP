# ZMKファームウェア設計書

現在のファームウェアはDYA Studioに対応した構成です。操作は[DYA Studioガイド](dya-studio.md)、配線は[Cirque組み込み](cirque-trackpad-integration.md)、組み立ては[ビルドガイド](../build-guide/README.md)を参照してください。

## 構成と依存先

| 項目 | 現在の構成 |
|---|---|
| マイコン | 左右各1個のXIAO nRF52840 Plus |
| ビルドboard | `xiao_ble//zmk` |
| キー数 | 70（左31、右39） |
| 左側 | セントラル。USB／BluetoothでPCへ接続し、右側の入力を集約 |
| 右側 | ペリフェラル。左側へBLE接続。`CONFIG_BT_MAX_CONN=1` |
| ZMK | cormoran/zmk `e5c9b6915b56801193e359dd9bad4a167ce0d1b8` |
| Zephyr | cormoran/zephyr `63363d92c475ad203b35e9047cef7ecd8706a6fc`（4.1系） |
| RGB LED | caksoylar/zmk-rgbled-widget `e6b467792a1dabef8cfa5c9fd26bfefc9c16662b` |
| 配布物 | 左右のUF2とsettings_reset。通常の更新は左右UF2のみ |

完全な依存一覧は [`config/west.yml`](../config/west.yml)。ローカル修正は `modules/` の各 `UPSTREAM.md`、`src/pinnacle/UPSTREAM.md`、`src/studio/UPSTREAM.md` に出典を記録しています。

## 設定・実装の読み込み

- 左側は `config/boards/shields/cleave_hhjp/cleave_hhjp_left.conf`、右側は同ディレクトリの `cleave_hhjp_right.conf` を読み込みます。共通名の `.conf` の内容だけで実効値を判断しません。
- ビルド定義は [`build.yaml`](../build.yaml)。左側に `studio-rpc-usb-uart` を指定します。DYAのホストRPCは左側だけに組み込みます。
- 左側のUSB HIDデバイス数は2。標準キーボード／マウスと独自の残量・更新機能を併用します。
- split relayのデータ長は240バイト。左右のsplit用スタックは2048バイト。システムworkqueueは4096バイトです。
- スリープは左右とも有効、初期値30分。各マトリックスがwake sourceで、パッドへの接触は復帰条件ではありません。DYAで保存した待機時間が初期値より優先されます。
- GATTトランスポートは `src/studio/gatt_rpc_transport.c` を中央側だけに組み込み、ATT MTUに従った分割と接続参照の解放を補正しています。

実効値はActionsの左右それぞれのKconfig／Devicetreeログで確認します。UF2と一緒に保存した `build-logs.zip` が確認資料です。

## キーマップとレイアウト

[`config/cleave_hhjp.keymap`](../config/cleave_hhjp.keymap) の `default_layer` と `fn_layer` は各70 bindingです。追加用の4レイヤー枠は初期状態では無効です。

左右の専用Fnは `&mo 1`。旧LANG2位置は `&lt 1 INT5`、旧LANG1位置は `&lt 1 INT4`、独立Kanaは `&kp LANG1`。hold-tapは200ms、`tap-preferred`。Fn＋Ctrl＋1～5でBluetoothプロファイル、Fn＋Ctrl＋Backspaceで現在のペアリングを消去します。Fn＋\|はDYAのBLE検出、Fn＋Z／\_は左右のUF2モード移行です。

70位置のtransform、物理レイアウトとkscanは `cleave_hhjp.dtsi`、行列GPIOは左右overlayに定義します。右側は `col-offset=7`。右側1～4段目の表示には実物と同じ段ずれを付けています。DYAに保存したキー配置はコンパイル時の初期配置より優先されます。

Runtime Macroは `<behaviors/runtime_macro.dtsi>` から `&rmacro <slot>` を公開します。マクロ本文とキー割り当ては別々に保存します。コンボと押下表示、接続先・OS別レイヤーも有効です。

## トラックパッド

左右のCirque TM040040は追加GPIOへSPI接続します。右側の入力は `trackpad_split` からBLEで左側へ、左側の入力はローカルlistenerへ送ります。右はFn中もカーソル、左は縦横スクロールとFn中の戻る／進む。Fn＋F／Sは左右クリックです。

速度、加速、最大倍率、左右それぞれのスクロール量はDYAのカスタム設定へ移行しました。旧USB Feature 7の設定version 3は廃止し、Windowsアプリからは変更しません。パッド別の速度・端数状態を保持し、左スクロールが右カーソルの加速に影響しないようにしています。

`trackpad_scroll` は互換用の定義として残っていますが、右listenerでFnスクロールへ切り替える処理には使いません。チップの感度は1x、Sleep Intervalは50。右端スクロールはPinnacle内蔵の機能で、2本指スクロールの実装ではありません。

## DYA設定・診断

BLE管理、活動設定の永続同期、接続先・OS別レイヤー、キースキャン、ウォッチドッグ、スタック使用量に対応しています。同期の保存完了応答や表示範囲、BLE再接続の運用は[DYA Studioガイド](dya-studio.md)を参照してください。

## ビルドと検証

確認済みのソースは `9b4ba539`、埋込ビルドIDは `e377a35a`。成果物の場所と戻し用は[生成物一覧](generated-output.md)に記載します。ドキュメント整理のコミットはファームウェアの内容を変えません。以後のソースビルドでは識別子が変わるため、検証済みUF2と新規ビルドを区別します。

Actionsは固定リビジョンの再利用ワークフローを呼び出します。`tools/battery/verify_firmware.py` でUF2／HID、`tools/dya-studio/verify_build.py` で実効設定とDYA機能、`tools/battery/dev/verify_current.py` でキーマップを確認します。構成変更後は該当する実機確認も行います。


## 7. USB残量・充電状態・更新プロトコル

`src/usb_battery.c` はvendor usage page `0xff60`、usage `1` の `HID_1` を登録します。標準のキーボード・マウスHID、Studioとは別の用途です。読取専用の状態レポートに加え、更新開始用SET_FEATUREを受け付けます。コンパイル条件は残量fetching有効かつUSB HIDデバイス数が2以上です。

| Feature ID | 長さ（ID込み） | 内容 |
|---|---|---|
| 1 | 7 | ID、version=1、左%、右%、右valid、右通知経過秒（uint16 LE） |
| 2 | 6 | ID、version=1、左電源状態、右電源状態、右状態経過秒（uint16 LE） |
| 3 | 32 | 親機の更新対応情報 |
| 4 | 8（Windows送信時32） | ID=4、version=1、対象側、ASCII `BOOT`、ゼロ埋め |
| 5 | 32 | 子機の更新対応情報キャッシュ |
| 6 | 16 | 左側の診断情報：残量・電源状態・センサーのキャッシュ電圧/残量・valid flags・uptime・最終残量変化イベントからの経過秒 |

Windowsではcollection最大長32バイトでFeature Reportを読み、ID1/2は有効な7/6バイトを取り出します。ID4は8または32バイトを受け付け、余白はゼロのみです。
診断用ID6も32バイトで読み、先頭16バイトを取り出します。`sensor_channel_get` で既存センサーのキャッシュを取得し、追加のADCサンプリングは行いません。取得できない値はflagsでunknownを表します。残量変化イベントの経過時間はADC計測の経過時間とは異なります。記録ツールは[診断手順](../tools/battery/README.md#sudden-battery-percentage-changes-diagnostics)を参照してください。

右残量はsource=0の通知で更新し、未取得・切断時はunknownです。0%はunknownと区別します。値が変わらない間は通知が来ないことがあるため、残量には時間だけによる失効を設定していません。

電源状態は0=unknown、1=バッテリー、2=USB給電（充電信号なし）、3=充電中。`src/charge_status.c` はP0.17のactive-low CHGを入力として読み、VBUSを別に検出します。USBありの場合のみpull-upを使います。充電電流の設定変更は行いません。右側の暗号化GATT値を5秒ごとに取得し、切断または最終取得から約20秒超でunknownになります。
USB給電やCHG解除だけでは満充電とは判定しません。残量%はZMKの電圧による推定値です。
USB接続中の左側はスイッチOFF/ONにより測定電圧と残量が変わることを確認しました。残量確認時はスイッチONを使用します。経緯・測定値・確認範囲は[調査結果](battery-measurement.md)を参照してください。

ID3/5は `[ID, version, side, flags, build8, CHHP, chipID8, reserved]`。sideは0=左、1=右、flagsはbit0=更新対応、bit1=USB給電です。子機GATTは先頭16バイトのみで、親機キャッシュのchipIDはゼロです。子機情報は5秒ごとに取得し、切断または20秒超で失効します。

## 8. UF2検証と手動更新

独自WindowsアプリとPC側の更新処理は廃止しました。`tools/battery/firmware_update.py`は既存スクリプトとの互換のため名前を維持し、オフラインの`validate_firmware`だけを残しています。UF2 magic、family、payload、ブロックの欠落・重複・連続性、アプリ領域、左右とビルド識別子を確認し、デバイス操作や書き込みはしません。

`CMakeLists.txt`が生成する識別子はUF2内の`CLEAVE_HHJP_UPDATE1|LEFT|<build8>`または`RIGHT`へ格納されます。検証ツールは引き続きこの識別子を読み取ります。

更新は[キー操作によるUF2モード移行](bootloader-keys.md)後、対象側のUF2をドライブへコピーします。設定変更は[DYA Studio](dya-studio.md)を使用します。旧アプリ向けHID Feature 1～6と`src/app_update.c`は今回変更していません。

## 起床状態のLED表示

左右のRGB LEDはACTIVE・IDLE中、自分側の残量の色で点灯します。80%以上は緑、20〜79%は黄、20%未満は赤。起動時と同じ関数を使い、未取得／0%時のマゼンタも維持します。既存の通知表示後は残量の色へ戻り、SLEEPでは即時消灯します。追加のADC測定・周期タイマー・PWM調光はありません。

固定LEDモジュールの `src/widget.c` だけをCMakeの遅延処理で `src/status_led/widget.c` に置換します。左右それぞれで元の翻訳単位が1個であることを要求し、settings_resetには適用しません。通知中のスリープに備え、GPIO書き込みの排他と消灯ゲートを設けています。[出典・変更点](../src/status_led/UPSTREAM.md)、[利用記録](../build-guide/customizations/system.md)を参照してください。実機の点灯・消灯と電池持ちは別途確認が必要です。
