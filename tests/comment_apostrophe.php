<?php
// Regression: an apostrophe inside a // comment must NOT cause _sub_outside_strings()
// to treat subsequent code as a string literal.
//
// Before this fix, a ' in a // comment started a fake string span that swallowed
// code up to the next matching quote, silently breaking substitution steps.

// Here's a comment with an apostrophe: it's harmless.
$x = 42;
assert($x == 42);

// Another comment: let's make sure $var substitution works.
$msg = "hello";
assert($msg == "hello");

// The // to # conversion must still work in comments AFTER the apostrophe.
$y = $x + 1;
assert($y == 43);

// Verify that string literals containing apostrophes are still protected.
$s = "it's a string";
assert($s == "it's a string");

// Verify that // inside a string is not consumed as a comment.
$url = "https://example.com";
assert($url == "https://example.com");

// Regression: class using static property in foreach after a comment with apostrophe.
class CfgApostrophe {
    public static $Items = ["alpha", "beta"];
}

class ProcessorApostrophe {
    function run() {
        // It's time to iterate.
        $result = [];
        foreach (CfgApostrophe::$Items as $item) {
            $result[] = $item;
        }
        return $result;
    }
}

$p = new ProcessorApostrophe();
$r = $p->run();
assert(count($r) == 2);
assert($r[0] == "alpha");
assert($r[1] == "beta");
