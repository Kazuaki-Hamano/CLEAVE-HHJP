# タッチパッド設定

現行ファームウェアは[DYA Studio](https://studio.dya.cormoran.works/)で調整します。Windowsアプリの旧トレイメニュー・USB Feature 7による設定は使用しません。アプリの残量表示・診断・更新機能は継続使用できます。

1. 左側をUSB接続、またはFn＋UからBluetooth接続します。
2. DYAの「設定」→詳細設定を開きます。
3. `cleave_left_scroll` の `scroll_percent` で左のスクロール量を調整します。
4. `cleave_right_trackpad` で右の基本速度、加速の強さ、加速上限、右端スクロール量を調整します。
5. 各グループを保存します。電源再投入後にも値が残ることを確認します。

倍率は100が1倍です。左は縦横スクロールとFn中の戻る／進む、右はFn中もカーソル移動です。感度は両側とも1x固定。右の加速を0にすると、加速上限の設定は効きません。

項目の初期値・保存と再接続の扱いは[DYA Studioガイド](../../docs/dya-studio.md)を参照してください。BLEの再接続が進まない場合はタブを閉じて開き直します。取り付けは[TM040040ガイド](../../build-guide/06-TRACKPAD.md)、配線・実装は[Cirque組み込み](../../docs/cirque-trackpad-integration.md)、現行UF2は[生成物一覧](../../docs/generated-output.md)に記載しています。
