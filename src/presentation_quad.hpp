#pragma once
#include <array>
#include <cstddef>
#include <cstdint>
#include <stdexcept>
#include <type_traits>

// Bounded final-presentation geometry model.
// This is the final texture-to-backbuffer blit, not a universal sprite API.
// No Windows code, D3D headers, binary loading or execution is involved.
namespace dnf_render_proof {
struct Vertex28 {
    float x, y, z, rhw;
    std::uint32_t diffuse_argb;
    float u, v;
};
static_assert(std::is_standard_layout<Vertex28>::value, "plain vertex layout");
static_assert(sizeof(Vertex28) == 28, "observed D3D stride 0x1c");
static_assert(offsetof(Vertex28, diffuse_argb) == 16, "FVF diffuse offset");
static_assert(offsetof(Vertex28, u) == 20 && offsetof(Vertex28, v) == 24,
              "FVF texture-coordinate offsets");

inline std::array<Vertex28, 4> observed_presentation_quad(std::uint32_t width,
                                                        std::uint32_t height) {
    // Safety bound is prototype policy, not a recovered original check.
    if (width == 0 || height == 0 || width > 16384 || height > 16384)
        throw std::invalid_argument("backbuffer dimensions must be 1..16384");
    const float r = static_cast<float>(width) - 0.5f;
    const float b = static_cast<float>(height) - 0.5f;
    return {{{-0.5f, b,     0.f, 1.f, 0xffffffffu, 0.f, 1.f},
             {-0.5f, -0.5f, 0.f, 1.f, 0xffffffffu, 0.f, 0.f},
             {r,     b,     0.f, 1.f, 0xffffffffu, 1.f, 1.f},
             {r,    -0.5f,  0.f, 1.f, 0xffffffffu, 1.f, 0.f}}};
}

struct HostVertex { float x, y, u, v; };
// Native backends whose top-left pixel-edge is (0,0) should remove D3D9's
// half-pixel offset. The return is normalized clip XY, with top-left UV.
// This is a porting adapter, not a claim that the original uses clip vertices.
inline std::array<HostVertex, 4> presentation_clip_quad(std::uint32_t width,
                                                      std::uint32_t height) {
    auto source = observed_presentation_quad(width, height);
    std::array<HostVertex, 4> out{};
    for (std::size_t i = 0; i != source.size(); ++i) {
        out[i] = {2.f * (source[i].x + 0.5f) / static_cast<float>(width) - 1.f,
                  1.f - 2.f * (source[i].y + 0.5f) / static_cast<float>(height),
                  source[i].u, source[i].v};
    }
    return out;
}

// D3DPT_TRIANGLESTRIP = 5, two triangles, four vertices in BL/TL/BR/TR order.
inline constexpr std::uint32_t observed_fvf = 0x144;
inline constexpr std::uint32_t observed_primitive_type = 5;
inline constexpr std::uint32_t observed_primitive_count = 2;
// Equivalent list topology for a backend that only exposes triangle lists.
inline constexpr std::array<std::uint16_t, 6> triangle_list_indices{{0,1,2,2,1,3}};
}
