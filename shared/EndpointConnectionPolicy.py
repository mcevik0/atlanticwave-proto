from __future__ import print_function
from __future__ import absolute_import
# Copyright 2017 - Sean Donovan
# AtlanticWave/SDX Project


from shared.UserPolicy import *
from shared.L2TunnelPolicy import *
from datetime import datetime
import networkx as nx
from shared.PathResource import VLANPathResource, BandwidthPathResource
from shared.constants import *
from math import ceil


class EndpointConnectionPolicy(UserPolicy):
    ''' This policy is for connecting endpoints easily via L2 tunnels. It it 
        based on the L2TunnelPolicy, but requires less information provided by
        the user.

        It requires the following information to create a connection:
          - Deadline
          - Src endpoint
          - Dst endpoint
          - Data-Quantity

        Internally, we care about start time, end time, and bandwidth, however 
        this may not be something that a domain scientists will understand or
        care about. As such, translating from their external representation to
        what we care about is easy: some division and adjusting for some leeway
        will determine an end time.
   
        FIXME: Should this be more generous in options? That is, if the users
        actually know what the start and end times should, allow them to create
        those? 
   
        FIXME: Recurrant items too!

        Example Json:
        {"EndpointConnection":{
            "deadline":"1985-04-12T23:20:50",
            "srcendpoint":"atlh1",
            "dstendpoint":"miah2",
            "dataquantity":57000000000}}
        Time is RFC3339 formated offset from UTC, if any, is after the seconds
        dataquantity is number of bytes that need to be transferred, so ~57GB
          is seen here.

        Side effect of coming from JSON, everything's unicode. Need to handle 
        parsing things into the appropriate types (int, for instance).    
    '''
    buffer_time_sec = 300
    buffer_bw_percent = 1.05

    def __init__(self, username, json_policy):
        # From JSON
        self.deadline = None
        self.src = None
        self.dst = None
        self.data = None


        # Derived values:
        self.bandwidth = None
        self.intermediate_vlan = None
        self.fullpath = None

        # for get_endpoints()
        self.endpoints = []

        super(EndpointConnectionPolicy, self).__init__(username,
                                                       json_policy)

        print("Passed: %s:%s:%s:%s:%s:%s:%s" % (self.deadline,
                                                self.src,
                                                self.dst,
                                                self.data,
                                                self.bandwidth,
                                                self.intermediate_vlan,
                                                self.fullpath))
        # Second
        pass

    def __str__(self):
        return "%s(%s,%s,%s,%s)" % (self.get_policy_name(), self.deadline,
                                    self.src, self.dst, self.data)

    @classmethod
    def check_syntax(cls, json_policy):
        try:
            jsonstring = cls.get_policy_name()
            deadline = datetime.strptime(json_policy[jsonstring]['deadline'],
                                         rfc3339format)
            src = json_policy[jsonstring]['srcendpoint']
            dst = json_policy[jsonstring]['dstendpoint']
            data = json_policy[jsonstring]['dataquantity']

            if type(data) != int:
                raise UserPolicyTypeError("data is not an int: %s:%s" %
                                          (str(data), type(data)))
            #FIXME: checking on src and dst to see if they're strings?
        except Exception as e:
            import os
            exc_type, exc_obj, exc_tb = sys.exc_info()
            filename = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
            lineno = exc_tb.tb_lineno
            print("%s: Exception %s at %s:%d" % (self.get_policy_name(),
                                                 str(e), filename,lineno))
            raise

    def breakdown_policy(self, tm, ai):
        # There is a lot of logic borrowed from L2TunnelPolicy's version of
        # breakdown_policy, but there are some significant differences.
        self.breakdown = []
        self.resources = []
        topology = tm.get_topology()
        authorization_func = ai.is_authorized
        
        # First, find out the bandwidth requirements
        total_time = (datetime.strptime(self.deadline, rfc3339format) - 
                  datetime.now()).total_seconds()
        if total_time == EndpointConnectionPolicy.buffer_time_sec or total_time == 0:
            # This adjustment is to prevent 0 denominators in the next formulas
            total_time += 1

        data_in_bits = self.data * 8
        self.bandwidth = int(ceil(max(data_in_bits/(total_time - EndpointConnectionPolicy.buffer_time_sec),
                                      (data_in_bits/total_time)*EndpointConnectionPolicy.buffer_bw_percent)))

        # Second, get the path, and reserve bw and a VLAN on it
        self.switchpath = tm.find_valid_path(self.src, self.dst,
                                             self.bandwidth, True)
        if self.switchpath == None:
            raise UserPolicyError("There is no available path between %s and %s for bandwidth %s" % (self.src, self.dst, self.bandwidth))
        
        # Switchpath is the path between endpoint switches. self.src and
        # self.dst are hosts, not switches, so they're not useful for certain
        # things.
        self.fullpath = [self.src] + self.switchpath + [self.dst]

        self.intermediate_vlan = tm.find_vlan_on_path(self.switchpath)
        if self.intermediate_vlan == None:
            raise UserPolicyError("There are no available VLANs on path %s for policy %s" % (self.fullpath, self))
        
        # Third, build the breakdown policies for the path.
        # This section is heavily based on the L2TunnelPolicy.breakdown_policy()

        # Single switch case:
        if len(self.switchpath) == 1:
            location = self.switchpath[0]
            shortname = topology.node[location]['locationshortname']
            switch_id = topology.node[location]['dpid']
            inedge  = topology.edge[location][self.src]
            outedge = topology.edge[location][self.dst]
            inport  = inedge[location]
            outport = outedge[location]
            invlan  = int(topology.node[self.src]['vlan'])
            outvlan = int(topology.node[self.dst]['vlan'])
            bandwidth = self.bandwidth

            # Add to self.endpoints
            self.endpoints.append((self.src, inedge, invlan))
            self.endpoints.append((self.dst, outedge, outvlan))
            bd = UserPolicyBreakdown(shortname, [])

            rule = VlanTunnelLCRule(switch_id, inport, outport, invlan, outvlan,
                                    True, bandwidth)
            bd.add_to_list_of_rules(rule)
            self.breakdown.append(bd)

            # Enumerate resources
            self.resources.append(VLANPathResource(self.switchpath,
                                                   self.intermediate_vlan))
            self.resources.append(VLANPathResource((location,self.src),
                                                   src_vlan))
            self.resources.append(VLANPathResource((location,self.dst),
                                                   dst_vlan))
            self.resources.append(BandwidthPathResource(self.fullpath,
                                                        self.bandwidth))
            return self.breakdown



        # Multi-switch case, endpoints:
        src_switch = self.switchpath[0]
        dst_switch = self.switchpath[-1]
        src_edge = topology.edge[src_switch][self.src]
        dst_edge = topology.edge[dst_switch][self.dst]
        src_port = src_edge[src_switch]
        dst_port = dst_edge[dst_switch]
        src_vlan = int(topology.node[self.src]['vlan'])
        dst_vlan = int(topology.node[self.dst]['vlan'])
        srcpath = self.switchpath[1]
        dstpath = self.switchpath[-2]

        # Add to self.endpoints
        self.endpoints.append((self.src, src_edge, src_vlan))
        self.endpoints.append((self.dst, dst_edge, dst_vlan))

        # Enumerate resources
        self.resources.append(VLANPathResource(self.switchpath,
                                               self.intermediate_vlan))
        self.resources.append(VLANPathResource((src_switch,self.src),
                                               src_vlan))
        self.resources.append(VLANPathResource((dst_switch,self.dst),
                                               dst_vlan))
        self.resources.append(BandwidthPathResource(self.fullpath,
                                                    self.bandwidth))
        

        for location, inport, invlan, path in [(src_switch, src_port,
                                                src_vlan, srcpath),
                                               (dst_switch, dst_port,
                                                dst_vlan, dstpath)]:
            shortname = topology.node[location]['locationshortname']
            switch_id = topology.node[location]['dpid']
            bandwidth = self.bandwidth
            
            bd = UserPolicyBreakdown(shortname, [])

            # get edge
            edge = topology.edge[location][path]
            outport = edge[location]


            rule = VlanTunnelLCRule(switch_id, inport, outport, 
                                    invlan, self.intermediate_vlan,
                                    True, bandwidth)

            bd.add_to_list_of_rules(rule)

            self.breakdown.append(bd)

        # Multi-switch case, midpoints:
        for (prevnode, node, nextnode) in zip(self.switchpath[0:-2],
                                              self.switchpath[1:-1],
                                              self.switchpath[2:]):

            shortname = topology.node[node]['locationshortname']
            switch_id = topology.node[node]['dpid']
            bandwidth = self.bandwidth

            bd = UserPolicyBreakdown(shortname, [])

            # get edges
            prevedge = topology.edge[prevnode][node]
            nextedge = topology.edge[node][nextnode]

            inport = prevedge[node]
            outport = nextedge[node]

            rule = VlanTunnelLCRule(switch_id, inport, outport,
                                    self.intermediate_vlan,
                                    self.intermediate_vlan,
                                    True, bandwidth)            

            bd.add_to_list_of_rules(rule)

            # Add the four new rules created above to the breakdown
            self.breakdown.append(bd)
        
        # Return the breakdown, now that we've finished.
        return self.breakdown


    def check_validity(self, topology, authorization_func):
        #FIXME: This is going to be skipped for now, as we need to figure out what's authorized and what's not.
        return True

    def _parse_json(self, json_policy):
        jsonstring = self.policytype
        if type(json_policy) is not dict:
            raise UserPolicyTypeError(
                "json_policy is not a dictionary:\n    %s" % json_policy)
        if jsonstring not in json_policy.keys():
            raise UserPolicyValueError(
                "%s value not in entry:\n    %s" % ('policies', json_policy))

        self.deadline = str(json_policy[jsonstring]['deadline'])
        self.src = str(json_policy[jsonstring]['srcendpoint'])
        self.dst = str(json_policy[jsonstring]['dstendpoint'])
        self.data = int(json_policy[jsonstring]['dataquantity'])




    def pre_add_callback(self, tm, ai):
        ''' This is called before a policy is added to the database. For 
            instance, if certain resources need to be locked down or policies 
            authorized, this can do it. May not need to be implemented. '''
        pass

    def pre_remove_callback(self, tm, ai):
        ''' This is called before a policy is removed from the database. For 
            instance, if certain resources need to be released, this can do it.
            May not need to be implemented. '''
        pass

    def get_endpoints(self):
        return self.endpoints
    
    def get_bandwidth(self):
        return self.bandwidth
