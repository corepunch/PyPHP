<?php
// ── Increment/decrement operators inside expressions ─────────────────────────

// Post-increment ($x++): returns old value, then increments
$i = 5;
$got = intval(strval($i++));
assert($got == 5);
assert($i == 6);

// Post-decrement ($x--): returns old value, then decrements
$j = 10;
$got = intval(strval($j--));
assert($got == 10);
assert($j == 9);

// Pre-increment (++$x): increments first, returns new value
$k = 7;
$got = intval(strval(++$k));
assert($got == 8);
assert($k == 8);

// Pre-decrement (--$x): decrements first, returns new value
$m = 3;
$got = intval(strval(--$m));
assert($got == 2);
assert($m == 2);

// Post-increment as a function argument (the motivating use-case from the issue)
function get_nth($arr, $n) {
    return $arr[$n];
}

$arr = [10, 20, 30, 40];
$idx = 0;
$val = get_nth($arr, $idx++);
assert($val == 10);  // old index (0) used
assert($idx == 1);   // incremented after the call

$val = get_nth($arr, $idx++);
assert($val == 20);  // old index (1) used
assert($idx == 2);

// Post-decrement as a function argument
$idx2 = 3;
$val2 = get_nth($arr, $idx2--);
assert($val2 == 40);  // old index (3) used
assert($idx2 == 2);   // decremented after the call

// Pre-increment as a function argument
$idx3 = 0;
$val3 = get_nth($arr, ++$idx3);
assert($val3 == 20);  // new index (1) used
assert($idx3 == 1);

// Pre-decrement as a function argument
$idx4 = 3;
$val4 = get_nth($arr, --$idx4);
assert($val4 == 30);  // new index (2) used
assert($idx4 == 2);

// Post-increment in assignment RHS
$x = 0;
$a = $x++;
assert($a == 0);
assert($x == 1);

// Post-decrement in assignment RHS
$y = 5;
$b = $y--;
assert($b == 5);
assert($y == 4);
?>
