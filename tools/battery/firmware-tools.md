# ファームウェア取得・確認用ツール

リポジトリのルートから実行します。

```powershell
python tools/battery/github_build.py
python tools/battery/github_build.py download
python tools/battery/verify_firmware.py output/firmware/9b4ba539
```

`github_build.py` は Git の認証情報を使用して
`Kazuaki-Hamano/CLEAVE-HHJP` の `battery/peripheral-fetch` ブランチの
最新 Actions 実行を確認します。`download` 指定時は完了済み実行の
成果物とログを `output/firmware/` に取得します。
このヘルパーの取得対象は旧開発ブランチです。現行DYA版は[Actions Run 39358929004](https://github.com/Kazuaki-Hamano/CLEAVE-HHJP/actions/runs/39358929004)から取得します。確認済みソースは`9b4ba539`、埋込ビルドIDは`e377a35a`です。保持する旧版と更新対象は[生成物の保存場所](../../docs/generated-output.md)を参照してください。新しいビルドを確認する場合は取得先に置き換えてください。`download`はrunの完了を条件としており、ビルド成功を保証する操作ではありません。

`verify_firmware.py` は取得した UF2 の構造、左側の HID 記述子、
ビルドログ内の設定を検証し、同じフォルダーに `checksums.json` を保存します。
バッテリー・充電状態・アプリ更新に対応したビルド向けの確認です。
