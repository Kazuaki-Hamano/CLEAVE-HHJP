# TM040040-2024-302 組み込み

対象: CLEAVE HHJP、XIAO nRF52840 Plus、ZMK v0.3-branch。
2026-10-16: 初回ビルド4222ac0bでユーザーがカーソル移動を確認。左右は正常、上下は逆だったため、右側の`y-invert`を追加しました。反転後の実機確認はこれからです。

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

- `config/west.yml`に[petejohanson/cirque-input-module](https://github.com/petejohanson/cirque-input-module)を追加。依存は`0de55f36bc720b5be3d8880dc856d4d78baf5214`に固定。
- 右側の`Kconfig.defconfig`で`ZMK_POINTING`と`SPI`を有効化。右側には従来どおり共通の`cleave_hhjp.conf`が読み込まれます。
- 右overlayの`spi2`を追加GPIOに割り当て、1MHzのSPI、CS active-low、DR active-highで読み取ります。キーのD0～D10、P0.09、P0.10は変更しません。
- 共通`cleave_hhjp_trackpad.dtsi`に`zmk,input-split`（ID 0）を定義。右側の実デバイス→左右間BLE→左側listener→USB/BLEのマウスレポートという経路です。
- 左右両方のUF2を更新してください。右だけの更新では転送先がありません。
- 初回対応済みの4222ac0bから上下反転を修正する際は、右側だけの更新で反映されます。
- 初回は常時カーソル移動のみ。`no-taps`でタップクリックを無効化し、`sensitivity = "1x"`、`sleep`を指定。回転・反転は実機の向きを見て調整します。
- 既存のW/A/S/D、クリック、スクロール、1/2/3とShift/Altの速度設定は維持。速度処理は既存の`mmv_input_listener`専用で、パッドの移動には適用しません。
- `mouse_speed.c`はホストへ送信する左側のみコンパイルし、右側に中央専用HID処理をリンクしません。

## 検証

ビルド後、左右それぞれの生成DTS・Kconfig、Pinnacleドライバーとinput-splitのリンク、UF2識別子を確認します。

実機では次を確認してください。

1. 左右を更新して再起動し、通常キーと左右の接続を確認。
2. パッドでカーソルが動くか、指の移動方向と合うかを確認。
3. タップでクリックされないこと、既存マウスレイヤーのクリック・スクロール・速度変更を確認。
4. USB接続と、使用する場合はPCへのBluetooth接続を確認。
5. 放置後の復帰、左右の電源再投入・再接続を確認。

ビルド成功と実機動作確認は別です。未接続時の継続動作、向き、感度、消費電力は実機で評価します。
