# OptionsBot AGENTS 快速指南

## 项目概览
- **目标**：构建可动态在自选池里轮动的美股期权策略，自动挑选账户中满足条件的股票（Covered Call）与预设指数（Put Credit Spread）进行交易。
- **关键文件**：
  - `main.py`: AIOptionsMaster 类，负责连接 ib_insync、执行核心策略、Rolling 与风险熔断。
  - `config.py`: 策略全局配置（Delta 目标、Rolling 阈值、熔断限制等）。
  - `target_list.py`: 可配置的自选池，定义股票（及其起步股数）和指数标的。
  - `data_logger.py`: 基于 SQLite 的异步交易行为日志持久化工具，含财报缓存表。
  - `earnings_calendar.py`: 智能财报日历模块，通过 yfinance 获取未来 2 年财报并缓存，极低频查询。
  - `vix_monitor.py`: VIX 环境感知模块，实时获取市场波动率。
  - `self_tuner.py`: 自学习调参模块，每小时分析交易历史优化策略参数。
  - `options_lookup.py`: 期权搜索核心逻辑，含流动性检验与 Greeks 批量拉取。
  - `utils.py`: 日期处理、交易时间检查与 Net Credit 校验。
  - `tests/`: 包含针对核心逻辑的单元测试与 Smoke test。
  - `CLAUDE.md`: 策略数学约束、编码规范与安全断路器说明。
  - `TODO.md`: 开发路线图。

## 技术栈与运行环境
- Python 3.11+，依赖 `ib_insync`, `asyncio`, `pandas`, `pytest`, `pytest-asyncio`, `pytz`。
- 本地运行依赖 IB TWS 或 Gateway（端口 7497/7496）。
- 建议安装依赖：
  ```bash
  python3 -m venv .venv
  source .venv/bin/activate
  pip install -r requirements.txt
  ```

## 建议运行流程
1. 启动 IB TWS/Gateway。
2. 运行测试：`pytest tests/`。
3. 启动机器人：`python main.py`。
4. 审计日志：查看 `options_bot.log` 或分析 `strategy_data.db`。

## 代码规范
- **配置驱动**：修改策略参数请前往 `config.py`，不要硬编码在逻辑中。
- **异步记录**：交易、Rolling、紧急平仓必须通过 `data_logger.log_trade` 存入数据库。
- **安全检查**：下单前必须经过 `options_lookup` 的流动性过滤。

## Codex 代理专用说明
- 修改参数前优先检查 `config.py`。
- 确保所有关键决策（下单、滚动）都有对应的 `log_trade` 调用以便自强学习。
