// Native ABI bridge for the resource prototype; never loads a game binary.
#define main resource_cli_main
#include "npk_preview.cpp"
#undef main
#include "input_state.hpp"
#include "presentation_quad.hpp"
// IMG metadata is loaded on demand: an avatar NPK can contain many appearances,
// while the offline actor uses only selected entries. The cache retains a bounded
// total number of parsed frame records and the source bytes remain immutable.
#include <memory>
struct Pack {
 Bytes source;std::vector<Entry> entries;std::vector<std::unique_ptr<Img>> images;Bytes frame;
 size_t cached_frames=0;
 dnf_re::MouseState mouse;
 explicit Pack(const char*path):source(read_file(path)),entries(read_npk(View(source))),images(entries.size()){}
 Img& image(size_t entry){
  require(entry<entries.size(),"entry_out_of_range");
  if(!images[entry]){
   auto candidate=std::make_unique<Img>(read_img(View(source),entries[entry]));
   require(candidate->frames.size()<=16384-cached_frames,"cached_frame_limit");
   cached_frames+=candidate->frames.size();images[entry]=std::move(candidate);
  }
  return *images[entry];
 }
};
static thread_local std::string last_error;
extern "C" {
const char*dnf_error(){return last_error.c_str();}
void*dnf_open(const char*path){try{return new Pack(path);}catch(const std::exception&e){last_error=e.what();return nullptr;}}
void dnf_close(void*p){delete static_cast<Pack*>(p);}
int dnf_entries(void*p){return p?static_cast<int>(static_cast<Pack*>(p)->entries.size()):0;}
int dnf_frames(void*p,int entry){
 try{auto*q=static_cast<Pack*>(p);require(q&&entry>=0,"invalid_argument");return static_cast<int>(q->image(size_t(entry)).frames.size());}
 catch(const std::exception&e){last_error=e.what();return 0;}
}
const uint8_t*dnf_frame(void*p,int entry,int frame,int*out_w,int*out_h){
 try{auto*q=static_cast<Pack*>(p);require(q&&out_w&&out_h&&entry>=0&&frame>=0,"invalid_argument");auto&img=q->image(size_t(entry));const auto&f=resolve(img,size_t(frame));q->frame=canvas(f,pixels(img,f));*out_w=int(f.canvas_w);*out_h=int(f.canvas_h);return q->frame.data();}
 catch(const std::exception&e){last_error=e.what();return nullptr;}
}
int dnf_mouse_event(void*p,int event,int x,int y,int wheel,int*out){
 if(!p||!out||event<0||event>6)return -1;
 auto&q=static_cast<Pack*>(p)->mouse;q.apply(static_cast<dnf_re::MouseEvent>(event),x,y,wheel);
 out[0]=q.x;out[1]=q.y;out[2]=int(q.left_code);out[3]=int(q.right_code);out[4]=q.left_down;out[5]=q.right_down;out[6]=q.wheel_delta;return 0;
}
void dnf_finish_frame(void*p){if(p)static_cast<Pack*>(p)->mouse.finish_frame();}
int dnf_quad(unsigned w,unsigned h,float*out){
 if(!out)return -1;
 try{auto q=dnf_render_proof::presentation_clip_quad(w,h);for(size_t i=0;i<q.size();i++){out[i*4]=q[i].x;out[i*4+1]=q[i].y;out[i*4+2]=q[i].u;out[i*4+3]=q[i].v;}return 0;}catch(...){return -1;}
}
}
