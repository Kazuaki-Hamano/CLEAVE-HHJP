# CLEAVE HHJP
日本語配列互換 / 完全無線 / Choc MX両対応のキーボード自作キット「CLEAVE HHJP」のドキュメントリポジトリです。

<p align="center">
  <img src="build-guide/images/visual/cleave-hhjp-build-variations.png" alt="CLEAVE HHJPの複数作例" width="100%">
</p>

<p align="center">
  <img src="build-guide/images/visual/cleave-hhjp-white-transparent-build.png" alt="白い透明ケースのCLEAVE HHJP作例" width="49%">
  <img src="build-guide/images/visual/cleave-hhjp-black-trackpad-setup.png" alt="黒いCLEAVE HHJPとトラックパッドの作例" width="49%">
</p>

購入先：[BOOTH販売ページ](https://rimebeck.booth.pm/items/8395519)

## ドキュメント

- [ビルドガイド](build-guide/README.md)
  組み立て、ファームウェア書き込み、ケース作成、完成後の使い方、カスタマイズ方法をまとめています。
- [現在のファームウェア設計](docs/firmware_design.md)
  このフォークのキーマップ、実効設定の確認方法、USB残量・充電状態・更新機能をまとめています。
- [Windowsバッテリーアプリと更新手順](tools/battery/README.md)
- [キー操作によるUF2モード移行](docs/bootloader-keys.md)
- [タッチパッド設定](tools/battery/trackpad-settings.md)
- [生成物の保存場所](docs/generated-output.md)
- [ケース設計ツール](tools/case-design/README.md)

このフォークでは右側タッチパッド、Fn併用スクロール、アプリでの速度・加速・スクロール量設定、左右のバッテリー・充電状態表示、アプリ更新用プロトコルを追加しています。旧マウスレイヤーは削除済みです。
以下の標準配布元のReleaseが、このフォークの追加機能を含むとは限りません。
追加機能を使う場合は、このリポジトリのActionsで生成した左右用UF2を使用してください。

## 関連リンク

- [ファームウェア配布ページ](https://github.com/Rimebeck/Cleave-HHJP/releases)
- [ケースの3Dモデル・PCB 3Dデータ](https://github.com/Rimebeck/Cleave-HHJP/tree/main/models)

## 問い合わせ・不具合報告

ご不明な点はビルドガイドリポジトリの[Issues](https://github.com/Rimebeck/Cleave-HHJP/issues)またはBOOTHの購入者問合せからご連絡ください。

----
QRコードは株式会社デンソーウェーブの登録商標です
