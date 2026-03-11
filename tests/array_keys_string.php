<?php
// Tests for array_keys() on PhpArray with string keys

// Create array with string keys
$map = [];
$map["Node2D"] = "comp1";
$map["Sprite2D"] = "comp2";
$map["Camera"] = "comp3";

$keys = array_keys($map);
assert(count($keys) == 3);
assert($keys[0] == "Node2D");
assert($keys[1] == "Sprite2D");
assert($keys[2] == "Camera");

// Mixed integer + string keys
$mixed = [];
$mixed[] = "first";
$mixed[] = "second";
$mixed["name"] = "third";

$mkeys = array_keys($mixed);
assert(count($mkeys) == 3);
assert($mkeys[0] === 0);
assert($mkeys[1] === 1);
assert($mkeys[2] === "name");

// array_keys with search_value on string-keyed PhpArray
$map2 = [];
$map2["a"] = 1;
$map2["b"] = 2;
$map2["c"] = 1;

$found = array_keys($map2, 1);
assert(count($found) == 2);
assert($found[0] == "a");
assert($found[1] == "c");

// Pure sequential (numeric) array — should still work
$arr = ["x", "y", "z"];
$nkeys = array_keys($arr);
assert($nkeys == [0, 1, 2]);
