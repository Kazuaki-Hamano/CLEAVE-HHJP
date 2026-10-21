# ファームウェア検証・診断ツール

独自Windowsアプリは廃止・削除しました。EXEの作成・配布・トレイ常駐・アプリからの書き込み機能はありません。キー・マクロ・トラックパッド設定は[DYA Studio](../../docs/dya-studio.md)を使用します。

## 残すツール

- [ファームウェア取得・検証](firmware-tools.md)：Actions成果物の取得、UF2とビルド設定の確認。
- `firmware_update.py`：既存検証スクリプト向けのオフラインUF2検証。旧名を維持しますが、デバイス操作・書き込み機能は削除済みです。
- `battery_diagnostics.py`：生のUSB HID値とキャッシュ電圧を読み取るCLI。ADC計測や設定変更は行いません。
- `test_trackpad_*.c` と [dev/](dev/README.md)：現行ファームウェアの検証用。

## Firmware updater

旧Windowsアプリによる更新は廃止しました。[キー操作によるUF2モード移行](../../docs/bootloader-keys.md)を使い、対応するUF2をドライブへコピーしてください。通常の更新に`settings_reset`は不要です。

## Sudden battery-percentage changes: diagnostics

過去の調査結果は[残量急変の調査](../../docs/battery-measurement.md)を参照してください。既存のJSONLログは保持しています。

Pythonとhidapiを用意してリポジトリのルートから実行します。

```powershell
python -m pip install -r tools/battery/requirements.txt
python tools/battery/battery_diagnostics.py --duration 600
```

左側をUSB接続して使用します。診断ツールのEXE版は削除しました。通常の設定変更にはDYA Studioを使用します。
