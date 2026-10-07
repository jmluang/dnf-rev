#pragma once
#include <array>
#include <cstdint>
#include <optional>

// Independently written model of the visible state contracts in the supplied
// a supplied application. No original machine code, Windows headers, DLLs or game assets.
namespace dnf_re {
enum class MouseEvent { Move, LeftDown, LeftUp, LeftDoubleClick, RightDown, RightUp, Wheel };
struct MouseState {
    int x = 0, y = 0;
    bool left_down = false, right_down = false;
    unsigned left_code = 0, right_code = 0;
    bool changed = false, released = false;
    int wheel_delta = 0;
    bool wheel_up = false, wheel_down = false;

    // Coordinates are already in engine logical space. The Windows event
    // wrapper scales client coordinates to 800 x 600 before this boundary.
    void apply(MouseEvent event, int logical_x, int logical_y, int delta = 0) {
        changed = false;  // Reset on each translator invocation.
        if (event != MouseEvent::Wheel) { x = logical_x; y = logical_y; }
        switch (event) {
        case MouseEvent::Move: break;
        case MouseEvent::LeftDown: left_down = true; left_code = 1; changed = true; break;
        case MouseEvent::LeftUp: left_down = false; left_code = 8; released = true; break;
        case MouseEvent::LeftDoubleClick: left_code = 0x40; break;
        case MouseEvent::RightDown: right_down = true; right_code = 2; changed = true; break;
        case MouseEvent::RightUp: right_down = false; right_code = 0x10; released = true; break;
        case MouseEvent::Wheel:
            wheel_delta = delta;
            if (delta > 0) { wheel_up = true; wheel_down = false; }
            else if (delta < 0) { wheel_up = false; wheel_down = true; }
            // Zero leaves direction flags unchanged, preserving the direction state.
            break;
        }
    }
    void finish_frame() {
        // Called after the application tick.
        if (left_code == 8) left_code = 0;
        if (right_code == 0x10) right_code = 0;
        released = false;
        wheel_delta = 0; wheel_up = false; wheel_down = false;
    }
};

struct KeyboardState {
    using Snapshot = std::array<std::uint8_t, 256>;
    Snapshot current{}, previous{};
    bool enabled = true;
    // Sampling copies current to previous first.
    // A failed Acquire/Poll does not clear current. nullopt models that path.
    void sample(const std::optional<Snapshot>& next) {
        previous = current;
        if (next) current = *next;
    }
    bool held(unsigned scancode) const {
        return enabled && scancode < current.size() && current[scancode] != 0;
    }
    bool pressed(unsigned scancode) const {
        return held(scancode) && previous[scancode] == 0;
    }
    // Modifier flags: 1=left shift, 2=left alt,
    // 4=left control; 7 bypasses filtering; 0 requires none of those held.
    bool pressed_with_modifiers(unsigned scancode, unsigned flags) const {
        if (!pressed(scancode)) return false;
        const bool shift = held(0x2a), alt = held(0x38), control = held(0x1d);
        if (flags == 7) return true;
        if (flags == 0) return !shift && !alt && !control;
        return (!(flags & 1) || shift) && (!(flags & 2) || alt) && (!(flags & 4) || control);
    }
};
} // namespace dnf_re
