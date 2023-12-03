import contextlib
import logging
import os
import re
import threading
from typing import Optional, Callable

from mcdreforged.api.types import CommandSource, MCDReforgedLogger
from mcdreforged.api.rtext import RColor, RTextBase, RText
from mcdreforged.api.event import MCDRPluginEvents

from my_plugin.utils.misc import psi
from my_plugin.utils.file_util import ensure_dir
from my_plugin.utils.translation import MessageText


class BlossomLogger(MCDReforgedLogger):
    class NoColorFormatter(logging.Formatter):
        def formatMessage(self, record) -> str:
            return self.clean_console_color_code(super().formatMessage(record))

        @staticmethod
        def clean_console_color_code(text: str) -> str:
            return re.compile(r'\033\[(\d+(;\d+)?)?m').sub('', text)

    __inst: Optional["BlossomLogger"] = None
    __verbosity: bool = False

    __SINGLE_FILE_LOG_PATH: Optional[str] = None
    if psi is not None:
        __SINGLE_FILE_LOG_PATH = f'{psi.get_self_metadata().id}.log'
    FILE_FMT: NoColorFormatter = NoColorFormatter(
        '[%(name)s] [%(asctime)s] [%(threadName)s/%(levelname)s]: %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    @classmethod
    def get_instance(cls) -> "BlossomLogger":
        if cls.__inst is None:
            cls.__inst = cls().bind_single_file()
        return cls.__inst

    @classmethod
    def set_verbose(cls, verbosity: bool) -> None:
        cls.__verbosity = verbosity
        cls.get_instance().debug("Verbose mode enabled")

    @classmethod
    def get_verbose(cls) -> bool:
        return cls.__verbosity

    def __init__(self):
        if psi is not None:
            super().__init__(psi.get_self_metadata().id)
            psi.register_event_listener(MCDRPluginEvents.PLUGIN_LOADED, lambda *args, **kwargs: self.unbind_file())
        else:
            super().__init__()

    def debug(self, *args, option=None, no_check: bool = False) -> None:
        return super().debug(*args, option=option, no_check=no_check or self.__verbosity)

    def unbind_file(self) -> None:
        if self.file_handler is not None:
            self.removeHandler(self.file_handler)
            self.file_handler.close()
            self.file_handler = None

    def bind_single_file(self, file_name: Optional[str] = None) -> "BlossomLogger":
        if file_name is None:
            if self.__SINGLE_FILE_LOG_PATH is None:
                return self
            file_name = os.path.join(psi.get_data_folder(), self.__SINGLE_FILE_LOG_PATH)
        self.unbind_file()
        ensure_dir(os.path.dirname(file_name))
        self.file_handler = logging.FileHandler(file_name, encoding='UTF-8')
        self.file_handler.setFormatter(self.FILE_FMT)
        self.addHandler(self.file_handler)
        return self


class ConfigSerializeLogger:
    def __init__(self, verbose: bool = True):
        self.__verbose = verbose
        self.__lock = threading.RLock()
        self.__src: Optional[CommandSource] = None
        self.__logger = logger
        self.__cached_verbose = None
        self.__log_record = []
        self.__recording = False

    @property
    def log_record(self):
        return self.__log_record

    def log(self, func: Callable, msg, *args, exc_info: Optional[BaseException] = None, **kwargs):
        if self.__recording:
            self.__log_record.append(msg)
        if self.__src is not None:
            self.__src.reply(msg)
        if self.__verbose:
            func(msg, *args, exc_info=exc_info, **kwargs)

    @staticmethod
    def __set_color(msg: MessageText, color: RColor):
        if isinstance(msg, RTextBase):
            return msg.set_color(color)
        return RText(msg, color)

    def info(self, msg, *args, **kwargs):
        self.log(self.__logger.info, msg, *args, **kwargs)

    def error(self, msg, *args, exc_info: Optional[BaseException] = None, **kwargs):
        msg = self.__set_color(msg, RColor.red)
        self.log(self.__logger.error, msg, *args, exc_info=exc_info, **kwargs)

    def warn(self, msg, *args, exc_info: Optional[BaseException] = None, **kwargs):
        msg = self.__set_color(msg, RColor.yellow)
        self.log(self.__logger.warning, msg, *args, exc_info=exc_info, **kwargs)

    @contextlib.contextmanager
    def reply_to_source_context(self, verbose: bool = True, source: Optional[CommandSource] = None):
        with self.__lock:
            try:
                self.__cached_verbose = self.__verbose
                self.__verbose = verbose
                self.__src = source
                yield
            finally:
                self.__verbose = self.__cached_verbose
                self.__src = None
                self.__cached_verbose = None

    @contextlib.contextmanager
    def record_context(self, verbose: bool = True, source: Optional[CommandSource] = None):
        with self.__lock:
            self.__log_record = []
            self.__recording = True
            try:
                with self.reply_to_source_context(verbose=verbose, source=source):
                    yield
            finally:
                self.__recording = False


logger: BlossomLogger = BlossomLogger.get_instance()
