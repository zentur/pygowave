"""
unit testing code for pygowave's federation module
"""

import unittest

import crypto

class SignerTestCase(unittest.TestCase):

    def setUp(self):
        self.signer = crypto.Signer()

    def testLoadCertificates(self):
        """
        check that signer.certificates contains at least one element
        """
        certfile = '../cert.pem'
        self.signer.loadCertificates(certfile)
        
        self.assert_(len(self.signer.certificates) > 0)


if __name__ == "__main__":
    suite = unittest.TestLoader().loadTestsFromTestCase(SignerTestCase)
    unittest.TextTestRunner(verbosity=2).run(suite)

