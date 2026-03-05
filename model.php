<?php
/*
 * model.php — PHP rewrite of model.py
 *
 * Uses xml\etree\ElementTree (via PyPHP's 'use' import) for XML parsing,
 * matching the Python original closely while using PHP syntax.
 *
 * Run through PyPHP: python pyphp.py model.php
 */

use os;
use xml\etree\ElementTree as ET;

/* ── Kind "enum" implemented as PHP class constants ── */
class Kind {
    const ATOMIC    = "atomic";
    const ENUM      = "enum";
    const STRUCT    = "struct";
    const COMPONENT = "component";
    const RESOURCE  = "resource";
    const FIXED     = "fixed";
    const UNKNOWN   = "unknown";
}

/* ── Atomic-type lookup table ── */
$atomic_types = {};
$atomic_types["float"]  = ["luaL_checknumber",  "lua_pushnumber"];
$atomic_types["int"]    = ["luaL_checknumber",  "lua_pushnumber"];
$atomic_types["uint"]   = ["luaL_checknumber",  "lua_pushnumber"];
$atomic_types["long"]   = ["luaL_checkinteger", "lua_pushinteger"];
$atomic_types["bool"]   = ["lua_toboolean",     "lua_pushboolean"];
$atomic_types["string"] = ["luaL_checkstring",  "lua_pushstring"];
$atomic_types["fixed"]  = ["luaL_checkstring",  "lua_pushstring"];
$atomic_types["handle"] = ["lua_touserdata",    "lua_pushlightuserdata"];

/* ── C-type printer format strings, keyed by Kind constant ── */
$printers = {};
$printers[Kind::ATOMIC]    = "%s";
$printers[Kind::ENUM]      = "enum %s";
$printers[Kind::STRUCT]    = "struct %s";
$printers[Kind::COMPONENT] = "struct %s";
$printers[Kind::RESOURCE]  = "struct %s";
$printers[Kind::FIXED]     = "%sString_t";
$printers[Kind::UNKNOWN]   = "%s_t";

/* ─────────────────────────────────────────────────────── */

class Model {
    public function __construct($xml_file, $include_file = null) {
        $tree = ET::parse($xml_file);
        $this->root = $tree->getroot();
        $this->source = $include_file;

        /* requires */
        $this->requires = [];
        foreach ($tree->getroot()->findall('require') as $req):
            $this->requires[] = new Model(os::path::join(os::path::dirname($xml_file), $req->get('file')), $req->get('file'));
        endforeach;

        /* structs */
        $this->structs = {};
        foreach ($this->root->findall(".//struct[@name]") as $s):
            $this->structs[$s->get('name')] = new Struct($s, $this);
        endforeach;

        /* enums */
        $this->enums = {};
        foreach ($this->root->findall(".//enums[@name]") as $e):
            $this->enums[$e->get('name')] = new Enum($e, $this);
        endforeach;

        /* components (XML tag: class) */
        $this->components = {};
        foreach ($this->root->findall(".//class[@name]") as $c):
            $this->components[$c->get('name')] = new Component($c, $this);
        endforeach;

        /* resources */
        $this->resources = {};
        foreach ($this->root->findall(".//resource[@type]") as $c):
            $this->resources[$c->get('type')] = new Resource($c, $this);
        endforeach;
    }

    /* Recursive helper: is $key present in attribute $attr_name of this model
     * or any of its transitive requires?  Cycle-safe via $visited list. */
    public function _has_in($key, $attr_name, $visited = null) {
        if ($visited == null) {
            $visited = [];
        }
        if (in_array(id($this), $visited)) {
            return false;
        }
        $visited[] = id($this);
        if (array_key_exists($key, getattr($this, $attr_name))) {
            return true;
        }
        foreach ($this->requires as $req):
            if ($req->_has_in($key, $attr_name, $visited)) {
                return true;
            }
        endforeach;
        return false;
    }

    public function getModuleName() {
        return $this->root->get('name');
    }

    public function getStruct($name) {
        return $this->structs->get($name);
    }

    public function getEnum($name) {
        return $this->enums->get($name);
    }

    public function getComponent($name) {
        return $this->components->get($name);
    }

    public function getResource($resource_type) {
        return $this->resources->get($resource_type);
    }

    public function getStructs() {
        return $this->structs;
    }

    public function getEnums() {
        return $this->enums;
    }

    public function getComponents() {
        return $this->components;
    }

    public function getResources() {
        return $this->resources;
    }

    public function getKind($type) {
        if ($type == "fixed") {
            return Kind::FIXED;
        }
        if (array_key_exists($type, $atomic_types)) {
            return Kind::ATOMIC;
        }
        if ($this->_has_in($type, "enums")) {
            return Kind::ENUM;
        }
        if ($this->_has_in($type, "structs")) {
            return Kind::STRUCT;
        }
        if ($this->_has_in($type, "components")) {
            return Kind::COMPONENT;
        }
        if ($this->_has_in($type, "resources")) {
            return Kind::RESOURCE;
        }
        return Kind::UNKNOWN;
    }

    /* Generator: yield (module_name, model) for each required module. */
    public function getRequires() {
        foreach ($this->requires as $r):
            yield $r->getModuleName(), $r;
        endforeach;
    }
}

/* ── Base class: wraps an XML element and exposes its attributes ── */
class Base {
    public function __construct($element, $model) {
        $this->_element = $element;
        $this->_model   = $model;
        /* Mirror every XML attribute as a Python instance attribute. */
        foreach ($element->attrib as $k => $v):
            setattr($this, $k, $v);
        endforeach;
    }

    public function getName() {
        return $this->_element->get('name');
    }

    public function getAttribute($key) {
        return $this->_element->get($key);
    }

    public function getAttributes() {
        return $this->_element->attrib;
    }
}

/* ── Type: a typed field / argument / return value ── */
class Type extends Base {
    public function __construct($element, $model) {
        parent::__construct($element, $model);
        $this->kind = $model->getKind($this->type);
    }

    /* Return the C-type string for this Type node. */
    public function __str__() {
        $base = $printers->get($this->kind, "%s") % $this->type;
        if (getattr($this, 'const', false)) {
            $base .= " const";
        }
        if (getattr($this, 'pointer', false)) {
            $base .= "*";
        }
        return $base;
    }
}

/* ── Method: a function / method descriptor with argument list ── */
class Method extends Base {
    public function __construct($element, $model, $owner = null) {
        parent::__construct($element, $model);

        $this->args = [];
        foreach ($this->_element->findall('arg') as $arg):
            $this->args[] = [$arg->get('name'), new Type($arg, $model)];
        endforeach;

        $this->static = $this->_element->get('static');

        /* Prepend implicit 'this' argument for non-static methods. */
        if ($owner != null && !$this->static) {
            $arg_el = ET::Element("arg", {"name": "this", "type": $owner->get('name'), "pointer": "true"});
            $this->args = [["this", new Type($arg_el, $model)]] + $this->args;
        }

        $returns = $this->_element->find('returns');
        if ($returns != null) {
            $this->return_type = new Type($returns, $model);
        } else {
            $this->return_type = 'void';
        }

        if ($owner != null) {
            $this->full_name = $owner->get('prefix', '') . $this->getName();
        } else {
            $this->full_name = $this->getName();
        }
    }

    /* Generator: yield (name, Type) for each argument. */
    public function getArgs() {
        foreach ($this->args as $item):
            yield $item[0], $item[1];
        endforeach;
    }

    /* Generator: yield Type for each argument (types only). */
    public function getArgsTypes() {
        foreach ($this->args as $item):
            yield $item[1];
        endforeach;
    }
}

/* ── Struct: a named collection of typed fields and methods ── */
class Struct extends Base {
    public function __construct($element, $model) {
        parent::__construct($element, $model);
    }

    public function getFields() {
        foreach ($this->_element->findall(".//field[@name]") as $f):
            yield $f->get('name'), new Type($f, $this->_model);
        endforeach;
    }

    public function getMethods() {
        foreach ($this->_element->findall(".//method[@name]") as $m):
            yield $m->get('name'), new Method($m, $this->_model, $this->_element);
        endforeach;
    }

    public function __iter__() {
        return $this->getFields();
    }

    public function __getitem__($key) {
        foreach ($this->getFields() as $item):
            $name  = $item[0];
            $type_ = $item[1];
            if ($name == $key) {
                return $type_;
            }
        endforeach;
        raise KeyError($key);
    }
}

/* ── Component (XML tag: class): Struct + property list ── */
class Component extends Struct {
    public function __construct($element, $model) {
        parent::__construct($element, $model);
    }

    public function getProperties() {
        foreach ($this->_element->findall(".//property[@name]") as $f):
            yield $f->get('name'), new Type($f, $this->_model);
        endforeach;
    }
}

/* ── Enum: a named enumeration ── */
class Enum extends Base {
    public function __construct($element, $model) {
        parent::__construct($element, $model);
    }

    public function getValues() {
        foreach ($this->_element->findall(".//enum[@name]") as $e):
            yield $e->get('name'), $e->text;
        endforeach;
    }
}

/* ── Resource: a named resource type ── */
class Resource extends Base {
    public function __construct($element, $model) {
        parent::__construct($element, $model);
    }
}
?>
