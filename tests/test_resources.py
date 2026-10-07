import hashlib,json,os,struct,subprocess,tempfile,unittest,zlib
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
BIN=Path(os.environ.get('NPK_PREVIEW_BIN',str(ROOT/'build/npk_preview')))

def record(fmt=16,compression=6,width=1,height=1,raw=bytes([0,0,255,255]),x=0,y=0,cw=None,ch=None,declared=None):
 data=zlib.compress(raw) if compression==6 else raw
 fields=[fmt,compression,width,height,len(data) if declared is None else declared,x&0xffffffff,y&0xffffffff,cw or width,ch or height]
 return struct.pack('<9I',*fields),data

def img(frames,version=2):
 idx=b''.join(a for a,b in frames);payload=b''.join(b for a,b in frames)
 return b'Neople Img File\0'+struct.pack('<4I',len(idx),0,version,len(frames))+idx+payload

def npk(images):
 off=20+264*len(images);table=b'';payload=b''
 for image in images:
  table+=struct.pack('<II',off,len(image))+bytes(range(256));payload+=image;off+=len(image)
 return b'NeoplePack_Bill\0'+struct.pack('<I',len(images))+table+payload

def png(path):
 b=path.read_bytes()
 if b[:8]!=b'\x89PNG\r\n\x1a\n':raise ValueError('PNG signature')
 p=8;compressed=b'';w=h=0
 while p<len(b):
  n=struct.unpack_from('>I',b,p)[0];tag=b[p+4:p+8];data=b[p+8:p+8+n]
  if zlib.crc32(tag+data)&0xffffffff!=struct.unpack_from('>I',b,p+8+n)[0]:raise ValueError('PNG CRC')
  if tag==b'IHDR':w,h=struct.unpack_from('>II',data)
  if tag==b'IDAT':compressed+=data
  p+=12+n
 raw=zlib.decompress(compressed);rows=[]
 for y in range(h):
  off=y*(w*4+1)
  if raw[off]!=0:raise ValueError('PNG filter')
  rows.append(raw[off+1:off+1+w*4])
 return w,h,b''.join(rows)

class ResourceTests(unittest.TestCase):
 def setUp(self):self.tmp=tempfile.TemporaryDirectory();self.dir=Path(self.tmp.name);self.input=self.dir/'input.NPK'
 def tearDown(self):self.tmp.cleanup()
 def run_data(self,b,export=False,code=0):
  self.input.write_bytes(b);before=hashlib.sha256(b).hexdigest()
  cmd=[str(BIN),'--export' if export else '--inspect',str(self.input)]
  if export:cmd.append(str(self.dir/'output'))
  r=subprocess.run(cmd,capture_output=True,text=True)
  self.assertEqual(r.returncode,code,r.stderr);self.assertEqual(hashlib.sha256(self.input.read_bytes()).hexdigest(),before)
  return r
 def test_bgra_red_to_rgba(self):
  self.run_data(npk([img([record()])]),True)
  self.assertEqual(png(self.dir/'output/entry_0_frame_0.png'),(1,1,bytes([255,0,0,255])))
 def test_argb1555_green(self):
  self.run_data(npk([img([record(fmt=14,raw=struct.pack('<H',0x83e0))])]),True)
  self.assertEqual(png(self.dir/'output/entry_0_frame_0.png')[2],bytes([0,255,0,255]))
 def test_argb4444_alpha(self):
  self.run_data(npk([img([record(fmt=15,raw=struct.pack('<H',0x8f21))])]),True)
  self.assertEqual(png(self.dir/'output/entry_0_frame_0.png')[2],bytes([255,34,17,136]))
 def test_actual_raw_length_convention(self):
  self.run_data(npk([img([record(fmt=14,compression=5,raw=b'\xff\xff',declared=4)])]),True)
  self.assertEqual(png(self.dir/'output/entry_0_frame_0.png')[2],b'\xff'*4)
 def test_canvas_offset(self):
  self.run_data(npk([img([record(x=1,y=1,cw=2,ch=2)])]),True)
  self.assertEqual(png(self.dir/'output/entry_0_frame_0.png'),(2,2,b'\0'*12+bytes([255,0,0,255])))
 def test_negative_offset_clipped(self):
  self.run_data(npk([img([record(x=-1,cw=2)])]),True)
  self.assertEqual(png(self.dir/'output/entry_0_frame_0.png')[2],b'\0'*8)
 def test_reference_frame_equal(self):
  self.run_data(npk([img([record(),(struct.pack('<II',17,0),b'')])]),True)
  self.assertEqual((self.dir/'output/entry_0_frame_0.png').read_bytes(),(self.dir/'output/entry_0_frame_1.png').read_bytes())
 def test_reference_cycle(self):self.run_data(npk([img([(struct.pack('<II',17,0),b'')])]),code=2)
 def test_link_out_of_bounds(self):self.run_data(npk([img([(struct.pack('<II',17,9),b'')])]),code=2)
 def test_bad_magic(self):self.run_data(b'not a package',code=2)
 def test_truncated_header(self):self.run_data(b'NeoplePack_Bill\0',code=2)
 def test_truncated_payload(self):self.run_data(npk([img([record()])])[:-1],code=2)
 def test_count_limit(self):self.run_data(b'NeoplePack_Bill\0'+struct.pack('<I',0xffffffff),code=2)
 def test_bad_version(self):self.run_data(npk([img([record()],4)]),code=2)
 def test_bad_format(self):self.run_data(npk([img([record(fmt=18)])]),code=2)
 def test_bad_compression(self):self.run_data(npk([img([record(compression=7)])]),code=2)
 def test_huge_dimensions(self):self.run_data(npk([img([record(width=0xffffffff,height=0xffffffff)])]),code=2)
 def test_zlib_expansion_size_mismatch(self):self.run_data(npk([img([record(raw=b'a'*100000)])]),code=2)
 def test_zlib_trailing_bytes_rejected(self):
  a,b=record();a=bytearray(a);struct.pack_into('<I',a,16,len(b)+4)
  self.run_data(npk([img([(bytes(a),b+b'junk')])]),code=2)
 def test_clipped_large_source_budget(self):
  first=record(fmt=14,width=4096,height=4096,cw=1,ch=1,raw=b'\0'*(4096*4096*2))
  frames=[first]+[(struct.pack('<II',17,0),b'')]*4
  r=self.run_data(npk([img(frames)]),code=2)
  self.assertIn('total_source_pixel_limit',r.stderr)
 def test_opaque_name_not_used_as_path(self):
  b=bytearray(npk([img([record()])]))
  b[28:284]=b'../private/secret.png\0'+b'\0'*(256-22)
  # Keep fixture exactly256 name bytes.
  self.assertEqual(len(b),len(npk([img([record()])])) )
  self.run_data(bytes(b),True)
  self.assertEqual([p.name for p in (self.dir/'output').iterdir()],['entry_0_frame_0.png'])
 def test_output_existing_rejected(self):
  (self.dir/'output').mkdir();(self.dir/'output/keep').write_text('keep')
  self.run_data(npk([img([record()])]),True,2)
  self.assertEqual((self.dir/'output/keep').read_text(),'keep')
if __name__=='__main__':unittest.main(verbosity=2)
