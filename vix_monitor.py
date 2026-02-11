import logging

from ib_insync import Index

logger = logging.getLogger(__name__)


async def fetch_vix(ib):
    try:
        vix = Index('VIX', 'CBOE', 'USD')
        await ib.qualifyContractsAsync(vix)
        [ticker] = await ib.reqTickersAsync(vix)
        value = ticker.marketPrice()
        if value is None or value <= 0:
            value = ticker.last
        return value
    except Exception as exc:
        logger.warning(f"无法读取 VIX 价格: {exc}")
        return None
