import functools
import inspect
import warnings


def redirect_warnings(logger, keep_filter=False):
    """Redirect all messages from the `warnings` module to a `Logger`"""
    if not keep_filter:
        warnings.simplefilter('always')

    _old_showwarning = warnings.showwarning

    @functools.wraps(warnings.showwarning)
    def showwarning(message, category, filename, lineno, file=None, line=None):
        if file is not None:
            _old_showwarning(message, category, filename, lineno, file, line)
            return

        module = inspect.getmodule(None, filename)
        if module:
            filename = module.__name__
        message = f'{category.__name__}({filename}:{lineno}): {message}'
        if category is DeprecationWarning:
            logger.deprecation_warning(message, stacklevel=1)
        else:
            logger.warning(message)

    warnings.showwarning = showwarning


def _wrap_download_retcode(ydl, logger):
    _old_error = logger.error

    @functools.wraps(logger.error)
    def error_wrapper(*args, **kwargs):
        result = _old_error(*args, **kwargs)
        if result is not None:
            ydl._download_retcode = result

    logger.error = error_wrapper
