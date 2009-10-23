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

PRESENCE = '/presence' # this is an global xpath query to use in an observer
MESSAGE  = '/message'  # message xpath 
IQ       = '/iq'       # iq xpath

NS_XMPP_RECEIPTS = "urn:xmpp:receipts";
NS_DISCO_INFO = "http://jabber.org/protocol/disco#info";
NS_DISCO_ITEMS = "http://jabber.org/protocol/disco#items";
NS_PUBSUB = "http://jabber.org/protocol/pubsub";
NS_PUBSUB_EVENT = "http://jabber.org/protocol/pubsub#event";
NS_WAVE_SERVER = "http://waveprotocol.org/protocol/0.2/waveserver";

import base64

from twisted.words.protocols.jabber import jid, xmlstream, component
from twisted.words.xish import domish, xpath

from django.utils import simplejson

#import common_pb2
from protobuf import convOpToPb, convPbToOp
from pygowave_server.models import Wavelet

from wavefederationremote import WaveFederationRemote
from wavefederationhost import WaveFederationHost

class WaveFederationService(component.Service):
    """
    The WaveFederationService handles incoming xmpp stanzas and amqp messages and
    passes them to handlers inside the WaveFederationHost or WaveFederationRemote

    """


    def __init__(self):
        self.features = { NS_XMPP_RECEIPTS: None,
                          NS_DISCO_INFO: None,
                          NS_WAVE_SERVER: None,
        }

    def componentConnected(self, xmlstream):
        """
        This method is called when the componentConnected event gets called.
        That event gets called when we have connected and authenticated with the XMPP server.

        @param {xmlstream} xmlstream

        """

        self.jabberId = xmlstream.authenticator.otherHost
        self.xmlstream = xmlstream # set the xmlstream so we can reuse it

        self.remote = WaveFederationRemote(self)
        self.host = WaveFederationHost(self)
        
        xmlstream.addObserver(PRESENCE, self.onPresence, 1)
        xmlstream.addObserver(IQ, self.onIq, 1)
        xmlstream.addObserver(MESSAGE, self.onMessage, 1)
        #TODO: maybe add support for XCP Component Presence


    def onPresence(self, prs):
        """
        Act on the presence stanza that has just been received (Stub).

        """

        pass


    def processAMQPMessage(self, msg, chan):
        """
        handle messages received from our local wave provider
        filter messages we do not care about, initiate sending of submit request to remote wave server

        @param {Object} msg the message
        @param {Object} chan the amqp channel

        """

        print 'WaveFederationRemote received: ' + msg.content.body + ' from channel #' + str(chan.id)

        #FIXME How to get the routing key the right way?
        rkey = msg[4]
        participant_conn_key, wavelet_id, message_category = rkey.split(".")
        body = simplejson.loads(msg.content.body)

        data = base64.b64encode(convOpToPb(msg.content.body))

        if body['type'] == 'PARTICIPANT_INFO' or body['type'] == 'WAVELET_OPEN':
            print "ignoring message"
            return

        if not data:
            print "data not set - skipping"
            return

        wavelet = Wavelet.objects.get(id=wavelet_id)
        #check if wavelet is hosted locally
        if not wavelet.wavelet_name().startswith(self.jabberId):
            self.remote.sendSubmitRequest(wavelet, data)
        else:
            self.host.sendUpdate(wavelet, data)


    def onMessage(self, msg):
        """
        Act on the message stanza that has just been received.

        @param {Element} msg the message stanza received

        """

        for el in msg.elements():
            if el.name == 'received':
                #remote server ack's one of our packages, we can remove it from our
                #to-be-implemented resend queue
                pass

            elif el.name == 'request':
                #we received a wavelet update
                self.remote.onUpdateMessage(msg)

            else:
                pass

        
    def onIq(self, iq):
        """
        Act on the iq stanza that has just been received.

        @param {Element} iq

        """

        if iq.attributes['type'] == 'get':
            for el in iq.elements():
                if el.uri == NS_DISCO_INFO:
                    #service discovery
                    self.remote.sendDiscoInfoResponse(iq)
                elif el.uri == NS_DISCO_ITEMS:
                    #service discovery
                    self.remote.sendDiscoItemsResponse(iq)
                elif el.uri == NS_PUBSUB:
                    for items in el.elements():
                        if items.attributes['node'] == 'wavelet':
                            #history request 
                            self.host.onHistoryRequest(iq)
                        elif items.attributes['node'] == 'signer':
                            #or signer request
                            self.host.onGetSignerRequest(iq)
                        else:
                            print "Unknown IQ:", iq
                else:
                    print "Unknown IQ:", iq

        elif iq.attributes['type'] == 'result':
            for el in iq.elements():
                if el.uri == NS_DISCO_INFO:
                    #service discovery
                    self.remote.onDiscoInfoResponse(iq)
                elif el.uri == NS_DISCO_ITEMS:
                    #service discovery
                    self.remote.onDiscoItemsResponse(iq)
                else:
                    print "Unknown IQ:", iq

        elif iq.attributes['type'] == 'set':
            for el in iq.elements():
                if el.uri == NS_PUBSUB:
                    for publish in el.elements():
                        if publish.attributes['node'] == 'wavelet':
                            #submit of wavelet delta or signer posts FIXME implement the later
                            self.host.onSubmitRequest(iq)
                        elif publish.attributes['node'] == 'signer':
                            #or signer request FIXME: implement
                            self.host.onSetSignerRequest(iq)
                        else:
                            print "Unknown IQ:", iq
                else:
                    print "Unknown IQ:", iq
        else:
            print "Unknown IQ:", iq


