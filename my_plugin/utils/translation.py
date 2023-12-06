import re
from typing import Union, Optional, List, Dict

from mcdreforged.api.rtext import *

from my_plugin.utils.misc import psi

MessageText: type = Union[str, RTextBase]
TRANSLATION_KEY_PREFIX = psi.get_self_metadata().id + '.'


def htr(translation_key: str, *args, prefixes: Optional[List[str]] = None, **kwargs) -> RTextMCDRTranslation:
    def __get_regex_result(line: str):
        pattern = r'(?<=§7){}[\S ]*?(?=§)'
        for prefix_tuple in prefixes:
            for prefix in prefix_tuple:
                result = re.search(pattern.format(prefix), line)
                if result is not None:
                    return result
        return None

    def __htr(key: str, *inner_args, **inner_kwargs) -> MessageText:
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


def rtr(translation_key: str, *args, with_prefix: bool = True, **kwargs) -> RTextMCDRTranslation:
    if with_prefix and not translation_key.startswith(TRANSLATION_KEY_PREFIX):
        translation_key = f"{TRANSLATION_KEY_PREFIX}{translation_key}"
    return RTextMCDRTranslation(translation_key, *args, **kwargs).set_translator(ntr)


def ntr(
        translation_key: str, *args, language: Optional[str] = None, _mcdr_tr_language: Optional[str] = None,
        allow_failure: bool = True, _default_fallback: Optional[MessageText] = None, log_error_message: bool = True, **kwargs
) -> MessageText:
    if language is not None and _mcdr_tr_language is None:
        _mcdr_tr_language = language
    try:
        return psi.tr(
            translation_key, *args, language=_mcdr_tr_language,
            _mcdr_tr_language=_mcdr_tr_language, allow_failure=False, **kwargs
        )
    except (KeyError, ValueError):
        fallback_language = psi.get_mcdr_language()
        try:
            if fallback_language == 'en_us':
                raise KeyError(translation_key)
            return psi.tr(
                translation_key, *args, _mcdr_tr_language='en_us',
                language='en_us', allow_failure=False, **kwargs
            )
        except (KeyError, ValueError):
            languages = []
            for item in (_mcdr_tr_language, fallback_language, 'en_us'):
                if item not in languages:
                    languages.append(item)
            languages = ', '.join(languages)
            if allow_failure:
                if log_error_message:
                    psi.logger.error(f'Error translate text "{translation_key}" to language {languages}')
                if _default_fallback is None:
                    return translation_key
                return _default_fallback
            else:
                raise KeyError(f'Translation key "{translation_key}" not found with language {languages}')


def ktr(
        translation_key: str, *args, default_fallback: Optional[MessageText] = None,
        log_error_message: bool = False, prefix: str = TRANSLATION_KEY_PREFIX, **kwargs
) -> RTextMCDRTranslation:
    actual_translation_key = translation_key
    if not translation_key.startswith(prefix):
        actual_translation_key = f"{prefix}{translation_key}"
    return RTextMCDRTranslation(
        actual_translation_key, *args, log_error_message=log_error_message,
        default_fallback=translation_key if default_fallback is None else default_fallback, **kwargs
    ).set_translator(ntr)


def dtr(translation_dict: Dict[str, str], *args, **kwargs) -> RTextMCDRTranslation:
    def fake_tr(
            translation_key: str,
            *inner_args,
            language: Optional[str] = None,
            _mcdr_tr_language: Optional[str] = None,
            allow_failure: bool = True,
            **inner_kwargs
    ) -> MessageText:
        if language is not None and _mcdr_tr_language is None:
            _mcdr_tr_language = language
        result = translation_dict.get(language)
        fallback_language = [psi.get_mcdr_language()]
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
