<?php
// Tests for ?? null-coalescing operator with statement prefixes (issue #1)

// Simple assignment: $a ?? $b
$a = null;
$b = "default";
$result = $a ?? $b;
assert($result == "default");

// Chain of three: $a ?? $b ?? $c
$c = "fallback";
$result2 = $a ?? $b ?? $c;
assert($result2 == "default");

// Both null: falls through to last
$x = null;
$y = null;
$z = "found";
$result3 = $x ?? $y ?? $z;
assert($result3 == "found");

// First non-null wins
$val = "first";
$other = "second";
$result4 = $val ?? $other;
assert($result4 == "first");

// return $a ?? $b (issue #1 main case: should not become 'return _php_coalesce(lambda: return ...)')
function getDefault($arr, $key) {
    return $arr[$key] ?? "missing";
}
$data = array("name" => "Alice");
assert(getDefault($data, "name") == "Alice");
assert(getDefault($data, "age") == "missing");

// echo $a ?? $b
$greeting = null;
$echo_result = $greeting ?? "Hello";
assert($echo_result == "Hello");

// Nested in array access
$cfg = array("timeout" => 30);
$timeout = $cfg["timeout"] ?? 60;
assert($timeout == 30);
$retries = $cfg["retries"] ?? 3;
assert($retries == 3);
