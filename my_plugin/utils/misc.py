import functools
import inspect
import sys
import threading
from ruamel import yaml
from io import StringIO
from typing import Optional, Callable, Union, TYPE_CHECKING

from mcdreforged.api.decorator import FunctionThread
from mcdreforged.api.types import PluginServerInterface, ServerInterface

from my_plugin.utils.util_abc import AbstractUtil

if TYPE_CHECKING:
    from my_plugin.my_plugin import MyPlugin


class MiscTools(AbstractUtil):
    @classmethod
    def get_thread_prefix(cls) -> str:
        return cls.to_camel_case(cls._plugin_inst.server.get_self_metadata().name, divider='_') + '_'

    @classmethod
    def named_thread(cls, arg: Optional[Union[str, Callable]] = None) -> Callable:
        def wrapper(func):
            @functools.wraps(func)
            def wrap(*args, **kwargs):
                def try_func():
                    try:
                        return func(*args, **kwargs)
                    finally:
                        if sys.exc_info()[0] is not None:
                            cls._plugin_inst.server.logger.exception('Error running thread {}'.format(threading.current_thread().name))

                prefix = cls.get_thread_prefix()
                thread = FunctionThread(target=try_func, args=[], kwargs={}, name=prefix + thread_name)
                thread.start()
                return thread

            wrap.__signature__ = inspect.signature(func)
            wrap.original = func
            return wrap

        # Directly use @new_thread without ending brackets case, e.g. @new_thread
        if isinstance(arg, Callable):
            thread_name = cls.to_camel_case(arg.__name__, divider="_")
            return wrapper(arg)
        # Use @new_thread with ending brackets case, e.g. @new_thread('A'), @new_thread()
        else:
            thread_name = arg
            return wrapper

    @classmethod
    def to_camel_case(cls, string: str, divider: str = ' ', upper: bool = True) -> str:
        word_list = [cls.capitalize(item) for item in string.split(divider)]
        if not upper:
            first_word_char_list = list(word_list[0])
            first_word_char_list[0] = first_word_char_list[0].lower()
            word_list[0] = ''.join(first_word_char_list)
        return ''.join(word_list)

    @staticmethod
    def capitalize(string: str) -> str:
        if string == '':
            return ''
        char_list = list(string)
        char_list[0] = char_list[0].upper()
        return ''.join(char_list)

    @staticmethod
    def yaml_dump_to_string(data: Union[dict, list], yaml_inst: Optional[yaml.YAML] = None):
        if yaml_inst is None:
            yaml_inst = yaml.YAML(typ='rt')
            yaml_inst.width = 1048576
        with StringIO() as stream:
            yaml_inst.dump(data, stream)
            stream.seek(0)
            return stream.read()
