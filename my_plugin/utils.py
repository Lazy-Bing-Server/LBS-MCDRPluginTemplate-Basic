import re
import sys
import inspect
import functools
import threading

from mcdreforged.api.types import ServerInterface, PluginServerInterface
from mcdreforged.api.rtext import *
from mcdreforged.api.decorator import FunctionThread
from typing import Union, Optional, Dict, Callable, List


DEBUG = True
gl_server: PluginServerInterface = ServerInterface.get_instance().as_plugin_server_interface()
TRANSLATION_KEY_PREFIX = gl_server.get_self_metadata().id
MessageText = Union[str, RTextBase]


def htr(translation_key: str, *args, prefixes: Optional[List[str]] = None, **kwargs) -> RTextMCDRTranslation:
    def __get_regex_result(line: str):
        pattern = r'(?<=§7){}[\S ]*?(?=§)'
        for prefix_tuple in prefixes:
            for prefix in prefix_tuple:
                result = re.search(pattern.format(prefix), line)
                if result is not None:
                    return result
        return None

    def __htr(key: str, *inner_args, **inner_kwargs):
        original, processed = ntr(key, *inner_args, **inner_kwargs), []
        if not isinstance(original, str):
            return key
        for line in original.splitlines():
            result = __get_regex_result(line)
            if result is not None:
                command = result.group() + ' '
                processed.append(RText(line).c(RAction.suggest_command, command).h(
                    rtr(f'hover.suggest', command)))
            else:
                processed.append(line)
        return RTextBase.join('\n', processed)

    return rtr(translation_key, *args, **kwargs).set_translator(__htr)


def debug_log(text: Union[RTextBase, str]):
    gl_server.logger.debug(text, no_check=DEBUG)


def get_thread_prefix():
    return to_camel_case(gl_server.get_self_metadata().name, divider='_') + '_'


def rtr(translation_key: str, *args, with_prefix=True, **kwargs) -> RTextMCDRTranslation:
    prefix = gl_server.get_self_metadata().id + '.'
    if with_prefix and not translation_key.startswith(prefix):
        translation_key = f"{prefix}{translation_key}"
    return gl_server.rtr(translation_key, *args, **kwargs).set_translator(ntr)


def named_thread(arg: Optional[Union[str, Callable]] = None):
    def wrapper(func):
        @functools.wraps(func)  # to preserve the origin function information
        def wrap(*args, **kwargs):
            def try_func():
                try:
                    return func(*args, **kwargs)
                finally:
                    if sys.exc_info()[0] is not None:
                        gl_server.logger.exception('Error running thread {}'.format(threading.current_thread().name))

            prefix = get_thread_prefix()
            thread = FunctionThread(target=try_func, args=[], kwargs={}, name=prefix + thread_name)
            thread.start()
            return thread

        # bring the signature of the func to the wrap function
        # so inspect.getfullargspec(func) works correctly
        wrap.__signature__ = inspect.signature(func)
        wrap.original = func  # access this field to get the original function
        return wrap

    # Directly use @new_thread without ending brackets case, e.g. @new_thread
    if isinstance(arg, Callable):
        thread_name = to_camel_case(arg.__name__, divider="_")
        return wrapper(arg)
    # Use @new_thread with ending brackets case, e.g. @new_thread('A'), @new_thread()
    else:
        thread_name = arg
        return wrapper


def ntr(translation_key: str, *args, language: Optional[str] = None,
        allow_failure: bool = True, **kwargs) -> MessageText:
    try:
        return gl_server.tr(
            translation_key, *args, language=language, allow_failure=False, **kwargs
        )
    except (KeyError, ValueError):
        fallback_language = gl_server.get_mcdr_language()
        try:
            if fallback_language == 'en_us':
                raise KeyError(translation_key)
            return gl_server.tr(
                translation_key, *args, language='en_us', allow_failure=allow_failure, **kwargs
            )
        except (KeyError, ValueError):
            languages = []
            for item in (language, fallback_language, 'en_us'):
                if item not in languages:
                    languages.append(item)
            languages = ', '.join(languages)
            if allow_failure:
                gl_server.logger.error(f'Error translate text "{translation_key}" to language {languages}')
            else:
                raise KeyError(f'Translation key "{translation_key}" not found with language {languages}')


def to_camel_case(string: str, divider: str = ' ', upper: bool = True):
    word_list = [capitalize(item) for item in string.split(divider)]
    if not upper:
        first_word_char_list = list(word_list[0])
        first_word_char_list[0] = first_word_char_list[0].lower()
        word_list[0] = ''.join(first_word_char_list)
    return ''.join(word_list)


def capitalize(string: str):
    char_list = list(string)
    char_list[0] = char_list[0].upper()
    return ''.join(char_list)


def dtr(translation_dict: Dict[str, str], *args, **kwargs):
    def fake_tr(
            translation_key: str,
            *inner_args,
            language: Optional[str] = None,
            allow_failure: bool = True,
            **inner_kwargs
    ) -> MessageText:
        result = translation_dict.get(language)
        fallback_language = [gl_server.get_mcdr_language()]
        if 'en_us' not in fallback_language and 'en_us' != language:
            fallback_language.append('en_us')
        for lang in fallback_language:
            result = translation_dict.get(lang)
            if result is not None:
                use_rtext = any([isinstance(e, RTextBase) for e in list(inner_args) + list(inner_kwargs.values())])
                if use_rtext:
                    return RTextBase.format(result, *inner_args, **inner_kwargs)
                return result.format(*inner_args, **inner_kwargs)
        if result is None:
            if allow_failure:
                return '<Translation failed>'
            raise KeyError(
                        'Failed to translate from dict with translations {}, language {}, fallback_language {}'.format(
                            translation_dict, language, ', '.join(fallback_language)))

    return RTextMCDRTranslation('', *args, **kwargs).set_translator(fake_tr)
