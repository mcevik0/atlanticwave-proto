from __future__ import absolute_import
# Copyright 2016 - Sean Donovan
# AtlanticWave/SDX Project


from lib.AtlanticWaveInspector import AtlanticWaveInspector
from .AuthorizationInspector import AuthorizationInspector 
from .TopologyManager import TopologyManager

class ValidityInspectorError(Exception):
    ''' Parent class, can be used as a catch-all for the other errors '''
    pass

class ValidityInspectorNotValidPolicy(ValidityInspectorError):
    ''' Raised when a policy is not valid. Policy cannot be installed. '''
    pass

class ValidityInspectorOverlappingPolicy(ValidityInspectorError):
    ''' Raised when a policy overlaps another policy, but is of different 
        priority. Policy can be installed, but may not have the indented effect.
    '''
    pass

class ValidityInspector(AtlanticWaveInspector):
    ''' The ValidityInspector will verify that a particular policy is valid. For
        instance, confirming that port 16 exists at a given location. To handle 
        validation, external information will be needed. As an example, 
        information about physical setup at each location may be provided by the
        LocalControllerManager. How this is done is not decided as of this 
        writing, and may introduce more links into the diagram above.
        Singleton. '''

    def __init__(self, loggeridprefix='sdxcontroller'):
        loggerid = loggeridprefix + '.validityinspector'
        super(ValidityInspector, self).__init__(loggerid)
        
        self.logger.warning("%s initialized: %s" % (self.__class__.__name__,
                                                    hex(id(self))))

    def is_valid_policy(self, policy):
        ''' Checks to see if a policy is valid. True if valid. Raises error 
            describing problem if invalid. '''
        #FIXME: I am confused. I cannot find an object named 'policy' anywhere
        #and doing a search in the filesystem for objects that call
        #"check_validity" just takes me back here. I need some clarification
        #please.
        return policy.check_validity(TopologyManager().get_topology(),
                                   AuthorizationInspector().is_authorized)

