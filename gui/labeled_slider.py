from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QHBoxLayout, QLabel, QSlider, QWidget


class LabeledSlider(QWidget):
    valueChanged = Signal(int)

    def __init__(
        self,
        label: str,
        minimum: int,
        maximum: int,
        value: int,
        step: int = 1,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self._block = False

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self._name = QLabel(label)
        self._name.setMinimumWidth(100)
        layout.addWidget(self._name)

        self._slider = QSlider(Qt.Horizontal)
        self._slider.setMinimum(minimum)
        self._slider.setMaximum(maximum)
        self._slider.setValue(value)
        self._slider.setSingleStep(step)
        self._slider.setPageStep(max(step * 2, 1))
        layout.addWidget(self._slider, stretch=1)

        self._value_label = QLabel(str(value))
        self._value_label.setMinimumWidth(36)
        self._value_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        layout.addWidget(self._value_label)

        self._slider.valueChanged.connect(self._on_changed)

    def _on_changed(self, val: int) -> None:
        self._value_label.setText(str(val))
        if not self._block:
            self.valueChanged.emit(val)

    def value(self) -> int:
        return self._slider.value()

    def setValue(self, val: int) -> None:
        self._block = True
        self._slider.setValue(val)
        self._value_label.setText(str(val))
        self._block = False

    def setEnabled(self, enabled: bool) -> None:
        super().setEnabled(enabled)
        self._slider.setEnabled(enabled)
