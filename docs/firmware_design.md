# ZMKファームウェア設計書

この文書は、このリポジトリのソース・設定・ビルド定義に対応します。
組み立てと標準配布版の導入は[ビルドガイド](../build-guide/README.md)、Windowsアプリの操作は[バッテリーアプリ](../tools/battery/README.md)を参照してください。
標準配布版と、このフォークで追加した機能は区別して扱います。

## 1. 構成

| 項目 | 現在の構成 |
|---|---|
| マイコン | 左右各1個のXIAO nRF52840 Plus |
| ZMKビルド用board名 | `seeeduino_xiao_ble` |
| キー数 | 70（左31、右39） |
| 左側 | セントラル（親機）。右側の入力を集約し、ホストへ送信 |
| 右側 | ペリフェラル（子機）。左側へBLE接続 |
| ホスト接続 | 左側からUSBまたはBluetooth |
| ZMK | `config/west.yml` の `v0.3-branch` |
| RGB LEDモジュール | `caksoylar/zmk-rgbled-widget` の `v0.3` |
| 更新ファイル | UF2（左右用とsettings_reset用の3ターゲット） |

左右間の通信はBLEです。左側をUSB接続してキーボード・マウス入力、Studio、残量アプリを使用できます。残量アプリのためにPCとBluetooth接続する必要はありません。右側の状態を取得するには左右間の接続が必要です。ホストへの入力先はZMKの出力先選択に従います。

## 2. ファイルの役割

| ファイル・ディレクトリ | 役割 |
|---|---|
| [`config/cleave_hhjp.keymap`](../config/cleave_hhjp.keymap) | 通常・Fnの2レイヤー、hold-tap、Bluetooth操作 |
| [`cleave_hhjp.dtsi`](../config/boards/shields/cleave_hhjp/cleave_hhjp.dtsi) | 70キーの物理レイアウト、5行×15列の変換、共通kscan |
| [`cleave_hhjp_left.overlay`](../config/boards/shields/cleave_hhjp/cleave_hhjp_left.overlay) | 左側GPIOマトリックス |
| [`cleave_hhjp_right.overlay`](../config/boards/shields/cleave_hhjp/cleave_hhjp_right.overlay) | 右側GPIOマトリックス、列オフセット7 |
| [`cleave_hhjp_left.conf`](../config/boards/shields/cleave_hhjp/cleave_hhjp_left.conf) | 左側pointing、残量取得、USB HID数、Studio |
| [`cleave_hhjp.conf`](../config/boards/shields/cleave_hhjp/cleave_hhjp.conf) | 共通名の設定ファイル。現在のビルドで読み込まれるとは限らない（3節） |
| [`Kconfig.defconfig`](../config/boards/shields/cleave_hhjp/Kconfig.defconfig) | キーボード名、分割構成、左側の役割と接続数の既定値 |
| [`config/west.yml`](../config/west.yml) / [`build.yaml`](../build.yaml) | 依存先とビルドターゲット |
| [`zephyr/module.yml`](../zephyr/module.yml) / [`CMakeLists.txt`](../CMakeLists.txt) | 独自ソース・DTS bindingの登録とビルドID生成 |
| [`src/`](../src) / [`dts/bindings/`](../dts/bindings) | マウス速度、残量・充電状態・更新処理とbinding定義 |
| [`tools/battery/`](../tools/battery/README.md) | Windowsアプリ、EXE作成、UF2更新・検証 |
| [`tools/case-design/`](../tools/case-design/README.md) | STL断面によるケース近似再構成 |
| `output/` | 生成物・依存パッケージ・ログ。Git管理対象外 |

`cleave_hhjp_right.conf` は現在存在しません。キーマップはシールド内ではなく `config/cleave_hhjp.keymap` にあります。

## 3. 設定の読み込み

設定ファイルの記述と実効設定は区別します。Actionsログの `Merged configuration` と各ターゲットのKconfig出力を確認してください。

現行の成功ビルド `bc546789`（Run `38914707698`）では、左側は `cleave_hhjp_left.conf` を読み込み、右側はこのシールドの `.conf` を読み込んでいません。両側とも `cleave_hhjp.conf` はマージされていません。今後のビルド結果も毎回確認します。

左側 `.conf` の明示設定は次のとおりです。

| 設定 | 値 |
|---|---|
| `CONFIG_ZMK_POINTING` | `y` |
| `CONFIG_ZMK_BATTERY_REPORTING` | `y` |
| `CONFIG_ZMK_SPLIT_BLE_CENTRAL_BATTERY_LEVEL_FETCHING` | `y` |
| `CONFIG_USB_HID_DEVICE_COUNT` | `2` |
| `CONFIG_ZMK_STUDIO` | `y` |
| `CONFIG_ZMK_STUDIO_LOCKING` | `n` |

`Kconfig.defconfig` は左側の `ZMK_KEYBOARD_NAME` を `CLEAVE HHJP`、`ZMK_SPLIT_ROLE_CENTRAL` を `y`、`ZMK_SPLIT_BLE_CENTRAL_PERIPHERALS` を `1`、`BT_MAX_CONN` を `5` に設定します。左右とも `ZMK_SPLIT=y` が既定です。Bluetoothプロファイル1〜5の選択と同時接続数は別の概念です。

共通名ファイルには `CONFIG_ZMK_IDLE_TIMEOUT=300000`（5分）、`CONFIG_ZMK_IDLE_SLEEP_TIMEOUT=3600000`（60分）、`CONFIG_ZMK_SLEEP=y`、NFCピンのGPIO化、+8dBm、残量proxyなどが記述されています。これらは現在の実効設定ではありません。現行ビルドのidle timeoutは左右とも `30000`（30秒）で、`CONFIG_ZMK_SLEEP=y` はありません。右側の`CONFIG_INPUT_PINNACLE=y`もビルドログで確認済みです。

スリープ、NFCピン、BLE出力などを変更する場合は、実際に読み込まれる側の設定へ反映し、Kconfig・生成DTS・実機で確認します。この文書の更新ではファームウェア設定を変更していません。

## 4. マトリックスと物理レイアウト

| 側 | 列 | 行 |
|---|---|---|
| 左（7列×5行） | `xiao_d` 0〜6 | `xiao_d` 7〜10、`gpio0` 9 |
| 右（8列×5行） | `xiao_d` 0〜7 | `xiao_d` 8〜10、`gpio0` 9・10 |

ダイオード方向は `col2row`。列は `GPIO_ACTIVE_HIGH`、行は `GPIO_ACTIVE_HIGH | GPIO_PULL_DOWN` です。P0.09/P0.10はNFC兼用ピンです。`xiao_d` の物理GPIO対応は使用するboard定義を参照します。

`cleave_hhjp.dtsi` の `default_transform` は5行×15列で70位置を列挙し、右側overlayが `col-offset = <7>` を設定します。`cleave_hhjp_physical_layout` はtransformとkscanを参照し、`chosen` の `zmk,physical-layout` から選択します。キーの幅・高さ・座標はcenti-keyunits（1U=100）で、ミリメートルではありません。
RGB LEDの定義はこのdtsiにはなく、boardと `rgbled_adapter` モジュールを使用します。

## 5. キーマップ

各レイヤーには70個のbindingがあります。

| 番号 | ノード / 表示名 | 内容 |
|---|---|---|
| 0 | `default_layer` / Default | HHKB JPベースの通常入力 |
| 1 | `fn_layer` / Fn | F1〜F12、音量・ミュート・Eject、ナビゲーション、Bluetooth、UF2移行 |

左右の専用Fnキーは `&mo 1`。左の旧LANG2位置は `&lt 1 INT5`、右Space直後の旧LANG1位置は通常の `&kp INT4` です。LANG2は短押しでInternational5、200msのhold-tap判定後はFnになります。隣の独立したKana位置は従来の `&kp LANG1` です。右側の並びはINT4、Kana、Alt、Fnです。`&lt` は `tap-preferred` で、別キーを押しただけでは即座にhold確定しません。Mouseレイヤーは削除しました。

Fn+Ctrl+1〜5は `BT_SEL 0`〜`BT_SEL 4`、Fn+Ctrl+Backspaceは `BT_CLR`。CtrlなしではF1〜F5 / Deleteです。`zmk,behavior-mod-morph` で実装しています。

### タッチパッド

右側TM040040の移動と左右タップクリックをinput-splitで左側へ転送します。`cleave_hhjp_left.overlay`のlistenerはFnレイヤー1で`trackpad_scroll`を適用し、横移動を抑制して縦スクロールに変換します。`src/trackpad_pointer.c`で`-Y × スクロール倍率 / 16`を計算し、端数を保持します。1.0倍は従来と同量です。ボタンイベントは変更しません。通常レイヤーではカーソル速度と加速を適用します。

LANG2長押しと専用Fnキーのどちらでもスクロールになります。旧マウスレイヤー、`src/mouse_speed.c`、専用behavior/scalerのbindingとCMake参照は削除しました。`src/trackpad_settings.c`でUSB Feature 7 version 2の変更・保存・固定感度1xの確認を行います。基本速度と最大倍率は0.1倍刻み、スクロール量は0.1～4.0倍です。旧保存値は引き継ぎ、感度を1x、スクロール量を1.0倍へ移行します。仕様と確認範囲は[タッチパッド設定](../tools/battery/trackpad-settings.md)を参照してください。設定の反映・保存・再起動後の保持はユーザー確認済みです。スクロール量は使い心地に合わせて調整してください。

### UF2移行

Fn+B（左）/ Fn+N（右）を2秒長押しすると、操作した側で `&bootloader` を呼びます。短押しはB / ＋。`boot_hold` は `tap-preferred` のhold-tapです。
USBを対象側につなぎ、左右が通常動作・接続している状態で操作します。詳細は[キー操作の手順](bootloader-keys.md)を参照してください。

## 6. ZMK Studio

左側設定の `CONFIG_ZMK_STUDIO=y` と左ビルドの `studio-rpc-usb-uart` snippetでUSB経由の編集に対応します。`CONFIG_ZMK_STUDIO_LOCKING=n` のため、このビルドはロック解除操作を要求しません。本リポジトリの案内は左側USB接続を使用します。

Studioでは既存のキー割り当て・ファームウェアに定義済みのbehaviorを編集します。新規マクロ・コンボ・behaviorの定義や、DTSにないレイヤーの追加はソース側で行います。JSONエクスポートや新規マクロ作成をこの構成の実装済み機能として案内しません。[ZMK v0.3のStudio説明](https://v0-3-branch.zmk.dev/docs/features/studio)も参照してください。

Studio保存済みの配置は `.keymap` の初期配置に優先します。新しい初期配置を使う場合はRestore Stock Settingsを実行します。通常の更新でsettings_resetは不要です。使用するとペアリング・保存済み設定を消去します。

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
| 7 | 32 | version=2、カーソル速度・加速・固定感度1x・Fnスクロール量の取得、変更、明示保存、通信診断 |

Windowsではcollection最大長32バイトでFeature Reportを読み、ID1/2は有効な7/6バイトを取り出します。ID4は8または32バイトを受け付け、余白はゼロのみです。
診断用ID6も32バイトで読み、先頭16バイトを取り出します。`sensor_channel_get` で既存センサーのキャッシュを取得し、追加のADCサンプリングは行いません。取得できない値はflagsでunknownを表します。残量変化イベントの経過時間はADC計測の経過時間とは異なります。記録ツールは[診断手順](../tools/battery/README.md#sudden-battery-percentage-changes-diagnostics)を参照してください。

右残量はsource=0の通知で更新し、未取得・切断時はunknownです。0%はunknownと区別します。値が変わらない間は通知が来ないことがあるため、残量には時間だけによる失効を設定していません。

電源状態は0=unknown、1=バッテリー、2=USB給電（充電信号なし）、3=充電中。`src/charge_status.c` はP0.17のactive-low CHGを入力として読み、VBUSを別に検出します。USBありの場合のみpull-upを使います。充電電流の設定変更は行いません。右側の暗号化GATT値を5秒ごとに取得し、切断または最終取得から約20秒超でunknownになります。
USB給電やCHG解除だけでは満充電とは判定しません。残量%はZMKの電圧による推定値です。
USB接続中の左側はスイッチOFF/ONにより測定電圧と残量が変わることを確認しました。残量確認時はスイッチONを使用します。経緯・測定値・確認範囲は[調査結果](battery-measurement.md)を参照してください。

ID3/5は `[ID, version, side, flags, build8, CHHP, chipID8, reserved]`。sideは0=左、1=右、flagsはbit0=更新対応、bit1=USB給電です。子機GATTは先頭16バイトのみで、親機キャッシュのchipIDはゼロです。子機情報は5秒ごとに取得し、切断または20秒超で失効します。

## 8. アプリからのUF2更新

`CMakeLists.txt` はGit HEADと `src/`、`config/`、`dts/`、`zephyr/`、CMake自身の内容から8桁のビルドIDを生成します。Gitコミットの短縮IDとは異なります。UF2には `CLEAVE_HHJP_UPDATE1|LEFT|<build8>` または `RIGHT` の識別子が入ります。

`src/app_update.c` はUSB要求から250ms後に、左なら `sys_reboot(RST_UF2)`、右なら既存split behaviorコマンドで右側の `bootload` を呼びます。右側は更新対応情報とUSB給電が確認できる場合のみ指示を受け付けます。

`tools/battery/firmware_update.py` はUF2 magic・nRF52840 family・256バイトpayload・欠落/重複・連続アドレス・左右とビルド識別子を検証します。対象は `0x27000` から始まり終端が `0xec000` 以下のアプリ領域です。検証済みデータをメモリに保持して書き込みます。
既存UF2ドライブがある場合は開始せず、新規ドライブが1台だけであること、XIAO Board-ID、コピー直前のvolume identityを確認します。左右の選択はUF2内の識別子で行い、UF2ドライブ自体に左右識別情報があるとは扱いません。

新規UF2ドライブ待ちは90秒、再起動後のビルド確認は60秒です。ファイルコピーやドライブ消失だけでは確認済み成功にしません。自動モードでは取得可能な対象chipIDも照合します（右側chipIDは取得できません）。
初回の右更新は旧親機で検証できずpendingになることがあります。同じアプリセッション内で左更新を確認した後、右のビルドを追加で30秒確認します。USBケーブル1本の場合の切り替え手順は[アプリの説明](../tools/battery/README.md)を参照してください。

キー操作による左右のUF2ドライブ表示は確認済みです。アプリによる実機への書き込みと、再起動後の左右ビルド照合は未確認です。

## 9. GitHub Actionsと配布

[`build-firmware.yml`](../.github/workflows/build-firmware.yml) は対象パスの変更を伴う `main` pushとPull Requestで起動します。PRの宛先ブランチ制限はありません。対象パスは `config/**`、`src/**`、`tools/battery/**`、`CMakeLists.txt`、`build.yaml`、ワークフロー自身です。`build-user-config.yml@v0.3-branch` を呼び出します。
`dts/**` と `zephyr/**` は現在のpath filterに含まれないため、それらだけの変更では起動しません。

`build.yaml` は次の構成です。

```yaml
include:
  - board: seeeduino_xiao_ble
    shield: cleave_hhjp_left rgbled_adapter
    snippet: studio-rpc-usb-uart
  - board: seeeduino_xiao_ble
    shield: cleave_hhjp_right rgbled_adapter
  - board: seeeduino_xiao_ble
    shield: settings_reset
```

Studioの有効化は左側 `.conf` にあります。`firmware` artifact内の左右用UF2を対象へ書き込みます。settings_resetはアプリ更新の対象外です。
[`release.yml`](../.github/workflows/release.yml) の手動実行は `run_id`、`version`、`prerelease` を受け取り、指定runのartifactをReleaseへ添付します。EXEはこのActionsでは生成せず、[`build-exe.ps1`](../tools/battery/build-exe.ps1) で作成します。

カスタマイズするときはこのリポジトリ全体をフォークしてください。シールド定義だけを別テンプレートへコピーすると独自CモジュールやDTS bindingが欠落します。
ローカルビルドでは依存を `config/west.yml` に従って取得し、`ZMK_CONFIG` に `config/`、`ZMK_EXTRA_MODULES` にこのリポジトリのルートを指定します。追加モジュールの指定は[ZMKのビルド説明](https://zmk.dev/docs/development/local-toolchain/build-flash)を参照してください。この文書の照合ではローカルのファームウェア再ビルドは実施していません。

## 10. 変更後の確認

- Actionsの読み込みログと実効Kconfig、生成DTSを確認する
- UF2の構造・HID記述子・設定を[検証ツール](../tools/battery/firmware-tools.md)で確認する
- 対象側へ書き込み、通常入力・Fn・マウス・Bluetooth切替・Studioを確認する
- 残量・充電表示はUSBの抜き差しと子機の電源OFF/ONで確認する
- 更新機能は右→左で実機確認し、再起動後のビルド一致を確認する

ケース・配線・バッテリーの実装条件は[組み立てガイド](../build-guide/01-ASSEMBLY.md)と[ケース設計ガイド](../build-guide/03-2-CUSTOM_CASE.md)に従います。ソース確認だけでは寸法の適合、充電時間、電池持ち、実機の更新成功を証明しません。
