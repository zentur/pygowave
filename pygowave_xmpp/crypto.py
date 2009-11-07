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

import hashlib
import base64
from M2Crypto.X509 import load_cert
from M2Crypto.RSA import load_key


class Signer(object):
    """
    TODO

    Certificates are stored as a list of M2Crypto's x509 objects
    """


    def __init__(self, certfile, keyfile):
        """
        """

        self.load_certificates(certfile)
        self.load_keyfile(keyfile)

        #TODO make algorithm configurable
        self.algorithm = hashlib.sha1
        pass


    def sign(self, payload):
        """
        Sign the payload with this signer's private key.

        @param {payload} the data to be signed
        """

        h = hashlib.sha1()
        h.update(payload)
        data = h.digest()

        return self.private_key.private_encrypt(data, 1)


    def get_signer_id(self):
        """
        Return the signer id of this signer
        """

        return self.signer_id


    def _calculate_signer_id(self):
        """
        The signer id is the base64 encoded hash of the pki-path of this signer:

        The pki path is defined as a ASN1 encoded sequence of certificates, where the
        first certificate is the "nearest" (e.g. the one generated for this very server)
        and the following are the rest of the certificate chain up to the CA's cert
        """

        pkipath = ''

        for cert in self.certificates:
            pkipath += cert.as_der()

        h = hashlib.sha1()
        h.update(pkipath)
        signer_id = h.digest()
        self.signer_id = signer_id


    def get_cerfificate_chain(self):
        #return self.certificates
        return ['some_certificate']


    def load_certificates(self, certfile):
        """
        We load the certificate from the file provided in PEM format,
        we may need to load more than one file but one's complex enough for testing ;)

        after the certificates are loaded, we calculate the signer id
        """

        self.certificates = []

        certificate = load_cert(certfile)
    
        self.certificates.append(certificate)

        self._calculate_signer_id()


    def load_keyfile(self, keyfile):
        """
        """

        self.private_key = load_key('cert.key')


