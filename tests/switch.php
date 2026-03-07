<?php
// ── Basic switch/case ────────────────────────────────────────────────────────

$x = 2;
switch ($x) {
    case 1:
        $result = "one";
        break;
    case 2:
        $result = "two";
        break;
    case 3:
        $result = "three";
        break;
    default:
        $result = "other";
}
assert($result == "two");

// ── Default case ─────────────────────────────────────────────────────────────

$y = 99;
switch ($y) {
    case 1:
        $result2 = "one";
        break;
    default:
        $result2 = "default";
}
assert($result2 == "default");

// ── Fall-through (multiple cases same body) ──────────────────────────────────

$day = 6;
switch ($day) {
    case 1:
    case 7:
        $type = "weekend-ish";
        break;
    case 6:
        $type = "Saturday";
        break;
    default:
        $type = "weekday";
}
assert($type == "Saturday");

// ── Switch on string ─────────────────────────────────────────────────────────

$color = "red";
switch ($color) {
    case "red":
        $hex = "#FF0000";
        break;
    case "green":
        $hex = "#00FF00";
        break;
    case "blue":
        $hex = "#0000FF";
        break;
    default:
        $hex = "#000000";
}
assert($hex == "#FF0000");

// ── Switch in function ───────────────────────────────────────────────────────

function grade($score) {
    switch (true) {
        case $score >= 90:
            return "A";
        case $score >= 80:
            return "B";
        case $score >= 70:
            return "C";
        default:
            return "F";
    }
}
assert(grade(95) == "A");
assert(grade(85) == "B");
assert(grade(72) == "C");
assert(grade(50) == "F");
