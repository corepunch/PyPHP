<?php
// ── ! (logical NOT) ─────────────────────────────────────────────────────────

$t = true;
$f = false;

// Basic NOT
assert(!$f);
assert(!false);

// Double negation
assert(!(!$t));

// NOT applied to a function call
$empty = [];
assert(!in_array("x", $empty));

// NOT in if condition
if (!$f) {
    $r = "ok";
} else {
    $r = "fail";
}
assert($r == "ok");

// ── != (loose inequality) — must NOT be mangled by ! -> not conversion ──────

assert(1 != 2);
assert("a" != "b");
assert(0 != 1);

// ── === (strict equality) ────────────────────────────────────────────────────

assert(1 === 1);
assert("hello" === "hello");
assert(true === true);
assert(false === false);

// Different types are not strictly equal (Python == also returns False here)
assert(!(1 === "1"));

// ── !== (strict inequality) ──────────────────────────────────────────────────

assert(1 !== 2);
assert("a" !== "b");
assert(1 !== "1");
assert(!(1 !== 1));
assert(!("x" !== "x"));

// ── == stays unmodified (must not become === after strict-eq pass) ───────────

assert(1 == 1);
assert("a" == "a");
assert(!(1 == 2));

// ── && (logical AND) ─────────────────────────────────────────────────────────

assert($t && $t);
assert(!($t && $f));
assert(!($f && $t));
assert(!($f && $f));

// && in an if block
if ($t && !$f) {
    $and_r = "both";
} else {
    $and_r = "not both";
}
assert($and_r == "both");

// ── || (logical OR) ──────────────────────────────────────────────────────────

assert($t || $t);
assert($t || $f);
assert($f || $t);
assert(!($f || $f));

// || in an if block
if ($f || $t) {
    $or_r = "either";
} else {
    $or_r = "neither";
}
assert($or_r == "either");

// ── operator combinations ─────────────────────────────────────────────────────

$x = 5;
$y = 10;

// NOT + strict equality
assert(!($x === $y));
assert(!($x !== $x));

// AND + OR together
assert(($x < $y) && ($y > 0));
assert(($x > $y) || ($y > 0));

// Compound: AND of two not-equal comparisons
assert(($x !== $y) && ($y !== 0));

// NOT + AND + OR chain
assert(!($x === $y) && ($x !== 0));
assert(!($x > $y) || ($y > $x));

// === combined in assignment condition
if ($x === 5) {
    $label = "five";
} else {
    $label = "other";
}
assert($label == "five");

// !== combined in assignment condition
if ($x !== 99) {
    $label2 = "not 99";
} else {
    $label2 = "ninety-nine";
}
assert($label2 == "not 99");

// ── operators inside strings must NOT be modified ─────────────────────────────

$s1 = "use && for AND";
assert($s1 == "use && for AND");

$s2 = "strict === check";
assert($s2 == "strict === check");

$s3 = "not equal !== same";
assert($s3 == "not equal !== same");

$s4 = "a || b";
assert($s4 == "a || b");

// ── foreach with -> in iterable (regression for _php_expr bug) ───────────────

// Single-level -> in foreach iterable
$xml = simplexml_load_string('<items><item>alpha</item><item>beta</item></items>');
$names = [];
foreach ($xml->item as $it) {
    array_push($names, strval($it));
}
assert($names == ["alpha", "beta"]);

// Chained -> -> in foreach iterable
$xml2 = simplexml_load_string('<root><list><item>x</item><item>y</item></list></root>');
$nested = [];
foreach ($xml2->list->item as $it) {
    array_push($nested, strval($it));
}
assert($nested == ["x", "y"]);

// Key-value foreach with -> in iterable
$pairs = simplexml_load_string('<catalog><book id="1">A</book><book id="2">B</book></catalog>');
$ids = [];
foreach ($pairs->book as $k => $book) {
    array_push($ids, $book['id']);
}
assert($ids == ["1", "2"]);

// foreach -> combined with ! in body
$xml3 = simplexml_load_string('<items><item ok="yes">p</item><item ok="no">q</item></items>');
$ok_items = [];
foreach ($xml3->item as $item) {
    if (!($item['ok'] == "no")) {
        array_push($ok_items, strval($item));
    }
}
assert($ok_items == ["p"]);

// foreach -> combined with && and !== in body
$xml4 = simplexml_load_string('<data><row a="1" b="ok"/><row a="2" b="skip"/><row a="3" b="ok"/></data>');
$filtered = [];
foreach ($xml4->row as $row) {
    if ($row['b'] !== "skip" && $row['a'] !== "0") {
        array_push($filtered, $row['a']);
    }
}
assert($filtered == ["1", "3"]);
?>
