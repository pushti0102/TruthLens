"""
conftest.py
===========
Pytest configuration file at the project root.

Registers the --integration flag and the 'integration' marker so pytest
does not warn about unknown markers.
"""

import pytest


def pytest_addoption(parser):
    parser.addoption(
        "--integration",
        action="store_true",
        default=False,
        help="Run integration tests that require model weights (~330 MB download).",
    )


def pytest_configure(config):
    config.addinivalue_line(
        "markers",
        "integration: requires model weights download (~330 MB, needs internet).",
    )


def pytest_collection_modifyitems(config, items):
    """Auto-skip integration tests unless --integration is passed."""
    if config.getoption("--integration", default=False):
        return  # run everything

    skip_integration = pytest.mark.skip(
        reason="Integration test: pass --integration to run (downloads ~330 MB)."
    )
    for item in items:
        if "integration" in item.keywords:
            item.add_marker(skip_integration)
