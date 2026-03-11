<?php
// ── yield with PHP string-concat key  (Issue: concat operands were wrongly
//    swallowed into _cat() along with the => $value separator)  ─────────────

// Basic: concat key using . operator
function dotKeys($items) {
    foreach ($items as $struct) {
        foreach ($struct['methods'] as $method) {
            yield $struct['name'] . "." . $method['name'] => $method;
        }
    }
}

$data = [
    ['name' => 'Foo', 'methods' => [['name' => 'bar'], ['name' => 'baz']]],
    ['name' => 'Qux', 'methods' => [['name' => 'quux']]],
];

$keys = [];
foreach (dotKeys($data) as $k => $v) {
    array_push($keys, $k);
}
assert(implode(",", $keys) == "Foo.bar,Foo.baz,Qux.quux");

// Three-part concat key
function tripleKey($items) {
    foreach ($items as $ns) {
        foreach ($ns['structs'] as $struct) {
            foreach ($struct['methods'] as $method) {
                yield $ns['name'] . "::" . $struct['name'] . "." . $method['name'] => $method;
            }
        }
    }
}

$ns_data = [
    ['name' => 'NS', 'structs' => [
        ['name' => 'Cls', 'methods' => [['name' => 'f']]],
    ]],
];
$triple_keys = [];
foreach (tripleKey($ns_data) as $k => $v) {
    array_push($triple_keys, $k);
}
assert(implode(",", $triple_keys) == "NS::Cls.f");

// Concat in both key and value
function concatBoth($pairs) {
    foreach ($pairs as $p) {
        yield $p['a'] . "-" . $p['b'] => $p['c'] . "+" . $p['d'];
    }
}

$both_result = [];
foreach (concatBoth([['a' => 'x', 'b' => 'y', 'c' => '1', 'd' => '2']]) as $k => $v) {
    array_push($both_result, $k . "=" . $v);
}
assert(implode(",", $both_result) == "x-y=1+2");

// ── yield with null-coalesce (??) inside a braced interpolated string key ──
// (Issue: ?? inside {$var} interpolation in a double-quoted string was left
//  as raw ?? in the Python f-string, causing a SyntaxError)

function exportKeys($items) {
    foreach ($items as $struct) {
        foreach ($struct['methods'] as $method) {
            yield "{$struct['export'] ?? $struct['name']}_{$method['name']}" => $method;
        }
    }
}

$items = [
    // export is set: use it
    ['name' => 'Alpha', 'export' => 'A', 'methods' => [['name' => 'run']]],
    // export is null: fall back to name
    ['name' => 'Beta',  'export' => null, 'methods' => [['name' => 'stop']]],
];

$export_keys = [];
foreach (exportKeys($items) as $k => $v) {
    array_push($export_keys, $k);
}
assert(implode(",", $export_keys) == "A_run,Beta_stop");

// ?? inside a plain (non-yield) string interpolation also still works
$name = null;
$label = "{$name ?? 'unknown'}";
assert($label == "unknown");

$name2 = "world";
$label2 = "{$name2 ?? 'unknown'}";
assert($label2 == "world");

$val = "actual";
$s = "{$val ?? 'default'}";
assert($s == "actual");
?>
