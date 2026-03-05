<?php
// foreach without colon: body on next line (single-value iteration)
$items = ["apple", "banana", "cherry"];
$out = [];
foreach ($items as $item)
    array_push($out, $item);
endforeach
assert($out == ["apple", "banana", "cherry"])

// foreach ($k => $v) without colon: body on next line
$pairs = array_combine(["a", "b", "c"], [1, 2, 3]);
$keys = [];
foreach ($pairs as $k => $v)
    array_push($keys, $k);
endforeach
assert($keys == ["a", "b", "c"])

// echo(expr) — parenthesised form should work like echo expr
$word = "hello";
$got = [];
foreach (["world"] as $w) {
    $label = $word . " " . $w;
    array_push($got, $label);
}
assert($got == ["hello world"])

// foreach without colon inside a function body
function sumList($nums) {
    $total = 0;
    foreach ($nums as $n)
        $total = $total + $n;
    endforeach
    return $total;
}
assert(sumList([1, 2, 3, 4]) == 10)
?>
