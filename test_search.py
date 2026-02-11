import asyncio
import pytest
from ib_insync import *
import pandas as pd

# 配置测试目标
TARGET_STOCK = 'GOOG'
TARGET_INDEX = 'SPX'
GOOG_DELTA = 0.15
SPX_DELTA = 0.07

@pytest.mark.asyncio
async def test_option_search():
    ib = IB()
    try:
        # 1. 连接 TWS/Gateway (确保端口 7497 或 7496 正确)
        await ib.connectAsync('127.0.0.1', 7497, clientId=99)
        print(f"✅ 已连接到 IBKR。正在获取 {TARGET_STOCK} 实时行情...")

        # 2. 获取正股当前价格
        stock = Stock(TARGET_STOCK, 'SMART', 'USD')
        [ticker] = await ib.reqTickersAsync(stock)
        curr_price = ticker.marketPrice()
        print(f"📈 {TARGET_STOCK} 当前市价: ${curr_price}")

        # 3. 运行寻标逻辑 - 寻找下周五到期的 Call
        # 获取下周五日期 (简单计算)
        from datetime import datetime, timedelta
        days_ahead = 4 - datetime.now().weekday()
        if days_ahead <= 0: days_ahead += 7
        target_expiry = (datetime.now() + timedelta(days=days_ahead + 7)).strftime('%Y%m%d')

        print(f"🔍 正在寻找 {target_expiry} 到期的 {GOOG_DELTA} Delta 合约...")
        
        # 调用我们之前定义的寻标函数
        best_contract = await find_contract_by_delta_logic(ib, stock, target_expiry, GOOG_DELTA, 'C')

        if best_contract:
            # 获取该合约的详细行情
            [opt_ticker] = await ib.reqTickersAsync(best_contract)
            delta = opt_ticker.modelGreeks.delta if opt_ticker.modelGreeks else "N/A"
            bid = opt_ticker.bid
            ask = opt_ticker.ask
            
            print("-" * 30)
            print(f"🎯 寻标结果成功！")
            print(f"合约名称: {best_contract.localSymbol}")
            print(f"行权价格: {best_contract.strike}")
            print(f"实时 Delta: {delta}")
            print(f"买一/卖一: ${bid} / ${ask}")
            print(f"买卖点差: {((ask-bid)/ask)*100:.2f}%")
            print("-" * 30)
        else:
            print("❌ 未能找到符合条件的合约，请检查数据订阅或 DTE 设置。")

    except Exception as e:
        print(f"⚠️ 测试中途出错: {e}")
    finally:
        ib.disconnect()

async def find_contract_by_delta_logic(ib, underlying, expiry, target_delta, right):
    # 这里的逻辑与之前补完的函数一致
    # 1. 获取期权链
    chains = await ib.reqSecDefOptParamsAsync(underlying.symbol, '', underlying.secType, underlying.conId)
    chain = next(c for c in chains if c.exchange == 'SMART')
    
    # 2. 筛选行权价并构建合约
    strikes = [s for s in chain.strikes if (s > 150) ] # 这里的 150 仅为示例过滤
    contracts = [Option(underlying.symbol, expiry, s, right, 'SMART') for s in strikes[:20]] 
    contracts = await ib.qualifyContractsAsync(*contracts)
    
    # 3. 获取 Tickers 并比对
    tickers = await ib.reqTickersAsync(*contracts)
    best_match = None
    min_diff = 999
    
    for t in tickers:
        greeks = t.modelGreeks
        if greeks:
            diff = abs(abs(greeks.delta) - target_delta)
            if diff < min_diff:
                min_diff = diff
                best_match = t.contract
    return best_match

if __name__ == "__main__":
    asyncio.run(test_option_search())
