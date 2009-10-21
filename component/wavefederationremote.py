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
from pygowave_server.models import Wavelet
from wavefederationservice import NS_XMPP_RECEIPTS, NS_DISCO_INFO, NS_DISCO_ITEMS, NS_PUBSUB, NS_PUBSUB_EVENT, NS_WAVE_SERVER


class WaveFederationRemote(object):
    """
    PyGoWave XMPP component service using twisted words.

    This is the federation remote part which according to the spec does the following:

    * It receives new wavelet operations pushed to it from the wave providers that host the wavelets.
    * It requests old wavelet operations from the hosting wave providers.
    * It submits wavelet operations to the hosting wave providers.

    For now, we simply skip the whole protocol buffer part and send data in pygowave specific JSON

    """

    def __init__(self, service):
        self.service = service


    def onUpdateMessage(self, msg):
        """
        Act on the message stanza that has just been received.

        @param {Element} msg the message stanza received

        """

        for wavelet_update in xpath.XPathQuery('/message/event/items/item/wavelet-update').queryForNodes(msg):
                    waveletName = wavelet_update.attributes['wavelet-name']

        for applied_delta in xpath.XPathQuery('/message/event/items/item/wavelet-update/applied-delta').queryForNodes(msg):
            content = str(applied_delta) #holy api failure
            op = convPbToOp(base64.b64decode(content))
            print "Received operation: %s, for wavelet: %s" %(op, waveletName)


        reply = domish.Element((None, 'message'))
        reply.attributes['id'] = msg.attributes['id']
        reply.attributes['to'] = msg.attributes['from']
        reply.attributes['from'] = self.service.jabberId
        reply.addElement(('urn:xmpp:receipts', 'received'))

        self.service.xmlstream.send(reply)

        
    def sendDiscoInfoResponse(self, iq):
        """

        """

        reply = domish.Element((None, 'iq'))
        reply.attributes['type'] = 'result'
        reply.attributes['from'] = self.service.jabberId
        reply.attributes['to']   = iq.attributes['from']
        reply.attributes['id']   = iq.attributes['id']

        query = reply.addElement((NS_DISCO_INFO, 'query'))

        identity = query.addElement('identity')
        identity.attributes['name']     = 'PyGoWave'
        identity.attributes['category'] = 'collaboration'
        identity.attributes['type']     = 'pygowave'

        for key in self.service.features.keys():
            feature = query.addElement('feature')
            feature.attributes['var'] = key        

        self.service.xmlstream.send(reply)


    def sendSubmitRequest(self, wavelet, data):
        """
        sends a submit request to the remote federation host
        called when a not locally hosted wave is changed by local participant

        @param {Wavelet} wavelet
        @param {String} data

        """

        #TODO: implement
        print "Submit request for wavelet %s" % (wavelet)
        

    def sendHistoryRequest(self):
        """
        Request the history of a wavelet from the wavelet's hosting server

        """

        #TODO: implement
        pass

