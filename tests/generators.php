<?php
// ── Basic yield / generator function ──────────────────────────────────────
function counter($start, $end) {
    $i = $start;
    while ($i <= $end) {
        yield $i;
        $i += 1;
    }
}

// foreach over a generator
$result = [];
foreach (counter(1, 5) as $n) {
    array_push($result, $n);
}
assert(implode(",", $result) == "1,2,3,4,5");

// ── Key-value generator (yield $key => $value) ─────────────────────────────
function indexedWords() {
    yield "a" => "apple";
    yield "b" => "banana";
    yield "c" => "cherry";
}

$kv = [];
foreach (indexedWords() as $k => $v) {
    $item = $k . "=" . $v;
    array_push($kv, $item);
}
assert(implode(",", $kv) == "a=apple,b=banana,c=cherry");

// ── array_ functions transparently accept generators ───────────────────────
function squares($n) {
    $i = 1;
    while ($i <= $n) {
        yield $i * $i;
        $i += 1;
    }
}

// implode with generator
assert(implode(",", squares(4)) == "1,4,9,16");

// array_sum with generator
assert(array_sum(squares(4)) == 30);

// count / in_array / array_map with generator
$arr = [];
foreach (squares(4) as $v) {
    array_push($arr, $v);
}
assert(count($arr) == 4);
assert(in_array(9, $arr));
assert(implode(",", array_map(fn($v) => $v + 1, squares(3))) == "2,5,10");

// array_filter with generator
assert(implode(",", array_filter(squares(5), fn($v) => $v > 5)) == "9,16,25");

// array_reverse with generator
assert(implode(",", array_reverse(squares(3))) == "9,4,1");

// array_unique with generator
function repeats() {
    yield 1;
    yield 2;
    yield 2;
    yield 3;
}
assert(implode(",", array_unique(repeats())) == "1,2,3");

// array_keys / array_values with key-value generator
function pairs() {
    yield "x" => 10;
    yield "y" => 20;
    yield "z" => 30;
}
assert(implode(",", array_keys(pairs())) == "x,y,z");
assert(implode(",", array_values(pairs())) == "10,20,30");

// array_merge with generators
assert(implode(",", array_merge(squares(2), squares(2))) == "1,4,1,4");

// array_slice with generator
assert(implode(",", array_slice(squares(5), 1, 3)) == "4,9,16");

// array_search with generator
assert(array_search(9, squares(5)) === 2);

// array_flip with generator
$flipped = array_flip(pairs());
assert($flipped[10] == "x");
assert($flipped[20] == "y");

// array_combine with generators
function letters() {
    yield "a";
    yield "b";
    yield "c";
}
function nums() {
    yield 1;
    yield 2;
    yield 3;
}
$combined = array_combine(letters(), nums());
assert($combined["a"] == 1);
assert($combined["c"] == 3);

// ── Generator used in a nested foreach ────────────────────────────────────
function range_gen($start, $end) {
    $i = $start;
    while ($i <= $end) {
        yield $i;
        $i += 1;
    }
}
$matrix = [];
foreach (range_gen(1, 2) as $row) {
    foreach (range_gen(1, 3) as $col) {
        array_push($matrix, $row * 10 + $col);
    }
}
assert(implode(",", $matrix) == "11,12,13,21,22,23");

// ── Empty generator edge case ─────────────────────────────────────────────
function empty_gen() {
    if (false) {
        yield 0;
    }
}
assert(count(array_values(empty_gen())) == 0);
assert(array_sum(empty_gen()) == 0);

// ── Generator passed to count() ────────────────────────────────────────────
assert(count(array_values(squares(3))) == 3);

// ── array_chunk with generator ─────────────────────────────────────────────
$chunks = array_chunk(squares(6), 2);
assert(count($chunks) == 3);
assert(implode(",", $chunks[0]) == "1,4");
assert(implode(",", $chunks[2]) == "25,36");

// ── is_iterable() and is_array() with generators ───────────────────────────
assert(is_iterable(squares(2)));
assert(!is_array(squares(2)));
assert(is_iterable([]));
assert(is_array([]));

// ── array_key_exists() with key-value generator ────────────────────────────
assert(array_key_exists("x", pairs()));
assert(array_key_exists("z", pairs()));
assert(!array_key_exists("w", pairs()));

// ── rsort() on a generator materialised to a list ─────────────────────────
$sorted = array_values(squares(4));
rsort($sorted);
assert(implode(",", $sorted) == "16,9,4,1");

// ── Generator expression: array_map chained with array_filter ─────────────
$result2 = array_filter(array_map(fn($v) => $v * 2, squares(5)), fn($v) => $v > 10);
assert(implode(",", $result2) == "18,32,50");
?>
