# ケース設計ツール

リポジトリのルートから実行します。元データは `models/` の STL、
生成物は `output/case-design/` に保存します。

```powershell
python tools/case-design/analyze.py
python tools/case-design/build.py
python tools/case-design/verify.py
python tools/case-design/check_parameters.py
```

必要な Python パッケージは numpy、trimesh、networkx、shapely、ezdxf、cadquery、
matplotlib です。既存の `output/case-design/python-packages/` も読み込みます。
`build.py` は `feature-template.fs` から Onshape 用 FeatureScript を生成します。
STL の断面に基づく近似モデルで、元の CAD 履歴を復元するものではありません。

`verify.py` と `check_parameters.py` は `build.py` の生成物を使用します。

対象は左右ベース、左右トップカバー、左右Chocトッププレート、電源スイッチノブの7部品です。MXトッププレートや別のトップカバーを自動処理するツールではありません。
`build.py` のSTEP・DXF・FeatureScript・画像・検証JSONは `output/case-design/onshape/`、`analyze.py` の解析結果は `output/case-design/analysis.json` に保存します。ZIP作成は現在のスクリプトには含まれません。
ローカルの幾何検証とOnshape上での生成・パラメーター変更の確認、実機との干渉確認は別に行ってください。
