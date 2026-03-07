<?php
// Tests for variadic ...$args parameters (issue #6)

// Basic variadic: sum(1,2,3)
function sum(...$args) {
    $total = 0;
    foreach ($args as $v) {
        $total = $total + $v;
    }
    return $total;
}
assert(sum(1, 2, 3) == 6);
assert(sum(10, 20) == 30);
assert(sum() == 0);

// Variadic with a leading fixed parameter
function prefixAll($prefix, ...$words) {
    $result = [];
    foreach ($words as $w) {
        $result[] = $prefix . $w;
    }
    return $result;
}
$prefixed = prefixAll("Mr.", "Smith", "Jones", "Brown");
assert(count($prefixed) == 3);
assert($prefixed[0] == "Mr.Smith");
assert($prefixed[1] == "Mr.Jones");
assert($prefixed[2] == "Mr.Brown");

// Count of variadic args
function countArgs(...$args) {
    return count($args);
}
assert(countArgs() == 0);
assert(countArgs(1) == 1);
assert(countArgs(1, 2, 3, 4, 5) == 5);
