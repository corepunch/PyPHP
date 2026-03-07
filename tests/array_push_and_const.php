<?php
// ── Array push shorthand $arr[] = val ────────────────────────────────────────

$arr = [];
$arr[] = 1;
$arr[] = 2;
$arr[] = 3;
assert($arr == [1, 2, 3]);
assert(count($arr) == 3);

// Push string values
$words = ["hello"];
$words[] = "world";
assert(implode(" ", $words) == "hello world");

// Push in a loop
$squares = [];
for ($i = 1; $i <= 4; $i++) {
    $squares[] = $i * $i;
}
assert($squares == [1, 4, 9, 16]);

// Push in foreach
$nums = [1, 2, 3, 4, 5];
$evens = [];
foreach ($nums as $n) {
    if ($n % 2 == 0) {
        $evens[] = $n;
    }
}
assert($evens == [2, 4]);

// ── Constants (define / const) ──────────────────────────────────────────────

define('MAX_SIZE', 100);
define('APP_NAME', 'PyPHP');
assert(MAX_SIZE == 100);
assert(APP_NAME == 'PyPHP');

// define in conditional context
define('PI_APPROX', 3.14159);
assert(PI_APPROX > 3.14);
assert(PI_APPROX < 3.15);

// ── const keyword ────────────────────────────────────────────────────────────

const GREETING = "Hello";
assert(GREETING == "Hello");

const MAX_RETRIES = 5;
assert(MAX_RETRIES == 5);
