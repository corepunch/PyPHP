<?php $pair = ["Alice", 30]; ?>
<?php list($name, $age) = $pair; ?>
<?php assert($name == "Alice") ?>
<?php assert($age == 30) ?>
<?php $rgb = [255, 128, 0]; ?>
<?php list($r, $g, $b) = $rgb; ?>
<?php assert($r == 255) ?>
<?php assert($g == 128) ?>
<?php assert($b == 0) ?>
