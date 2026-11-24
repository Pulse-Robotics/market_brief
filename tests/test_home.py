from pathlib import Path

from market_brief import config
from market_brief.home import init_home

ROOT = Path(__file__).resolve().parent.parent


def test_init_creates_layout(tmp_path):
    created, kept = init_home(tmp_path)
    assert (tmp_path / ".env").exists()
    assert (tmp_path / "portfolio" / "portfolio.example.csv").exists()
    assert (tmp_path / "img").is_dir() and (tmp_path / "logs").is_dir()
    assert kept == []


def test_init_never_overwrites(tmp_path):
    (tmp_path / ".env").write_text("GEMINI_API_KEY=real\n")
    init_home(tmp_path)
    assert (tmp_path / ".env").read_text() == "GEMINI_API_KEY=real\n"


def test_bundled_templates_match_repo_files():
    pkg = ROOT / "market_brief" / "templates"
    assert (pkg / "env.example").read_text() == (ROOT / ".env.example").read_text()
    assert (pkg / "portfolio.example.csv").read_text() == \
        (ROOT / "portfolio" / "portfolio.example.csv").read_text()


def test_template_placeholders_count_as_missing():
    assert config._is_placeholder("your_key_here")
    assert config._is_placeholder("https://discord.com/api/webhooks/...")
    assert config._is_placeholder("")
    assert not config._is_placeholder("AIzaRealLookingKey")