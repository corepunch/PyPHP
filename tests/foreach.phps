<?php $items = ["apple", "banana", "cherry"]; ?>
<?php $out = []; ?>
<?php foreach ($items as $item): ?>
<?php array_push($out, $item); ?>
<?php endforeach ?>
<?php assert($out == ["apple", "banana", "cherry"]) ?>
