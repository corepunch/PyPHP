# PyPHP

A lightweight **file parser and code generator** that understands PHP-style template tags (`<?php ?>` and `<?= ?>`), powered by Python under the hood.

The idea is simple: write templates that look like PHP, run them with Python, and generate any text-based output — C headers, HTML pages, SQL scripts, configuration files, and more.

---

## Why PyPHP?

PHP was originally a *preprocessor* — it sat in front of plain text and let you sprinkle logic into it.  PyPHP brings that same workflow to Python:

- You write a `.php` template that mixes static text with `<?php ?>` logic tags.
- You run `python pyphp.py template.php` (or call `render()` from Python).
- You get the generated text on stdout (or as a string).

This is especially useful for **generating source code** from structured data.  For example, you can read an XML schema and emit a C header file, or walk a JSON config and produce an HTML report — all from a single readable template.

---

## Quick Start

```
python3 -m pyphp template.php [key=value ...]
```

Variables passed on the command line are available as `$key` inside the template.

```php
<?= "Hello, World!" ?>
```

```
$ python3 -m pyphp hello.php
Hello, World!
```

---

## Runnable Examples

The [`examples/`](examples/) directory contains three ready-to-run use cases.
Run them all at once with:

```
make examples
```

Or individually:

| Example | Command | Output |
|---------|---------|--------|
| **C header generation** from an XML model | `python3 -m pyphp examples/c_header/header.php examples/c_header/model.xml` | A `.h` file with `typedef` / `struct` declarations |
| **HTML report** with KPI cards and a data table | `python3 -m pyphp examples/html/report.php` | A styled HTML page |
| **Markdown API docs** generated from inline data | `python3 -m pyphp examples/docs/api.php` | A Markdown reference document |

---

## Examples

### Generating a C header from an XML model

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

You can write the model helper in **Python** or in **PHP** — both work the same way.

#### Option 1 — Python model (`model.py`)

```python
import xml.etree.ElementTree as ET
from pyphp import E   # wraps XML elements so $el->attr works in templates

class Model:
    def __init__(self, path):
        self._root = ET.parse(path).getroot()

    def structs(self):
        # E() enables dot-attribute access: $struct->name instead of struct.get("name")
        return [E(s) for s in self._root.findall("struct")]
```

#### Option 2 — PHP model (`model.php`)

```php
<?php
// PyPHP maps `use` to Python imports, so Python's xml.etree.ElementTree
// is available here transparently — no PHP XML extension required.
use xml\etree\ElementTree as ET;
use pyphp\renderer as renderer;

class Model {
    public function __construct($path) {
        $this->_root = ET::parse($path)->getroot();
    }

    public function structs() {
        $elements = $this->_root->findall("struct");
        $result = [];
        foreach ($elements as $el) {
            array_push($result, renderer::E($el));
        }
        return $result;
    }
}
?>
```

The template `header.php`.  Inside the template, `$argv[1]` is the first
command-line argument — `model.xml` in the `run` command below.  Swap
`require "model.py"` for `require "model.php"` depending on which helper
you chose:

```php
<?php require "model.py"; ?>  <?php /* or: require "model.php"; */ ?>
<?php $model = new Model($argv[1]); ?>
<?php foreach ($model->structs() as $struct): ?>
typedef struct <?= $struct->name ?> <?= $struct->name ?>, *lp<?= $struct->name ?>;
struct <?= $struct->name ?> {
<?php foreach ($struct->findall("field") as $field): ?>
    <?= $field->type ?> <?= $field->name ?>;
<?php endforeach ?>
};

<?php endforeach ?>
```

Run it:

```
python pyphp.py header.php model.xml
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

## Using PyPHP as a Library

```python
from pyphp import render, render_file, Context

ctx = Context(vars={"title": "Hello", "items": ["a", "b", "c"]})
output = render_file("template.php", ctx)
print(output)
```

You can also register **filters** that post-process expression output:

```python
ctx = Context(
    vars={"name": "world"},
    filters={"upper": str.upper},
)
# In template: <?= $name | upper ?>  →  WORLD
```

---

## Supported PHP Features

| Feature | Syntax | Notes |
|---|---|---|
| Echo shorthand | `<?= $expr ?>` | Outputs the expression |
| Code block | `<?php ... ?>` | Executes arbitrary logic |
| Variables | `$name` | Mapped to Python variables |
| Property / method access | `$obj->prop`, `$obj->method()` | Mapped to `.` |
| Object creation | `new ClassName(args)` | Mapped to `ClassName(args)` |
| Boolean / null literals | `true`, `false`, `null` | Mapped to `True`, `False`, `None` |
| `foreach` (value) | `foreach ($arr as $v):` | Works on lists and any iterable |
| `foreach` (key-value) | `foreach ($arr as $k => $v):` | Works on dicts and lists (index, value) |
| `if` / `elseif` / `else` | `if ($x > 0):` | Standard conditionals |
| `while` | `while ($n > 0):` | Standard loop |
| Block-end keywords | `endif`, `endforeach`, `endwhile`, `endfor` | Closes the nearest open block |
| `count()` | `count($arr)` | Mapped to `len()` |
| `echo` | `echo $x` | Outputs the value (works inside function bodies too) |
| Line comments | `// text` | Mapped to `# text` |
| File inclusion | `require "file.php"` or `require "file.py"` | Executes the file in the current scope |
| Arithmetic | `+`, `-`, `*`, `/`, `%` | Delegated to Python |
| Comparison | `==`, `!=`, `<`, `>`, `<=`, `>=` | Delegated to Python |
| String output filters | `<?= $x \| filter ?>` | Custom post-processing functions |
| HTML comment stripping | `<!-- ... -->` | Stripped before parsing |
| `$argv` | `$argv[1]` | Command-line arguments (index 0 = first real arg) |
| XML dot-access wrapper | `E` class | Lets `$el->attr` work on XML elements |
| String interpolation | `"Hello $name"`, `"Item $arr[0]"`, `"{$name}"` | Double-quoted strings with `$var` become Python f-strings |
| String concatenation | `$a . $b`, `$a .= $b` | Coerces both sides to string (mixed types safe) |
| `include` / `require_once` / `include_once` | `include "file.php"` | Alias for `require`; executes file in current scope |
| Type casting | `(int)$x`, `(float)$x`, `(string)$x`, `(bool)$x` | Mapped to `int()`, `float()`, `str()`, `bool()` |
| `list()` assignment | `list($a, $b) = $arr` | Mapped to Python tuple unpacking |
| Function definitions | `function foo($a, $b) { ... }` | Named functions with parameters; body uses `{}`; supports `return` and `echo` |
| PHP string functions | `strlen()`, `strtolower()`, `strtoupper()`, `trim()`, `str_replace()`, `substr()`, `strpos()`, `sprintf()`, `ucfirst()`, `ucwords()`, `str_repeat()`, `str_contains()`, `str_starts_with()`, `str_ends_with()`, `number_format()`, `nl2br()`, `htmlspecialchars()`, `strip_tags()`, `str_split()`, … | Available directly in templates |
| PHP array functions | `implode()`, `explode()`, `in_array()`, `array_merge()`, `array_keys()`, `array_values()`, `array_map()`, `array_filter()`, `array_reverse()`, `array_unique()`, `array_push()`, `array_pop()`, `array_shift()`, `array_slice()`, `array_chunk()`, `array_sum()`, `array_flip()`, `array_search()`, `sort()`, `rsort()`, … | Available directly in templates |
| Math functions | `abs()`, `ceil()`, `floor()`, `round()`, `pow()`, `sqrt()`, `max()`, `min()`, `rand()` | Available directly in templates |
| Type-check / conversion helpers | `intval()`, `floatval()`, `strval()`, `is_array()`, `is_string()`, `is_int()`, `is_numeric()`, `isset()`, `empty()` | Available directly in templates |
| JSON helpers | `json_encode()`, `json_decode()` | Available directly in templates |

---

## Not Yet Supported

The following PHP features are not currently translated and are on the roadmap:

| Feature | PHP syntax | Status |
|---|---|---|
| PHP ternary operator | `$a ? $b : $c` | ⏳ Planned (use Python `$b if $a else $c` for now) |
| `switch` / `case` | `switch ($x) { case 1: ... }` | ⏳ Planned |
| Class definitions | `class Foo { ... }` | ⏳ Planned |

> **Tip:** Because the code inside `<?php ?>` tags is executed as Python, you can use any Python expression or built-in directly — `len()`, `range()`, `sorted()`, list comprehensions, etc.

---

## License

MIT — see [LICENSE](LICENSE).
