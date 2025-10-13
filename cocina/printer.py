"""

Cocina Printer Module

This module provides the Printer class for handling structured output and logging
with timestamps, dividers, and file output capabilities.

License: BSd 3-clause

"""
#
# IMPORTS
#
import os
import re
from pathlib import Path
from typing import Any, Literal, List, Optional, Tuple, Union
from cocina.utils import Timer, safe_join, write
from cocina.constants import (
    ICON_START, ICON_SUCCESS, ICON_FAILED, cocina_CLI_DEFAULT_HEADER,
    cocina_log_path_key
)


#
# CONSTANTS
#
LOG_FILE_EXT: str = 'log'
DEFAULT_ERROR_MSG: str = 'Error'


#
# PUBLIC
#
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
                 header: Optional[Union[str, List[str]]] = None,
                 div_len: int = 100,
                 icons: bool = True,
                 silent: bool = False) -> None:
        """Initialize Printer with configuration options.

        Args:
            header: String or list of strings for the message header prefix
            log_dir: Directory path for log file output (optional)
            log_name_part: Part of the log filename to use
            timer: Timer instance for timestamps (creates new if None)
            div_len: Length of divider lines (default: 100)
            icons: Whether to display icons in messages (default: True)
            silent: Whether to suppress console output (default: False)

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
        self.set_header(header)

    def start(self,
              message: str = 'start',
              div: Union[str, Tuple[str, str]] = ('=','-'),
              vspace: int = 2,
              **kwargs: Any) -> None:
        """Start the printer session with timing and optional log file creation.

        Args:
            message: Start message to display (default: 'start')
            div: Divider characters as string or tuple (default: ('=','-'))
            vspace: Vertical spacing before message (default: 2)
            **kwargs: Additional keyword arguments passed to message formatting

        Raises:
            ValueError: If log file already exists at the target path

        Usage:
            >>> printer.start('Processing begins')
            >>> printer.start('Init', div='*', vspace=1)
        """
        self.timer.start()
        self._process_log_path()
        self.message(message, div=div, vspace=vspace, icon=ICON_START)

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
            *subheader: str,
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
            *subheader: Additional header components to append
            div: Divider characters as string or tuple (optional)
            vspace: Vertical spacing as boolean or number of lines
            icon: Optional icon string to display with message
            error: Error indicator - False for none, string for custom message, Exception for error object
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
            if error is not False:
                msg = f'{msg}: {error}'
            icon = ICON_FAILED
        if icon and self.icons:
            msg = f'{icon} {msg}'
        self._print(self._format_msg(msg, subheader, kwargs))
        if div:
            self.line(div2)
        if callout:
            self.line(callout_div)
            self.vspace(2)

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
        if msg is None:
            msg = DEFAULT_ERROR_MSG
        self.message(
            msg=msg,
            error=error,
            div=div,
            vspace=vspace,
            icon=icon,
            **kwargs)

    def set_header(self, header: Optional[Union[str, List[str]]] = None) -> None:
        """Set header for messages.

        Args:
            header: String or list of strings for message prefix

        Usage:
            >>> printer.set_header("job header")
            >>> printer.message("my message")  # job header [timestamp]: my message
            >>> printer.set_header(["job", "header"])
            >>> printer.message("my message")  # job.header [timestamp]: my message
        """
        if header is None:
            header = cocina_CLI_DEFAULT_HEADER
        if isinstance(header, (str, list)):
            if isinstance(header, list):
                header = safe_join(*header, sep='.')
            self.header = re.sub(r'/$', '', header)
        else:
            raise ValueError('header must be str or list[str]', header)

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
        if not self.log_path:
            env_log_path = os.environ.get(cocina_log_path_key)
            if env_log_path:
                self.log_path = env_log_path
                _append = True
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
            if (not _append) and Path(self.log_path).is_file():
                err = (
                    'log already exists at log_path'
                    f'({self.log_path})'
                )
                raise ValueError(err)
            else:
                os.environ[cocina_log_path_key] = self.log_path
                Path(self.log_path).parent.mkdir(parents=True, exist_ok=True)


    def _format_msg(self, message: str, subheader: Tuple[str, ...], key_values: Optional[dict] = None) -> str:
        """Format message with header, timestamp, and key-value pairs.

        Args:
            message: Main message content
            subheader: Tuple of additional header components
            key_values: Optional dictionary of key-value pairs to append

        Returns:
            Formatted message string with header and timestamp
        """
        if self.timer.initiated:
            timer_part = f'[{self.timer.timestamp()} ({self.timer.state()})] '
        else:
            timer_part = ''
        header = self.header
        if subheader:
            header = safe_join(header, *subheader, sep='.')
        msg = safe_join(timer_part, header, ': ', message, sep='')
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
