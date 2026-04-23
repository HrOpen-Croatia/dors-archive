"""Empty conftest.py at the project root so pytest puts the repo root
on sys.path — that way `tests/` can `from scripts.rewrite_links import ...`
without needing PYTHONPATH.
"""
