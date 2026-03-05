<?php
/* This is a block comment — should be stripped. */
$x = 42;

/*
 * Multi-line block comment.
 * None of this should appear in the output.
 */
$y = 10;

// Line comment — already supported
$z = $x + $y;
assert($z == 52);

/* inline block comment */ $msg = "hello";
assert($msg == "hello");
?>
