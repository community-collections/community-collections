#!/usr/bin/env python

# Python 2/3 compatabilty and color printer
from __future__ import print_function
from __future__ import unicode_literals

import os
import sys
import argparse
import json
import re
import pickle
import time
import datetime
import copy

from . import stdtools
from .stdtools import introspect_function
from .stdtools import str_types
from .stdtools import tracebacker

class Singleton(type):
    # via https://stackoverflow.com/a/42239713
    def __init__(cls, name, bases, dict):
        super(Singleton, cls).__init__(name, bases, dict)
        cls._instance = None
    def __call__(cls, *args, **kw):
        if cls._instance is None:
            cls._instance = super(Singleton, cls).__call__(*args, **kw)
        return cls._instance

if False:
    class Cacher:
        """
        A class which when called by the cacher decorator will wrap execution
        in a read/write operation on the cache.
        """
        __metaclass__ = Singleton
        # since we enforce singleton the cache can be a class attribute
        cache = None
        cache_fn = 'cache.dat'
        cache_policy = 'empty'
        logger_policy = 'function_name,time'
        errorclear_policy = 'clear'
        establish_policy = 'check'
        def __init__(self,subject,obj):
            # subject is the function we are wrapping in the kernel
            self.subject = subject
            # object is the self of the class with a method decorated by cacher
            self.obj = obj
            # an empty cache policy means we do not use it
            if self.cache_policy=='empty': return
            # load 
            #! possibly confusing class and instance attributes
            if not os.path.isfile(self.cache_fn): self.cache = {}
            else: 
                print('status reading %s'%self.cache_fn)
                with open(self.cache_fn) as fp: 
                    self.cache = json.load(fp)
            self.errorclear()
            # note that the kernel and subsequent cache writes are handled manually
            #   typically by the cacher decorator
            return
        def kernel(self,*args,**kwargs):
            """
            Run the class method which is bookended by the read/write of cache
            """
            # run the subject (class method wrapped in cacher)
            # note that the obj here is the self of the class instance that 
            #   must be sent to the subject
            try: self.subject(self.obj,*args,**kwargs)
            # handle failure without breaking the cache
            except Exception as e:
                print('error caught')
                if hasattr(self,'cache'): 
                    self.cache['error'] = str(e)
                self.standard_write()
                raise
            self.standard_write()
            return
        def standard_write(self):
            # policy: this handler writes the current cache on error
            if self.cache_policy=='standard': 
                # standard write
                print('status writing %s'%self.cache_fn)
                with open(self.cache_fn,'w') as fp:
                    json.dump(self.cache,fp)
            elif self.cache_policy=='empty': pass
            else: raise Exception('invalid cache policy: %s'%self.cache_policy)
        def errorclear(self):
            if self.errorclear_policy=='clear':
                if 'error' in self.cache: 
                    del self.cache['error']
            else: raise Exception(
                'invalid errorclear_policy: %s'%self.errorclear_policy)
        def establish(self,name,function,policy='check',**kwargs):
            """
            Ensure that a result is stored in the cache.
            """
            if policy=='check':
                if name not in self.cache:
                    self.cache[name] = function(**kwargs)
            else: raise Exception('invalid policy %s'%policy)

#!!! this is a nope because it runs before Cacher.cache is ready
if False:
    def logger(function):
        """Decorator for updating the cache."""
        def logger(*args,**kwargs):
            #! self is really Parser/Cacher here ... !?? is this wise?
            if Cacher.cache_policy!='empty':
                if Cacher.cache==None:
                    import pdb;pdb.set_trace()
                if 'log' not in Cacher.cache:
                    Cacher.cache['log'] = []
                #! design?
                #! Cacher is singleton
                if Cacher.logger_policy=='function_name,time':
                    ts = datetime.datetime.fromtimestamp(
                        time.time()).strftime('%Y.%m.%d.%H%M')
                    record = {'when':ts,'function_name':function.__name__}
                    record['return'] = result
                    return record
                else: raise Exception('invalid logger_policy: %s'%logger_policy)
                #! done design?
                Cacher.cache['log'].append(record)
            return function(*args,**kwargs)
        return logger

    def logger(function):
        """Decorator for updating the cache."""
        def logger(*args,**kwargs):
            print('LOGGING NOW! %s'%function.__name__)
            return function(*args,**kwargs)
        return logger

    def cacher(subject):
        """Decorate a class function with the Cacher class."""
        # note that this is a critical link between Parser and Cacher
        def cacher(self,*args,**kwargs): 
            cache_partner = Cacher(subject=subject,obj=self)
            # dynamically populate the target class with cache tools
            for attr in ['cache','establish']:
                if hasattr(cache_partner,attr):
                    setattr(self,attr,getattr(cache_partner,attr))
            # run the kernel of the computation here
            return cache_partner.kernel(*args,**kwargs)
        return cacher

class Cacher(object):
    """
    Class decorator which supplies a cache and associated functions.
    """
    def __init__(self,
        # default policies
        cache=None,
        cache_fn='cache.dat',
        cache_policy='standard',
        errorclear_policy='clear',
        establish_policy='check',
        reserve_policy=True):
        if not isinstance(cache_fn,str_types):
            import pdb;pdb.set_trace()
            raise Exception(('The argument to Cacher must be a string, '
                'the name of the cache file. Use `Cacher()` for the '
                'default. We received cache_fn=%s in error.')%cache_fn)
        # allow the user to pass along a cache
        self.cache = cache
        # pass the decorator settings to the CachedClass below
        self.cache_fn = cache_fn
        self.cache_policy = cache_policy
        self.errorclear_policy = errorclear_policy
        self.establish_policy = establish_policy
        self.reserve_policy = reserve_policy
    def __call__(self,cls):
        # when using a class decorator is that the derived class is a singleton
        class CachedClass(cls):
            # receive the cache_fn from the decoration
            #! clumsy variable passing below
            cache = self.cache
            cache_fn = self.cache_fn
            cache_policy = self.cache_policy
            cache_policy = self.cache_policy
            errorclear_policy = self.errorclear_policy
            establish_policy = self.establish_policy
            reserve_policy = self.reserve_policy
            def __init__(self):
                if self.cache==None: self.cache = {}
                # an empty cache policy means we do not use it
                if self.cache_policy=='empty': return
                # load 
                if not os.path.isfile(self.cache_fn): pass
                else: 
                    print('status reading %s'%self.cache_fn)
                    with open(self.cache_fn) as fp: 
                        incoming = json.load(fp)
                        #! avoid collisions here?
                        self.cache.update(**incoming)
                if self.reserve_policy:
                    self.cache_copy = copy.deepcopy(self.cache)
                self.errorclear()
                # initialize the parent class
                super(cls,self).__init__()
            def _try_except(self,exception=None):
                print('error caught')
                if self.cache_policy!='empty': 
                    self.cache['error'] = str(exception)
                self.standard_write()
                if exception!=None:
                    tracebacker(exception)
                else: raise Exception('caught exception but it was not passed')
            def _try_else(self):
                self.standard_write()
            def standard_write(self):
                if self.cache_policy=='standard': 
                    if self.reserve_policy:
                        if self.cache==self.cache_copy:
                            print('status cache is unchanged')
                            return
                    # standard write
                    print('status writing %s'%self.cache_fn)
                    with open(self.cache_fn,'w') as fp:
                        json.dump(self.cache,fp)
                elif self.cache_policy=='empty': pass
                else: raise Exception('invalid cache policy: %s'%self.cache_policy)
            def errorclear(self):
                if self.errorclear_policy=='clear':
                    if 'error' in self.cache: 
                        del self.cache['error']
                else: raise Exception(
                    'invalid errorclear_policy: %s'%self.errorclear_policy)
            def establish(self,name,function,**kwargs):
                """
                Ensure that a result is stored in the cache.
                """
                if self.establish_policy=='check':
                    if name not in self.cache:
                        self.cache[name] = function(**kwargs)
                else: raise Exception('invalid policy %s'%policy)
        return CachedClass

def logger(cache):
    """Decorator for updating the cache when a function runs."""
    if not isinstance(cache,dict):
        raise Exception(('The @logger decorator must have '
            'the cache as an argument. We received: %s')%str(cache))
    def intermediate(function):
        def logger(*args,**kwargs):
            if 'log' not in cache:
                cache['log'] = []
            ts = datetime.datetime.fromtimestamp(
                time.time()).strftime('%Y.%m.%d.%H%M')
            record = {'when':ts,'function_name':function.__name__}
            #! WE DO NOT SAVE THE ANSWER
            result = function(*args,**kwargs)
            #! record['return'] = result
            cache['log'].append(record)
            return result
        return logger
    return intermediate

class Parser:
    """
    Convert all methods in a subclass into argparse and run with cacher.
    """
    __metaclass__ = Singleton
    def __init__(self):
        subject = self
        subcommand_names = [func for func in dir(subject) 
            if callable(getattr(subject, func))
            and not func.startswith('_')]
        parser = argparse.ArgumentParser(
            description='Manager.')
        subparsers = parser.add_subparsers(title='subcommands',
            description='valid subcommands',
            help='additional help')
        for name in subcommand_names:
            func = getattr(self,name)
            detail = {}
            if hasattr(func,'__doc__'):
                detail['help'] = func.__doc__
            sub = subparsers.add_parser(name,**detail)
            # introspection
            inspected = introspect_function(func)
            if ('func' in inspected['args'] 
                or 'func' in inspected['kwargs']):
                raise Exception('cannot use the argument func in %s'%name)
            #! temporary fix for introspect_function issue
            if (sys.version_info<(3,3) and len(inspected['args'])>0 
                and inspected['args'][0]=='self'): 
                inspected['args'] = inspected['args'][1:]
            for arg in inspected['args']:
                sub.add_argument(arg)
            for arg in inspected['kwargs'].keys():
                sub.add_argument(arg,nargs='?')
            sub.set_defaults(**inspected['kwargs'])
            # set the function
            sub.set_defaults(func=func)
        args = parser.parse_args()
        # print help if no function
        if not hasattr(args,'func'): 
            parser.print_help()
        # separate cacher before execute
        else: 
            # we protect the main execution loop with a handler here
            try: self._call(args)
            except Exception as e:
                if hasattr(self,'_try_except'):
                    # traceback is necessary here or raise is not useful
                    self._try_except(exception=e)
            else: 
                if hasattr(self,'_try_else'):
                    self._try_else()
        return

    def _call(self,args):
        """Main execution loop for a subcommand with handler and else"""
        func = args.func
        delattr(args,'func')
        func(**vars(args))

    def debug(self):
        """
        Interactive mode.
        """
        import code
        sys.ps1 = "[cc]: "
        vars = globals()
        vars.update(locals())
        if hasattr(self,'subshell',): 
            vars.update(**self.subshell)
        import readline,rlcompleter
        readline.set_completer(rlcompleter.Completer(vars).complete)
        readline.parse_and_bind("tab: complete")
        code.interact(local=vars,banner='')

class Convey(object):
    """
    Class decorator which supplies a cache and associated functions.
    """
    def __init__(self,**kwargs):
        for key,val in kwargs.items():
            setattr(self,key,val)
        self._keys = kwargs.keys()
    def __call__(self,cls):
        # when using a class decorator is that the derived class is a singleton
        class Convey(cls):
            for key in self._keys:
                setattr(cls,key,getattr(self,key))
        Convey.__name__ = cls.__name__
        return Convey            

