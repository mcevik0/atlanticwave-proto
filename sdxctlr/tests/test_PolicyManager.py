from __future__ import print_function
# Copyright 2016 - Sean Donovan
# AtlanticWave/SDX Project


# Unit tests for the PolicyManager class

import unittest
import threading
import networkx as nx
#import mock
import dataset
import os
import logging

from sdxctlr.PolicyManager import *
from shared.UserPolicy import *
from sdxctlr.TopologyManager import TopologyManager


TOPO_CONFIG_FILE = 'test_manifests/topo.manifest'
db = ':memory:'
dbcxn = dataset.connect("sqlite:///"+db,
                        engine_kwargs={'connect_args':
                                       {'check_same_thread':False}})
def rmhappy(param):
    pass

class PolicyStandin(object):
    def __init__(self, name):
        self.name = name
    def __str__(self):
        return "PolicyStandin %s" % self.name
    def set_cookie(self, cookie):
        return

class UserPolicyStandin(UserPolicy):
    # Use the username as a return value for checking validity.
    def __init__(self, username, json_policy):
        super(UserPolicyStandin, self).__init__(username, json_policy)
        self.valid = username
        self.breakdown = json_policy
        
    def check_validity(self, topology, authorization_func):
        # Verify that topology is a nx.Graph, and authorization_func is ???
        if not isinstance(topology, nx.Graph):
            raise Exception("Topology is not nx.Graph")
        if self.valid == True:
            return True
        raise Exception("NOT VALID")
    
    def breakdown_policy(self, topology, authorization_func):
        # Verify that topology is a nx.Graph, and authorization_func is ???
        if not isinstance(topology, TopologyManager):
            print("- Raising Exception")
            raise Exception("Topology is not nx.Graph")
        if self.breakdown == True:
            return [UserPolicyBreakdown("1.2.3.4",
                                        [PolicyStandin("policy1"),
                                         PolicyStandin("policy2")])]
        raise Exception("NO BREAKDOWN")
    
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
        firstManager = PolicyManager(db, 'sdxcontroller', rmhappy, rmhappy)
        secondManager = PolicyManager(db, 'sdxcontroller', rmhappy, rmhappy)

        self.failUnless(firstManager is secondManager)

class AddPolicyTest(unittest.TestCase):
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
        
    def test_good_test_add_policy(self):
        self.logger.warning("BEGIN %s" % (self.id()))

        topo = TopologyManager(topology_file=TOPO_CONFIG_FILE)
        man = PolicyManager(db, 'sdxcontroller', rmhappy, rmhappy)
        valid_policy = UserPolicyStandin(True, True)

        #FIXME
        man.test_add_policy(valid_policy)

    def test_invalid_test_add_policy(self):
        self.logger.warning("BEGIN %s" % (self.id()))

        topo = TopologyManager(topology_file=TOPO_CONFIG_FILE)
        man = PolicyManager(db, 'sdxcontroller', rmhappy, rmhappy)
        invalid_policy = UserPolicyStandin(False, True)

        self.failUnlessRaises(Exception,
                              man.test_add_policy, invalid_policy)

    def test_no_breakdown_test_add_policy(self):
        self.logger.warning("BEGIN %s" % (self.id()))

        topo = TopologyManager(topology_file=TOPO_CONFIG_FILE)
        man = PolicyManager(db, 'sdxcontroller', rmhappy, rmhappy)
        invalid_policy = UserPolicyStandin(True, False)

        self.failUnlessRaises(Exception,
                              man.test_add_policy, invalid_policy)

    def test_good_add_policy(self):
        self.logger.warning("BEGIN %s" % (self.id()))

        topo = TopologyManager(topology_file=TOPO_CONFIG_FILE)
        man = PolicyManager(db, 'sdxcontroller', rmhappy, rmhappy)
        valid_policy = UserPolicyStandin(True, True)

#        print(man.add_policy(valid_policy))
        self.failUnless(isinstance(man.add_policy(valid_policy), int))

    def test_invalid_add_policy(self):
        self.logger.warning("BEGIN %s" % (self.id()))

        topo = TopologyManager(topology_file=TOPO_CONFIG_FILE)
        man = PolicyManager(db, 'sdxcontroller', rmhappy, rmhappy)
        invalid_policy = UserPolicyStandin(False, True)

        self.failUnlessRaises(Exception,
                              man.add_policy, invalid_policy)

    def test_no_breakdown_add_policy(self):
        self.logger.warning("BEGIN %s" % (self.id()))

        topo = TopologyManager(topology_file=TOPO_CONFIG_FILE)
        man = PolicyManager(db, 'sdxcontroller', rmhappy, rmhappy)
        invalid_policy = UserPolicyStandin(True, False)

        self.failUnlessRaises(Exception,
                              man.add_policy, invalid_policy)

class RemovePolicyTest(unittest.TestCase):
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
        
    def test_good_remove_policy(self):
        self.logger.warning("BEGIN %s" % (self.id()))

        topo = TopologyManager(topology_file=TOPO_CONFIG_FILE)
        man = PolicyManager(db, 'sdxcontroller', rmhappy, rmhappy)
        valid_policy = UserPolicyStandin(True, True)

        #FIXME
        hash = man.add_policy(valid_policy)
        man.get_policy_details(hash)
        self.failUnless(man.get_policy_details(hash) != None)

        man.remove_policy(hash, "dummy_user")
        self.failUnless(man.get_policy_details(hash) == None)

class GetPolicies(unittest.TestCase):
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
        
    def test_get_policies(self):
        self.logger.warning("BEGIN %s" % (self.id()))

        topo = TopologyManager(topology_file=TOPO_CONFIG_FILE)
        man = PolicyManager(db, 'sdxcontroller', rmhappy, rmhappy)
        valid_policy = UserPolicyStandin(True, True)

        hash = man.add_policy(valid_policy)
        self.failUnless(man.get_policies() != [])


class RemoveAllPolicies(unittest.TestCase):
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
        
    def test_remove_all_policies(self):
        self.logger.warning("BEGIN %s" % (self.id()))

        topo = TopologyManager(topology_file=TOPO_CONFIG_FILE)
        man = PolicyManager(db, 'sdxcontroller', rmhappy, rmhappy)
        valid_policy = UserPolicyStandin(True, True)

        # Add a policy.
        man.add_policy(valid_policy)

        self.failUnless(man.get_policies() != [])
        
        man.remove_all_policies("dummy_user")

        policies = man.get_policies()
        self.failUnless(man.get_policies() == [])

        
if __name__ == '__main__':
    unittest.main()
