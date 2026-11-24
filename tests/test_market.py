from market_brief import market


def test_cap_tiers():
    assert market.tier_for_cap(3e12) == "large"
    assert market.tier_for_cap(10e9) == "large"
    assert market.tier_for_cap(5e9) == "mid"
    assert market.tier_for_cap(1e9) == "small"
    assert market.tier_for_cap(1e8) == "micro"
    assert market.tier_for_cap(None) == "unknown"


def test_fund_tier_from_category():
    assert market.holding_tier({"quoteType": "ETF", "category": "Large Blend"}) == "large"
    assert market.holding_tier({"quoteType": "ETF", "category": "Mid-Cap Growth"}) == "mid"
    assert market.holding_tier({"quoteType": "ETF", "category": "Small Value"}) == "small"
    assert market.holding_tier({"quoteType": "ETF", "category": "Technology"}) == "unknown"


def test_norm_sector():
    assert market.norm_sector("Financial Services") == "financial_services"
    assert market.norm_sector("Real Estate") == "realestate"


def test_headline_terms_match_company_not_neighbors():
    terms = market.search_terms("NVDA", {"shortName": "NVIDIA Corporation", "quoteType": "EQUITY"})
    hit = lambda t: any(p.search(t) for p in terms)
    assert hit("Nvidia's comeback CEO faces questions")
    assert hit("NVDA slides 8%")
    assert not hit("Stocks give back gains as Anthropic dips")


def test_etf_terms_skip_first_word():
    terms = market.search_terms("VOO", {"shortName": "Vanguard S&P 500 ETF", "quoteType": "ETF"})
    hit = lambda t: any(p.search(t) for p in terms)
    assert hit("Did Nvidia's rebound make VOO owners whole?")
    assert not hit("Vanguard's overlooked quality ETF")