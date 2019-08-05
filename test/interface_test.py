#!/usr/bin/env python

from interface import Interface
import argparse
import cc_tools
from cc_tools.statetools import Cacher
from cc_tools.statetools import Parser
import sys

# try:
#     from unittest import mock  # python 3.3+
# except ImportError:
#     import mock  # python 2.6-3.2
try:
        # python 3.4+ should use builtin unittest.mock not mock package
            from unittest.mock import patch
except ImportError:
        from mock import patch

#@mock.patch('argparse.ArgumentParser.parse_args',
#            return_value=argparse.Namespace())
def test_flake8():
    """
    Test the flake8 command where we compare the files under flake8 inspection
    """
    # the cli arg matches the method call
    with patch.object(sys, 'argv', ['cc', 'flake8']):
        pyfiles = Interface().flake8()
    assert ['cc_tools/__init__.py', 'cc_tools/execute.py',
           'cc_tools/installers.py', 'cc_tools/misc.py',
           'cc_tools/modulefile_templates.py', 'cc_tools/settings.py',
           'cc_tools/statetools.py', 'cc_tools/stdtools.py',
           'interface.py'] == pyfiles
