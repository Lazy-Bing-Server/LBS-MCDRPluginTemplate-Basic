from mcdreforged.api.all import *
from typing import TYPE_CHECKING, Optional
if TYPE_CHECKING:
    from my_plugin.config import Configuration

__loading_exc: Optional[Exception] = None
config: Optional["Configuration"] = None
try:
    from my_plugin.utils.translation import rtr, MessageText
    from my_plugin.config import config
    from my_plugin.commands import register_command
    __all__ = []
except Exception as exc:
    __loading_exc = exc


def on_load(server: PluginServerInterface, prev_module):
    reload_source: Optional[CommandSource] = None
    if prev_module is not None:
        try:
            prev_config: Optional["Configuration"] = getattr(prev_module, 'config')
        except AttributeError:
            prev_config = None
        try:
            reload_source = prev_config.reloader
        except:
            reload_source = None

    def reload_reply(msg: MessageText):
        if reload_source is not None and isinstance(reload_source, PlayerCommandSource):
            reload_source.reply(msg)

    if __loading_exc is not None:
        id_ = server.get_self_metadata().id
        reload_reply(server.rtr(f'{id_}.loading.reloading_failed', id=id_).set_color(RColor.red))
        reload_reply(RTextList(
                "§7<§r", RText(__loading_exc.__class__.__name__, RColor.dark_red, RStyle.bold), "§7>§r ",
                RText(str(__loading_exc), RColor.red)
            ))
        server.unload_plugin(id_)
        raise __loading_exc

    while True:
        if len(config.logger.log_record) == 0:
            break
        reload_reply(config.logger.log_record.pop(0))

    server.register_help_message(config.primary_prefix, rtr('help.mcdr'))
    register_command()
    reload_reply(rtr('loading.reloaded'))
