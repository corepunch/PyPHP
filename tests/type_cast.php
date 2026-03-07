<?php $x = "42"; $y = "3.14"; ?>
<?php assert((int)$x == 42) ?>
<?php assert((float)$y == 3.14) ?>
<?php assert((string)100 == "100") ?>
<?php $flag = 1; ?>
<?php assert((bool)$flag == true) ?>
<?php
// cast applied to subscript: (string)$arr['key'] -> str(__arr['key'])
$data = ['name' => 'Alice', 'score' => 99];
assert((string)$data['name'] == 'Alice');
assert((int)$data['score'] == 99);
?>
<?php
// cast applied to property access after -> conversion: (string)$obj->prop
$xml = simplexml_load_string('<root name="Test"/>');
assert((string)$xml['name'] == 'Test');
?>
