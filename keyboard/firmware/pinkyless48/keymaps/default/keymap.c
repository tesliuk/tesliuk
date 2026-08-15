// Default keymap for pinkyless48.
//
// The pinky has three keys (number, top, home) and no bottom row. Because the
// number row keeps all five columns, it carries a full 1234567890 across the
// two halves, so digits do not need a layer.
//
// Everything the pinky would normally carry on the bottom row (Z, Shift,
// Ctrl) has moved onto the thumbs and onto home-row mods, which is the point
// of the layout.
//
// Home-row mods: holding a home-row key gives a modifier, tapping types the
// letter. If they feel fiddly at first, adjust TAPPING_TERM in config.h
// before giving up on them - 200 ms suits most people, slower typists want
// 250-300.
//
// Thumb clusters, per half:  t1 t2 t3  = the comfortable arc
//                              t4 t5   = the deliberate stretch island
//
// This is a starting point, not a finished layout. Expect to rearrange it.

#include QMK_KEYBOARD_H

enum layers {
    _BASE,
    _NAV,
    _SYM,
};

// Home-row mods, strongest fingers get the most-used modifiers.
#define HM_A LGUI_T(KC_A)
#define HM_S LALT_T(KC_S)
#define HM_D LCTL_T(KC_D)
#define HM_F LSFT_T(KC_F)
#define HM_J RSFT_T(KC_J)
#define HM_K RCTL_T(KC_K)
#define HM_L LALT_T(KC_L)
#define HM_SC RGUI_T(KC_SCLN)

#define NAV_SPC LT(_NAV, KC_SPC)
#define SYM_ENT LT(_SYM, KC_ENT)

const uint16_t PROGMEM keymaps[][MATRIX_ROWS][MATRIX_COLS] = {

// BASE - QWERTY. Z sits on a left thumb; it is the only letter the reduced
// bottom row cannot hold.
//
//  1     2     3     4     5          6     7     8     9     0
//  Q     W     E     R     T          Y     U     I     O     P
//  A     S     D     F     G          H     J     K     L     ;
//        X     C     V     B          N     M     ,     .
//   spc  nav   tab                        bsp   sym   ent
//     esc  z                                 del  '
[_BASE] = LAYOUT(
    KC_1,    KC_2,    KC_3,    KC_4,    KC_5,        KC_6,    KC_7,    KC_8,    KC_9,    KC_0,
    KC_Q,    KC_W,    KC_E,    KC_R,    KC_T,        KC_Y,    KC_U,    KC_I,    KC_O,    KC_P,
    HM_A,    HM_S,    HM_D,    HM_F,    KC_G,        KC_H,    HM_J,    HM_K,    HM_L,    HM_SC,
             KC_X,    KC_C,    KC_V,    KC_B,        KC_N,    KC_M,    KC_COMM, KC_DOT,
    NAV_SPC, MO(_NAV), KC_TAB, KC_ESC,  KC_Z,        KC_QUOT, KC_DEL,  KC_BSPC, MO(_SYM), SYM_ENT
),

// NAV - arrows, word/line movement, function keys, media.
[_NAV] = LAYOUT(
    KC_F1,   KC_F2,   KC_F3,   KC_F4,   KC_F5,       KC_F6,   KC_F7,   KC_F8,   KC_F9,   KC_F10,
    KC_TAB,  KC_HOME, KC_UP,   KC_END,  KC_PGUP,     KC_PGUP, KC_HOME, KC_UP,   KC_END,  KC_F11,
    KC_LGUI, KC_LEFT, KC_DOWN, KC_RGHT, KC_PGDN,     KC_PGDN, KC_LEFT, KC_DOWN, KC_RGHT, KC_F12,
             KC_MPRV, KC_MPLY, KC_MNXT, KC_VOLD,     KC_VOLU, KC_MUTE, KC_BRID, KC_BRIU,
    _______, _______, _______, KC_ESC,  KC_CAPS,     KC_INS,  KC_DEL,  KC_BSPC, _______, _______
),

// SYM - symbols. Digits are on the base layer, so this layer is purely
// punctuation and brackets.
[_SYM] = LAYOUT(
    KC_EXLM, KC_AT,   KC_HASH, KC_DLR,  KC_PERC,     KC_CIRC, KC_AMPR, KC_ASTR, KC_LPRN, KC_RPRN,
    KC_GRV,  KC_LABK, KC_RABK, KC_LBRC, KC_RBRC,     KC_MINS, KC_EQL,  KC_LCBR, KC_RCBR, KC_BSLS,
    KC_TILD, KC_UNDS, KC_PLUS, KC_LPRN, KC_RPRN,     KC_PIPE, KC_QUES, KC_SLSH, KC_COLN, KC_DQUO,
             KC_MINS, KC_EQL,  KC_UNDS, KC_PLUS,     KC_AMPR, KC_PERC, KC_SCLN, KC_QUOT,
    _______, _______, _______, QK_BOOT, _______,     _______, _______, _______, _______, _______
),
};
