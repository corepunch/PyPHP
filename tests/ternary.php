<?php
// ── Basic ternary ────────────────────────────────────────────────────────────

$x = 5;
$result = $x > 3 ? "big" : "small";
assert($result == "big");

$result2 = $x > 10 ? "big" : "small";
assert($result2 == "small");

// ── Ternary in assignment ────────────────────────────────────────────────────

$a = 1;
$b = $a == 1 ? "one" : "other";
assert($b == "one");

// ── Ternary with variables as values ────────────────────────────────────────

$yes = "yes";
$no = "no";
$flag = true;
$answer = $flag ? $yes : $no;
assert($answer == "yes");

// ── Nested ternary (evaluated left-to-right) ────────────────────────────────

$score = 75;
$grade = $score >= 90 ? "A" : ($score >= 70 ? "C" : "F");
assert($grade == "C");

// ── Ternary in return ────────────────────────────────────────────────────────

function describe($n) {
    return $n > 0 ? "positive" : ($n < 0 ? "negative" : "zero");
}
assert(describe(5) == "positive");
assert(describe(-3) == "negative");
assert(describe(0) == "zero");

// ── Ternary with function call ───────────────────────────────────────────────

$arr = [1, 2, 3];
$msg = count($arr) > 2 ? "many" : "few";
assert($msg == "many");

// ── Boolean coercion ─────────────────────────────────────────────────────────

$zero = 0;
$empty_str = "";
$r1 = $zero ? "truthy" : "falsy";
assert($r1 == "falsy");

$r2 = $empty_str ? "truthy" : "falsy";
assert($r2 == "falsy");

$r3 = 1 ? "truthy" : "falsy";
assert($r3 == "truthy");
