from market_brief.portfolio import load_holdings

HEADER = ("Symbol,Current Price,Date,Time,Change,Open,High,Low,Volume,Trade Date,"
          "Purchase Price,Quantity,Commission,High Limit,Low Limit,Comment,Transaction Type")


def write(tmp_path, text, name="p.csv"):
    path = tmp_path / name
    path.write_text(text, encoding="utf-8")
    return path


def test_combines_lots_with_weighted_cost(tmp_path):
    path = write(tmp_path, "\n".join([
        HEADER,
        "AMZN,,,,,,,,,,100,3,,,,,",
        "AMZN,,,,,,,,,,200,1,,,,,",
    ]))
    h = load_holdings(path)["AMZN"]
    assert h["shares"] == 4
    assert h["cost"] == 500
    assert h["cost_known"]


def test_skips_rows_without_quantity(tmp_path):
    path = write(tmp_path, "\n".join([HEADER, "SPY,,,,,,,,,,,,,,,,", "WFC,,,,,,,,,,27.3,5,,,,,"]))
    assert set(load_holdings(path)) == {"WFC"}


def test_tab_separated_export(tmp_path):
    path = write(tmp_path, HEADER.replace(",", "\t") + "\n" + "nvda" + "\t" * 10 + "162.01\t7" + "\t" * 5)
    h = load_holdings(path)
    assert h["NVDA"]["shares"] == 7


def test_missing_purchase_price_marks_cost_unknown(tmp_path):
    path = write(tmp_path, "\n".join([HEADER, "MSFT,,,,,,,,,,,2,,,,,"]))
    assert load_holdings(path)["MSFT"]["cost_known"] is False


def test_example_file_parses():
    from market_brief import config
    holdings = load_holdings(config.BASE / "portfolio" / "portfolio.example.csv")
    assert "SPY" not in holdings          # watchlist row skipped
    assert holdings["AMZN"]["shares"] == 8  # two lots combined