"""`market-brief init`: set up a working folder for a pip-installed copy.

Creates, without overwriting anything that already exists:
    .env                            settings template (fill in your keys)
    portfolio/portfolio.example.csv format reference for your Yahoo export
    img/  logs/                     output folders
"""
from importlib import resources
from pathlib import Path


def _template(name):
    return resources.files("market_brief").joinpath("templates", name).read_text(encoding="utf-8")


def init_home(base):
    base = Path(base)
    created, kept = [], []

    def write(rel, text):
        path = base / rel
        if path.exists():
            kept.append(rel)
            return
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
        created.append(rel)

    write(".env", _template("env.example"))
    write("portfolio/portfolio.example.csv", _template("portfolio.example.csv"))
    for folder in ("img", "logs"):
        path = base / folder
        if path.exists():
            kept.append(folder + "/")
        else:
            path.mkdir(parents=True)
            created.append(folder + "/")

    return created, kept