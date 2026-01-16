# MonitoringIndicator - Claude Code指示書

## プロジェクト概要

MT4カスタムインジケーターのアラートを監視し、MT5（Vantage Trading）で自動注文を行うPythonシステム。

**詳細仕様:** [SPECIFICATION.md](./SPECIFICATION.md)を参照

## アーキテクチャ

```
MT4アラートログ → Python監視 → シグナル解析 → 重複排除 → MT5注文
```

### コアモジュール

| モジュール | 責務 |
|------------|------|
| `alert_monitor.py` | MT4アラートログのファイル監視 |
| `signal_parser.py` | アラートメッセージの解析 |
| `order_executor.py` | MT5への注文実行 |
| `config.py` | YAML設定の読み込み・管理 |
| `logger.py` | ログ出力管理 |

## 開発ルール

### コーディング規約

- **言語:** Python 3.11+
- **フォーマット:** Black, isort
- **型ヒント:** 必須（mypy準拠）
- **docstring:** Google Style
- **命名規則:**
  - クラス: PascalCase
  - 関数/変数: snake_case
  - 定数: UPPER_SNAKE_CASE

### ディレクトリ構造

```
src/           # ソースコード
config/        # 設定ファイル
logs/          # 出力ログ（gitignore対象）
tests/         # テストコード
```

### 依存パッケージ

```
metatrader5>=5.0.45    # MT5連携
watchdog>=3.0.0        # ファイル監視
PyYAML>=6.0            # 設定ファイル
```

## シグナル形式

### アラートメッセージ

```
{ACTION} {SYMBOL} SL:{STOP_LOSS} TP:{TAKE_PROFIT}
```

**例:**
```
BUY XAUUSD SL:1920.50 TP:1950.00
SELL BTCUSD SL:45000.00 TP:42000.00
```

### 対応シンボル

- XAUUSD（週末停止）
- BTCUSD
- ETHUSD

## 重要な制約

### MT5接続

- `metatrader5`パッケージはWindows専用
- MT5ターミナルが起動・ログイン状態が必須
- 接続エラー時は自動リトライ（5秒間隔、最大10回）

### シグナル処理

- **重複排除:** 同一シンボル+ACTIONが3分以内は無視
- **処理遅延:** シグナル検知〜注文実行は1秒以内
- **複数ポジション:** 許可

### 取引時間制限

| シンボル | 制限 |
|----------|------|
| XAUUSD | 週末停止（金曜クローズ〜日曜オープン） |
| BTCUSD | なし |
| ETHUSD | なし |

## テスト方針

### 単体テスト対象

- `signal_parser.py` - 各種メッセージ形式のパース
- `config.py` - 設定読み込み、バリデーション
- 重複排除ロジック

### モックが必要な箇所

- MT5接続（`metatrader5`パッケージ）
- ファイルシステム操作

### テスト実行

```bash
pytest tests/ -v
```

## 設定ファイル

### 必須設定項目

```yaml
mt4:
  alert_log_path: "..."  # MT4アラートログのパス

mt5:
  login: 12345678
  password: "..."
  server: "VantageInternational-Live"

symbols:
  XAUUSD:
    enabled: true
    lot_size: 0.01
    weekend_stop: true
```

### セキュリティ

- `config/settings.yaml`は`.gitignore`に追加
- `config/settings.example.yaml`をテンプレートとして提供

## エラーハンドリング

| エラー種別 | 対処 |
|------------|------|
| MT5接続エラー | リトライ後、ログ出力して継続 |
| 注文エラー | ログ出力、次のシグナルを処理 |
| パースエラー | 警告ログ、該当シグナルをスキップ |

## 将来の拡張予定

- 複数口座/ブローカー対応
- WebUI（設定変更、ステータス確認）
- 外部通知（LINE、Discord）

## 開発時の注意

1. **MT5パッケージのテスト**
   - 実際のMT5環境がないとテスト不可
   - CI/CDではモックを使用

2. **アラート形式の変更**
   - インジケーターのアップデートで形式が変わる可能性
   - パーサーは拡張しやすい設計に

3. **タイムゾーン**
   - MT4/MT5のサーバー時間を考慮
   - 週末判定はサーバー時間基準

4. **ログ**
   - 機密情報（パスワード等）をログに出力しない
   - デバッグ用の詳細ログはDEBUGレベルで

## コマンド

```bash
# 開発環境セットアップ（推奨: pyproject.toml使用）
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -e ".[dev]"

# または requirements-dev.txt 使用
pip install -r requirements-dev.txt

# テスト実行
pytest                    # 基本
pytest --cov=src          # カバレッジ付き

# 型チェック
mypy src/

# フォーマット
black src/ tests/
isort src/ tests/

# 本番実行
python -m src.main
# または
monitoring-indicator  # pip install -e . 後
```

## プロジェクト設定

- **pyproject.toml** - 依存関係とツール設定の一元管理
- **requirements.txt** - 本番依存関係（pip互換）
- **requirements-dev.txt** - 開発依存関係
