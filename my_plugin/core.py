from typing import Union, Iterable, List
from mcdreforged.api.types import CommandSource
from mcdreforged.api.command import *

from my_plugin.utils import gl_server, rtr, DEBUG, htr
from my_plugin.config import config


def show_help(source: CommandSource):
    meta = gl_server.get_self_metadata()
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
    gl_server.reload_plugin(gl_server.get_self_metadata().id)
    source.reply(rtr('msg.reloaded'))


def register_command():
    def permed_literal(literals: Union[str, Iterable[str]]) -> Literal:
        literals = {literals} if isinstance(literals, str) else set(literals)
        perm = 1
        for item in literals:
            target_perm = config.get_prem(item)
            if target_perm > perm:
                perm = target_perm
        return Literal(literals).requires(lambda src: src.has_permission(target_perm))

    root_node: Literal = Literal(config.prefix).runs(lambda src: show_help(src))

    children: List[AbstractNode] = [
        permed_literal('reload').runs(lambda src: reload_self(src))
    ]

    debug_nodes: List[AbstractNode] = []

    if DEBUG:
        children += debug_nodes

    for node in children:
        root_node.then(node)

    gl_server.register_command(root_node)
