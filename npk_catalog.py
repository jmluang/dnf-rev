"""Read-only NPK name index for resource-format interoperability.
No resource path is opened or used as an output path. Standard on-disk XOR
mask is a file-format constant, not an account credential or authorization key.
"""
from pathlib import Path,PurePosixPath
import hashlib,struct
MAX_FILE=256*1024*1024
PREFIX=b'puchikon@neople dungeon and fighter '
NAME_MASK=(PREFIX+b'DNF'*100)[:255]+b'\0'

class FormatError(ValueError):pass

def canonical_image_path(name):
 name=name.replace('\\','/').lower()
 p=PurePosixPath(name)
 if not name or p.is_absolute() or '..' in p.parts or ':' in name or '\x00' in name:
  raise FormatError('unsafe_resource_name')
 if not name.startswith('sprite/'):name='sprite/'+name
 if not name.endswith('.img'):raise FormatError('resource_not_IMG')
 return name

def read_index(path):
 path=Path(path)
 if path.stat().st_size>MAX_FILE:raise FormatError('file_size_limit')
 with path.open('rb') as f:
  head=f.read(20)
  if len(head)!=20 or head[:16]!=b'NeoplePack_Bill\0':raise FormatError('invalid_NPK_header')
  count=struct.unpack_from('<I',head,16)[0]
  if not 0<count<=100000:raise FormatError('entry_count_limit')
  table_end=20+264*count;size=path.stat().st_size
  if table_end>size:raise FormatError('truncated_NPK_index')
  result=[];seen=set()
  for i in range(count):
   rec=f.read(264)
   if len(rec)!=264:raise FormatError('truncated_NPK_record')
   off,length=struct.unpack_from('<II',rec)
   if off<table_end or off>size or length>size-off:raise FormatError('payload_out_of_bounds')
   encoded=rec[8:264];decoded=bytes(a^b for a,b in zip(encoded,NAME_MASK));end=decoded.find(b'\0')
   if end<0:raise FormatError('unterminated_name')
   name=decoded[:end].decode('utf-8',errors='strict');canonical=canonical_image_path(name)
   if canonical in seen:raise FormatError('duplicate_name')
   seen.add(canonical)
   result.append({'npk':str(path),'entry':i,'virtual_path':canonical,'offset':off,'length':length})
 return result

def build_catalog(paths):
 result={}
 for path in paths:
  for item in read_index(path):
   name=item['virtual_path']
   if name in result:raise FormatError('ambiguous_IMG_across_NPKs')
   result[name]=item
 return result

if __name__=='__main__':
 import argparse,json
 ap=argparse.ArgumentParser();ap.add_argument('npk',type=Path,nargs='+');args=ap.parse_args()
 print(json.dumps(build_catalog(args.npk),ensure_ascii=False,indent=2))
