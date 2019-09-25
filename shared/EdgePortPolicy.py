from __future__ import print_function
from __future__ import absolute_import
# Copyright 2017 - Sean Donovan
# AtlanticWave/SDX Project


from .UserPolicy import *
from datetime import datetime
from shared.constants import *
from .EdgePortLCRule import *
import networkx as nx

class EdgePortPolicy(UserPolicy):
    ''' This policy is used during initialization of the LocalController to let 
        it know which ports of it are edge ports. This is necessary for proper
        learning of new paths to occur without redundant "new destination" 
        messages coming in from switch-to-switch ports. 

        It requires the following information at intialization:
          - Switch

        Example Json:
        {"EdgePort":{
            "switch":"mia-switch"}}
    
        The vast majority of the work is handled by the breakdown_rule() function
        which uses the topology to determine which ports are actually the edge 
        ports.    
    ''' 

    def __init__(self, username, json_policy):
        self.switch = None

        super(EdgePortPolicy, self).__init__(username,
                                             json_policy)

        # Anything specific here?
        pass

    def __str__(self):
        return "%s(%s)" % (self.get_policy_name(), self.switch)
    
    @classmethod
    def check_syntax(cls, json_policy):
        try:
            # Make sure the times are the right format
            # https://stackoverflow.com/questions/455580/json-datetime-between-python-and-javascript

            switch = json_policy[cls.get_policy_name()]['switch']

        except Exception as e:
            import os
            exc_type, exc_obj, exc_tb = sys.exc_info()
            filename = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
            lineno = exc_tb.tb_lineno
            print("%s: Exception %s at %s:%d" % (self.get_policy_name(),
                                                 str(e), filename,lineno))
            raise
            
    def breakdown_policy(self, tm, ai):
        ''' There are two stages to breaking down these policies:
              - determine edge ports for the local switch
              - create EdgePortLCRules for each edge port
            To determine which ports are edge port, we look at each port and see
            what type the neighbor is. If they are a "switch" type, then that's
            an internal port, otherwise, it's an edge port.
        '''

        self.breakdown = []
        topology = tm.get_topology()
        authorization_func = ai.is_authorized
        switch_id = topology.node[self.switch]['dpid']
        shortname = topology.node[self.switch]['locationshortname']

        bd = UserPolicyBreakdown(shortname, [])

        for neighbor in topology.neighbors(self.switch):
            if topology.node[neighbor]['type'] == "switch":
                continue
            # Not a switch neighbor, so it's an edge port
            edge_port = topology[self.switch][neighbor][self.switch]
            
            epr = EdgePortLCRule(switch_id, edge_port)
            bd.add_to_list_of_rules(epr)
        
        self.breakdown.append(bd)
        return self.breakdown

    
    def check_validity(self, tm, ai):
        #FIXME: This is going to be skipped for now, as we need to figure out
        #what's authorized and what's not.
        return True

    def _parse_json(self, json_policy):
        jsonstring = self.policytype
        if type(json_policy) is not dict:
            raise UserPolicyTypeError(
                "json_policy is not a dictionary:\n    %s" % json_policy)
        if jsonstring not in json_policy.keys():
            raise UserPolicyValueError(
                "%s value not in entry:\n    %s" % ('policys', json_policy))

        self.switch = str(json_policy[jsonstring]['switch'])

        #FIXME: Really need some type verifications here.
        
    
    def pre_add_callback(self, tm, ai):
        ''' This is called before a policy is added to the database. For 
            instance, if certain resources need to be locked down or policiess 
            authorized, this can do it. May not need to be implemented. '''
        pass

    def pre_remove_callback(self, tm, ai):
        ''' This is called before a policy is removed from the database. For 
            instance, if certain resources need to be released, this can do it.
            May not need to be implemented. '''

        pass

        




