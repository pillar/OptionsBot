import asyncio
import logging
from typing import List, Optional, Tuple
from ib_insync import Option, IB, Ticker

logger = logging.getLogger(__name__)

async def find_contract_by_delta(
    ib: IB,
    underlying,
    expiry: str,
    target_delta: float,
    right: str,
    exchange: str = 'SMART',
    price_padding: Tuple[float, float] = (0.85, 1.15),
    chunk_size: int = 50,
    early_exit_diff: float = 0.02,
) -> Optional[Option]:
    """
    在期权链中查找与目标 Delta 最接近的合约。
    """
    logger.info(f"找合约中: {underlying.symbol} {expiry} {right} 目标 Delta {target_delta}")

    # 1. 获取期权参数
    chains = await ib.reqSecDefOptParamsAsync(underlying.symbol, '', underlying.secType, underlying.conId)
    chain = next((c for c in chains if c.exchange == exchange), None)
    if not chain:
        logger.error(f"未找到适合的期权链 (Exchange: {exchange})")
        return None

    if expiry not in chain.expirations:
        logger.error(f"到期日 {expiry} 不在可用列表中")
        return None

    # 2. 价格过滤
    [underlying_ticker] = await ib.reqTickersAsync(underlying)
    curr_price = underlying_ticker.marketPrice()
    if curr_price <= 0:
        logger.error(f"无法获取有效标的价格: {curr_price}")
        return None

    lower_bound = curr_price * price_padding[0]
    upper_bound = curr_price * price_padding[1]

    # 3. 筛选行权价
    if right == 'C':
        potential_strikes = [s for s in chain.strikes if lower_bound <= s <= upper_bound and s > curr_price]
    else:
        potential_strikes = [s for s in chain.strikes if lower_bound <= s <= upper_bound and s < curr_price]
        potential_strikes.sort(reverse=True)

    contracts = [Option(underlying.symbol, expiry, s, right, exchange) for s in potential_strikes[:120]]
    if not contracts:
        logger.warning("没有找到合适行权价范围内的合约")
        return None

    # 4. 资格确认
    qualified = await ib.qualifyContractsAsync(*contracts)

    candidates = []  # store tuples (diff, ticker)

    # 5. 分批拉取 Greeks
    for i in range(0, len(qualified), chunk_size):
        chunk = qualified[i:i + chunk_size]
        tickers = await ib.reqTickersAsync(*chunk)
        
        for t in tickers:
            greeks = t.modelGreeks or t.marketGreeks
            if not greeks or greeks.delta is None:
                continue
            
            current_delta = abs(greeks.delta)
            diff = abs(current_delta - target_delta)
            candidates.append((diff, t))
            
        # 满足提前退出条件
        if candidates and min(c[0] for c in candidates) < early_exit_diff:
            break
            
        await asyncio.sleep(0.1)

    if not candidates:
        logger.warning("未找到满足 Delta 要求的合约")
        return None

    candidates.sort(key=lambda x: x[0])
    spread_threshold = 0.1
    best_contract = None
    best_diff = candidates[0][0]

    for diff, ticker in candidates:
        price = ticker.marketPrice()
        if price <= 0:
            continue
        if ticker.bid is None or ticker.ask is None:
            continue
        spread_ratio = (ticker.ask - ticker.bid) / price
        if spread_ratio <= spread_threshold:
            best_contract = ticker.contract
            best_diff = diff
            break
        logger.info(f"跳过 {ticker.contract.localSymbol}: Spread/Price={spread_ratio:.2%} 太大")

    if best_contract:
        logger.info(f"🎯 找到最优合约: {best_contract.localSymbol} (Delta 误差 {best_diff:.4f})")
    else:
        logger.warning("所有候选合约流动性不足，未选定合约")
    
    return best_contract


async def is_contract_liquid(ib, contract, spread_threshold=0.1):
    """检查合约的 Bid-Ask spread/price 是否在合理范围内"""
    if not contract:
        return False
    [ticker] = await ib.reqTickersAsync(contract)
    price = ticker.marketPrice()
    if price <= 0 or ticker.bid is None or ticker.ask is None:
        logger.warning(f"合约 {contract.localSymbol} 无效价格/报价，视为流动性不足")
        return False
    spread_ratio = (ticker.ask - ticker.bid) / price
    if spread_ratio > spread_threshold:
        logger.warning(
            f"合约 {contract.localSymbol} Spread/Price={spread_ratio:.2%} > {spread_threshold:.2%}, 流动性不足"
        )
        return False
    return True
