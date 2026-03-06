<?php
// ── getopt() ────────────────────────────────────────────────────────────────
// When no real CLI args are present (test runner passes no extra args after
// the php file path), getopt() returns an empty dict.
$opts = getopt("u:h", ["user:", "help"]);
assert(is_array($opts))

// ── isset() with array keys ──────────────────────────────────────────────────
$map = ['a' => 1, 'b' => null];
assert(isset($map['a']))
assert(!isset($map['b']))
assert(!isset($map['missing']))

// isset() with a plain variable
$x = 42;
assert(isset($x))
$y = null;
assert(!isset($y))

// ── null-coalescing operator ?? ───────────────────────────────────────────────
$a = null;
$b = $a ?? "default";
assert($b == "default")

$c = "hello";
$d = $c ?? "ignored";
assert($d == "hello")

// chained ??
$p = null;
$q = null;
$r = "found";
$result = $p ?? $q ?? $r;
assert($result == "found")

// ?? with missing array key (must not throw)
$arr = ['x' => 10];
$val = $arr['missing'] ?? 99;
assert($val == 99)

$val2 = $arr['x'] ?? 0;
assert($val2 == 10)

// ── isset() with multiple arguments ──────────────────────────────────────────
$m = ['k' => 1];
$n = 5;
assert(isset($n))
assert(!isset($m['nope']))
?>
