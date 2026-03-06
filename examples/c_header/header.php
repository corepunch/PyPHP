<?php require "examples/c_header/model.php"; ?>
<?php $model = new Model($argv[1]); ?>
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
