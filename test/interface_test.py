#!/usr/bin/env python

from interface import Interface
import sys
import os

try:
    # python 3.4+ should use builtin unittest.mock not mock package
    from unittest.mock import patch
except ImportError:
    from mock import patch


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


def test_profile_cc_file():
    """
    Test the noninteractive command './cc profile --no-bashrc'
    """
    # the cli arg matches the method call
    with patch.object(sys, 'argv', ['cc', 'profile', '--no-bashrc']):
        Interface().profile(bashrc=False)
    assert os.path.exists('profile_cc.sh')


def test_capable():
    """
    Test the noninteractive command './cc capable'
    There is not an assertion to test yet because this is system dependent
    """
    # the cli arg matches the method call
    with patch.object(sys, 'argv', ['cc', 'capable']):
        Interface().capable()
