import unittest
import prog
import serv
import multiprocessing
import time
import socket

#class TestSome(unittest.TestCase):
#
#    def test_normal(self):
#        self.assertEqual(prog.funct(1, 2), 1.5)
#
#    def test_exception(self):
#        with self.assertRaises(ZeroDivisioonError):
#            prog.funct(1, 0)




class TestSqroot(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.proc = multiprocessing.Process(target=serv.srv)
        cls.proc.start()
        time.sleep(1)

    
    @classmethod
    def tearDownClass(cls):
        cls.proc.terminate()
    
    def setUp(self):
        self.s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.s.connect(("127.0.0.1", 1337))

    def tearDown(self):
        self.s.close()

    def test_except(self):
        with self.assertRaises(ValueError):
            #prog.sqroots("1 0")
            prog.sqrootnet("1 0", self.s)

    def test_roots(self):
        self.assertEqual(prog.sqrootnet("1 2 3", self.s), "")
        self.assertEqual(prog.sqrootnet("1 0 -1", self.s), "1.0 -1.0")
        self.assertEqual(prog.sqrootnet("1 0 0", self.s), "0.0")
