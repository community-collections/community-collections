#!/usr/bin/env python

# Python 2/3 compatabilty and color printer
from __future__ import print_function
from __future__ import unicode_literals

import os
import sys
import subprocess
import re

str_types = (str,unicode) if sys.version_info<(3,0) else (str,)

def say(text,*flags):
	"""Colorize the text."""
	# three-digit codes: first one is style (0 and 2 are regular, 3 is italics, 1 is bold)
	colors = {'gray':(0,37,48),'cyan_black':(1,36,40),'red_black':(1,31,40),'black_gray':(0,37,40),
		'white_black':(1,37,40),'mag_gray':(0,35,47)}
	# no colors if we are logging to a text file because nobody wants all that unicode in a log
	if flags and hasattr(sys.stdout,'isatty') and sys.stdout.isatty()==True: 
		if any(f for f in flags if f not in colors): 
			raise Exception('cannot find a color %s. try one of %s'%(str(flags),colors.keys()))
		for f in flags[::-1]: 
			style,fg,bg = colors[f]
			text = '\x1b[%sm%s\x1b[0m'%(';'.join([str(style),str(fg),str(bg)]),text)
	return text

def prepare_print(override=False):
	"""
	Prepare a special override print function.
	This decorator stylizes print statements so that printing a tuple that begins with words like `status` 
	will cause print to prepend `[STATUS]` to each line. This makes the output somewhat more readable but
	otherwise does not affect printing. We use builtins to distribute the function. Any python 2 code which 
	imports `print_function` from `__future__` gets the stylized print function. Any python 3 code which 
	uses print will print this correctly. The elif which uses a regex means that the overloaded print
	can turn e.g. print('debug something bad happened')	into "[DEBUG] something bad happened" in stdout.
	"""
	# python 2/3 builtins
	try: import __builtin__ as builtins
	except ImportError: import builtins
	# use custom print function everywhere
	if builtins.__dict__['print'].__name__!='print_stylized':
		# every script must import print_function from __future__ or syntax error
		# hold the standard print
		_print = print
		key_leads = ['status','warning','error','note','usage',
			'exception','except','question','run','tail','watch',
			'bash','debug']
		key_leads_regex = re.compile(r'^(?:(%s)\s)(.+)$'%'|'.join(key_leads))
		def print_stylized(*args,**kwargs):
			"""Custom print function."""
			if (len(args)>0 and 
				isinstance(args[0],str_types) and args[0] in key_leads):
				return _print('[%s]'%args[0].upper(),*args[1:])
			# regex here adds very little time and allows more natural print 
			#   statements to be capitalized
			#! note that we can retire all print('debug','message') statements
			elif len(args)==1 and isinstance(args[0],str_types):
				match = key_leads_regex.match(args[0])
				if match: return _print(
					#! rpb modifies for community collections
					#!   '[%s]'%match.group(1).upper(),
					say('[CC]','red_black')+' '+say('[%s]'%match.group(1).upper(),'mag_gray'),
					match.group(2),**kwargs)
				else: return _print(*args,**kwargs)
			else: return _print(*args,**kwargs)
		# export custom print function before other imports
		# this code ensures that in python 3 we overload print
		#   while any python 2 code that wishes to use overloaded print
		#   must of course from __future__ import print_function
		builtins.print = print_stylized

def command_check(command):
    """Run a command and see if it completes with returncode zero."""
    try:
        with open(os.devnull,'w') as FNULL:
            proc = subprocess.Popen(command,stdout=FNULL,stderr=FNULL,shell=True,executable='/bin/bash')
            proc.communicate()
            return proc.returncode==0
    except Exception as e: 
        print('warning caught exception on command_check: %s'%e)
        return False

def bash(command,log=None,cwd=None,inpipe=None,scroll=True,tag=None,
	announce=False,local=False,scroll_log=True):
	"""
	Run a bash command.
	Development note: tee functionality would be useful however you cannot use pipes with subprocess here.
	Vital note: log is relative to the current location and not the cwd.
	"""
	if announce: 
		print('status',
			'ortho.bash%s runs command: %s'%(' (at %s)'%cwd if cwd else '',str(command)))
	merge_stdout_stderr = False
	if local: cwd_local = str(cwd)
	if not cwd or local: cwd = '.'
	if local: 
		if log: log = os.path.relpath(log,cwd_local)
		pwd = os.getcwd()
		os.chdir(cwd_local)
	if log == None: 
		# no present need to separate stdout and stderr so note the pipe below
		merge_stdout_stderr = True
		kwargs = dict(cwd=cwd,shell=True,executable='/bin/bash',
			stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
		if input: kwargs['stdin'] = subprocess.PIPE
		proc = subprocess.Popen(command,**kwargs)
		if inpipe and scroll: raise Exception('cannot use inpipe with scrolling output')
		if inpipe: 
			#! note that some solutions can handle input
			#!   see: https://stackoverflow.com/questions/17411966
			#!   test with make_ndx at some point
			stdout,stderr = proc.communicate(input=inpipe)
		# no log and no input pipe
		else: 
			# scroll option pipes output to the screen
			if scroll:
				empty = '' if sys.version_info<(3,0) else b''
				for line in iter(proc.stdout.readline,empty):
					sys.stdout.write((tag if tag else '')+line.decode('utf-8'))
					sys.stdout.flush()
				proc.wait()
				if proc.returncode:
					raise Exception('see above for error. bash return code %d'%proc.returncode)
			# no scroll waits for output and then checks it below
			else: stdout,stderr = proc.communicate()
	# alternative scroll method via https://stackoverflow.com/questions/18421757
	# special scroll is useful for some cases where buffered output was necessary
	# this method can handle universal newlines while the threading method cannot
	elif log and scroll=='special':
		with io.open(log,'wb') as writes, io.open(log,'rb',1) as reads:
			proc = subprocess.Popen(command,stdout=writes,
				cwd=cwd,shell=True,universal_newlines=True)
			while proc.poll() is None:
				sys.stdout.write(reads.read().decode('utf-8'))
				time.sleep(0.5)
			# read the remaining
			sys.stdout.write(reads.read().decode('utf-8'))
	# log to file and print to screen using the reader function above
	elif log and scroll:
		# via: https://stackoverflow.com/questions/31833897/
		# note that this method also works if you remove output to a file
		#   however I was not able to figure out how to identify which stream 
		#   was which during iter, for obvious reasons
		#! note that this fails with weird newlines i.e. when GROMACS supplies
		#!   a "remaining wall clock time" and this problem cannot be overcome
		#!   by setting universal_newlines with this scroll method. recommend
		#!   that users instead try the special method above, which works fine
		#!   with unusual newlines
		proc = subprocess.Popen(command,cwd=cwd,shell=True,executable='/bin/bash',
			stdout=subprocess.PIPE,stderr=subprocess.PIPE,bufsize=1)
		qu = queue.Queue()
		threading.Thread(target=reader,args=[proc.stdout,qu]).start()
		threading.Thread(target=reader,args=[proc.stderr,qu]).start()
		empty = '' if sys.version_info<(3,0) else b''
		with open(log,'ab') as fp:
			for _ in range(2):
				for _,line in iter(qu.get,None):
					# decode early, encode late
					line_decode = line.decode('utf-8')
					# note that sometimes we get a "\r\n" or "^M"-style newline
					#   which makes the output appear inconsistent (some lines are prefixed) so we 
					#   replace newlines, but only if we are also reporting the log file on the line next
					#   to the output. this can get cluttered so you can turn off scroll_log if you want
					if scroll_log:
						line = re.sub('\r\n?',r'\n',line_decode)
						line_subs = ['[LOG] %s | %s'%(log,l.strip(' ')) 
							for l in line.strip('\n').splitlines() if l] 
						if not line_subs: continue
						line_here = ('\n'.join(line_subs)+'\n')
					else: line_here = re.sub('\r\n?',r'\n',line_decode)
					# encode on the way out to the file, otherwise print
					# note that the encode/decode events in this loop work for ascii and unicode in both
					#   python 2 and 3, however python 2 (where we recommend importing unicode_literals) will
					#   behave weird if you print from a script called through ortho.bash due to locale issues
					#   described here: https://pythonhosted.org/kitchen/unicode-frustrations.html
					#   so just port your unicode-printing python 2 code or use a codecs.getwriter
					print(line_here,end='')
					# do not write the log file in the final line
					fp.write(line.encode('utf-8'))
	# log to file and suppress output
	elif log and not scroll:
		output = open(log,'w')
		kwargs = dict(cwd=cwd,shell=True,executable='/bin/bash',
			stdout=output,stderr=output)
		if inpipe: kwargs['stdin'] = subprocess.PIPE
		proc = subprocess.Popen(command,**kwargs)
		if not inpipe: stdout,stderr = proc.communicate()
		else: stdout,stderr = proc.communicate(input=inpipe.encode('utf-8'))
	else: raise Exception('invalid options')
	if not scroll and stderr: 
		if stdout: print('error','stdout: %s'%stdout.decode('utf-8').strip('\n'))
		if stderr: print('error','stderr: %s'%stderr.decode('utf-8').strip('\n'))
		raise Exception('bash returned error state')
	# we have to wait or the returncode below is None
	# note that putting wait here means that you get a log file with the error 
	#   along a standard traceback to the location of the bash call
	proc.wait()
	if proc.returncode: 
		if log: raise Exception('bash error, see %s'%log)
		else: 
			if stdout:
				print('error','stdout:')
				print(stdout.decode('utf-8').strip('\n'))
			if stderr:
				print('error','stderr:')
				print(stderr.decode('utf-8').strip('\n'))
			raise Exception('bash error with returncode %d and stdout/stderr printed above'%proc.returncode)
	if scroll==True: 
		proc.stdout.close()
		if not merge_stdout_stderr: proc.stderr.close()
	if local: os.chdir(pwd)
	if not scroll:
		if stderr: stderr = stderr.decode('utf-8')
		if stdout: stdout = stdout.decode('utf-8')
	return None if scroll else {'stdout':stdout,'stderr':stderr}