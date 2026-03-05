<?php
// ── foreach: all 3 PHP syntaxes ────────────────────────────────────────────

$items = ["apple", "banana", "cherry"];
$pairs = array_combine(["a", "b", "c"], [1, 2, 3]);

// Syntax 1 — brace style { } (single PHP tag, single-value)
$out1 = [];
foreach ($items as $item) {
    array_push($out1, $item);
}
assert($out1 == ["apple", "banana", "cherry"]);

// Syntax 1 — brace style { } (single PHP tag, key => value)
$keys1 = [];
foreach ($pairs as $k => $v) {
    array_push($keys1, $k);
}
assert($keys1 == ["a", "b", "c"]);

// Syntax 2 — colon + endforeach (single PHP tag, single-value)
$out2 = [];
foreach ($items as $item):
    array_push($out2, $item);
endforeach;
assert($out2 == ["apple", "banana", "cherry"]);

// Syntax 2 — colon + endforeach (single PHP tag, key => value)
$vals2 = [];
foreach ($pairs as $k => $v):
    array_push($vals2, $v);
endforeach;
assert($vals2 == [1, 2, 3]);

// Syntax 3 — no colon, body on next line, closed by endforeach
$out3 = [];
foreach ($items as $item)
    array_push($out3, $item);
endforeach;
assert($out3 == ["apple", "banana", "cherry"]);

// Syntax 3 — no colon, key => value, closed by endforeach
$keys3 = [];
foreach ($pairs as $k => $v)
    array_push($keys3, $k);
endforeach;
assert($keys3 == ["a", "b", "c"]);

// ── foreach: function body with brace style (from the issue example) ──────

function printContents($list) {
    $result = [];
    foreach ($list as $name => $type) {
        array_push($result, $name);
    }
    return $result;
}
assert(printContents($pairs) == ["a", "b", "c"]);

// ── if/else: brace style { } ────────────────────────────────────────────────

$x = 7;

// Brace style
if ($x > 5) {
    $r1 = "big";
} else {
    $r1 = "small";
}
assert($r1 == "big");

// Brace style with elseif
if ($x > 10) {
    $r2 = "very big";
} elseif ($x > 5) {
    $r2 = "big";
} else {
    $r2 = "small";
}
assert($r2 == "big");

// Colon style (already covered in if.php — included here for completeness)
if ($x > 5):
    $r3 = "big";
else:
    $r3 = "small";
endif;
assert($r3 == "big");

// ── while: brace style { } ──────────────────────────────────────────────────

$n = 4;
$total = 0;
while ($n > 0) {
    $total += $n;
    $n -= 1;
}
assert($total == 10);
?>

<?php $tItems = ["x", "y", "z"]; ?>
<?php $tOut = []; ?>

<?php foreach ($tItems as $tItem) { ?>
<?php array_push($tOut, $tItem); ?>
<?php } ?>
<?php assert($tOut == ["x", "y", "z"]) ?>

<?php $tPairs = array_combine(["p", "q"], [10, 20]); ?>
<?php $tKeys = []; ?>
<?php foreach ($tPairs as $k => $v) { ?>
<?php array_push($tKeys, $k); ?>
<?php } ?>
<?php assert($tKeys == ["p", "q"]) ?>

<?php $flag = true; ?>
<?php if ($flag) { ?>
<?php $tResult = "yes"; ?>
<?php } else { ?>
<?php $tResult = "no"; ?>
<?php } ?>
<?php assert($tResult == "yes") ?>
