<?php
use xml\etree\ElementTree as ET;
use pyphp\renderer as renderer;

$xml_path = "examples/docs/api.xml";
$root     = renderer::E(ET::parse($xml_path)->getroot());
$lib      = $root->lib;
$version  = $root->version;

$funcs = [];
foreach ($root->find("functions")->findall("function") as $fn) {
    $params = [];
    foreach ($fn->findall("param") as $p) {
        array_push($params, [$p->name, $p->type, $p->description]);
    }
    array_push($funcs, [
        $fn->name,
        $fn->signature,
        $fn->description,
        $params,
        $fn->returns,
        $fn->example,
    ]);
}

$classes = [];
foreach ($root->find("classes")->findall("class") as $cls) {
    $attrs = [];
    foreach ($cls->findall("attr") as $a) {
        array_push($attrs, [$a->name, $a->type, $a->description]);
    }
    array_push($classes, [
        $cls->name,
        $cls->description,
        $attrs,
    ]);
}
?>
# <?= strtoupper($lib) ?> API Reference

**Version:** <?= $version ?>  |  **Package:** `<?= $lib ?>`

---

## Functions

<?php foreach ($funcs as $fn): ?>
### `<?= $fn[1] ?>`

<?= $fn[2] ?>

**Parameters**

| Name | Type | Description |
|------|------|-------------|
<?php foreach ($fn[3] as $p): ?>| `<?= $p[0] ?>` | `<?= $p[1] ?>` | <?= $p[2] ?> |
<?php endforeach ?>
**Returns:** `<?= $fn[4] ?>`

**Example**

```python
<?= $fn[5] ?>
```

---

<?php endforeach ?>
## Classes

<?php foreach ($classes as $cls): ?>
### `<?= $cls[0] ?>`

<?= $cls[1] ?>

| Attribute | Type | Description |
|-----------|------|-------------|
<?php foreach ($cls[2] as $a): ?>| `<?= $a[0] ?>` | `<?= $a[1] ?>` | <?= $a[2] ?> |
<?php endforeach ?>
---

<?php endforeach ?>
