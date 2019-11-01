# Copyright 2016 - Sean Donovan
# AtlanticWave/SDX Project


# Unit tests for the AuthorizationInspector class

import unittest
import threading
#import mock
import os

from sdxctlr.AuthorizationInspector import *


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
        
    def test_singleton(self):
        self.logger.warning("BEGIN %s" % (self.id()))
        firstInspector = AuthorizationInspector()
        secondInspector = AuthorizationInspector()

        self.failUnless(firstInspector is secondInspector)


#FIXME: This is boring because the AuthorizationInspector is boring right now.
#Once the AuthorizationInspector has been fleshed out, this should be as well.

if __name__ == '__main__':
    unittest.main()
