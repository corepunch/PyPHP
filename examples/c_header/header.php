<?php require "examples/c_header/model.php"; ?>
<?php
$options = getopt("f:", ["file:"]);
$file = $options['file'] ?? $options['f'] ?? null;
if (!$file) {
    echo "Usage: python3 -m pyphp examples/c_header/header.php --file=model.xml\n";
    exit(1);
}
$model = new Model($file);
?>
<?php $structs = $model->structs(); ?>
#pragma once
#include <stdint.h>

<?php foreach ($structs as $struct): ?>
typedef struct <?= $struct->name ?> <?= $struct->name ?>, *lp<?= $struct->name ?>;
struct <?= $struct->name ?> {
<?php $fields = $struct->findall("field"); ?>
<?php foreach ($fields as $field): ?>
    <?= $field->type ?> <?= $field->name ?>;
<?php endforeach ?>
};

<?php endforeach ?>
