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

import waveprotocolbuffer
from pygowave_server.models import Wavelet, Delta
from wavefederationservice import NS_XMPP_RECEIPTS, NS_DISCO_INFO, NS_DISCO_ITEMS, NS_PUBSUB, NS_PUBSUB_EVENT, NS_WAVE_SERVER


class WaveFederationHost(object):
    """
    PyGoWave XMPP component service using twisted words.

    This is the federation host part which according to the spec does the following:

    * It pushes new wavelet operations that are applied to a local wavelet to the wave providers of any remote participants.
    * It satisfies requests for old wavelet operations.
    * It processes wavelet operations submission requests.

    """

    #TODO Implement queueing of messages in case remote server is not online

    def __init__(self, service):
        self.service = service


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
                message.attributes['from'] = self.service.jabberId
                message.addUniqueId()

                request = message.addElement((NS_XMPP_RECEIPTS, 'request'))
                event   = message.addElement((NS_PUBSUB_EVENT, 'event'))

                items   = event.addElement((None, 'items'))
                item    = items.addElement((None, 'item'))

                wavelet_update = item.addElement((NS_WAVE_SERVER, 'wavelet-update'))
                wavelet_update.attributes['wavelet-name'] = wavelet.wavelet_name()

                applied_delta = wavelet_update.addElement((None, 'applied-delta'))
                applied_delta.addRawXml('<![CDATA[%s]]>' % (data))

                self.service.xmlstream.send(message)


    def onHistoryRequest(self, request):
        """
        respond to incoming history request (stub)

        @param {Element} request the history request received


        """
        #fetch history and pack it

        for delta_history in xpath.XPathQuery('/iq/pubsub/items/delta-history').queryForNodes(request):
            wavelet_name = delta_history.attributes['wavelet-name']
            start_version = int(delta_history.attributes['start-version'])
            start_version_hash = delta_history.attributes['start-version-hash']
            end_version = int(delta_history.attributes['end-version'])
            end_version_hash = delta_history.attributes['end-version-hash']

        waveletDomain, waveId, waveletId = wavelet_name.replace('wave://','').split('/')

        if '$' in waveId:
            waveDomain, waveId = waveId.split('$')
        else:
            waveDomain = waveletDomain

        print "fetch history for:", waveDomain, waveId, waveletDomain, waveletId, start_version, start_version_hash, end_version, end_version_hash

        _id = waveId + '!' + waveletId
        wavelet = Wavelet.objects.get(pk=_id)

        iq = domish.Element((None, 'iq'))
        iq.attributes['type'] = 'result'
        iq.attributes['from'] = self.service.jabberId
        iq.attributes['to']   = request.attributes['from']
        iq.attributes['id']   = request.attributes['id']

        pubsub = iq.addElement((NS_PUBSUB, 'pubsub'))
        items = pubsub.addElement((None, 'items'))


        for i in range(start_version, end_version):
            #TODO: Our versions start with number 1, so we add 1                
            delta = Delta.objects.filter(wavelet=wavelet).get(version=i+1)

            #FIXME: naming conventions *sigh*
            #FIXME: delta in database does not contain author
            d = waveprotocolbuffer.getWaveletDelta(delta, 'murk@localhost')
            app_delta = waveprotocolbuffer.getAppliedWaveletDelta(d)

            data = base64.b64encode(app_delta.SerializeToString())

            item = items.addElement((None, 'item'))
            
            applied_delta = item.addElement((None, 'applied-delta'))
            applied_delta.addRawXml('<![CDATA[%s]]>' % (data))

        self.service.xmlstream.send(iq)


    def onSubmitRequest(self, request):
        """
        respond to submit request (remote server sending wavelet updates) (stub)

        apply sent delta to the wavelet, ack the success or send error

        @param {Element} request the submit request received
        """

        #TODO apply sent delta to wavelet

        iq = domish.Element((None, 'iq'))
        iq.attributes['type'] = 'result'
        iq.attributes['from'] = self.service.jabberID
        iq.attributes['to']   = request.attributes['from']
        iq.attributes['id']   = request.attributes['id']

        pubsub = iq.addElement((NS_PUBSUB, 'pubsub'))
        publish = pubsub.addElement((None, 'pubslish'))
        publish.attributes['node'] = 'wavelet'

        item = publish.addElement((None, 'item'))

        submitResponse = item.addElement((NS_WAVE_SERVER, 'submit-response'))
        submitResponse.attributes['application-timestamp'] = 123456789.0
        submitResponse.attributes['operations-applied'] = 1

        hashedVersion = submitResponse.addElement((None, 'hashed-version'))
        hashedVersion.attributes['history-hash'] = ''
        hashedVersion.attributes['version'] = 1

        print "submit response: %s" % (iq.toXml())


    def postSignature(self, target):
        """
        post the signature chain to the target wave server

        @param {String} target the jid of the server to send the signatures to

        """

        certificates = ['some certificate']

        iq = domish.Element((None, 'iq'))
        iq.attributes['type'] = 'set'
        iq.attributes['from'] = self.service.jabberId
        iq.attributes['to'] = target
        iq.addUniqueId()

        pubsub = iq.addElement((NS_PUBSUB, 'pubsub'))

        publish = pubsub.addElement((None, 'publish'))
        publish.attributes['node'] = 'signer'

        item = publish.addElement((None, 'item'))

        signature = item.addElement((NS_WAVE_SERVER, 'signature'))
        signature.attributes['domain'] = 'some domain'
        signature.attributes['algorithm'] = 'SHA256'

        for c in certificates:
            certificate = signature.addElement((None, 'certificate'))
            certificate.addRawXml('<![CDATA[%s]]>' % (base64.b64encode(c)) ) 

        self.service.xmlstream.send(reply)


    def onGetSignerRequest(self, request):
        """

        Respond to a get signer request

        """

        print "Received signer Get request"
        
        #<iq type="get" id="1-1" from="wave.initech-corp.com" to="wave.acmewave.com">
        #  <pubsub xmlns="http://jabber.org/protocol/pubsub">
        #    <items node="signer">
        #      <signer-request xmlns="http://waveprotocol.org/protocol/0.2/waveserver"
        #        history-hash="somehash" version="1234"
        #        wavelet-name="acmewave.com/initech-corp.com!a/b"/> </items>
        #  </pubsub>
        #</iq>

        certificates = ['some certificate']

        reply = domish.Element((None, 'iq'))
        reply.attributes['type'] = 'result'
        reply.attributes['from'] = self.service.jabberId
        reply.attributes['to'] = request.attributes['from']
        reply.attributes['id'] = request.attributes['id']

        pubsub = reply.addElement((NS_PUBSUB, 'pubsub'))

        items = pubsub.addElement((None, 'items'))

        signature = items.addElement((NS_WAVE_SERVER, 'signature'))
        signature.attributes['domain'] = 'some domain'
        signature.attributes['algorithm'] = 'SHA256'

        for c in certificates:
            certificate = signature.addElement((None, 'certificate'))
            certificate.addRawXml('<![CDATA[%s]]>' % (base64.b64encode(c)))

        self.service.xmlstream.send(reply)


    def onSetSignerRequest(self, request):
        """

        """
        #TODO we ack the Post request but don't do anything with it yet
        print "Received signer Set request"

        reply = domish.Element((None, 'iq'))
        #NOTE: the spec's example says type=set, which is wrong imho
        reply.attributes['type'] = 'result'
        reply.attributes['from'] = self.service.jabberId
        reply.attributes['to']   = request.attributes['from']
        reply.attributes['id']   = request.attributes['id']

        pubsub = reply.addElement((NS_PUBSUB, 'pubsub'))
        publish = pubsub.addElement((None, 'publish'))

        item = publish.addElement((None, 'item'))
        item.attributes['node'] = 'signer'

        signature_response = item.addElement((NS_WAVE_SERVER, 'signature-response'))

        self.service.xmlstream.send(reply)

