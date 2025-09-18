"""

Project Kit Printer Module

This module provides the Printer class for handling structured output and logging
with timestamps, dividers, and file output capabilities.

License: CC-BY-4.0

"""
#
# IMPORTS
#
from pathlib import Path
from typing import Any, List, Optional, Tuple, Union
from project_kit import utils
from project_kit import constants as c

#
# CONSTANTS
#
LOG_FILE_EXT: str = 'log'

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
                 timer: Optional[utils.Timer] = None,
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
            FIX ME: icons: bool = True,
            silent: Whether to suppress console output (default: False)

        Raises:
            ValueError: If header is not a string or list of strings

        Usage:
            >>> printer = Printer(header='MyApp', log_dir='/logs')
            >>> printer = Printer(['Module', 'SubModule'], silent=True)
        """
        self.log_dir = log_dir
        self.log_name_part = log_name_part
        self.timer = timer or utils.Timer()
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
        if self.log_dir:
            self.log_path = utils.safe_join(
                self.log_dir,
                self.timer.timestamp(),
                self.log_name_part,
                ext=LOG_FILE_EXT)
            if Path(self.log_path).is_file():
                err = (
                    'log already exists at log_path'
                    f'({self.log_path})'
                )
                raise ValueError(err)
            else:
                Path(self.log_path).parent.mkdir(parents=True, exist_ok=True)
        else:
            self.log_path = None
        self.message(message, div=div, vspace=vspace, icon=c.ICON_START)

    def stop(self,
             message: str = 'complete',
             div: Union[str, Tuple[str, str]] = ('-','='),
             vspace: int = 1,
             **kwargs: Any) -> str:
        """Stop the printer session and return timing information.

        Args:
            message: Completion message to display (default: 'complete')
            div: Divider characters as string or tuple (default: ('-','='))
            vspace: Vertical spacing before message (default: 1)
            **kwargs: Additional keyword arguments passed to message formatting

        Returns:
            Time when stop was called

        Usage:
            >>> stop_time = printer.stop('Processing complete')
            >>> printer.stop('Done', div='#')
        """
        time_stop = self.timer.stop()
        duration = self.timer.delta()
        info = dict(duration=duration)
        if self.log_path:
            info['log'] = self.log_path
        self.message(
            message,
            div=div,
            vspace=vspace,
            icon=c.ICON_SUCCESS,
            **info)
        return time_stop

    def message(self,
            msg: str,
            *subheader: str,
            div: Optional[Union[str, Tuple[str, str]]] = None,
            vspace: Union[bool, int] = False,
            icon: Optional[str] = None,
            error: Union[bool, str, Exception] = False,
            **kwargs: Any) -> None:
        """Print a formatted message with optional dividers and spacing.

        Args:
            msg: Main message content
            *subheader: Additional header components to append
            div: Divider characters as string or tuple (optional)
            vspace: Vertical spacing as boolean or number of lines
            FIX ME: icon: Optional[str] = None,
            FIX ME: error: Union[bool, str, Exception] = False,
            **kwargs: Additional key-value pairs to append to message

        Usage:
            >>> printer.message('Status update')
            >>> printer.message('Error', 'processing', div='*', vspace=2)
            >>> printer.message('Info', count=42, status='ok')
        """
        self.vspace(vspace)
        if div:
            if isinstance(div, str):
                div1, div2 = div, div
            else:
                div1, div2 = div
            self.line(div1)
        if error:
            if isinstance(error, (str, Exception)):
                msg = f'{msg}: {error}'
            icon = c.ICON_FAILED
        if icon and self.icons:
            msg = f'{icon} {msg}'
        self._print(self._format_msg(msg, subheader, kwargs))
        if div:
            self.line(div2)

    def set_header(self, header: Optional[str] = None):
        """ set header for messages:
        FIX ME:

        self.header = "job header"
        self.message("my message") ~> job header [timestamps]: my message


        self.header = ["job", "header"]
        self.message("my message") ~> job.header [timestamps]: my message
        """
        if header is None:
            header = c.PKIT_CLI_DEFAULT_HEADER
        if isinstance(header, str):
            self.header = header
        elif isinstance(header, list):
            self.header = utils.safe_join(*header, sep='.')
        else:
            raise ValueError('header must be str or list[str]', header)

    def vspace(self, vspace: Union[bool, int] = False) -> None:
        """
        FIX ME
        """
        if vspace:
            self._print('\n' * int(vspace))

    def line(self, marker: str, length: Optional[int] = None):
        """
        FIX ME
        """
        self._print(marker * (length or self.div_len))

    #
    # INTERNAL
    #
    def _format_msg(self, message: str, subheader: Tuple[str, ...], key_values: Optional[dict] = None) -> str:
        """Format message with header, timestamp, and key-value pairs.

        Args:
            message: Main message content
            subheader: Tuple of additional header components
            key_values: Optional dictionary of key-value pairs to append

        Returns:
            Formatted message string with header and timestamp
        """
        header = self.header
        if subheader:
            header = utils.safe_join(header, *subheader, sep='.')
        msg = (
            f'{header} '
            f'[{self.timer.timestamp()} ({self.timer.state()})]: '
            f'{message}'
        )
        if key_values:
            for k,v in key_values.items():
                msg += f'\n- {k}: {v}'
        return msg


    def _print(self, message: str) -> None:
        """Print message to console and optionally write to log file.

        Args:
            message: Message string to print and/or log
        """
        if not self.silent:
            print(message)
        if self.log_path:
            utils.write(self.log_path, message, mode='a')
