#!/usr/bin/env python

# Python 2/3 compatabilty and color printer
from __future__ import print_function
from __future__ import unicode_literals
import os,sys,re

str_types = (str,unicode) if sys.version_info<(3,0) else (str,)
basestring = string_types = str_types = (str,unicode) if sys.version_info<(3,0) else (str,)

### COLOR PRINTER (requires compatibility above)

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

def color_printer(override=False,prefix=None):
    """
    Prepare a special override print function.
    This decorator stylizes print statements so that printing a tuple that begins with words like `status` 
    will cause print to prepend `[STATUS]` to each line. This makes the output somewhat more readable but
    otherwise does not affect printing. We use builtins to distribute the function. Any python 2 code which 
    imports `print_function` from `__future__` gets the stylized print function. Any python 3 code which 
    uses print will print this correctly. The elif which uses a regex means that the overloaded print
    can turn e.g. print('debug something bad happened') into "[DEBUG] something bad happened" in stdout.
    """
    if prefix==None: prefix = ''
    else: prefix = "%s "%prefix
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
                if match: 
                    return _print(prefix+'[%s]'%match.group(1).upper()+' '+match.group(2),**kwargs)
                else: return _print(*args,**kwargs)
            else: return _print(*args,**kwargs)
        # export custom print function before other imports
        # this code ensures that in python 3 we overload print
        #   while any python 2 code that wishes to use overloaded print
        #   must of course from __future__ import print_function
        builtins.print = print_stylized

### BASH INTERFACE

import subprocess

def command_check(command,cwd=None,quiet=False):
    """Run a command and see if it completes with returncode zero."""
    kwargs = {}
    if cwd: kwargs['cwd'] = cwd
    try:
        with open(os.devnull,'w') as FNULL:
            proc = subprocess.Popen(command,stdout=FNULL,
            	stderr=FNULL,shell=True,executable='/bin/bash',**kwargs)
            proc.communicate()
            return proc.returncode
    except Exception as e: 
        if not quiet: print('warning caught exception on command_check: %s'%e)
        # we return an invalid bash state to ensure that it cannot match
        #   the returncode on failures
        return -1

def bash(command,log=None,cwd=None,inpipe=None,scroll=True,tag=None,
	announce=False,local=False,scroll_log=True,quiet=False):
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
		if stdout and not quiet: print('error','stdout: %s'%stdout.decode('utf-8').strip('\n'))
		if stderr and not quiet: print('error','stderr: %s'%stderr.decode('utf-8').strip('\n'))
		raise Exception('bash returned error state')
	# we have to wait or the returncode below is None
	# note that putting wait here means that you get a log file with the error 
	#   along a standard traceback to the location of the bash call
	proc.wait()
	if proc.returncode: 
		if log: raise Exception('bash error, see %s'%log)
		else: 
			if stdout and not quiet:
				print('error','stdout:')
				print(stdout.decode('utf-8').strip('\n'))
			if stderr and not quiet:
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

### INTROSPECTION

import inspect

def introspect_function(func,**kwargs):
	"""
	Get arguments and kwargs expected by a function.
	"""
	#! BUG REPORT!
	#! inside a class method: def debug(self,**kwargs): you get different
	#!   python 2/3 behavior: {'args': ('self',), 'kwargs': {}} in 2 and
	#!   {'args': ('kwargs',), 'kwargs': {}, '**': ['kwargs']} in 3
	#!   see temporary fix in a customer, statetools.py
	message = kwargs.pop('message',(
		'function introspection received a string instead of a function '
		'indicating that we have gleaned the function without importing it. '
		'this indicates an error which requires careful debugging.'))
	# getargspec will be deprecated by Python 3.6
	if sys.version_info<(3,3): 
		if isinstance(func,str_types): raise Exception(messsage)
		args,varargs,varkw,defaults = inspect.getargspec(func)
		if defaults: 
			std,var = args[:-len(defaults)],args[-len(defaults):]
			packed = dict(args=tuple(std),kwargs=dict(zip(var,defaults)))
		else: packed = dict(args=tuple(args),kwargs={})
		return packed
	else:
		#! might need to validate this section for python 3 properly
		sig = inspect.signature(func) # pylint: disable=no-member
		packed = {'args':tuple([key for key,val in sig.parameters.items() 
			if val.default==inspect._empty])}
		keywords = [(key,val.default) for key,val in sig.parameters.items() 
			if val.default!=inspect._empty]
		packed['kwargs'] = dict(keywords)
		double_star = [i for i in sig.parameters 
			if str(sig.parameters[i]).startswith('**')]
		if double_star: packed['**'] = double_star
		return packed

### MISC

def listify(x): 
	"""Turn a string or a list into a list."""
	if isinstance(x,basestring): return [x]
	elif isinstance(x,list): return x
	elif isinstance(x,tuple): return x
	else: raise Exception(
		'listify takes a string, list, tuple but got: %s'%type(x))

### TREEVIEW

str_types_list = list(str_types)

def asciitree(obj,depth=0,wide=2,last=[],recursed=False):
	"""
	Print a dictionary as a tree to the terminal.
	Includes some simuluxe-specific quirks.
	"""
	corner = u'\u251C'
	corner_end = u'\u2514'
	horizo,horizo_bold = u'\u2500',u'\u2501'
	vertic,vertic_bold = u'\u2502',u'\u2503'
	tl,tr,bl,br = u'\u250F',u'\u2513',u'\u2517',u'\u251B'
	spacer_both = dict([(k,{
		0:'\n',1:(' '*(wide+1)*(depth-1)+c+horizo*wide),
		2:' '*(wide+1)*(depth-1)}[depth] if depth <= 1 
		else (''.join([(vertic if d not in last else ' ')+
		' '*wide for d in range(1,depth)]))+c+horizo*wide) 
		for (k,c) in [('mid',corner),('end',corner_end)]])
	spacer = spacer_both['mid']
	if type(obj) in [float,int,bool]+str_types_list:
		if depth == 0: print(spacer+str(obj)+'\n'+horizo*len(obj))
		else: print(spacer+str(obj))
	elif isinstance(obj,dict) and all([type(i) in [str,float,int,bool] for i in obj.values()]) and depth==0:
		asciitree({'HASH':obj},depth=1,recursed=True)
	elif type(obj) in [list,tuple]:
		for ind,item in enumerate(obj):
			spacer_this = spacer_both['end'] if ind==len(obj)-1 else spacer
			if type(item) in [float,int,bool]+str_types_list: print(spacer_this+str(item))
			elif item != {}:
				print(spacer_this+'('+str(ind)+')')
				asciitree(item,depth=depth+1,
					last=last+([depth] if ind==len(obj)-1 else []),
					recursed=True)
			else: print('unhandled tree object %s'%item)
	elif isinstance(obj,dict) and obj != {}:
		for ind,key in enumerate(obj.keys()):
			spacer_this = spacer_both['end'] if ind==len(obj)-1 else spacer
			if type(obj[key]) in [float,int,bool]+str_types_list: print(spacer_this+str(key)+' = '+str(obj[key]))
			# special: print single-item lists of strings on the same line as the key
			elif type(obj[key])==list and len(obj[key])==1 and type(obj[key][0]) in [str,float,int,bool]:
				print(spacer_this+key+' = '+str(obj[key]))
			# special: skip lists if blank dictionaries
			elif type(obj[key])==list and all([i=={} for i in obj[key]]):
				print(spacer_this+key+' = (empty)')
			elif obj[key] != {}:
				# fancy border for top level
				if depth == 0:
					print('\n'+tl+horizo_bold*(len(key)+0)+
						tr+spacer_this+vertic_bold+str(key)+vertic_bold+'\n'+\
						bl+horizo_bold*len(key)+br+'\n'+vertic)
				elif obj[key]==None: print(spacer_this+key+' = None')
				else: print(spacer_this+key)
				if obj[key]!=None: 
					asciitree(obj[key],depth=depth+1,
						last=last+([depth] if ind==len(obj)-1 else []),
						recursed=True)
			elif type(obj[key])==list and obj[key]==[]:
				print(spacer_this+'(empty)')
			elif obj[key]=={}: print(spacer_this+'%s = {}'%key)
			else: print('unhandled tree object %s'%key)
	else: print('unhandled tree object %s'%obj)
	if not recursed: print('\n')

def treeview(data,style='unicode'):
	"""
	Print a tree in one of several styles.
	"""
	#! if not style: style = conf.get('tree_style','unicode')  # pylint: disable=undefined-variable
	if style=='unicode': 
		# protect against TeeMultiplexer here because it cannot print unicode to the log file
		do_swap_stdout = sys.stdout.__class__.__name__=='TeeMultiplexer'
		do_swap_stderr = sys.stderr.__class__.__name__=='TeeMultiplexer'
		if do_swap_stdout: 
			hold_stdout = sys.stdout
			#! assume fd1 is the original stream
			sys.stdout = sys.stdout.fd1
		if do_swap_stderr: 
			hold_stderr = sys.stderr
			#! assume fd1 is the original stream
			sys.stderr = sys.stderr.fd1
		# show the tree here
		asciitree(data)
		# swap back
		if do_swap_stderr: sys.stderr = hold_stderr
		if do_swap_stdout: sys.stdout = hold_stdout
	elif style=='json': return print(json.dumps(data))
	elif style=='pprint': 
		import pprint
		return pprint.pprint(data)
	else: raise Exception('invalid style %s'%style)

### HANDLER

#! depends on treeview stuff

class Handler(object):
	_taxonomy = {}
	# internals map to special structures in the Handler level
	_internals = {'name':'name','meta':'meta'}
	# whether to allow inexact matching (we still prefer strict matching)
	lax = True
	def _report(self):
		print('debug Handler summary follows')
		print(
			'debug the Handler parent class allows the child to define methods '
			'one of which is automatically called with the args and kwargs '
			'given to the child class constructor. The _protected keys are '
			'diverted into attributes common to all child clas instances. For '
			'example the name and meta flags are common to all.')
		print('debug _protected keys not sent to methods: %s'%
			list(self._internals.keys()))
		if not self._taxonomy: print('debug There are no methods.')
		else: 
			for k,v in self._taxonomy.items():
				print('debug A method named "%s" has arguments: %s'%(k,v))
	def _matchless(self,args):
		"""Report that we could not find a match."""
		#! note that we need a more strict handling for the name keyword
		#!   which incidentally might be worth retiring
		name_child = self.__class__.__name__ 
		self._report()
		raise Exception(
			('%(name)s cannot classify instructions with '
				'keys: %(args)s. See the report above for details.'
			if not self.classify_fail else self.classify_fail)%
			{'args':args,'name':name_child})
	def _classify(self,*args):
		matches = [name for name,keys in self._taxonomy.items() if (
			(isinstance(keys,set) and keys==set(args)) or 
			(isinstance(keys,dict) and set(keys.keys())=={'base','opts'} 
				and (set(args)-keys['opts'])==keys['base']
				and (set(args)-keys['base'])<=keys['opts']))]
		if len(matches)==0: 
			if not self.lax: self._matchless(args)
			else:
				# collect method target that accept spillovers
				# where spillover means we have extra kwargs going to **kwargs
				# and not that we do not allow arguments in this dev stage
				spillovers = [i for i,j in self._taxonomy.items() 
					if j.get('kwargs',False)]
				spills = [(i,
					set.difference(set(args),set.union(j['base'],j['opts']))) 
					for i,j in self._taxonomy.items() if i in spillovers]
				if not spills: self._matchless(args)
				scores = dict([(i,len(j)) for i,j in spills])
				try: score_min = min(scores.values())
				except:
					import ipdb;ipdb.set_trace()
				matches_lax = [i for i,j in scores.items() if j==score_min]
				if len(matches_lax)==0: self._matchless(args)
				elif len(matches_lax)==1: return matches_lax[0]
				else:
					# if we have redundant matches and one is the default
					#   then the default is the tiebreaker
					#! the following logic needs to be checked more carefully
					if self._default and self._default in matches_lax: 
						return self._default
					# if no default tiebreaker we are truly stuck
					self._report()
					raise Exception('In lax mode we have redundant matches. '
						'Your arguments (%s) are equally compatible with these '
						'methods: %s'%(list(args),matches_lax))
		elif len(matches)>1: 
			raise Exception('redundant matches: %s'%matches)
		else: return matches[0]
	def _taxonomy_inference(self):
		"""
		Infer a taxonomy from constituent functions. The taxonomy enumerates
		which functions are called when required (base) and optional (opts)
		arguments are supplied. Historically we set the class attribute 
		taxonomy to specify this, but we infer it here.
		"""
		# note that all functions that start with "_" are invalid target methods
		methods = dict([(i,j) for i,j in 
			inspect.getmembers(self,predicate=inspect.ismethod)
			if not i.startswith('_')])
		expected = dict([(name,introspect_function(methods[name])) 
			for name in methods])
		# decorated handler subclass methods should save introspect as an attr
		for key in methods:
			if hasattr(methods[key],'_introspected'): 
				expected[key] = methods[key]._introspected
		#! this is not useful in python 3 because the self argument is 
		#!   presumably ignored by the introspection
		if sys.version_info<(3,0):
			for name,expect in expected.items():
				if 'self' not in expect['args']:
					print('debug expect=%s'%expect)
					raise Exception('function "%s" lacks the self argument'%
						name)
		# convert to a typical taxonomy structure
		self._taxonomy = dict([(name,{
			'base':set(expect['args'])-set(['self']),
			'opts':set(expect['kwargs'].keys())
			}) for name,expect in expected.items()
			if not name.startswith('_')])
		"""
		exceptions to the taxonomy
		any functions with kwargs as a base argument via "**kwargs" are allowed
		to accept any arbitrary keyword arguments, as is the 
		"""
		for key in self._taxonomy:
			if ('kwargs' in self._taxonomy[key]['base'] 
				and 'kwargs' in expected[key].get('**',[])):
				self._taxonomy[key]['base'].remove('kwargs')
				self._taxonomy[key]['kwargs'] = True
		# check for a single default handler that only accespts **kwargs
		defaults = [i for i,j in self._taxonomy.items() 
			if j.get('kwargs',False) and len(j['base'])==0 
			and len(j['opts'])==0]
		if len(defaults)>1: 
			raise Exception('More than one function accepts only **kwargs: %s'%defaults)
		elif len(defaults)==1: self._default = defaults[0]
		else: self._default = None
		# check valid taxonomy
		# note that using a protected keyword in the method arguments can
		#   be very confusing. for example, when a method that takes a name
		#   is used, the user might expect name to go to the method but instead
		#   it is intercepted by the parent Handler class and stored as an
		#   attribute. hence we have a naming table called _internals and we
		#   protect against name collisions here
		collisions = {}
		for key in self._taxonomy:
			argnames = (list(self._taxonomy[key]['base'])+
				list(self._taxonomy[key]['opts']))
			collide = [i for i in self._internals.values()
				if i in argnames]
			if any(collide): collisions[key] = collide
		if any(collisions):
			# we print the internals so you can see which names you cannot use
			print('debug internals are: %s'%self._internals)
			raise Exception((
				'Name collisions in %s (Handler) method '
				'arguments: %s. See internals above.')%(
					self.__class__.__name__,collisions))
		fallbacks = []
	def __init__(self,*args,**kwargs):
		if args: 
			raise Exception(
				'Handler classes cannot receive arguments: %s'%list(args))
		classify_fail = kwargs.pop('classify_fail',None)
		inspect = kwargs.pop('inspect',False)
		# safety check that internals include the values we require
		#   including a name and a meta target
		required_internal_targets = set(['meta','name'])
		if not set(self._internals.keys())==required_internal_targets:
			raise Exception(
				'Handler internals must map to %s but we received: %s'%(
				required_internal_targets,set(self._internals.keys())))
		name = kwargs.pop(self._internals['name'],None)
		meta = kwargs.pop(self._internals['meta'],{})
		self.meta = meta if meta else {}
		#! name is a common key. how are we using it here?
		if not name: self.name = "UnNamed"
		else: self.name = name
		# kwargs at this point are all passed to the subclass method
		# leaving taxonomy blank means that it is inferred from args,kwargs
		#   of the constitutent methods in the class
		if not self._taxonomy: self._taxonomy_inference()
		# allow a blank instance of a Handler subclass, sometimes necessary
		#   to do the taxonomy_inference first
		#! note that some use-case for Handler needs to be updated with inspect
		#!   in which we need the taxonomy beforehand. perhaps a replicator?
		if not kwargs and inspect: return
		self.classify_fail = classify_fail
		fname = self._classify(*kwargs.keys())
		self.style = fname
		self.kwargs = kwargs
		if not hasattr(self,fname): 
			raise Exception(
				'development error: taxonomy name "%s" is not a member'%fname)
		# before we run the function to generate the object, we note the 
		#   inherent attributes assigned by Handler, the parent, so we can
		#   later identify the novel keys
		self._stock = dir(self)+['_stock','solution']
		# introspect on the function to make sure the keys 
		#   in the taxonomy match the available keys in the function?
		self.solution = getattr(self,fname)(**kwargs)
		# make a list of new class attributes set during the method above
		self._novel = tuple(set(dir(self)) - set(self._stock))
	def __repr__(self):
		"""Look at the subclass-specific parts of the object."""
		#! this is under development
		if hasattr(self,'_novel'): 
			report = dict(object=dict(self=dict([(i,getattr(self,i)) for i in self._novel])))
			if self.meta: report['object']['meta'] = self.meta
			report['object']['name'] = self.name
			treeview(report) #! is it silly to print trees?
			return "%s [a Handler]"%self.name
		else: return super(Handler,self).__repr__()
	@property
	def solve(self): 
		return self.solution
	@property
	def result(self): 
		# an alias for solve
		# instantiating a Handler subclass runs the function
		# the solve, result properties return the result
		return self.solution

### TRACER

import sys,re,traceback

def tracebacker_base(exc_type,exc_obj,exc_tb,debug=False):
	"""Standard traceback handling for easy-to-read error messages."""
	tag = say('[TRACEBACK]','gray')
	tracetext = tag+' '+re.sub(r'\n','\n%s'%tag,str(''.join(traceback.format_tb(exc_tb)).strip()))
	if not debug:
		print(say(tracetext))
		print(say('[ERROR]','red_black')+' '+say('%s'%exc_obj,'cyan_black'))
	else: 
		try: import ipdb as pdb_this
		except: 
			print('note','entering debug mode but cannot find ipdb so we are using pdb')
			import pdb as pdb_this
		print(say(tracetext))	
		print(say('[ERROR]','red_black')+' '+say('%s'%exc_obj,'cyan_black'))
		print(say('[DEBUG] entering the debugger','mag_gray'))
		import ipdb;ipdb.set_trace()
		pdb_this.pm()

def tracebacker(*args,**kwargs):
	"""Standard traceback handling for easy-to-read error messages."""
	debug = kwargs.pop('debug',False)
	if kwargs: raise Exception('unprocessed kwargs %s'%kwargs)
	# note: previously handled interrupt here but this prevents normal traceback
	if len(args)==1 or len(args)==0: 
		exc_type,exc_obj,exc_tb = sys.exc_info()
		tracebacker_base(exc_type,exc_obj,exc_tb,debug=debug)
	elif len(args)==3: tracebacker_base(*args,debug=debug)
	else: raise Exception(
		'tracebacker expects either 0, 1 or 3 arguments but got %d'%
		len(args))

def debugger(*args): 
	"""Run the tracebacker with interactive debugging if possible."""
	debug = not (hasattr(sys, 'ps1') or not sys.stderr.isatty())
	if args[0]==KeyboardInterrupt: 
		print()
		print('status','received KeyboardInterrupt')
		debug = False
	return tracebacker(*args,debug=debug)

### MISC

def confirm(*msgs,**kwargs):
	"""Check with the user."""
	sure = kwargs.pop('sure',False)
	if kwargs: raise Exception('unprocessed kwargs: %s'%kwargs)
	return sure or all(
		re.match('^(y|Y)',(input if sys.version_info>(3,0) else raw_input)
		('[QUESTION] %s (y/N)? '%msg))!=None for msg in msgs)

