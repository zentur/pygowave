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
from wavefederationservice import WaveFederationService, NS_XMPP_RECEIPTS, NS_DISCO_INFO
from wavefederationservice import NS_DISCO_ITEMS, NS_PUBSUB, NS_PUBSUB_EVENT, NS_WAVE_SERVER


class WaveFederationHost(WaveFederationService):
    """
    PyGoWave XMPP component service using twisted words.

    This is the federation host part which according to the spec does the following:

    * It pushes new wavelet operations that are applied to a local wavelet to the wave providers of any remote participants.
    * It satisfies requests for old wavelet operations.
    * It processes wavelet operations submission requests.

    For now, we simply skip the whole protocol buffer part and send data in pygowave specific JSON

    """

    #TODO Implement queueing of messages in case remote server is not online

    def processAMQPMessage(self, msg, chan):
        """
        handle messages received from our local wave provider
        filter messages we do not care about, initiate sending of messages to remote wave server

        @param {Object} msg the message
        @param {Object} chan the amqp channel

        """

        print 'WaveFederationService received: ' + msg.content.body + ' from channel #' + str(chan.id)

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
        self.sendUpdate(wavelet, data)


    def sendUpdate(self, wavelet, data):
        """
        send a wavelet update to each remote wave provider that is interested in this wavelet

        @param {Wavelet} wavelet
        @param {String} data

        """
        participants = wavelet.participants.all()
        for p in participants:
            if not p.id.endswith('@localhost'):
                remote = p.id.split('@')[1]

                message = domish.Element((None, 'message'))
                message.attributes['type'] = 'normal'
                message.attributes['to'] = remote
                message.attributes['from'] = self.jabberId
                message.addUniqueId()

                request = message.addElement((NS_XMPP_RECEIPTS, 'request'))
                event   = message.addElement((NS_PUBSUB_EVENT, 'event'))

                items   = event.addElement((None, 'items'))
                item    = items.addElement((None, 'item'))

                wavelet_update = item.addElement((NS_WAVE_SERVER, 'wavelet-update'))
                wavelet_update.attributes['wavelet-name'] = wavelet.wavelet_name()

                applied_delta = wavelet_update.addElement((None, 'applied-delta'))
                applied_delta.addRawXml('<![CDATA[%s]]>' % (data))

                self.xmlstream.send(message)


    def onIq(self, iq):
        """
        Handle incoming IQ stanzas and pass them to stanza-specific handlers

        only reacts on messages meant for federation host, ignore the rest

        @param {Element} iq

        """
        #TODO: use xpath here(?)
        if iq.attributes['type'] == 'get':
            child = iq.firstChildElement()

            if child.attributes['xmlns'] == NS_PUBSUB:
                #history request or signer request FIXME implement the later
                self.onHistoryRequest(iq)

        elif iq.attributes['type'] == 'result':
            #nothing to do here
            pass

        elif iq.attributes['type'] == 'set':
            child = iq.firstChildElement()
            if child.attributes['xmlns'] == 'NS_PUBSUB':
                #submit of wavelet delta or signer posts FIXME implement the later
                self.onSubmitRequest(iq)
        else:
            #we ignore anything else for now, no error reporting
            pass


    def onHistoryRequest(self, request):
        """
        respond to incoming history request (stub)

        @param {Element} request the history request received

        """
        #TODO fetch history and pack it

        iq = domish.Element((None, 'iq'))
        iq.attributes['type'] = 'result'
        iq.attributes['from'] = self.jabberId
        iq.attributes['to']   = request.attributes['from']
        iq.attributes['id']   = request.attributes['id']

        pubsub = iq.addElement((NS_PUBSUB, 'pubsub'))
        items = pubsub.addElement((None, 'items'))

        print "history response: %s" % (iq.toXml())
        #self.xmlstream.send(iq)


    def onSubmitRequest(self, request):
        """
        respond to submit request (remote server sending wavelet updates) (stub)

        apply sent delta to the wavelet, ack the success or send error

        @param {Element} request the submit request received
        """

        #TODO apply sent delta to wavelet

        iq = domish.Element((None, 'iq'))
        iq.attributes['type'] = 'result'
        iq.attributes['from'] = self.jabberID
        iq.attributes['to']   = request.attributes['from']
        iq.attributes['id']   = request.attributes['id']

        pubsub = iq.addElement((NS_PUBSUB, 'pubsub'))
        publish = pubsub.addElement((None, 'pubslish'))
        item = publish.addElement((None, 'item'))

        submitResponse = item.addElement((NS_WAVE_SERVER, 'submit-response'))
        submitResponse.attributes['application-timestamp'] = 123456789.0
        submitResponse.attributes['operations-applied'] = 1

        hashedVersion = submitResponse.addElement((None, 'hashed-version'))
        hashedVersion.attributes['history-hash'] = ''
        hashedVersion.attributes['version'] = 1

        print "submit response: %s" % (iq.toXml())

