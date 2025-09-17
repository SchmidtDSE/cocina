from pathlib import Path
from project_kit import utils

LOG_FILE_EXT = 'log'

class Printer(object):

	def __init__(self,
			header=None,
			log_dir=None,
			log_name_part=None,
			timer=None,
			div_len=100,
			silent=False):
		self.log_dir = log_dir
		self.timer = timer or utils.Timer()
		self.div_len = div_len
		self.silent = silent
		self.log_name_part = log_name_part
		print('-----', self.log_name_part)
		if isinstance(header, str):
			self.header = header
		elif isinstance(header, list):
			self.header = utils.safe_join(*header, sep='.')
		else:
			raise ValueError('header must be str or list[str]', header)

	def start(self,
			message='start',
			div=('=','-'),
			vspace=2,
			**kwargs):
		self.timer.start()
		if self.log_dir:
			self.log_path = utils.safe_join(
				self.log_dir,
				self.timer.timestamp(),
				self.log_name_part,
				ext=LOG_FILE_EXT)
			print()
			print(self.log_name_part, '<<<')
			print(self.log_path)
			print()
			print()
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
		self.message(message, div=div, vspace=vspace)

	def stop(self,
			message='complete',
			div=('-','='),
			vspace=1,
			**kwargs):
		time_stop = self.timer.stop()
		duration = self.timer.delta()
		info = dict(duration=duration)
		if self.log_path:
			info['log'] = self.log_path
		self.message(
			message,
			div=div,
			vspace=vspace,
			**info)

	def message(self, msg, *subheader, div=None, vspace=False, **kwargs):
		if vspace:
			self._print('\n' * vspace)
		if div:
			if isinstance(div, str):
				div1, div2 = div, div
			else:
				div1, div2 = div
			self._print(div1 * self.div_len)
		self._print(self._format_msg(msg, subheader, kwargs))
		if div:
			self._print(div2 * self.div_len)

	#
	# INTERNAL
	#
	def _format_msg(self, message, subheader, key_values=None):
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


	def _print(self, message):
		if not self.silent:
			print(message)
		if self.log_path:
			utils.write(self.log_path, message, mode='a')
