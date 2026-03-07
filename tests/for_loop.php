<?php
// ── C-style for loop ────────────────────────────────────────────────────────

// Basic counter
$out = [];
for ($i = 0; $i < 5; $i++) {
    array_push($out, $i);
}
assert($out == [0, 1, 2, 3, 4]);

// Decrementing counter
$out2 = [];
for ($j = 3; $j >= 0; $j--) {
    array_push($out2, $j);
}
assert($out2 == [3, 2, 1, 0]);

// Step by 2
$out3 = [];
for ($k = 0; $k <= 10; $k += 2) {
    array_push($out3, $k);
}
assert($out3 == [0, 2, 4, 6, 8, 10]);

// Nested for loops
$sum = 0;
for ($i = 0; $i < 3; $i++) {
    for ($j = 0; $j < 3; $j++) {
        $sum += 1;
    }
}
assert($sum == 9);

// for loop with break
$found = -1;
for ($i = 0; $i < 10; $i++) {
    if ($i == 5) {
        $found = $i;
        break;
    }
}
assert($found == 5);

// for loop building string
$s = "";
for ($i = 1; $i <= 3; $i++) {
    $s .= $i;
}
assert($s == "123");

// ── Standalone increment/decrement ──────────────────────────────────────────

$n = 0;
$n++;
assert($n == 1);

$n++;
$n++;
assert($n == 3);

$n--;
assert($n == 2);

$m = 5;
$m--;
assert($m == 4);

// ── while loop with increment ────────────────────────────────────────────────

$count = 0;
$i = 0;
while ($i < 4) {
    $count++;
    $i++;
}
assert($count == 4);
assert($i == 4);
