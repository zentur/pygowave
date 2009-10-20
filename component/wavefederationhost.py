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

from twisted.words.protocols.jabber import jid, xmlstream
from twisted.internet import interfaces, defer, reactor
from twisted.words.xish import domish, xpath
from twisted.words.protocols.jabber.ijabber import IService
from twisted.words.protocols.jabber import component

from zope.interface import Interface, implements

from django.utils import simplejson

import common_pb2
from protobuf import convOpToPb, convPbToOp
from pygowave_server.models import Wavelet
from wavefederationservice import WaveFederationService, NS_XMPP_RECEIPTS, NS_DISCO_INFO
from wavefederationservice import NS_DISCO_ITEMS, NS_PUBSUB, NS_PUBSUB_EVENT, NS_WAVE_SERVER

# includes for txamqp
from twisted.internet.defer import inlineCallbacks
from twisted.internet.protocol import ClientCreator
from txamqp.protocol import AMQClient
from txamqp.client import TwistedDelegate
import txamqp.spec


class WaveFederationHost(WaveFederationService):
    """
    PyGoWave XMPP component service using twisted words.

    For now, we simply skip the whole protocol buffer part and send
    data in pygowave specific JSON
    """
    implements(IService)


    def __init__(self):
        host = 'localhost'
        port = 5672
        vhost = '/'
        username = 'pygowave_xmpp'
        password = 'pygowave_xmpp'

        spec = txamqp.spec.load('amqp0-8.xml')

        delegate = TwistedDelegate()

        d = ClientCreator(reactor, AMQClient, delegate=delegate, vhost=vhost,
                spec=spec).connectTCP(host, port)

        d.addCallback(self.gotAMQPConnection, username, password)

        
    def processAMQPMessage(self, msg, chan):
        """
        <message type='normal'
            from='wave.ferrum-et-magica.de'
            id='H_0' to='wavetester@ferrum-et-magica.de'>
            <request xmlns='urn:xmpp:receipts'/>
            <event xmlns='http://jabber.org/protocol/pubsub#event'>
                <items>
                    <item>
                        <wavelet-update
                            xmlns='http://waveprotocol.org/protocol/0.2/waveserver'
                            wavelet-name='CH0H59rYDc!conv+root'>
                            <applied-delta><![CDATA[ChJtdXJrdGVzdEBsb2NhbGhvc3Q=]]></applied-delta>
                        </wavelet-update>
                    </item>
                </items>
            </event>
        </message>

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


    @inlineCallbacks
    def gotAMQPConnection(self, conn, username, password):
        print "Connected to broker."
        yield conn.authenticate(username, password)

        print "Authenticated. Ready to receive messages"
        chan = yield conn.channel(1)
        yield chan.channel_open()

        yield chan.queue_declare(queue="federation", durable=True, exclusive=False, auto_delete=False)
#        yield chan.exchange_declare(exchange="wavelet.topic", type="direct", durable=True, auto_delete=False)

        yield chan.queue_bind(queue="federation", exchange="wavelet.topic", routing_key="#.#.clientop")

        yield chan.basic_consume(queue='federation', no_ack=True, consumer_tag="testtag")

        queue = yield conn.queue("testtag")

#        self.processAMQPMessage('test')
        while True:
            msg = yield queue.get()
            yield self.processAMQPMessage(msg, chan)
            if msg.content.body == "STOP":
                break

        yield chan.basic_cancel("testtag")
        yield chan.channel_close()
        chan0 = yield conn.channel(0)
        yield chan0.connection_close()


