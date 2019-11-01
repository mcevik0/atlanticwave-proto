from __future__ import print_function
# Copyright 2016 - Sean Donovan
# AtlanticWave/SDX Project


# Unit tests for the BreakdownEngine class

import unittest
import threading
import networkx as nx
#import mock
import os
import logging

from shared.UserPolicy import UserPolicy
from sdxctlr.BreakdownEngine import *
from sdxctlr.TopologyManager import TopologyManager

TOPO_CONFIG_FILE = 'sdxctlr/tests/test_manifests/topo.manifest'
class UserPolicyStandin(UserPolicy):
    # Use the username as a return value 
    def __init__(self, username, json_policy):
        super(UserPolicyStandin, self).__init__(username, json_policy)
        self.retval = username
        print("retval = %s" % self.retval)
        
    def breakdown_policy(self, topology, authorization_func):
        # Verify that topology is a nx.Graph, and authorization_func is ???
        print("breakdown_policy called: %s:%s" % (authorization_func, topology))
        if not isinstance(topology, TopologyManager):
            print("- Raising Exception")
            raise Exception("Topology is not nx.Graph")
        if self.retval == True:
            print("- Success")
            return "Success"
        raise Exception("BAD")
    def _parse_json(self, json_policy):
        return
    

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

        topo = TopologyManager(topology_file=TOPO_CONFIG_FILE)
        first = BreakdownEngine()
        second =  BreakdownEngine()

        self.failUnless(first is second)
        del topo

#FIXME: Nothing's mocked here!

class BreakdownTest(unittest.TestCase):
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
        
    def test_good_valid(self):
        self.logger.warning("BEGIN %s" % (self.id()))

        valid_policy = UserPolicyStandin(True, "")
        topo = TopologyManager(topology_file=TOPO_CONFIG_FILE)
        engine = BreakdownEngine()
        self.assertEquals(engine.get_breakdown(valid_policy), "Success")
        del topo
                        
    def test_bad_valid(self):
        self.logger.warning("BEGIN %s" % (self.id()))
        invalid_policy = UserPolicyStandin(False, "")
        topo = TopologyManager(topology_file=TOPO_CONFIG_FILE)
                               
        engine = BreakdownEngine(CATCH_ERRORS=False)
        self.failUnlessRaises(Exception, engine.get_breakdown, invalid_policy)
        del engine


if __name__ == '__main__':
    unittest.main()
