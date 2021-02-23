import pytest

from bravepatcher.utils.firewall.WindowsFirewallHelper import *


def test_quote():
    if 'quote' not in globals():
        pytest.skip('no quote function imported')
    assert quote("") == '""'
    assert quote("abc") == "abc"
    assert quote("ab d") == '"ab d"'
