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
import base64

from twisted.words.xish import domish, xpath

from django.utils import simplejson

import common_pb2
from protobuf import convOpToPb, convPbToOp
from wavefederationservice import WaveFederationService, NS_XMPP_RECEIPTS, NS_DISCO_INFO
from wavefederationservice import NS_DISCO_ITEMS, NS_PUBSUB, NS_PUBSUB_EVENT, NS_WAVE_SERVER


class WaveFederationRemote(WaveFederationService):
    """
    PyGoWave XMPP Federation Remote.

    """


    def onMessage(self, msg):
        """
        Act on the message stanza that has just been received.

        @param msg the message stanza received

        """


        for el in msg.elements():
            if el.name == 'request':
                for wavelet_update in xpath.XPathQuery('/message/event/items/item/wavelet-update').queryForNodes(msg):
                    waveletName = wavelet_update.attributes['wavelet-name']

                for applied_delta in xpath.XPathQuery('/message/event/items/item/wavelet-update/applied-delta').queryForNodes(msg):
                    content = str(applied_delta) #holy api failure
                    op = convPbToOp(base64.b64decode(content))
                    print "Received operation: %s, for wavelet: %s" %(op, waveletName)


                reply = domish.Element((None, 'message'))
                reply.attributes['id'] = msg.attributes['id']
                reply.attributes['to'] = msg.attributes['from']
                reply.attributes['from'] = self.jabberId
                reply.addElement(('urn:xmpp:receipts', 'received'))

                self.xmlstream.send(reply)

        
    def onIq(self, iq):
        """
        Act on the iq stanza that has just been received.

        """

        jidfrom = iq.getAttribute('from')
        id = iq.getAttribute('id')

        for query in iq.elements():
            xmlns = query.uri

            if xmlns == NS_DISCO_INFO:
                self.sendDiscoInfoResponse(to=jidfrom, id=id)


#            for (feature, handler) in self.features.items():
#                if xmlns == feature:
#                    handler(iq)
        

    def sendDiscoInfoResponse(self, to, id):
        iq = domish.Element((None, 'iq'))
        iq.attributes['type'] = 'result'
        iq.attributes['to']   = to
        iq.attributes['from'] = self.jabberId
        iq.attributes['id']   = id

        query = iq.addElement((NS_DISCO_INFO, 'query'))

        identity = query.addElement('identity')
        identity.attributes['name']     = 'PyGoWave'
        identity.attributes['category'] = 'collaboration'
        identity.attributes['type']     = 'pygowave'

        for key in self.features.keys():
            feature = query.addElement('feature')
            feature.attributes['var'] = key        

        self.xmlstream.send(iq)


    def submitRequest(self, waveletName):
        """
        sends a submit request to the remote federation host
        called when a not locally hosted wave is changed by local participant

        @param waveletName
        """
        #TODO: implement
        print "Submit request for wavelet %s" % (waveletName)
        
