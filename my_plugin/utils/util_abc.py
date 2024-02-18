from typing import TYPE_CHECKING, Optional


if TYPE_CHECKING:
    from my_plugin.my_plugin import MyPlugin


class AbstractUtil:
    _plugin_inst: Optional[MyPlugin] = None

    @classmethod
    def set_plugin_instance(cls, plugin_inst: "MyPlugin"):
        cls._plugin_inst = plugin_inst
