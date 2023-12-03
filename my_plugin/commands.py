from typing import Union, Iterable, List
from mcdreforged.api.types import CommandSource
from mcdreforged.api.command import *

from my_plugin.utils.misc import psi
from my_plugin.utils.translation import htr, rtr
from my_plugin.config import config


def show_help(source: CommandSource):
    meta = psi.get_self_metadata()
    source.reply(
        htr(
            'help.detailed',
            prefixes=config.prefix,
            prefix=config.primary_prefix,
            name=meta.name,
            ver=str(meta.version)
        )
    )


def reload_self(source: CommandSource):
    config.set_reloader(source)
    psi.reload_plugin(psi.get_self_metadata().id)


def register_command():
    def permed_literal(literals: Union[str, Iterable[str]]) -> Literal:
        literals = {literals} if isinstance(literals, str) else set(literals)
        return Literal(literals).requires(config.get_permission_checker(*literals))

    root_node: Literal = Literal(config.prefix).runs(lambda src: show_help(src))

    children: List[AbstractNode] = [
        permed_literal('reload').runs(lambda src: reload_self(src))
    ]

    debug_nodes: List[AbstractNode] = []

    if config.enable_debug_commands:
        children += debug_nodes

    for node in children:
        root_node.then(node)

    psi.register_command(root_node)
