from scanner import config


def test_weights_sum_to_one():
    assert abs(sum(config.WEIGHTS.values()) - 1.0) < 1e-9


def test_weight_keys():
    assert set(config.WEIGHTS) == {"momentum", "liquidity", "safety", "freshness"}


def test_top_n_is_ten():
    assert config.TOP_N == 10


def test_repo_constants():
    assert config.GITHUB_OWNER == "Djolesd02"
    assert config.GITHUB_REPO == "ai-crypto-recommendation"
    assert config.DATA_BRANCH == "data"
    assert config.DATA_PATH == "data.json"
