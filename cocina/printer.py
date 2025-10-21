"""

Cocina Printer Module

This module provides the Printer class for handling structured output and logging
with timestamps, dividers, and file output capabilities.

License: BSd 3-clause

"""
#
# IMPORTS
#
import re
from pathlib import Path
from typing import Any, Literal, List, Optional, Tuple, Union
from cocina.utils import Timer, safe_join, write, singleton, caller_name
from cocina.constants import (
    ICON_START, ICON_SUCCESS, ICON_FAILED, cocina_CLI_DEFAULT_HEADER,
    cocina_log_path_key
)


#
# CONSTANTS
#
LOG_FILE_EXT: str = 'log'
ERROR_HEADER: str = 'Error'


#
# PUBLIC
#
@singleton
class Printer(object):
    """Structured output and logging class with timestamps and file output.

    Handles formatted printing with headers, timestamps, dividers, and optional
    file logging. Supports timing operations and structured message formatting.
    """
    def __init__(self,
            log_dir: Optional[str] = None,
            log_name_part: Optional[str] = None,
            log_path: Optional[str] = None,
            timer: Optional[Timer] = None,
            basename: Optional[str] = None,
            div_len: int = 100,
            icons: bool = True,
            silent: bool = False,
            start_message: Optional[str] = 'start',
            start_div: Union[str, Tuple[str, str]] = ('=','-'),
            start_vspace: int = 2,
            start_icon: Optional[str] = ICON_START) -> None:
        """Initialize Printer with configuration options.

        Args:
            basename: string to prefix header in messages
            log_dir: Directory path for log file output (optional)
            log_name_part: Part of the log filename to use
            timer: Timer instance for timestamps (creates new if None)
            div_len: Length of divider lines (default: 100)
            icons: Whether to display icons in messages (default: True)
            silent: Whether to suppress console output (default: False)
            start_message: Optional start message to display (default: 'start')
            start_div: Divider characters as string or tuple (default: ('=','-'))
            start_vspace: Vertical spacing before message (default: 2)
            start_icon: icon for start message (None will not include icon)
        Raises:
            ValueError: If header is not a string or list of strings

        Usage:
            >>> printer = Printer(header='MyApp', log_dir='/logs')
            >>> printer = Printer(['Module', 'SubModule'], silent=True)
        """
        self.log_dir = log_dir
        self.log_name_part = log_name_part
        self.log_path = log_path
        self.timer = timer or Timer()
        self.div_len = div_len
        self.icons = icons
        self.silent = silent
        self.basename = basename
        self.timer.start()
        self._process_log_path()
        if start_message:
            self.message(start_message, div=start_div, vspace=start_vspace, icon=start_icon)
        self._initialized = True

    def stop(self,
            message: str = 'complete',
            div: Union[str, Tuple[str, str]] = ('-','='),
            vspace: int = 1,
            error: Union[bool, str, Exception] = False,
             **kwargs: Any) -> str:
        """Stop the printer session and return timing information.

        Args:
            message: Completion message to display (default: 'complete')
            div: Divider characters as string or tuple (default: ('-','='))
            vspace: Vertical spacing before message (default: 1)
            error: Error indicator - False for none, string for custom message, Exception for error object
            **kwargs: Additional keyword arguments passed to message formatting

        Returns:
            Time when stop was called

        Usage:
            >>> stop_time = printer.stop('Processing complete')
            >>> printer.stop('Done', div='#')
        """
        time_stop = self.timer.stop()
        duration = self.timer.delta()
        kwargs['duration'] = duration
        if self.log_path:
            kwargs['log'] = self.log_path
        self.message(
            message,
            div=div,
            vspace=vspace,
            icon=ICON_SUCCESS,
            error=error,
            **kwargs)
        return time_stop

    def message(self,
            msg: str,
            header: Optional[Union[str, Literal[False]]] = None,
            div: Optional[Union[str, Tuple[str, str]]] = None,
            vspace: Union[bool, int] = False,
            icon: Optional[str] = None,
            error: Union[bool, str, Exception] = False,
            callout: bool = False,
            callout_div: str = '*',
            **kwargs: Any) -> None:
        """Print a formatted message with optional dividers and spacing.

        Args:
            msg: Main message content
            header:
                - if None: prefix message with name of module where .message is being called
                - if False: do not prefix message
                - else: prefix message with <header>
            div: Divider characters as string or tuple (optional)
            vspace: Vertical spacing as boolean or number of lines
            icon: Optional icon string to display with message
            error: Error indicator - False for none, string for custom message, Exception for error object
            callout: if callout, wrap message in lines and 2 vertical spaces
            callout_div: character to create wrapping lines
            **kwargs: Additional key-value pairs to append to message

        Usage:
            >>> printer.message('Status update')
            >>> printer.message('Error', 'processing', div='*', vspace=2)
            >>> printer.message('Info', count=42, status='ok')
        """
        if callout:
            self.vspace(2)
            self.line(callout_div)
        self.vspace(vspace)
        if div:
            if isinstance(div, str):
                div1, div2 = div, div
            else:
                div1, div2 = div
            self.line(div1)
        if error:
            error_msg = f'{ERROR_HEADER}:'
            if msg:
                error_msg = f'{error_msg} {msg}'
            if error:
                error_msg = f'{error_msg} [{error}]'
            icon = ICON_FAILED
            msg = error_msg
        if icon and self.icons:
            msg = f'{icon} {msg}'
        self._print(self._format_msg(msg, header, kwargs))
        if div:
            self.line(div2)
        if callout:
            self.line(callout_div)
            self.vspace(2)

    def callout(self,
            msg: str,
            header: Optional[Union[str, Literal[False]]] = None,
            div: Optional[Union[str, Tuple[str, str]]] = None,
            callout_div: str = '*',
            **kwargs: Any) -> None:
        """Convenience wrapper for displaying "callout" messages.

        Makes it easy to see messages in logs by using lines & spacing.
        Mainly for debuging and development

        Args:
            msg: Main message content
            header:
                - if None: prefix message with name of module where .message is being called
                - if False: do not prefix message
                - else: prefix message with <header>
            div: Divider characters as string or tuple (optional)
            **kwargs: Additional key-value pairs to append to message

        Usage:
            >>> printer.message('Status update')
            >>> printer.message('Error', 'processing', div='*', vspace=2)
            >>> printer.message('Info', count=42, status='ok')
        """
        self.message(self,
            msg,
            header=header,
            div=div,
            callout=True,
            callout_div=callout_div,
            **kwargs)

    def error(self,
            error: Union[bool, str, Exception],
            msg: Optional[str] = None,
            div: Optional[Union[str, Tuple[str, str]]] = None,
            vspace: Union[bool, int] = False,
            icon: Optional[str] = None,
            **kwargs: Any) -> None:
        """Convenience wrapper for displaying error messages.

        Displays an error message with optional formatting. If no message is provided,
        uses the default error message. This method wraps the main message() method
        with error-specific styling.

        Args:
            error: Error condition (bool, string, or Exception)
            msg: Optional error message text
            div: Optional divider formatting
            vspace: Vertical spacing (bool or int)
            icon: Optional icon for the message
            **kwargs: Additional arguments passed to message()

        Usage:
            ```python
            printer = Printer()
            printer.error(True, "Connection failed")
            printer.error(ConnectionError("Timeout"), div="=")
            ```
        """
        self.message(
            msg=msg,
            error=error,
            div=div,
            vspace=vspace,
            icon=icon,
            **kwargs)

    def vspace(self, vspace: Union[Literal[True], int] = True) -> None:
        """Print vertical spacing (blank lines).

        Args:
            vspace: Number of blank lines to print, or False for none

        Usage:
            >>> printer.vspace(2)    # Print 2 blank lines
            >>> printer.vspace(True) # Print 1 blank line
            >>> printer.vspace(False) # Print no blank lines
        """
        if vspace:
            self._print('\n' * int(vspace))

    def line(self, marker: str = '-', length: Optional[int] = None) -> None:
        """Print a horizontal line using repeated marker characters.

        Args:
            marker: Character to repeat for the line (default: '-')
            length: Length of line, uses div_len if None

        Usage:
            >>> printer.line()          # Print line of dashes
            >>> printer.line('=', 50)   # Print line of equals, 50 chars
            >>> printer.line('*')       # Print line of asterisks
        """
        if marker is not None:
            self._print(marker * (length or self.div_len))

    #
    # INTERNAL
    #
    def _process_log_path(self) -> None:
        """Process and set up the log file path for output.

        Determines log file path from environment variables or configuration,
        creates necessary directories, and sets up file logging.

        Usage:
            Internal method called during initialization to configure logging.
        """
        _append = False
        if self.log_path:
            _p =  Path(self.log_path)
            self.log_name = _p.name
            self.log_name_part = _p.stem.split('.')[-1]
            self.log_dir = str(_p.parent)
        elif self.log_dir:
            self.log_name = safe_join(self.timer.timestamp(), self.log_name_part, ext=LOG_FILE_EXT, sep='.')
            self.log_path = safe_join(self.log_dir, self.log_name)
        else:
            self.log_name = None
            self.log_path = None
            self.log_name_part = None
        if self.log_path:
            Path(self.log_path).parent.mkdir(parents=True, exist_ok=True)

    def _format_msg(self, message: str, header: Optional[Union[str, Literal[False]]], key_values: Optional[dict] = None) -> str:
        """Format message with header, timestamp, and key-value pairs.

        Args:
            message: Main message content
            header:
                - if None: prefix message with name of module where .message is being called
                - if False: do not prefix message
                - else: prefix message with <header>
            key_values: Optional dictionary of key-value pairs to append

        Returns:
            Formatted message string with header and timestamp
        """
        if self.timer.initiated:
            timer_part = f'[{self.timer.timestamp()} ({self.timer.state()})] '
        else:
            timer_part = ''
        if header is None:
            header = caller_name()
        header = safe_join(self.basename, header, sep='.')
        if header:
            header = f'{header}: '
        msg = safe_join(timer_part, header, message, sep='')
        if key_values:
            for k,v in key_values.items():
                msg += f'\n\t- {k}: {v}'
        return msg


    def _print(self, message: str) -> None:
        """Print message to console and optionally write to log file.

        Args:
            message: Message string to print and/or log
        """
        if not self.silent:
            print(message)
        if self.log_path:
            write(self.log_path, message, mode='a')
