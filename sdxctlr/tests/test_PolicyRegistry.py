# Copyright 2016 - Sean Donovan
# AtlanticWave/SDX Project


# Unit tests for the PolicyRegistry class

import unittest
import threading
#import mock

from sdxctlr.PolicyRegistry import *


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
        
        firstRegistry = PolicyRegistry()
        secondRegistry = PolicyRegistry()

        self.assertTrue(firstRegistry is secondRegistry)

class AddingPoliciesTest(unittest.TestCase):
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
        
    def test_add_policytype(self):
        self.logger.warning("BEGIN %s" % (self.id()))
        
        class FakePolicyType(object):
            def __init__(self):
                self.status = "I am Fake!"
            @classmethod
            def get_policy_name(cls):
                return cls.__name__

        reg = PolicyRegistry()
        reg.add_policytype(FakePolicyType)
        retval = reg.get_policy_class("FakePolicyType")
        self.assertTrue(retval is FakePolicyType)
        reg.rm_policytype(FakePolicyType)

class NonPolicyTest(unittest.TestCase):
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
        
    def test_non_policytype(self):
        self.logger.warning("BEGIN %s" % (self.id()))
        
        reg = PolicyRegistry()
        self.assertRaises(PolicyRegistryTypeError,
                          reg.get_policy_class, "TotallyDoesNotExist")
        

class FindPoliciesTest(unittest.TestCase):
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
        
    def test_autopopulate(self):
        self.logger.warning("BEGIN %s" % (self.id()))
        
        reg = PolicyRegistry()
        print("Before find_policies()")
        reg.find_policies()
        print("After find_policies()")
        print(reg.get_list_of_policies())

if __name__ == '__main__':
    unittest.main()
