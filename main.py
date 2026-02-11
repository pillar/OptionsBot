import asyncio
import logging
import os
import sys
from datetime import datetime
from ib_insync import *

from utils import get_next_friday, is_trading_hours, validate_net_credit
from options_lookup import find_contract_by_delta, is_contract_liquid
from target_list import STOCK_CANDIDATES, INDEX_CANDIDATES
from earnings_calendar import is_near_earnings
from config import DEFAULT_MODE, load_parameters
from data_logger import ensure_db, log_trade, log_market_snapshot
from vix_monitor import fetch_vix
from self_tuner import tune_parameters

# 配置日志 - 增加文件输出以便审计
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('options_bot.log')
    ]
)
logger = logging.getLogger(__name__)

class AIOptionsMaster:
    def __init__(self, host='127.0.0.1', port=7497, client_id=1, mode=None):
        self.ib = IB()
        self.host = host
        self.port = port
        self.client_id = client_id
        self.mode = mode or os.environ.get('STRATEGY_MODE', DEFAULT_MODE)
        
        # 初始加载参数
        self.refresh_config()
        
        # 运行状态
        self.initial_nav = None
        self.force_exit_flag = False
        self.current_vix = None

    def refresh_config(self):
        """从 config.py (含已学习参数) 加载最新配置"""
        params = load_parameters(self.mode)
        self.cc_delta_target = params['CC_DELTA_TARGET']
        self.pcs_sell_delta = params['PCS_SELL_DELTA']
        self.pcs_width = params['PCS_WIDTH']
        self.roll_delta_threshold = params['ROLL_DELTA_THRESHOLD']
        self.roll_dte_threshold = params['ROLL_DTE_THRESHOLD']
        self.max_daily_drawdown = params['MAX_DAILY_DRAWDOWN']
        logger.info(f"⚙️ 配置已刷新: Delta={self.cc_delta_target}, RollThresh={self.roll_delta_threshold}")

    def _select_stock_candidate(self):
        """从候选池中选择当前持有正股的标的"""
        positions = self.ib.positions()
        for candidate in STOCK_CANDIDATES:
            symbol = candidate['symbol']
            min_shares = candidate.get('min_shares', 100)
            stock_pos = next(
                (p for p in positions if p.contract.symbol == symbol and p.contract.secType == 'STK'),
                None
            )
            if not stock_pos or stock_pos.position < min_shares:
                continue
            opt_pos = next(
                (p for p in positions if p.contract.symbol == symbol and p.contract.secType == 'OPT' and p.contract.right == 'C'),
                None
            )
            return candidate, stock_pos, opt_pos
        return None, None, None

    def _get_index_candidate(self):
        """获取当前配置的指数标的"""
        return INDEX_CANDIDATES[0] if INDEX_CANDIDATES else None

    async def connect(self):
        try:
            await self.ib.connectAsync(self.host, self.port, clientId=self.client_id)
            self.account = self.ib.wrapper.accounts[0]
            # 获取初始净资产
            acc_summary = await self.ib.accountSummaryAsync(self.account)
            nav_item = [item for item in acc_summary if item.tag == 'NetLiquidation']
            if nav_item:
                self.initial_nav = float(nav_item[0].value)
            logger.info(f"✅ 已连接账户: {self.account}, 初始 NAV: {self.initial_nav}")
        except Exception as e:
            logger.error(f"连接失败: {e}")
            sys.exit(1)

    # --- 核心逻辑 1：多标的备兑收租 (Covered Call) ---
    async def manage_covered_calls(self):
        if self.force_exit_flag: return
        logger.info(">>> 检查股票候选池中的 Covered Call 机会...")
        
        candidate, stock_pos, opt_pos = self._select_stock_candidate()
        if not candidate:
            logger.info("未在候选池中找到满足持仓条件的股票，跳过 Covered Call")
            return

        symbol = candidate['symbol']
        if await is_near_earnings(symbol):
            logger.info(f"📅 {symbol} 即将财报，跳过 Covered Call")
            return

        stock = Stock(symbol, 'SMART', 'USD')
        await self.ib.qualifyContractsAsync(stock)

        # 环境感知调参：如果 VIX 很高 (如 > 30)，我们稍微降低目标 Delta 以追求更安全
        effective_delta = self.cc_delta_target
        if self.current_vix and self.current_vix > 30:
            effective_delta *= 0.8
            logger.info(f"📉 高波动环境 (VIX={self.current_vix:.2f})，调低目标 Delta 至 {effective_delta:.3f}")

        qty = int(stock_pos.position / 100)
        if not opt_pos or abs(opt_pos.position) < 1:
            expiry = get_next_friday(offset_weeks=0)
            contract = await find_contract_by_delta(self.ib, stock, expiry, effective_delta, 'C')
            if contract:
                order = MarketOrder('SELL', qty)
                self.ib.placeOrder(contract, order)
                logger.info(f"🚀 [OPEN] {symbol} Covered Call: {contract.localSymbol} x {qty}")
                await log_trade("COVERED_CALL", symbol, "OPEN", qty, delta=effective_delta, notes=f"Contract: {contract.localSymbol}, VIX: {self.current_vix}")
        else:
            await self.check_and_roll_call(opt_pos)

    async def check_and_roll_call(self, current_pos):
        contract = current_pos.contract
        symbol = contract.symbol
        [ticker] = await self.ib.reqTickersAsync(contract)
        
        if not ticker.modelGreeks:
            logger.warning(f"无法获取 {contract.localSymbol} Greeks，跳过此轮。")
            return

        delta = abs(ticker.modelGreeks.delta)
        expiry_dt = datetime.strptime(contract.lastTradeDateOrContractMonth, '%Y%m%d')
        dte = (expiry_dt - datetime.now()).days

        # 触发条件: Delta > ROLL_DELTA_THRESHOLD 或 DTE < ROLL_DTE_THRESHOLD
        if delta > self.roll_delta_threshold or dte < self.roll_dte_threshold:
            logger.info(f"⚠️ 触发 Rolling: {contract.localSymbol} (Delta={delta:.2f}, DTE={dte})")
            
            new_expiry = get_next_friday(offset_weeks=1)
            new_contract = await find_contract_by_delta(self.ib, Stock(symbol, 'SMART'), new_expiry, self.cc_delta_target, 'C')
            
            if new_contract:
                if not await is_contract_liquid(self.ib, new_contract):
                    logger.warning('Rolling 新合约流动性不足，跳过')
                    return
                [new_ticker] = await self.ib.reqTickersAsync(new_contract)
                # 简单校验：新合约 Bid > 旧合约 Ask (买回成本)
                if new_ticker.bid > ticker.ask:
                    # 使用 Bag 组合单减少滑点
                    buy_leg = ComboLeg(conId=contract.conId, ratio=1, action='BUY')
                    sell_leg = ComboLeg(conId=new_contract.conId, ratio=1, action='SELL')
                    roll_bag = Bag(symbol=symbol, comboLegs=[buy_leg, sell_leg])
                    self.ib.placeOrder(roll_bag, MarketOrder('SELL', abs(current_pos.position)))
                    logger.info(f"✅ [ROLL] {contract.localSymbol} -> {new_contract.localSymbol}")
                    await log_trade("ROLLING", symbol, "ROLL", abs(current_pos.position), delta=delta, notes=f"From {contract.localSymbol} to {new_contract.localSymbol}")
                else:
                    logger.error("❌ Rolling 失败: Net Credit 验证未通过。")

    # --- 核心逻辑 2：指数概率收割 (Put Credit Spread) ---
    async def manage_index_spreads(self):
        if self.force_exit_flag: return
        candidate = self._get_index_candidate()
        if not candidate:
            logger.warning("没有可用的指数候选，跳过 Spread 策略")
            return

        # 保护性检查：如果 VIX 极高 (如 > 40)，暂停开新 Spread 仓位
        if self.current_vix and self.current_vix > 40:
            logger.warning(f"🚨 恐慌模式 (VIX={self.current_vix:.2f})，暂停开仓 Put Credit Spread。")
            return

        symbol = candidate['symbol']
        exchange = candidate.get('exchange', 'CBOE')
        logger.info(f">>> 扫描 {symbol} 现金流机会...")

        index = Index(symbol, exchange, 'USD')
        await self.ib.qualifyContractsAsync(index)

        positions = [p for p in self.ib.positions() if p.contract.symbol == symbol and p.contract.secType == 'OPT']
        if positions:
            logger.info(f"已有 {symbol} Spread 仓位，监控中...")
            return

        expiry = datetime.now().strftime('%Y%m%d') # 0DTE
        sell_side = await find_contract_by_delta(self.ib, index, expiry, self.pcs_sell_delta, 'P')
        if not sell_side:
            return
        if not await is_contract_liquid(self.ib, sell_side):
            logger.warning(f'{symbol} 卖出腿流动性不足，跳过本轮')
            return

        buy_strike = sell_side.strike - self.pcs_width
        buy_side = Option(symbol, expiry, buy_strike, 'P', exchange)
        await self.ib.qualifyContractsAsync(buy_side)
        if not await is_contract_liquid(self.ib, buy_side):
            logger.warning(f'{symbol} 买入腿流动性不足，跳过本轮')
            return

        legs = [
            ComboLeg(conId=sell_side.conId, ratio=1, action='SELL'),
            ComboLeg(conId=buy_side.conId, ratio=1, action='BUY')
        ]
        spread_bag = Bag(symbol=symbol, comboLegs=legs)
        self.ib.placeOrder(spread_bag, MarketOrder('SELL', 1))
        logger.info(f"🚀 [OPEN] {symbol} Spread: Sell {sell_side.strike}P / Buy {buy_side.strike}P")
        await log_trade("SPREAD", symbol, "OPEN", 1, delta=self.pcs_sell_delta, notes=f"Sell {sell_side.strike}P, Buy {buy_side.strike}P, VIX: {self.current_vix}")

    # --- 风控 ---
    async def risk_monitor(self):
        acc_summary = await self.ib.accountSummaryAsync(self.account)
        nav_item = [item for item in acc_summary if item.tag == 'NetLiquidation']
        if not nav_item or not self.initial_nav: return
        
        current_nav = float(nav_item[0].value)
        drawdown = (self.initial_nav - current_nav) / self.initial_nav
        
        if drawdown > self.max_daily_drawdown:
            logger.error(f"🚨 [FATAL] 达到日回撤熔断线 ({drawdown:.2%})！执行紧急避险...")
            await self.emergency_exit()

    async def emergency_exit(self):
        self.force_exit_flag = True
        self.ib.reqGlobalCancel() # 取消所有挂单
        
        positions = self.ib.positions()
        for p in positions:
            if p.contract.secType == 'OPT':
                action = 'BUY' if p.position < 0 else 'SELL'
                order = MarketOrder(action, abs(p.position))
                self.ib.placeOrder(p.contract, order)
                logger.warning(f"📢 [EXIT] 紧急平仓期权: {p.contract.localSymbol}")
                await log_trade("EMERGENCY", p.contract.symbol, "EXIT", abs(p.position), notes=f"Emergency liquidation of {p.contract.localSymbol}")

    async def run_loop(self):
        await ensure_db()
        await self.connect()
        
        iteration = 0
        while True:
            try:
                # 每轮刷新 VIX 状态
                self.current_vix = await fetch_vix(self.ib)
                if self.current_vix:
                    await log_market_snapshot('VIX', self.current_vix)
                    logger.info(f"📊 当前 VIX: {self.current_vix:.2f}")

                if is_trading_hours():
                    # 每 6 轮 (约 1 小时) 运行一次自学习调参
                    if iteration % 6 == 0:
                        logger.info(f"🧠 正在运行自学习调参 (Mode: {self.mode})...")
                        tuned = tune_parameters(self.mode)
                        if tuned:
                            logger.info(f"✨ 发现新优化参数: {tuned}")
                        self.refresh_config()

                    await self.risk_monitor()
                    await self.manage_covered_calls()
                    await self.manage_index_spreads()
                else:
                    logger.info("非交易时段，休眠中...")
                
                iteration += 1
                await asyncio.sleep(600) # 10分钟/轮
            except Exception as e:
                logger.error(f"异常: {e}")
                await asyncio.sleep(60)

if __name__ == "__main__":
    bot = AIOptionsMaster()
    try:
        asyncio.run(bot.run_loop())
    except KeyboardInterrupt:
        logger.info("人工停止。")
