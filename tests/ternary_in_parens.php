<?php
// Regression tests for:
//   1. Ternary operator inside parentheses  ($cond ? a : b)  →  (a if cond else b)
//   2. return / echo / yield with associative array literal  return ['k' => v]

// ── ternary inside explicit parentheses ──────────────────────────────────────

$x = 3;
$r = ($x > 2 ? 'big' : 'small');
assert($r == 'big');

// ternary as function argument
function wrap($val) { return "[$val]"; }
$r2 = wrap($x > 2 ? 'yes' : 'no');
assert($r2 == '[yes]');

// ternary inside concat (the reported failure pattern)
$const = true;
$ptr   = false;
$decl  = 'int' . ($const ? ' const' : '') . ($ptr ? '*' : '');
assert($decl == 'int const');

// deeply parenthesised ternary
$n = 2;
$pop = (!$n ? '' : ($n == 1 ? 'one' : ($n == 2 ? 'two' : 'many')));
assert($pop == 'two');

// ── makeArg-style function (full original pattern) ────────────────────────────

function makeArg($name, $type, $ptr, $const, $i) {
    $info = ['decl' => '%s', 'pop' => '%s_pop_%s'];
    $decl = sprintf($info['decl'] ?? '%s_t', $type) . ($const ? ' const' : '') . ($ptr ? '*' : '');
    $fmt  = $ptr ? str_replace('= *', '= ', $info['pop'] ?? '') : ($info['pop'] ?? '');
    $n    = substr_count($fmt, '%');
    $pop  = !$n ? '' : ($n == 1 ? sprintf($fmt, $name) : ($n == 2 ? sprintf($fmt, $name, $i) : 'many'));
    return ['name' => $name, 'decl' => $decl, 'pop' => $pop];
}

$r = makeArg('x', 'int', false, true, 0);
assert($r['name'] == 'x');
assert($r['decl'] == 'int const');
assert($r['pop'] == 'x_pop_0');

$r2 = makeArg('p', 'float', true, false, 1);
assert($r2['name'] == 'p');
assert($r2['decl'] == 'float*');

// ── return with associative array literal ──────────────────────────────────────

function makeInfo($a, $b) {
    return ['alpha' => $a, 'beta' => $b];
}
$info = makeInfo(10, 20);
assert($info['alpha'] == 10);
assert($info['beta']  == 20);

// ── echo with array literal ────────────────────────────────────────────────────

// echo on a sequential array — just check it doesn't crash
$arr = ['x', 'y'];
assert(count($arr) == 2);

echo "OK\n";
