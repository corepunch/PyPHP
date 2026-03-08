---
layout: default
title: Examples
nav_order: 2
permalink: /examples
---

# Examples

The [`examples/`](https://github.com/corepunch/PyPHP/tree/main/examples)
directory in the repository contains several ready-to-run use cases.
Run them all at once with:

```
make examples
```

| Example | Command | Output |
|---------|---------|--------|
| **C header generation** from an XML model | `python3 -m pyphp examples/c_header/header.php --file=examples/c_header/model.xml` | A `.h` file with `typedef` / `struct` declarations |
| **HTML weather report** fetched from open-meteo.com | `python3 -m pyphp examples/html/report.php` | A styled HTML page with live weather for several cities |
| **Markdown API docs** generated from an XML definition file | `python3 -m pyphp examples/docs/api.php` | A Markdown reference document |
| **CLI option parsing** with `getopt()` and `isset()` | `python3 -m pyphp examples/getopt/greet.php --user=World` | Demonstrates `getopt`, `isset`, and `??` |

---

## Generating a C header from an XML model

This is the canonical use case.  Suppose `model.xml` describes a set of structs:

```xml
<model>
  <struct name="Point">
    <field name="x" type="float"/>
    <field name="y" type="float"/>
  </struct>
  <struct name="Rect">
    <field name="origin" type="Point"/>
    <field name="size"   type="Point"/>
  </struct>
</model>
```

The template `header.php` iterates over the model and emits a C header:

```php
<?php require "model.py"; ?>
<?php
$options = getopt("f:", ["file:"]);
$file = $options['file'] ?? $options['f'] ?? null;
if (!$file) {
    echo "Usage: python3 -m pyphp header.php --file=model.xml\n";
    exit(1);
}
$model = new Model($file);
?>
<?php foreach ($model->structs() as $struct): ?>
typedef struct <?= $struct->name ?> <?= $struct->name ?>, *lp<?= $struct->name ?>;
struct <?= $struct->name ?> {
<?php foreach ($struct->findall("field") as $field): ?>
    <?= $field->type ?> <?= $field->name ?>;
<?php endforeach ?>
};

<?php endforeach ?>
```

The Python model helper (`model.py`) loads and wraps the XML:

```python
import xml.etree.ElementTree as ET
from pyphp import E   # wraps XML elements so $el->attr works in templates

class Model:
    def __init__(self, path):
        self._root = ET.parse(path).getroot()

    def structs(self):
        return [E(s) for s in self._root.findall("struct")]
```

Run it:

```
python3 -m pyphp header.php --file=model.xml
```

Output:

```c
typedef struct Point Point, *lpPoint;
struct Point {
    float x;
    float y;
};

typedef struct Rect Rect, *lpRect;
struct Rect {
    Point origin;
    Point size;
};
```

---

## Parsing CLI options with `getopt()`

Use `getopt()` to accept named command-line options in any script:

```php
<?php
$options = getopt("u:p:", ["user:", "password:", "help"]);

if (isset($options['help']) || empty($options)) {
    echo "Usage: php file.php [OPTIONS]\n";
    echo "Options:\n";
    echo "  -u, --user=NAME      Username (required)\n";
    echo "  -p, --password=PASS  Password (required)\n";
    echo "  --help               Show this help message\n";
    exit(0);
}

$user = $options['user'] ?? $options['u'] ?? null;
$pass = $options['password'] ?? $options['p'] ?? null;

if (!$user || !$pass) {
    echo "Error: Missing required arguments\n\n";
    exit(1);
}

echo "Running with user: $user\n";
?>
```

Run it:

```
python3 -m pyphp file.php --user=alice --password=secret
# Running with user: alice
```

Key points:
- `getopt("u:p:", ["user:", "password:", "help"])` — short options with `:` require a value; long options without `:` are boolean flags
- `isset($options['help'])` — safely returns `false` for missing keys (no exception)
- `$options['user'] ?? $options['u'] ?? null` — null-coalescing falls back safely through missing keys

---

## Generating an HTML report from a live API

The `examples/html/report.php` template fetches JSON from
[open-meteo.com](https://open-meteo.com/) and emits a styled HTML page:

```php
<?php
// cities.json defines lat/lon for each city
$cities = json_decode(file_get_contents("cities.json"), true);
foreach ($cities as $city) {
    $url = "https://api.open-meteo.com/v1/forecast?latitude={$city['lat']}&longitude={$city['lon']}&current_weather=true";
    $weather = json_decode(file_get_contents($url), true);
    $city['temp'] = $weather['current_weather']['temperature'];
    // ...
}
?>
<!DOCTYPE html>
<html>
<body>
<?php foreach ($cities as $city): ?>
<div class="card">
  <h2><?= $city['name'] ?></h2>
  <p><?= $city['temp'] ?> °C</p>
</div>
<?php endforeach ?>
</body>
</html>
```

---

## Generating Markdown API docs from XML

The `examples/docs/api.php` template reads an XML API definition and emits a
Markdown reference page:

```php
<?php
use xml\etree\ElementTree as ET;
$tree = ET::parse("api.xml");
$root = $tree->getroot();
?>
# API Reference

<?php foreach ($root->findall("endpoint") as $ep): ?>
## <?= $ep->get("method") ?> `<?= $ep->get("path") ?>`

<?= $ep->findtext("description") ?>

<?php endforeach ?>
```
