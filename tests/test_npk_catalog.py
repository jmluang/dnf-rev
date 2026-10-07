from pathlib import Path
import sys,tempfile,unittest
sys.path.insert(0,str(Path(__file__).parents[1]))
import npk_catalog as m
from test_resources import npk,img,record
class CatalogTests(unittest.TestCase):
 def setUp(self):self.tmp=tempfile.TemporaryDirectory();self.path=Path(self.tmp.name)/'test.npk'
 def tearDown(self):self.tmp.cleanup()
 def data(self,name):
  b=bytearray(npk([img([record()])]))
  raw=name.encode()+b'\0'*(256-len(name.encode()))
  b[28:284]=bytes(a^v for a,v in zip(raw,m.NAME_MASK));self.path.write_bytes(b)
 def test_named_index(self):
  self.data('sprite/character/test.img');r=m.read_index(self.path);self.assertEqual(r[0]['virtual_path'],'sprite/character/test.img');self.assertEqual(r[0]['entry'],0)
 def test_normalization(self):self.assertEqual(m.canonical_image_path('Character\\TEST.IMG'),'sprite/character/test.img')
 def test_path_traversal(self):
  self.data('../private.img')
  with self.assertRaises(m.FormatError):m.read_index(self.path)
 def test_absolute(self):
  with self.assertRaises(m.FormatError):m.canonical_image_path('/private.img')
 def test_not_img(self):
  with self.assertRaises(m.FormatError):m.canonical_image_path('secret.toml')
 def test_bad_header(self):
  self.path.write_bytes(b'bad')
  with self.assertRaises(m.FormatError):m.read_index(self.path)
 def test_ambiguous_catalog(self):
  self.data('sprite/a.img')
  with self.assertRaises(m.FormatError):m.build_catalog([self.path,self.path])
if __name__=='__main__':unittest.main(verbosity=2)
