<?php
// Tests for ?? null-coalescing inside function calls and nested expressions

// Issue 1: ?? inside function call argument (using an array directly)
$elemWithParent = ["parent" => "parentVal"];
$parent = strval($elemWithParent["parent"] ?? "");
assert($parent == "parentVal");

// Missing key falls back to default
$elemEmpty = [];
$parent2 = strval($elemEmpty["parent"] ?? "none");
assert($parent2 == "none");

// ?? as function call argument with array access
$globalComponents = ["MyComp" => "compObj"];
$compName = "MyComp";
$comp3 = $globalComponents[$compName] ?? null;
assert($comp3 == "compObj");

$missing = "MissingComp";
$comp4 = $globalComponents[$missing] ?? null;
assert($comp4 === null);

// Nested ?? inside intval()
$data = ["count" => "42"];
$n = intval($data["count"] ?? "0");
assert($n == 42);

$n2 = intval($data["missing"] ?? "0");
assert($n2 == 0);

// Multiple ?? inside a function call (chain)
$cfg = [];
$timeout = intval($cfg["timeout"] ?? $cfg["wait"] ?? "30");
assert($timeout == 30);

// ?? inside strval()
$arr = ["key" => "value"];
$val = strval($arr["key"] ?? "default");
assert($val == "value");

$val2 = strval($arr["nokey"] ?? "default");
assert($val2 == "default");
