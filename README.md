# MonitoringIndicator

MT4カスタムインジケーターのアラートを監視し、MT5（Vantage Trading）で自動注文を行うPythonシステム。

## 機能

- MT4アラートログのリアルタイム監視
- シグナル解析（BUY/SELL、SL/TP抽出）
- 重複シグナルの自動排除（3分以内）
- MT5への自動注文実行
- 通貨ペアごとのロットサイズ設定
- 週末取引停止機能（XAUUSD）
- 詳細なログ出力

## 対応通貨ペア

| シンボル | 週末取引 |
|----------|----------|
| XAUUSD | 停止 |
| BTCUSD | 24/7 |
| ETHUSD | 24/7 |

## 要件

- Windows OS（MT5パッケージはWindows専用）
- Python 3.11以上
- MT4ターミナル（インジケーター実行用）
- MT5ターミナル（Vantage Trading、注文実行用）

## インストール

```bash
# リポジトリをクローン
git clone https://github.com/yourusername/MonitoringIndicator.git
cd MonitoringIndicator

# 仮想環境を作成
python -m venv .venv

# 仮想環境を有効化（Windows）
.venv\Scripts\activate

# 依存パッケージをインストール
pip install -r requirements.txt
```

## 設定

1. 設定ファイルをコピー

```bash
cp config/settings.example.yaml config/settings.yaml
```

2. `config/settings.yaml`を編集

```yaml
mt4:
  alert_log_path: "C:/path/to/mt4/logs/alerts.log"

mt5:
  login: 12345678
  password: "your_password"
  server: "VantageInternational-Live"

symbols:
  XAUUSD:
    enabled: true
    lot_size: 0.01
    weekend_stop: true
```

## 使用方法

```bash
# デフォルト設定で起動
python -m src.main

# 設定ファイルを指定して起動
python -m src.main -c config/settings.yaml
```

## シグナル形式

インジケーターが出力するアラート形式：

```
BUY XAUUSD SL:1920.50 TP:1950.00
SELL BTCUSD SL:45000.00 TP:42000.00
```

## テスト

```bash
# テスト実行
pytest tests/ -v

# カバレッジ付き
pytest tests/ -v --cov=src
```

## ログ

ログは `logs/trading.log` に出力されます。

```
2025-01-16 10:30:00 | INFO     | Signal detected: BUY XAUUSD SL:1920.5 TP:1950.0
2025-01-16 10:30:01 | INFO     | Order executed: BUY XAUUSD Lot:0.01 Ticket:123456
```

## 注意事項

- MT4とMT5は同一PC上で動作している必要があります
- MT5ターミナルは起動・ログイン状態を維持してください
- アルゴリズム取引がMT5で有効になっている必要があります

## ライセンス

MIT License

## ドキュメント

- [詳細仕様書](./SPECIFICATION.md)
- [Claude Code指示書](./CLAUDE.md)
