<?php
// ── simplexml_load_string: basic element access ────────────────────────────
$xml = simplexml_load_string('<root><price>1.99</price><name>Widget</name></root>');
assert($xml->getName() == "root");
assert(strval($xml->price) == "1.99");
assert(strval($xml->name) == "Widget");

// ── attribute access via string index ─────────────────────────────────────
$xml2 = simplexml_load_string('<items><item id="1" color="red">Apple</item><item id="2" color="green">Lime</item></items>');
assert($xml2->item['id'] == "1");
assert($xml2->item['color'] == "red");
assert(strval($xml2->item) == "Apple");

// ── integer index to get nth child of same tag ────────────────────────────
assert($xml2->item[0]['id'] == "1");
assert($xml2->item[1]['id'] == "2");
assert(strval($xml2->item[1]) == "Lime");

// ── count of same-tag children ────────────────────────────────────────────
assert(count($xml2->item) == 2);

// ── iteration over same-tag children ─────────────────────────────────────
$ids = [];
foreach ($xml2->item as $item) {
    array_push($ids, $item['id']);
}
assert($ids[0] == "1");
assert($ids[1] == "2");

// ── children() returns all direct children ────────────────────────────────
$root = simplexml_load_string('<root><a>1</a><b>2</b><c>3</c></root>');
$kids = $root->children();
assert(count($kids) == 3);

// ── attributes() returns a dict of attributes ─────────────────────────────
$el = simplexml_load_string('<node x="10" y="20"/>');
$attrs = $el->attributes();
assert($attrs['x'] == "10");
assert($attrs['y'] == "20");

// ── xpath query ───────────────────────────────────────────────────────────
$doc = simplexml_load_string('<root><a><b>hello</b></a><a><b>world</b></a></root>');
$bs = $doc->xpath('.//b');
assert(count($bs) == 2);
assert(strval($bs[0]) == "hello");
assert(strval($bs[1]) == "world");

// ── absolute xpath from root (//tag) ─────────────────────────────────────
$doc2 = simplexml_load_string('<root><a><b id="1">hello</b></a><a><b id="2">world</b></a></root>');
$bs2 = $doc2->xpath('//b');
assert(count($bs2) == 2);
assert(strval($bs2[0]) == "hello");
assert($bs2[0]['id'] == "1");
assert(strval($bs2[1]) == "world");

// xpath on a nested element still searches whole document for absolute paths
$as = $doc2->a;
$bs3 = $as->xpath('//b');
assert(count($bs3) == 2);

// ── addChild and addAttribute ─────────────────────────────────────────────
$catalog = simplexml_load_string('<catalog/>');
$book = $catalog->addChild('book', 'Learning PHP');
$book->addAttribute('id', '42');
assert(strval($catalog->book) == "Learning PHP");
assert($catalog->book['id'] == "42");

// ── asXML round-trip ──────────────────────────────────────────────────────
$simple = simplexml_load_string('<msg>hi</msg>');
$xmlStr = $simple->asXML();
assert(strval(simplexml_load_string($xmlStr)) == "hi");

// ── missing child returns empty list (falsy) ──────────────────────────────
$empty = simplexml_load_string('<root/>');
assert(count($empty->missing) == 0);
assert(strval($empty->missing) == "");
?>
