<?php
// Tests for anonymous closures with use clause (issue #5)

// Closure assigned to variable without use
$double = function($x) {
    return $x * 2;
};
assert($double(5) == 10);
assert($double(3) == 6);

// Closure with multiple parameters
$add = function($a, $b) {
    return $a + $b;
};
assert($add(3, 4) == 7);

// Closure capturing outer variable (read-only, no & needed for reading)
$multiplier = 3;
$triple = function($x) use ($multiplier) {
    return $x * $multiplier;
};
assert($triple(4) == 12);
assert($triple(7) == 21);

// Closure with use clause is stripped of 'use' clause (no syntax error)
$base = 100;
$addBase = function($x) use ($base) {
    return $x + $base;
};
// Python closures naturally capture $base as __base from outer scope
assert($addBase(5) == 105);
assert($addBase(50) == 150);

// Recursive-style using assignment
$factorial = function($n) {
    $result = 1;
    $i = 1;
    while ($i <= $n) {
        $result = $result * $i;
        $i = $i + 1;
    }
    return $result;
};
assert($factorial(5) == 120);
assert($factorial(0) == 1);
