# 印尼 IDX 股票支持指南

本文档说明如何在本系统中使用印尼证券交易所（IDX）股票。

## 快速开始

在 `STOCK_LIST` 中使用 Yahoo Finance `.JK` 后缀格式添加印尼股票：

```env
# 含印尼股票的配置示例
STOCK_LIST=600519,BBCA.JK,TLKM.JK,BBRI.JK
```

支持的格式示例：

| 股票 | 代码 | 说明 |
|------|------|------|
| Bank Central Asia | `BBCA.JK` | 印尼最大私人银行 |
| Telkom Indonesia | `TLKM.JK` | 印尼国有电信运营商 |
| Bank Rakyat Indonesia | `BBRI.JK` | 印尼国有银行 |
| Astra International | `ASII.JK` | 印尼综合企业 |
| Bank Mandiri | `BMRI.JK` | 印尼最大银行 |

## 数据源与延迟

- **数据来源**：Yahoo Finance（通过 `yfinance` 库）
- **数据延迟**：约 15 分钟（免费公开数据源的标准延迟）
- **历史数据**：支持完整的日线 OHLCV 数据，适合技术分析
- **实时行情**：近实时（有延迟）的当前价格、涨跌幅等

## 环境变量

| 变量名 | 默认值 | 说明 |
|--------|--------|------|
| `IDX_POLL_INTERVAL_SECONDS` | `300` | 近实时行情轮询间隔（秒），建议 300–600；低于 60 秒可能触发 Yahoo Finance 限流 |

配置示例（`.env` 文件）：

```env
# IDX 轮询间隔（秒）：每 5 分钟刷新一次行情
IDX_POLL_INTERVAL_SECONDS=300
```

## 技术实现

### 代码格式

IDX 股票使用 Yahoo Finance 标准的 `.JK` 后缀：
- 格式：`<代码>.JK`（大小写均可）
- 示例：`BBCA.JK`、`TLKM.JK`、`bbca.jk`

### 路由策略

系统通过 `is_idx_stock_code()` 函数识别 `.JK` 后缀，自动将 IDX 股票直接路由到 YfinanceFetcher（跳过不支持 IDX 的国内数据源如 Efinance、AkShare 等），避免无效请求。

### 交易日历

IDX 使用 `XIDX`（印尼证券交易所）交易日历，时区为 `Asia/Jakarta`（UTC+7）。当 `TRADING_DAY_CHECK_ENABLED=true` 时，系统会自动判断印尼市场是否开市。

## 限制说明

1. **数据延迟**：Yahoo Finance 免费数据有约 15 分钟延迟，不适合高频交易决策。
2. **历史数据**：部分流动性较低的股票历史数据可能不完整。
3. **成交额**：`amount`（成交额）字段通过 `volume × close` 估算，非精确值。
4. **汇率**：报告中价格以印尼盾（IDR）显示。

## 常见问题

**Q: 如何验证 IDX 股票代码是否有效？**

运行以下 Python 代码验证：
```python
import yfinance as yf
ticker = yf.Ticker('BBCA.JK')
print(ticker.history(period='5d'))
```

**Q: 能否结合 A 股和 IDX 股票一起分析？**

可以。在 `STOCK_LIST` 中混合使用不同市场的代码，系统会自动识别并路由到对应数据源：
```env
STOCK_LIST=600519,000001,BBCA.JK,TLKM.JK,AAPL
```

**Q: IDX 股票支持哪些技术分析指标？**

与其他市场相同，支持所有基于 OHLCV 的指标：MA、MACD、RSI、布林带、乖离率等。
