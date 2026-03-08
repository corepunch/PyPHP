<?php
// Regression test: multiline echo-shorthand tags must be evaluated,
// not passed through unchanged as literal text.
//
// assert_renders() is injected by the renderer; it renders a template
// string in a fresh context and asserts the result equals the expected value.
//
// The close-tag sequence is built at runtime to avoid confusing the tokenizer.

$ct = chr(63) . chr(62);  // builds the two-char close-tag sequence

// Multiline echo-shorthand tag with a simple function call.
assert_renders(
    '<?= implode(' . "\n" . "    ', ',\n    ['a', 'b', 'c']\n) " . $ct,
    'a, b, c'
);

// Multiline echo-shorthand tag with nested array_map (mirrors the original bug report).
assert_renders(
    '<?= implode(", ", array_map(' . "\n" . '    fn($x) => strtoupper($x),' . "\n    ['a', 'b', 'c']\n)) " . $ct,
    'A, B, C'
);
?>
