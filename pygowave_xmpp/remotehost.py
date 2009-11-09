from twisted.words.xish import domish

from crypto import VerifierFromString
from wavefederationservice import NS_XMPP_RECEIPTS, NS_DISCO_INFO, NS_DISCO_ITEMS, NS_PUBSUB, NS_PUBSUB_EVENT, NS_WAVE_SERVER

class RemoteHost(object):
    """
    Object representing a remote host, used to
    - implement a per-host resend queue
    - storing received certificates
    - storing JID's from service discovery
    
    the WaveFederationService calls the send method of this object.
    if the remote JID is not yet discovered, we store the message in a queue and send it after the discovery has finished
    """

    def __init__(self, domain, service):
        self.domain = domain
        self.service = service #service is used to get access to the xmlstream

        self.jid = 'UNDISCOVERED'
        self.certificates = []
        self.queue = []

    def updateCertificates(self, certificates):
        """
        certificates comes as a list of strings
        """
        print "Updating certificates for host/domain:", self.domain
        self.certificates = certificates

        self.verifier = VerifierFromString(certificates)


    def discoverJid(self):
        """
        start service discovery requests for this host
        we first send an item discovery request to the domain,
        and an info discovery request to each item received.
        we pick the first item with the waveserver feature.

        """
        if self.jid != 'UNDISCOVERED':
            #FIXME: no rediscovering so far
            return

        iq = domish.Element((None, 'iq'))
        iq.attributes['from'] = self.service.jabberId
        iq.attributes['type'] = 'get'
        iq.attributes['to'] = self.domain
        iq.addUniqueId()

        query = iq.addElement((NS_DISCO_ITEMS, 'query'))

        self.service.xmlstream.send(iq)

    def onJidDiscovered(self,  jid):
        """
        called when the service discovery returns a jid
        
        @param {String} jid
        """
        
        print "Discovered JID %s for domain %s" % (jid, self.domain)
        
        self.jid = jid
        
        self.sendQueue()

    def send(self, stanza):
        """
        Try to send stanza to remote host. If the jid of the remote domain is not discovered,
        put the stanza on the local queue to resend it after discovery has finished
        """
        if self.jid == 'UNDISCOVERED':
            self.discoverJid()
            self.queue.append(stanza)
        else:
            stanza.attributes['to'] = self.jid
        
            self.service.xmlstream.send(stanza)

    def sendQueue(self):
        """
        Send the whole queue
        """
        
        while len(self.queue) > 0:
            self.send(self.queue.pop(0))
