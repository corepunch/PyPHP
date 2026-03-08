<?php
// Regression test: single-line foreach without braces must execute its body,
// not fail with a syntax error.

// Key-value foreach with echo body (mirrors the original bug report).
$parsers = ['translation' => 'char*', 'rotation' => 'float', 'scale' => 'float'];
$decls = [];
foreach ($parsers as $field => $type) array_push($decls, "$type $field;");
assert($decls == ['char* translation;', 'float rotation;', 'float scale;']);

// Value-only foreach with echo body.
$items = ['a', 'b', 'c'];
$out = '';
foreach ($items as $v) $out .= $v;
assert($out == 'abc');

// Single-line foreach with echo — verify the body actually executes.
$seen = [];
foreach ($parsers as $field => $type) array_push($seen, "$type $field");
assert($seen == ['char* translation', 'float rotation', 'float scale']);
?>
