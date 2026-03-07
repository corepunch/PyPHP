<?py
# Raw Python code — no PHP→Python conversion applied.
# Variables shared with PHP use the __ prefix (PHP $x → Python __x).

# Define a Python helper function callable from PHP
def py_double(n):
    return n * 2

# Define a Python generator callable from PHP
def py_range_gen(start, stop):
    i = start
    while i < stop:
        yield i
        i += 1

# Set a variable accessible as $py_greeting in PHP
__py_greeting = "Hello from Python"
?>
<?php
// ── Python-defined function callable from PHP ──────────────────────────────
assert(py_double(21) == 42);
assert(py_double(0) == 0);

// ── Python-defined variable readable as PHP variable ──────────────────────
assert($py_greeting == "Hello from Python");

// ── Python-defined generator usable in foreach ────────────────────────────
$nums = [];
foreach (py_range_gen(1, 5) as $v) {
    array_push($nums, $v);
}
assert(implode(",", $nums) == "1,2,3,4");

// ── Python-defined generator in array_ functions ──────────────────────────
assert(array_sum(py_range_gen(1, 6)) == 15);
assert(implode(",", array_reverse(py_range_gen(1, 4))) == "3,2,1");
?>
<?py
# Multiple <?py blocks are allowed; each shares the same execution scope.
import math as math_module
__pi_approx = round(math_module.pi, 4)
?>
<?php
// ── Variable set in a later <?py block ────────────────────────────────────
assert($pi_approx == 3.1416);
?>
