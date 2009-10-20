# -*- coding: utf8 -*-
"""

 PyGoWave Server - The Python Google Wave Server
 Copyright 2009 Patrick Schneider <patrick.p2k.schneider@gmail.com>

 PyGoWave XMPP component service.
 Copyright 2009 Markus Wagner  <murk@ferrum-et-magica.de>

 Licensed under the Apache License, Version 2.0 (the "License");
 you may not use this file except in compliance with the License.
 You may obtain a copy of the License at

     http://www.apache.org/licenses/LICENSE-2.0

 Unless required by applicable law or agreed to in writing, software
 distributed under the License is distributed on an "AS IS" BASIS,
 WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 See the License for the specific language governing permissions and
 limitations under the License.

"""

from twisted.words.protocols.jabber import jid, xmlstream, component
from twisted.words.xish import domish, xpath


PRESENCE = '/presence' # this is an global xpath query to use in an observer
MESSAGE  = '/message'  # message xpath 
IQ       = '/iq'       # iq xpath

NS_XMPP_RECEIPTS = "urn:xmpp:receipts";
NS_DISCO_INFO = "http://jabber.org/protocol/disco#info";
NS_DISCO_ITEMS = "http://jabber.org/protocol/disco#items";
NS_PUBSUB = "http://jabber.org/protocol/pubsub";
NS_PUBSUB_EVENT = "http://jabber.org/protocol/pubsub#event";
NS_WAVE_SERVER = "http://waveprotocol.org/protocol/0.2/waveserver";


class WaveFederationService(component.Service):
    """
    Common class for WaveFederationHost and WaveFederationRemote

    """


    def __init__(self):
        # XEP-0184 says we MUST include the feature if we use/support it
        self.features = { 'urn:xmpp:receipts': None
        }
        # No registration support for now
        # self.registrationManager = register.RegistrationManager(self)


    def componentConnected(self, xmlstream):
        """
        This method is called when the componentConnected event gets called.
        That event gets called when we have connected and authenticated with the XMPP server.
        """

        self.jabberId = xmlstream.authenticator.otherHost
        self.xmlstream = xmlstream # set the xmlstream so we can reuse it
        
        xmlstream.addObserver(PRESENCE, self.onPresence, 1)
        xmlstream.addObserver(IQ, self.onIq, 1)
        xmlstream.addObserver(MESSAGE, self.onMessage, 1)
        #TODO: maybe add support for XCP Component Presence


    def onMessage(self, msg):
        """
        Act on the message stanza that has just been received (Stub).

        """
        pass

        
    def onIq(self, iq):
        """
        Act on the iq stanza that has just been received (Stub).

        """
        pass


    def onPresence(self, prs):
        """
        Act on the presence stanza that has just been received (Stub).

        """

        pass


