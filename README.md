ewj@UbuntuVM:~/Documents/x2410-main$ sudo python3 simple-topo.py 
Traceback (most recent call last):
  File "/home/ewj/Documents/x2410-main/simple-topo.py", line 32, in <module>
    net = Mininet( topo=topo, link=TCLink )
  File "/usr/lib/python3/dist-packages/mininet/net.py", line 178, in __init__
    self.build()
  File "/usr/lib/python3/dist-packages/mininet/net.py", line 508, in build
    self.buildFromTopo( self.topo )
  File "/usr/lib/python3/dist-packages/mininet/net.py", line 475, in buildFromTopo
    self.addController( 'c%d' % i, cls )
  File "/usr/lib/python3/dist-packages/mininet/net.py", line 291, in addController
    controller_new = controller( name, **params )
  File "/usr/lib/python3/dist-packages/mininet/node.py", line 1592, in DefaultController
    raise Exception( 'Could not find a default OpenFlow controller' )
Exception: Could not find a default OpenFlow controller
