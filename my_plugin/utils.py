import logging

from mcdreforged.api.types import ServerInterface, PluginServerInterface, MCDReforgedLogger
from mcdreforged.api.rtext import *
from typing import Optional


DEBUG = True
gl_server: PluginServerInterface = ServerInterface.get_instance().as_plugin_server_interface()
TRANSLATION_KEY_PREFIX = gl_server.get_self_metadata().id


class PluginLogger(MCDReforgedLogger):
    DEFAULT_NAME = 'MCDR'
    __verbosity = False

    def debug(self, *args, option=None, no_check: bool = False):
        if self.__verbosity:
            super(PluginLogger, self).debug(*args, option, no_check=True)
        elif option is not None:
            super(PluginLogger, self).debug(*args, option)

    def set_file(self, file_name: str):
        if self.file_handler is not None:
            self.removeHandler(self.file_handler)
        self.file_handler = logging.FileHandler(file_name, encoding='UTF-8')
        self.file_handler.setFormatter(self.FILE_FMT)
        self.addHandler(self.file_handler)

    def set_verbose(self, verbosity: bool):
        self.__verbosity = verbosity


logger = PluginLogger()


def tr(translation_key: str, *args, with_prefix=True, **kwargs) -> RTextMCDRTranslation:
    translation_key = translation_key if with_prefix and not translation_key.startswith(TRANSLATION_KEY_PREFIX) else \
        f"{TRANSLATION_KEY_PREFIX}.{translation_key}"
    return gl_server.rtr(translation_key, *args, **kwargs)


def ntr(translation_key: str, *args, with_prefix: bool = True, language: Optional[str] = None, **kwargs) -> str:
    translation_key = translation_key if with_prefix and not translation_key.startswith(TRANSLATION_KEY_PREFIX) else \
        f"{TRANSLATION_KEY_PREFIX}.{translation_key}"
    return gl_server.tr(translation_key, *args, language=language, **kwargs)
