---
layout: default
title: Use Cases
nav_order: 3
permalink: /usecases
---

# Suggested Use Cases

PyPHP is a general-purpose text generator.  If you can describe your output as
"static structure + data-driven logic", PyPHP is a good fit.  Here are four
real-world scenarios that show the range of what's possible.

---

## 1. C / C++ Code Generation

The most common use case.  An XML or JSON model describes your data structures
(field names, types, constraints), and a PyPHP template turns that model into:

- Struct / class declarations (`.h`)
- Serialization / deserialization boilerplate
- Lookup tables and enumerations
- Test stubs

**Example — C header from an XML model:**

```xml
<!-- model.xml -->
<model>
  <struct name="Packet">
    <field name="id"      type="uint32_t"/>
    <field name="length"  type="uint16_t"/>
    <field name="payload" type="uint8_t *"/>
  </struct>
</model>
```

```php
<?php require "model.py"; ?>
<?php $model = new Model("model.xml"); ?>
#pragma once
#include <stdint.h>

<?php foreach ($model->structs() as $s): ?>
/** Auto-generated from model.xml */
typedef struct <?= $s->name ?> {
<?php foreach ($s->findall("field") as $f): ?>
    <?= $f->type ?> <?= $f->name ?>;
<?php endforeach ?>
} <?= $s->name ?>;

<?php endforeach ?>
```

Output:

```c
#pragma once
#include <stdint.h>

/** Auto-generated from model.xml */
typedef struct Packet {
    uint32_t id;
    uint16_t length;
    uint8_t * payload;
} Packet;
```

See [`examples/c_header/`](https://github.com/corepunch/PyPHP/tree/main/examples/c_header)
for a fully runnable version.

---

## 2. JavaScript / TypeScript SDK Generation

Given an XML or JSON API definition, generate a complete client SDK — no manual
copy-paste, no drift between spec and code.

**Example — TypeScript interfaces from an API schema:**

```xml
<!-- api.xml -->
<api>
  <type name="User">
    <field name="id"    type="number"/>
    <field name="name"  type="string"/>
    <field name="email" type="string"/>
  </type>
  <type name="Post">
    <field name="id"      type="number"/>
    <field name="title"   type="string"/>
    <field name="authorId" type="number"/>
  </type>
</api>
```

```php
<?php
use xml\etree\ElementTree as ET;
$root = ET::parse("api.xml")->getroot();
?>
// Auto-generated — do not edit

<?php foreach ($root->findall("type") as $type): ?>
export interface <?= $type->get("name") ?> {
<?php foreach ($type->findall("field") as $field): ?>
  <?= $field->get("name") ?>: <?= $field->get("type") ?>;
<?php endforeach ?>
}

<?php endforeach ?>
```

Output:

```typescript
// Auto-generated — do not edit

export interface User {
  id: number;
  name: string;
  email: string;
}

export interface Post {
  id: number;
  title: string;
  authorId: number;
}
```

You can extend this template to also generate fetch wrappers, Zod schemas,
or React Query hooks for each endpoint in the spec.

---

## 3. Java / Kotlin Data Classes from XML

Generate Java POJOs or Kotlin data classes from a shared XML model so that
back-end and front-end stay in sync automatically.

**Example — Java POJO from XML:**

```xml
<!-- schema.xml -->
<schema package="com.example.model">
  <entity name="Product">
    <field name="id"    type="long"/>
    <field name="title" type="String"/>
    <field name="price" type="double"/>
  </entity>
</schema>
```

```php
<?php
use xml\etree\ElementTree as ET;
$root   = ET::parse("schema.xml")->getroot();
$pkg    = $root->get("package");
?>
package <?= $pkg ?>;

import java.util.Objects;

<?php foreach ($root->findall("entity") as $entity): ?>
/** Auto-generated. Do not edit. */
public class <?= $entity->get("name") ?> {
<?php foreach ($entity->findall("field") as $f): ?>
    private <?= $f->get("type") ?> <?= $f->get("name") ?>;
<?php endforeach ?>

    public <?= $entity->get("name") ?>() {}

<?php foreach ($entity->findall("field") as $f): ?>
    public <?= $f->get("type") ?> get<?= ucfirst($f->get("name")) ?>() { return this.<?= $f->get("name") ?>; }
    public void set<?= ucfirst($f->get("name")) ?>(<?= $f->get("type") ?> value) { this.<?= $f->get("name") ?> = value; }
<?php endforeach ?>
}
<?php endforeach ?>
```

Output (simplified):

```java
package com.example.model;

/** Auto-generated. Do not edit. */
public class Product {
    private long id;
    private String title;
    private double price;

    public Product() {}

    public long getId() { return this.id; }
    public void setId(long value) { this.id = value; }
    // ...
}
```

The same template can be adapted to emit Kotlin data classes, Lombok
annotations, JPA entity annotations, or anything else you need.

---

## 4. Markdown / HTML Documentation

Generate reference documentation from the same source-of-truth XML or JSON that
drives your code.  This keeps your docs and your API in sync.

**Example — REST API reference in Markdown:**

```xml
<!-- api.xml -->
<api version="1.0">
  <endpoint method="GET" path="/users">
    <description>List all users.</description>
    <param name="limit"  type="integer" description="Max results (default 20)"/>
    <param name="offset" type="integer" description="Pagination offset"/>
  </endpoint>
  <endpoint method="POST" path="/users">
    <description>Create a new user.</description>
    <param name="name"  type="string"  description="Display name (required)"/>
    <param name="email" type="string"  description="Email address (required)"/>
  </endpoint>
</api>
```

```php
<?php
use xml\etree\ElementTree as ET;
$root = ET::parse("api.xml")->getroot();
?>
# API Reference v<?= $root->get("version") ?>

<?php foreach ($root->findall("endpoint") as $ep): ?>
## `<?= $ep->get("method") ?>` <?= $ep->get("path") ?>

<?= $ep->findtext("description") ?>

<?php $params = $ep->findall("param"); ?>
<?php if (count($params) > 0): ?>
**Parameters:**

| Name | Type | Description |
|------|------|-------------|
<?php foreach ($params as $p): ?>
| `<?= $p->get("name") ?>` | `<?= $p->get("type") ?>` | <?= $p->get("description") ?> |
<?php endforeach ?>
<?php endif ?>

---
<?php endforeach ?>
```

See [`examples/docs/`](https://github.com/corepunch/PyPHP/tree/main/examples/docs)
for a runnable version.

---

## More Ideas

| Idea | Input | Output |
|------|-------|--------|
| SQL migration scripts | JSON schema diff | `ALTER TABLE` statements |
| Nginx / Apache config | JSON vhost list | `server {}` blocks |
| Makefile / CMakeLists | JSON module list | Build rules |
| OpenAPI spec | JSON route list | YAML spec |
| GitHub Actions workflow | JSON job matrix | `.yml` workflow |
| Protocol Buffer definitions | XML type model | `.proto` file |
| CSS utility classes | JSON design tokens | Tailwind / plain CSS |
| Email HTML templates | JSON campaign data | Personalized HTML emails |
