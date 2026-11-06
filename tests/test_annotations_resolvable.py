"""注解可解析性回归测试(静态).

背景: Python 3.14 起函数注解是惰性求值的(PEP 649), 所以「注解里直接引用了只在
``TYPE_CHECKING`` 下导入的名字」这种错误在 3.14 上**导入期不会暴露**, 要到
3.12 / 3.13 创建函数/类时才抛 ``NameError``。实际踩过一次: ``SceneApi.build_reply``
把 ``PreparedReply`` 当返回值, 本地 3.14 全绿, CI 的 3.12 直接 collect 失败。

因此这里不复用 ``typing.get_type_hints``(它在 3.14 上同样是惰性的, 也会把
继承自第三方基类的注解一起扫进来), 而是用 AST 静态复现 3.12 的求值规则:

- 模块若写了 ``from __future__ import annotations``, 注解全部变成字符串, 跳过;
- 否则, 每个**非字符串字面量**的注解, 其中引用的名字必须在模块顶层可解析
  (模块级 import / 赋值 / 类名 / 内置名), 且不能只存在于 ``if TYPE_CHECKING`` 里。
"""

import ast
import builtins
from pathlib import Path

import pytest

# 三个发行包的源码根目录
SRC_ROOTS = [
    Path(__file__).resolve().parent.parent / "packages" / "qqbotsdk-base" / "src",
    Path(__file__).resolve().parent.parent / "packages" / "qqbotsdk" / "src",
    Path(__file__).resolve().parent.parent / "packages" / "qqbotsdk-guild" / "src",
]


def _source_files() -> list[Path]:
    files: list[Path] = []
    for root in SRC_ROOTS:
        if root.is_dir():
            files.extend(sorted(root.rglob("*.py")))
    return files


def _module_level_names(tree: ast.Module) -> set[str]:
    """收集模块顶层可解析的名字, 跳过 ``if TYPE_CHECKING`` 块."""
    names: set[str] = set()

    def visit(stmts: list[ast.stmt]) -> None:
        for node in stmts:
            if isinstance(node, ast.Import):
                for alias in node.names:
                    names.add(alias.asname or alias.name.split(".")[0])
            elif isinstance(node, ast.ImportFrom):
                for alias in node.names:
                    names.add(alias.asname or alias.name)
            elif isinstance(
                node, ast.ClassDef | ast.FunctionDef | ast.AsyncFunctionDef
            ):
                names.add(node.name)
            elif isinstance(node, ast.TypeAlias):
                # PEP 695: `type X = ...`
                if isinstance(node.name, ast.Name):
                    names.add(node.name.id)
            elif isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name):
                        names.add(target.id)
            elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
                names.add(node.target.id)
            elif isinstance(node, ast.If):
                # if TYPE_CHECKING: 里的导入运行时不存在, 不能算作可解析
                if _is_type_checking_test(node.test):
                    continue
                visit(node.body)
                visit(node.orelse)
            elif isinstance(node, ast.Try):
                visit(node.body)
                visit(node.orelse)
                visit(node.finalbody)

    visit(tree.body)
    return names


def _is_type_checking_test(test: ast.expr) -> bool:
    """判断 ``if`` 条件是不是 ``TYPE_CHECKING`` / ``typing.TYPE_CHECKING``."""
    if isinstance(test, ast.Name):
        return test.id == "TYPE_CHECKING"
    if isinstance(test, ast.Attribute):
        return test.attr == "TYPE_CHECKING"
    return False


def _annotation_nodes(tree: ast.Module) -> list[ast.expr]:
    """收集所有**非字符串字面量**的注解表达式."""
    found: list[ast.expr] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.AnnAssign | ast.arg):
            annotation = node.annotation
            if annotation is None:
                continue
            if isinstance(annotation, ast.Constant) and isinstance(
                annotation.value, str
            ):
                # 显式加引号的前向引用不会被立即求值, 属于合法写法
                continue
            found.append(annotation)
        elif isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
            returns = node.returns
            if returns is not None and not (
                isinstance(returns, ast.Constant) and isinstance(returns.value, str)
            ):
                found.append(returns)
    return found


def _used_names(annotation: ast.expr) -> set[str]:
    """注解表达式里引用到的名字(不含属性访问的右侧)."""
    names: set[str] = set()
    for node in ast.walk(annotation):
        if isinstance(node, ast.Name):
            names.add(node.id)
        elif isinstance(node, ast.Attribute):
            # 只关心 a.b 里的 a
            root = node
            while isinstance(root, ast.Attribute):
                root = root.value
            if isinstance(root, ast.Name):
                names.add(root.id)
    return names


def _has_future_annotations(tree: ast.Module) -> bool:
    for node in tree.body:
        if (
            isinstance(node, ast.ImportFrom)
            and node.module == "__future__"
            and any(alias.name == "annotations" for alias in node.names)
        ):
            return True
    return False


@pytest.mark.parametrize(
    "path",
    _source_files(),
    ids=lambda p: str(p.name),
)
def test_annotations_resolve_without_future_import(path: Path) -> None:
    """没有 ``from __future__ import annotations`` 的模块, 注解必须能立即求值."""
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    if _has_future_annotations(tree):
        pytest.skip("已启用 from __future__ import annotations, 注解不立即求值")

    available = _module_level_names(tree) | set(dir(builtins))
    problems: list[str] = []
    for annotation in _annotation_nodes(tree):
        for name in _used_names(annotation):
            if name not in available:
                problems.append(f"line {annotation.lineno}: {name}")

    assert problems == [], (
        f"{path} 的注解引用了运行时不可解析的名字(可能是只导入了 TYPE_CHECKING): "
        f"{sorted(set(problems))}"
    )
