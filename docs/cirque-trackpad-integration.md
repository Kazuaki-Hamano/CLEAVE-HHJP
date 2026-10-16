# TM040040-2024-302 組み込み

対象: CLEAVE HHJP、XIAO nRF52840 Plus、ZMK v0.3-branch。
2026-10-16: 初回ビルド4222ac0bで移動を確認。8c7b8e50のY軸反転後、ユーザーが上下左右の正常動作を確認しました。次に左右タップクリックを有効化し、実機確認待ちです。

## 配線

| 色 | パッドのランド | XIAO | GPIO |
|---|---|---|---|
| 黒 | GND | GND | — |
| 赤 | VDD | 3V3 | — |
| 茶 | SS | D11 | P0.15 |
| 橙 | DR | D12 | P0.19 |
| 黄 | SCK | D17 | P1.03 |
| 緑 | SO / MISO | D18 | P1.05 |
| 青 | SI / MOSI | D19 | P1.07 |

VDDは2.5～3.6V仕様。5V/VBUSやBAT+には接続しません。SPI用R1は外しません。B1/B2/B3、SCL/SDA、FFCコネクタは使いません。

USB端子を上、シールド面を手前にしたXIAOの表面では、左側D0/D1間がD11、D1/D2間がD12、右側D10/D9間がD19、D9/D8間がD18、D8/D7間がD17です。右側の大きな端子の上から2番目がGND、3番目が3V3。下端の2列×3個の長方形パッドは今回のGPIOではありません。裏面への配線やXIAOの取り外しは不要です。

- [Cirque仕様書](https://www.mouser.com/pdfdocs/TM040040_SPI-I2C-PINNTrackpad_SPEC1-21.pdf)
- [Seeed端子表](https://wiki.seeedstudio.com/XIAO_BLE/)

## ファームウェア

- [petejohanson/cirque-input-module](https://github.com/petejohanson/cirque-input-module)の`0de55f36bc720b5be3d8880dc856d4d78baf5214`を基に、実行時の感度変更を追加したドライバーを`src/pinnacle/`へ取り込みました。外部west依存は削除しました。
- 右側の`Kconfig.defconfig`で`ZMK_POINTING`と`SPI`を有効化。右側には従来どおり共通の`cleave_hhjp.conf`が読み込まれます。
- 右overlayの`spi2`を追加GPIOに割り当て、1MHzのSPI、CS active-low、DR active-highで読み取ります。キーのD0～D10、P0.09、P0.10は変更しません。
- 共通`cleave_hhjp_trackpad.dtsi`に`zmk,input-split`（ID 0）を定義。右側の実デバイス→左右間BLE→左側listener→USB/BLEのマウスレポートという経路です。
- 左右両方のUF2を更新してください。右だけの更新では転送先がありません。
- 初回対応済みの4222ac0bから上下反転を修正する際は、右側だけの更新で反映されます。
- 常時カーソル移動と左右タップクリックを有効化。`no-taps`と`no-secondary-tap`を指定しないことで、通常タップとチップ内蔵の右クリック領域を利用します。領域は標準方向の右上で、現ドライバーに位置・広さの指定項目はありません。実装方向での位置は実機で確認します。`sensitivity = "1x"`、`sleep`、`y-invert`を指定。
- ユーザーが通常タップの左クリックと右下端の右クリックを確認済み。
- Mouseレイヤーと専用速度処理を削除。旧LANG1位置は通常のINT4キーに戻します。
- LANG2長押しでFnレイヤー1が有効な間、左側listenerでパッドの上下移動を縦スクロールに変換します。横移動を0倍、Y移動を-1/16倍（端数保持）にしてからホイールへ変換。左右の専用Fnキーでも有効です。タップクリックとFnのキー操作は維持します。
- 基本速度・加速の強さ・最大倍率・検出感度をアプリから変更し、左側へ保存できます。操作手順・範囲・初期値・実機確認項目は[タッチパッド設定](../tools/battery/trackpad-settings.md)を参照してください。速度・加速とFnスクロールは別に処理します。

## 検証

ビルド後、左右それぞれの生成DTS・Kconfig、Pinnacleドライバーとinput-splitのリンク、UF2識別子を確認します。

実機では次を確認してください。

1. 左右を更新して再起動し、通常キーと左右の接続を確認。
2. パッドでカーソルが動くか、指の移動方向と合うかを確認。
3. 通常領域のタップで左クリック、右下端で右クリック、LANG2長押しで縦スクロールとなることを確認。
4. USB接続と、使用する場合はPCへのBluetooth接続を確認。
5. 放置後の復帰、左右の電源再投入・再接続を確認。

ビルド成功と実機動作確認は別です。未接続時の継続動作、向き、感度、消費電力は実機で評価します。
