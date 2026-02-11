import asyncio
import logging
import sys
from datetime import datetime
from ib_insync import *

from utils import get_next_friday, is_trading_hours, validate_net_credit
from options_lookup import find_contract_by_delta, is_contract_liquid

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
    def __init__(self, host='127.0.0.1', port=7497, client_id=1):
        self.ib = IB()
        self.host = host
        self.port = port
        self.client_id = client_id
        
        # 策略参数 (严格对齐 CLAUDE.md)
        self.target_stock = 'GOOG'
        self.index_symbol = 'SPX'
        self.cc_delta_target = 0.15
        self.pcs_sell_delta = 0.07
        self.pcs_width = 30 # 20-50 点间隔
        
        # 风控参数
        self.max_daily_drawdown = 0.01 # 1% 熔断
        self.initial_nav = None
        self.force_exit_flag = False

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

    # --- 核心逻辑 1：Google Covered Call ---
    async def manage_goog_covered_call(self):
        if self.force_exit_flag: return
        logger.info(">>> 扫描 Google 备兑仓位...")
        
        stock = Stock(self.target_stock, 'SMART', 'USD')
        await self.ib.qualifyContractsAsync(stock)
        
        # 持仓审计
        positions = self.ib.positions()
        stock_pos = next((p for p in positions if p.contract.symbol == self.target_stock and p.contract.secType == 'STK'), None)
        opt_pos = next((p for p in positions if p.contract.symbol == self.target_stock and p.contract.secType == 'OPT'), None)

        if not stock_pos or stock_pos.position < 100:
            logger.warning("正股持仓不足 100 股，跳过。")
            return

        qty = int(stock_pos.position / 100)

        if not opt_pos:
            # 寻找下周五到期的 Call
            expiry = get_next_friday(offset_weeks=0)
            contract = await find_contract_by_delta(self.ib, stock, expiry, self.cc_delta_target, 'C')
            if contract:
                order = MarketOrder('SELL', qty)
                trade = self.ib.placeOrder(contract, order)
                logger.info(f"🚀 [OPEN] 开仓 Covered Call: {contract.localSymbol} x {qty}")
        else:
            # 监控 Rolling 条件
            await self.check_and_roll_call(opt_pos)

    async def check_and_roll_call(self, current_pos):
        contract = current_pos.contract
        [ticker] = await self.ib.reqTickersAsync(contract)
        
        if not ticker.modelGreeks:
            logger.warning(f"无法获取 {contract.localSymbol} Greeks，跳过此轮。")
            return

        delta = abs(ticker.modelGreeks.delta)
        expiry_dt = datetime.strptime(contract.lastTradeDateOrContractMonth, '%Y%m%d')
        dte = (expiry_dt - datetime.now()).days

        # 触发条件: Delta > 0.45 或 DTE < 1
        if delta > 0.45 or dte < 1:
            logger.info(f"⚠️ 触发 Rolling: {contract.localSymbol} (Delta={delta:.2f}, DTE={dte})")
            
            new_expiry = get_next_friday(offset_weeks=1)
            new_contract = await find_contract_by_delta(self.ib, Stock(self.target_stock, 'SMART'), new_expiry, self.cc_delta_target, 'C')
            
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
                    roll_bag = Bag(symbol=self.target_stock, comboLegs=[buy_leg, sell_leg])
                    self.ib.placeOrder(roll_bag, MarketOrder('SELL', abs(current_pos.position)))
                    logger.info(f"✅ [ROLL] {contract.localSymbol} -> {new_contract.localSymbol}")
                else:
                    logger.error("❌ Rolling 失败: Net Credit 验证未通过。")

    # --- 核心逻辑 2：SPX Put Credit Spread ---
    async def manage_spx_cashflow(self):
        if self.force_exit_flag: return
        logger.info(">>> 扫描 SPX 现金流...")
        
        index = Index(self.index_symbol, 'CBOE', 'USD')
        await self.ib.qualifyContractsAsync(index)
        
        # 检查是否已有 Spread 仓位
        positions = [p for p in self.ib.positions() if p.contract.symbol == self.index_symbol and p.contract.secType == 'OPT']
        if positions:
            logger.info("已有 SPX 仓位，监控中...")
            return

        # 寻找 1DTE 合约 (通常选明天或今天)
        expiry = datetime.now().strftime('%Y%m%d') # 示例选 0DTE
        
        sell_side = await find_contract_by_delta(self.ib, index, expiry, self.pcs_sell_delta, 'P')
        if not sell_side: return
        if not await is_contract_liquid(self.ib, sell_side):
            logger.warning('SPX 卖出腿流动性不足，跳过本轮')
            return
        
        buy_strike = sell_side.strike - self.pcs_width
        buy_side = Option(self.index_symbol, expiry, buy_strike, 'P', 'CBOE')
        await self.ib.qualifyContractsAsync(buy_side)
        if not await is_contract_liquid(self.ib, buy_side):
            logger.warning('SPX 买入腿流动性不足，跳过本轮')
            return
        
        # 构建 Combo
        legs = [
            ComboLeg(conId=sell_side.conId, ratio=1, action='SELL'),
            ComboLeg(conId=buy_side.conId, ratio=1, action='BUY')
        ]
        spread_bag = Bag(symbol=self.index_symbol, comboLegs=legs)
        self.ib.placeOrder(spread_bag, MarketOrder('SELL', 1))
        logger.info(f"🚀 [OPEN] SPX Spread: Sell {sell_side.strike}P / Buy {buy_side.strike}P")

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

    async def run_loop(self):
        await self.connect()
        while True:
            try:
                if is_trading_hours():
                    await self.risk_monitor()
                    await self.manage_goog_covered_call()
                    await self.manage_spx_cashflow()
                else:
                    logger.info("非交易时段，休眠中...")
                
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
