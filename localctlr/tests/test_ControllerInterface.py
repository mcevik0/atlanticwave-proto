# Copyright 2019 - Sean Donovan
# AtlanticWave/SDX Project


# Unittests for localctlr/ControllerInterface class

import unittest
import logging
import os
from localctlr.ControllerInterface import *

class BasicTests(unittest.TestCase):
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

    def test_init(self):
        self.logger.warning("BEGIN %s" % (self.id()))
        ctlr = ControllerInterface("test")
        
    def test_send_command(self):
        self.logger.warning("BEGIN %s" % (self.id()))
        ctlr = ControllerInterface("test")
        self.failUnlessRaises(NotImplementedError, ctlr.send_command,
                              'test', 'test')

    def test_remove_rule(self):
        self.logger.warning("BEGIN %s" % (self.id()))
        ctlr = ControllerInterface("test")
        self.failUnlessRaises(NotImplementedError, ctlr.remove_rule,
                              'test', 'test')
        


        
if __name__ == '__main__':
    unittest.main()
