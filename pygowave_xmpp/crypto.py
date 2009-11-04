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

import hmac
import hashlib


class Signer(object):
    """
    TODO
    """


    def __init__(self):
        """
        """

        self.signingkey = 'some_signing_key'
        self.certificates = ['some_certificate']
        #TODO make algorithm configurable
        self.algorithm = hashlib.sha1
        pass


    def sign(self, payload):
        """
        """

        h = hmac.new(self.signingkey, payload, self.algorithm)
        return h.digest()


    def getSignature(self):
        """
        Return the signature for this signer

        The signature is the base64 encode hash of the pki-path of this signers certificate chain
        """

        return 'some signature'


    def getSignerId(self):
        return 'some_signer_id'


    def getCerfificateChain(self):
        return self.certificates


    def loadCertificates(self, certfile):
        """
        Bah, can't believe python has no native support for this...
        """

        certificates = ['some certificate']

        f = open(certfile)
        data = f.read()
        f.close()

        print "Data loaded from certfile:", data
    
        self.certificates = certificates


