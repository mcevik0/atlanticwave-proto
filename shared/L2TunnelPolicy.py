from __future__ import print_function
from __future__ import absolute_import
# Copyright 2016 - Sean Donovan
# AtlanticWave/SDX Project


from shared.UserPolicy import *
from datetime import datetime
import sys
from shared.constants import *
from shared.VlanTunnelLCRule import VlanTunnelLCRule
from shared.PathResource import VLANPathResource, BandwidthPathResource,  VLANPortResource, BandwidthPortResource

class L2TunnelPolicy(UserPolicy):
    ''' This policy is for network administrators to create L2 tunnels, similar 
        to NSI tunnels.
        It requires the following information to create a tunnel:
          - Start time
          - End time
          - Src Switch
          - Dst Switch
          - Src Port
          - Dst Port 
          - Src VLAN
          - Dst VLAN
          - Bandwidth

        Example Json:
        {"L2Tunnel":{
            "starttime":"1985-04-12T23:20:50",
            "endtime":"1985-04-12T23:20:50+0400",
            "srcswitch":"atl-switch",
            "dstswitch":"mia-switch",
            "srcport":5,
            "dstport":7,
            "srcvlan":1492,
            "dstvlan":1789,
            "bandwidth":1}}
        Times are RFC3339 formated offset from UTC, if any, is after the seconds
        Bandwidth is in kbit/sec

        Side effect of coming from JSON, everything's unicode. Need to handle 
        parsing things into the appropriate types (int, for instance).
    '''

    def __init__(self, username, json_policy):
        self.start_time = None
        self.stop_time = None
        self.src_switch = None
        self.dst_switch = None
        self.src_port = None
        self.dst_port = None
        self.src_vlan = None
        self.dst_vlan = None
        self.bandwidth = None

        # Derived values
        self.intermediate_vlan = None
        self.fullpath = None

        # For get_endpoints()
        self.endpoints = []
        
        super(L2TunnelPolicy, self).__init__(username, json_policy)

        # Anything specific here?
        pass
    
    def __str__(self):
        return "%s(%s,%s,SRC(%s,%s,%s),DST(%s,%s,%s),%s" % (
            self.get_policy_name(), self.start_time, self.stop_time,
            self.src_switch, self.src_port, self.src_vlan,
            self.dst_switch, self.dst_port, self.dst_vlan,
            self.bandwidth)

    def __eq__(self, other):
        if (type(self) != type(other) or
            self.start_time != other.start_time or
            self.stop_time != other.stop_time or
            self.bandwidth != other.bandwidth):
            return False

        # Src and Dst could be flipped. Same thing, just backwards.
        return ((self.src_switch == other.src_switch and
                 self.src_port == other.src_port and
                 self.src_vlan == other.src_vlan and
                 self.dst_switch == other.dst_switch and
                 self.dst_port == other.dst_port and
                 self.dst_vlan == other.dst_vlan) or
                (self.src_switch == other.dst_switch and
                 self.src_port == other.dst_port and
                 self.src_vlan == other.dst_vlan and
                 self.dst_switch == other.src_switch and
                 self.dst_port == other.src_port and
                 self.dst_vlan == other.src_vlan))

    @classmethod
    def check_syntax(cls, json_policy):
        try:
            # Make sure the times are the right format
            # https://stackoverflow.com/questions/455580/json-datetime-between-python-and-javascript
            jsonstring = cls.get_policy_name()
            starttime = datetime.strptime(json_policy[jsonstring]['starttime'],
                                         rfc3339format)
            endtime = datetime.strptime(json_policy[jsonstring]['endtime'],
                                         rfc3339format)
            src_switch = json_policy[jsonstring]['srcswitch']
            dst_switch = json_policy[jsonstring]['dstswitch']
            src_port = int(json_policy[jsonstring]['srcport'])
            dst_port = int(json_policy[jsonstring]['dstport'])
            src_vlan = int(json_policy[jsonstring]['srcvlan'])
            dst_vlan = int(json_policy[jsonstring]['dstvlan'])
            bandwidth = int(json_policy[jsonstring]['bandwidth'])

            delta = endtime - starttime
            if delta.total_seconds() < 0:
                raise UserPolicyValueError("Time ends before it begins: begin %s, end %s" % (starttime, endtime))

            if ((src_port < 0) or
                (src_port > 24)):
                raise UserPolicyValueError("src_port is out of range %d" %
                                           src_port)
            if ((dst_port < 0) or
                (dst_port > 24)):
                raise UserPolicyValueError("dst_port is out of range %d" %
                                           dst_port)
            if ((src_vlan < 0) or
                (src_vlan > 4090)):
                raise UserPolicyValueError("src_vlan is out of range %d" %
                                           src_vlan)
            if ((dst_vlan < 0) or
                (dst_vlan > 4090)):
                raise UserPolicyValueError("dst_vlan is out of range %d" %
                                           dst_vlan)
        except Exception as e:
            import os
            exc_type, exc_obj, exc_tb = sys.exc_info()
            filename = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
            lineno = exc_tb.tb_lineno
            print("%s: Exception %s at %s:%d" % (cls.get_policy_name(),
                                                 str(e), filename,lineno))
            raise
        
    def breakdown_policy(self, tm, ai):
        self.breakdown = []
        self.resources = []
        topology = tm.get_topology()
        authorization_func = ai.is_authorized
        # Get a path from the src_switch to the dst_switch form the topology
        #FIXME: This needs to be updated to get *multiple* options
        self.fullpath = tm.find_valid_path(self.src_switch,
                                           self.dst_switch,
                                           self.bandwidth)
        if self.fullpath == None:
            raise UserPolicyError("There is no available path between %s and %s for bandwidth %s" % (self.src_switch, self.dst_switch, self.bandwidth))

        #nodes = topology.nodes(data=True)
        #edges = topology.edges(data=True)
        #import json
        #print "NODES:"
        #print json.dumps(nodes, indent=2)
        #print "\n\nEDGES:"
        #print json.dumps(edges, indent=2)
        
        # Get a VLAN to use
        # Topology manager should be able to provide this for us. 
        self.intermediate_vlan = tm.find_vlan_on_path(self.fullpath)
        if self.intermediate_vlan == None:
            raise UserPolicyError(
                "There are no available VLANs on path %s for policy %s" %
                (self.fullpath, self))

        # Add necessary resource
        self.resources.append(VLANPathResource(self.fullpath,
                                               self.intermediate_vlan))
        self.resources.append(VLANPortResource(self.src_switch,
                                               self.src_port,
                                               self.src_vlan))
        self.resources.append(VLANPortResource(self.dst_switch,
                                               self.dst_port,
                                               self.dst_vlan))
        self.resources.append(BandwidthPathResource(self.fullpath,
                                                    self.bandwidth))
        self.resources.append(BandwidthPortResource(self.src_switch,
                                                    self.src_port,
                                                    self.bandwidth))
        self.resources.append(BandwidthPortResource(self.dst_switch,
                                                    self.dst_port,
                                                    self.bandwidth))

        # Fill out self.endpoints
        self.endpoints = []
        self.endpoints.append((self.src_switch,
                               tm.get_switch_port_neighbor(self.src_switch,
                                                           self.src_port),
                               self.src_vlan))
        self.endpoints.append((self.dst_switch,
                               tm.get_switch_port_neighbor(self.dst_switch,
                                                           self.dst_port),
                               self.dst_vlan))
        
        # Special case: Single node:
        if len(self.fullpath) == 1:
            if (self.src_switch != self.dst_switch):
                raise UserPolicyValueError(
                    "Path length is 1, but switches are different: fullpath %s, src_switch %s, dst_switch %s" %
                    (self.fullpath, src_switch, dst_switch))
                
            location = self.src_switch
            shortname = topology.node[location]['locationshortname']
            switch_id = topology.node[location]['dpid']
            inport = self.src_port
            outport = self.dst_port
            invlan = self.src_vlan
            outvlan = self.dst_vlan
            bandwidth = self.bandwidth

            bd = UserPolicyBreakdown(shortname, [])

            rule = VlanTunnelLCRule(switch_id, inport, outport, invlan, outvlan,
                                    True, bandwidth)
            bd.add_to_list_of_rules(rule)
            self.breakdown.append(bd)            
            return self.breakdown

        
        # Create breakdown rule for this node

        # First and last are different, due to the VLAN translation necessary
        # on the outbound path, handle them separately.
        #  - on inbound, match on the switch, port, and local VLAN
        #               action set VLAN to intermediate, fwd
        #  - on outbound, match on the switch, port, intermediate VLAN
        #               action set VLAN to local VLAN, fwd
        srcpath = self.fullpath[1]   # Next one after src
        dstpath = self.fullpath[-2]  # One prior to dst
        for location, inport, invlan, path in [(self.src_switch, self.src_port,
                                                self.src_vlan, srcpath),
                                               (self.dst_switch, self.dst_port,
                                                self.dst_vlan, dstpath)]:
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
        
        
        # Loop through the intermediary nodes in the path. Python's smart, so
        # the slicing that's happening just works, even if there are only two
        # locations in the path. Magic!
        for (prevnode, node, nextnode) in zip(self.fullpath[0:-2], 
                                              self.fullpath[1:-1], 
                                              self.fullpath[2:]):
            # Need inbound and outbound rules for the VLAN that's being used,
            # Don't need to modify packet.
            #  - on inbound, match on the switch, port, and intermediate VLAN
            #               action set fwd
            #  - on outbound, match on the switch, port, and intermediate VLAN
            #               action set fwd
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

    def _get_neighbor(self, topo, node, port):
        ''' helper function that gets the name of the neighbor '''
        for n in topo[node].keys():
            if topo[node][n][node] == port:
                return n

        # This shouldn't happen...
        return None

    
    def check_validity(self, tm, ai):
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

        self.start_time = json_policy[jsonstring]['starttime']
        self.stop_time =  json_policy[jsonstring]['endtime']
        # Make sure end is after start and after now.
        #FIXME

        self.src_switch = str(json_policy[jsonstring]['srcswitch'])
        self.dst_switch = str(json_policy[jsonstring]['dstswitch'])
        self.src_port = int(json_policy[jsonstring]['srcport'])
        self.dst_port = int(json_policy[jsonstring]['dstport'])
        self.src_vlan = int(json_policy[jsonstring]['srcvlan'])
        self.dst_vlan = int(json_policy[jsonstring]['dstvlan'])
        self.bandwidth = int(json_policy[jsonstring]['bandwidth'])

        #FIXME: Really need some type verifications here.
    
        
    
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


