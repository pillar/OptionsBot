# OptionsBot AGENTS 快速指南

## 项目概览
- **目标**：构建可动态在自选池里轮动的美股期权策略，自动挑选账户中满足条件的股票（Covered Call）与预设指数（Put Credit Spread）进行交易。
- **关键文件**：
  - `main.py`: AIOptionsMaster 类，负责连接 ib_insync、从 `target_list.py` 筛选候选、执行 Covered Call / Spread 逻辑、Rolling 与风险熔断。
  - `target_list.py`: 可配置的自选池，按优先级提供股票和指数，并支持最小持仓要求。
  - `options_lookup.py`: 提炼出的期权搜索逻辑，支持异步批量请求、Greeks 容错、流动性检验与提前退出。
  - `utils.py`: 包含日期处理、交易时间检查与信用校验。
  - `tests/`: 包含针对核心逻辑的单元测试。
  - `CLAUDE.md`: 写明策略数学约束、编码规范、安全断路器等策略 guardrails，以及对 Codex 的指令说明。
  - `test_search.py`: 封装搜索期权合约的实用脚本，用来验证 Delta 定位逻辑与 IBKR 连通性。
  - `TODO.md`: 分阶段列出搭建、开发、风控与上线任务，并包含已知问题区域。

## 技术栈与运行环境
- Python 3.11+，依赖 `ib_insync`, `asyncio`, `pandas`, `pytest`, `pytest-asyncio`, `pytz`。
- 本地运行依赖 IB TWS 或 Gateway（端口 7497/7496），需开启 API 权限。
- 建议安装依赖（推荐使用 venv）：
  ```bash
  python3 -m venv .venv
  source .venv/bin/activate
  pip install -r requirements.txt
  ```

## 建议运行流程
1. 启动 IB TWS/Gateway，确认 API 访问配置，端口与 clientId 匹配。
2. 在项目根下（`OptionsBot` 目录）运行：
   - 运行单元测试：`pytest tests/`
   - 验证连接与 Delta 寻标（smoke test）：`pytest tests/test_search.py`
   - 主策略循环：`python main.py`
3. 日志信息通过 `logging` 输出，重点包括：连接成功（账户）、下单/滚动动作、风险熔断触发、异常捕获。

## 代码规范
- **命名**：变量与函数 `snake_case`；类 `PascalCase`；常量大写。
- **异步安全**：所有 IBKR 异步 API（`reqTickers`, `placeOrder` 等）需写 `try/except`，防止网络波动直接中断循环。
- **日志**：使用 `logger`，每次下单、滚动、熔断都记录 Delta、DTE、价格、预期收益。
- **文档**：函数/类保留 docstring 和简短注释。

## Codex 代理专用说明
- 修改代码前必须阅读 `CLAUDE.md` 的数学约束。
- 提炼逻辑至辅助库并保持单元测试覆盖。
- 代码审查时重点检查：异步错误处理、Net Credit 计算、Rolling 逻辑。
