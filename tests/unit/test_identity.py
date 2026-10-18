"""Unit tests for TrustedIdentity resolution."""

import os
from unittest.mock import patch
from graph_intelligence.common.identity import TrustedIdentity


def test_trusted_identity_resolution():
    with patch.dict(os.environ, {"DEMO_USER_ID": "user-test-custom"}):
        from graph_intelligence.common import config
        config._settings_instance = None  # reset cache
        ident = TrustedIdentity.current()
        assert ident.user_id == "user-test-custom"
        config._settings_instance = None  # cleanup
