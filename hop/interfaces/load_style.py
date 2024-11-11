try:
    import hou
except ModuleNotFoundError:
    from ..util import import_hou

    hou = import_hou()


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
