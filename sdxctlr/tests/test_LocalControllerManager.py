# Copyright 2016 - Sean Donovan
# AtlanticWave/SDX Project


# Unit tests for the AuthorizationInspector class

import unittest
import threading
import mock
import os
import logging

from sdxctlr.LocalControllerManager import *

CONFIG_FILE = 'sdxctlr/tests/test_manifests/lcmanagertest.manifest'
class SingletonTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):

        cls.logger = logging.getLogger(cls.__name__)
        formatter = logging.Formatter('%(asctime)s %(name)-12s: %(thread)s %(levelname)-8s %(message)s')
        console = logging.StreamHandler()
        console.setLevel(logging.DEBUG)
        console.setFormatter(formatter)
        cls.logger.setLevel(logging.DEBUG)
        cls.logger.handlers = []
        cls.logger.addHandler(console)

        cls.logger.debug("Beginning %s:%s" % (os.path.basename(__file__),
                                              cls.__name__))

        import sys
        cls.logger.debug("BEGIN %s" % cls.__name__)
        cls.logger.debug("sys.path: %s" % sys.path)
        
    @mock.patch('sdxctlr.LocalControllerManager.AuthenticationInspector',
                autospec=True)
    def test_singleton(self, authentication):
        self.logger.warning("BEGIN %s" % (self.id()))
        firstManager = LocalControllerManager(manifest=CONFIG_FILE)
        secondManager = LocalControllerManager(manifest=CONFIG_FILE)

        self.failUnless(firstManager is secondManager)

class VerifyLCTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):

        cls.logger = logging.getLogger(cls.__name__)
        formatter = logging.Formatter('%(asctime)s %(name)-12s: %(thread)s %(levelname)-8s %(message)s')
        console = logging.StreamHandler()
        console.setLevel(logging.DEBUG)
        console.setFormatter(formatter)
        cls.logger.setLevel(logging.DEBUG)
        cls.logger.handlers = []
        cls.logger.addHandler(console)

        cls.logger.debug("Beginning %s:%s" % (os.path.basename(__file__),
                                              cls.__name__))

        import sys
        cls.logger.debug("BEGIN %s" % cls.__name__)
        cls.logger.debug("sys.path: %s" % sys.path)
        
    @mock.patch('sdxctlr.LocalControllerManager.AuthenticationInspector',
                autospec=True)
    def test_get_user(self, authentication):
        self.logger.warning("BEGIN %s" % (self.id()))
        man = LocalControllerManager(manifest=CONFIG_FILE)

        ctlrname = 'atl'
        credentials = "atlpw"
        lcip = "10.10.10.10"
        switchips = ['10.10.10.11']

        part = man._get_controller(ctlrname)
        self.assertNotEqual(part, None)
        self.assertEquals(part.shortname, ctlrname)
        self.assertEquals(part.credentials, credentials)
        self.assertEquals(part.lcip, lcip)
        self.assertEquals(part.switchips, switchips)
               
        ctlrname = 'mia'
        credentials = "miapw"
        lcip = "10.10.10.20"
        switchips = ['10.10.10.21']

        part = man._get_controller(ctlrname)
        self.assertNotEqual(part, None)
        self.assertEquals(part.shortname, ctlrname)
        self.assertEquals(part.credentials, credentials)
        self.assertEquals(part.lcip, lcip)
        self.assertEquals(part.switchips, switchips)

        ctlrname = 'gru'
        credentials = "grupw"
        lcip = "10.10.10.30"
        switchips = ['10.10.10.31']

        part = man._get_controller(ctlrname)
        self.assertNotEqual(part, None)
        self.assertEquals(part.shortname, ctlrname)
        self.assertEquals(part.credentials, credentials)
        self.assertEquals(part.lcip, lcip)
        self.assertEquals(part.switchips, switchips)

    @mock.patch('sdxctlr.LocalControllerManager.AuthenticationInspector',
                autospec=True)
    def test_get_bad_ctlr(self, authentication):
        self.logger.warning("BEGIN %s" % (self.id()))
        man = LocalControllerManager(manifest=CONFIG_FILE)

        ctlrname = "NOTREAL"
        self.failUnless(man._get_controller(ctlrname) == None)

        ctlrname = "nyc"
        credentials = "nycpw"
        lcip = "10.10.10.30"
        switchips = ['10.10.10.31']

        man.add_controller(ctlrname, credentials, lcip, switchips)
        part = man._get_controller(ctlrname)
        self.failUnless(part != None)
        self.failUnless(part.shortname == ctlrname)
        self.failUnless(part.credentials == credentials)
        self.failUnless(part.lcip == lcip)
        self.failUnless(part.switchips == switchips)

        # Make sure the old ones are still there.
        ctlrname = 'atl'
        credentials = "atlpw"
        lcip = "10.10.10.10"
        switchips = ['10.10.10.11']

        part = man._get_controller(ctlrname)
        self.assertNotEqual(part, None)
        self.assertEquals(part.shortname, ctlrname)
        self.assertEquals(part.credentials, credentials)
        self.assertEquals(part.lcip, lcip)
        self.assertEquals(part.switchips, switchips)
               
        ctlrname = 'mia'
        credentials = "miapw"
        lcip = "10.10.10.20"
        switchips = ['10.10.10.21']

        part = man._get_controller(ctlrname)
        self.assertNotEqual(part, None)
        self.assertEquals(part.shortname, ctlrname)
        self.assertEquals(part.credentials, credentials)
        self.assertEquals(part.lcip, lcip)
        self.assertEquals(part.switchips, switchips)

        ctlrname = 'gru'
        credentials = "grupw"
        lcip = "10.10.10.30"
        switchips = ['10.10.10.31']

        part = man._get_controller(ctlrname)
        self.assertNotEqual(part, None)
        self.assertEquals(part.shortname, ctlrname)
        self.assertEquals(part.credentials, credentials)
        self.assertEquals(part.lcip, lcip)
        self.assertEquals(part.switchips, switchips)

    @mock.patch('sdxctlr.LocalControllerManager.AuthenticationInspector',
                autospec=True)
    def test_add_ctlr(self, authentication):
        self.logger.warning("BEGIN %s" % (self.id()))
        man = LocalControllerManager(manifest=CONFIG_FILE)


        
if __name__ == '__main__':
    unittest.main()
