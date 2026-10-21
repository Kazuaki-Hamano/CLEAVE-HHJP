# TM040040-2024-302 組み込み

取り付けと配線の記録は[ハードウェア](../build-guide/customizations/hardware.md)、調整は[DYA Studioガイド](dya-studio.md)を参照してください。この文書では配線とドライバー実装を扱います。

対象はCLEAVE HHJP、左右のXIAO nRF52840 PlusとCirque TM040040です。現行は固定リビジョンのcormoran ZMK／Zephyr 4.1構成で、詳細は[ファームウェア設計](firmware_design.md)に記載します。

## ドライバーと入力経路

- `src/pinnacle/` はpetejohanson/cirque-input-moduleの固定版を基に取り込んだドライバーです。出典・ローカル変更は同ディレクトリの `UPSTREAM.md` を参照します。
- 左右ともD11＝CS、D12＝DR、D17＝SCK、D18＝MISO、D19＝MOSI。SPIは1MHz。VDDはXIAOの3V3、GNDはGNDです。BAT+やVBUSへ接続しません。
- 右側は実デバイス→`trackpad_split`→BLE→左側listener→USB／BLEマウス。左側はローカルSPI→専用listenerで、BLE転送しません。
- 右はFn中もカーソル、左は縦横スクロール、Fn中は左右スワイプで戻る／進む。Fn＋Q／Eは左／右クリックです。
- 感度1x、`sleep`、`y-invert` を使用します。Sleep Intervalは50。左右の速度・端数状態を分離し、設定の計算と保存は左側で行います。
- 通常のタップクリックとチップ内蔵の右クリック領域を使用します。取り付け方向で右下端の右クリックを確認済みです。領域の位置・広さを変更する項目は公開していません。
- 右端スクロールはチップ内蔵機能です。通常時・Fn中とも利用できます。2本指スクロールではありません。
- 調整はDYA詳細設定の `cleave_left_scroll`／`cleave_right_trackpad`。旧Windows設定用のFeature 7は廃止しました。初回移行時は左右を対応UF2へ更新します。

通常入力、左右パッド、設定保存、スリープからの左右キー復帰、DYAのマクロ割り当てはユーザー確認済みです。消費電流の実測や全ての取り付け方向の検証をしたものではありません。


## 配線

左右それぞれのXIAOへ、同じ端子割り当てで接続します。次の色は右側用です。

| 色 | パッドのランド | XIAO | GPIO |
|---|---|---|---|
| 黒 | GND | GND | — |
| 赤 | VDD | 3V3 | — |
| 茶 | SS | D11 | P0.15 |
| 橙 | DR | D12 | P0.19 |
| 黄 | SCK | D17 | P1.03 |
| 緑 | SO / MISO | D18 | P1.05 |
| 青 | SI / MOSI | D19 | P1.07 |

左側のケーブル色は以下です。

| 色 | パッド端子 | 左XIAO |
|---|---|---|
| 黒 | GND | GND |
| 白 | VDD | 3V3 |
| 灰 | SS / CS | D11 |
| 紫 | DR | D12 |
| 黄 | SCK | D17 |
| 緑 | SO / MISO | D18 |
| 青 | SI / MOSI | D19 |

VDDは2.5～3.6V仕様。5V/VBUSやBAT+には接続しません。SPI用R1は外しません。B1/B2/B3、SCL/SDA、FFCコネクタは使いません。

USB端子を上、シールド面を手前にしたXIAOの表面では、左側D0/D1間がD11、D1/D2間がD12、右側D10/D9間がD19、D9/D8間がD18、D8/D7間がD17です。右側の大きな端子の上から2番目がGND、3番目が3V3。下端の2列×3個の長方形パッドは今回のGPIOではありません。裏面への配線やXIAOの取り外しは不要です。

- [Cirque仕様書](https://www.mouser.com/pdfdocs/TM040040_SPI-I2C-PINNTrackpad_SPEC1-21.pdf)
- [Seeed端子表](https://wiki.seeedstudio.com/XIAO_BLE/)
