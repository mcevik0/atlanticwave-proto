from __future__ import print_function
from __future__ import absolute_import
# Copyright 2018 - Sean Donovan
# AtlanticWave/SDX Project

# Some parts are based on the Sense Resource Manager for the OSCARS interface:
# https://bitbucket.org/berkeleylab/sensenrm-oscars/src/d09db31aecbe7654f03f15eed671c0675c5317b5/sensenrm_server.py

from lib.AtlanticWaveManager import AtlanticWaveManager

from shared.L2MultipointPolicy import L2MultipointPolicy
from shared.L2TunnelPolicy import L2TunnelPolicy

from .AuthenticationInspector import AuthenticationInspector
from .AuthorizationInspector import AuthorizationInspector
from .PolicyManager import PolicyManager, PolicyManagerError
from sdxctlr.TopologyManager import TopologyManager, TOPO_EDGE_TYPE
from .UserManager import UserManager

from threading import Lock
import rdflib
from rdflib.util import list2set

import sys
if sys.version_info[0] < 3:
    import cPickle as pickle
else:
    import pickle


# Flask imports
from flask import Flask, jsonify, abort, make_response, request
from flask_restful import Api, Resource, reqparse, fields, marshal
import ssl

# Other imports
import networkx as nx
from networkx.readwrite import json_graph
import json
import zlib
import base64
import uuid

# Multithreading
from threading import Thread

# Timing
from datetime import datetime, timedelta, tzinfo
from shared.constants import rfc3339format, MAXENDTIME
#FIXME - sensetimeformat should be updated for Python3 to include %z
sensetimeformat = "%Y-%m-%dT%H:%M:%S.%f" 

# Globals
errors = {
    'NotFound': {
        'message': "A resource with that ID does not exist.",
        'status': 404,
        'extra': "No extra information",
    },
}

# HTTP status codes:
HTTP_GOOD           = 200
HTTP_CREATED        = 201
HTTP_ACCEPTED       = 202
HTTP_NO_CONTENT     = 204
HTTP_NOT_MODIFIED   = 304
HTTP_BAD_REQUEST    = 400
HTTP_FORBIDDEN      = 403     # RETURNED BY FLASK-RESTFUL ONLY
HTTP_NOT_FOUND      = 404
HTTP_NOT_ACCEPTABLE = 406
HTTP_CONFLICT       = 409
HTTP_SERVER_ERROR   = 500     # RETURNED BY FLASK-RESTFUL ONLY

# SENSE status codes
STATUS_ACCEPTING    = "ACCEPTING"
STATUS_ACCEPTED     = "ACCEPTED"
STATUS_COMMITTING   = "COMMITTING"
STATUS_COMMITTED    = "COMMITTED"
STATUS_ACTIVATING   = "ACTIVATING"
STATUS_ACTIVATED    = "ACTIVATED"
STATUS_FAILED       = "FAILED"

# PHASE definition
PHASE_RESERVED        = "RESERVED"
PHASE_COMMITTED       = "COMMITTED"

# URN info
baseurn = "urn:ogf:network:"
fullurn = baseurn + "atlanticwave-sdx.net"
awaveurn = "urn:ogf:network:atlanticwave-sdx.net"


class SenseAPIError(Exception):
    pass

class SenseAPIB64Error(SenseAPIError):
    ''' For Base64-related errors. Usually debug errors. '''
    pass

class SenseAPIClientError(SenseAPIError):
    ''' Catch all for Client-side errors. Likley has subclasses. '''
    pass

class SenseAPIArgumentError(SenseAPIClientError):
    ''' For errors with arguments being passed in. '''
    pass

        


class SenseAPI(AtlanticWaveManager):
    ''' The SenseAPI is the main interface for SENSE integration. It generates
        the appropriate XML for the current configuration status, and sends 
        updates automatically based on changes in SENSE requests and topology 
        as provided by the PolicyManager and TopologyManager.
    '''
    # Delta Database entries:
    # {"delta_id":delta_id,
    #  "raw_request": raw_addition (pickled in DB),
    #  "addition": addition in db (pickled in DB),
    #  "reduction": reduction in db (pickled in DB),
    #  "status": status code (see list, below),
    #  "last_modified": last modified time,
    #  "timestamp": initial timestamp of the delta,
    #  "model_id": Model ID}

    # Model Database entries:
    # {"model_id": Model ID (UUID),
    #  "model_data": XML that was sent over,
    #  "model_raw_info": raw topology information (pickled in DB),
    #  "timestamp": Timestamp of model}

    # Hash Database entries:
    # {"hash": Hash from the PolicyManager returned on installing a policy,
    #  "policy": Policy that's installed,
    #  "delta_id": Delta ID associated with the policy}

    def __init__(self, db_filename, loggerprefix='sdxcontroller',
                 host='0.0.0.0', port=5002):
        global app, api, context

        loggerid = loggerprefix + ".sense"
        super(SenseAPI, self).__init__(loggerid)

        # For FLASK
        self.host = host
        self.port = port
        self.urlbase = "http://%s:%s" % (host, port)

        # SENSE Service constants
        self.SVC_SENSE          = "l2switching"
        self.SVC_SENSE_L2P2P    = "l2switching"
        self.SVC_SENSE_L2MP     = "l2mp"
        self.SVC_NONSENSE       = "ServiceDomain:AWaveServices"
        
        # Set up local repositories for policies and topology to perform diffs
        # on.
        self.current_policies = PolicyManager().get_policies()
        self.current_topo = TopologyManager().get_topology()
        self.simplified_topo = None
        self.list_of_services = None
        self.topo_XML = None
        self.delta_XML = None
        self.topolock = Lock()
        self.userid = "SENSE"

        # Start database
        db_tuples = [('delta_table','delta'),
                     ('model_table', 'model'),
                     ('hash_table','hash')]
        self._initialize_db(db_filename, db_tuples, True)
        self._sanitize_db()
        
        # Register update functions
        PolicyManager().register_for_policy_updates(self.policy_add_callback,
                                                    self.policy_rm_callback)
        TopologyManager().register_for_topology_updates(
            self.topo_change_callback)

        # Flask setup
        #FIXME: SSL
        #context = ssl.SSLContext(ssl.PROTOCOL_TLSv1_2) 
        #context.load_verify_locations(capath=ssl_config["capath"])
        #context.load_cert_chain(ssl_config["hostcertpath"],
        #                        ssl_config["hostkeypath"])
        # sss._https_verify_certificates(enable=ssl_config["httpsverify"])
        app = Flask(__name__)
        api = Api(app, errors=errors)
        api.add_resource(ModelsAPI,
            '/sense-rm/api/sense/v1/models',
            endpoint='models',
            resource_class_kwargs={'urlbase':self.urlbase})
        api.add_resource(DeltasAPI,
            '/sense-rm/api/sense/v1/deltas',
            endpoint='deltas',
            resource_class_kwargs={'urlbase':self.urlbase})
        api.add_resource(DeltaAPI,
            '/sense-rm/api/sense/v1/deltas/<string:deltaid>',
            endpoint='delta',
            resource_class_kwargs={'urlbase':self.urlbase})
        api.add_resource(CommitsAPI,
            '/sense-rm/api/sense/v1/deltas/<string:deltaid>/actions/commit',
            endpoint='commits',
            resource_class_kwargs={'urlbase':self.urlbase})

        
        self.generate_simplified_topology()
                
        # Connection handling
        #FIXME - Is it inbound or outbound?

        api_thread = Thread(target=self.api_process)
        api_thread.daemon = True
        api_thread.start()
        self.logger.critical("Opening socket %s:%s" % (self.host, self.port))

        self.logger.warning("%s initialized: %s" % (self.__class__.__name__,
                                                    hex(id(self))))





    def __DEBUG_print_lots_of_details(self):
        print("\n\n\n\n")
        self.__print_all_deltas()
        print("current_topo:")
        self.__print_topology_details(self.current_topo)
        print("Neighbors of Miadtn: %s" % self.current_topo['miadtn'])
        print("Neighbors of br1   : %s" % self.current_topo['br1'])
        print("Neighbors of br2   : %s" % self.current_topo['br2'])
        print("br1 neighbor list  : %s" % self.current_topo['br1'].keys())
        print("br2 neighbor list  : %s" % self.current_topo['br2'].keys())
        for n in self.current_topo['br1'].keys():
            print("br1-%s:  %s" % (n, self.current_topo['br1'][n]['br1']))
        for n in self.current_topo['br2'].keys():
            print("br2-%s:  %s" % (n, self.current_topo['br2'][n]['br2']))
        print("\n\n")

        #model, newbool = self.get_latest_model()
        #print "get_latest_model %s, %s" % (newbool, model['model'])
        #print "\n\n"
        #model, newbool = self.get_latest_model()
        #print "get_latest_model %s, %s" % (newbool, model['model'])
        
        print("\n\n")
        print("simplified_topo:\n")
        self.__print_topology_details(self.simplified_topo)
        print("\n\n\n\n")
        #self._INTERNAL_TESTING_DELETE_FINAL_CHECKIN()

    def api_process(self):
        app.run(host=self.host, port=self.port)
        #FIXME: need SSL, threaded, debug

    def __print_topology_details(self, topo):
        #DEBUGING ONLY, SHOULD DELETE
        # Pass either topo - current_topo, simplified_topo - and print out
        # the details of the nodes and the edges
        print("\n\nNODES WITH DETAILS\n%s" %
              json.dumps(topo.nodes(data=True), indent=4, sort_keys=True))
        print("\n\nEDGES WITH DETAILS\n%s\n\n\n" %
              json.dumps(topo.edges(data=True), indent=4, sort_keys=True))

    def __print_all_deltas(self, all_details=True):
        deltas = self.get_all_deltas()

        print("\n\n&&&&& DELTAS &&&&&")
        for d in deltas:
            if all_details:
                print(d)
            else:
                print("%s" % d['id'])
        print("&&&&&        &&&&&\n\n")

    def __print_all_policy_hashes(self):
        hashes = self.hash_table.find()

        print("\n\n&&&&& POLICY_HASHES &&&&&")
        for h in hashes:
            print("%s - %s %s" % (h['hash'], h['delta_id'],
                                  pickle.loads(str(h['policy']))))
        print("&&&&&        &&&&&\n\n")

        

    def _INTERNAL_TESTING_DELETE_FINAL_CHECKIN(self):
        nodes = self.current_topo.nodes()
        print("\n\nNODES WITH DETAILS\n" +
              json.dumps(self.current_topo.nodes(data=True),
                                    indent=4, sort_keys=True))
        print("\n\nEDGES\n" + str(self.current_topo.edges()) + "\n\n\n")
        for node in nodes:
            print("  %s : %s" % (node, self.current_topo[node]))
        for node in nodes:
            print("\n%s:%s " % (node, json.dumps(self.current_topo[node],
                                                    indent=4, sort_keys=True)))
        self.generate_simplified_topology()
        for node in self.simplified_topo.nodes():
            if self.simplified_topo.node[node]['type'] != 'central':
                self.get_bw_available_on_egress_port(node)
                self.get_vlans_in_use_on_egress_port(node)

        for srcnode in self.simplified_topo.nodes():
            if self.simplified_topo.node[srcnode]['type'] != 'central':
                for dstnode in self.simplified_topo.nodes():
                    if self.simplified_topo.node[dstnode]['type'] != 'central':
                        self.install_point_to_point_policy(
                            srcnode, dstnode,
                            100, 200,
                            100000,
                            "1985-04-12T12:34:56",
                            "2985-04-12T12:34:56",
                            1)
                        self.install_point_to_point_policy(
                            srcnode, dstnode,
                            101, 201,
                            100000,
                            "1985-04-12T12:34:56",
                            "2985-04-12T12:34:56",
                            2)
                        self.install_point_to_point_policy(
                            srcnode, dstnode,
                            102, 202,
                            100000,
                            "1985-04-12T12:34:56",
                            "2985-04-12T12:34:56",
                            3)
                        self.install_point_to_point_policy(
                            srcnode, dstnode,
                            103, 203,
                            100000,
                            "1985-04-12T12:34:56",
                            "2985-04-12T12:34:56",
                            4)

    def _sanitize_db(self):
        #FIXME work in progress
        ''' This is a helper function to compare what's in the SENSE DB with 
            what is in the PolicyManager's DB. PolicyManager is ground truth.'''
        all_deltas = self.delta_table.find()
        all_hashes = list(self.hash_table.find())
        
        # First, let's clean up the delta table if a policy isn't installed and
        # has one-or-more hashes in the hash table.
        # - Loop through deltas and remove those from the DB that don't have a
        #   hash.
        # -- If delta doesn't have at least one correstponding hash in the DB,
        #    remove it from the DB
        # -- If delta does have one or more hashes:
        # --- For each policy_hash, check with the  PolicyManager to confirm
        #     the policy with that policy_hash exists.
        # ---- If it does, good
        # ---- If it does not:
        # ----- Delete delta
        # ----- We need to loop through all of the policy_hashes associated with
        #       the that delta:
        # ------ If PolicyManager policy exists, delete it
        # ------ Delete policy_hash
        print("\n\n\n\n\n")
        self.__print_all_deltas(False)
        self.__print_all_policy_hashes()
        
        for delta in all_deltas:
            print("    _sanitize_db() - Looking at delta %s" % delta['delta_id'])
            matches = list(self.hash_table.find(delta_id=delta['delta_id']))
            print("    _sanitize_db() - matches on delta %s" % len(matches))
            for m in matches:
                print("      %s" % m)
            if matches == []:
                print("    _sanitize_db() - Attempting to remove - NO HASH - %s" % delta['delta_id'])
                self.delta_table.delete(**delta)
                continue
            problem = False
            for match in matches:
                all_hashes.remove(match)
                if PolicyManager().get_policy_details(match['hash']) == None:
                   problem = True
                   print("    _sanitize_db() - Problem: match %s  isn't in PolicyManager" % match['hash'])
                   break
                    
            if problem:
                print("    _sanitize_db() - Attempting to remove - NO RM - %s" % delta['delta_id'])
                self.delta_table.delete(**delta)
                for match in matches:
                    print("    _sanitize_db() - Removing hash - NO RM - %s" % match['hash'])
                    if PolicyManager().get_policy_details(match['hash']) != None:
                        print("     _sanitize_db() - Removing policy - NO RM - %s" % match['hash'])
                        PolicyManager().remove_policy(match['hash'], self.userid)
                    self.hash_table.delete(**match)
                

        # Second, we're going to go through the remaining hashes to see if they
        # exist in the PolicyManager. We already know that a corresponding delta
        # does not exist, based on our loops above.
        # - Loop through the hashes
        # -- If PolicyManager policy exists, delete it
        # -- delete policy_hash from hash_table.

        for policy_hash in all_hashes:
            print("    _sanitize_db() - Removing hash - NO DELTA - %s" % policy_hash['hash'])
            if PolicyManager().get_policy_details(policy_hash['hash']) != None:
                print("    _sanitize_db() - Removing policy - NO DELTA - %s" % policy_hash['hash'])
                PolicyManager().remove_policy(policy_hash['hash'], self.userid)
            self.hash_table.delete(**policy_hash)

        self.__print_all_deltas(False)
        self.__print_all_policy_hashes()
        print("\n\n\n\n\n")
        
    def policy_add_callback(self, policy):
        ''' Handles policies being added. '''
        print("policy_add_callback - %s" % policy)

    def policy_rm_callback(self, policy):
        ''' Handles policies being removed. '''
        print("policy_rm_callback - %s" % policy)

    def topo_change_callback(self):
        ''' Handles topology changes. 
            FIXME: topologies don't change right now. '''
        pass

    def get_bw_available_on_egress_port(self, node):
        ''' Get the bandwidth available on a given egress port from the original
            network graph. Be sure to update topology before making these 
            requests. '''

        # Access the bandwidth from the original topology.
        start_node = self.simplified_topo.node[node]['start_node']
        end_node = self.simplified_topo.node[node]['end_node']
        bw_available = self.simplified_topo.node[node]['max_bw']
        # Swapped around, because the end_node is always the switch, and the
        # switch's data structure is the keeper of the bw_in_use
        bw_in_use = self.current_topo[end_node][start_node]['bw_in_use']

        self.dlogger.debug("get_bw_available_on_egress_port: %s" %
                           self.simplified_topo.node[node])
        self.dlogger.debug("  %s: bw_available %s, bw_in_use %s" %
                           (node, bw_available, bw_in_use))
        
        # Return BW on egress port
        return (bw_available - bw_in_use)

    def get_vlans_in_use_on_egress_port(self, node):
        ''' Get the VLANs that are in use on a given egress port. '''

        # Access the bandwidth from the original topology.
        start_node = self.simplified_topo.node[node]['start_node']
        end_node = self.simplified_topo.node[node]['end_node']
        # Swapped around, because the end_node is always the switch, and the
        # switch's data structure is the keeper of the vlans_in_use on the port
        print("self.current_topo[%s][%s]:%s" % (end_node, start_node,
                                    self.current_topo[end_node][start_node]))
        vlans_in_use = self.current_topo[end_node][start_node]['vlans_in_use']

        self.dlogger.debug("get_vlans_in_use_on_egress_port: %s" %
                           self.simplified_topo.node[node])
        self.dlogger.debug("  %s: vlans_in_use %s" % (node, vlans_in_use))

        # Return VLANs in use on egress port
        return vlans_in_use

    def get_vlans_available_on_egress_port(self, node):
        ''' Get VLANs available for SENSE API use. 
            Take in a node name
            Returns a string with the available VLANs.
        '''

        # Get available VLANs
        raw_available_vlans = self.simplified_topo.node[node]['available_vlans']
        available_vlans = TopologyManager().get_available_vlan_list(
            raw_available_vlans)

        # Get VLANs in use
        in_use = self.get_vlans_in_use_on_egress_port(node)
        
        # Get difference
        # https://www.geeksforgeeks.org/python-intersection-two-lists/
        diff = set(available_vlans).difference(in_use)

        # Simplify to text
        sortedlist = sorted(diff)
        index = 0
        begin = None
        current = None
        text_vlan = ""

        while index < len(sortedlist):
            begin = sortedlist[index]
            current = begin

            index += 1

            while (index < len(sortedlist) and
                   current + 1 == sortedlist[index]):
                current += 1
                index += 1

            if begin == current:
                text_vlan += "%d" % current
            else:
                text_vlan += "%d-%d" % (begin, current)

            if index < len(sortedlist):
                text_vlan += ","

        # Return text
        return text_vlan

    def _is_default_lifetime(self, start_time, stop_time):
        return False
        start_datetime = datetime.strptime(start_time, rfc3339format)
        stop_datetime  = datetime.strptime(stop_time, rfc3339format)

        if (stop_datetime - start_datetime) == timedelta(365*100):
            return True
        return False
            
                                   
    def generate_list_of_services(self):
        ''' Generates a list of external facing services based on endpoints. 
            Any service that has at least one endpoint at the end of the 
            controlled network is included in the list.

            Each element in the list is quite simple:
              {"service":"servicename",
               "bandwidth":bandwidth in bits per second,
               "starttime":start time string,
               "endtime":end time string
               "endpoints": [ list of endpoint tuples]}

            An endpoint tuple looks as follows:
              ("endpointname",VLAN number)

            The servicename includes the Service Domain.
            The endpointname include the switch/port combo.
            Neither include the URN.
            starttime and endtime are in the SENSE format.
        
            Requires the simplified topology to be generated. '''
        self.current_policies = PolicyManager().get_policies()
        self.list_of_services = []
        
        # Get exterior ports - from the simplified_topology
        exterior_nodes = self.simplified_topo.nodes()
        exterior_nodes.remove('central')

        # Loop through policies
        for r in self.current_policies:
            policy = PolicyManager().get_raw_policy(r[0])
            potential_endpoints = policy.get_endpoints()
            # - Loop through endpoints
            endpoints = []
            for (e, f, v) in potential_endpoints:
                print("   endpoint: %s, %s, %d" % (e, f, v))
                # -- check if policy ends on an exterior port
                if (("%s-%s" % (e,f)) in exterior_nodes):
                    # -- if it does, save off name
                    endpoints.append(("%s-%s" % (e,f), v))
                elif (("%s-%s" % (f,e)) in exterior_nodes):
                    endpoints.append(("%s-%s" % (f,e), v))
            # - if list is not empty, then continue. If empty, next policy
            if len(endpoints) == 0:
                continue
            
            # - get start and end times
            start_time = policy.get_start_time()
            stop_time = policy.get_stop_time()
            # - if now < start_time or now > stop_time, don't care about
            #   the policy
            start_datetime = datetime.strptime(start_time, rfc3339format)
            stop_datetime =  datetime.strptime(stop_time,  rfc3339format)
            now = datetime.now()
            if (now < start_datetime or
                now > stop_datetime):
                continue
            
            # - get it's bandwidth
            bandwidth = policy.get_bandwidth()

            # - get the user
            user = policy.get_user()
            
            # - create service name:
            #   Get the policy_hash from the policy
            policy_hash = policy.get_policy_hash()
            #   if user is self.userid, then give back uuid
            if user == self.userid:
                # -- find the delta in the local database to get the UUID
                delta = self._get_delta_by_policy_hash(policy_hash)
                    
                # -- Put together service name.
                svc_name = self.SVC_SENSE
                service_name = "%s:conn+%s" % (svc_name,
                                               delta['delta_id'])
                
            #   if user is other, then make up name
            else:
                service_name = "%s:conn+%s" % (self.SVC_NONSENSE,
                                               policy_hash)
            
            # - create new service dictionary
            svc_dict = {"service":service_name,
                        "bandwidth":bandwidth,
                        "starttime":start_time,
                        "endtime":stop_time,
                        "endpoints":endpoints}
            # - add new dictionary to self.list_of_services
            self.list_of_services.append(svc_dict)
        return
    
    def generate_simplified_topology(self):
        ''' Calculates the 'black box' version of the topology, exposing only 
            the outside networks and DTNs as endpoints. The internals are *not*
            exposed, as we handle those ourselves. '''
        
        # Create graph with central node only.
        with self.topolock:
            self.current_topo = TopologyManager().get_topology()     # Update!
            self.simplified_topo = nx.Graph()
            self.simplified_topo.add_node('central')
            self.simplified_topo.node['central']['type'] = 'central'

            # For each EDGE node (returns true on TOPO_EDGE_TYPE), loop over
            # each connection on the edge node add a connection to the central
            # node.
            for node in self.current_topo.nodes(): # name of node
                #print self.current_topo[node]
                t = self.current_topo.node[node]['type']
                alias = None
                if 'alias' in self.current_topo.node[node].keys():
                    alias = self.current_topo.node[node]['alias']
                if TOPO_EDGE_TYPE(t):
                    for edge in self.current_topo[node]: # edge dictionary
                        new_node = node + "-" + edge
                        self.simplified_topo.add_node(new_node)
                        self.simplified_topo.add_edge(new_node, 'central')

                        # Copy over how to access the connection (which two
                        # nodes on the original topology), and the max bandwidth
                        # of the connection.                    
                        self.simplified_topo.node[new_node]['start_node'] = node
                        self.simplified_topo.node[new_node]['end_node'] = edge
                        #print self.current_topo[node][edge]
                        bw = self.current_topo[node][edge]['weight']
                        self.simplified_topo.node[new_node]['max_bw'] = bw
                        vlans = self.current_topo[node][edge]['available_vlans']
                        self.simplified_topo.node[new_node]['available_vlans'] = vlans
                        self.simplified_topo.node[new_node]['type'] = t
                        if alias != None:
                            self.simplified_topo.node[new_node]['alias'] = alias

    def generate_model(self):
        ''' Generates a model of the simplified topology. '''

        list_of_vlan_services = []
        list_of_physical_ports = []
        
        # Boilerplate prefixes
        output  = "@prefix sd: <http://schemas.ogf.org/nsi/2013/12/services/definition#> .\n"
        output += "@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .\n"
        output += "@prefix owl: <http://www.w3.org/2002/07/owl#> .\n"
        output += "@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .\n"
        output += "@prefix rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .\n"
        output += "@prefix nml: <http://schemas.ogf.org/nml/2013/03/base#> .\n"
        output += "@prefix mrs: <http://schemas.ogf.org/mrs/2013/12/topology#> .\n\n\n"

        
        # Get all endpoints and active services
        endpoints = ""
        self.generate_simplified_topology()
        self.generate_list_of_services()

        #self.__DEBUG_print_lots_of_details()
        
        for ep in self.simplified_topo.neighbors('central'):
            # For each endpoint:
            #  - Get endpoint name
            node = self.simplified_topo.node[ep]
            epname = "%s::%s" % (fullurn, ep)
            list_of_physical_ports.append(epname)
            
            #  - Definition of VLANs available on said endpoint
            # FIXME: does this need to remove in-use VLANs?
            vlan_name = "%s:vlan_range" % epname
            vlan_def  = "<%s>\n" %vlan_name
            vlan_def += "                a nml:LabelGroup, owl:NamedIndividual ;\n"
            vlan_def += "                nml:labeltype <http://schemas.ogf.org/nml/2012/10/ethernet#vlan> ;\n"
            vlan_def += "                nml:values \"%s\" .\n\n" % self.get_vlans_available_on_egress_port(ep)

            #  - Bandwidth on a given port
            bw_name = "%s:BandwidthService" % epname
            available_bw = self.get_bw_available_on_egress_port(ep)
            bw_def  = "<%s>\n" % bw_name
            bw_def += "                a mrs:BandwidthService ;\n"
            bw_def += "                mrs:availableCapacity \"%d\"^^xsd:long ;\n" % available_bw
            bw_def += "                mrs:reservableCapacity \"%d\"^^xsd:long ;\n" % available_bw
            bw_def += "                mrs:maximumCapacity \"%d\"^^xsd:long ;\n" % node["max_bw"]
            bw_def += "                mrs:unit \"bps\" ;\n"
            bw_def += "                nml:belongsTo <%s> .\n\n" % epname
            
            #  - Definition of Link structure
            #  -- Get list of BidirectionalPorts
            bidiports = ""
            for s in self.list_of_services:
                for e,f in s['endpoints']:
                    if e == ep:
                        bidiports += ", <%s:vlanport+%d>" % (epname, f)
                        print("%s:vlanport+%d" % (epname, f))
            if bidiports != "":
                # trim off the leading ", "
                bidiports = bidiports[2:] 
            
            link_def  = "<%s>\n" % epname
            link_def += "                a nml:BidirectionalPort ;\n"
            link_def += "                nml:belongsTo <%s::%s>, <%s> ;\n" % (fullurn, self.SVC_SENSE, fullurn)
            link_def += "                nml:hasLabelGroup <%s> ;\n" % vlan_name
            link_def += "                nml:hasService <%s> ;\n" % bw_name
            if 'alias' in node.keys():
                link_def += "                nml:isAlias <%s> ;\n" % node['alias']
            if bidiports != "":
                link_def += "                nml:hasBidirectionalPort %s ;\n" % bidiports
            link_def += "                nml:name \"%s\" .\n\n" % ep

            endpoints += vlan_def
            endpoints += bw_def
            endpoints += link_def

        # Add services and all the various related bits.
        services = ""
        for s in self.list_of_services:
            # - Pull out bandwidth and service name
            bandwidth = s['bandwidth']
            servicename = s['service']
            starttime = s['starttime']
            endtime = s['endtime']
            per_service_endpoints = []

            # - Loop through all service endpoints
            for e in s['endpoints']:
                (endpointname, vlannum) = e
                service_str = "%s::%s:resource+links-connection_1:vlan+%d" % (
                    fullurn, servicename, vlannum)
                list_of_vlan_services.append(service_str)

                # -- Add VLAN label for virtual port
                services += "<%s::%s:vlanport+%d:label+%d>\n" % (
                    fullurn, endpointname, vlannum, vlannum)
                services += "        a nml:Label ;\n"
                services += "        nml:belongsTo <%s::%s:vlanport+%d> ;\n" % (
                    fullurn, endpointname, vlannum)
                if not self._is_default_lifetime(starttime, endtime):
                    services += "        nml:existsDuring <%s:existsDuring> ;\n" % (
                        service_str)
                services += "        nml:labeltype <http://schemas.ogf.org/nml/2012/10/ethernet#vlan> ;\n"
                services += "        nml:value \"%d\" .\n\n" % vlannum
                
                # -- Add bandwidth on virtual port
                if bandwidth != 0:
                    services += "<%s::%s:vlanport+%d:service+bw>\n" % (
                        fullurn, endpointname, vlannum)
                    services += "        a mrs:BandwidthService ;\n"
                    services += "        mrs:reservableCapacity \"%d\"^^xsd:long ;\n" % (bandwidth)
                    services += "        mrs:type \"guaranteedCapped\" ;\n"
                    services += "        mrs:unit \"bps\" ;\n"
                    services += "        nml:belongsTo <%s::%s:vlanport+%d> ;\n" % (
                        fullurn, endpointname, vlannum)
                    if not self._is_default_lifetime(starttime, endtime):
                        services += "        nml:existsDuring <%s:existsDuring> .\n\n" % (
                            service_str)
                
                # -- Add service lifetime
                if not self._is_default_lifetime(starttime, endtime):
                    services += "<%s:existsDuring>\n" % service_str
                    services += "        a nml:Lifetime ;\n"
                    services += "        nml:end \"%s.000000-0000\" ;\n" % endtime
                    services += "        nml:start \"%s.000000-0000\" .\n\n" % starttime
                
                # -- Add virtual port
                services += "<%s::%s:vlanport+%d>\n" % (
                    fullurn, endpointname, vlannum)
                services += "        a nml:BidirectionalPort, mrs:SwitchingSubnet ;\n"
                services += "        nml:belongsTo <%s>,<%s:%s> ;\n" % (
                    service_str, fullurn, endpointname)
                services += "        nml:encoding <http://schemas.ogf.org/nml/2012/10/ethernet> ;\n"
                if not self._is_default_lifetime(starttime, endtime):
                    services += "        nml:existsDuring <%s:existsDuring> ;\n" % (
                        service_str)
                services += "        nml:hasLabel <%s::%s:vlanport+%d:label+%d> ;\n" % (
                    fullurn, endpointname, vlannum, vlannum)
                if bandwidth != 0:
                    services += "        nml:hasService <%s::%s:vlanport+%d:service+bw> ;\n" % (
                        fullurn, endpointname, vlannum)
                services += "        nml:name \"UNKNOWN\" .\n\n"

                per_service_endpoints.append("%s:%s:vlanport+%d" % (
                    fullurn, endpointname, vlannum))
                
            # - Add service
            endpoints_str = ""
            for entry in per_service_endpoints[:-1]:
                endpoints_str += "<%s>, " % entry
            endpoints_str += "<%s> ;" % per_service_endpoints[-1]
            
            services += "<%s>\n" % service_str
            services += "        a mrs:SwitchingSubnet ;\n"
            services += "        nml:belongsTo <%s> ;\n" % fullurn
            services += "        nml:encoding <http://schemas.ogf.org/nml/2012/10/ethernet> ;\n"
            if not self._is_default_lifetime(starttime, endtime):
                services += "        nml:existsDuring <%s:existsDuring> ;\n" % (
                    service_str)
            services += "        nml:hasBidirectionalPort %s\n" % endpoints_str
            services += "        nml:labelSwapping true ;\n"
            services += "        nml:labelType <http://schemas.ogf.org/nml/2012/10/ethernet#vlan> .\n\n"
        
        # Add topology (acts as switch)
        physical_ports_str = ""
        for entry in list_of_physical_ports[:-1]:
            physical_ports_str += "<%s>, " % entry
        physical_ports_str += "<%s> ;" % list_of_physical_ports[-1]

        topology = "<%s>\n" % fullurn
        topology += "                a nml:Topology, owl:NamedIndividual ;\n"
        #        topology += "                nml:belongsTo" #Fixme: who?
        topology += "                nml:hasBidirectionalPort %s\n" % physical_ports_str
        topology += "                nml:hasService <%s::%s> ;\n" % (
            fullurn, self.SVC_SENSE)
        topology += "                nml:name \"AtlanticWave/SDX\" .\n\n"

        # Add L2 service domain
        vlan_services_str = ""
        self.dlogger.debug("LIST_OF_VLAN_SERVICES: %s" % list_of_vlan_services)
        if len(list_of_vlan_services) > 0:
            for entry in list_of_vlan_services[:-1]:
                vlan_services_str += "<%s>, " % entry
            vlan_services_str += "<%s>" % list_of_vlan_services[-1]


        # L2 switching
        service_domain  = "<%s::%s>\n" % (fullurn, self.SVC_SENSE)
        service_domain += "                 a nml:SwitchingService ;\n"
        service_domain += "                 sd:hasServiceDefinition <%s::ServiceDefinition:%s> ;\n" % (fullurn, self.SVC_SENSE_L2MP)
        service_domain += "                 nml:encoding <http://schemas.ogf.org/nml/2012/10/ethernet> ;\n"
        service_domain += "                 nml:labeltype <http://schemas.ogf.org/nml/2012/10/ethernet#vlan> ;\n"
        if len(list_of_vlan_services) > 0:
            service_domain += "                 mrs:providesSubnet %s ;\n" % vlan_services_str
        service_domain += "                 nml:hasBidirectionalPort %s\n" % physical_ports_str
        service_domain += "                 nml:labelSwapping true .\n\n"

        # L2 MP - This is a service definition, child of the SwitchingService
        service_domain += "<%s::ServiceDefinition:%s>\n" % (fullurn, self.SVC_SENSE_L2MP)
        service_domain += "                 a sd:ServiceDefinition ;\n"
        service_domain += "                 sd:serviceType \"http://services.ogf.org/nsi/2018/06/descriptions/l2-mp-es\" .\n\n"
        
        # Add AWave service domain
        #FIXME

        output += service_domain
        output += topology
        output += services
        output += endpoints

        return output


    def get_latest_model(self):
        ''' Gets the latest model. 
            Returns tuple of the dictionary (described below), and bool whether
            the dictionary is new or not: (dictionary, new?)
             {'id': UUID of model,
              'href': address of model,
              'creationTime': timestamp of model,
              'model': the model itself}
        '''

        self.dlogger.debug("get_latest_model(): start")
        # Dictionary components
        model_id = None
        href = None
        creation_time = None
        model = None

        # Control components
        need_new_model = False
        retnew = False

        
        # Check DB: if there is a latest one, already inserted, use it.
        # The - in front of timestamp gets the latest.
        result = self.model_table.find_one(order_by=['-timestamp'])

        if result != None:
            model_id = result['model_id']
            href = "%s/sense-rm/api/sense/v1/models/%s" % (self.urlbase,
                                                           model_id)
            creation_time = result['timestamp']
            model = result['model_data']

        # Now, do we need a new model? Two reasons for this:
        #  - There wasn't a model in the DB
        #  - The latest model in the DB is stale, based on changes to either
        #    the topology or to the policies that are installed
        if creation_time == None:
            self.dlogger.debug("get_latest_model(): need new model - no creation time in latest.")
            need_new_model = True
        else:
            # Get the most recent time that there was a change
            topo_update_time = TopologyManager().get_last_modified_timestamp()
            policy_update_time = PolicyManager().get_last_modified_timestamp()
            parsed_creation = datetime.strptime(creation_time, rfc3339format)
            parsed_topo = datetime.strptime(topo_update_time, rfc3339format)
            parsed_policy = datetime.strptime(policy_update_time, rfc3339format)

            # Check if model is stale
            if (parsed_creation < parsed_topo):
                self.dlogger.debug("get_latest_model(): need new model - Topology changed. Current %s, Topo %s" % (creation_time, topo_update_time))
                need_new_model = True
            if (parsed_creation < parsed_policy):
                # This should be an if, not an elif, because we want good logging
                self.dlogger.debug("get_latest_model(): need new model - Policies changed.    Current %s, Policy %s" % (creation_time, policy_update_time))
                need_new_model = True
            
        if need_new_model:
            # Generate the model
            model = self.generate_model()
            raw_model = self.simplified_topo
            
            # Get creation time
            creation_time = datetime.now().strftime(rfc3339format)
            
            # Get ID
            model_id = str(uuid.uuid5(uuid.NAMESPACE_URL,
                                      creation_time))

            # Insert it into the DB
            self._put_model(model_id, model, raw_model, creation_time)
            retnew = True

        # Return the correct format
        self.dlogger.debug("get_latest_model(): Returning model %s" % model_id)
        retdict = {'id':model_id,
                   'href':href,
                   'creationTime':creation_time,
                   'model':model}
        return (retdict, retnew)
    
    def process_deltas(self, args):
        # Parse the args
        self.dlogger.debug("process_delta() begin with args: %s" % args) 
       
        keys = args.keys()
        if ('id' not in keys or
            'lastModified' not in keys or
            'modelId' not in keys):
            raise SenseAPIArgumentError(
                "Missing id, lastModified, or modelId: %s" % keys)

        if ('reduction' not in keys and
            'addition' not in keys):
            raise SenseAPIArgumentError("Missing reduction or addition: %s" %
                                        keys)
        
        delta_id = args['id']
        last_modified = args['lastModified']
        model_id = args['modelId']

        reduction = args['reduction']
        addition = args['addition']
        parsed_reductions = None
        parsed_additions = None
        status = HTTP_GOOD
        self.logger.info("process_delta() on delta_id %s" % delta_id)

        # If reduction:
        #  - parse reduction
        #  - find matching hashes per policy
        #  - if they don't exist, reject the reduction
        if reduction != None:
            try:
                parsed_reductions = self._parse_delta(reduction)
            except SenseAPIClientError as e:
                self.dlogger.error(
                    "process_deltas: reduction parsing received %s" %
                                   e)
                return None, HTTP_BAD_REQUEST

            for policy in parsed_reductions:
                policy_hash = self._get_policy_hash_by_policy(policy)
                if policy_hash == None:
                    self.dlogger.error(
                        "process_deltas: reduction no known hash for policy %s"
                        % str(policy))
                    return None, HTTP_BAD_REQUEST
            
        # If addition:
        #  - parse addition
        #  - See if each policy is possible (BW, VLANs, etc.)
        #  - If possible, great, continue on
        #  - If not possible, return failed status - automagic due to raised
        #    errors
        if addition != None:
            try:
                parsed_additions = self._parse_delta(addition)
            except SenseAPIClientError as e:
                self.dlogger.error("process_deltas: add parsing received %s" %
                                   e)
                return None, HTTP_BAD_REQUEST
            
            for policy in parsed_additions:
                bd = PolicyManager().test_add_policy(policy)            

        if parsed_reductions != None:
            self.dlogger.debug("_parse_delta(): parsed_reductions: %d" %
                               len(parsed_reductions))
            for p in parsed_reductions:
                self.dlogger.debug("  - %s" % p)
        if parsed_additions != None:
            self.dlogger.debug("_parse_delta(): parsed_additions: %d " %
                               len(parsed_additions))
            for p in parsed_additions:
                self.dlogger.debug("  - %s" % p)
            
                           
        # Have good addition and/or reduction,
        # - Put the delta into the db
        # - Get delta from db
        # - convert delta into what the orchestrator is expecting
        # - return delta and status

        #self._put_delta(delta_id, args, parsed_additions,
        #                    parsed_reductions, model_id, status)
        try:
            self._put_delta(delta_id, args, parsed_additions,
                            parsed_reductions, model_id, status)
        except SenseAPIError as e:
            self.dlogger.error("process_deltas: _put_delta received %s" % e)
            return None, HTTP_CONFLICT
        delta = self._get_delta_by_id(delta_id)
        retdelta = self._convert_delta(delta)

        self.dlogger.debug("process_deltas: returning %s, %s" %
                           (retdelta, status))
        self.logger.info("process_deltas(): Processed delta_id %s, status %s" %
                         (delta_id, status))

                   
        
        return retdelta, status
    
    def _parse_delta(self, raw_delta):
        # This is based on part of nrmDelta.processDelta() from
        # senserm_oscars's senserm_delta.py.
        # Parses the raw_delta, and returns back the policies that it thinks
        # matches the delta
        #
        # ASSUMPTION: only one policy is being added with each addition. Changes
        # would be needed if multiple policies are in each addition.
        #FIXME: anything else that needs to be returned back?

        def __get_uuid_and_service_name(s):
            # I'm sorry for this ugly string manipulation...
            # belongsTo
            if awaveurn in s:
                uuid = s.split("+")[1].split(":")[0]
                svcname = s.split("+")[2].split(":")[0].split("-")[1]
                return uuid, svcname
            # tag
            uuid = s.split("+")[2].split(":")[0]
            svcname = s.split(":")[-1]
            return uuid, svcname

        self.dlogger.debug("_parse_delta(): Begin")
        gr = rdflib.Graph()
        try:
            result = gr.parse(data=raw_delta, format='ttl')
            #FIXME: check the result
        except Exception as e:
            self.dlogger.error(
                "_parse_delta: Error on parsing graph: %s" % e)
            self.dlogger.error("  Delta: %s" % raw_delta)
            raise SenseAPIClientError("Delta unparsable %s:%s" %
                                      (e, raw_delta))


        # Get list of services
        # - Loop through graph and find the vlanport link structure
        # -- Extract UUID.
        # -- If UUID is new, create service dictionary
        # --- initialize services dictionary
        # --- Use dummy values for B/W and start (now) and end (now+100y) times
        # -- Add port to UUID
        # -- Find lifetime from link structure - if they exist
        # -- Find bandwidth from link structure
        services = {}
        for s in list2set(gr.subjects()):
            if awaveurn not in str(s):
                continue
            if ('vlanport+' in str(s).split(":")[-1]):
                # UUID
                objects = []

                for p,o in gr.predicate_objects(s):
                    # For some reason, I can't get objects(s, "...topology#tag")
                    # to work correctly. Probably some escaped character? Not 
                    # sure, so working around it this way. Ugly.
                    if (str(p) ==
                        "http://schemas.ogf.org/nml/2013/03/base#belongsTo"):
                        if ('l2switching' in str(o)):
                            objects.append(o)

                if len(objects) != 1:
                    # Ok, backup path is topology#tag, especially for additions
                    for p,o in gr.predicate_objects(s):
                        if (str(p) ==
                            'http://schemas.ogf.org/mrs/2013/12/topology#tag'):
                            objects.append(o)
                            
                if len(objects) != 1:
                    raise SenseAPIClientError("There is not one http://schemas.ogf.org/nml/2013/03/base#belongsTo or http://schemas.ogf.org/mrs/2013/12/topology#tag' for %s: %s" % (str(s), str(objects)))
                    
                uuid, svcname = __get_uuid_and_service_name(objects[0])

                if uuid not in services.keys():
                    self.dlogger.debug("  _parse_delta(): New UUID %s" % uuid)
                    # Initialize new service things with defaults.
                    services[uuid] = {}
                    services[uuid][svcname] = {'endpoints':[],
                                               'starttime':
                                               datetime.strftime(
                                                   datetime.now(),
                                                   rfc3339format),
                                               'endtime':
                                               datetime.strftime(
                                                   (datetime.now() +
                                                    timedelta(365*100)),
                                                   rfc3339format),
                                               'bandwidth': 0}

                self.dlogger.debug("  _parse_delta(): New service %s:%s"%
                                   (uuid, svcname))
                
                # Get the VLAN, physical port, and switch info
                vlan = s.split('+')[1]
                epname = s.split("::")[1].split(":")[0]
                ep, switchname  = str(epname).split('-')
                port = self.current_topo[switchname][ep][switchname]
                self.dlogger.debug("  port: %s" % port)
                endpoint = {'switch':switchname,
                            'port':port,
                            'vlan':vlan}
                self.dlogger.debug("  endpoint: %s" % endpoint)
                services[uuid][svcname]['endpoints'].append(endpoint)

                # Other stuff: lets loop through since it's easier.
                for p,o in gr.predicate_objects(s):
                    # See if lifetime exists
                    if "existsDuring" in str(p):
                        for p2,o2 in gr.predicate_objects(o):
                            if 'start' in str(p2):
                                self.dlogger.debug( "     starttime: %s" % str(o2))
                                starttime = datetime.strftime(
                                    datetime.strptime(str(o2)[:-5],
                                                      sensetimeformat),
                                    rfc3339format)
                                self.dlogger.debug("  starttime: %s" %
                                                   starttime)
                                services[uuid][svcname]['starttime'] = starttime
                            elif "end" in str(p2):
                                self.dlogger.debug( "     endtime  : %s" % str(o2))
                                endtime = datetime.strftime(
                                    datetime.strptime(str(o2)[:-5],
                                                      sensetimeformat),
                                    rfc3339format)
                                services[uuid][svcname]['endtime'] = endtime
                                self.dlogger.debug("  endtime:   %s" %
                                                   endtime)
                    # See if bandwidth exists
                    elif ('hasService' in str(p) and
                          'service+bw' in str(o)):
                        for p3,o3 in gr.predicate_objects(o):
                                    if "reservableCapacity" in str(p3):
                                        bw = int(o3)
                                        self.dlogger.debug("  bw: %s" % bw)
                                        services[uuid][svcname]['bandwidth'] =bw
                                   
        # Have details, now loop through services and create policies that are
        # being described.
        generated_policies = []
        for uuid in services.keys():
            for svc in services[uuid].keys():
                self.dlogger.debug("services[uuid][%s]: %s" % (svc, 
services[uuid][svc]))
                endpointcount = len(services[uuid][svc]['endpoints'])

                # These are exclusively for error cases.
                starttime = None
                endtime = None
                bandwidth = None
                ep0 = None
                ep1 = None
                endpoints = None
                
                if endpointcount < 2:
                    raise SenseAPIClientError(
                        "There are fewer than 2 endpoints: %s, %s, %s" %
                        (endpoints, uuid, svc))
                elif endpointcount == 2:
                    # L2Tunnel
                    try:
                        ep0 = services[uuid][svc]['endpoints'][0]
                        ep1 = services[uuid][svc]['endpoints'][1]
                        starttime = services[uuid][svc]['starttime']
                        endtime = services[uuid][svc]['endtime']
                        bandwidth = services[uuid][svc]['bandwidth']
                        policy = {L2TunnelPolicy.get_policy_name():
                                  {'starttime':starttime,
                                   'endtime':endtime,
                                   'srcswitch':ep0['switch'],
                                   'dstswitch':ep1['switch'],
                                   'srcport':ep0['port'],
                                   'dstport':ep1['port'],
                                   'srcvlan':ep0['vlan'],
                                   'dstvlan':ep1['vlan'],
                                   'bandwidth':bandwidth}}
                        policy = L2TunnelPolicy(self.userid, policy)
                        generated_policies.append(policy)
                    except Exception as e:
                        self.dlogger.error(
                           "_parse_delta: Error on L2TunnelPolicy creation - %s:%s:%s:%s:%s" %
                            (starttime, endtime, bandwidth, ep0, ep1))
                        self.dlogger.error("    %s" % str(e))
                        raise SenseAPIClientError(
                            "Invalid parameters for L2TunnelPolicy - %s:%s:%s:%s:%s" %
                            (starttime, endtime, bandwidth, ep0, ep1))
                    
                elif endpointcount > 2:
                    # L2Multipoint
                    try:
                        starttime = services[uuid][svc]['starttime']
                        endtime = services[uuid][svc]['endtime']
                        bandwidth = services[uuid][svc]['bandwidth']
                        endpoints = services[uuid][svc]['endpoints']
                        policy = {L2MultipointPolicy.get_policy_name():
                                  {"starttime":starttime,
                                   "endtime":endtime,
                                   "bandwidth":bandwidth,
                                  "endpoints":endpoints}}
                        policy = L2MultipointPolicy(self.userid, policy)
                        generated_policies.append(policy)
                    except Exception as e:
                        self.dlogger.error(
                            "_parse_delta: Error on L2MultipointPolicy creation - %s:%s:%s:%s" %
                            (starttime, endtime, bandwidth, endpoints))
                        raise SenseAPIClientError(
                            "Invalid parameters for L2MultipointPolicy - %s:%s:%s:%s" %
                            (starttime, endtime, bandwidth, endpoints))

        self.logger.info("_parse_delta: Generated %d policies for UUIDs %s" %
                         (len(generated_policies), str(services.keys())))
        self.dlogger.debug("_parse_delta: Generated policies:")
        for pol in generated_policies:
            self.dlogger.debug("    %s" % pol)
        return generated_policies

    def get_delta(self, deltaid):
        ''' Get the delta.
            Returns:
              - (state, phase) - if deltaid is valid
              - (None, None) - if deltaid is invalid        
        '''
        #FIXME: does this need to exist?
        # Get from the DB based on the deltaid -
        delta = self._get_delta_by_id(deltaid)
        # If found, Pull out phase and state to return
        if delta != None:
            status = delta['status']
            phase = PHASE_RESERVED
            if status == STATUS_ACTIVATED:
                phase = PHASE_COMMITTED #FIXME?
            self.dlogger.debug("get_delta: %s %s" % (status, phase))
            return status, phase
        #FIXME: If not found, return ........
        return None, None
    
    def commit(self, deltaid):
        ''' Commits the specified deltaid.
            Returns:
              - HTTP_GOOD if everything is committed.
              - HTTP_NOT_FOUND if delta is not found.
              - HTTP_CONFLICT if delta cannot be committed.
        '''
    
        self.dlogger.debug("commit(): Attempting to commit deltaid %s" %
                           deltaid)
        # Get the delta information
        delta = self._get_delta_by_id(deltaid)
        if delta == None:
            return HTTP_NOT_FOUND

        # Make sure additions can still work
        if delta['addition'] != None:
            for policy in delta['addition']:
                try:
                    PolicyManager().test_add_policy(policy)
                except Exception as e:
                    # This means that policy cannot be added, for whatever
                    # reason, log it, and return bad status
                    self.logger.error("commit: addition failed, aborting. " +
                                      "%s, %s" % (str(policy), e))
                    return HTTP_CONFLICT

        # Reductions first
        # - Loop through the reductions
        # -- get the corresponding policy_hash
        # -- Call PolicyManager().remove_policy() to get rid of the policy
        # -- if it doesn't exist in the PolicyManager, that's fine, but log it!
        if delta['reduction'] != None:
            for policy in delta['reduction']:
                policy_hash = self._get_policy_hash_by_policy(policy)
                try:
                    PolicyManager().remove_policy(policy_hash, self.userid)
                except PolicyManagerError as e:
                    self.dlogger.info("commit: reduction failed: %s" %
                                      policy_hash)
                    self.logger.error("commit: reduction failed: %s, %s" %
                                      (policy_hash, e))
                    #FIXME: Is this the right return code?
                    return HTTP_SERVER_ERROR 

        # Addition commit second
        # - Loop through second time
        # -- Install policy this time
        # -- push the policy_hash into the hashDB with
        #    _put_policy_hash_by_policy()
        if delta['addition'] != None:
            for policy in delta['addition']:
                try:
                    policy_hash = PolicyManager().add_policy(policy)
                    self._put_policy_hash_by_policy(policy, policy_hash,
                                                    deltaid)
                except:
                    self.dlogger.info("commit: addition failed: %s" %
                                      policy_hash)
                    self.logger.error("commit: addition failed: %s, %s" %
                                      (policy_hash, e))
                    #FIXME: Is this the right return code?
                    return HTTP_SERVER_ERROR

        # Update status
        self._put_delta(deltaid, status=STATUS_ACTIVATED, update=True)
        self.logger.info("commit: successfully commited delta_id %s" %
                         deltaid)
        # Return good status
        return HTTP_GOOD
    

    def _get_current_time(self):
        ''' Helper function, 
            Returns:
              - String of properly formatted time for timestamps. '''
        # Based on https://bitbucket.org/berkeleylab/sensenrm-oscars/src/d09db31aecbe7654f03f15eed671c0675c5317b5/sensenrm_cancel.py's get_time() function.
        tZERO = timedelta(0)
        class UTC(tzinfo):
          def utcoffset(self, dt):
            return tZERO
          def tzname(self, dt):
            return "UTC"
          def dst(self, dt):
            return tZERO
        utc = UTC()
        
        dt = datetime.now(utc)
        fmt_datetime = dt.strftime('%Y-%m-%dT%H:%M:%S')
        tz = dt.utcoffset()
        if tz is None:
            fmt_timezone = "+00:00"
            #fmt_timezone = "Z"
        else:
            fmt_timezone = "+00:00"
        time_iso8601 = fmt_datetime + fmt_timezone
        return time_iso8601
    
    def _get_delta_by_id(self, delta_id):
        ''' Helper function, just pulls a delta based on the ID.
            Returns:
              - None if delta id doesn't exist
              - Dictionary containing delta. See comment at top of SenseAPI 
                definition for keys. 
        '''
        raw_delta = self.delta_table.find_one(delta_id=delta_id)
        if raw_delta == None:
            return None
        
        # Unpickle the pickled values and rebuild dictionary to return
        delta = {'delta_id':raw_delta['delta_id'],
                 'raw_request':pickle.loads(str(raw_delta['raw_request'])),
                 'addition':pickle.loads(str(raw_delta['addition'])),
                 'reduction':pickle.loads(str(raw_delta['reduction'])),
                 'status':raw_delta['status'],
                 'last_modified':raw_delta['last_modified'],
                 'timestamp':raw_delta['timestamp'],
                 'model_id':raw_delta['model_id']}

        self.dlogger.debug("_get_delta_by_id() on %s successful" % delta_id)
        return delta

    def _get_delta_by_policy_hash(self, policy_hash):
        ''' Helper function, just pulls a delta based on the policy hash (from 
            the PolicyManager).
            Returns:
              - None if policy_hash doesn't exist
              - Dictionary containing delta. See comment at top of SenseAPI
                definition for keys.
        '''

        raw_hash = self.hash_table.find_one(hash=policy_hash)

        if raw_hash == None:
            return None

        delta_id = raw_hash['delta_id']
        
        delta = self._get_delta_by_id(delta_id)

        self.dlogger.debug("_get_delta_by_policy_hash() on %s successful %s" %
                           (policy_hash, delta_id))
        return delta

    def _get_policy_hash_by_policy(self, policy):
        ''' Helper function, finds the policy hash based on a policy that was in
            an addition in the past. '''

        print("\n\nPOLICY: %s" % policy)

        for raw_hash in self.hash_table.find():
            if pickle.loads(str(raw_hash['policy'])) == policy:
                policy_hash = raw_hash['hash']
                self.dlogger.debug(
                    "_get_policy_hash_by_policy() successful %s" % policy_hash)
                return policy_hash
                
        self.dlogger.debug("_get_policy_hash_by_policy() unsuccessful")
        return None

    def _put_policy_hash_by_policy(self, policy, policy_hash, delta_id):
        ''' helper function, puts the policy hash and policy into the hash_table
            to make finding them easier. Note: a delta can have multiple
            policies as part of the addition, which is where this comes in.
            We can find this information other ways, but this is *so* much 
            easier. '''

        #FIXME: possible enhancement to check if something matching the
        # policy_hash is already in the hash_table.

        self.dlogger.info("_put_policy_hash_by_policy: %s, %s" % (policy_hash,
                                                                  delta_id))
        
        hash_policy = {'hash':policy_hash,
                       'policy':pickle.dumps(policy),
                       'delta_id':delta_id}
        #self.dlogger.debug("Inserting hash_policy %s" % hash_policy)
        self.hash_table.insert(hash_policy)
        print("\n\nWHOLE HASH TABLE:") 
        for entry in self.hash_table.find():
            print(entry)
        print("\n\n\n")
        
    
    def get_all_deltas(self):
        ''' Gets a list of all deltas and returns in the following format:
            {'id': Delta ID,
             'lastModified': Last modified time,
             'description': Not actually sure what that is,
             'modelID': model ID,
             'reduction': Reduction section of the raw_request,
             'addition': Addition section of the raw_request}
        '''

        deltas = self.delta_table.find()
        parsed_deltas = []

        if deltas == None:
            return parsed_deltas

        # Convert to Endpoint-friendly
        for delta in deltas:
            d = self._convert_delta(delta, True)
            parsed_deltas.append(d)
        return parsed_deltas

    def _convert_delta(self, delta, unpickle=False):
        ''' Helper to convert DB's form to what the endpoints are expecting. '''
        raw_request = delta['raw_request']
        if unpickle:
            raw_request = pickle.loads(str(raw_request))
        reduction = raw_request['reduction']
        addition = raw_request['addition']
            
        d = {'id':delta['delta_id'],
             'lastModified':delta['last_modified'],
             'description':None,
             'modelId':delta['model_id'],
             'reduction':reduction,
             'addition':addition}
        return d
                        
    def _put_delta(self, delta_id, raw_request=None, addition=None,
                   reduction=None, model_id=None, status=None, update=False):
        ''' Helper Function, just puts delta into DB. 
            Overwrites older versions for updates (when update=True). 
            status isn't required for creating: default of HTTP_CREATED will 
            be used.
            Returns Nothing.
            Raises errors.
        '''
        raw_delta = self._get_delta_by_id(delta_id)
        last_modified = self._get_current_time()
        delta = None

        self.dlogger.info("_put_delta() for delta_id %s, update = %s" %
                          (delta_id, update))
        
        # if it's a new entry (update=False)
        #   - There is no existing policy with delta_id==delta_id
        #   - Make sure everything is filled in
        #   - Build dictionary to be inserted into table, including timestamp
        #     and last_modified
        if update == False:
            if raw_delta != None:
                raise SenseAPIError(
                    "Delta with ID %s already exists" % delta_id)
            if status == None:
                status = STATUS_ACCEPTED
            if (addition == None and
                reduction == None):
                raise SenseAPIError(
                    "Delta %s requires at least an addition or a reduction " +
                    "(%s, %s, %s, %s, %s)" %
                    (delta_id, raw_request, addition, reduction, model_id,
                     status))
            if (raw_request == None or
                model_id == None or
                status == None):
                raise SenseAPIError(
                    "Delta %s requires all fields (%s, %s, %s, %s, %s)" %
                    (delta_id, raw_request, addition, reduction, model_id,
                     status))
            delta = {'delta_id':delta_id,
                     'raw_request':pickle.dumps(raw_request),
                     'addition':pickle.dumps(addition),
                     'reduction':pickle.dumps(reduction),
                     'status':status,
                     'last_modified':last_modified,
                     'timestamp':last_modified, #Both of these will be the same
                     'model_id':model_id}
            # insert dictionary into DB
            self.dlogger.debug("Inserting delta %s" % delta_id)                
            self.delta_table.insert(delta)
            
        # else, it's an update (update=True)
        #   - Make sure there is an existing policy with delta_id==delta_id
        #   - Build dictionary to be inserted into table, including
        #     last_modified
        else:
            if raw_delta == None:
                raise SenseAPIError(
                    "No delta with ID %s exists, cannot update." % delta_id)
            delta = {'delta_id':delta_id,
                     'last_modified':last_modified}
            
            rows = []
            if raw_request != None:
                delta['raw_request'] = pickle.dumps(raw_request)
                rows.append('raw_request')
            if addition != None:
                delta['addition'] = pickle.dumps(addition)
                rows.append('addition')
            if reduction != None:
                delta['reduction'] = pickle.dumps(reduction)
                rows.append('reduction')
            if status != None:
                delta['status'] = status
                rows.append('status')
            if model_id != None:
                delta['model_id'] = model_id
                rows.append('model_id')

            if len(rows) == 0:
                raise SenseAPIError(
                    "Updates require one or more parts updated")
                                    
            self.dlogger.debug("Updating delta %s with rows %s" % (delta_id,
                                                                   rows))
            self.delta_table.update(delta, ['delta_id'])

        self.dlogger.debug("_put_delta() successful with ID %s. Update? %s" %
                           (delta_id, update))

    def _get_model_by_id(self, model_id):
        ''' Helper function, just retrieves models based on model_id.
            Returns:
              - None if model_id does not exists.
              - Dictionary containing model. See top of SenseAPI definition for
                keys.
        '''
        raw_model = self.model_table.find_one(model_id=str(model_id))
        if raw_model == None:
            return None
        
        # Unpickle the pickled values and rebuild dictionary to return
        model = {'model_id':raw_model['model_id'],
                 'model_data':raw_model['model_data'],
                 'model_raw_info':pickle.loads(str(
                     raw_model['model_raw_info'])),
                 'timestamp':raw_model['timestamp']}

        self.dlogger.debug('_get_model_by_id() on %s successful' % model_id)
        return model
    
    def _put_model(self, model_id, model_xml, model_raw_info, timestamp=None):
        ''' Helper function, just puts model into DB. No updates allowed. 
            Returns nothing.
            Raises errors.
        '''
        # Check to see if a model with model_id already exists, if so, raise
        # an error.
        if model_id == None:
            raise SenseAPIError("Model ID is necessary.")
        if self._get_model_by_id(model_id) != None:
            raise SenseAPIError("Model with ID %s already exists", model_id)
        
        # Make sure all fields are filled in
        if model_xml == None or model_raw_info == None:
            raise SenseAPIError("Model needs both model_xml and model_raw_info. (%s, %s)" %
                                (model_xml, model_raw_info))
        
        # Build dictionary to be inserted into table, including timestamp
        if timestamp == None:
            timestamp = self._get_current_time()
            
        model = {'model_id':model_id,
                 'model_data':model_xml,
                 'model_raw_info':pickle.dumps(model_raw_info),
                 'timestamp':timestamp}

        # Insert dictionary into DB
        self.dlogger.debug("Inserting model %s" % model_id)
        self.model_table.insert(model)
    
    def _encode_gzip_b64(self, data):
        ''' Helper function that handles gziping then encoding into base64 
            string.
            Based on https://bitbucket.org/berkeleylab/sensenrm-oscars/src/d09db31aecbe7654f03f15eed671c0675c5317b5/sensenrm_server.py?at=master&fileviewer=file-view-default
        '''
        gzip_compress = zlib.compressobj(9, zlib.DEFLATED, zlib.MAX_WBITS | 16)
        gzipped_data = gzip_compress.compress(data) + gzip_compress.flush()
        b64_gzip_data = base64.b64encode(gzipped_data).decode()
        return b64_gzip_data

    def _decode_b64_gunzip(self, data):
        ''' Helper function that handles decoding then unzipping data.
            Based on https://bitbucket.org/berkeleylab/sensenrm-oscars/src/d09db31aecbe7654f03f15eed671c0675c5317b5/sensenrm_server.py?at=master&fileviewer=file-view-default
        '''
        try:
            unzipped_data = zlib.decompress(base64.b64decode(data),
                                        16+zlib.MAX_WBITS)
            return unzipped_data
        except Exception as e:
            self.dlogger.error("_decode_b64_gunzip() error: %s" % e)
            self.dlogger.error("   Data: %s" % data)
            raise SenseAPIB64Error("Error decoding or decompressing: %s\n%s" %
                                   (str(e), data))
    


class SenseAPIResource(Resource):
    ''' Has common pieces for all Resource objects used by the SenseAPI, 
        including logging. '''

    def __init__(self, urlbase,
                 loggeridsuffix, loggeridprefix='sdxcontroller.sense'):
        loggerid = loggeridprefix + "." + loggeridsuffix
        self._setup_loggers(loggerid)
        self.urlbase = urlbase
        super(SenseAPIResource, self).__init__()

    def _setup_loggers(self, loggerid, logfilename=None, debuglogfilename=None):
        ''' Internal function for setting up the logger formats. '''
        # Copied from https://github.com/atlanticwave-sdx/atlanticwave-proto/blob/master/lib/AtlanticWaveModule.py#L49
        import logging
        self.logger = logging.getLogger(loggerid)
        self.dlogger = logging.getLogger("debug." + loggerid)
        if logfilename != None:
            formatter = logging.Formatter('%(asctime)s %(name)-12s: %(thread)s %(levelname)-8s %(message)s')
            console = logging.StreamHandler()
            console.setLevel(logging.WARNING)
            console.setFormatter(formatter)
            logfile = logging.FileHandler(logfilename)
            logfile.setLevel(logging.DEBUG)
            logfile.setFormatter(formatter)
            self.logger.setLevel(logging.DEBUG)
            self.logger.addHandler(console)
            self.logger.addHandler(logfile)

        if debuglogfilename != None:
            formatter = logging.Formatter('%(asctime)s %(name)-12s: %(thread)s %(levelname)-8s %(message)s')
            console = logging.StreamHandler()
            console.setLevel(logging.DEBUG)
            console.setFormatter(formatter)
            logfile = logging.FileHandler(debuglogfilename)
            logfile.setLevel(logging.DEBUG)
            logfile.setFormatter(formatter)
            self.dlogger.setLevel(logging.DEBUG)
            self.dlogger.addHandler(console)
            self.dlogger.addHandler(logfile)

    def dlogger_tb(self):
        ''' Print out the current traceback. '''
        from traceback import format_stack
        tbs = format_stack()
        all_tb = "Traceback: id: %s\n" % str(hex(id(self)))
        for line in tbs:
            all_tb = all_tb + line
        self.dlogger.warning(all_tb)



model_fields = {
    'id': fields.Raw,
    'href': fields.Raw,
    'creationTime': fields.Raw,
    'model': fields.Raw
}

delta_fields = {
    'id': fields.Raw,
    'lastModified': fields.Raw,
    'description': fields.Raw,
    'modelId': fields.Raw,
    'reduction': fields.Raw,
    'addition': fields.Raw
}
        
        

        
class ModelsAPI(SenseAPIResource):#FIXME
    def __init__(self, urlbase):
        super(ModelsAPI, self).__init__(urlbase, self.__class__.__name__)
        self.dlogger.debug("__init__() start")
        self.reqparse = reqparse.RequestParser()
        self.reqparse.add_argument('current', type=str, default='true')
        self.reqparse.add_argument('summary', type=str, default='false')
        self.reqparse.add_argument('encode', type=str, default='false')
        self.model, newbool = SenseAPI().get_latest_model()
        self.dlogger.debug("__init__() complete")
    
    def get(self):
        self.dlogger.debug("get() start")

        retval = [dict(marshal(self.model, model_fields))]
        self.dlogger.debug("get() returning %s" % retval)
        self.logger.info("get() complete")
        return retval
    
    def post(self):
        self.dlogger.debug("post() start")

        args = self.reqparse.parse_args()
        self.dlogger.debug("post() args %s" % args)
        retval = {'models': marshal(self.models, model_fields)}, 201 #FIXME
        
        self.dlogger.debug("post() returning %s" % retval)
        self.dlogger.info("post() complete")
        return retval
    
class DeltasAPI(SenseAPIResource):
    def __init__(self, urlbase):
        super(DeltasAPI, self).__init__(urlbase, self.__class__.__name__)
        self.dlogger.debug("__init__() start")
        self.reqparse = reqparse.RequestParser()
        self.reqparse.add_argument('id', type=str, location='json')
        self.reqparse.add_argument('lastModified', type=str, location='json')
        self.reqparse.add_argument('modelId', type=str, location='json')
        self.reqparse.add_argument('reduction', type=str, location='json')
        self.reqparse.add_argument('addition', type=str, location='json')
        self.deltas = SenseAPI().get_all_deltas()

        self.dlogger.debug("__init__() complete")
    
    def get(self):
        self.dlogger.debug("get() start")
        retval = {'deltas': marshal(self.deltas, delta_fields)}
        
        self.logger.info("get() returning %s" % retval)
        self.dlogger.debug("get() complete")
        return retval
    
    def post(self):
        self.dlogger.debug("post() start")

        args = self.reqparse.parse_args()
        self.logger.info("post() args %s" % args)
        deltas, mystatus = SenseAPI().process_deltas(args)
        self.logger.info("post() results %s" % mystatus)
        self.dlogger.info("post() deltas %s" % deltas)
        rstatus = HTTP_CREATED
        if int(mystatus) != HTTP_GOOD:
            rstatus = mystatus
            
        retval = {'deltas': marshal(deltas, delta_fields)}, rstatus

        self.logger.info("post() returning %s" % str(retval))
        self.logger.debug("post() complete")
        return retval
    
class DeltaAPI(SenseAPIResource):
    def __init__(self, urlbase):
        super(DeltaAPI, self).__init__(urlbase, self.__class__.__name__)
        self.dlogger.debug("__init__() start")
        self.reqparse = reqparse.RequestParser()
        self.reqparse.add_argument('summary', type=str, default='true')
        # Removed, as deltaid is in the URL
        #self.reqparse.add_argument('deltaid', type=str, location='json')
        self.dlogger.debug("__init__() complete")
    
    def get(self, deltaid):
        self.dlogger.debug("get() start")
        self.logger.info("get() deltaid %s" % deltaid)
        status, phase = SenseAPI().get_delta(deltaid)
        self.dlogger.debug("get() %s:%s" % (status, phase))
        retval = {'state': str(status), 'deltaid': str(deltaid)}, HTTP_GOOD
        self.logger.info("get() returning %s" % str(retval))
        self.dlogger.debug("get() complete")
        return retval

class CommitsAPI(SenseAPIResource):
    def __init__(self, urlbase):
        super(CommitsAPI, self).__init__(urlbase, self.__class__.__name__)
        self.dlogger.debug("__init__() start")
        self.dlogger.debug("__init__() complete")

    def put(self, deltaid):
        self.dlogger.debug("put() start")
        self.logger.info("put() deltaid %s" % deltaid)
        resp = SenseAPI().commit(deltaid)
        retval = {'result': True}, resp
        self.logger.info("put() returning %s" % str(retval))
        self.dlogger.debug("put() complete")
        return retval

