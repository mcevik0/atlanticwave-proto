from mininet.topo import Topo
from mininet.net import Containernet
from mininet.link import TCLink
from mininet.util import custom
from mininet.node import RemoteController, Host
from mininet.cli import CLI

from docker.types import Mount

# This runs multiple switch, each with three hosts at easy to read formats.
# LAX and NYC have their own Local Controllers, while ORD and ATL share a
# single local controller

# To run (in 3 separate terminals) the topology and two controllers.
#   cd ~/atlanticwave-proto/demo
#   sudo python demo-multi-site.py
#
#   cd ~/atlanticwave-proto/sdxctlr
#   python SDXController.py
#
#   cd ~/atlanticwave-proto/
#   python LocalController.py
#

# From: https://github.com/mininet/mininet/blob/master/examples/vlanhost.py

class VLANHost( Host ):
    "Host connected to VLAN interface"

    def config( self, vlan=100, **params ):
        """Configure VLANHost according to (optional) parameters:
           vlan: VLAN ID for default interface"""

        r = super( VLANHost, self ).config( **params )

        intf = self.defaultIntf()
        # remove IP from default, "physical" interface
        self.cmd( 'ifconfig %s inet 0' % intf )
        # create VLAN interface
        self.cmd( 'vconfig add %s %d' % ( intf, vlan ) )
        # assign the host's IP to the VLAN interface
        self.cmd( 'ifconfig %s.%d inet %s' % ( intf, vlan, params['ip'] ) )
        # update the intf name and host's intf map
        newName = '%s.%d' % ( intf, vlan )
        # update the (Mininet) interface to refer to VLAN interface name
        intf.name = newName
        # add VLAN interface to host's name to intf map
        self.nameToIntf[ newName ] = intf

        return r

hosts = { 'vlan': VLANHost }

def MultiSite():
    ''' This is the topology that we will be building here.


    11         12         13                  21         22         23
+-------+  +-------+  +-------+           +-------+  +-------+  +-------+
|  H1   |  |  H2   |  |  H3   |           |  H4   |  |  H5   |  |  H6   |
+---+---+  +---+---+  +---+---+           +---+---+  +---+---+  +---+---+
  1 |        1 |        1 |                 1 |        1 |        1 |
    |   1      | 2        | 3                 |   1      | 2        | 3
    +------+---+---+------+                   +------+---+---+------+
           |       |                                 |       |
           |  S1   +---------------------------------+  S2   |
           |       |      5                     5    |       |
        +--+-------+--+                              +---+---+
        | 10       11 |                                  | 10
        |             |                                  |
     +--+---+     +---+--+                            +--+---+
     |  LC1 |     |  SDX |                            |  LC2 |
     +------+     +------+                            +------+
       .100         .200                                .101


'''


    # Hosts and switches
    net = Containernet(topo=None, build=False)
    s1switch = net.addSwitch('s1', listenPort=6680, mac='00:00:00:00:00:01')
    s2switch = net.addSwitch('s2', listenPort=6681, mac='00:00:00:00:00:02')

    h1 = net.addHost('laxh1', mac='00:00:00:00:11:00',
                        cls=VLANHost, vlan=11)
    h2 = net.addHost('laxh2', mac='00:00:00:00:12:00',
                        cls=VLANHost, vlan=12)
    h3 = net.addHost('laxh3', mac='00:00:00:00:13:00',
                        cls=VLANHost, vlan=13)
    h4 = net.addHost('ordh1', mac='00:00:00:00:21:00',
                        cls=VLANHost, vlan=21)
    h5 = net.addHost('ordh2', mac='00:00:00:00:22:00',
                        cls=VLANHost, vlan=22)
    h6 = net.addHost('ordh3', mac='00:00:00:00:23:00',
                        cls=VLANHost, vlan=23)

    # Controller containers
    sdx_env = {"MANIFEST":"/containernet.manifest", "IPADDR":"0.0.0.0",
               "PORT":"5000", "LCPORT":"5555"}
    sdx_pbs = {5000:5000}
    sdx_mounts = [Mount("/dev", "~/dev", "bind")]
    sdxctlr = net.addDocker('sdxctlr', ip='10.0.0.200', dimage="sdx_container",
                            environment=sdx_env, port_bindings=sdx_pbs,
                            mounts=sdx_mounts)
    
    lc1_env = {"MANIFEST":"/containernet.manifest", "SITE":"westctlr",
               "SDXIP":"10.0.0.200"}
    lc1_pbs = {6680:6680}
    lc1_mounts = sdx_mounts
    lc1 = net.addDocker('westctlr', ip='10.0.0.100', dimage="lc_container",
                        environment=lc1_env, port_bindings=lc1pbs,
                        mounts=lc1_mounts)

    lc2_env = {"MANIFEST":"/containernet.manifest", "SITE":"westctlr",
                  "SDXIP":"10.0.0.200"}
    lc2_pbs = {6681:6681}
    lc2_mounts = sdx_mounts
    lc2 = net.addDocker('centctlr', ip='10.0.0.101', dimage="lc_container",
                        environmeqnt=lc2_env, port_bindings=lc2pbs,
                        mounts=lc2_mounts)


    # Host Wiring
    net.addLink(s1switch, h1, port1=1)
    net.addLink(s1switch, h2, port1=2)
    net.addLink(s1switch, h3, port1=3)
    net.addLink(s2switch, h4, port1=1)
    net.addLink(s2switch, h5, port1=2)
    net.addLink(s2switch, h6, port1=3)


    # Switch Wiring
    net.addLink(s1switch, s2switch, port1=5, port2=5)

    # Controller wiring
    net.addLink(s1switch, lc1, port1=10)
    net.addLink(s1switch, sdxctlr, port1=11)
    net.addLink(s2switch, lc2, port1=10

    # Add controllers
    # https://stackoverflow.com/questions/23677291/how-to-connect-different-switches-to-different-remote-controllers-in-mininet

    lc1ctlr = net.addController('c1', controller=RemoteController, 
                                 ip='127.0.0.1', port=6680)
    lc2ctlr = net.addController('c2', controller=RemoteController, 
                                 ip='127.0.0.1', port=6681)

    net.build()
    print "net.build"
    
    net.start()
    print "net.start"
    CLI(net)
    print "CLI(net)"
    net.stop()
    print "net.stop"


if __name__ == '__main__':
    MultiSite()
