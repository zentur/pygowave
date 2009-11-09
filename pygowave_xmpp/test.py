"""
unit testing code for pygowave's federation module
"""

import unittest
from M2Crypto.X509 import load_cert

import crypto

class SignerTestCase(unittest.TestCase):

    def setUp(self):
        self.signer = crypto.Signer('cert.pem', 'cert.key')

    def test_load_certificates(self):
        """
        check that signer.certificates contains at least one element
        """

        self.assert_(len(self.signer.certificates) > 0)


    def test_get_signer_id(self):
        """
        """
        testid = '\237\247\017)P@s_\024\350\221T\262(\310f\311\2133k\320\227\005\266D\231\034\354\231\025\033\n'
        self.assertEqual(testid, self.signer.get_signer_id())


    def test_sign(self):
        """
        """
        expected_signature = 'NG\247G\354\313p\305\003\346\020d\r\377\355\022-9).2.\325\360\322\274\312\217\202\355\272\367\235B\r\313L.\202\231\371Z\262\304p\273\307\355\3377Y\n&b[\217\262\000\332 \340\322;\035;\005\032\226j#X\321\312\333Y\251\031j`h\256J\205\035t\371_\261\241\004\221Q\200\254\276:\357T\315\2653\232\243\0042\021[\267\215\323\352\225_\325\212Z\216\332Fh\273\240/\273\255\377\350Z'

        teststring = '\n\030\010\003\022\024\221\r\331\230\357\270\024\353\352ft\221\261jR@\014\207\315\265\022\037murk@fedone.ferrum-et-magica.de\032H\032F\n\004main\022>\n\002(\003\n/\032-\n\004line\022%\n\002by\022\037murk@fedone.ferrum-et-magica.de\n\002 \001\n\003\022\001b'
        self.assertEqual(expected_signature, self.signer.sign(teststring))


def signer_suite():
    suite = unittest.TestSuite()
    suite.addTest(SignerTestCase('test_load_certificates'))
    suite.addTest(SignerTestCase('test_get_signer_id'))
    suite.addTest(SignerTestCase('test_sign'))
    return suite


class VerifierTestCase(unittest.TestCase):

    def setUp(self):
        cert = load_cert('cert.pem')
        self.verifier = crypto.Verifier([cert])


    def test_verify_true(self):
        """
        test that verify works
        """

        testsignature = 'NG\247G\354\313p\305\003\346\020d\r\377\355\022-9).2.\325\360\322\274\312\217\202\355\272\367\235B\r\313L.\202\231\371Z\262\304p\273\307\355\3377Y\n&b[\217\262\000\332 \340\322;\035;\005\032\226j#X\321\312\333Y\251\031j`h\256J\205\035t\371_\261\241\004\221Q\200\254\276:\357T\315\2653\232\243\0042\021[\267\215\323\352\225_\325\212Z\216\332Fh\273\240/\273\255\377\350Z'
        teststring = '\n\030\010\003\022\024\221\r\331\230\357\270\024\353\352ft\221\261jR@\014\207\315\265\022\037murk@fedone.ferrum-et-magica.de\032H\032F\n\004main\022>\n\002(\003\n/\032-\n\004line\022%\n\002by\022\037murk@fedone.ferrum-et-magica.de\n\002 \001\n\003\022\001b'

        result = self.verifier.verify(teststring, testsignature)
        self.assertEqual(result, 1)


    def test_verify_false(self):
        """
        test that verify return false with bad data
        """

        testsignature = 'NG\247G\354\313p\305\003\346\020d\r\377\355\022-9).2.\325\360\322\274\312\217\202\355\272\367\235B\r\313L.\202\231\371Z\262\304p\273\307\355\3377Y\n&b[\217\262\000\332 \340\322;\035;\005\032\226j#X\321\312\333Y\251\031j`h\256J\205\035t\371_\261\241\004\221Q\200\254\276:\357T\315\2653\232\243\0042\021[\267\215\323\352\225_\325\212Z\216\332Fh\273\240/\273\255\377\350Z'

        self.assert_(self.verifier.verify('bad string', testsignature) == False)


def verifier_suite():
    suite = unittest.TestSuite()
    suite.addTest(VerifierTestCase('test_verify_true'))
    suite.addTest(VerifierTestCase('test_verify_false'))
    return suite


def suite():
    suite = unittest.TestSuite()
    suite.addTest(signer_suite())
    suite.addTest(verifier_suite())
    return suite

if __name__ == "__main__":
    unittest.TextTestRunner(verbosity=2).run(suite())

