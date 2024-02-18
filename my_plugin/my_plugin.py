import os.path

from mcdreforged.api.types import ServerInterface, PluginServerInterface, MCDReforgedLogger
from mcdreforged.api.rtext import RTextMCDRTranslation
from typing import Optional, Self, IO

from my_plugin.config import Configuration
from my_plugin.commands import CommandManager
from my_plugin.utils.logger import BlossomLogger

# from my_plugin.utils.standalone_tr import BlossomTranslator

from my_plugin.generic import MessageText
from my_plugin.constants import TRANSLATION_KEY_PREFIX, CONFIG_FILE


class MyPlugin:
    __instance: Optional[Self] = None

    @classmethod
    def get_instance(cls) -> Self:
        if cls.__instance is None:
            cls.__instance = cls()
        return cls.__instance

    def __init__(self):
        self.server = ServerInterface.psi()
        # self.server = ServerInterface.psi_opt()  # psi_opt() if requires to be run standalone
        self.__verbosity = False
        # self.translator = BlossomTranslator(self)
        # self.translator.register_bundled_translations()
        # self.logger = BlossomLogger(self)
        # self.logger.blossom_bind_single_file()
        # self.config = Configuration.load(self)
        self.config = self.server.load_config_simple(
            os.path.join(self.get_data_folder(), CONFIG_FILE),
            target_class=Configuration
        )


        self.command_manager = CommandManager(self)

    @property
    def logger(self) -> MCDReforgedLogger:
        return self.server.logger

    @property
    def verbosity(self):
        return self.__verbosity

    def debug(self, msg, *args, no_check: bool = False, **kwargs):
        return self.logger.debug(msg, *args, **kwargs, no_check=self.__verbosity or no_check)

    def get_data_folder(self):
        return self.server.get_data_folder()

    def set_verbose(self, verbosity: bool):
        self.__verbosity = verbosity
        if self.__verbosity:
            self.debug("Verbose mode enabled")

    def on_load(self, server: PluginServerInterface, prev_module):
        server.register_help_message(self.config.primary_prefix, self.rtr('help.mcdr'))
        # self.logger.register_event_listeners()
        self.command_manager.register_command()

    # Translations
    def rtr(
            self,
            translation_key: str,
            *args,
            _lb_rtr_prefix: str = TRANSLATION_KEY_PREFIX,
            **kwargs
    ) -> RTextMCDRTranslation:
        if not translation_key.startswith(_lb_rtr_prefix):
            translation_key = f"{_lb_rtr_prefix}{translation_key}"
        return RTextMCDRTranslation(translation_key, *args, **kwargs).set_translator(self.ntr)

    def ntr(
            self,
            translation_key: str,
            *args,
            _mcdr_tr_language: Optional[str] = None,
            _mcdr_tr_allow_failure: bool = True,
            _mcdr_tr_fallback_language: Optional[str] = None,
            _lb_tr_default_fallback: Optional[MessageText] = None,
            _lb_tr_log_error_message: bool = True,
            **kwargs
    ) -> MessageText:
        try:
            return self.server.tr(
                translation_key,
                *args,
                _mcdr_tr_language=_mcdr_tr_language,
                _mcdr_tr_fallback_language=_mcdr_tr_fallback_language or 'en_us',
                _mcdr_tr_allow_failure=False,
                **kwargs
            )
        except (KeyError, ValueError):
            languages = []
            for item in (_mcdr_tr_language, _mcdr_tr_fallback_language):
                if item not in languages:
                    languages.append(item)
            languages = ', '.join(languages)
            if _mcdr_tr_allow_failure:
                if _lb_tr_log_error_message:
                    self.logger.error(f'Error translate text "{translation_key}" to language {languages}')
                if _lb_tr_default_fallback is None:
                    return translation_key
                return _lb_tr_default_fallback
            else:
                raise KeyError(f'Translation key "{translation_key}" not found with language {languages}')

    def ktr(
            self,
            translation_key: str,
            *args,
            _lb_tr_default_fallback: Optional[MessageText] = None,
            _lb_tr_log_error_message: bool = False,
            _lb_rtr_prefix: str = TRANSLATION_KEY_PREFIX,
            **kwargs
    ) -> RTextMCDRTranslation:
        return self.rtr(
            translation_key, *args,
            _lb_rtr_prefix=_lb_rtr_prefix,
            _lb_tr_log_error_message=_lb_tr_log_error_message,
            _lb_tr_default_fallback=translation_key if _lb_tr_default_fallback is None else _lb_tr_default_fallback,
            **kwargs
        )

    def open_bundled_file(self, file_path: str) -> 'IO[bytes]':
        return self.server.open_bundled_file(file_path)

    """
    # Only MCDR plugin, turn into ABC
    def open_bundled_file(self, file_path: str) -> 'IO[bytes]':
        raise NotImplementedError

    def get_package_path(self):
        raise NotImplementedError
    """