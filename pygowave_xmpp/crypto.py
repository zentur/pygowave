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
import base64
from OpenSSL.crypto import load_certificate, dump_certificate, FILETYPE_PEM, FILETYPE_ASN1


class Signer(object):
    """
    TODO

    Certificates are stored as a list of pyopenssl's x509 objects
    """


    def __init__(self, certfile, keyfile):
        """
        """

        self.load_certificates(certfile)
        self.load_keyfile(keyfile)

        self.certificates = ['some_certificate']
        #TODO make algorithm configurable
        self.algorithm = hashlib.sha1
        pass


    def sign(self, payload):
        """
        Sign the payload with this signer's private key.

        @param {payload} the data to be signed
        """

        h = hmac.new(self.signingkey, payload, self.algorithm)
        return h.digest()


    def get_signer_id(self):
        """
        Return the signer id of this signer
        """

        return 'some_signer_id'


    def _calculate_signer_id(self):
        """
        The signer id is the base64 encoded hash of the pki-path of this signer:

        The pki path is defined as a ASN1 encoded sequence of certificates, where the
        first certificate is the "nearest" (e.g. the one generated for this very server)
        and the following are the rest of the certificate chain up to the CA's cert
        """

        pkipath = ''

        for cert in self.certificates:
            pkipath += dump_certificate(FILETYPE_ASN1, cert)

        h = hashlib.sha1()
        h.update(pkipath)
        signer_id = h.digest()

        self.signer_id = base64.b64encode(signer_id)


    def get_cerfificate_chain(self):
        #return self.certificates
        return ['some_certificate']


    def load_certificates(self, certfile):
        """
        We load the certificate from the file provided in PEM format,
        we may need to load more than one file but one's complex enough for testing ;)

        TEST: It looks like newlines and the ...BEGIN CERTIFICATE... stuff is ignored by pyopenssl, thanks ;)

        after the certificates are loaded, we calculate the signer id
        """

        self.certificates = []

        f = open(certfile)
        data = f.read()
        f.close()

        certificate = load_certificate(FILETYPE_PEM, data)
    
        self.certificates.append(certificate)

        self._calculate_signer_id()


    def load_keyfile(self, keyfile):
        """
        """

        f = open(keyfile)
        data = f.read()
        f.close()
        
        self.signingkey = 'some_signing_key'

