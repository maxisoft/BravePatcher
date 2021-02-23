from pathlib import Path
from typing import Optional

from ..firewall import AbstractFirewallHelper, WindowsFirewallHelper


class UpdateDisabler:
    rule_name = "BravePatcher - Block Brave update"

    def __init__(self, brave_path: Path, firewall_helper: Optional[AbstractFirewallHelper] = None):
        self.brave_path = brave_path
        if firewall_helper is None:
            firewall_helper = WindowsFirewallHelper()
        self.firewall_helper = firewall_helper

    def disable_update(self):
        if not self.firewall_helper.has_rule(self.rule_name):
            self.firewall_helper.block_program(self.brave_path, self.rule_name)

    def enable_update(self):
        if self.firewall_helper.has_rule(self.rule_name):
            self.firewall_helper.allow_program(self.brave_path, self.rule_name)
