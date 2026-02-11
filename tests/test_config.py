import pytest
import os
import json
from pathlib import Path
from config import load_parameters, save_learned_config, DEFAULTS

def test_load_parameters_default(tmp_path):
    # Test loading when no learned config exists
    with pytest.MonkeyPatch.context() as mp:
        mp.setattr("config.LEARNED_CONFIG_PATH", tmp_path / "non_existent.json")
        params = load_parameters('base')
        # Check defaults are there
        for k, v in DEFAULTS.items():
            assert params[k] == v
        assert params['STRATEGY_MODE'] == 'base'

def test_save_and_load_learned_config(tmp_path):
    learned_path = tmp_path / "learned.json"
    new_params = {"CC_DELTA_TARGET": 0.12, "ROLL_DELTA_THRESHOLD": 0.5}
    
    with pytest.MonkeyPatch.context() as mp:
        mp.setattr("config.LEARNED_CONFIG_PATH", learned_path)
        # 修正：现在需要传入 mode 参数
        save_learned_config('base', new_params)
        
        loaded = load_parameters('base')
        assert loaded["CC_DELTA_TARGET"] == 0.12
        assert loaded["ROLL_DELTA_THRESHOLD"] == 0.5
        # Ensure other defaults remain
        assert loaded["PCS_WIDTH"] == DEFAULTS["PCS_WIDTH"]

def test_aggressive_mode():
    params = load_parameters('aggressive')
    assert params['STRATEGY_MODE'] == 'aggressive'
    assert params['CC_DELTA_TARGET'] == 0.25 # Aggressive target
    assert params['PCS_WIDTH'] == 50
