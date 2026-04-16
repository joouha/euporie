#!/usr/bin/env python
"""Generate .pyi stub files for apptk by merging prompt_toolkit and apptk sources.

This script:
1. Finds all prompt_toolkit modules (lower layer)
2. Finds all apptk override modules (upper layer)
3. For each module, merges type information from both layers
4. Replaces prompt_toolkit types/imports with apptk equivalents
5. Writes .pyi stub files next to the apptk .py files

Usage:
    uv run python scripts/generate_stubs.py [--dry-run] [--verbose] [--module MODULE]
"""

from __future__ import annotations

import argparse
import ast
import importlib.util
import os
import re
import sys
from collections import OrderedDict
from dataclasses import dataclass, field
from pathlib import Path

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

# Root paths
REPO_ROOT = Path(__file__).resolve().parent.parent
APPTK_SRC = REPO_ROOT / "packages" / "apptk" / "src" / "apptk"


def _find_ptk_src() -> Path:
    """Locate prompt_toolkit's source directory programmatically."""
    spec = importlib.util.find_spec("prompt_toolkit")
    if spec is None:
        raise RuntimeError(
            "prompt_toolkit is not installed. "
            "Install it first (e.g. `uv sync`) so the script can locate its source."
        )
    if spec.origin is None:
        raise RuntimeError(
            "prompt_toolkit spec has no origin — cannot determine source path."
        )
    # spec.origin points to prompt_toolkit/__init__.py
    return Path(spec.origin).resolve().parent


PTK_SRC: Path  # Assigned in main() after argument parsing

# The lower (original) package and the upper (override) package names
LOWER_PKG = "prompt_toolkit"
UPPER_PKG = "apptk"

# Modules/patterns to skip
SKIP_PATTERNS = {
    "__pycache__",
    "__modshim__",
    ".mypy_cache",
}

# Known prompt_toolkit -> apptk type mappings for common renames
# These are types where the class name itself changes
EXPLICIT_TYPE_MAP: dict[str, str] = {
    # Add explicit mappings here if class names differ between packages
}


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------


@dataclass
class ImportInfo:
    """Represents a single import statement."""

    module: str  # The module being imported from (for 'from X import Y')
    names: list[tuple[str, str | None]]  # [(name, asname), ...]
    is_from: bool = True  # True for 'from X import Y', False for 'import X'
    is_type_checking: bool = False  # True if inside TYPE_CHECKING block
    level: int = 0  # Relative import level


@dataclass
class MemberInfo:
    """Represents a class member (method, attribute, property)."""

    name: str
    node: ast.AST
    source_lines: list[str]
    is_property: bool = False
    is_classvar: bool = False
    is_method: bool = False
    is_overload: bool = False
    decorators: list[str] = field(default_factory=list)
    order: int = 0  # Preserve definition order


@dataclass
class ClassInfo:
    """Represents a class definition."""

    name: str
    node: ast.ClassDef
    bases: list[str]
    docstring: str | None
    members: OrderedDict[str, list[MemberInfo]]  # name -> [MemberInfo] (overloads)
    type_params: list[str]  # e.g. Generic[_AppResult]
    source_lines: list[str]
    decorators: list[str] = field(default_factory=list)


@dataclass
class FunctionInfo:
    """Represents a module-level function."""

    name: str
    node: ast.FunctionDef | ast.AsyncFunctionDef
    source_lines: list[str]
    decorators: list[str] = field(default_factory=list)
    is_overload: bool = False


@dataclass
class VariableInfo:
    """Represents a module-level variable/constant."""

    name: str
    source_line: str
    annotation: str | None = None


@dataclass
class ModuleInfo:
    """All extracted information from a module."""

    path: Path
    module_name: str  # Dotted module name
    docstring: str | None
    imports: list[ImportInfo]
    type_checking_imports: list[ImportInfo]
    classes: OrderedDict[str, ClassInfo]
    functions: OrderedDict[str, list[FunctionInfo]]  # name -> [overloads]
    variables: OrderedDict[str, VariableInfo]
    all_names: list[str] | None  # __all__ if defined
    source: str


# ---------------------------------------------------------------------------
# AST Helpers
# ---------------------------------------------------------------------------


def get_source_segment(source_lines: list[str], node: ast.AST) -> list[str]:
    """Extract source lines for an AST node."""
    if not hasattr(node, "lineno") or not hasattr(node, "end_lineno"):
        return []
    start = node.lineno - 1
    end = node.end_lineno or node.lineno
    return source_lines[start:end]


def get_decorator_names(node: ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef) -> list[str]:
    """Get decorator names as strings."""
    names = []
    for dec in node.decorator_list:
        if isinstance(dec, ast.Name):
            names.append(dec.id)
        elif isinstance(dec, ast.Attribute) or isinstance(dec, ast.Call):
            names.append(ast.unparse(dec))
        else:
            names.append(ast.unparse(dec))
    return names


def get_docstring_from_node(node: ast.AST) -> str | None:
    """Extract docstring from a class or module node."""
    if isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
        if (
            node.body
            and isinstance(node.body[0], ast.Expr)
            and isinstance(node.body[0].value, ast.Constant)
        ):
            val = node.body[0].value
            if isinstance(val.value, str):
                return val.value
    return None


def has_decorator(node: ast.FunctionDef | ast.AsyncFunctionDef, name: str) -> bool:
    """Check if a function has a specific decorator."""
    for dec in node.decorator_list:
        if isinstance(dec, ast.Name) and dec.id == name:
            return True
        if isinstance(dec, ast.Attribute) and dec.attr == name:
            return True
        if isinstance(dec, ast.Call):
            func = dec.func
            if isinstance(func, ast.Name) and func.id == name:
                return True
            if isinstance(func, ast.Attribute) and func.attr == name:
                return True
    return False


def is_property_node(node: ast.FunctionDef | ast.AsyncFunctionDef) -> bool:
    """Check if a function definition is a property."""
    return has_decorator(node, "property") or any(
        isinstance(dec, ast.Attribute) and dec.attr in ("setter", "deleter", "getter")
        for dec in node.decorator_list
    )


def is_overload_node(node: ast.FunctionDef | ast.AsyncFunctionDef) -> bool:
    """Check if a function definition is an overload."""
    return has_decorator(node, "overload")


def get_class_type_params(node: ast.ClassDef) -> list[str]:
    """Extract Generic type parameters from class bases."""
    params = []
    for base in node.bases:
        unparsed = ast.unparse(base)
        if "Generic[" in unparsed or "Generic [" in unparsed:
            # Extract the type params
            match = re.search(r"Generic\s*\[(.+)\]", unparsed)
            if match:
                params.append(f"Generic[{match.group(1)}]")
    return params


def annotation_to_str(node: ast.AST | None) -> str | None:
    """Convert an annotation AST node to string."""
    if node is None:
        return None
    return ast.unparse(node)


# ---------------------------------------------------------------------------
# Rewriting prompt_toolkit -> apptk
# ---------------------------------------------------------------------------


def rewrite_ptk_references(text: str) -> str:
    """Replace prompt_toolkit references with apptk equivalents in a string."""
    # Replace module references
    text = text.replace("prompt_toolkit.", "apptk.")

    # Replace common import aliases
    text = re.sub(r"\bPtk(\w+)", lambda m: m.group(1), text)

    # Apply explicit type map
    for ptk_name, apptk_name in EXPLICIT_TYPE_MAP.items():
        text = re.sub(rf"\b{re.escape(ptk_name)}\b", apptk_name, text)

    return text


def rewrite_import_module(module: str) -> str:
    """Rewrite a module path from prompt_toolkit to apptk."""
    if module.startswith("prompt_toolkit"):
        return module.replace("prompt_toolkit", "apptk", 1)
    return module


def rewrite_import(imp: ImportInfo) -> ImportInfo:
    """Rewrite an import to use apptk instead of prompt_toolkit."""
    new_module = rewrite_import_module(imp.module)

    # Rewrite imported names - remove Ptk prefix aliases
    new_names = []
    for name, asname in imp.names:
        new_name = rewrite_ptk_references(name)
        new_asname = asname
        # If the name had a Ptk prefix that was used as an alias, drop the alias
        if asname and rewrite_ptk_references(asname) == new_name:
            new_asname = None
        new_names.append((new_name, new_asname))

    return ImportInfo(
        module=new_module,
        names=new_names,
        is_from=imp.is_from,
        is_type_checking=imp.is_type_checking,
        level=imp.level,
    )


# ---------------------------------------------------------------------------
# Module parsing
# ---------------------------------------------------------------------------


def _infer_annotation_from_expr(
    expr: ast.expr,
    param_annotations: dict[str, ast.expr | None],
) -> ast.expr | None:
    """Try to infer a type annotation from an expression and parameter annotations.

    Handles simple cases like:
    - ``param`` -> use param's annotation directly
    - ``param or default`` -> use param's annotation (stripping ``| None``)
    - ``value if cond else other`` -> try the ``value`` branch
    - ``func(param)`` -> use param's annotation as a fallback

    Returns the annotation AST node, or ``None`` if no annotation can be
    inferred.
    """
    # Simple name: self.x = param
    if isinstance(expr, ast.Name) and expr.id in param_annotations:
        return param_annotations[expr.id]

    # BoolOp: self.x = param or default_value
    # The pattern ``param or fallback`` means param could be None and fallback
    # is the non-None default, so the resulting type is the param type without
    # None.  However, stripping None from a Union at the AST level is complex,
    # so we return the param annotation as-is (still useful for stubs).
    if isinstance(expr, ast.BoolOp) and isinstance(expr.op, ast.Or) and expr.values:
        first = expr.values[0]
        if isinstance(first, ast.Name) and first.id in param_annotations:
            return param_annotations[first.id]

    # Ternary: self.x = a if cond else b
    if isinstance(expr, ast.IfExp):
        result = _infer_annotation_from_expr(expr.body, param_annotations)
        if result is not None:
            return result
        return _infer_annotation_from_expr(expr.orelse, param_annotations)

    # Call: self.x = SomeClass(...) or self.x = some_func(param)
    if isinstance(expr, ast.Call):
        # First, try to infer from the first positional arg matching a parameter
        if expr.args:
            first_arg = expr.args[0]
            if isinstance(first_arg, ast.Name) and first_arg.id in param_annotations:
                return param_annotations[first_arg.id]

        # If the callable is a Name that looks like a class (starts with uppercase),
        # use it as the type annotation: self.x = KeyProcessor(...) -> KeyProcessor
        func = expr.func
        if isinstance(func, ast.Name) and func.id[:1].isupper():
            return func
        if isinstance(func, ast.Attribute) and func.attr[:1].isupper():
            return func

    return None


def parse_module(path: Path, module_name: str) -> ModuleInfo:
    """Parse a Python module and extract all type information."""
    source = path.read_text(encoding="utf-8")
    source_lines = source.splitlines(keepends=True)
    tree = ast.parse(source, filename=str(path))

    docstring = get_docstring_from_node(tree)
    imports: list[ImportInfo] = []
    type_checking_imports: list[ImportInfo] = []
    classes: OrderedDict[str, ClassInfo] = OrderedDict()
    functions: OrderedDict[str, list[FunctionInfo]] = OrderedDict()
    variables: OrderedDict[str, VariableInfo] = OrderedDict()
    all_names: list[str] | None = None

    # Track if we're inside a TYPE_CHECKING block
    def process_imports(
        node: ast.ImportFrom | ast.Import, is_type_checking: bool = False
    ) -> None:
        if isinstance(node, ast.ImportFrom):
            module = node.module or ""
            names = [(alias.name, alias.asname) for alias in node.names]
            imp = ImportInfo(
                module=module,
                names=names,
                is_from=True,
                is_type_checking=is_type_checking,
                level=node.level,
            )
        else:
            names = [(alias.name, alias.asname) for alias in node.names]
            imp = ImportInfo(
                module="",
                names=names,
                is_from=False,
                is_type_checking=is_type_checking,
            )

        if is_type_checking:
            type_checking_imports.append(imp)
        else:
            imports.append(imp)

    def process_class(node: ast.ClassDef) -> ClassInfo:
        bases = [ast.unparse(b) for b in node.bases]
        type_params = get_class_type_params(node)
        class_docstring = get_docstring_from_node(node)
        members: OrderedDict[str, list[MemberInfo]] = OrderedDict()
        decorators = get_decorator_names(node)
        class_source = get_source_segment(source_lines, node)

        order_counter = 0
        for item in node.body:
            if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                member_name = item.name
                is_prop = is_property_node(item)
                is_ovl = is_overload_node(item)
                member = MemberInfo(
                    name=member_name,
                    node=item,
                    source_lines=get_source_segment(source_lines, item),
                    is_property=is_prop,
                    is_method=True,
                    is_overload=is_ovl,
                    decorators=get_decorator_names(item),
                    order=order_counter,
                )
                members.setdefault(member_name, []).append(member)
                order_counter += 1

            elif isinstance(item, ast.AnnAssign):
                # Class variable with annotation
                if isinstance(item.target, ast.Name):
                    member_name = item.target.id
                    member = MemberInfo(
                        name=member_name,
                        node=item,
                        source_lines=get_source_segment(source_lines, item),
                        is_classvar=True,
                        order=order_counter,
                    )
                    members.setdefault(member_name, []).append(member)
                    order_counter += 1

            elif isinstance(item, ast.Assign):
                # Simple assignment (e.g. __all__ = [...])
                for target in item.targets:
                    if isinstance(target, ast.Name):
                        member_name = target.id
                        member = MemberInfo(
                            name=member_name,
                            node=item,
                            source_lines=get_source_segment(source_lines, item),
                            order=order_counter,
                        )
                        members.setdefault(member_name, []).append(member)
                        order_counter += 1

        # Extract instance attributes from all methods (self.x = ... and
        # self.x: Type = ... assignments).  We scan __init__ first, then
        # other methods, so that __init__ annotations take precedence.
        init_methods = [
            item for item in node.body
            if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef))
            and item.name == "__init__"
        ]
        other_methods = [
            item for item in node.body
            if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef))
            and item.name != "__init__"
        ]
        for item in init_methods + other_methods:
            # Build a map of parameter name -> annotation
            param_annotations: dict[str, ast.expr | None] = {}
            for arg in item.args.args + item.args.kwonlyargs:
                if arg.arg != "self":
                    param_annotations[arg.arg] = arg.annotation
            if item.args.vararg:
                param_annotations[item.args.vararg.arg] = item.args.vararg.annotation
            if item.args.kwarg:
                param_annotations[item.args.kwarg.arg] = item.args.kwarg.annotation

            # Walk the entire method body (including nested blocks like
            # if/for/while/try) to find self.x assignments.
            for stmt in ast.walk(item):
                if isinstance(stmt, ast.AnnAssign):
                    # self.x: Type = value
                    if (
                        isinstance(stmt.target, ast.Attribute)
                        and isinstance(stmt.target.value, ast.Name)
                        and stmt.target.value.id == "self"
                    ):
                        attr_name = stmt.target.attr
                        if attr_name not in members:
                            ann_str = ast.unparse(stmt.annotation)
                            synthetic_line = f"{attr_name}: {ann_str}"
                            member = MemberInfo(
                                name=attr_name,
                                node=stmt,
                                source_lines=[synthetic_line + "\n"],
                                is_classvar=True,
                                order=order_counter,
                            )
                            members.setdefault(attr_name, []).append(member)
                            order_counter += 1
                elif isinstance(stmt, ast.Assign):
                    # self.x = param  (infer type from param annotation)
                    for target in stmt.targets:
                        if (
                            isinstance(target, ast.Attribute)
                            and isinstance(target.value, ast.Name)
                            and target.value.id == "self"
                        ):
                            attr_name = target.attr
                            if attr_name not in members:
                                # Try to infer type from RHS if it's a simple name matching a parameter
                                ann_node = _infer_annotation_from_expr(
                                    stmt.value, param_annotations
                                )
                                if ann_node is not None:
                                    ann_str = ast.unparse(ann_node)
                                    synthetic_line = f"{attr_name}: {ann_str}"
                                else:
                                    # Fall back to the raw assignment
                                    val_str = ast.unparse(stmt.value)
                                    synthetic_line = f"{attr_name} = {val_str}"
                                member = MemberInfo(
                                    name=attr_name,
                                    node=stmt,
                                    source_lines=[synthetic_line + "\n"],
                                    is_classvar=True,
                                    order=order_counter,
                                )
                                members.setdefault(attr_name, []).append(member)
                                order_counter += 1

        return ClassInfo(
            name=node.name,
            node=node,
            bases=bases,
            docstring=class_docstring,
            members=members,
            type_params=type_params,
            source_lines=class_source,
            decorators=decorators,
        )

    def process_function(node: ast.FunctionDef | ast.AsyncFunctionDef) -> FunctionInfo:
        return FunctionInfo(
            name=node.name,
            node=node,
            source_lines=get_source_segment(source_lines, node),
            decorators=get_decorator_names(node),
            is_overload=is_overload_node(node),
        )

    # Walk top-level statements
    for node in tree.body:
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            process_imports(node, is_type_checking=False)

        elif isinstance(node, ast.If):
            # Check for TYPE_CHECKING block
            test = node.test
            is_tc = False
            if (isinstance(test, ast.Name) and test.id == "TYPE_CHECKING") or (isinstance(test, ast.Attribute) and test.attr == "TYPE_CHECKING"):
                is_tc = True

            if is_tc:
                for sub_node in node.body:
                    if isinstance(sub_node, (ast.Import, ast.ImportFrom)):
                        process_imports(sub_node, is_type_checking=True)
                    elif isinstance(sub_node, ast.Assign):
                        # Type aliases defined in TYPE_CHECKING blocks
                        for target in sub_node.targets:
                            if isinstance(target, ast.Name):
                                line = "".join(
                                    get_source_segment(source_lines, sub_node)
                                ).strip()
                                variables[target.id] = VariableInfo(
                                    name=target.id, source_line=line
                                )
                    elif isinstance(sub_node, ast.AnnAssign):
                        if isinstance(sub_node.target, ast.Name):
                            line = "".join(
                                get_source_segment(source_lines, sub_node)
                            ).strip()
                            ann = annotation_to_str(sub_node.annotation)
                            variables[sub_node.target.id] = VariableInfo(
                                name=sub_node.target.id,
                                source_line=line,
                                annotation=ann,
                            )
                    elif isinstance(sub_node, ast.ClassDef):
                        # Classes defined in TYPE_CHECKING blocks (e.g. Protocols)
                        classes[sub_node.name] = process_class(sub_node)
            # Also process non-TYPE_CHECKING if blocks for imports at top level
            # (rare but possible)

        elif isinstance(node, ast.ClassDef):
            classes[node.name] = process_class(node)

        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            func_info = process_function(node)
            functions.setdefault(node.name, []).append(func_info)

        elif isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name):
                    if target.id == "__all__":
                        # Extract __all__ list
                        if isinstance(node.value, (ast.List, ast.Tuple)):
                            all_names = []
                            for elt in node.value.elts:
                                if isinstance(elt, ast.Constant) and isinstance(
                                    elt.value, str
                                ):
                                    all_names.append(elt.value)
                    else:
                        line = "".join(get_source_segment(source_lines, node)).rstrip()
                        variables[target.id] = VariableInfo(
                            name=target.id, source_line=line
                        )

        elif isinstance(node, ast.AnnAssign):
            if isinstance(node.target, ast.Name):
                line = "".join(get_source_segment(source_lines, node)).rstrip()
                ann = annotation_to_str(node.annotation)
                variables[node.target.id] = VariableInfo(
                    name=node.target.id, source_line=line, annotation=ann
                )

    return ModuleInfo(
        path=path,
        module_name=module_name,
        docstring=docstring,
        imports=imports,
        type_checking_imports=type_checking_imports,
        classes=classes,
        functions=functions,
        variables=variables,
        all_names=all_names,
        source=source,
    )


# ---------------------------------------------------------------------------
# Module discovery
# ---------------------------------------------------------------------------


def discover_modules(src_dir: Path, pkg_name: str) -> dict[str, Path]:
    """Discover all Python modules under a source directory.

    Returns a dict mapping relative module names (e.g. 'application.application')
    to their file paths.
    """
    modules: dict[str, Path] = {}

    for root, dirs, files in os.walk(src_dir):
        # Skip unwanted directories
        dirs[:] = [d for d in dirs if d not in SKIP_PATTERNS and not d.startswith(".")]

        root_path = Path(root)
        rel_path = root_path.relative_to(src_dir)

        for fname in sorted(files):
            if not fname.endswith(".py"):
                continue
            if fname.startswith("."):
                continue

            fpath = root_path / fname

            # Build module name
            if fname == "__init__.py":
                parts = rel_path.parts
            else:
                parts = (*rel_path.parts, fname[:-3])

            if not parts:
                # This is the package __init__.py
                module_name = ""
            else:
                module_name = ".".join(parts)

            modules[module_name] = fpath

    return modules


# ---------------------------------------------------------------------------
# Stub generation
# ---------------------------------------------------------------------------


# Decorators that should be preserved in stubs per the typing style guide.
# All other decorators should have their effects incorporated into the types.
_STUB_ALLOWED_DECORATORS = {
    "classmethod",
    "staticmethod",
    "property",
    "abc.abstractmethod",
    "abstractmethod",
    "dataclasses.dataclass",
    "dataclass",
    "typing.dataclass_transform",
    "dataclass_transform",
    "warnings.deprecated",
    "typing_extensions.deprecated",
    "deprecated",
    "typing.type_check_only",
    "type_check_only",
    "overload",
    "typing.overload",
}

# Property setter/deleter patterns
_STUB_PROPERTY_PATTERNS = {".setter", ".deleter"}


def _is_allowed_stub_decorator(dec: str) -> bool:
    """Check if a decorator should be preserved in a stub file."""
    if dec in _STUB_ALLOWED_DECORATORS:
        return True
    # Allow property.setter, property.deleter, name.setter, name.deleter
    for pattern in _STUB_PROPERTY_PATTERNS:
        if dec.endswith(pattern):
            return True
    return False


def _decorator_is_class(dec: str) -> str | None:
    """Check if a decorator is a class instantiation (constructs an instance).

    When a class is used as a decorator (e.g. ``@Condition``), the decorated
    function is passed to the class constructor and the result is an instance
    of that class.

    Returns the class name if the decorator looks like a class instantiation,
    or ``None`` otherwise.  A decorator is considered a class if its
    unqualified name starts with an uppercase letter and it is not in the
    set of allowed stub decorators (which are known non-class decorators
    that happen to start with uppercase, if any).
    """
    # Strip any call syntax: @SomeClass(...) -> SomeClass
    base = dec.split("(")[0]
    # Get the unqualified name (last component of dotted path)
    simple_name = base.rsplit(".", 1)[-1]
    if simple_name and simple_name[0].isupper() and not _is_allowed_stub_decorator(dec):
        return base
    return None


def _transform_return_type_for_decorator(
    dec: str,
    return_annotation: ast.expr | None,
    is_async: bool,
) -> ast.expr | None:
    """Transform a return type to incorporate the effect of a removed decorator.

    For @contextmanager, AsyncGenerator[T] / Generator[T] -> AbstractContextManager[T]
    For @asynccontextmanager, AsyncGenerator[T] -> AbstractAsyncContextManager[T]
    """
    if return_annotation is None:
        return None

    ret_str = ast.unparse(return_annotation)

    if dec in ("contextmanager", "contextlib.contextmanager"):
        # Generator[T, ...] or Generator[T] -> AbstractContextManager[T]
        match = re.match(r"Generator\[(.+?)(?:,\s*None(?:,\s*None)?)?\]$", ret_str)
        if match:
            yield_type = match.group(1)
            new_ret = f"AbstractContextManager[{yield_type}]"
            return ast.parse(new_ret, mode="eval").body
        # Iterator[T] -> AbstractContextManager[T]
        match = re.match(r"Iterator\[(.+)\]$", ret_str)
        if match:
            yield_type = match.group(1)
            new_ret = f"AbstractContextManager[{yield_type}]"
            return ast.parse(new_ret, mode="eval").body

    if dec in ("asynccontextmanager", "contextlib.asynccontextmanager"):
        # AsyncGenerator[T, ...] or AsyncGenerator[T] -> AbstractAsyncContextManager[T]
        match = re.match(r"AsyncGenerator\[(.+?)(?:,\s*None)?\]$", ret_str)
        if match:
            yield_type = match.group(1)
            new_ret = f"AbstractAsyncContextManager[{yield_type}]"
            return ast.parse(new_ret, mode="eval").body
        # AsyncIterator[T] -> AbstractAsyncContextManager[T]
        match = re.match(r"AsyncIterator\[(.+)\]$", ret_str)
        if match:
            yield_type = match.group(1)
            new_ret = f"AbstractAsyncContextManager[{yield_type}]"
            return ast.parse(new_ret, mode="eval").body

    return return_annotation


def format_function_stub(
    func_node: ast.FunctionDef | ast.AsyncFunctionDef,
    decorators: list[str],
    indent: str = "",
    is_method: bool = False,
) -> list[str]:
    """Format a function/method as a stub definition."""
    lines: list[str] = []

    # If the function is decorated with a class (e.g. @Condition), it becomes
    # an instance of that class — emit as a variable declaration instead of a
    # function signature.
    if not is_method:
        for dec in decorators:
            cls_name = _decorator_is_class(dec)
            if cls_name is not None:
                lines.append(f"{indent}{func_node.name}: {rewrite_ptk_references(cls_name)}")
                return lines

    # Track removed decorators so we can transform the return type
    is_async = isinstance(func_node, ast.AsyncFunctionDef)
    effective_return = func_node.returns
    removed_decorators: list[str] = []

    for dec in decorators:
        if _is_allowed_stub_decorator(dec):
            pass  # will be emitted below
        else:
            removed_decorators.append(dec)

    # Transform return type for removed decorators
    for dec in removed_decorators:
        effective_return = _transform_return_type_for_decorator(
            dec, effective_return, is_async
        )

    # Decorators — only allowed ones
    for dec in decorators:
        if _is_allowed_stub_decorator(dec):
            lines.append(f"{indent}@{dec}")

    # Function signature
    is_async = isinstance(func_node, ast.AsyncFunctionDef)
    prefix = "async def" if is_async else "def"

    # Build argument string
    args = func_node.args
    arg_parts: list[str] = []

    # Positional-only args
    posonlyargs = getattr(args, "posonlyargs", [])
    defaults_offset = len(args.args) - len(args.defaults)
    posonlydefaults_offset = len(posonlyargs) - max(
        0, len(args.defaults) - len(args.args)
    )

    all_positional = list(posonlyargs) + list(args.args)
    total_positional = len(all_positional)
    total_defaults = len(args.defaults)
    first_default_idx = total_positional - total_defaults

    for i, arg in enumerate(all_positional):
        ann = f": {rewrite_ptk_references(ast.unparse(arg.annotation))}" if arg.annotation else ""
        default_idx = i - first_default_idx
        if default_idx >= 0 and default_idx < len(args.defaults):
            default_val = ast.unparse(args.defaults[default_idx])
            # In stubs, use ... for complex defaults
            if len(default_val) > 30 or "\n" in default_val:
                default_val = "..."
            default = f" = {rewrite_ptk_references(default_val)}"
        else:
            default = ""
        arg_parts.append(f"{arg.arg}{ann}{default}")

        # Insert / after positional-only args
        if i == len(posonlyargs) - 1 and posonlyargs:
            arg_parts.append("/")

    # *args
    if args.vararg:
        ann = (
            f": {rewrite_ptk_references(ast.unparse(args.vararg.annotation))}"
            if args.vararg.annotation
            else ""
        )
        arg_parts.append(f"*{args.vararg.arg}{ann}")
    elif args.kwonlyargs:
        arg_parts.append("*")

    # Keyword-only args
    for i, arg in enumerate(args.kwonlyargs):
        ann = f": {rewrite_ptk_references(ast.unparse(arg.annotation))}" if arg.annotation else ""
        if i < len(args.kw_defaults) and args.kw_defaults[i] is not None:
            default_val = ast.unparse(args.kw_defaults[i])
            if len(default_val) > 30 or "\n" in default_val:
                default_val = "..."
            default = f" = {rewrite_ptk_references(default_val)}"
        else:
            default = ""
        arg_parts.append(f"{arg.arg}{ann}{default}")

    # **kwargs
    if args.kwarg:
        ann = (
            f": {rewrite_ptk_references(ast.unparse(args.kwarg.annotation))}"
            if args.kwarg.annotation
            else ""
        )
        arg_parts.append(f"**{args.kwarg.arg}{ann}")

    # Return annotation
    ret = ""
    if effective_return is not None:
        ret = f" -> {rewrite_ptk_references(ast.unparse(effective_return))}"

    # Format the signature
    args_str = ", ".join(arg_parts)
    sig = f"{indent}{prefix} {func_node.name}({args_str}){ret}"

    # Check if we need multi-line
    if len(sig) > 88:
        lines.append(f"{indent}{prefix} {func_node.name}(")
        for j, part in enumerate(arg_parts):
            comma = "," if j < len(arg_parts) - 1 else ","
            lines.append(f"{indent}    {part}{comma}")
        lines.append(f"{indent}){ret}:")
    else:
        lines.append(f"{sig}:")

    lines.append(f"{indent}    ...")

    return lines


def _is_enum_class(cls: ClassInfo) -> bool:
    """Check if a class is an enum (inherits from Enum or similar)."""
    enum_bases = {"Enum", "IntEnum", "StrEnum", "Flag", "IntFlag", "enum.Enum",
                  "enum.IntEnum", "enum.StrEnum", "enum.Flag", "enum.IntFlag"}
    for base in cls.bases:
        if base in enum_bases or base.endswith(".Enum") or base.endswith(".IntEnum"):
            return True
    return False


def format_class_stub(
    cls: ClassInfo,
    indent: str = "",
) -> list[str]:
    """Format a class as a stub definition."""
    lines: list[str] = []

    # Decorators
    for dec in cls.decorators:
        lines.append(f"{indent}@{dec}")

    # Class definition line
    bases = []
    for tp in cls.type_params:
        bases.append(rewrite_ptk_references(tp))

    # Add non-Generic bases (rewritten)
    for base in cls.bases:
        if "Generic" not in base:
            rewritten = rewrite_ptk_references(base)
            # Skip prompt_toolkit parent classes - we flatten them
            # Only keep bases that are not from prompt_toolkit
            if not rewritten.startswith("apptk.") or "." not in rewritten:
                # Keep simple bases and apptk bases
                if rewritten not in [b for b in bases]:
                    bases.append(rewritten)

    # Detect unbound type variables used in members and add Generic[...] if needed
    has_generic = any("Generic[" in b for b in bases)
    if not has_generic:
        # Collect type variable names used in member annotations
        cls_source = "\n".join("".join(m.source_lines) for ms in cls.members.values() for m in ms)
        cls_source = rewrite_ptk_references(cls_source)
        # Check for common type variable patterns like _AppResult, _T, etc.
        used_tvars = set()
        for var_name in ("_AppResult", "_T", "_U", "_KT", "_VT"):
            if re.search(rf"\b{re.escape(var_name)}\b", cls_source):
                used_tvars.add(var_name)
        if used_tvars:
            tvars_str = ", ".join(sorted(used_tvars))
            bases.insert(0, f"Generic[{tvars_str}]")

    if bases:
        bases_str = ", ".join(bases)
        lines.append(f"{indent}class {cls.name}({bases_str}):")
    else:
        lines.append(f"{indent}class {cls.name}:")

    # Members
    has_members = False

    # First: class variables / annotations
    for name, member_list in cls.members.items():
        for member in member_list:
            if member.is_classvar or (
                not member.is_method and not member.is_property
            ):
                src = "".join(member.source_lines).strip()
                src = rewrite_ptk_references(src)
                lines.append(f"{indent}    {src}")
                has_members = True

    # Then: methods and properties
    for name, member_list in cls.members.items():
        for member in member_list:
            if member.is_method or member.is_property:
                assert isinstance(
                    member.node, (ast.FunctionDef, ast.AsyncFunctionDef)
                )
                method_lines = format_function_stub(
                    member.node,
                    member.decorators,
                    indent=f"{indent}    ",
                    is_method=True,
                )
                lines.extend(method_lines)
                has_members = True

    if not has_members:
        lines.append(f"{indent}    ...")

    return lines


def merge_class_info(
    lower_cls: ClassInfo | None,
    upper_cls: ClassInfo | None,
) -> ClassInfo:
    """Merge a lower (prompt_toolkit) class with an upper (apptk) override.

    The upper class's members take precedence. Members from the lower class
    that are not overridden are included. The result has no prompt_toolkit
    base classes.
    """
    if lower_cls is None and upper_cls is not None:
        return upper_cls
    if upper_cls is None and lower_cls is not None:
        return lower_cls
    assert lower_cls is not None and upper_cls is not None

    # Use upper's metadata as primary
    merged_members: OrderedDict[str, list[MemberInfo]] = OrderedDict()

    # Start with lower members
    for name, members in lower_cls.members.items():
        merged_members[name] = list(members)

    # Override/add with upper members
    for name, members in upper_cls.members.items():
        merged_members[name] = list(members)

    # Merge type params
    type_params = upper_cls.type_params or lower_cls.type_params

    # Use upper's docstring if available, else lower's
    docstring = upper_cls.docstring or lower_cls.docstring

    # Merge bases: keep Generic params, drop ptk parent classes
    bases = []
    for tp in type_params:
        bases.append(tp)

    # Add any non-ptk, non-Generic bases from upper
    for base in upper_cls.bases:
        if "Generic" not in base and not _is_ptk_base(base):
            if base not in bases:
                bases.append(base)

    # Merge decorators (prefer upper)
    decorators = upper_cls.decorators or lower_cls.decorators

    return ClassInfo(
        name=upper_cls.name,
        node=upper_cls.node,
        bases=bases,
        docstring=docstring,
        members=merged_members,
        type_params=type_params,
        source_lines=upper_cls.source_lines,
        decorators=decorators,
    )


def _is_ptk_base(base: str) -> bool:
    """Check if a base class reference is a prompt_toolkit class."""
    return (
        base.startswith("PtkApplication")
        or base.startswith("Ptk")
        or base.startswith("prompt_toolkit.")
        or base.startswith("_Ptk")
    )


def merge_imports(
    lower_imports: list[ImportInfo],
    upper_imports: list[ImportInfo],
) -> list[ImportInfo]:
    """Merge imports from lower and upper modules.

    Upper imports take precedence. All prompt_toolkit imports are rewritten
    to apptk.
    """
    # Track by (module, level, name) to deduplicate
    seen: dict[tuple[str, int, str], ImportInfo] = {}
    result: list[ImportInfo] = []

    def add_import(imp: ImportInfo) -> None:
        rewritten = rewrite_import(imp)
        for name, asname in rewritten.names:
            key = (rewritten.module, rewritten.level, name)
            if key not in seen:
                seen[key] = ImportInfo(
                    module=rewritten.module,
                    names=[(name, asname)],
                    is_from=rewritten.is_from,
                    is_type_checking=rewritten.is_type_checking,
                    level=rewritten.level,
                )

    # Add lower imports first
    for imp in lower_imports:
        add_import(imp)

    # Upper imports override
    for imp in upper_imports:
        add_import(imp)

    # Group by (module, level) for cleaner output
    by_module: OrderedDict[tuple[str, int], list[tuple[str, str | None]]] = OrderedDict()
    tc_by_module: OrderedDict[tuple[str, int], list[tuple[str, str | None]]] = OrderedDict()

    for key, imp in seen.items():
        target = tc_by_module if imp.is_type_checking else by_module
        mod_key = (imp.module, imp.level)
        for name, asname in imp.names:
            target.setdefault(mod_key, []).append((name, asname))

    for (mod, level), names in by_module.items():
        # Deduplicate names
        unique_names = list(dict.fromkeys(names))
        result.append(
            ImportInfo(
                module=mod,
                names=unique_names,
                is_from=bool(mod) or level > 0,
                is_type_checking=False,
                level=level,
            )
        )

    for (mod, level), names in tc_by_module.items():
        unique_names = list(dict.fromkeys(names))
        result.append(
            ImportInfo(
                module=mod,
                names=unique_names,
                is_from=bool(mod) or level > 0,
                is_type_checking=True,
                level=level,
            )
        )

    return result


def format_import(imp: ImportInfo) -> str:
    """Format an ImportInfo as a source line."""
    if not imp.is_from:
        parts = []
        for name, asname in imp.names:
            if asname:
                parts.append(f"{name} as {asname}")
            else:
                parts.append(name)
        return f"import {', '.join(parts)}"

    parts = []
    for name, asname in imp.names:
        if asname:
            parts.append(f"{name} as {asname}")
        else:
            parts.append(name)

    names_str = ", ".join(parts)
    dots = "." * imp.level
    module_str = f"{dots}{imp.module}" if imp.module else dots
    line = f"from {module_str} import {names_str}"

    if len(line) > 88:
        # Multi-line import
        lines = [f"from {module_str} import ("]
        for j, part in enumerate(parts):
            comma = "," if j < len(parts) - 1 else ","
            lines.append(f"    {part}{comma}")
        lines.append(")")
        return "\n".join(lines)

    return line


def should_skip_import(imp: ImportInfo) -> bool:
    """Check if an import should be skipped in the stub."""
    # Skip __future__ imports (we'll add our own)
    if imp.module == "__future__":
        return True
    # Skip imports of implementation details
    for name, _ in imp.names:
        if name.startswith("_") and not name.startswith("__"):
            # Keep _AppResult and similar type vars
            if not any(
                c.isupper() for c in name[1:]
            ):
                continue
    return False


def filter_stub_imports(
    imports: list[ImportInfo],
    current_module: str = "",
) -> list[ImportInfo]:
    """Filter imports appropriate for a stub file.

    Args:
        imports: The imports to filter.
        current_module: The fully-qualified module name of the stub being
            generated (e.g. ``apptk.application.application``).  Imports
            from this module are dropped to avoid self-imports.
    """
    result = []
    for imp in imports:
        if imp.module == "__future__":
            continue
        # Skip internal implementation imports
        if imp.module.startswith("_") and not imp.module.startswith("__"):
            continue
        # Skip self-imports (importing from the module we are generating)
        if current_module and imp.is_from and imp.level == 0:
            fq = imp.module
            if fq == current_module:
                continue
        result.append(imp)
    return result


def generate_stub(
    lower_info: ModuleInfo | None,
    upper_info: ModuleInfo | None,
    module_rel_name: str,
) -> str:
    """Generate a .pyi stub file content by merging lower and upper module info."""
    lines: list[str] = []

    # Determine the primary module info
    primary = upper_info or lower_info
    assert primary is not None

    # Determine the fully-qualified module name for self-import filtering.
    # Stub files must not use ``from __future__ import annotations`` or
    # include docstrings per the typing style guide.
    pkg_module = f"{UPPER_PKG}.{module_rel_name}" if module_rel_name else UPPER_PKG

    # Collect and merge imports
    lower_imports = lower_info.imports + lower_info.type_checking_imports if lower_info else []
    upper_imports = upper_info.imports + upper_info.type_checking_imports if upper_info else []

    all_imports = merge_imports(lower_imports, upper_imports)
    all_imports = filter_stub_imports(all_imports, current_module=pkg_module)

    # Separate regular and TYPE_CHECKING imports
    regular_imports = [i for i in all_imports if not i.is_type_checking]
    tc_imports = [i for i in all_imports if i.is_type_checking]

    # Group regular imports: stdlib, third-party (apptk), local
    stdlib_imports = []
    apptk_imports = []
    other_imports = []

    stdlib_modules = {
        "asyncio", "contextvars", "os", "re", "signal", "sys", "threading",
        "time", "typing", "collections", "collections.abc", "subprocess",
        "traceback", "contextlib", "io", "logging", "struct", "marshal",
        "types", "importlib", "pathlib", "functools", "abc", "enum",
        "dataclasses", "copy", "weakref", "math", "json", "hashlib",
    }

    for imp in regular_imports:
        mod_root = imp.module.split(".")[0] if imp.module else ""
        if mod_root in stdlib_modules or (not imp.is_from and any(n[0].split(".")[0] in stdlib_modules for n in imp.names)):
            stdlib_imports.append(imp)
        elif mod_root == "apptk" or mod_root == "prompt_toolkit":
            apptk_imports.append(imp)
        else:
            other_imports.append(imp)

    # Write imports
    for imp in stdlib_imports:
        lines.append(format_import(imp))
    if stdlib_imports:
        lines.append("")

    for imp in other_imports:
        lines.append(format_import(imp))
    if other_imports:
        lines.append("")

    for imp in apptk_imports:
        lines.append(format_import(imp))
    if apptk_imports:
        lines.append("")

    # TYPE_CHECKING imports
    if tc_imports:
        lines.append("if TYPE_CHECKING:")
        for imp in tc_imports:
            formatted = format_import(imp)
            for fl in formatted.splitlines():
                lines.append(f"    {fl}")
        lines.append("")

    # Module-level variables
    lower_vars = lower_info.variables if lower_info else OrderedDict()
    upper_vars = upper_info.variables if upper_info else OrderedDict()
    merged_vars = OrderedDict(lower_vars)
    merged_vars.update(upper_vars)

    for name, var in merged_vars.items():
        if name.startswith("_") and not name.startswith("__"):
            # Include type vars and similar
            src = rewrite_ptk_references(var.source_line)
            lines.append(src)
        elif not name.startswith("_"):
            src = rewrite_ptk_references(var.source_line)
            lines.append(src)

    # __all__ — merge from both modules like modshim does at runtime:
    # lower items first, then new items from upper (preserving order, no dupes)
    all_names = None
    lower_all = lower_info.all_names if lower_info else None
    upper_all = upper_info.all_names if upper_info else None
    if lower_all is not None and upper_all is not None:
        all_names = list(lower_all)
        for item in upper_all:
            if item not in all_names:
                all_names.append(item)
    elif upper_all is not None:
        all_names = upper_all
    elif lower_all is not None:
        all_names = lower_all

    if all_names is not None:
        lines.append("")
        lines.append("__all__ = [")
        for name in all_names:
            lines.append(f'    "{name}",')
        lines.append("]")

    lines.append("")

    # Module-level functions
    lower_funcs = lower_info.functions if lower_info else OrderedDict()
    upper_funcs = upper_info.functions if upper_info else OrderedDict()
    merged_funcs: OrderedDict[str, list[FunctionInfo]] = OrderedDict(lower_funcs)
    merged_funcs.update(upper_funcs)

    for name, func_list in merged_funcs.items():
        # Skip private functions in stubs (keep dunder)
        if name.startswith("_") and not name.startswith("__"):
            continue
        for func in func_list:
            func_lines = format_function_stub(
                func.node, func.decorators, indent=""
            )
            lines.extend(func_lines)

    # Classes
    lower_classes = lower_info.classes if lower_info else OrderedDict()
    upper_classes = upper_info.classes if upper_info else OrderedDict()

    # Determine class order: lower first, then upper additions
    all_class_names = list(lower_classes.keys())
    for name in upper_classes:
        if name not in all_class_names:
            all_class_names.append(name)

    for cls_name in all_class_names:
        lower_cls = lower_classes.get(cls_name)
        upper_cls = upper_classes.get(cls_name)

        # Skip private classes (keep those starting with single underscore
        # if they appear in __all__ or are used as type annotations)
        if cls_name.startswith("__"):
            continue

        merged_cls = merge_class_info(lower_cls, upper_cls)
        cls_lines = format_class_stub(merged_cls)
        lines.extend(cls_lines)
        lines.append("")

    # Clean up trailing whitespace and ensure single trailing newline
    result = "\n".join(line.rstrip() for line in lines)
    result = result.rstrip() + "\n"

    # Auto-add imports for AbstractContextManager / AbstractAsyncContextManager
    # if they appear in the stub but aren't already imported.
    needs_acm = "AbstractContextManager" in result and "import AbstractContextManager" not in result
    needs_aacm = "AbstractAsyncContextManager" in result and "import AbstractAsyncContextManager" not in result
    if needs_acm or needs_aacm:
        names_to_add = []
        if needs_acm:
            names_to_add.append("AbstractContextManager")
        if needs_aacm:
            names_to_add.append("AbstractAsyncContextManager")
        import_line = f"from contextlib import {', '.join(names_to_add)}"
        # Insert at the beginning of the file (before the first import)
        result_lines = result.splitlines(keepends=True)
        insert_idx = None
        for i, line in enumerate(result_lines):
            if line.startswith("import ") or line.startswith("from "):
                insert_idx = i
                break
        if insert_idx is not None:
            result_lines.insert(insert_idx, import_line + "\n")
            result = "".join(result_lines)

    return result


# ---------------------------------------------------------------------------
# Main logic
# ---------------------------------------------------------------------------


def find_matching_modules(
    ptk_modules: dict[str, Path],
    apptk_modules: dict[str, Path],
) -> list[tuple[str, Path | None, Path | None]]:
    """Find all modules that need stubs.

    Returns list of (relative_module_name, ptk_path, apptk_path).
    """
    all_module_names = sorted(set(ptk_modules.keys()) | set(apptk_modules.keys()))
    result = []

    for mod_name in all_module_names:
        ptk_path = ptk_modules.get(mod_name)
        apptk_path = apptk_modules.get(mod_name)
        result.append((mod_name, ptk_path, apptk_path))

    return result


def compute_stub_path(module_rel_name: str) -> Path:
    """Compute the output .pyi path for a module."""
    if not module_rel_name:
        return APPTK_SRC / "__init__.pyi"

    parts = module_rel_name.split(".")
    # Check if this is a package (has __init__.py)
    pkg_path = APPTK_SRC / Path(*parts) / "__init__.py"
    mod_path = APPTK_SRC / Path(*parts[:-1]) / f"{parts[-1]}.py" if len(parts) > 1 else APPTK_SRC / f"{parts[0]}.py"

    if pkg_path.exists():
        return APPTK_SRC / Path(*parts) / "__init__.pyi"
    else:
        if len(parts) > 1:
            return APPTK_SRC / Path(*parts[:-1]) / f"{parts[-1]}.pyi"
        else:
            return APPTK_SRC / f"{parts[0]}.pyi"


def main() -> None:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Generate .pyi stub files for apptk by merging with prompt_toolkit"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print stub contents instead of writing files",
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Print progress information",
    )
    parser.add_argument(
        "--module", "-m",
        type=str,
        default=None,
        help="Only generate stub for a specific module (e.g. 'application.application')",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default=None,
        help="Output directory for stubs (default: alongside apptk source)",
    )
    args = parser.parse_args()

    global PTK_SRC
    try:
        PTK_SRC = _find_ptk_src()
    except RuntimeError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

    if args.verbose:
        print(f"prompt_toolkit source: {PTK_SRC}")

    if not PTK_SRC.exists():
        print(f"Error: prompt_toolkit source not found at {PTK_SRC}", file=sys.stderr)
        sys.exit(1)

    if not APPTK_SRC.exists():
        print(f"Error: apptk source not found at {APPTK_SRC}", file=sys.stderr)
        sys.exit(1)

    # Discover modules
    ptk_modules = discover_modules(PTK_SRC, LOWER_PKG)
    apptk_modules = discover_modules(APPTK_SRC, UPPER_PKG)

    if args.verbose:
        print(f"Found {len(ptk_modules)} prompt_toolkit modules")
        print(f"Found {len(apptk_modules)} apptk modules")

    # Find matching modules
    matches = find_matching_modules(ptk_modules, apptk_modules)

    if args.module:
        # Allow fully-qualified names like 'apptk.clipboard' or
        # 'prompt_toolkit.application.application' — strip the package prefix
        # to get the relative module name used in the discovery dict.
        filter_name = args.module
        for prefix in (f"{UPPER_PKG}.", f"{LOWER_PKG}."):
            if filter_name.startswith(prefix):
                filter_name = filter_name[len(prefix):]
                break
        matches = [(m, p, a) for m, p, a in matches if m == filter_name]
        if not matches:
            print(
                f"Error: module '{args.module}' (resolved to '{filter_name}') not found",
                file=sys.stderr,
            )
            sys.exit(1)

    generated = 0
    skipped = 0
    errors = 0

    for module_rel_name, ptk_path, apptk_path in matches:
        # Skip modules that are only in apptk and have no ptk counterpart
        # (they don't need merged stubs, just regular type checking)
        # But we DO want stubs for ptk-only modules (re-exported with apptk types)
        # and for modules that exist in both

        if args.verbose:
            status = []
            if ptk_path:
                status.append("ptk")
            if apptk_path:
                status.append("apptk")
            print(f"  Processing {module_rel_name or '<root>'} [{'+'.join(status)}]")

        try:
            lower_info = parse_module(ptk_path, f"{LOWER_PKG}.{module_rel_name}") if ptk_path else None
            upper_info = parse_module(apptk_path, f"{UPPER_PKG}.{module_rel_name}") if apptk_path else None

            # Skip if only apptk module exists (no merging needed)
            if lower_info is None and upper_info is not None:
                if args.verbose:
                    print("    Skipping (apptk-only, no merge needed)")
                skipped += 1
                continue

            stub_content = generate_stub(lower_info, upper_info, module_rel_name)

            # Determine output path
            if args.output_dir:
                out_base = Path(args.output_dir)
            else:
                out_base = APPTK_SRC

            stub_path = compute_stub_path(module_rel_name)
            if args.output_dir:
                # Rebase to output dir
                rel = stub_path.relative_to(APPTK_SRC)
                stub_path = out_base / rel

            if args.dry_run:
                print(f"\n{'=' * 60}")
                print(f"# {stub_path}")
                print(f"{'=' * 60}")
                print(stub_content)
            else:
                stub_path.parent.mkdir(parents=True, exist_ok=True)
                stub_path.write_text(stub_content, encoding="utf-8")
                if args.verbose:
                    print(f"    Wrote {stub_path}")

            generated += 1

        except Exception as e:
            print(f"  Error processing {module_rel_name}: {e}", file=sys.stderr)
            if args.verbose:
                import traceback
                traceback.print_exc()
            errors += 1

    print(f"\nDone: {generated} stubs generated, {skipped} skipped, {errors} errors")


if __name__ == "__main__":
    main()
