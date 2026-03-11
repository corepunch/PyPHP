"""
simplexml.py — PHP SimpleXML-compatible wrapper around xml.etree.ElementTree.

Provides SimpleXMLElement and SimpleXMLElementList that expose the same
dot-access / array-index syntax as PHP's SimpleXMLElement, and the factory
functions simplexml_load_string() / simplexml_load_file() that mirror the
PHP built-ins of the same name.

PHP SimpleXML semantics reproduced here
----------------------------------------
  $xml->child          first <child> element (also iterable over all <child>s)
  $xml->child['attr']  attribute value on the first <child>
  $xml->child[1]       second <child> element
  (string)$xml->child  text content of the first <child>
  count($xml->child)   number of <child> elements
  $xml->getName()      tag name of the element
  $xml->children()     all direct children as a list
  $xml->attributes()   element attributes as a dict
  $xml->xpath($path)   XPath query — returns a list of SimpleXMLElements
  $xml->addChild($n)   append a new child element, returns it
  $xml->addAttribute() set an attribute on the element
  $xml->asXML()        serialise back to an XML string
"""

import warnings
import xml.etree.ElementTree as ET


class SimpleXMLElement:
    """Wraps an xml.etree.ElementTree.Element with a PHP SimpleXML-compatible API.

    Attribute access (``elem.tagname``) returns a :class:`SimpleXMLElementList`
    containing all direct children whose tag matches *tagname*.  The list
    transparently proxies single-element operations to its first item so that
    code written for a single element and code written to iterate over multiple
    elements of the same tag both work without branching.
    """

    def __init__(self, element: ET.Element,
                 tree: ET.ElementTree = None) -> None:
        object.__setattr__(self, '_element', element)
        object.__setattr__(self, '_tree', tree)

    # ── child-element access ──────────────────────────────────────────────────

    def __getattr__(self, name: str) -> 'SimpleXMLElementList':
        """Return all direct children whose tag equals *name*."""
        element = object.__getattribute__(self, '_element')
        tree = object.__getattribute__(self, '_tree')
        return SimpleXMLElementList(
            [SimpleXMLElement(c, tree) for c in element if c.tag == name]
        )

    # ── attribute / index access ──────────────────────────────────────────────

    def __getitem__(self, key):
        """
        String key  →  XML attribute value (mirrors PHP ``$el['attr']``).
        Integer key →  ``self`` if 0, else ``None`` (a bare element is always
                       index 0 in its own single-element list).
        """
        element = object.__getattribute__(self, '_element')
        if isinstance(key, str):
            return element.get(key)
        if isinstance(key, int):
            return self if key == 0 else None
        raise TypeError(
            f'SimpleXMLElement indices must be integers or strings, '
            f'not {type(key).__name__!r}'
        )

    # ── string / bool / len ───────────────────────────────────────────────────

    def __str__(self) -> str:
        """Text content of the element (mirrors PHP ``(string)$el``)."""
        element = object.__getattribute__(self, '_element')
        return element.text or ''

    def __repr__(self) -> str:
        element = object.__getattribute__(self, '_element')
        return f'SimpleXMLElement({element.tag!r})'

    def __bool__(self) -> bool:
        return True

    def __len__(self) -> int:
        """Number of direct children."""
        element = object.__getattribute__(self, '_element')
        return len(list(element))

    def __iter__(self):
        """Iterate over direct children."""
        element = object.__getattribute__(self, '_element')
        tree = object.__getattribute__(self, '_tree')
        return (SimpleXMLElement(child, tree) for child in element)

    # ── PHP SimpleXML methods ─────────────────────────────────────────────────

    def getName(self) -> str:
        """Return the tag name of this element."""
        element = object.__getattribute__(self, '_element')
        return element.tag

    def children(self, ns: str = None) -> 'SimpleXMLElementList':
        """Return all direct children as a :class:`SimpleXMLElementList`.

        If *ns* (a namespace URI) is provided, only children in that namespace
        are included (matching PHP's ``children($ns, true)`` behaviour).
        """
        element = object.__getattribute__(self, '_element')
        tree = object.__getattribute__(self, '_tree')
        if ns is not None:
            prefix = f'{{{ns}}}'
            return SimpleXMLElementList(
                [SimpleXMLElement(c, tree) for c in element if c.tag.startswith(prefix)]
            )
        return SimpleXMLElementList([SimpleXMLElement(c, tree) for c in element])

    def attributes(self, ns: str = None) -> dict:
        """Return the element's attributes as a plain dict.

        If *ns* is given, only attributes in that namespace are returned.
        """
        element = object.__getattribute__(self, '_element')
        if ns is not None:
            prefix = f'{{{ns}}}'
            return {
                k[len(prefix):]: v
                for k, v in element.attrib.items()
                if k.startswith(prefix)
            }
        return dict(element.attrib)

    def xpath(self, path: str) -> 'SimpleXMLElementList':
        """Evaluate an XPath expression and return matching elements.

        Uses :func:`xml.etree.ElementTree.Element.findall` which supports a
        subset of XPath 1.0.  Absolute paths (starting with ``/``) are
        evaluated against the document root via the stored
        :class:`~xml.etree.ElementTree.ElementTree` — matching PHP's
        behaviour where ``$el->xpath('//tag')`` always searches from the
        document root regardless of which element the call is made on.
        """
        element = object.__getattribute__(self, '_element')
        tree = object.__getattribute__(self, '_tree')
        if path.startswith('/'):
            # Absolute paths require an ElementTree, not just an Element.
            # Fall back to wrapping the current element when no tree is stored.
            searcher = tree if tree is not None else ET.ElementTree(element)
            with warnings.catch_warnings():
                warnings.simplefilter('ignore', FutureWarning)
                matches = searcher.findall(path)
        else:
            matches = element.findall(path)
        return SimpleXMLElementList(
            [SimpleXMLElement(e, tree) for e in matches]
        )

    def addChild(self, name: str, value: str = None) -> 'SimpleXMLElement':
        """Append a new ``<name>`` child element and return it.

        If *value* is given it is set as the element's text content.
        """
        element = object.__getattribute__(self, '_element')
        tree = object.__getattribute__(self, '_tree')
        child = ET.SubElement(element, name)
        if value is not None:
            child.text = str(value)
        return SimpleXMLElement(child, tree)

    def addAttribute(self, name: str, value: str) -> None:
        """Set (or add) an attribute on this element."""
        element = object.__getattribute__(self, '_element')
        element.set(name, str(value))

    def asXML(self) -> str:
        """Serialise the element back to an XML string."""
        element = object.__getattribute__(self, '_element')
        return ET.tostring(element, encoding='unicode')

    def count(self) -> int:
        """Return the number of direct children (mirrors PHP ``count($el)``)."""
        return len(self)


class SimpleXMLElementList(list):
    """A list of :class:`SimpleXMLElement` objects returned by child-tag access.

    Behaves as a regular Python list for iteration and integer indexing, but
    also proxies single-element operations (attribute access, string conversion,
    method calls) to ``self[0]`` when used as a scalar — reproducing PHP
    SimpleXML's dual list/element behaviour for ``$xml->child``.
    """

    # ── proxy attribute access to first element ───────────────────────────────

    def __getattr__(self, name: str):
        if self:
            return getattr(self[0], name)
        return SimpleXMLElementList([])

    # ── mixed string/integer subscript ───────────────────────────────────────

    def __getitem__(self, key):
        """
        Integer key → nth element (standard list behaviour).
        String key  → attribute of the first element (mirrors ``$list['attr']``).
        """
        if isinstance(key, str):
            if self:
                # self[0] goes through the integer branch → list.__getitem__(0)
                return list.__getitem__(self, 0)[key]
            return None
        return list.__getitem__(self, key)

    # ── scalar coercions ──────────────────────────────────────────────────────

    def __str__(self) -> str:
        """Text content of the first element, or empty string."""
        if self:
            return str(list.__getitem__(self, 0))
        return ''

    def __bool__(self) -> bool:
        return len(self) > 0


# ── factory functions ─────────────────────────────────────────────────────────

def simplexml_load_string(xml_string: str) -> SimpleXMLElement:
    """Parse an XML string and return a :class:`SimpleXMLElement` for the root.

    Mirrors PHP's ``simplexml_load_string()``.
    """
    element = ET.fromstring(xml_string)
    tree = ET.ElementTree(element)
    return SimpleXMLElement(element, tree)


def simplexml_load_file(filename: str) -> SimpleXMLElement:
    """Parse an XML file and return a :class:`SimpleXMLElement` for the root.

    Mirrors PHP's ``simplexml_load_file()``.
    """
    tree = ET.parse(filename)
    return SimpleXMLElement(tree.getroot(), tree)
