<?php
// Tests for pass-by-reference parameter syntax being stripped (&$param)

// Named function with &$param - the & is stripped; for lists Python passes by ref
function collectItems($type_, $path, &$result) {
    $result[] = [$path, $type_];
}

$items = [];
collectItems("typeA", "/path/a", $items);
collectItems("typeB", "/path/b", $items);
assert(count($items) == 2);
assert($items[0][0] == "/path/a");
assert($items[1][1] == "typeB");

// Pass-by-ref with type hint (stripped by type hint step first)
function addValue(string $key, int $val, &$acc) {
    $acc[$key] = $val;
}

$acc = [];
addValue("x", 10, $acc);
addValue("y", 20, $acc);
assert($acc["x"] == 10);
assert($acc["y"] == 20);
