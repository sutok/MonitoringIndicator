# MonitoringIndicator

[![CI](https://github.com/sutok/MonitoringIndicator/actions/workflows/ci.yml/badge.svg)](https://github.com/sutok/MonitoringIndicator/actions/workflows/ci.yml)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

MT4カスタムインジケーターのアラートを監視し、MT5（Vantage Trading）で自動注文を行うPythonシステム。

## 機能

- MT4アラートログのリアルタイム監視
- シグナル解析（BUY/SELL、SL/TP抽出）
- 重複シグナルの自動排除（3分以内）
- MT5への自動注文実行
- 通貨ペアごとのロットサイズ設定
- 週末取引停止機能（XAUUSD）
- MT4 EAによる取引ON/OFF制御
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

### パス記法について（Windows）

設定ファイル内のパスは **スラッシュ `/` を使用**してください。

```yaml
# ✅ 正しい記法
alert_log_path: "C:/Users/YourName/AppData/Roaming/MetaQuotes/Terminal/ABC123/MQL4/Logs/{date}.log"

# ❌ バックスラッシュは使わない
alert_log_path: "C:\Users\YourName\..."
```

Windowsエクスプローラーからコピーしたパスは `\` になりますが、`/` に置き換えてください。
Pythonが内部で自動的に正しく処理します。

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

## MT4 EA設定（取引制御）

MT4側で取引のON/OFFを制御するためのEAを設定します。

1. `mt4/TradeController.mq4` をMT4のExpertsフォルダにコピー
   ```
   C:\Users\{ユーザー名}\AppData\Roaming\MetaQuotes\Terminal\{ID}\MQL4\Experts\
   ```

2. MT4でコンパイル（Navigatorで右クリック → Compile）

3. チャートにEAをアタッチ

4. パラメータを設定
   | パラメータ | 説明 | デフォルト |
   |------------|------|------------|
   | TradeEnabled | MT5注文の有効/無効 | true |
   | UpdateInterval | 更新間隔（秒） | 1 |
   | ControlFileName | 制御ファイル名 | trade_control.json |

5. `config/settings.yaml` に制御ファイルパスを設定
   ```yaml
   trade_control:
     enabled: true
     control_file_path: "C:/Users/{ユーザー名}/.../MQL4/Files/trade_control.json"
     default_enabled: true
   ```

## 使用方法

```bash
# デフォルト設定で起動
python -m src.main

# 設定ファイルを指定して起動
python -m src.main -c config/settings.yaml

# ドライランモード（MT5に接続せずシグナル監視のみ）
python -m src.main --dry-run
```

### コマンドラインオプション

| オプション | 説明 |
|------------|------|
| `-c`, `--config` | 設定ファイルのパス（デフォルト: `config/settings.yaml`） |
| `-d`, `--dry-run` | MT5に接続せず、シグナル検出のみを標準出力に表示 |

## シグナル形式

インジケーターが出力するアラート形式：

**エントリーシグナル:**
```
Ark_BTC Alert: BUY XAUUSD SL:1920.50 TP:1950.00
Ark_BTC Indicator SELL BTCUSD SL:45000.00 TP:42000.00
```

**決済シグナル:**
```
ロング決済サイン at price: 2650.50
ショート決済サイン at price: 2600.00
```

決済シグナルを受信すると、対象シンボルの全ポジションを成行で決済します。

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
