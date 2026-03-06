<?php
$lib     = "pyphp";
$version = "1.0";
$funcs = [
    [
        "render",
        "render(source, ctx)",
        "Render a PHP template string and return the output as a string.",
        [
            ["source", "str",     "PHP template source code"],
            ["ctx",    "Context", "Holds template variables and optional output filters"],
        ],
        "str",
        'render(source, Context(vars={"name": "world"}))',
    ],
    [
        "render_file",
        "render_file(path, ctx)",
        "Load a .php template from disk and render it.",
        [
            ["path", "str | Path", "Path to the .php template file"],
            ["ctx",  "Context",    "Holds template variables and optional output filters"],
        ],
        "str",
        'render_file("page.php", Context(vars={"title": "Hello"}))',
    ],
    [
        "php_to_python",
        "php_to_python(code)",
        "Translate a snippet of PHP code to equivalent Python.",
        [
            ["code", "str", "Raw PHP code string (without template tags)"],
        ],
        "str",
        "php_to_python('strtolower(implode(\", \", [\"a\", \"b\"]))')",
    ],
];
$classes = [
    [
        "Context",
        "Holds the variables and filters passed to a template.",
        [
            ["vars",    "dict[str, Any]",      "Template variables, accessed as PHP variables inside templates"],
            ["filters", "dict[str, Callable]", "Named post-processing functions for output expressions"],
        ],
    ],
    [
        "E",
        "Wraps an xml.etree.ElementTree.Element for dot-access of attributes in templates.",
        [
            ["(any XML attribute)", "str", "Read directly as a property: el->name, el->type, etc."],
        ],
    ],
];
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
