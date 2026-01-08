"""
Flow layout implementation for Qt.
Arranges widgets in rows, wrapping to new lines as needed.
"""
from PySide6.QtWidgets import QLayout, QLayoutItem, QWidget, QSizePolicy
from PySide6.QtCore import Qt, QRect, QSize, QPoint


class FlowLayout(QLayout):
    """A layout that arranges widgets in a flowing manner, wrapping to new lines."""
    
    def __init__(self, parent=None, margin: int = -1, spacing: int = -1):
        super().__init__(parent)
        
        if margin >= 0:
            self.setContentsMargins(margin, margin, margin, margin)
        
        self._spacing = spacing
        self._items: list[QLayoutItem] = []
    
    def __del__(self):
        item = self.takeAt(0)
        while item:
            item = self.takeAt(0)
    
    def addItem(self, item: QLayoutItem):
        self._items.append(item)
    
    def count(self) -> int:
        return len(self._items)
    
    def itemAt(self, index: int) -> QLayoutItem | None:
        if 0 <= index < len(self._items):
            return self._items[index]
        return None
    
    def takeAt(self, index: int) -> QLayoutItem | None:
        if 0 <= index < len(self._items):
            return self._items.pop(index)
        return None
    
    def spacing(self) -> int:
        if self._spacing >= 0:
            return self._spacing
        return super().spacing()
    
    def expandingDirections(self) -> Qt.Orientation:
        return Qt.Orientation(0)
    
    def hasHeightForWidth(self) -> bool:
        return True
    
    def heightForWidth(self, width: int) -> int:
        return self._do_layout(QRect(0, 0, width, 0), test_only=True)
    
    def setGeometry(self, rect: QRect):
        super().setGeometry(rect)
        self._do_layout(rect, test_only=False)
    
    def sizeHint(self) -> QSize:
        return self.minimumSize()
    
    def minimumSize(self) -> QSize:
        size = QSize()
        
        for item in self._items:
            size = size.expandedTo(item.minimumSize())
        
        margins = self.contentsMargins()
        size += QSize(margins.left() + margins.right(), margins.top() + margins.bottom())
        
        return size
    
    def _do_layout(self, rect: QRect, test_only: bool) -> int:
        """Perform the layout."""
        margins = self.contentsMargins()
        effective_rect = rect.adjusted(margins.left(), margins.top(), -margins.right(), -margins.bottom())
        
        x = effective_rect.x()
        y = effective_rect.y()
        line_height = 0
        spacing = self.spacing()
        
        for item in self._items:
            widget = item.widget()
            if widget is None or not widget.isVisible():
                continue
            
            space_x = spacing
            space_y = spacing
            
            next_x = x + item.sizeHint().width() + space_x
            
            if next_x - space_x > effective_rect.right() and line_height > 0:
                x = effective_rect.x()
                y = y + line_height + space_y
                next_x = x + item.sizeHint().width() + space_x
                line_height = 0
            
            if not test_only:
                item.setGeometry(QRect(QPoint(x, y), item.sizeHint()))
            
            x = next_x
            line_height = max(line_height, item.sizeHint().height())
        
        return y + line_height - rect.y() + margins.bottom()
