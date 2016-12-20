import sublime, sublime_plugin, re, os, subprocess, platform, ntpath, shlex

PLUGIN_DIR = os.getcwd() if int(sublime.version()) < 3000 else os.path.dirname(__file__)
SUBL_ASYNC = callable(getattr(sublime, 'set_timeout_async', None))
USE_SHELL = sublime.platform() == 'windows'
POPEN_ENV = ({'PATH': ':'.join(['/usr/local/bin', os.environ['PATH']])}) if sublime.platform() == 'osx' and os.path.isdir('/usr/local/bin') else None

if sublime.load_settings('Minify.sublime-settings').get('debug_mode'):
	print('Minify: Sublime Platform:' + str(sublime.platform()))
	print('Minify: Sublime Version:' + str(sublime.version()))
	print('Minify: Python Version:' + str(platform.python_version()))
	print('Minify: PLUGIN_DIR:' + str(PLUGIN_DIR))
	print('Minify: SUBL_ASYNC:' + str(SUBL_ASYNC))
	print('Minify: USE_SHELL:' + str(USE_SHELL))
	print('Minify: POPEN_ENV:' + str(POPEN_ENV))

class MinifyUtils():
	def fixStr(self, s):
		return s.encode('utf8') if (type(s).__name__ == 'unicode') else s

	def runProgram(self, cmd):
		if '>' in cmd:
			p = subprocess.Popen(cmd, stderr=subprocess.PIPE, shell=USE_SHELL, env=POPEN_ENV)
			output = p.communicate()[1]
		else:
			p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=USE_SHELL, env=POPEN_ENV)
			output = p.communicate()[0]
		return p.returncode, output

	def get_setting(self, key):
		settings = self.view.settings().get('Minify')
		if settings is None or settings.get(key) is None:
			settings = sublime.load_settings('Minify.sublime-settings')
		return settings.get(key)

if not SUBL_ASYNC:
	import threading

	class RunCmdInOtherThread(MinifyUtils, threading.Thread):
		def __init__(self, cmd):
			self.cmd = cmd
			self.retCode = 1
			self.output = ''
			threading.Thread.__init__(self)

		def run(self):
			self.retCode, self.output = self.runProgram(self.cmd)

class ThreadHandling(MinifyUtils):
	def handle_result(self, cmd, outfile, retCode, output):
		if retCode:
			if output:
				sublime.error_message(' '.join(cmd) + '\r\n\r\n' + output.decode('utf-8'))
		else:
			if self.get_setting('open_file'):
				sublime.active_window().open_file(outfile)

	def handle_thread(self, thread, outfile):
		if thread.is_alive():
			sublime.set_timeout(lambda: self.handle_thread(thread, outfile), 100)
		else:
			self.handle_result(thread.cmd, outfile, thread.retCode, thread.output)

	def run_cmd(self, cmd, outfile):
		if self.get_setting('debug_mode'):
			print('Minify: Output file:' + str(outfile))
			print('Minify: Command:' + str(cmd))
		if SUBL_ASYNC:
			retCode, output = self.runProgram(cmd)
			self.handle_result(cmd, outfile, retCode, output)
		else:
			thread = RunCmdInOtherThread(cmd)
			thread.start()
			sublime.set_timeout(lambda: self.handle_thread(thread, outfile), 100)

class PluginBase(ThreadHandling):
	def is_enabled(self):
		filename = self.view.file_name()
		return bool(type(filename).__name__ in ('str', 'unicode') and ((re.search(r'\.(?:css|js|json|html?|svg)$', filename)) or (re.search(r'(\.[^\.]+)$', filename) and re.search(r'/(?:CSS|JavaScript|JSON|HTML)\.tmLanguage$', self.view.settings().get('syntax')))))

	def run(self, edit):
		if SUBL_ASYNC:
			sublime.set_timeout_async(lambda: self.do_action(), 0)
		else:
			self.do_action()

class MinifyClass(MinifyUtils):
	def minify(self):
		inpfile = self.view.file_name()
		if type(inpfile).__name__ in ('str', 'unicode') and re.search(r'\.[^\.]+$', inpfile):
			if self.view.is_dirty() and self.get_setting('save_first'):
				self.view.run_command('save')
				if self.get_setting('auto_minify_on_save'):
					return
			outfile = re.sub(r'(\.[^\.]+)$', r'.min\1', inpfile, 1)
			syntax = self.view.settings().get('syntax')
			if self.get_setting('debug_mode'):
				print('Minify: Syntax: ' + str(syntax))
			if re.search(r'\.js$', inpfile) or re.search(r'/JavaScript\.tmLanguage$', syntax):
				cmd = shlex.split(self.fixStr(self.get_setting('uglifyjs_command') or 'uglifyjs'))
				cmd.extend([inpfile, '-o', outfile, '-m', '-c'])
				if self.get_setting('source_map'):
					head, tail = ntpath.split(outfile)
					mapfile = tail or ntpath.basename(head)
					cmd.extend(['--source-map', outfile + '.map', '--source-map-url', mapfile + '.map', '--source-map-root', './', '-p', 'relative'])
				if self.get_setting('keep_comments'):
					cmd.extend(['--comments'])
					eo = self.get_setting('comments_to_keep')
					if type(eo).__name__ in ('str', 'unicode'):
						cmd.extend([eo])
			elif re.search(r'\.json$', inpfile) or re.search(r'/JSON\.tmLanguage$', syntax):
				cmd = shlex.split(self.fixStr(self.get_setting('minjson_command') or 'minjson'))
				cmd.extend([inpfile, '-o', outfile])
			elif re.search(r'\.css$', inpfile) or re.search(r'/CSS\.tmLanguage$', syntax):
				minifier = self.get_setting('cssminifier') or 'clean-css'
				if minifier == 'uglifycss':
					cmd = shlex.split(self.fixStr(self.get_setting('uglifycss_command') or 'uglifycss'))
					eo = self.get_setting('uglifycss_options')
					if type(eo).__name__ in ('str', 'unicode'):
						cmd.extend(shlex.split(self.fixStr(eo)))
					cmd.extend([inpfile, '>', outfile])
				elif minifier == 'yui':
					cmd = shlex.split(self.fixStr(self.get_setting('java_command') or 'java'))
					yui_compressor = self.get_setting('yui_compressor') or 'yuicompressor-2.4.7.jar'
					cmd.extend(['-jar', PLUGIN_DIR + '/bin/' + str(yui_compressor), inpfile, '-o', outfile])
					eo = self.get_setting('yui_charset')
					if type(eo).__name__ in ('str', 'unicode'):
						cmd.extend(['--charset', eo])
					eo = self.get_setting('yui_line_break')
					if type(eo).__name__ in ('int', 'str', 'unicode'):
						cmd.extend(['--line-break', str(eo)])
				else:
					cmd = shlex.split(self.fixStr(self.get_setting('cleancss_command') or 'cleancss'))
					eo = self.get_setting('cleancss_options') or '--s0 -s --skip-rebase'
					if type(eo).__name__ in ('str', 'unicode'):
						cmd.extend(shlex.split(self.fixStr(eo)))
					if self.get_setting('css_source_map'):
						cmd.extend(['--source-map'])
					cmd.extend(['-o', outfile, inpfile])
			elif re.search(r'\.html?$', inpfile) or re.search(r'/HTML\.tmLanguage$', syntax):
				cmd = shlex.split(self.fixStr(self.get_setting('html-minifier_command') or 'html-minifier'))
				eo = self.get_setting('html-minifier_options') or '--collapse-boolean-attributes --collapse-whitespace --html5 --minify-css --minify-js --preserve-line-breaks --process-conditional-comments --remove-comments --remove-empty-attributes --remove-redundant-attributes --remove-script-type-attributes --remove-style-link-type-attributes'
				if type(eo).__name__ in ('str', 'unicode'):
					cmd.extend(shlex.split(self.fixStr(eo)))
				cmd.extend(['-o', outfile, inpfile])
			elif re.search(r'\.svg$', inpfile):
				cmd = shlex.split(self.fixStr(self.get_setting('svgo_command') or 'svgo'))
				eo = self.get_setting('svgo_min_options')
				if type(eo).__name__ in ('str', 'unicode'):
					cmd.extend(shlex.split(self.fixStr(eo)))
				cmd.extend([inpfile, outfile])
			else:
				cmd = False
			if cmd:
				print('Minify: Minifying file:' + str(inpfile))
				self.run_cmd(cmd, outfile)

class BeautifyClass(MinifyUtils):
	def beautify(self):
		inpfile = self.view.file_name()
		if type(inpfile).__name__ in ('str', 'unicode') and re.search(r'\.[^\.]+$', inpfile):
			if self.view.is_dirty() and self.get_setting('save_first'):
				self.view.run_command('save')
			outfile = re.sub(r'(?:\.min)?(\.[^\.]+)$', r'.beautified\1', inpfile, 1)
			syntax = self.view.settings().get('syntax')
			if re.search(r'\.js$', inpfile) or re.search(r'/JavaScript\.tmLanguage$', syntax):
				cmd = shlex.split(self.fixStr(self.get_setting('uglifyjs_command') or 'uglifyjs'))
				cmd.extend([inpfile, '-o', outfile, '--comments', 'all', '-b'])
				eo = self.get_setting('uglifyjs_pretty_options')
				if type(eo).__name__ in ('str', 'unicode'):
					cmd.extend(shlex.split(self.fixStr(eo)))
			elif re.search(r'\.json$', inpfile) or re.search(r'/JSON\.tmLanguage$', syntax):
				cmd = shlex.split(self.fixStr(self.get_setting('minjson_command') or 'minjson'))
				cmd.extend([inpfile, '-o', outfile, '-b'])
			elif re.search(r'\.css$', inpfile) or re.search(r'/CSS\.tmLanguage$', syntax):
				cmd = shlex.split(self.fixStr(self.get_setting('js-beautify_command') or 'js-beautify'))
				eo = self.get_setting('js-beautify_options')
				if type(eo).__name__ in ('str', 'unicode'):
					cmd.extend(shlex.split(self.fixStr(eo)))
				cmd.extend(['--css', '-o', outfile, inpfile])
			elif re.search(r'\.html?$', inpfile) or re.search(r'/HTML\.tmLanguage$', syntax):
				outfile = re.sub(r'(?:\.min)?(\.[^\.]+)$', r'.pretty\1', inpfile, 1)
				cmd = shlex.split(self.fixStr(self.get_setting('js-beautify_command') or 'js-beautify'))
				eo = self.get_setting('js-beautify_html_options')
				if type(eo).__name__ in ('str', 'unicode'):
					cmd.extend(shlex.split(self.fixStr(eo)))
				cmd.extend(['--html', '-o', outfile, inpfile])
			elif re.search(r'\.svg$', inpfile):
				outfile = re.sub(r'(?:\.min)?(\.[^\.]+)$', r'.pretty\1', inpfile, 1)
				cmd = shlex.split(self.fixStr(self.get_setting('svgo_command') or 'svgo'))
				eo = self.get_setting('svgo_pretty_options')
				if type(eo).__name__ in ('str', 'unicode'):
					cmd.extend(shlex.split(self.fixStr(eo)))
				cmd.extend(['--pretty', inpfile, outfile])
			if cmd:
				print('Minify: Beautifying file:' + str(inpfile))
				self.run_cmd(cmd, outfile)

class MinifyCommand(PluginBase, MinifyClass, sublime_plugin.TextCommand):
	def do_action(self):
		self.minify()

class BeautifyCommand(PluginBase, BeautifyClass, sublime_plugin.TextCommand):
	def do_action(self):
		self.beautify()

class RunAfterSave(ThreadHandling, MinifyClass, sublime_plugin.EventListener):
	def on_post_save(self, view):
		self.view = view
		if self.get_setting('auto_minify_on_save'):
			filename = self.view.file_name()
			syntax = self.view.settings().get('syntax')
			if type(filename).__name__ in ('str', 'unicode') and ((re.search(r'\.(?:css|js|json|html?|svg)$', filename)) or (re.search(r'(\.[^\.]+)$', filename) and re.search(r'/(?:CSS|JavaScript|JSON|HTML)\.tmLanguage$', syntax))):
				searchFName = ''
				searchSyntax = ''
				if 'css' in self.get_setting('allowed_file_types'):
					searchFName += 'css|'
					searchSyntax += 'CSS|'
				if 'js' in self.get_setting('allowed_file_types'):
					searchFName += 'js|'
					searchSyntax += 'JavaScript|'
				if 'json' in self.get_setting('allowed_file_types'):
					searchFName += 'json|'
					searchSyntax += 'JSON|'
				if 'html' in self.get_setting('allowed_file_types'):
					searchFName += 'html?|'
					searchSyntax += 'HTML|'
				if 'svg' in self.get_setting('allowed_file_types'):
					searchFName += 'svg|'
				searchFNameRegEx = r'\.(?:' + searchFName.rstrip('|') + ')$'
				searchSyntaxRegEx = r'/(?:' + searchSyntax.rstrip('|') + ')\.tmLanguage$'
				if re.search(searchFNameRegEx, filename) or (re.search(r'(\.[^\.]+)$', filename) and re.search(searchSyntaxRegEx, syntax)):
					if re.search(r'\.min\.[^\.]+$', filename):
						if self.get_setting('debug_mode'):
							print('Minify: Skipping file ' + filename + ' - already minified')
					else:
						if SUBL_ASYNC:
							sublime.set_timeout_async(lambda: self.minify(), 0)
						else:
							self.minify()
				else:
					if self.get_setting('debug_mode'):
						print('Minify: Skipping file ' + filename + ' - not in allowed_file_types')
