"""

Project Kit Utilities

This module contains utility functions and classes for the Project Kit package,
including file system operations, YAML handling, and timing functionality.

License: CC-BY-4.0

"""
#
# IMPORTS
#
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Optional
import yaml


#
# CONSTANTS
#
MAX_DIR_SEARCH_DEPTH: int = 6
TIME_FORMAT: str = '%H:%M:%S'
DATE_TIME_FORMAT: str = '%Y.%m.%d %H:%M:%S'
TIME_STAMP_FORMAT: str = '%Y%m%d-%H%M%S'


#
# PUBLIC
#
def dir_search(
        *search_names: str,
        max_depth: int = MAX_DIR_SEARCH_DEPTH,
        default: Optional[str] = None) -> str:
    """Search parent directories for files matching search names.

    Args:
        *search_names: File names to search for
        max_depth: Maximum directory depth to search (default: MAX_DIR_SEARCH_DEPTH)
        default: Default return value if files not found (default: None)

    Returns:
        Path to directory containing matching files

    Raises:
        ValueError: If files not found and no default provided
    """
    cwd = Path.cwd()
    directory = cwd
    for _ in range(max_depth):
        file_names = [str(n.name) for n in directory.iterdir()]
        if bool(set(file_names) & set(search_names)):
            return str(directory)
        else:
            directory = directory.parent
    if default:
        return default
    else:
        raise ValueError(f'{search_names} file(s) not found at depth {max_depth}')


def read_yaml(path: str, *key_path: str, safe: bool = False) -> Any:
    """Read and optionally extract part of a YAML file.

    # TODO: READ_YAML check for ext?

    Usage:
        ```python
        data = read_yaml(path)
        data_with_key_path = read_yaml(path, 'a', 'b', 'c')
        data['a']['b']['c'] == data_with_key_path  # ==> True
        ```

    Args:
        path: Path to YAML file
        *key_path: Key path to extract from loaded data
        safe: If True, return empty dict when path not found; otherwise raise error

    Returns:
        Dictionary or extracted data from YAML file

    Raises:
        ValueError: If path does not exist and safe=False
    """
    if Path(path).is_file():
        with open(path, 'rb') as file:
            obj = yaml.safe_load(file)
        for k in key_path:
            obj = obj[k]
        return obj
    elif safe:
        return dict()
    else:
        raise ValueError(f'{path} does not exist')

#
# CORE
#
def replace_dictionary_values(value: Any, update_dict: dict) -> dict:
    """
    replace any values in value-dictionary
    that are keys in update_dict
    """
    if isinstance(value, dict):
        return {k: replace_dictionary_values(v, update_dict) for k, v in value.items()}
    elif isinstance(value, list):
        return [replace_dictionary_values(v, update_dict) for v in value]
    elif isinstance(value, str):
        return update_dict.get(value, value)
    else:
        return value

def safe_join(*parts, sep='/', ext=None):
    """
    join together non-null values
    add possible ext
    """
    parts = [str(v) for v in parts if v]
    result = sep.join(parts)
    if ext:
        ext = re.sub(r'^\.', '', ext)
        result = f'{result}.{ext}'
    return result



#
# DATES AND TIMES
#
class Timer:
    """Simple timer class for measuring elapsed time.

    Usage:
        ```python
        timer = Timer()
        print('Timer starting at:', timer.start())
        print('Start-time as timestamp:', timer.timestamp())
        ...
        print('Current duration:', timer.state())
        ...
        timer.start_lap()
        ...
        print('Duration since start_lap called:', timer.stop_lap())
        ...
        print('Timer stops at:', timer.stop())
        print('Duration that timer ran:', timer.delta())
        ```

    Args:
        fmt: Format string for datetime display (default: DATE_TIME_FORMAT)
        ts_fmt: Format string for timestamp display (default: TIME_STAMP_FORMAT)
    """
    def __init__(self, fmt: str = DATE_TIME_FORMAT, ts_fmt: str = TIME_STAMP_FORMAT) -> None:
        self.fmt = fmt
        self.ts_fmt = ts_fmt
        self.start_datetime = None
        self.end_datetime = None
        self.lap_start = None
        self.lap_duration = None

    def start(self) -> Optional[str]:
        """Start the timer and return formatted start time."""
        if not self.start_datetime:
            self.start_datetime = datetime.now()
            return self.start_datetime.strftime(self.fmt)
        return None

    def start_lap(self) -> None:
        """Start a lap timer."""
        self.lap_start = datetime.now()

    def stop_lap(self):
        """Stop lap timer and return lap duration."""
        if self.lap_start:
            self.lap_duration = datetime.now() - self.lap_start
            self.lap_start = None
            return self.lap_duration
        return None

    def timestamp(self) -> Optional[str]:
        """Return start time as formatted timestamp."""
        if self.start_datetime:
            return self.start_datetime.strftime(self.ts_fmt)
        return None

    def state(self) -> Optional[str]:
        """Return current elapsed time as string."""
        if self.start_datetime:
            return str(datetime.now() - self.start_datetime)
        return None

    def stop(self) -> str:
        """Stop the timer and return formatted stop time."""
        if not self.end_datetime:
            self.end_datetime = datetime.now()
        return self.end_datetime.strftime(self.fmt)

    def delta(self) -> Optional[str]:
        """Return total elapsed time as string."""
        if self.start_datetime and self.end_datetime:
            return str(self.end_datetime - self.start_datetime)
        return None

    def now(self, fmt: str = 'time') -> str:
        """Return current time in specified format.

        Args:
            fmt: Format type - 'time'/'t' for datetime format, 'timestamp'/'ts' for timestamp format

        Returns:
            Formatted current time string
        """
        if fmt in ['t', 'time']:
            fmt = self.fmt
        elif fmt in ['ts', 'timestamp']:
            fmt = self.ts_fmt
        return datetime.now().strftime(fmt)