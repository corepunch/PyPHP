<?php
// Tests for PHP heredoc and nowdoc strings

// Basic heredoc with variable interpolation
$name = "World";
$text = <<<EOT
Hello, $name!
EOT;
assert($text == "Hello, World!\n");

// Nowdoc (no interpolation)
$raw = <<<'NOWDOC'
No $interpolation here!
NOWDOC;
assert($raw == 'No $interpolation here!\n');

// Multi-line heredoc
$multiline = <<<HTML
Line 1
Line 2
Line 3
HTML;
assert($multiline == "Line 1\nLine 2\nLine 3\n");

// Heredoc with array interpolation
$arr = ["key" => "value"];
$msg = <<<EOT
Key: {$arr['key']}
EOT;
assert($msg == "Key: value\n");

// Heredoc assigned in expression
$greeting = "Dear " . <<<EOT
$name,
EOT;
assert($greeting == "Dear " . "World,\n");

// Empty heredoc
$empty = <<<EOT
EOT;
assert($empty == "");

// Nowdoc preserves backslashes - test with forward slashes to avoid Python escape issues
$path = <<<'EOT'
/usr/local/bin/php
EOT;
assert($path == "/usr/local/bin/php\n");

// Heredoc with multiple variables
$first = "John";
$last = "Doe";
$full = <<<EOT
$first $last
EOT;
assert($full == "John Doe\n");
?>
