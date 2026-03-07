<?php
// ── preg_match ───────────────────────────────────────────────────────────────

// Basic match
$matches = [];
$r = preg_match('/\d+/', "abc123def", $matches);
assert($r == 1);
assert($matches[0] == "123");

// No match
$m2 = [];
$r2 = preg_match('/xyz/', "abc123def", $m2);
assert($r2 == 0);

// Capture groups
$m3 = [];
$r3 = preg_match('/(\d{4})-(\d{2})-(\d{2})/', "Date: 2024-01-15", $m3);
assert($r3 == 1);
assert($m3[0] == "2024-01-15");
assert($m3[1] == "2024");
assert($m3[2] == "01");
assert($m3[3] == "15");

// Case-insensitive
$m4 = [];
$r4 = preg_match('/hello/i', "HELLO WORLD", $m4);
assert($r4 == 1);

// ── preg_replace ─────────────────────────────────────────────────────────────

$s = preg_replace('/\s+/', '_', "hello world foo");
assert($s == "hello_world_foo");

// Replace with backreference
$date = preg_replace('/(\d{4})-(\d{2})-(\d{2})/', '$3/$2/$1', "2024-01-15");
assert($date == "15/01/2024");

// No match — original returned
$s2 = preg_replace('/xyz/', 'ABC', "hello world");
assert($s2 == "hello world");

// ── preg_split ───────────────────────────────────────────────────────────────

$parts = preg_split('/[\s,]+/', "one two,three  four");
assert(count($parts) == 4);
assert($parts[0] == "one");
assert($parts[3] == "four");

// ── preg_match_all ────────────────────────────────────────────────────────────

$all = [];
$count = preg_match_all('/\d+/', "a1b22c333", $all);
assert($count == 3);
assert($all[0][0] == "1");
assert($all[0][1] == "22");
assert($all[0][2] == "333");

// ── preg_quote ───────────────────────────────────────────────────────────────

$special = preg_quote("hello.world+test", '/');
$quoted_m = [];
$pattern = '/' . $special . '/';
preg_match($pattern, "prefix hello.world+test suffix", $quoted_m);
assert($quoted_m[0] == "hello.world+test");
