<?php
// Tests for multi-line PHP array literals (issue: _braces_to_indent handling)
// Covers:
//   - multi-line nested array with separate closing bracket line
//   - multi-line nested array where closing bracket shares line with last value
//   - single-line array with double-quoted keys containing {placeholder} strings
//   - multi-line array with double-quoted keys

class Config {
    public static $TypeInfosSQ = [
        'float' => [
            'decl'    => "%s",
            'check'   => "luaL_checknumber(L, {arg})",
            'push'    => "lua_pushnumber(L, {arg})",
            'convert' => "self.{addr} = {arg}",
            'format'  => "%f"
        ],
        'int' => [
            'decl'    => "%d",
            'check'   => "luaL_checkinteger(L, {arg})",
            'push'    => "lua_pushinteger(L, {arg})",
            'convert' => "self.{addr} = {arg}",
            'format'  => "%d"
        ],
    ];

    public static $TypeInfosDQ = [
        "float" => [
            "decl"    => "%s",
            "check"   => "luaL_checknumber(L, {arg})",
            "push"    => "lua_pushnumber(L, {arg})",
            "convert" => "self.{addr} = {arg}",
            "format"  => "%f"
        ],
        "int" => [
            "decl"    => "%d",
            "check"   => "luaL_checkinteger(L, {arg})",
            "push"    => "lua_pushinteger(L, {arg})",
            "convert" => "self.{addr} = {arg}",
            "format"  => "%d"
        ],
    ];

    // Mixed: closing bracket on same line as last value
    public static $TypeInfosMixed = [
        'float' => [
            'decl'    => "%s",
            'check'   => "luaL_checknumber(L, {arg})",
            'push'    => "lua_pushnumber(L, {arg})",
            'convert' => "self.{addr} = {arg}",
            'format'  => "%f"],
        'int' => [
            'decl'    => "%d",
            'check'   => "luaL_checkinteger(L, {arg})",
            'push'    => "lua_pushinteger(L, {arg})",
            'convert' => "self.{addr} = {arg}",
            'format'  => "%d"],
    ];

    // Single-line with double-quoted keys
    public static $TypeInfosInline = [
        "float" => ["decl" => "%s", "check" => "luaL_checknumber(L, {arg})", "push" => "lua_pushnumber(L, {arg})", "convert" => "self.{addr} = {arg}", "format" => "%f"],
        "int"   => ["decl" => "%d", "check" => "luaL_checkinteger(L, {arg})", "push" => "lua_pushinteger(L, {arg})", "convert" => "self.{addr} = {arg}", "format" => "%d"],
    ];
}

// ── Verify single-quoted multi-line ──────────────────────────────────────────
assert(Config::$TypeInfosSQ['float']['decl'] == "%s");
assert(Config::$TypeInfosSQ['float']['check'] == "luaL_checknumber(L, {arg})");
assert(Config::$TypeInfosSQ['float']['convert'] == "self.{addr} = {arg}");
assert(Config::$TypeInfosSQ['int']['decl'] == "%d");
assert(Config::$TypeInfosSQ['int']['format'] == "%d");

// ── Verify double-quoted multi-line ──────────────────────────────────────────
assert(Config::$TypeInfosDQ["float"]["decl"] == "%s");
assert(Config::$TypeInfosDQ["float"]["check"] == "luaL_checknumber(L, {arg})");
assert(Config::$TypeInfosDQ["float"]["convert"] == "self.{addr} = {arg}");
assert(Config::$TypeInfosDQ["int"]["decl"] == "%d");

// ── Verify mixed (closing bracket on last-value line) ────────────────────────
assert(Config::$TypeInfosMixed['float']['decl'] == "%s");
assert(Config::$TypeInfosMixed['float']['convert'] == "self.{addr} = {arg}");
assert(Config::$TypeInfosMixed['int']['format'] == "%d");

// ── Verify inline double-quoted ──────────────────────────────────────────────
assert(Config::$TypeInfosInline["float"]["decl"] == "%s");
assert(Config::$TypeInfosInline["float"]["convert"] == "self.{addr} = {arg}");
assert(Config::$TypeInfosInline["int"]["check"] == "luaL_checkinteger(L, {arg})");
