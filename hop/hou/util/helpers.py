import os
import sys
from typing import Any
from warnings import warn
from pathlib import Path


def import_hou() -> Any:
    try:
        import hou

        return hou
    except ModuleNotFoundError:
        install = None
        if "HOUDINI_PATH" in os.environ:
            install = os.environ["HOUDINI_PATH"]
        else:
            PATH = os.getenv("PATH")
            if PATH is not None:
                path_separator = ";" if os.name == "nt" else ":"
                paths = PATH.split(path_separator)
                for path in paths:
                    if "Houdini" in path or "hfs" in path:
                        install = os.path.dirname(path)
                        break
        s_dlopen_flag = False
        old_dlopen_flags = 0
        if install is not None:
            jemalloc = os.path.join(install, "dsolib/libjemalloc.so")
            LD_PRELOAD = os.getenv("LD_PRELOAD")
            if os.path.exists(jemalloc) and LD_PRELOAD is None:
                warn(f"set LD_PRELOAD to {jemalloc}", RuntimeWarning)

        if hasattr(sys, "setdlopenflags"):
            old_dlopen_flags = sys.getdlopenflags()
            sys.setdlopenflags(old_dlopen_flags | os.RTLD_GLOBAL)
            s_dlopen_flag = True

        if sys.platform == "win32   " and hasattr(os, "add_dll_directory"):
            hfs_path = os.getenv("HFS")
            if hfs_path:
                os.add_dll_directory(f"{hfs_path}/bin")

        try:
            import hou
        except ModuleNotFoundError:
            HHP = os.getenv("HHP")

            # Attempt to locate hou.py
            if HHP is not None:
                sys.path.append(HHP)
            elif install is not None:
                houdini_path = os.path.join(
                    install,
                    f"houdini/python{sys.version_info[0]}.{sys.version_info[1]}libs",
                )
                hou_path = os.path.join(houdini_path, "hou.py")
                if os.path.exists(hou_path):
                    sys.path.append(houdini_path)

            try:
                import hou
            except ModuleNotFoundError:
                raise ModuleNotFoundError("Couldn't find hou module path")

        if s_dlopen_flag:
            sys.setdlopenflags(old_dlopen_flags)

        return hou


try:
    import hou
except ModuleNotFoundError:
    hou = import_hou()
from hou import ObjNode
import loptoolutils


def place_node(
    kwargs: dict, pane_type: str | list, node_type: str, node_name: None | str = None
) -> ObjNode | None:
    if node_name is None:
        node_name = node_type

    node = None
    try:
        node = loptoolutils.genericTool(
            kwargs, node_type, node_name, clicktoplace=False
        )
    except AttributeError:
        desktop = hou.ui.curDesktop()
        pane = desktop.paneTabUnderCursor()
        if pane is not None:
            current_context = pane.pwd()
            if current_context.type().name() == pane_type:
                node = current_context.createNode(
                    node_type, node_name, True, True, False, True
                )
                node.moveToGoodPosition()
        else:
            if pane_type[0] != "/":
                pane_type = f"/{pane_type}"
            current_context = hou.node(pane_type)
            if current_context is not None:
                node = current_context.createNode(
                    node_type, node_name, True, True, False, True
                )
                node.moveToGoodPosition()

    return node


def expand_path(path: str, create_path: bool = False) -> str | None:
    expanded_path = Path(hou.text.expandString(path)).resolve().as_posix()
    if os.path.exists(expanded_path):
        return expanded_path
    elif create_path:
        make_dir = expanded_path
        if "." in os.path.basename(expanded_path):
            make_dir = os.path.dirname(make_dir)
        os.makedirs(make_dir, exist_ok=True)
        return expanded_path
    return None


def confirmation_dialog(title: str, text: str, details: str | None = None) -> bool:
    confirm = hou.ui.displayMessage(
        text=text,
        buttons=["OK", "Cancel"],
        severity=hou.severityType.Warning,
        default_choice=1,
        close_choice=1,
        title=title,
        details=details,
    )
    return confirm == 0


def error_dialog(title: str, text: str) -> None:
    hou.ui.displayMessage(
        text=text,
        severity=hou.severityType.Error,
        title=title,
    )


def load_style() -> str:
    Border = hou.qt.getColor("ListBorder").name()
    ListEntry1 = hou.qt.getColor("ListEntry1").name()
    ListEntry2 = hou.qt.getColor("ListEntry2").name()
    ListShadow = hou.qt.getColor("ListShadow").name()
    ListHighlight = hou.qt.getColor("ListHighlight").name()
    ListEntrySelected = hou.qt.getColor("ListEntrySelected").name()
    ListTitleGradHi = hou.qt.getColor("ListTitleGradHi").name()
    ListTitleGradLow = hou.qt.getColor("ListTitleGradLow").name()
    ListText = hou.qt.getColor("ListText").name()
    Button = hou.qt.getColor("ButtonColor").name()
    style_sheet = f"""
    QListWidget {{
        background-color: {ListEntry2};                     
        alternate-background-color: {ListEntry1};
        border: 1px solid {Border};
    }}

    QListWidget::item:selected {{
        background-color: {ListEntrySelected};
        color: {ListText};
    }}

    QListWidget {{
        border-top: 1px solid {ListShadow};
        border-bottom: 1px solid {ListHighlight};
    }}

    QHeaderView::section {{
        background: qlineargradient(
            x1: 0, y1: 0, x2: 0, y2: 1,
            stop: 0 {ListTitleGradHi},
            stop: 1 {ListTitleGradLow}
        );
        color: {ListText};
    }}

    QTabBar::tab {{
        background-color: {Button};
        border: 1px solid {Border};
        padding: 4px;
    }}

    QTabBar::tab:selected {{
        background-color: {ListEntry2};
        color: {ListText};
        border: 1px solid {ListHighlight};
    }}

    QTabWidget::pane {{
        border: 1px solid {Border};
    }}

    QTabWidget::tab-bar {{
        alignment: center;
    }}

    QLabel#bold {{
        font-weight: bold;
        color: {ListText};
    }}
    """

    return style_sheet