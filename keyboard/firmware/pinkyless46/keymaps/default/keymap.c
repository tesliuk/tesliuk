// Default keymap for pinkyless46.
//
// The board has no pinky bottom row and no pinky number row - the pinky gets
// exactly two keys, on the top and home rows. Everything the pinky would
// normally carry (Z, Shift, Ctrl, Tab, Esc, Enter, Backspace) has been moved
// onto the thumbs or onto home-row mods, which is the whole point of the
// layout.
//
// Home-row mods: holding a home-row key gives a modifier, tapping types the
// letter. If you find them fiddly at first, raise TAPPING_TERM in config.h
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

// BASE - QWERTY, minus Z which lives on a left thumb.
//
//        1     2     3     4          7     8     9     0
//  Q     W     E     R     T          Y     U     I     O     P
//  A     S     D     F     G          H     J     K     L     ;
//        X     C     V     B          N     M     ,     .     /
//   spc  nav   tab                        bsp   sym   ent
//     esc  z                                 del  '
[_BASE] = LAYOUT(
             KC_1,    KC_2,    KC_3,    KC_4,        KC_7,    KC_8,    KC_9,    KC_0,
    KC_Q,    KC_W,    KC_E,    KC_R,    KC_T,        KC_Y,    KC_U,    KC_I,    KC_O,    KC_P,
    HM_A,    HM_S,    HM_D,    HM_F,    KC_G,        KC_H,    HM_J,    HM_K,    HM_L,    HM_SC,
             KC_X,    KC_C,    KC_V,    KC_B,        KC_N,    KC_M,    KC_COMM, KC_DOT,
    NAV_SPC, MO(_NAV), KC_TAB, KC_ESC,  KC_Z,        KC_QUOT, KC_DEL,  KC_BSPC, MO(_SYM), SYM_ENT
),

// NAV - arrows, word/line movement, function keys.
[_NAV] = LAYOUT(
             KC_F1,   KC_F2,   KC_F3,   KC_F4,       KC_F7,   KC_F8,   KC_F9,   KC_F10,
    KC_TAB,  KC_HOME, KC_UP,   KC_END,  KC_PGUP,     KC_PGUP, KC_HOME, KC_UP,   KC_END,  KC_F11,
    KC_LGUI, KC_LEFT, KC_DOWN, KC_RGHT, KC_PGDN,     KC_PGDN, KC_LEFT, KC_DOWN, KC_RGHT, KC_F12,
             KC_MPRV, KC_MPLY, KC_MNXT, KC_VOLD,     KC_VOLU, KC_MUTE, KC_BRID, KC_BRIU,
    _______, _______, _______, KC_ESC,  KC_CAPS,     KC_INS,  KC_DEL,  KC_BSPC, _______, _______
),

// SYM - symbols and the numbers that do not fit the base number row.
[_SYM] = LAYOUT(
             KC_EXLM, KC_AT,   KC_HASH, KC_DLR,      KC_AMPR, KC_ASTR, KC_LPRN, KC_RPRN,
    KC_GRV,  KC_5,    KC_6,    KC_PERC, KC_CIRC,     KC_MINS, KC_EQL,  KC_LBRC, KC_RBRC, KC_BSLS,
    KC_TILD, KC_LCBR, KC_RCBR, KC_UNDS, KC_PLUS,     KC_PIPE, KC_QUES, KC_SLSH, KC_COLN, KC_DQUO,
             KC_LABK, KC_RABK, KC_MINS, KC_EQL,      KC_PLUS, KC_UNDS, KC_COMM, KC_DOT,
    _______, _______, _______, QK_BOOT, _______,     _______, _______, _______, _______, _______
),
};
