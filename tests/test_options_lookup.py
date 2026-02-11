import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from ib_insync import Option, Ticker
from options_lookup import find_contract_by_delta

@pytest.mark.asyncio
async def test_find_contract_by_delta_success():
    # Mock IB object
    ib = MagicMock()
    
    # Mock reqSecDefOptParamsAsync
    mock_chain = MagicMock()
    mock_chain.exchange = 'SMART'
    mock_chain.expirations = ['20260220']
    mock_chain.strikes = [150.0, 160.0, 170.0]
    ib.reqSecDefOptParamsAsync = AsyncMock(return_value=[mock_chain])
    
    # Mock reqTickersAsync for underlying
    mock_underlying_ticker = MagicMock()
    mock_underlying_ticker.marketPrice.return_value = 155.0
    
    # Mock option tickers
    t1 = MagicMock(contract=Option('GOOG', '20260220', 160.0, 'C', 'SMART'), 
                  modelGreeks=MagicMock(delta=0.15),
                  bid=1.0, ask=1.05)
    t1.marketPrice.return_value = 1.025
    
    t2 = MagicMock(contract=Option('GOOG', '20260220', 170.0, 'C', 'SMART'), 
                  modelGreeks=MagicMock(delta=0.05),
                  bid=0.2, ask=0.22)
    t2.marketPrice.return_value = 0.21
    
    ib.reqTickersAsync = AsyncMock(side_effect=[
        [mock_underlying_ticker], # First call for underlying
        [t1, t2]                  # Second call for chunks
    ])
    
    # Mock qualifyContractsAsync
    ib.qualifyContractsAsync = AsyncMock(side_effect=lambda *args: list(args))
    
    underlying = MagicMock(symbol='GOOG', secType='STK', conId=123)
    
    result = await find_contract_by_delta(
        ib, underlying, '20260220', 0.15, 'C'
    )
    
    assert result is not None
    assert result.strike == 160.0
    assert result.right == 'C'

@pytest.mark.asyncio
async def test_find_contract_by_delta_no_chain():
    ib = MagicMock()
    ib.reqSecDefOptParamsAsync = AsyncMock(return_value=[])
    
    underlying = MagicMock(symbol='GOOG', secType='STK', conId=123)
    result = await find_contract_by_delta(ib, underlying, '20260220', 0.15, 'C')
    
    assert result is None

@pytest.mark.asyncio
async def test_find_contract_by_delta_wrong_expiry():
    ib = MagicMock()
    mock_chain = MagicMock()
    mock_chain.exchange = 'SMART'
    mock_chain.expirations = ['20260213']
    ib.reqSecDefOptParamsAsync = AsyncMock(return_value=[mock_chain])
    
    underlying = MagicMock(symbol='GOOG', secType='STK', conId=123)
    result = await find_contract_by_delta(ib, underlying, '20260220', 0.15, 'C')
    
    assert result is None
