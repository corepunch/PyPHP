<?php
// PHP 7.4 arrow functions: fn($param) => expr
$doubled = array_map(fn($x) => $x * 2, [1, 2, 3]);
assert(implode(",", $doubled) == "2,4,6");

$filtered = array_filter([1, 2, 3, 4, 5], fn($x) => $x > 2);
assert(implode(",", $filtered) == "3,4,5");

$added = array_map(fn($x) => $x + 10, [1, 2, 3]);
assert(implode(",", $added) == "11,12,13");

// Arrow function returning a string using interpolation
$keys = ["foo", "bar", "baz"];
$prefixed = array_map(fn($k) => "item_$k", $keys);
assert(implode(",", $prefixed) == "item_foo,item_bar,item_baz");

// Arrow function in a template expression
?>
<?= implode(", ", array_map(fn($f) => $f, ["alpha", "beta", "gamma"])) ?>
