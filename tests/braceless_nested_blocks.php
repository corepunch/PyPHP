<?php
// Regression test: braceless nested control structures (body on next line).

// foreach without braces, if body also without braces
$TypeInfos = ['int' => ['type' => 'integer'], 'str' => ['type' => 'string']];

function findType($type) {
    global $TypeInfos;
    foreach ($TypeInfos as $kind => $info)
        if ($type == $kind)
            return $info;
    return [];
}

assert(findType('int') == ['type' => 'integer']);
assert(findType('str') == ['type' => 'string']);
assert(findType('float') == []);

// while without braces (body on next line)
$i = 0;
$sum = 0;
while ($i < 5)
    $sum += $i++;
assert($sum == 10);

// if without braces (body on next line)
$x = 7;
$r = '';
if ($x > 5)
    $r = 'big';
assert($r == 'big');

// Three levels of nesting without braces
function nestedNoBraces($items) {
    $result = [];
    foreach ($items as $k => $v)
        if ($v > 0)
            array_push($result, $k);
    return $result;
}
assert(nestedNoBraces(['a' => 1, 'b' => -1, 'c' => 2]) == ['a', 'c']);

echo "OK\n";
