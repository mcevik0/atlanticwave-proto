# Copyright 2016 - Sean Donovan
# AtlanticWave/SDX Project


# Unit tests for the ValidityInspector class

import unittest
import threading
import networkx as nx
#import mock

from shared.UserPolicy import UserPolicy
from sdxctlr.ValidityInspector import *
from sdxctlr.TopologyManager import TopologyManager

TOPO_CONFIG_FILE = 'sdxctlr/tests/test_manifests/topo.manifest'
class UserPolicyStandin(UserPolicy):
    # Use the username as a return value for checking validity.
    def __init__(self, username, json_policy):
        super(UserPolicyStandin, self).__init__(username, json_policy)
        self.retval = username
        
    def check_validity(self, topology, authorization_func):
        # Verify that topology is a nx.Graph, and authorization_func is ???
        if not isinstance(topology, nx.Graph):
            raise Exception("Topology is not nx.Graph (%s)" % topology)
        if self.retval == True:
            return True
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
        firstInspector = ValidityInspector()
        secondInspector = ValidityInspector()

        self.failUnless(firstInspector is secondInspector)

#FIXME: Nothing's mocked here!

class ValidityTest(unittest.TestCase):
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
        inspector = ValidityInspector()
        self.failUnless(inspector.is_valid_policy(valid_policy))
                        
    def test_bad_valid(self):
        self.logger.warning("BEGIN %s" % (self.id()))

        invalid_policy = UserPolicyStandin(False, "")
        inspector = ValidityInspector()
        self.failUnlessRaises(Exception, inspector.is_valid_policy,
                              invalid_policy)

if __name__ == '__main__':
    unittest.main()
