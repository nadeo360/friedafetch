"""Shared fixtures."""

from __future__ import annotations

from collections.abc import Generator
from unittest.mock import AsyncMock, patch

import pytest

pytest_plugins = "pytest_homeassistant_custom_component"

APPLE_ID = "test@icloud.com"
APP_PASSWORD = "abcd-efgh-ijkl-mnop"


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations: None) -> None:
    """Enable loading custom integrations in all tests."""
    return


@pytest.fixture
def mock_discover() -> Generator[AsyncMock]:
    """Make CalDAV discovery succeed without network."""
    with patch(
        "custom_components.icloud_mcp.caldav_client.ICloudCalDav.async_discover",
        new_callable=AsyncMock,
        return_value="https://p01-caldav.icloud.com/1/calendars/",
    ) as mocked:
        yield mocked


@pytest.fixture
def mock_mail_login() -> Generator[AsyncMock]:
    """Make the IMAP login check succeed without network."""
    with patch(
        "custom_components.icloud_mcp.mail.ICloudMail.async_test_login",
        new_callable=AsyncMock,
    ) as mocked:
        yield mocked
