<?php
// Tests for string concatenation inside arrow function bodies

// Basic: fn($p) => $prefix . "." . $p
$prefix = "prefix";
$items = ["item1", "item2", "item3"];
$parts = array_map(fn($p) => $prefix . "." . $p, $items);
assert($parts[0] == "prefix.item1");
assert($parts[1] == "prefix.item2");
assert($parts[2] == "prefix.item3");

// Arrow fn with subscript access and concat
$attribs = [["a", "x"], ["b", "y"]];
$result = array_map(fn($p) => $prefix . "." . $p[0], $attribs);
assert($result[0] == "prefix.a");
assert($result[1] == "prefix.b");

// Three-way concat in arrow body
$sep = "-";
$labels = array_map(fn($x) => "["  . $x . "]", ["one", "two"]);
assert($labels[0] == "[one]");
assert($labels[1] == "[two]");

// No concat in body: should still work
$doubled = array_map(fn($n) => $n * 2, [1, 2, 3]);
assert($doubled == [2, 4, 6]);
