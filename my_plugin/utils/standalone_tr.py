import contextlib
import json
import os
import re
from threading import RLock
from typing import Optional, List, Dict, Union, TYPE_CHECKING

from mcdreforged.api.rtext import *
from mcdreforged.api.types import ServerInterface
from ruamel.yaml import YAML

from my_plugin.constants import PLUGIN_ID
from my_plugin.generic import MessageText
from my_plugin.utils.file_util import FileUtils

if TYPE_CHECKING:
    from my_plugin.my_plugin import MyPlugin

_NONE = object()


class BlossomTranslator:
    PATH = 'resources/lang'
    yaml = YAML(typ='safe')

    def __init__(self, plugin_inst: "MyPlugin"):
        self.__inst = plugin_inst
        self.__storage = {}
        self.__lock = RLock()
        self.__language_translate_order = ['en_us']
        self.__initialized = False
        self.__translation_key_prefix = None
        psi = ServerInterface.psi_opt()
        if psi is not None:
            self.set_language(psi.get_mcdr_language())

    @property
    def logger(self):
        return self.__inst.logger

    def set_language(self, language: str):
        with self.__lock:
            if language in self.__language_translate_order:
                self.__language_translate_order.remove(language)
            self.__language_translate_order = [language] + self.__language_translate_order

    def register_translation(self, translation_dict: Dict[str, Union[dict, str]], language: str):
        def get_full_key_value_map(
                target_dict: Dict[str, Union[dict, str]],
                result_dict: Optional[Dict[str, str]] = None,
                current_layer: Optional[List[str]] = None
        ):
            if current_layer is None:
                current_layer = []
            if result_dict is None:
                result_dict = {}
            for k, v in target_dict.items():
                this_layer = current_layer.copy()
                this_layer.append(k)
                if len(current_layer) == 0 and k not in self.allowed_keys:
                    continue
                if isinstance(v, dict):
                    get_full_key_value_map(v, result_dict=result_dict, current_layer=this_layer)
                else:
                    result_dict['.'.join(this_layer)] = str(v)
            return result_dict

        translation_dict = get_full_key_value_map(translation_dict)
        for key, value in translation_dict.items():
            if key not in self.__storage.keys() or not isinstance(self.__storage[key], dict):
                self.__storage[key] = {}
            self.__storage[key][language] = value

    def register_translation_file(self, file_path: str, bundled: bool = True, encoding: str = 'utf8') -> bool:
        file_name = os.path.basename(file_path)
        if '.' not in list(file_name):
            return False
        language, file_extension = file_name.rsplit('.', 1)
        if file_extension in ['json', 'yml', 'yaml']:
            try:
                if bundled:
                    with self.__inst.open_bundled_file(file_path) as file:
                        text = file.read().decode(encoding=encoding)
                else:
                    with open(file_path, 'r', encoding=encoding) as f:
                        text = f.read()
                if file_extension == 'json':
                    translation_dict = json.loads(text)
                else:
                    translation_dict = self.yaml.load(text)
                if isinstance(translation_dict, dict):
                    self.register_translation(translation_dict, language)
                return True
            except:
                pass
        return False

    def register_bundled_translations(self):
        for file_name in FileUtils.list_bundled_file(self.PATH):
            file_path = os.path.join(self.PATH, file_name)
            if not self.register_translation_file(file_path):
                self.__inst.debug('Skipping unknown translation file {} in {}'.format(file_name, repr(self)))
        self.__initialized = True

    @property
    def allowed_keys(self):
        return [PLUGIN_ID]

    def has_translation(self, translation_key: str, override_language: Optional[str] = None):
        trans = self.__storage.get(translation_key)
        if isinstance(trans, dict):
            with self.language_context(override_language):
                for lang in self.__language_translate_order:
                    if lang in trans.keys():
                        return True
        return False

    @contextlib.contextmanager
    def language_context(self, language: Optional[str]):
        with self.__lock:
            language_order = self.__language_translate_order
            self.__language_translate_order = self.__language_translate_order.copy()
            try:
                if language is not None:
                    self.set_language(language)
                yield
            finally:
                self.__language_translate_order = language_order

    def translate_from_storage(self, translations: Dict[str, str]) -> MessageText:
        translated_formatter, default = None, _NONE
        for lang in self.__language_translate_order:
            translated_formatter = translations.get(lang)
            if translated_formatter is not None:
                break
        if translated_formatter is None:
            translated_formatter = default
        return translated_formatter

    def __dtr(self, translation_dict: Dict[str, str], *args, **kwargs):
        translated_formatter = _NONE
        for lang in self.__language_translate_order:
            translated_formatter = translation_dict.get(lang, _NONE)
            if translated_formatter is not _NONE:
                break
        # Allow null value in translation files
        if translated_formatter is None:
            translated_formatter = ''
        if translated_formatter is _NONE:
            raise KeyError("Translation key does not exist")

        use_rtext = any([isinstance(e, RTextBase) for e in list(args) + list(kwargs.values())])
        try:
            if use_rtext:
                return RTextBase.format(translated_formatter, *args, **kwargs)
            else:
                return translated_formatter.format(*args, **kwargs)
        except Exception as e:
            raise ValueError(f'Failed to apply args {args} and kwargs {kwargs} to translated_text {translated_formatter}: {str(e)}')

    def ntr(
            self, translation_key: str, *args, language: Optional[str] = None, _mcdr_tr_language: Optional[str] = None,
            _mcdr_tr_allow_failure: bool = True, _default_fallback: Optional[MessageText] = None,
            _log_error_message: bool = True, **kwargs
    ) -> MessageText:
        if not self.__initialized:
            raise RuntimeError('Illegal translate request before translation loading')
        if language is not None and _mcdr_tr_language is None:
            _mcdr_tr_language = language
        if _default_fallback is None:
            _default_fallback = translation_key
        translation_dict = self.__storage.get(translation_key, {})
        with self.language_context(language=_mcdr_tr_language):
            try:
                return self.__dtr(translation_dict, *args, **kwargs)
            except Exception as e:
                lang_text = ', '.join([f'"{l}"' for l in self.__language_translate_order])
                error_message = 'Error translate text "{}" to language {}: {}'.format(translation_key, lang_text, str(e))
                if _mcdr_tr_allow_failure:
                    if _log_error_message:
                        self.logger.error(error_message)
                    return _default_fallback
                else:
                    raise e

    def htr(self, translation_key: str, *args, _prefixes: Optional[List[str]] = None, **kwargs) -> RTextMCDRTranslation:
        def __get_regex_result(line: str):
            pattern = r'(?<=§7){}[\S ]*?(?=§)'
            for prefix_tuple in _prefixes:
                for prefix in prefix_tuple:
                    result = re.search(pattern.format(prefix), line)
                    if result is not None:
                        return result
            return None

        def __htr(key: str, *inner_args, **inner_kwargs) -> MessageText:
            original, processed = self.ntr(key, *inner_args, **inner_kwargs), []
            if not isinstance(original, str):
                return key
            for line in original.splitlines():
                result = __get_regex_result(line)
                if result is not None:
                    command = result.group() + ' '
                    processed.append(RText(line).c(RAction.suggest_command, command).h(
                        self.rtr(f'hover.suggest', command)))
                else:
                    processed.append(line)
            return RTextBase.join('\n', processed)

        return self.rtr(translation_key, *args, **kwargs).set_translator(__htr)

    def get_translation_key_prefix(self, *args):
        if self.__translation_key_prefix is None:
            self.__translation_key_prefix = f'{PLUGIN_ID}.'
        return '.'.join(list(self.__translation_key_prefix.rstrip('.').split('.')) + list(args)) + '.'

    def rtr(self, translation_key: str, *args, _with_prefix: bool = True, **kwargs) -> RTextMCDRTranslation:
        prefix = self.get_translation_key_prefix()
        if _with_prefix and not translation_key.startswith(prefix):
            translation_key = f"{prefix}{translation_key}"
        return RTextMCDRTranslation(translation_key, *args, **kwargs).set_translator(self.ntr)

    def ktr(
            self, translation_key: str, *args, _default_fallback: Optional[MessageText] = None,
            _log_error_message: bool = False, _prefix: Optional[str] = None, **kwargs
    ) -> RTextMCDRTranslation:
        actual_translation_key = translation_key
        if _prefix is None:
            _prefix = self.get_translation_key_prefix()
        if not translation_key.startswith(_prefix):
            actual_translation_key = f"{_prefix}{translation_key}"
        return RTextMCDRTranslation(
            actual_translation_key, *args, _log_error_message=_log_error_message,
            _default_fallback=translation_key if _default_fallback is None else _default_fallback, **kwargs
        ).set_translator(self.ntr)

    def dtr(self, translation_dict: Dict[str, str], *args, **kwargs):
        def fake_tr(
                translation_key: str,
                *inner_args,
                language: Optional[str] = None,
                _mcdr_tr_language: Optional[str] = None,
                _mcdr_tr_allow_failure: bool = True,
                _log_error_message: bool = True,
                _default_fallback: str = '<Translation failed>',
                **inner_kwargs
        ) -> MessageText:
            if language is not None and _mcdr_tr_language is None:
                _mcdr_tr_language = language
            try:
                return self.__dtr(translation_dict, *inner_args, _mcdr_tr_language=_mcdr_tr_language, **inner_kwargs)
            except Exception as e:
                lang_text = ', '.join([f'"{l}"' for l in self.__language_translate_order])
                error_message = f'Error translate text from dict to language {lang_text}: {str(e)}'
                if _mcdr_tr_allow_failure:
                    if _log_error_message:
                        self.logger.error(error_message)
                    return _default_fallback
                else:
                    raise e
        return RTextMCDRTranslation('', *args, **kwargs).set_translator(fake_tr)
