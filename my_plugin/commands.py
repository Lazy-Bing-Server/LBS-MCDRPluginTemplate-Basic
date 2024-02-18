from typing import Union, Iterable, List, TYPE_CHECKING, Optional
from mcdreforged.api.types import CommandSource
from mcdreforged.api.command import *
from mcdreforged.api.rtext import *

import re

from my_plugin.generic import MessageText


if TYPE_CHECKING:
    from my_plugin.my_plugin import MyPlugin


class CommandManager:
    def __init__(self, plugin_inst: "MyPlugin"):
        self.plugin_inst = plugin_inst

    @property
    def server(self):
        return self.plugin_inst.server

    @property
    def config(self):
        return self.plugin_inst.config

    def htr(self, translation_key: str, *args, _lb_htr_prefixes: Optional[List[str]] = None,
            **kwargs) -> RTextMCDRTranslation:
        def __get_regex_result(line: str):
            pattern = r'(?<=§7){}[\S ]*?(?=§)'
            for prefix_tuple in _lb_htr_prefixes:
                for prefix in prefix_tuple:
                    result = re.search(pattern.format(prefix), line)
                    if result is not None:
                        return result
            return None

        def __htr(key: str, *inner_args, **inner_kwargs) -> MessageText:
            original, processed = self.plugin_inst.ntr(key, *inner_args, **inner_kwargs), []
            if not isinstance(original, str):
                return key
            for line in original.splitlines():
                result = __get_regex_result(line)
                if result is not None:
                    command = result.group() + ' '
                    processed.append(RText(line).c(RAction.suggest_command, command).h(
                        self.plugin_inst.rtr(f'hover.suggest', command)))
                else:
                    processed.append(line)
            return RTextBase.join('\n', processed)

        return RTextMCDRTranslation(translation_key, *args, **kwargs).set_translator(__htr)

    def show_help(self, source: CommandSource):
        meta = self.server.get_self_metadata()
        source.reply(
            self.htr(
                'help.detailed',
                _lb_htr_prefixes=self.config.prefix,
                prefix=self.config.primary_prefix,
                name=meta.name,
                ver=str(meta.version)
            )
        )

    def reload_self(self, source: CommandSource):
        # self.config.set_reloader(source)
        self.server.reload_plugin(self.server.get_self_metadata().id)
        source.reply(self.plugin_inst.rtr('loading.reloaded'))

    def register_command(self):
        def permed_literal(literals: Union[str, Iterable[str]]) -> Literal:
            literals = {literals} if isinstance(literals, str) else set(literals)
            return Literal(literals).requires(self.config.get_permission_checker(*literals))

        root_node: Literal = Literal(self.config.prefix).runs(lambda src: self.show_help(src))

        children: List[AbstractNode] = [
            permed_literal('reload').runs(lambda src: self.reload_self(src))
        ]

        debug_nodes: List[AbstractNode] = []

        if self.config.enable_debug_commands:
            children += debug_nodes

        for node in children:
            root_node.then(node)

        self.server.register_command(root_node)
