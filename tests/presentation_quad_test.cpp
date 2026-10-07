#include "presentation_quad.hpp"
#include <cassert>
#include <iostream>
#include <limits>
using namespace dnf_render_proof;
int main() {
    for (const auto dims : {std::array<unsigned,2>{1,1}, {800,600}, {1280,720}, {16384,16384}}) {
        const auto v = observed_presentation_quad(dims[0], dims[1]);
        assert(v[0].x == -0.5f && v[0].y == dims[1] - 0.5f);
        assert(v[1].x == -0.5f && v[1].y == -0.5f);
        assert(v[2].x == dims[0] - 0.5f && v[2].y == dims[1] - 0.5f);
        assert(v[3].x == dims[0] - 0.5f && v[3].y == -0.5f);
        for (const auto &p : v) assert(p.z == 0.f && p.rhw == 1.f && p.diffuse_argb == 0xffffffffu);
        assert(v[0].u == 0.f && v[0].v == 1.f && v[1].u == 0.f && v[1].v == 0.f);
        assert(v[2].u == 1.f && v[2].v == 1.f && v[3].u == 1.f && v[3].v == 0.f);
        const auto h = presentation_clip_quad(dims[0], dims[1]);
        assert(h[0].x == -1.f && h[0].y == -1.f);
        assert(h[1].x == -1.f && h[1].y == 1.f);
        assert(h[2].x == 1.f && h[2].y == -1.f);
        assert(h[3].x == 1.f && h[3].y == 1.f);
        for (unsigned i=0;i<4;++i) assert(h[i].u == v[i].u && h[i].v == v[i].v);
    }
    assert((triangle_list_indices == std::array<std::uint16_t,6>{{0,1,2,2,1,3}}));
    assert(observed_fvf == 0x144 && observed_primitive_type == 5 && observed_primitive_count == 2);
    unsigned rejected=0;
    for (const auto dims : {std::array<unsigned,2>{0,1}, {1,0}, {16385,1}, {1,16385}, {std::numeric_limits<unsigned>::max(),1}}) {
        try { (void)observed_presentation_quad(dims[0], dims[1]); }
        catch (const std::invalid_argument&) { ++rejected; }
    }
    assert(rejected == 5);
    std::cout << "PASS: 4 dimension cases, vertex/UV/layout/topology contract, 5 safety rejects\n";
}
