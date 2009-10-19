import os
import sys

from twisted.application import service
from twisted.words.protocols.jabber import component

import settings
from component.wavefederationhost import WaveFederationHost
#from component.wavefederationremote import WaveFederationRemote
from component.logservice import LogService

# add permission for pygowave_server to the federation queue
# rabbitmqctl add_user pygowave_xmpp pygowave_xmpp 
# rabbitmqctl set_permissions pygowave_xmpp '^[^.]+\.[^.]+\.waveop$|^federation$|^wavelet\.(topic|direct)$' '^[^.]+\.[^.]+\.waveop$|^federation$|^wavelet\.direct$' '^[^.]+\.[^.]+\.waveop$|^federation$|^wavelet\.(topic|direct)$'

application = service.Application("pygowave-federation")

# set up Jabber Component
sm = component.buildServiceManager(settings.JABBERID, settings.JABBER_PASSWORD, ("tcp:127.0.0.1:5275" ))

# Turn on verbose mode
LogService().setServiceParent(sm)

# set up our Service
s = WaveFederationHost()
s.setServiceParent(sm)

sm.setServiceParent(application)

