<?php
// ── str_ireplace ─────────────────────────────────────────────────────────────
assert(str_ireplace('WORLD', 'PHP', 'Hello World') == 'Hello PHP');
assert(str_ireplace('hello', 'Hi', 'HELLO world') == 'Hi world');
assert(str_ireplace(['FOO', 'BAR'], ['baz', 'qux'], 'foo BAR') == 'baz qux');

// ── stripos ──────────────────────────────────────────────────────────────────
assert(stripos('Hello World', 'world') === 6);
assert(stripos('Hello World', 'HELLO') === 0);
// returns -1 when not found, consistent with strpos (Python str-find behaviour)
assert(stripos('Hello World', 'xyz') === -1);

// ── strstr ───────────────────────────────────────────────────────────────────
assert(strstr('user@example.com', '@') == '@example.com');
assert(strstr('user@example.com', '@', true) == 'user');
assert(strstr('no-at-sign', '@') === false);

// ── stristr ──────────────────────────────────────────────────────────────────
assert(stristr('Hello World', 'WORLD') == 'World');
assert(stristr('Hello World', 'WORLD', true) == 'Hello ');
assert(stristr('no match', 'xyz') === false);

// ── strrev ───────────────────────────────────────────────────────────────────
assert(strrev('Hello') == 'olleH');
assert(strrev('abcde') == 'edcba');
assert(strrev('') == '');

// ── addslashes / stripslashes ─────────────────────────────────────────────────
$plain = "say hi";
$slashed = addslashes($plain);
$unslashed = stripslashes($slashed);
assert($unslashed == $plain);
// addslashes escapes single quotes
$withquote = "it's";
$escaped = addslashes($withquote);
assert(str_contains($escaped, "it"));
$back = stripslashes($escaped);
assert($back == $withquote);

// ── levenshtein ──────────────────────────────────────────────────────────────
assert(levenshtein('kitten', 'sitting') == 3);
assert(levenshtein('', 'abc') == 3);
assert(levenshtein('abc', '') == 3);
assert(levenshtein('abc', 'abc') == 0);
assert(levenshtein('sunday', 'saturday') == 3);

// ── soundex ──────────────────────────────────────────────────────────────────
assert(soundex('Robert') == 'R163');
assert(soundex('Rupert') == 'R163');
assert(soundex('Thompson') == 'T512');

// ── array_fill_keys ──────────────────────────────────────────────────────────
$filled = array_fill_keys(['a', 'b', 'c'], 0);
assert($filled['a'] == 0);
assert($filled['b'] == 0);
assert($filled['c'] == 0);

$filled2 = array_fill_keys([1, 2, 3], 'x');
assert($filled2[1] == 'x');
assert($filled2[2] == 'x');

// ── array_diff ───────────────────────────────────────────────────────────────
$d = array_diff([1, 2, 3, 4, 5], [2, 4]);
assert(in_array(1, $d));
assert(in_array(3, $d));
assert(in_array(5, $d));
assert(!in_array(2, $d));
assert(!in_array(4, $d));

// ── array_intersect ──────────────────────────────────────────────────────────
$i = array_intersect([1, 2, 3, 4], [2, 4, 6]);
assert(in_array(2, $i));
assert(in_array(4, $i));
assert(!in_array(1, $i));
assert(!in_array(6, $i));

// ── array_diff_key ───────────────────────────────────────────────────────────
$dk = array_diff_key(['a' => 1, 'b' => 2, 'c' => 3], ['a' => 0, 'c' => 0]);
assert(array_key_exists('b', $dk));
assert(!array_key_exists('a', $dk));
assert(!array_key_exists('c', $dk));

// ── array_intersect_key ───────────────────────────────────────────────────────
$ik = array_intersect_key(['a' => 1, 'b' => 2, 'c' => 3], ['a' => 0, 'c' => 0]);
assert(array_key_exists('a', $ik));
assert(array_key_exists('c', $ik));
assert(!array_key_exists('b', $ik));

// ── array_walk ───────────────────────────────────────────────────────────────
function noop_callback($val, $key) {
    return $val;
}
$arr = ['a' => 1, 'b' => 2, 'c' => 3];
assert(array_walk($arr, 'noop_callback') === true);

// ── get_class ─────────────────────────────────────────────────────────────────
class TestGetClass {
    public $name = 'test';
}
$obj = new TestGetClass();
assert(get_class($obj) == 'TestGetClass');
assert(get_class(null) === false);

// ── get_parent_class ──────────────────────────────────────────────────────────
class TestParent {}
class TestChild extends TestParent {}
$child = new TestChild();
assert(get_parent_class($child) == 'TestParent');
$parent = new TestParent();
assert(get_parent_class($parent) === false);

// ── method_exists ─────────────────────────────────────────────────────────────
class TestMethods {
    public function hello() {}
    private function secret() {}
}
$tm = new TestMethods();
assert(method_exists($tm, 'hello') == true);
assert(method_exists($tm, 'secret') == true);
assert(method_exists($tm, 'nonexistent') == false);

// ── property_exists ───────────────────────────────────────────────────────────
class TestProps {
    public $pub = 1;
    protected $prot = 2;
}
$tp = new TestProps();
assert(property_exists($tp, 'pub') == true);
assert(property_exists($tp, 'doesnt_exist') == false);

// ── get_object_vars ───────────────────────────────────────────────────────────
class TestObjVars {
    public $x = 10;
    public $y = 20;
}
$ov = new TestObjVars();
$vars = get_object_vars($ov);
assert($vars['x'] == 10);
assert($vars['y'] == 20);

// ── gettype ───────────────────────────────────────────────────────────────────
assert(gettype(null) == 'NULL');
assert(gettype(true) == 'boolean');
assert(gettype(42) == 'integer');
assert(gettype(3.14) == 'double');
assert(gettype('hello') == 'string');
assert(gettype([1, 2, 3]) == 'array');

// ── version_compare ───────────────────────────────────────────────────────────
assert(version_compare('1.2.3', '1.2.4') < 0);
assert(version_compare('2.0.0', '1.9.9') > 0);
assert(version_compare('1.0.0', '1.0.0') == 0);
assert(version_compare('1.2.3', '1.2.4', '<') == true);
assert(version_compare('2.0.0', '1.9.9', '>') == true);
assert(version_compare('1.0.0', '1.0.0', '==') == true);
assert(version_compare('1.0.0', '1.0.0', '!=') == false);
assert(version_compare('1.2.3', '1.2.4', '>=') == false);
assert(version_compare('1.2.3', '1.2.3', '>=') == true);

// ── PHP_FLOAT_* constants ─────────────────────────────────────────────────────
assert(PHP_FLOAT_MAX > 1.0e308);
assert(PHP_FLOAT_MIN > 0);
assert(PHP_FLOAT_EPSILON > 0);
assert(PHP_FLOAT_EPSILON < 0.001);

// ── PATHINFO_* constants ──────────────────────────────────────────────────────
assert(pathinfo('/a/b/c.txt', PATHINFO_EXTENSION) == 'txt');
assert(pathinfo('/a/b/c.txt', PATHINFO_FILENAME) == 'c');
assert(pathinfo('/a/b/c.txt', PATHINFO_DIRNAME) == '/a/b');
assert(pathinfo('/a/b/c.txt', PATHINFO_BASENAME) == 'c.txt');

// ── str_getcsv ────────────────────────────────────────────────────────────────
$csv = str_getcsv('one,two,three');
assert(count($csv) == 3);
assert($csv[0] == 'one');
assert($csv[1] == 'two');
assert($csv[2] == 'three');

$csv2 = str_getcsv('"hello world",foo,bar');
assert($csv2[0] == 'hello world');
assert($csv2[1] == 'foo');
