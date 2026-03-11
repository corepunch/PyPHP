<?php
// Test that require/include work with variable-interpolated paths.
// PHP supports both "$var" and "{$var}" forms inside double-quoted strings.

// Form 1: $var directly in path
$helper = "tests/require_interp_helper";
require "$helper.php";
assert($interp_loaded === true);
assert($interp_value === "loaded via interpolated require");

// Form 2: {$var} curly-brace form
$interp_loaded = false;
$helper2 = "require_interp_helper";
require "tests/{$helper2}.php";
assert($interp_loaded === true);
