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

        certfile = 'cert.pem'
        self.signer.loadCertificates(certfile)
        
        self.assert_(len(self.signer.certificates) > 0)


    def testGetSignerId(self):
        """
        """

        certfile = 'cert.pem'
        self.signer.loadCertificates(certfile)

        self.assertEqual('some_signer_id', self.signer.getSignerId())

def suite():
    suite = unittest.TestSuite()
    suite.addTest(SignerTestCase('testLoadCertificates'))
    suite.addTest(SignerTestCase('testGetSignerId'))
    return suite


if __name__ == "__main__":
    unittest.TextTestRunner(verbosity=2).run(suite())

