"""

Cocina Utilities

This module contains utility functions and classes for the Cocina package,
including file system operations, YAML handling, and timing functionality.

License: BSd 3-clause

"""
#
# IMPORTS
#
import sys
import importlib.util
import re
import inspect
import yaml
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, List, Optional, Union
from types import ModuleType
from cocina.constants import cocina_NOT_FOUND, KEY_STR_REGEX


#
# CONSTANTS
#
MAX_DIR_SEARCH_DEPTH: int = 6
TIME_FORMAT: str = '%H:%M:%S'
DATE_TIME_FORMAT: str = '%Y.%m.%d %H:%M:%S'
TIME_STAMP_FORMAT: str = '%Y%m%d-%H%M%S'


#
# IO
#
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


def safe_copy_yaml(
        src: str,
        dest: str,
        force: bool = False,
        **replacements: Any) -> None:
    """Copy yaml files with replacement while preserving comments

    Args:
        src (str): path to source yaml file
        dest (str): destination path for processed yaml file
        force (bool = False): if <dest>-file exists:
            - if <force> overwrite file
            - otherwise raise error
        **replacements (str): key-value pairs to replace value in
            src-yaml-file. if

    Raises:
        ValueError: if <dest> exists and <force> is false

    """
    file_exists = Path(dest).is_file()
    if file_exists and (not force):
        err = f'destination ({dest}) exists. use `force=True` to overwrite file'
        raise ValueError(err)
    else:
        with open(src, "r") as file:
            processed_str = ''
            for line in file:
                for k, v in replacements.items():
                    if (v != cocina_NOT_FOUND) and re.search(f'^{k}', line):
                        line = f'{k}: {json.dumps(v)}'
                    else:
                        line = line.strip()
                processed_str += line + '\n'
        with open(dest, 'w') as file:
            file.write(processed_str)


def write(dest: str, *lines: str, mode='w', strip=True, **kwargs) -> None:
    """Write multiple lines to a file.

    Args:
        dest: Destination file path to write to
        *lines: Variable number of lines to write to the file
        mode: File open mode (default: 'w' for write)
        strip: Whether to strip whitespace from lines (default: True)
        **kwargs: Additional keyword arguments (currently unused)

    Usage:
        >>> write('output.txt', 'Line 1', 'Line 2', 'Line 3')
        >>> write('append.txt', 'New line', mode='a')
    """
    with open(dest, mode) as file:
        for line in lines:
            line = str(line)
            if strip:
                line = line.strip()
            file.write(f'\n{line}')


def import_module_from_path(path: str) -> ModuleType:
    """Import a module from file path.

    Args:
        path: Path to the Python module file to import

    Returns:
        Imported module object
    """
    spec = importlib.util.spec_from_file_location("module.name", path)
    module = importlib.util.module_from_spec(spec)
    sys.modules["module.name"] = module
    spec.loader.exec_module(module)
    return module


#
# INSPECTION
#
def nb_objects(path) -> int:
    """Count the number of objects (files and directories) in a path.

    Args:
        path: Directory path to count objects in

    Returns:
        Number of files and directories in the given path

    Usage:
        ```python
        count = nb_objects('/path/to/directory')
        print(f'Found {count} objects')
        ```
    """
    return len(list(Path(path).glob('*')))


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


def inspect_tree(max_depth: int = 4, sep: str = '.', as_list: bool = False) -> Union[List[str], str]:
    """Inspect the call stack and return function names up to max_depth.

    Args:
        max_depth: Maximum depth of call stack to inspect (default: 4)
        sep: Separator to join function names when returning string (default: '.')
        as_list: Whether to return as list of names or joined string (default: False)

    Returns:
        List of function names if as_list=True, otherwise joined string with separator

    Usage:
        >>> inspect_tree()  # Returns 'caller1.caller2.caller3'
        >>> inspect_tree(as_list=True)  # Returns ['caller1', 'caller2', 'caller3']
        >>> inspect_tree(sep='/')  # Returns 'caller1/caller2/caller3'
    """
    frames = inspect.stack()[1:max_depth+1]
    names = []
    for frame in frames:
        name = frame.function
        if name[0] == '<':
            break
        else:
            names.append(name)
    if as_list:
        return names
    else:
        return safe_join(*names, sep=sep)

#
# CORE
#
def replace_dictionary_values(value: Any, update_dict: dict) -> Any:
    """Replace any values in value-dictionary that are keys in update_dict.

    Recursively traverses dictionaries and lists, replacing string values
    that match keys in update_dict with corresponding values.

    Args:
        value: Dictionary, list, or other value to process
        update_dict: Dictionary containing replacement key-value pairs

    Returns:
        Processed value with replacements applied
    """
    if isinstance(value, dict):
        return {k: replace_dictionary_values(v, update_dict) for k, v in value.items()}
    elif isinstance(value, list):
        return [replace_dictionary_values(v, update_dict) for v in value]
    elif isinstance(value, str):
        return update_dict.get(value, value)
    else:
        return value


def keyed_replace_dictionary_values(
        value: dict,
        open_marker: str = '<<',
        close_marker: str = '>>',
        accepted_regex: str =  KEY_STR_REGEX,
        clean_path: bool =  True,
        **direct_replacements) -> dict:
    """Replace dictionary values using keyed markers and direct replacements.

    Recursively processes a dictionary to replace values containing marker patterns
    with corresponding values from the same dictionary. Also applies direct string
    replacements and optionally cleans up double slashes in paths.

    Args:
        value: Dictionary to process for value replacement
        open_marker: Opening marker pattern (default: '<<')
        close_marker: Closing marker pattern (default: '>>')
        accepted_regex: Regex pattern for valid keys (default: KEY_STR_REGEX)
        clean_path: Whether to clean double slashes in paths (default: True)
        **direct_replacements: Direct key-value string replacements to apply

    Returns:
        Dictionary with replaced values

    Usage:
        ```python
        config = {
            'host': 'localhost',
            'url': 'http://<<host>>/api'
        }
        result = keyed_replace_dictionary_values(config)
        # result['url'] becomes 'http://localhost/api'
        ```
    """
    regex = f'{open_marker}{accepted_regex}{close_marker}'
    value_str = json.dumps(value)
    markers = re.findall(regex, value_str)
    for m in markers:
        key = m.strip(open_marker).strip(close_marker)
        value_str = re.sub(m, value[key], value_str)
    for k, v in direct_replacements.items():
        value_str = re.sub(k, v or '', value_str)
    if clean_path:
        value_str = clean_path_string(value_str)
    return json.loads(value_str)


def clean_path_string(value: str) -> str:
    """
    Removes consecutive forward-slashes "/" from string,
    while preserving protocol delimiters

    Args:
        value: string to be cleaned

    Returns:
        string stripped of multiple slashes
    """
    value = re.sub(r'(://)/+', r'\1', value)
    return re.sub(r'(?<!:)//+', '/', value)


def safe_join(
        *parts,
        sep: str = '/',
        ext: Optional[str] = None,
        clean_path: bool =  True) -> str:
    """Join together non-null values with optional extension.

    Filters out None/empty values and joins remaining parts with separator.
    Optionally adds file extension.

    Args:
        *parts: Parts to join (None/empty values will be filtered out)
        sep: Separator to use for joining (default: '/')
        ext: Optional file extension to add (default: None)
        clean_path: Whether to clean double slashes in paths (default: True)

    Returns:
        Joined string with optional extension
    """
    parts = [str(v) for v in parts if v]
    result = sep.join(parts)
    if ext:
        ext = re.sub(r'^\.', '', ext)
        result = re.sub(f'\\.{ext}$', '', result)
        result = f'{result}.{ext}'
    if clean_path:
        result = clean_path_string(result)
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

    Properties:
        running (bool): Whether the timer is currently running
        initiated (bool): Whether the timer has been started at least once

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
        self.running = False
        self.initiated = False

    def start(self) -> Optional[str]:
        """Start the timer and return formatted start time."""
        self.running = True
        self.initiated = True
        if not self.start_datetime:
            self.start_datetime = datetime.now()
            return self.start_datetime.strftime(self.fmt)
        return None

    def start_lap(self) -> None:
        """Start a lap timer."""
        self.lap_start = datetime.now()

    def stop_lap(self) -> Optional[timedelta]:
        """Stop lap timer and return lap duration.

        Returns:
            Lap duration as timedelta object or None if no lap was started
        """
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
        """Stop the timer and return formatted stop time.

        Returns:
            Formatted stop time string
        """
        self.running = False
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