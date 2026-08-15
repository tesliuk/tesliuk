// Extra configuration that keyboard.json cannot express.
#pragma once

// Home-row mods live or die by this number. 200 ms suits most people; if you
// get modifiers when you meant letters, raise it to 250-300. If you get
// letters when you meant modifiers, lower it.
#define TAPPING_TERM 200

// Only treat a hold as a mod if another key is pressed *and released* while
// held. This makes home-row mods far more forgiving during fast typing.
#define PERMISSIVE_HOLD

// Never fire a mod when the same key is being repeated quickly.
#define QUICK_TAP_TERM 0

// The left half is the one plugged into USB by default. Change to
// MASTER_RIGHT, or use the EE_HANDS scheme, if you prefer the other side.
#define MASTER_LEFT
