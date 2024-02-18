from mcdreforged.api.types import PluginServerInterface
from my_plugin.my_plugin import MyPlugin


__main = MyPlugin.get_instance()


def on_load(server: PluginServerInterface, prev_module):
    __main.on_load(server, prev_module)
