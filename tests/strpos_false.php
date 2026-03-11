<?php
// Tests for strpos() returning false (not -1) when needle not found

// Not found: should return false
$r = strpos("hello", "xyz");
assert($r === false);

// Found: should return integer position
$r2 = strpos("hello", "ell");
assert($r2 === 1);

// The classic PHP !== false idiom
if (strpos("hello2D", "2D") !== false) {
    $found = true;
} else {
    $found = false;
}
assert($found === true);

if (strpos("hello", "xyz") !== false) {
    $notFound = false;
} else {
    $notFound = true;
}
assert($notFound === true);

// Position found should be a non-negative integer
$r3 = strpos("hello", "ell");
assert($r3 == 1);
assert($r3 !== false);

// strrpos also returns false when not found
$r4 = strrpos("hello", "xyz");
assert($r4 === false);

$r5 = strrpos("hello", "l");
assert($r5 === 3);
