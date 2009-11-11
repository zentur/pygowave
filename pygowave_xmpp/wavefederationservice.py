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

import waveprotocolbuffer
import crypto
from pygowave_server.models import Wavelet, ParticipantConn, Delta
from wavefederationremote import WaveFederationRemote
from wavefederationhost import WaveFederationHost
from remotehost import RemoteHost

class WaveFederationService(component.Service):
    """
    The WaveFederationService handles incoming xmpp stanzas and amqp messages and
    passes them to handlers inside the WaveFederationHost or WaveFederationRemote

    """


    def __init__(self, certificate_file, certificate_key_file):
        self.features = { NS_XMPP_RECEIPTS: None,
                          NS_DISCO_INFO: None,
                          NS_WAVE_SERVER: None,
        }

        self.signer = crypto.Signer(certificate_file, certificate_key_file)
        self.remoteHosts = {}


    def componentConnected(self, xmlstream):
        """
        This method is called when the componentConnected event gets called.
        That event gets called when we have connected and authenticated with the XMPP server.

        @param {xmlstream} xmlstream

        """

        self.jabberId = xmlstream.authenticator.otherHost
        self.xmlstream = xmlstream

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

        #FIXME: How to get the routing key the right way?
        rkey = msg[4]
        participant_conn_key, wavelet_id, message_category = rkey.split(".")
        body = simplejson.loads(msg.content.body)

        if body['type'] == 'PARTICIPANT_INFO' or body['type'] == 'WAVELET_OPEN' or body['type'] == 'PING' or body['type'] == 'GADGET_LIST' or body['type'] == 'PARTICIPANT_SEARCH' or body['type'] == 'WAVELET_REMOVE_SELF':
            print "ignoring message", body['type']
            return

        print 'WaveFederationService received: ' + msg.content.body + ' from channel #' + str(chan.id)

        try:
	        pconn = ParticipantConn.objects.get(tx_key=participant_conn_key)
        except:
            print "pconn not found"
            return

        wavelet = Wavelet.objects.get(id=wavelet_id)
        #Getting the delta from database would be nicer, but with the current implementation of our own
        #amqp message processor it would result in a race condition
        #delta = Delta.objects.filter(wavelet=wavelet).get(version=body['property']['version'])

        #check if wavelet is hosted locally
        if not wavelet.wavelet_name().startswith(self.jabberId):
            self.remote.sendSubmitRequest(wavelet, data)
        else:
            #NOTE: version is the version the delta is applied to
            version = body['property']['version']
            d = waveprotocolbuffer.getWaveletDelta2(version, body['property']['operations'], wavelet.wavelet_name(), pconn.participant.id, self.signer)
            print d
            print "***"
            app_delta = waveprotocolbuffer.getAppliedWaveletDelta(d, self.signer)
            print app_delta

            self.host.sendUpdate(wavelet, base64.b64encode(app_delta.SerializeToString()))


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

            elif el.attributes['type'] == 'error':
                #TODO Better error handling
                print "Error received"

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
                    self.remote.sendDiscoInfoResponse(iq)
                elif el.uri == NS_DISCO_ITEMS:
                    self.remote.sendDiscoItemsResponse(iq)
                elif el.uri == NS_PUBSUB:
                    for items in el.elements():
                        if items.attributes['node'] == 'wavelet':
                            self.host.onHistoryRequest(iq)
                        elif items.attributes['node'] == 'signer':
                            self.host.onGetSignerRequest(iq)
                        else:
                            print "Unknown IQ:", iq
                else:
                    print "Unknown IQ:", iq

        elif iq.attributes['type'] == 'result':
            for el in iq.elements():
                if el.uri == NS_DISCO_INFO:
                    self.remote.onDiscoInfoResponse(iq)
                elif el.uri == NS_DISCO_ITEMS:
                    self.remote.onDiscoItemsResponse(iq)
                else:
                    print "Unknown IQ:", iq

        elif iq.attributes['type'] == 'set':
            for el in iq.elements():
                if el.uri == NS_PUBSUB:
                    for publish in el.elements():
                        if publish.attributes['node'] == 'wavelet':
                            self.host.onSubmitRequest(iq)
                        elif publish.attributes['node'] == 'signer':
                            self.host.onSetSignerRequest(iq)
                        else:
                            print "Unknown IQ:", iq
                else:
                    print "Unknown IQ:", iq
        else:
            print "Unknown IQ:", iq


    def sendToRemoteHost(self,  domain,  stanza):
        """
        Sends stanzas to a remote host - takes care of creating a RemoteHost object if it does not exist
        """
        
        if self.remoteHosts.has_key(domain):
            remote = self.remoteHosts[domain]
        else:
            remote = RemoteHost(domain,  self)
            self.remoteHosts[domain] = remote
            
        self.remoteHosts[domain].send(stanza)
