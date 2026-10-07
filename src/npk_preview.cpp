// DNF resource reconstruction milestone 0.1. Independent C++17 implementation.
// Reads numeric NPK/IMG v2 structures. Opaque entry names are never decoded.
// Does not load/execute Windows code, connect to servers, or patch game files.
#include <algorithm>
#include <cstdint>
#include <cstring>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <limits>
#include <stdexcept>
#include <string>
#include <vector>
#include <zlib.h>
#include <cerrno>
#include <fcntl.h>
#include <unistd.h>
namespace fs = std::filesystem;
using Bytes=std::vector<uint8_t>;
constexpr size_t MAX_FILE=256*1024*1024, MAX_PIXELS=16*1024*1024;
static void require(bool v,const char *m){if(!v)throw std::runtime_error(m);}
struct View {
 const Bytes& data;size_t start=0,size=0;
 View(const Bytes& b):data(b),size(b.size()){}
 View(const Bytes& b,size_t p,size_t n):data(b),start(p),size(n){require(p<=b.size()&&n<=b.size()-p,"range_outside_file");}
 const uint8_t* at(size_t p,size_t n)const{require(p<=size&&n<=size-p,"truncated_structure");return data.data()+start+p;}
 uint32_t u32(size_t p)const{auto b=at(p,4);return uint32_t(b[0])|(uint32_t(b[1])<<8)|(uint32_t(b[2])<<16)|(uint32_t(b[3])<<24);}
};
struct Entry{uint32_t offset,length;};
struct Frame{uint32_t format=0,compression=0,width=0,height=0,length=0,canvas_w=0,canvas_h=0,link=0;int32_t x=0,y=0;size_t offset=0;};
struct Img{View bytes;std::vector<Frame> frames;std::vector<size_t> resolved; explicit Img(View v):bytes(v){}}
;
static Bytes read_file(const fs::path&p){
 std::ifstream f(p,std::ios::binary|std::ios::ate);require(bool(f),"input_not_readable");
 auto n=f.tellg();require(n>=0&&uint64_t(n)<=MAX_FILE,"file_size_limit");Bytes b(static_cast<size_t>(n));f.seekg(0);
 if(!b.empty()){f.read(reinterpret_cast<char*>(b.data()),static_cast<std::streamsize>(b.size()));require(bool(f),"short_read");}return b;
}
static std::vector<Entry> read_npk(const View&v){
 require(std::memcmp(v.at(0,16),"NeoplePack_Bill\0",16)==0,"not_NPK");
 uint32_t n=v.u32(16);require(n>0&&n<=100000,"entry_count_limit");
 size_t end=20+size_t(n)*264;v.at(0,end);std::vector<Entry> entries;
 for(uint32_t i=0;i<n;i++){
  Entry e{v.u32(20+size_t(i)*264),v.u32(24+size_t(i)*264)};
  require(e.offset>=end&&e.length>=32,"entry_overlaps_directory_or_short");v.at(e.offset,e.length);entries.push_back(e);
 }
 // Reject overlapping payloads. Directory order is not assumed to be sorted.
 auto sorted=entries;std::sort(sorted.begin(),sorted.end(),[](Entry a,Entry b){return a.offset<b.offset;});
 for(size_t i=1;i<sorted.size();i++)require(uint64_t(sorted[i-1].offset)+sorted[i-1].length<=sorted[i].offset,"overlapping_entries");
 return entries;
}
static Img read_img(const View&npk,Entry e){
 Img img(View(npk.data,npk.start+e.offset,e.length));const auto&v=img.bytes;
 require(std::memcmp(v.at(0,16),"Neople Img File\0",16)==0,"entry_not_IMG_v2");
 uint32_t index_length=v.u32(16),version=v.u32(24),count=v.u32(28);
 require(version==2,"unsupported_IMG_version");require(count>0&&count<=100000,"frame_count_limit");
 size_t index_end=32+size_t(index_length);v.at(0,index_end);size_t cursor=32,payload=index_end;
 for(uint32_t i=0;i<count;i++){
  require(cursor<=index_end&&index_end-cursor>=4,"frame_index_truncated");Frame f;f.format=v.u32(cursor);
  if(f.format==17){require(index_end-cursor>=8,"link_truncated");f.link=v.u32(cursor+4);require(f.link<count,"link_out_of_range");cursor+=8;}
  else{
   require(f.format>=14&&f.format<=16,"unsupported_pixel_format");require(index_end-cursor>=36,"frame_record_truncated");
   f.compression=v.u32(cursor+4);f.width=v.u32(cursor+8);f.height=v.u32(cursor+12);f.length=v.u32(cursor+16);
   f.x=static_cast<int32_t>(v.u32(cursor+20));f.y=static_cast<int32_t>(v.u32(cursor+24));f.canvas_w=v.u32(cursor+28);f.canvas_h=v.u32(cursor+32);
   require(f.width&&f.height&&uint64_t(f.width)*f.height<=MAX_PIXELS,"pixel_limit");
   require(f.canvas_w&&f.canvas_h&&uint64_t(f.canvas_w)*f.canvas_h<=MAX_PIXELS,"canvas_limit");
   require(f.compression==5||f.compression==6,"unsupported_compression");// In observed uncompressed IMG v2 frames the stored length can be RGBA
   // logical length, while payload uses 16-bit pixels. Derive physical bytes.
   if(f.compression==5) f.length=uint32_t(uint64_t(f.width)*f.height*(f.format==16?4:2));
   v.at(payload,f.length);f.offset=payload;payload+=f.length;cursor+=36;
  }img.frames.push_back(f);
 }
 require(cursor==index_end,"index_size_mismatch");require(payload==v.size,"payload_size_mismatch");
 // Resolve the reference graph once in O(frame_count); reject cycles.
 img.resolved.resize(count);std::vector<uint8_t> state(count,0);
 for(size_t first=0;first<count;first++){
  if(state[first]==2)continue;
  std::vector<size_t> path;size_t current=first,target=first;
  while(true){
   require(current<count,"link_out_of_range");
   if(state[current]==2){target=img.resolved[current];break;}
   require(state[current]!=1,"frame_link_cycle");state[current]=1;path.push_back(current);
   if(img.frames[current].format!=17){target=current;break;}
   current=img.frames[current].link;
  }
  for(auto item:path){img.resolved[item]=target;state[item]=2;}
 }
 return img;
}
static const Frame& resolve(const Img&img,size_t index){
 require(index<img.resolved.size(),"frame_index_out_of_range");
 return img.frames[img.resolved[index]];
}
static Bytes pixels(const Img&img,const Frame&f){
 const size_t count=size_t(f.width)*f.height, bpp=f.format==16?4:2;Bytes raw(count*bpp);
 if(f.compression==6){
  z_stream stream{};stream.next_in=const_cast<Bytef*>(img.bytes.at(f.offset,f.length));stream.avail_in=f.length;
  stream.next_out=raw.data();stream.avail_out=static_cast<uInt>(raw.size());
  require(inflateInit(&stream)==Z_OK,"zlib_init_failed");int rc=inflate(&stream,Z_FINISH);
  bool valid=rc==Z_STREAM_END&&stream.total_out==raw.size()&&stream.total_in==f.length;
  inflateEnd(&stream);require(valid,"zlib_input_or_output_size_mismatch");
 }else{require(f.length==raw.size(),"raw_pixel_size_mismatch");std::copy_n(img.bytes.at(f.offset,f.length),f.length,raw.data());}
 Bytes rgba(count*4);
 for(size_t i=0;i<count;i++){
  auto*d=rgba.data()+i*4;
  if(f.format==16){d[0]=raw[i*4+2];d[1]=raw[i*4+1];d[2]=raw[i*4];d[3]=raw[i*4+3];}
  else{uint16_t v=uint16_t(raw[i*2])|(uint16_t(raw[i*2+1])<<8);
   if(f.format==14){d[0]=uint8_t(((v>>10)&31)*255/31);d[1]=uint8_t(((v>>5)&31)*255/31);d[2]=uint8_t((v&31)*255/31);d[3]=(v&0x8000)?255:0;}
   else{d[0]=uint8_t(((v>>8)&15)*17);d[1]=uint8_t(((v>>4)&15)*17);d[2]=uint8_t((v&15)*17);d[3]=uint8_t(((v>>12)&15)*17);}
  }
 }return rgba;
}
static Bytes canvas(const Frame&f,const Bytes&rgba){
 Bytes out(size_t(f.canvas_w)*f.canvas_h*4,0);
 for(uint32_t y=0;y<f.height;y++)for(uint32_t x=0;x<f.width;x++){
  int64_t dx=int64_t(x)+f.x,dy=int64_t(y)+f.y;
  if(dx>=0&&dy>=0&&dx<f.canvas_w&&dy<f.canvas_h)std::copy_n(rgba.data()+(size_t(y)*f.width+x)*4,4,out.data()+(size_t(dy)*f.canvas_w+size_t(dx))*4);
 }return out;
}
static void be32(Bytes&b,uint32_t n){b.push_back(uint8_t(n>>24));b.push_back(uint8_t(n>>16));b.push_back(uint8_t(n>>8));b.push_back(uint8_t(n));}
static void chunk(Bytes&png,const char*type,const Bytes&data){
 be32(png,static_cast<uint32_t>(data.size()));size_t start=png.size();png.insert(png.end(),type,type+4);png.insert(png.end(),data.begin(),data.end());
 be32(png,static_cast<uint32_t>(crc32(0,png.data()+start,static_cast<uInt>(4+data.size()))));
}
static Bytes png_bytes(uint32_t w,uint32_t h,const Bytes&rgba){
 require(rgba.size()==size_t(w)*h*4,"invalid_RGBA_size");Bytes scan((size_t(w)*4+1)*h);
 for(uint32_t y=0;y<h;y++){scan[(size_t(w)*4+1)*y]=0;std::copy_n(rgba.data()+size_t(y)*w*4,size_t(w)*4,scan.data()+(size_t(w)*4+1)*y+1);}
 uLongf n=compressBound(static_cast<uLong>(scan.size()));Bytes compressed(n);
 require(compress2(compressed.data(),&n,scan.data(),static_cast<uLong>(scan.size()),Z_BEST_SPEED)==Z_OK,"PNG_compression_failed");compressed.resize(n);
 Bytes png={137,80,78,71,13,10,26,10},ihdr;be32(ihdr,w);be32(ihdr,h);ihdr.insert(ihdr.end(),{8,6,0,0,0});chunk(png,"IHDR",ihdr);chunk(png,"IDAT",compressed);chunk(png,"IEND",{});return png;
}
static void write_new(const fs::path&p,const Bytes&b){
 // Atomic exclusivity, unlike exists()+ofstream: never follow an existing link
 // or truncate an existing file even if another process races output creation.
 int fd=::open(p.c_str(),O_WRONLY|O_CREAT|O_EXCL|O_NOFOLLOW,0600);
 require(fd>=0,"output_not_new_or_not_writable");size_t done=0;
 while(done<b.size()){
  ssize_t n=::write(fd,b.data()+done,b.size()-done);
  if(n<0&&errno==EINTR)continue;
  if(n<=0){::close(fd);throw std::runtime_error("output_write_failed");}
  done+=size_t(n);
 }
 require(::close(fd)==0,"output_close_failed");
}
int main(int argc,char**argv){
 try{
  require(argc==3||argc==4,"usage: npk_preview --inspect input.NPK | --export input.NPK NEW_OUTPUT_DIR");
  std::string mode=argv[1];require((mode=="--inspect"&&argc==3)||(mode=="--export"&&argc==4),"invalid_arguments");
  Bytes b=read_file(argv[2]);View v(b);auto entries=read_npk(v);std::vector<Img> images;
  // Fully validate and decode all frames before creating output files.
  size_t frame_count=0,linked=0;uint64_t total_pixels=0,total_source_pixels=0;
  for(auto e:entries){auto img=read_img(v,e);for(size_t j=0;j<img.frames.size();j++){auto&f=resolve(img,j);total_pixels+=uint64_t(f.canvas_w)*f.canvas_h;total_source_pixels+=uint64_t(f.width)*f.height;require(total_pixels<=64*1024*1024,"total_output_pixel_limit");require(total_source_pixels<=64*1024*1024,"total_source_pixel_limit");require(frame_count<16384,"total_frame_limit");pixels(img,f);if(img.frames[j].format==17)linked++;frame_count++;}images.push_back(std::move(img));}
  fs::path dest;if(mode=="--export"){dest=argv[3];require(!fs::exists(dest)&&!fs::is_symlink(dest),"output_directory_must_be_new");require(fs::create_directories(dest),"cannot_create_output_directory");}
  std::cout<<"{\"entries\":"<<entries.size()<<",\"frames\":"<<frame_count<<",\"linked_frames\":"<<linked<<",\"names\":\"opaque_not_decoded\",\"images\":[";
  for(size_t i=0;i<images.size();i++){
   auto&img=images[i];if(i)std::cout<<",";std::cout<<"{\"entry\":"<<i<<",\"frames\":[";
   for(size_t j=0;j<img.frames.size();j++){
    const auto&f=resolve(img,j);if(j)std::cout<<",";
    std::cout<<"{\"frame\":"<<j<<",\"format\":"<<f.format<<",\"width\":"<<f.width<<",\"height\":"<<f.height<<",\"x\":"<<f.x<<",\"y\":"<<f.y<<",\"canvas_w\":"<<f.canvas_w<<",\"canvas_h\":"<<f.canvas_h<<",\"linked\":"<<(img.frames[j].format==17?"true":"false")<<"}";
    if(mode=="--export")write_new(dest/("entry_"+std::to_string(i)+"_frame_"+std::to_string(j)+".png"),png_bytes(f.canvas_w,f.canvas_h,canvas(f,pixels(img,f))));
   }std::cout<<"]}";
  }std::cout<<"],\"execution\":\"native_C++_resource_decode_only\"}\n";return 0;
 }catch(const std::exception&e){std::cerr<<"Error: "<<e.what()<<"\n";return 2;}
}
