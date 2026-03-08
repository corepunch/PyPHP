<?php
// Tests for ?? nested inside ternary expressions

// $a ? ($b ?? $c) : $d — ?? in true branch
$flag = true;
$b = null;
$c = "found";
$d = "other";
$result = $flag ? ($b ?? $c) : $d;
assert($result == "found");

// ?? in true branch, $b is non-null
$b2 = "first";
$result2 = $flag ? ($b2 ?? $c) : $d;
assert($result2 == "first");

// ?? in false branch
$flag3 = false;
$x = null;
$y = "fallback";
$z = "true_branch";
$result3 = $flag3 ? $z : ($x ?? $y);
assert($result3 == "fallback");

// ($a ?? $b) ? $c : $d — ?? in condition
$cond_null = null;
$cond_val = "yes";
$result4 = ($cond_null ?? $cond_val) ? "truthy" : "falsy";
assert($result4 == "truthy");

// ?? in both branches
$flag5 = true;
$p = null;
$q = "q_val";
$r = null;
$s = "s_val";
$result5 = $flag5 ? ($p ?? $q) : ($r ?? $s);
assert($result5 == "q_val");

$flag6 = false;
$result6 = $flag6 ? ($p ?? $q) : ($r ?? $s);
assert($result6 == "s_val");

// nested ternary with ?? inside a branch
$score = 75;
$default_grade = null;
$label = $score >= 90 ? ($default_grade ?? "A") : ($score >= 70 ? "C" : "F");
assert($label == "C");

// ?? inside ternary in function return
function getLabel($val, $maybeNull, $default) {
    return $val ? ($maybeNull ?? $default) : "other";
}
assert(getLabel(true, "hello", "fallback") == "hello");
assert(getLabel(true, null, "fallback") == "fallback");
assert(getLabel(false, "hello", "fallback") == "other");
