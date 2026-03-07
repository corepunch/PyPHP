<?php
// ── do/while loop ────────────────────────────────────────────────────────────

// Basic do/while
$i = 0;
do {
    $i++;
} while ($i < 3);
assert($i == 3);

// Body always executes at least once
$executed = 0;
do {
    $executed++;
} while (false);
assert($executed == 1);

// Collecting values
$out = [];
$n = 1;
do {
    array_push($out, $n);
    $n *= 2;
} while ($n <= 8);
assert($out == [1, 2, 4, 8]);

// Nested do/while
$outer = 0;
$inner_total = 0;
do {
    $outer++;
    $inner = 0;
    do {
        $inner++;
        $inner_total++;
    } while ($inner < 2);
} while ($outer < 3);
assert($outer == 3);
assert($inner_total == 6);
