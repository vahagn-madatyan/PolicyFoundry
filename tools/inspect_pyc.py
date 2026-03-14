#!/usr/bin/env python3
"""Bytecode inspection toolkit for reconstructing Python source from .pyc files.

Reads .pyc files using Python 3.13's marshal + dis + types modules and extracts
structured information: module docstrings, import statements, class definitions
with base classes, function/method signatures with argument names, default values,
and string constants.

Usage:
    .venv/bin/python3 tools/inspect_pyc.py <path-to-pyc>
    .venv/bin/python3 tools/inspect_pyc.py --recursive <directory>
"""

from __future__ import annotations

import argparse
import dis
import importlib.util
import marshal
import os
import struct
import sys
import types
from pathlib import Path


def read_pyc(path: str | Path) -> types.CodeType:
    """Read a .pyc file and return the code object.

    Handles Python 3.13 .pyc format:
      - 4 bytes magic number
      - 4 bytes flags
      - 8 bytes (timestamp + size) or 8 bytes (hash-based)
      - marshalled code object
    """
    path = Path(path)
    with open(path, "rb") as f:
        magic = f.read(4)
        if len(magic) < 4:
            raise ValueError(f"File too short to be a .pyc: {path}")

        flags = struct.unpack("<I", f.read(4))[0]

        # Flags bit 0: hash-based validation
        # Either way, skip 8 more bytes (timestamp+size or hash)
        f.read(8)

        try:
            code = marshal.load(f)
        except Exception as e:
            raise ValueError(f"Failed to unmarshal code from {path}: {e}") from e

    if not isinstance(code, types.CodeType):
        raise ValueError(f"Top-level object in {path} is not a code object: {type(code)}")

    return code


def extract_docstring(code: types.CodeType) -> str | None:
    """Extract module/class/function docstring from a code object."""
    if code.co_consts and isinstance(code.co_consts[0], str):
        return code.co_consts[0]
    return None


def extract_imports(code: types.CodeType) -> list[dict]:
    """Extract import statements from bytecode instructions.

    Returns list of dicts with keys:
      - type: 'import' or 'from_import'
      - module: module name
      - names: list of imported names (for from imports)
    """
    imports = []
    instructions = list(dis.get_instructions(code))

    i = 0
    while i < len(instructions):
        instr = instructions[i]

        if instr.opname == "IMPORT_NAME":
            module_name = instr.argval

            # Look backward for LOAD_CONST (fromlist) and LOAD_CONST (level)
            # Look forward for IMPORT_FROM or STORE_NAME
            from_names = []
            j = i + 1
            while j < len(instructions) and instructions[j].opname == "IMPORT_FROM":
                from_names.append(instructions[j].argval)
                j += 1

            if from_names:
                imports.append({
                    "type": "from_import",
                    "module": module_name,
                    "names": from_names,
                })
            else:
                imports.append({
                    "type": "import",
                    "module": module_name,
                    "names": [module_name.split(".")[-1]],
                })

        i += 1

    return imports


def extract_string_constants(code: types.CodeType) -> list[str]:
    """Extract string constants from a code object (excluding docstrings)."""
    strings = []
    for i, const in enumerate(code.co_consts):
        if isinstance(const, str) and const:
            # Skip the docstring (first const if it's a string)
            if i == 0 and extract_docstring(code) == const:
                continue
            strings.append(const)
    return strings


def extract_function_signature(code: types.CodeType) -> dict:
    """Extract function signature details from a code object."""
    argcount = code.co_argcount
    posonlycount = code.co_posonlyargcount
    kwonlycount = code.co_kwonlyargcount
    varnames = list(code.co_varnames)
    flags = code.co_flags

    # Positional args
    positional_args = varnames[:argcount]

    # Keyword-only args
    kw_start = argcount
    if flags & 0x04:  # CO_VARARGS (*args)
        kw_start += 1
    kwonly_args = varnames[argcount:argcount + kwonlycount]

    has_varargs = bool(flags & 0x04)
    has_varkw = bool(flags & 0x08)

    # Find *args and **kwargs names
    varargs_name = None
    varkw_name = None
    extra_idx = argcount + kwonlycount
    if has_varargs:
        if extra_idx < len(varnames):
            varargs_name = varnames[extra_idx]
        extra_idx += 1
    if has_varkw:
        if extra_idx < len(varnames):
            varkw_name = varnames[extra_idx]

    # Defaults are in co_consts but we need the code execution context
    # We can report which consts look like defaults
    defaults = []
    for const in code.co_consts:
        if const is not None and not isinstance(const, types.CodeType):
            pass  # Defaults are set at definition time, hard to distinguish

    return {
        "name": code.co_name,
        "args": positional_args,
        "kwonly_args": kwonly_args,
        "pos_only_count": posonlycount,
        "has_varargs": has_varargs,
        "varargs_name": varargs_name,
        "has_varkw": has_varkw,
        "varkw_name": varkw_name,
        "is_async": bool(flags & 0x100),  # CO_COROUTINE
        "is_generator": bool(flags & 0x20),  # CO_GENERATOR
    }


def extract_classes(code: types.CodeType) -> list[dict]:
    """Extract class definitions from bytecode.

    Looks for PUSH_NULL + LOAD_BUILD_CLASS patterns and extracts:
      - class name
      - base classes (from LOAD_GLOBAL/LOAD_ATTR before CALL)
      - methods (from inner code objects)
    """
    classes = []
    instructions = list(dis.get_instructions(code))

    i = 0
    while i < len(instructions):
        instr = instructions[i]

        if instr.opname == "PUSH_NULL":
            # Check if next is LOAD_BUILD_CLASS
            if i + 1 < len(instructions) and instructions[i + 1].opname == "LOAD_BUILD_CLASS":
                class_info = _parse_class_def(instructions, i + 2, code)
                if class_info:
                    classes.append(class_info)
        elif instr.opname == "LOAD_BUILD_CLASS":
            class_info = _parse_class_def(instructions, i + 1, code)
            if class_info:
                classes.append(class_info)

        i += 1

    return classes


def _parse_class_def(instructions: list, start: int, code: types.CodeType) -> dict | None:
    """Parse a class definition starting after LOAD_BUILD_CLASS."""
    # After LOAD_BUILD_CLASS we expect:
    #   MAKE_FUNCTION / LOAD_CONST (code) + MAKE_FUNCTION
    #   LOAD_CONST (class name string)
    #   LOAD_GLOBAL / LOAD_ATTR (base classes)
    #   CALL

    class_name = None
    bases = []
    class_code = None

    i = start
    while i < len(instructions):
        instr = instructions[i]

        if instr.opname == "LOAD_CONST" and isinstance(instr.argval, types.CodeType):
            class_code = instr.argval
        elif instr.opname == "LOAD_CONST" and isinstance(instr.argval, str):
            if class_name is None:
                class_name = instr.argval
        elif instr.opname in ("LOAD_GLOBAL", "LOAD_ATTR"):
            if isinstance(instr.argval, str):
                bases.append(instr.argval)
        elif instr.opname in ("CALL", "CALL_FUNCTION", "CALL_KW"):
            break
        elif instr.opname == "STORE_NAME":
            # This is where the class gets stored
            if class_name is None:
                class_name = instr.argval
            break
        elif instr.opname in ("LOAD_BUILD_CLASS", "RETURN_VALUE"):
            break

        i += 1

    if class_name is None and class_code is not None:
        class_name = class_code.co_name

    if class_name is None:
        return None

    # Extract methods from class code object
    methods = []
    if class_code is not None:
        for const in class_code.co_consts:
            if isinstance(const, types.CodeType) and const.co_name != class_name:
                sig = extract_function_signature(const)
                sig["docstring"] = extract_docstring(const)
                methods.append(sig)

    return {
        "name": class_name,
        "bases": bases,
        "methods": methods,
        "docstring": extract_docstring(class_code) if class_code else None,
    }


def extract_functions(code: types.CodeType) -> list[dict]:
    """Extract top-level function definitions from a code object."""
    functions = []

    for const in code.co_consts:
        if isinstance(const, types.CodeType):
            # Skip class bodies (they have a matching class name)
            # Function code objects are nested in co_consts
            name = const.co_name
            if name.startswith("<"):
                continue  # Skip <module>, <listcomp>, etc.

            sig = extract_function_signature(const)
            sig["docstring"] = extract_docstring(const)

            # Extract nested functions
            nested = []
            for inner_const in const.co_consts:
                if isinstance(inner_const, types.CodeType) and not inner_const.co_name.startswith("<"):
                    inner_sig = extract_function_signature(inner_const)
                    inner_sig["docstring"] = extract_docstring(inner_const)
                    nested.append(inner_sig)

            sig["nested_functions"] = nested
            functions.append(sig)

    return functions


def inspect_pyc(path: str | Path) -> dict:
    """Full inspection of a .pyc file. Returns structured dict."""
    path = Path(path)
    code = read_pyc(path)

    # Extract all info
    docstring = extract_docstring(code)
    imports = extract_imports(code)
    classes = extract_classes(code)
    functions = extract_functions(code)
    string_constants = extract_string_constants(code)

    # Filter functions that are actually class bodies
    class_names = {c["name"] for c in classes}
    functions = [f for f in functions if f["name"] not in class_names]

    return {
        "file": str(path),
        "module_name": code.co_name,
        "docstring": docstring,
        "imports": imports,
        "classes": classes,
        "functions": functions,
        "string_constants": string_constants,
        "co_filename": code.co_filename,
    }


def format_signature(sig: dict) -> str:
    """Format a function signature dict as a readable string."""
    parts = []

    args = sig["args"]
    pos_only = sig.get("pos_only_count", 0)

    for idx, arg in enumerate(args):
        parts.append(arg)
        if idx == pos_only - 1 and pos_only > 0:
            parts.append("/")

    if sig.get("has_varargs"):
        parts.append(f"*{sig.get('varargs_name', 'args')}")
    elif sig.get("kwonly_args"):
        parts.append("*")

    for kw in sig.get("kwonly_args", []):
        parts.append(kw)

    if sig.get("has_varkw"):
        parts.append(f"**{sig.get('varkw_name', 'kwargs')}")

    prefix = "async " if sig.get("is_async") else ""
    return f"{prefix}def {sig['name']}({', '.join(parts)})"


def print_inspection(info: dict, verbose: bool = False) -> None:
    """Print inspection results in a human-readable format."""
    print(f"{'=' * 70}")
    print(f"File: {info['file']}")
    print(f"Original source: {info['co_filename']}")
    print(f"{'=' * 70}")

    if info["docstring"]:
        print(f"\nModule docstring:")
        print(f"  \"\"\"{info['docstring']}\"\"\"")

    if info["imports"]:
        print(f"\nImports ({len(info['imports'])}):")
        for imp in info["imports"]:
            if imp["type"] == "import":
                print(f"  import {imp['module']}")
            else:
                names = ", ".join(imp["names"])
                print(f"  from {imp['module']} import {names}")

    if info["classes"]:
        print(f"\nClasses ({len(info['classes'])}):")
        for cls in info["classes"]:
            bases_str = f"({', '.join(cls['bases'])})" if cls["bases"] else ""
            print(f"\n  class {cls['name']}{bases_str}:")
            if cls.get("docstring"):
                doc_preview = cls["docstring"][:100]
                print(f"    \"\"\"{doc_preview}{'...' if len(cls['docstring']) > 100 else ''}\"\"\"")
            for method in cls.get("methods", []):
                sig_str = format_signature(method)
                print(f"    {sig_str}")
                if method.get("docstring"):
                    doc_preview = method["docstring"][:80]
                    print(f"      \"\"\"{doc_preview}{'...' if len(method['docstring']) > 80 else ''}\"\"\"")

    if info["functions"]:
        print(f"\nFunctions ({len(info['functions'])}):")
        for func in info["functions"]:
            sig_str = format_signature(func)
            print(f"\n  {sig_str}")
            if func.get("docstring"):
                doc_preview = func["docstring"][:100]
                print(f"    \"\"\"{doc_preview}{'...' if len(func['docstring']) > 100 else ''}\"\"\"")
            for nested in func.get("nested_functions", []):
                nested_sig = format_signature(nested)
                print(f"    [nested] {nested_sig}")

    if verbose and info["string_constants"]:
        print(f"\nString constants ({len(info['string_constants'])}):")
        for s in info["string_constants"]:
            preview = s[:80].replace("\n", "\\n")
            print(f"  {repr(preview)}")

    print()


def find_pyc_files(directory: str | Path) -> list[Path]:
    """Recursively find all .pyc files in a directory."""
    directory = Path(directory)
    return sorted(directory.rglob("*.pyc"))


def main():
    parser = argparse.ArgumentParser(
        description="Inspect Python .pyc bytecode files and extract structural information.",
    )
    parser.add_argument(
        "path",
        help="Path to a .pyc file or directory (with --recursive)",
    )
    parser.add_argument(
        "--recursive", "-r",
        action="store_true",
        help="Process all .pyc files in the directory tree",
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Show string constants and additional details",
    )
    parser.add_argument(
        "--summary", "-s",
        action="store_true",
        help="Show only a brief summary (class/function names)",
    )

    args = parser.parse_args()
    path = Path(args.path)

    if args.recursive or path.is_dir():
        if not path.is_dir():
            print(f"Error: {path} is not a directory", file=sys.stderr)
            sys.exit(1)

        pyc_files = find_pyc_files(path)
        if not pyc_files:
            print(f"No .pyc files found in {path}", file=sys.stderr)
            sys.exit(1)

        print(f"Found {len(pyc_files)} .pyc files in {path}\n")

        for pyc_path in pyc_files:
            try:
                info = inspect_pyc(pyc_path)
                if args.summary:
                    classes = [c["name"] for c in info["classes"]]
                    funcs = [f["name"] for f in info["functions"]]
                    print(f"{pyc_path}: classes={classes} functions={funcs}")
                else:
                    print_inspection(info, verbose=args.verbose)
            except Exception as e:
                print(f"Error processing {pyc_path}: {e}", file=sys.stderr)
    else:
        if not path.exists():
            print(f"Error: {path} does not exist", file=sys.stderr)
            sys.exit(1)
        if not path.suffix == ".pyc":
            print(f"Warning: {path} does not have .pyc extension", file=sys.stderr)

        try:
            info = inspect_pyc(path)
            print_inspection(info, verbose=args.verbose)
        except Exception as e:
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(1)


if __name__ == "__main__":
    main()
