from typing import Union, List, Optional, Any

from mcdreforged.api.utils import Serializable


_NONE = object()

class __Serializable(Serializable):
    def get(self, key: str, default_value: Any = None):
        if key not in self.get_field_annotations().keys():
            return default_value
        return getattr(self, key, default_value)


class PermissionRequirements(__Serializable):
    reload: int = 3

    def get_permission(self, cmd: str, default_value: int):
        return self.serialize().get(cmd, default_value)


# class Configuration(ConfigurationBase):
class Configuration(__Serializable):
    command_prefix: Union[List[str], str] = '!!template'
    permission_requirements: PermissionRequirements = PermissionRequirements.get_default()
    enable_permission_check: bool = True

    debug: bool
    verbosity: bool

    @property
    def prefix(self) -> List[str]:
        return list(set(self.command_prefix)) if isinstance(self.command_prefix, list) else [self.command_prefix]

    @property
    def primary_prefix(self) -> str:
        return self.prefix[0]

    @property
    def enable_debug_commands(self):
        return self.get('debug', False)

    @property
    def is_verbose(self):
        return self.get("verbosity", False)

    def after_load(self, plugin_inst):
        plugin_inst.set_verbose(self.is_verbose)

    def get_permission_checker(self, *cmd: str, default_value: int = 0):
        if not self.enable_permission_check:
            return lambda: True
        perm = default_value
        for item in cmd:
            current_item_perm = self.permission_requirements.get_permission(item, default_value)
            perm = perm if perm >= current_item_perm else current_item_perm
        return lambda src: src.has_permission(perm)
