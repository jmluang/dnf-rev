#include "input_state.hpp"
#include <iostream>
#include <stdexcept>
static unsigned checks = 0;
static void check(bool value, const char* label) {
    ++checks; if (!value) throw std::runtime_error(label);
}
int main() {
    using namespace dnf_re;
    MouseState m;
    m.apply(MouseEvent::LeftDown, 100, 200);
    check(m.left_down && m.left_code == 1 && m.changed, "left press");
    m.finish_frame();
    check(m.left_down && m.left_code == 1 && m.changed, "held code and changed persist across frame end");
    m.apply(MouseEvent::Move, 101, 202);
    check(!m.changed && m.left_down && m.x == 101 && m.y == 202, "move resets changed only");
    m.apply(MouseEvent::LeftUp, 101, 202);
    check(!m.left_down && m.left_code == 8 && m.released && !m.changed, "left release");
    m.finish_frame();
    check(m.left_code == 0 && !m.released, "release one-frame reset");
    m.apply(MouseEvent::RightDown, 110, 210);
    check(m.right_down && m.right_code == 2 && m.changed, "right press");
    m.apply(MouseEvent::RightUp, 111, 211);
    check(!m.right_down && m.right_code == 0x10 && m.released, "right release");
    m.finish_frame();
    check(m.right_code == 0 && !m.released, "right release reset");
    m.apply(MouseEvent::LeftDoubleClick, 112, 212);
    m.finish_frame();
    check(m.left_code == 0x40 && !m.left_down, "doubleclick changes only code");
    m.apply(MouseEvent::Wheel, 9000, 9000, 120);
    check(m.wheel_delta == 120 && m.wheel_up && !m.wheel_down && m.x == 112 && m.y == 212, "wheel preserves coordinates");
    m.apply(MouseEvent::Wheel, 0, 0, 0);
    check(m.wheel_delta == 0 && m.wheel_up, "zero wheel retains direction flag");
    m.apply(MouseEvent::Wheel, 0, 0, -240);
    check(m.wheel_delta == -240 && !m.wheel_up && m.wheel_down, "negative wheel");
    m.finish_frame();
    check(!m.wheel_up && !m.wheel_down && m.wheel_delta == 0, "wheel frame reset");
    KeyboardState k; KeyboardState::Snapshot s{};
    s[0x1e] = 0x80; k.sample(s);
    check(k.held(0x1e) && k.pressed(0x1e), "first A press, DirectInput high bit accepted");
    check(k.pressed_with_modifiers(0x1e, 0), "unmodified press");
    k.sample(s); check(k.held(0x1e) && !k.pressed(0x1e), "held is not repeated press");
    k.sample(std::nullopt); check(k.held(0x1e) && !k.pressed(0x1e), "failed poll preserves held state");
    s[0x1e] = 0; k.sample(s); check(!k.held(0x1e), "release snapshot");
    s[0x1e] = 1; s[0x2a] = 1; k.sample(s);
    check(!k.pressed_with_modifiers(0x1e, 0) && k.pressed_with_modifiers(0x1e, 1), "shift modifier");
    check(k.pressed_with_modifiers(0x1e, 7) && !k.pressed_with_modifiers(0x1e, 2), "any and alt modifier filters");
    check(!k.held(256) && !k.pressed(256), "safe invalid scancode");
    k.enabled = false; check(!k.held(0x1e), "input disabled");
    std::cout << "PASS: " << checks << " input contract checks\n";
}
