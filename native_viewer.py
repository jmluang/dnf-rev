#!/usr/bin/env python3
"""Real SDL2 desktop viewer, powered by the independent C++ NPK/IMG decoder.
Uses installed SDL2 through its public C ABI; no browser, Wine or game binaries.
Preview playback speed is demonstrative, not reconstructed animation timing.
"""
import argparse,ctypes as C,ctypes.util,json,os,struct,sys,time
from pathlib import Path
from native_runtime import check_runtime_abi,load_sdl2,load_bridge,initialize_sdl
ROOT=Path(__file__).resolve().parent
V=C.c_void_p;I=C.c_int;U=C.c_uint32
class Rect(C.Structure):_fields_=[('x',I),('y',I),('w',I),('h',I)]
class Event(C.Union):_fields_=[('align',C.c_uint64),('raw',C.c_ubyte*56)]

def bind(lib,name,args,result):
 f=getattr(lib,name);f.argtypes=args;f.restype=result;return f
check_runtime_abi()
sdl=load_sdl2(ROOT)
def Init(flags):return initialize_sdl(sdl,flags)
Quit=bind(sdl,'SDL_Quit',[],None)
Error=bind(sdl,'SDL_GetError',[],C.c_char_p)
CreateWindow=bind(sdl,'SDL_CreateWindow',[C.c_char_p,I,I,I,I,U],V)
DestroyWindow=bind(sdl,'SDL_DestroyWindow',[V],None)
CreateRenderer=bind(sdl,'SDL_CreateRenderer',[V,I,U],V);DestroyRenderer=bind(sdl,'SDL_DestroyRenderer',[V],None)
CreateTexture=bind(sdl,'SDL_CreateTexture',[V,U,I,I,I],V);DestroyTexture=bind(sdl,'SDL_DestroyTexture',[V],None)
UpdateTexture=bind(sdl,'SDL_UpdateTexture',[V,V,V,I],I)
Blend=bind(sdl,'SDL_SetTextureBlendMode',[V,I],I)
Color=bind(sdl,'SDL_SetRenderDrawColor',[V,C.c_ubyte,C.c_ubyte,C.c_ubyte,C.c_ubyte],I)
Fill=bind(sdl,'SDL_RenderFillRect',[V,C.POINTER(Rect)],I)
Clear=bind(sdl,'SDL_RenderClear',[V],I);Copy=bind(sdl,'SDL_RenderCopy',[V,V,V,C.POINTER(Rect)],I)
Present=bind(sdl,'SDL_RenderPresent',[V],None);Poll=bind(sdl,'SDL_PollEvent',[C.POINTER(Event)],I)
Hint=bind(sdl,'SDL_SetHint',[C.c_char_p,C.c_char_p],I)
bridge=load_bridge(ROOT)
Open=bind(bridge,'dnf_open',[C.c_char_p],V);Close=bind(bridge,'dnf_close',[V],None)
Entries=bind(bridge,'dnf_entries',[V],I);Frames=bind(bridge,'dnf_frames',[V,I],I)
Frame=bind(bridge,'dnf_frame',[V,I,I,C.POINTER(I),C.POINTER(I)],V)
BridgeError=bind(bridge,'dnf_error',[],C.c_char_p)
Mouse=bind(bridge,'dnf_mouse_event',[V,I,I,I,I,C.POINTER(I)],I)
Finish=bind(bridge,'dnf_finish_frame',[V],None)
Quad=bind(bridge,'dnf_quad',[U,U,C.POINTER(C.c_float)],I)
# Hand-authored 5x7 UI glyphs, not game font data.
GLYPHS={
'A':'01110 10001 10001 11111 10001 10001 10001','B':'11110 10001 10001 11110 10001 10001 11110','C':'01111 10000 10000 10000 10000 10000 01111','D':'11110 10001 10001 10001 10001 10001 11110','E':'11111 10000 10000 11110 10000 10000 11111','F':'11111 10000 10000 11110 10000 10000 10000','G':'01111 10000 10000 10111 10001 10001 01111','H':'10001 10001 10001 11111 10001 10001 10001','I':'11111 00100 00100 00100 00100 00100 11111','J':'00111 00010 00010 00010 10010 10010 01100','K':'10001 10010 10100 11000 10100 10010 10001','L':'10000 10000 10000 10000 10000 10000 11111','M':'10001 11011 10101 10101 10001 10001 10001','N':'10001 11001 10101 10011 10001 10001 10001','O':'01110 10001 10001 10001 10001 10001 01110','P':'11110 10001 10001 11110 10000 10000 10000','Q':'01110 10001 10001 10001 10101 10010 01101','R':'11110 10001 10001 11110 10100 10010 10001','S':'01111 10000 10000 01110 00001 00001 11110','T':'11111 00100 00100 00100 00100 00100 00100','U':'10001 10001 10001 10001 10001 10001 01110','V':'10001 10001 10001 10001 10001 01010 00100','W':'10001 10001 10001 10101 10101 10101 01010','X':'10001 10001 01010 00100 01010 10001 10001','Y':'10001 10001 01010 00100 00100 00100 00100','Z':'11111 00001 00010 00100 01000 10000 11111',
'0':'01110 10001 10011 10101 11001 10001 01110','1':'00100 01100 00100 00100 00100 00100 01110','2':'01110 10001 00001 00010 00100 01000 11111','3':'11110 00001 00001 01110 00001 00001 11110','4':'00010 00110 01010 10010 11111 00010 00010','5':'11111 10000 10000 11110 00001 00001 11110','6':'01110 10000 10000 11110 10001 10001 01110','7':'11111 00001 00010 00100 01000 01000 01000','8':'01110 10001 10001 01110 10001 10001 01110','9':'01110 10001 10001 01111 00001 00001 01110',
'-':'00000 00000 00000 11111 00000 00000 00000','+':'00000 00100 00100 11111 00100 00100 00000','/':'00001 00010 00010 00100 01000 01000 10000',':':'00000 00100 00100 00000 00100 00100 00000','.':'00000 00000 00000 00000 00000 00100 00100','=':'00000 11111 00000 11111 00000 00000 00000','_':'00000 00000 00000 00000 00000 00000 11111','(':'00010 00100 01000 01000 01000 00100 00010',')':'01000 00100 00010 00010 00010 00100 01000',
}

def main():
 import tempfile
 ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--samples',type=Path,default=ROOT/'samples');ap.add_argument('--receipt',type=Path,default=ROOT/'viewer-session.json');args=ap.parse_args()
 files=sorted(args.samples.glob('*.NPK'))
 if not files:raise ValueError('No NPK samples')
 if args.receipt.exists() or args.receipt.is_symlink():raise ValueError('receipt must be a new path')
 # Exclusive creation also closes the race after the friendly existence check.
 with args.receipt.open('x',encoding='utf8') as placeholder:placeholder.write('{}')
 file_index=entry=frame=0;pack=None;texture=None;window=None;renderer=None;w=h=0;zoom=5;playing=False;next_tick=0;running=True
 init_attempted=False;receipt_ready=False
 stats={'backend':'SDL2_native_window','decoder':'independent_C++17','original_game_executed':False,'frames_drawn':0,'frame_changes':0,'pack_changes':0,'key_events':0,'mouse_events':0,'wheel_events':0,'zoom_changes':0,'play_toggles':0,'last_mouse_state':[]}
 status='READY - RESOURCE VIEWER ONLY'
 def check_sdl(result):
  if result!=0:raise RuntimeError((Error() or b'SDL operation failed').decode('utf8','replace'))
 def require_handle(handle,error):
  if not handle:raise RuntimeError((error() or b'Native operation failed').decode('utf8','replace'))
 def rectangle(x,y,width,height,color):
  Color(renderer,*color,255);r=Rect(x,y,width,height);Fill(renderer,C.byref(r))
 def text(value,x,y,scale=2,color=(220,232,242)):
  Color(renderer,*color,255)
  for ch in value.upper():
   for ry,row in enumerate(GLYPHS.get(ch,'00000 '*7).split()):
    for rx,v in enumerate(row):
     if v=='1':r=Rect(x+rx*scale,y+ry*scale,scale,scale);Fill(renderer,C.byref(r))
   x+=6*scale
 def load_pack():
  nonlocal pack,entry,frame
  old_pack=pack;pack=None
  if old_pack:Close(old_pack)
  pack=Open(str(files[file_index]).encode());require_handle(pack,BridgeError);entry=frame=0
  load_frame()
 def load_frame():
  nonlocal texture,w,h
  width=I();height=I();ptr=Frame(pack,entry,frame,C.byref(width),C.byref(height));require_handle(ptr,BridgeError);w=width.value;h=height.value
  old_texture=texture;texture=None
  if old_texture:DestroyTexture(old_texture)
  texture=CreateTexture(renderer,0x16762004,0,w,h);require_handle(texture,Error)
  check_sdl(UpdateTexture(texture,None,ptr,w*4));check_sdl(Blend(texture,1))
  # Exercise recovered final-blit UV/half-pixel contract via the native bridge.
  quad=(C.c_float*16)()
  if Quad(w,h,quad)!=0:raise RuntimeError('Native quad generation failed')
  if list(quad)!=[-1.,-1.,0.,1.,-1.,1.,0.,0.,1.,-1.,1.,1.,1.,1.,1.,0.]:raise RuntimeError('Native quad contract mismatch')
 def next_frame(delta):
  nonlocal frame,status
  frame=(frame+delta)%Frames(pack,entry);stats['frame_changes']+=1;status='FRAME CHANGED';load_frame()
 def next_entry():
  nonlocal entry,frame,status
  entry=(entry+1)%Entries(pack);frame=0;status='IMG CHANGED';load_frame()
 def next_pack():
  nonlocal file_index,status
  file_index=(file_index+1)%len(files);stats['pack_changes']+=1;status='NPK CHANGED';load_pack()
 def input_mouse(kind,x,y,delta=0):
  nonlocal status
  out=(I*7)();Mouse(pack,kind,x*800//1000,y*600//720,delta,out)
  stats['last_mouse_state']=list(out);stats['mouse_events']+=1
  if kind!=0:status=f'MOUSE EVENT {kind}: L={out[2]} R={out[3]} W={out[6]}'
 def write_receipt():
  payload=dict(stats,current_pack=files[file_index].name,entry=entry,frame=frame,zoom=zoom,playing=playing,status=status)
  fd,name=tempfile.mkstemp(prefix='dnf-viewer-receipt-',dir=args.receipt.parent)
  try:
   with os.fdopen(fd,'w',encoding='utf8') as out:
    fd=None;out.write(json.dumps(payload,indent=2))
   os.replace(name,args.receipt);name=None
  finally:
   if fd is not None:os.close(fd)
   if name is not None:
    try:os.unlink(name)
    except FileNotFoundError:pass
 try:
  init_attempted=True;check_sdl(Init(0x20|0x4000))
  Hint(b'SDL_RENDER_SCALE_QUALITY',b'0')
  window=CreateWindow(b'DNF Native Resource Lab | No Wine | Research Prototype',0x2fff0000,0x2fff0000,1000,720,4)
  require_handle(window,Error);renderer=CreateRenderer(window,-1,0);require_handle(renderer,Error)
  load_pack();receipt_ready=True;last_save=0
  while running:
   ev=Event()
   while Poll(C.byref(ev)):
    b=bytes(ev.raw);kind=struct.unpack_from('<I',b)[0]
    if kind==0x100:running=False
    elif kind==0x200 and b[12]==14:running=False
    elif kind==0x300:
     key=struct.unpack_from('<i',b,20)[0];stats['key_events']+=1
     if key==27:running=False
     elif key==1073741903:next_frame(1)
     elif key==1073741904:next_frame(-1)
     elif key==1073741906:next_entry()
     elif key==9:next_pack()
     elif key==32:playing=not playing;stats['play_toggles']+=1;status='PREVIEW PLAY' if playing else 'PREVIEW PAUSE'
     elif key in (43,61):zoom=min(12,zoom+1);stats['zoom_changes']+=1
     elif key==45:zoom=max(1,zoom-1);stats['zoom_changes']+=1
    elif kind in (0x401,0x402):
     button=b[16];x,y=struct.unpack_from('<ii',b,20)
     if button in (1,3):input_mouse((1 if button==1 else 4) if kind==0x401 else (2 if button==1 else 5),x,y)
     if kind==0x401 and button==1 and 625<=y<665:
      if 30<=x<185:next_frame(-1)
      elif 200<=x<355:next_frame(1)
      elif 370<=x<525:next_entry()
      elif 540<=x<695:next_pack()
      elif 710<=x<965:playing=not playing;stats['play_toggles']+=1
    elif kind==0x400:
     x,y=struct.unpack_from('<ii',b,20);input_mouse(0,x,y)
    elif kind==0x403:
     delta=struct.unpack_from('<i',b,20)[0];direction=struct.unpack_from('<I',b,24)[0]
     if direction==1:delta=-delta
     input_mouse(6,0,0,delta*120);zoom=max(1,min(12,zoom+(1 if delta>0 else -1 if delta<0 else 0)));stats['wheel_events']+=1;stats['zoom_changes']+=1
   now=time.monotonic()
   if playing and now>=next_tick:next_frame(1);next_tick=now+0.15
   Color(renderer,16,25,35,255);Clear(renderer)
   text('DNF NATIVE RESOURCE LAB',30,25,4,(124,222,198))
   text('C++17 DECODER + SDL2 / LOCAL RESOURCE VIEWER',32,69,2)
   text(f'NPK {file_index+1}/{len(files)}   IMG {entry+1}/{Entries(pack)}   FRAME {frame+1}/{Frames(pack,entry)}   ZOOM {zoom}X',32,102,2,(155,177,197))
   # Native checkerboard panel and actual uploaded RGBA texture.
   for yy in range(142,566,24):
    for xx in range(30,686,24):rectangle(xx,yy,min(24,686-xx),min(24,566-yy),(38,56,72) if (xx//24+yy//24)%2 else (31,47,62))
   factor=min(float(zoom),630/w,400/h);dw=max(1,int(w*factor));dh=max(1,int(h*factor));dst=Rect(358-dw//2,354-dh//2,dw,dh)
   check_sdl(Copy(renderer,texture,None,C.byref(dst)))
   text('MODULES VERIFIED',716,152,2,(124,222,198))
   for i,line in enumerate(['NPK NUMERIC INDEX','IMG V2 PIXELS','LINKED FRAMES','ALPHA + CANVAS','NATIVE TEXTURE','MOUSE CONTRACT']):text(line,716,188+i*35,2)
   text(f'CANVAS {w} X {h}',716,424,2)
   text(f'DRAWS {stats["frames_drawn"]}',716,459,2)
   text('NOT A PLAYABLE GAME',716,511,1,(249,193,117))
   text(files[file_index].stem.upper()[:76],32,587,1,(155,177,197))
   for x,width,label in [(30,155,'PREV'),(200,155,'NEXT'),(370,155,'NEXT IMG'),(540,155,'NEXT NPK'),(710,255,'PAUSE' if playing else 'PLAY PREVIEW')]:
    rectangle(x,625,width,40,(39,77,87));text(label,x+14,638,2)
   text('ARROWS: FRAME/IMG  TAB: NPK  SPACE: PLAY  WHEEL: ZOOM  ESC: EXIT',32,682,1)
   text(status[:76],32,706,1,(249,193,117))
   Present(renderer);stats['frames_drawn']+=1;Finish(pack)
   if now-last_save>=0.25:write_receipt();last_save=now
   time.sleep(1/30)
 finally:
  # Keep the original failure; a receipt error must never bypass native cleanup.
  failed=sys.exc_info()[0] is not None
  try:
   if receipt_ready and not failed:write_receipt()
  finally:
   if texture:DestroyTexture(texture)
   if pack:Close(pack)
   if renderer:DestroyRenderer(renderer)
   if window:DestroyWindow(window)
   if init_attempted:Quit()
if __name__=='__main__':main()
