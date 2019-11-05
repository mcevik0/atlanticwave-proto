from __future__ import print_function
# Copyright 2016 - Sean Donovan
# AtlanticWave/SDX Project


# Unit tests for the TopologyManager class

import unittest
import threading
#import mock
import networkx as nx
import logging
import os

from sdxctlr.TopologyManager import *

CONFIG_FILE = 'sdxctlr/tests/test_manifests/topo.manifest'
STEINER_NO_LOOP_CONFIG_FILE = 'sdxctlr/tests/test_manifests/steiner-noloop.manifest'
STEINER_LOOP_CONFIG_FILE = 'sdxctlr/tests/test_manifests/steiner-loop.manifest'

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

        firstManager = TopologyManager(topology_file=CONFIG_FILE) 
        secondManager = TopologyManager(topology_file=CONFIG_FILE)

        self.failUnless(firstManager is secondManager)

class VerifyTopoTest(unittest.TestCase):
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
        
    def setUp(self):
        man = TopologyManager(topology_file=CONFIG_FILE)
        man.topo = nx.Graph()
        man._import_topology(CONFIG_FILE)
        
    def test_get_topo(self):
        self.logger.warning("BEGIN %s" % (self.id()))

        man = TopologyManager(topology_file=CONFIG_FILE)
        topo = man.get_topology()
        self.failUnless(isinstance(topo, nx.Graph))
        
    def test_simple_topo(self):
        self.logger.warning("BEGIN %s" % (self.id()))

        man = TopologyManager(topology_file=CONFIG_FILE)
        topo = man.get_topology()

        expected_nodes = ['br1', 'br2', 'br3', 'br4',
                          'br1dtn1', 'br1dtn2',
                          'br2dtn1', 'br2dtn2', 'br2dtn3',
                          'br3dtn1',
                          'br4dtn1', 'br4dtn2',
                          'oneLC'] # The LC counts as a node, just in case.
        nodes = topo.nodes()
        #print("\nNODES : %s" % nodes)
        #print("EXPECT: %s" % expected_nodes)
        self.assertEquals(len(nodes), len(expected_nodes))
        for node in expected_nodes:
            self.failUnless(node in nodes)

        #FIXME: Need to look at details! In the future, anyway.

        # Should contain
        expected_edges = [
            ('br1', 'br1dtn1'), ('br1', 'br1dtn2'),
            ('br2', 'br2dtn1'), ('br2', 'br2dtn2'), ('br2', 'br2dtn3'),
            ('br3', 'br3dtn1'),
            ('br4', 'br4dtn1'), ('br4', 'br4dtn2'),
            ('br1', 'br2'), ('br1', 'br3'),
            ('br2', 'br3'),
            ('br3', 'br4')]
        edges = topo.edges()

        self.failUnless(len(edges) == len(expected_edges))
        for edge in expected_edges:
            (a, b) = edge
            reversed_edge = (b,a)
            # We don't care about ordering of the edges)
            # Both options below end up with same result.
            self.failUnless((edge in edges) or (reversed_edge in edges))
            self.failUnless(topo.has_edge(a, b))

        #import json
        #print(json.dumps(topo.nodes(data=True), indent=1))
        #print("\n\n")
        #print(json.dumps(topo.edges(data=True), indent=1))


class VLANTopoTest(unittest.TestCase):
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
        
    def setUp(self):
        man = TopologyManager(topology_file=CONFIG_FILE)
        man.topo = nx.Graph()
        man._import_topology(CONFIG_FILE)
        
    
    def test_path_empty(self):
        self.logger.warning("BEGIN %s" % (self.id()))

        man = TopologyManager(topology_file=CONFIG_FILE)
        topo = man.get_topology()

        # Get a path
        path = nx.shortest_path(topo, source="br1", target="br4")
        
        # It should return 1
        vlan = man.find_vlan_on_path(path)
        self.failUnlessEqual(vlan, 1)

    def test_path_with_node_set(self):
        self.logger.warning("BEGIN %s" % (self.id()))

        man = TopologyManager(topology_file=CONFIG_FILE)
        topo = man.get_topology()

        # Get a path
        path = nx.shortest_path(topo, source="br4", target="br3")

        # Should return 1
        vlan = man.find_vlan_on_path(path)
        self.assertEqual(vlan, 1)

        # Add VLAN 1 to one of the points on the path
        man.topo.node["br4"]['vlans_in_use'].append(1)
        
        # Should return 2
        vlan = man.find_vlan_on_path(path)
        self.assertEqual(vlan, 2)
        man.topo.node["br4"]['vlans_in_use'].remove(1)

    def test_path_with_edge_set(self):
        self.logger.warning("BEGIN %s" % (self.id()))

        man = TopologyManager(topology_file=CONFIG_FILE)
        topo = man.get_topology()

        # Get a path
        path = nx.shortest_path(topo, source="br2", target="br4")

        # Should return 1
        vlan = man.find_vlan_on_path(path)
        self.assertEqual(vlan, 1)
        
        # Add VLAN 1 to one of the points on the path
        print("\n%s" % man.topo.edge['br3']['br4'])
        man.topo.edge["br3"]["br4"]['vlans_in_use'].append(1)
        print(man.topo.edge['br3']['br4'])
        
        # Should return 2
        vlan = man.find_vlan_on_path(path)
        self.assertEqual(vlan, 2)
        man.topo.edge["br3"]["br4"]['vlans_in_use'].remove(1)

    def test_path_node_filled(self):
        self.logger.warning("BEGIN %s" % (self.id()))

        man = TopologyManager(topology_file=CONFIG_FILE)
        topo = man.get_topology()

        # Get a path
        path = nx.shortest_path(topo, source="br4", target="br3")

        # Should return 1
        vlan = man.find_vlan_on_path(path)
        self.failUnlessEqual(vlan, 1)
        
        # Add VLANs 1-4090 to one of the points on the path        
        man.topo.node["br4"]['vlans_in_use'] = range(1,4090)
        
        # Should return None
        vlan = man.find_vlan_on_path(path)
        self.failUnlessEqual(vlan, None)
        man.topo.node["br4"]['vlans_in_use'] = []


    def test_path_edge_filled(self):
        self.logger.warning("BEGIN %s" % (self.id()))

        man = TopologyManager(topology_file=CONFIG_FILE)
        topo = man.get_topology()

        # Get a path
        path = nx.shortest_path(topo, source="br4", target="br1")

        # Should return 1
        vlan = man.find_vlan_on_path(path)
        self.failUnlessEqual(vlan, 1)
        
        # Add VLANs 1-4090 to one of the points on the path        
        man.topo.edge["br4"]["br3"]['vlans_in_use'] = range(1,4090)
        # Should return None
        vlan = man.find_vlan_on_path(path)
        self.failUnlessEqual(vlan, None)
        man.topo.edge["br4"]["br3"]['vlans_in_use'] = []

    def test_reserve_on_empty(self):
        self.logger.warning("BEGIN %s" % (self.id()))

        man = TopologyManager(topology_file=CONFIG_FILE)
        topo = man.get_topology()

        # Get a path
        path = nx.shortest_path(topo, source="br4", target="br1")

        # Reserve path on VLAN 1
        man.reserve_vlan_on_path(path, 1)
        # Should work

    def test_reserve_on_invalid(self):
        self.logger.warning("BEGIN %s" % (self.id()))

        # Get a path
        man = TopologyManager(topology_file=CONFIG_FILE)
        topo = man.get_topology()

        # Get a path
        path = nx.shortest_path(topo, source="br4", target="br1")
        
        # set VLAN 1 on one of the points on the path
        man.topo.edge["br4"]["br3"]['vlans_in_use'].append(1)

        # Reserve path on VLAN 1
        self.failUnlessRaises(Exception, man.reserve_vlan_on_path, path, 1)
        # Should throw an exception

    def test_unreserve_vlan(self):
        self.logger.warning("BEGIN %s" % (self.id()))

        # Get a path
        man = TopologyManager(topology_file=CONFIG_FILE)
        topo = man.get_topology()

        # Get a path
        path = nx.shortest_path(topo, source="br4", target="br3")
        
        # Reserve path on VLAN 100
        man.reserve_vlan_on_path(path, 100)

        # Reserve path on VLAN 100
        self.failUnlessRaises(Exception, man.reserve_vlan_on_path, path, 100)
        # Should throw an exception

        # Unreserve path
        man.unreserve_vlan_on_path(path, 100)

        # This should pass:
        man.reserve_vlan_on_path(path, 100)


class BWTopoTest(unittest.TestCase):
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
        
    def setUp(self):
        man = TopologyManager(topology_file=CONFIG_FILE)
        man.topo = nx.Graph()
        man._import_topology(CONFIG_FILE)
        
    def test_valid_reservation(self):
        self.logger.warning("BEGIN %s" % (self.id()))

        man = TopologyManager(topology_file=CONFIG_FILE)
        topo = man.get_topology()

        # Get a path
        path = nx.shortest_path(topo, source="br4", target="br1")

        man.reserve_bw_on_path(path, 100)
        man.reserve_bw_on_path(path, 100)
        man.reserve_bw_on_path(path, 100)
        
    def test_reserve_maximum(self):
        self.logger.warning("BEGIN %s" % (self.id()))

        man = TopologyManager(topology_file=CONFIG_FILE)
        topo = man.get_topology()

        # Get a path
        path = nx.shortest_path(topo, source="br4", target="br3")

        man.reserve_bw_on_path(path, 8000000000)
        man.unreserve_bw_on_path(path, 8000000000)

    def test_reserve_too_much(self):
        self.logger.warning("BEGIN %s" % (self.id()))

        man = TopologyManager(topology_file=CONFIG_FILE)
        topo = man.get_topology()

        # Get a path
        path = nx.shortest_path(topo, source="br4", target="br2")

        self.failUnlessRaises(Exception, man.reserve_bw_on_path, path, 
                              8000000001)

    def test_unreserve_reservation(self):
        self.logger.warning("BEGIN %s" % (self.id()))

        man = TopologyManager(topology_file=CONFIG_FILE)
        topo = man.get_topology()

        # Get a path
        path = nx.shortest_path(topo, source="br4", target="br1")

        man.reserve_bw_on_path(path, 100)
        man.reserve_bw_on_path(path, 100)
        man.reserve_bw_on_path(path, 100)

        man.unreserve_bw_on_path(path, 100)
        man.unreserve_bw_on_path(path, 100)
        man.unreserve_bw_on_path(path, 100)

    def test_unreserve_too_much(self):
        self.logger.warning("BEGIN %s" % (self.id()))

        man = TopologyManager(topology_file=CONFIG_FILE)
        topo = man.get_topology()

        # Get a path
        path = nx.shortest_path(topo, source="br4", target="br3")

        man.reserve_bw_on_path(path, 100)
        man.unreserve_bw_on_path(path, 100)
        
        self.failUnlessRaises(Exception, man.unreserve_bw_on_path, path, 100)

        man.reserve_bw_on_path(path, 100)
        self.failUnlessRaises(Exception, man.unreserve_bw_on_path, path, 200)

 
class SteinerTreeNoLoopTest(unittest.TestCase):
    ''' +-----+   +-----+   +-----+
        | sw1 |   | sw4 |   | sw6 |
        +--+--+   +--+--+   +--+--+
           |         |         |
        +--+--+   +--+--+   +--+--+
        | sw2 +---+ sw5 +---+ sw7 |
        +--+--+   +-----+   +--+--+
           |                   |
        +--+--+             +--+--+
        | sw3 |             | sw8 |
        +-----+             +-----+
    '''

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
        
    def setUp(self):
        man = TopologyManager(topology_file=STEINER_NO_LOOP_CONFIG_FILE)
        man.topo = nx.Graph()
        man._import_topology(STEINER_NO_LOOP_CONFIG_FILE)

    def test_steiner_tree_no_loop(self):
        self.logger.warning("BEGIN %s" % (self.id()))

        man = TopologyManager(topology_file=STEINER_NO_LOOP_CONFIG_FILE)
        topo = man.get_topology()
        
        # Get a tree connecting sw1, sw8, and sw6
        nodes = ['sw1', 'sw8', 'sw6']
        tree = man.find_valid_steiner_tree(nodes)
        expected_tree_nodes = ["sw1", "sw2", "sw5", "sw6", "sw7", "sw8"]
        returned_tree_nodes = tree.nodes()
        self.failUnlessEqual(len(expected_tree_nodes), 
                             len(returned_tree_nodes))
        for node in expected_tree_nodes:
            self.failUnless(node in returned_tree_nodes)

        # Get a tree connecting sw4, sw8, and sw6
        nodes = ["sw4", "sw6", "sw8"]
        tree = man.find_valid_steiner_tree(nodes)
        expected_tree_nodes = ["sw4", "sw5", "sw6", "sw7", "sw8"]
        returned_tree_nodes = tree.nodes()
        self.failUnlessEqual(len(expected_tree_nodes), 
                             len(returned_tree_nodes))
        for node in expected_tree_nodes:
            self.failUnless(node in returned_tree_nodes)

    def test_find_vlan(self):
        self.logger.warning("BEGIN %s" % (self.id()))

        man = TopologyManager(topology_file=STEINER_NO_LOOP_CONFIG_FILE)
        topo = man.get_topology()
        
        # Get a tree connecting sw1, sw8, and sw6
        nodes = ['sw1', 'sw8', 'sw6']
        tree = man.find_valid_steiner_tree(nodes)

        # Should work
        vlan = man.find_vlan_on_tree(tree)
    
    def test_reserve_vlan(self):
        self.logger.warning("BEGIN %s" % (self.id()))

        man = TopologyManager(topology_file=STEINER_NO_LOOP_CONFIG_FILE)
        topo = man.get_topology()
        
        # Get a tree connecting sw1, sw8, and sw6
        nodes = ['sw1', 'sw8', 'sw6']
        tree = man.find_valid_steiner_tree(nodes)

        # Should work
        vlan = man.find_vlan_on_tree(tree)

        # Should work
        man.reserve_vlan_on_tree(tree, vlan)

    def test_unreserve_vlan(self):
        self.logger.warning("BEGIN %s" % (self.id()))

        man = TopologyManager(topology_file=STEINER_NO_LOOP_CONFIG_FILE)
        topo = man.get_topology()
        
        # Get a tree connecting sw1, sw8, and sw6
        nodes = ['sw1', 'sw8', 'sw6']
        tree = man.find_valid_steiner_tree(nodes)

        # Should work
        vlan = man.find_vlan_on_tree(tree)

        # Should work
        man.reserve_vlan_on_tree(tree, vlan)

        # Should work
        man.unreserve_vlan_on_tree(tree, vlan)

        # Should work
        man.reserve_vlan_on_tree(tree, vlan)

    def test_reserve_on_invalid(self):
        self.logger.warning("BEGIN %s" % (self.id()))

        man = TopologyManager(topology_file=STEINER_NO_LOOP_CONFIG_FILE)
        topo = man.get_topology()
        
        # Get a tree connecting sw1, sw8, and sw6
        nodes = ['sw1', 'sw8', 'sw6']
        tree = man.find_valid_steiner_tree(nodes)

        # Should work
        vlan = man.find_vlan_on_tree(tree)

        # Should work
        man.reserve_vlan_on_tree(tree, vlan)

        # Should work
        self.failUnlessRaises(Exception, man.reserve_vlan_on_tree, tree, vlan)

    def test_reserve_bandwidth(self):
        self.logger.warning("BEGIN %s" % (self.id()))

        man = TopologyManager(topology_file=STEINER_NO_LOOP_CONFIG_FILE)

        # Get a tree connecting sw1, sw8, and sw6
        nodes = ['sw1', 'sw8', 'sw6']
        tree = man.find_valid_steiner_tree(nodes)

        # Should work
        man.reserve_bw_on_tree(tree, 100)
        man.reserve_bw_on_tree(tree, 100)
        man.reserve_bw_on_tree(tree, 100)        
        man.unreserve_bw_on_tree(tree, 100)
        man.unreserve_bw_on_tree(tree, 100)
        man.unreserve_bw_on_tree(tree, 100)        


    def test_reserve_maximum(self):
        self.logger.warning("BEGIN %s" % (self.id()))

        man = TopologyManager(topology_file=STEINER_NO_LOOP_CONFIG_FILE)

        # Get a tree connecting sw1, sw8, and sw6
        nodes = ['sw1', 'sw8', 'sw6']
        tree = man.find_valid_steiner_tree(nodes)

        # Should work
        man.reserve_bw_on_tree(tree, 80000000000)
        man.unreserve_bw_on_tree(tree, 80000000000)

    def test_reserve_too_much(self):
        self.logger.warning("BEGIN %s" % (self.id()))

        man = TopologyManager(topology_file=STEINER_NO_LOOP_CONFIG_FILE)

        # Get a tree connecting sw1, sw8, and sw6
        nodes = ['sw1', 'sw8', 'sw6']
        tree = man.find_valid_steiner_tree(nodes)

        # Should work
        self.failUnlessRaises(Exception, man.reserve_bw_on_tree, tree, 
                              80000000001)

    def test_unreserve_bw(self):
        self.logger.warning("BEGIN %s" % (self.id()))

        man = TopologyManager(topology_file=STEINER_NO_LOOP_CONFIG_FILE)

        # Get a tree connecting sw1, sw8, and sw6
        nodes = ['sw1', 'sw8', 'sw6']
        tree = man.find_valid_steiner_tree(nodes)

        # Should work
        man.reserve_bw_on_tree(tree, 100)
        man.reserve_bw_on_tree(tree, 100)
        man.reserve_bw_on_tree(tree, 100)        

        # Should work
        man.unreserve_bw_on_tree(tree, 100)
        man.unreserve_bw_on_tree(tree, 100)
        man.unreserve_bw_on_tree(tree, 100)        

    def test_unreserve_too_much(self):
        self.logger.warning("BEGIN %s" % (self.id()))

        man = TopologyManager(topology_file=STEINER_NO_LOOP_CONFIG_FILE)

        # Get a tree connecting sw1, sw8, and sw6
        nodes = ['sw1', 'sw8', 'sw6']
        tree = man.find_valid_steiner_tree(nodes)

        # Should work
        man.reserve_bw_on_tree(tree, 100)
        man.unreserve_bw_on_tree(tree, 100)

        self.failUnlessRaises(Exception, man.unreserve_bw_on_tree, tree, 100)

        man.reserve_bw_on_tree(tree, 100)
        self.failUnlessRaises(Exception, man.unreserve_bw_on_tree, tree, 200)
        man.unreserve_bw_on_tree(tree, 100)

    


class SteinerTreeWithLoopTest(unittest.TestCase):
    ''' +-----+   +-----+   +-----+
        | sw1 |   | sw4 +---+ sw6 |
        +--+--+   +--+--+   +--+--+
           |         |         |
        +--+--+   +--+--+   +--+--+
        | sw2 +---+ sw5 +---+ sw7 |
        +--+--+   +-----+   +--+--+
           |                   |
        +--+--+             +--+--+
        | sw3 +-------------+ sw8 |
        +-----+             +-----+
    '''
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
        
    def setUp(self):
        man = TopologyManager(topology_file=STEINER_LOOP_CONFIG_FILE)
        man.topo = nx.Graph()
        man._import_topology(STEINER_LOOP_CONFIG_FILE)

    def test_steiner_tree_with_loop(self):
        self.logger.warning("BEGIN %s" % (self.id()))

        man = TopologyManager(topology_file=STEINER_LOOP_CONFIG_FILE)
        topo = man.get_topology()
        
        # Get a tree connecting sw1, sw4, and sw7
        nodes = ['sw1', 'sw4', 'sw7']
        tree = man.find_valid_steiner_tree(nodes)
        expected_tree_nodes = ["sw1", "sw2", "sw5", "sw4", "sw7"]
        returned_tree_nodes = tree.nodes()
        self.failUnlessEqual(len(expected_tree_nodes), 
                             len(returned_tree_nodes))
        for node in expected_tree_nodes:
            self.failUnless(node in returned_tree_nodes)

        # Get a tree connecting sw1, sw3, sw8, sw6
        nodes = ["sw1", "sw3", "sw6", "sw8"]
        tree = man.find_valid_steiner_tree(nodes)
        expected_tree_nodes = ["sw1", "sw2", "sw3", "sw8", "sw7", "sw6"]
        returned_tree_nodes = tree.nodes()
        self.failUnlessEqual(len(expected_tree_nodes), 
                             len(returned_tree_nodes))
        for node in expected_tree_nodes:
            self.failUnless(node in returned_tree_nodes)

        # Get a tree connecting sw1, sw3, sw8
        nodes = ["sw1", "sw3", "sw8"]
        tree = man.find_valid_steiner_tree(nodes)
        expected_tree_nodes = ["sw1", "sw2", "sw3", "sw8"]
        returned_tree_nodes = tree.nodes()
        self.failUnlessEqual(len(expected_tree_nodes), 
                             len(returned_tree_nodes))
        for node in expected_tree_nodes:
            self.failUnless(node in returned_tree_nodes)




if __name__ == '__main__':
    unittest.main()
