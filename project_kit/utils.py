from pathlib import Path
from typing import Any, Optional
import yaml


#
# CONFIG
#
MAX_DIR_SEARCH_DEPTH: int = 6
TIME_FORMAT='%H:%M:%S'
DATE_TIME_FORMAT='%Y.%m.%d %H:%M:%S'
TIME_STAMP_FORMAT='%Y%m%d-%H%M%S'


#
# FILE HELPERS
#
def dir_search(
        *search_names: str,
        max_depth: int = MAX_DIR_SEARCH_DEPTH,
        default: Optional[str] = None):
    """ search parent directories for file in search names


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


#
# IO
#
def read_yaml(path: str, *key_path: str, safe: bool = False) -> Any:
    """ Reads (and optionally extracts part of) yaml file

    Usage:

    ```python
    data = read_yaml(path)
    data_with_key_path = read_yaml(path,'a','b','c')
    data['a']['b']['c'] == data_with_key_path # ==> True
    ```

    Args:

        path (str): path to yaml file
        *key_path (*str): key-path to extract
        safe (bool = False):
        	if path is not found and safe: return empty-dict
        	otherwise: raise error

    Returns:

        dictionary, or data extracted, from yaml file
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
# DATES AND TIME
#
class Timer(object):
    """ Timer: a super simple python timer

    Usage:

        timer=Timer()
        print('Timer starting at:',timer.start())
        print('start-time as timestamp:',timer.timestamp())
        ...
        print('current duration:',timer.state())
        ...
        timer.start_lap()
        ...
        print('duration since "start_lap" called:',timer.stop_lap()())
        ...
        print('Timer stops at:',timer.stop())
        print('Duration that timer ran:',timer.delta())

    """
    def __init__(self,fmt=DATE_TIME_FORMAT,ts_fmt=TIME_STAMP_FORMAT):
        self.fmt=fmt
        self.ts_fmt=ts_fmt
        self.start_datetime=None
        self.end_datetime=None
    def start(self):
        if not self.start_datetime:
            self.start_datetime=datetime.now()
            return self.start_datetime.strftime(self.fmt)
    def start_lap(self):
        self.lap_start = datetime.now()
    def stop_lap(self):
        self.lap_duration = datetime.now() - self.lap_start
        self.lap_start = None
        return self.lap_duration
    def timestamp(self):
        if self.start_datetime:
            return self.start_datetime.strftime(self.ts_fmt)
    def state(self):
        if self.start_datetime:
            return str(datetime.now()-self.start_datetime)
    def stop(self):
        if not self.end_datetime:
            self.end_datetime=datetime.now()
        return self.end_datetime.strftime(self.fmt)
    def delta(self):
        return str(self.end_datetime-self.start_datetime)
    def now(self,fmt='time'):
        if fmt in ['t','time']:
            fmt=self.fmt
        elif fmt in ['ts','timestamp']:
            fmt=self.ts_fmt
        return datetime.now().strftime(fmt)