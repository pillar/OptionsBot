# AI Options Trader: 指令与规范 (claude.md)

## 1. 项目目标
构建一个全自动、高胜率的美股周内期权交易系统。可以从 `target_list.py` 中维护的自选池里选择最合适的股票（默认 GOOG/AAPL/MSFT）执行 Covered Call，也可从指数池（默认 SPX）构建 Put Credit Spread。

## 1.5 策略拆分说明
- Covered Call lane：在持有的股票上卖出 Delta<0.15 的 Call，赚取权利金并通过滚动保持低 Delta 曝光。
- Put Credit Spread lane：在指数上做 Delta≈0.07 的卖出 + 保护价差，限损并产出现金流。
默认将这两条线保持独立以便分别监督和风控。如果未来想做跨策略对冲，请在 `TODO.md` 或此文件中注明目标与约束。

## 2. 核心数学约束
AI 在执行或生成代码时，必须严格遵守以下参数：
- **Covered Call**：目标 $\Delta < 0.15$，行权日选取最近的周五。每次选标之前从 `target_list.py` 中筛出持仓足够的候选股票，再应用这个 Delta 目标。
- **Credit Spread**：卖出端 $\Delta \approx 0.07$，买入端（保险）与卖出端间隔 20-50 点。指数标的从 `target_list.py` 的指数池中依次尝试。
- **Rolling 触发:** 当空头合约 $\Delta > 0.45$ 或 DTE (到期天数) < 1 时强制执行滚动。
- **Net Credit 验证:** 任何滚动操作必须保证 $New\_Credit - Old\_Cost > Commission + Slippage$。

## 3. 代码开发规范 (Python / ib_insync)
- **异步驱动:** 必须使用 `asyncio` 和 `ib_insync` 的异步方法。
- **异常处理:** 所有的 API 调用（如 `reqTickers`, `placeOrder`）必须包裹在 `try-except` 中，防止因网络闪断导致程序崩溃。
- **频率限制:** 对 `reqTickers` 的调用需进行节流处理，避免触发 IBKR API 的 50/sec 限制。
- **日志审计:** 所有下单行为、Rolling 操作必须记录详细的日志，包括当时的价格、Delta 和预计收益。

## 4. 安全断路器 (Safety Circuit)
- **回撤熔断:** 日回撤超过账户总值 1% 时，停止所有开仓并发送预警。
- **时间窗:** 仅在美股常规交易时段 (RTH, 9:30 AM - 4:00 PM EST) 运行交易逻辑。
- **数据校验:** 若 `modelGreeks` 返回空值，严禁下单。
