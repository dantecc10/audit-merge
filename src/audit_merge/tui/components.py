"""
Reusable UI components for Audit Merge TUI.

Built on top of Textual widgets with the design system from theme.py.
"""

from textual.containers import Container, Horizontal, Vertical, Grid
from textual.widgets import Static, Button, Label, ProgressBar
from textual.widget import Widget
from textual.message import Message
from textual.binding import Binding
from rich.text import Text
from typing import Optional, Literal
from enum import Enum


class CardVariant(str, Enum):
    """Card visual variants."""
    DEFAULT = "default"
    ELEVATED = "elevated"
    SECTION = "section"


class StatCardVariant(str, Enum):
    """StatCard color variants."""
    PRIMARY = "primary"
    SUCCESS = "success"
    WARNING = "warning"
    ERROR = "error"


class BadgeVariant(str, Enum):
    """Badge color variants."""
    SUCCESS = "success"
    WARNING = "warning"
    ERROR = "error"
    INFO = "info"
    NEUTRAL = "neutral"
    AUTO = "auto"
    CONFLICT = "conflict"
    REMOVED = "removed"
    ADDED = "added"
    MODIFIED = "modified"


class ButtonVariant(str, Enum):
    """Extended button variants."""
    PRIMARY = "primary"
    SECONDARY = "secondary"
    SUCCESS = "success"
    WARNING = "warning"
    ERROR = "error"
    GHOST = "ghost"


class Card(Container):
    """A styled card container with variant support."""
    
    DEFAULT_CSS = """
    Card {
        background: var(--surface);
        border: solid var(--border);
        border-radius: var(--radius-md);
        padding: var(--space-md);
        margin: var(--space-sm) 0;
    }
    
    Card.-elevated {
        background: var(--surface-elevated);
        border-radius: var(--radius-lg);
        padding: var(--space-lg);
        margin: var(--space-md) 0;
    }
    
    Card.-section {
        background: var(--surface-elevated);
        border-radius: var(--radius-md);
        padding: var(--space-md);
        margin: var(--space-sm) 0;
    }
    """
    
    def __init__(
        self,
        *children,
        variant: CardVariant = CardVariant.DEFAULT,
        **kwargs
    ):
        classes = kwargs.pop("classes", "")
        if variant == CardVariant.ELEVATED:
            classes += " -elevated"
        elif variant == CardVariant.SECTION:
            classes += " -section"
        kwargs["classes"] = classes.strip()
        super().__init__(*children, **kwargs)


class StatCard(Container):
    """A metric display card with icon, value, and label."""
    
    DEFAULT_CSS = """
    StatCard {
        background: var(--surface);
        border: solid var(--border);
        border-radius: var(--radius-lg);
        padding: var(--space-lg);
        min-width: 22;
        min-height: 10;
        layout: vertical;
        align: center middle;
    }
    
    StatCard.-primary { border-left: solid 4 var(--brand-primary); }
    StatCard.-success { border-left: solid 4 var(--success); }
    StatCard.-warning { border-left: solid 4 var(--warning); }
    StatCard.-error { border-left: solid 4 var(--error); }
    
    StatCard > .stat-icon {
        font-size: 200%;
        margin-bottom: var(--space-xs);
        height: auto;
    }
    
    StatCard > .stat-value {
        text-style: bold;
        font-size: 150%;
        color: var(--text-primary);
        margin-bottom: var(--space-xs);
        height: auto;
    }
    
    StatCard > .stat-label {
        color: var(--text-secondary);
        text-align: center;
        width: 100%;
        height: auto;
    }
    """
    
    def __init__(
        self,
        value: str,
        label: str,
        icon: str = "📊",
        variant: StatCardVariant = StatCardVariant.PRIMARY,
        **kwargs
    ):
        classes = kwargs.pop("classes", "")
        classes += f" -{variant.value}"
        kwargs["classes"] = classes.strip()
        
        icon_widget = Static(icon, classes="stat-icon")
        value_widget = Static(value, classes="stat-value")
        label_widget = Static(label, classes="stat-label")
        
        super().__init__(icon_widget, value_widget, label_widget, **kwargs)
    
    def update_value(self, value: str) -> None:
        """Update the displayed value."""
        self.query_one(".stat-value", Static).update(value)


class Badge(Static):
    """A colored badge/pill for status indicators."""
    
    DEFAULT_CSS = """
    Badge {
        padding: 0 var(--space-sm);
        border-radius: var(--radius-full);
        text-style: bold;
        font-size: 80%;
        height: 2;
        content-align: center middle;
        min-width: 8;
    }
    
    Badge.-success {
        background: var(--success-bg);
        color: var(--success);
        border: solid var(--success-border);
    }
    
    Badge.-warning {
        background: var(--warning-bg);
        color: var(--warning);
        border: solid var(--warning-border);
    }
    
    Badge.-error {
        background: var(--error-bg);
        color: var(--error);
        border: solid var(--error-border);
    }
    
    Badge.-info {
        background: var(--info-bg);
        color: var(--info);
        border: solid var(--info-border);
    }
    
    Badge.-neutral {
        background: var(--surface-elevated);
        color: var(--text-muted);
        border: solid var(--border);
    }
    
    Badge.-auto {
        background: var(--success-bg);
        color: var(--success);
        border: solid var(--success-border);
    }
    
    Badge.-conflict {
        background: var(--warning-bg);
        color: var(--warning);
        border: solid var(--warning-border);
    }
    
    Badge.-removed {
        background: var(--error-bg);
        color: var(--error);
        border: solid var(--error-border);
    }
    
    Badge.-added {
        background: var(--info-bg);
        color: var(--info);
        border: solid var(--info-border);
    }
    
    Badge.-modified {
        background: #f3e5f5;
        color: #6a1b9a;
        border: solid #ce93d8;
    }
    """
    
    def __init__(
        self,
        text: str,
        variant: BadgeVariant = BadgeVariant.NEUTRAL,
        **kwargs
    ):
        classes = kwargs.pop("classes", "")
        classes += f" -{variant.value}"
        kwargs["classes"] = classes.strip()
        super().__init__(text, **kwargs)


class ButtonGroup(Horizontal):
    """A group of buttons with consistent spacing and primary highlighting."""
    
    DEFAULT_CSS = """
    ButtonGroup {
        layout: horizontal;
        width: 100%;
        height: auto;
        padding: var(--space-md) 0;
    }
    
    ButtonGroup > Button {
        margin: 0 var(--space-xs);
    }
    
    ButtonGroup.-primary > Button.primary {
        margin-right: var(--space-sm);
    }
    """
    
    def __init__(
        self,
        *buttons: Button,
        primary_first: bool = True,
        **kwargs
    ):
        classes = kwargs.pop("classes", "")
        if primary_first:
            classes += " -primary-first"
        kwargs["classes"] = classes.strip()
        super().__init__(*buttons, **kwargs)


class Panel(Container):
    """A panel with header and content area."""
    
    DEFAULT_CSS = """
    Panel {
        background: var(--surface);
        border: solid var(--border);
        border-radius: var(--radius-lg);
        padding: var(--space-lg);
        layout: vertical;
    }
    
    Panel > .panel-header {
        text-style: bold;
        color: var(--text-primary);
        margin-bottom: var(--space-md);
        padding-bottom: var(--space-sm);
        border-bottom: solid var(--border);
        height: auto;
    }
    
    Panel > .panel-content {
        layout: vertical;
        height: 1fr;
        overflow: auto;
    }
    """
    
    def __init__(
        self,
        title: str,
        *children,
        **kwargs
    ):
        header = Static(title, classes="panel-header")
        content = Container(*children, classes="panel-content")
        super().__init__(header, content, **kwargs)


class Section(Container):
    """A section with title and collapsible content."""
    
    DEFAULT_CSS = """
    Section {
        background: var(--surface);
        border: solid var(--border);
        border-radius: var(--radius-md);
        overflow: hidden;
        margin: var(--space-sm) 0;
    }
    
    Section > .section-header {
        background: var(--surface-elevated);
        padding: var(--space-sm) var(--space-md);
        text-style: bold;
        color: var(--text-primary);
        border-bottom: solid var(--border);
        height: 3;
        layout: horizontal;
        align: center middle;
    }
    
    Section > .section-header > .section-title {
        width: 1fr;
    }
    
    Section > .section-header > .section-toggle {
        color: var(--text-muted);
        padding: 0 var(--space-sm);
    }
    
    Section > .section-content {
        padding: var(--space-md);
        height: auto;
    }
    
    Section.-collapsed > .section-content {
        display: none;
    }
    
    Section.-collapsed > .section-header > .section-toggle {
        transform: rotate(-90deg);
    }
    """
    
    def __init__(
        self,
        title: str,
        *children,
        collapsed: bool = False,
        **kwargs
    ):
        classes = kwargs.pop("classes", "")
        if collapsed:
            classes += " -collapsed"
        kwargs["classes"] = classes.strip()
        
        toggle_char = "▼" if not collapsed else "▶"
        toggle = Static(toggle_char, classes="section-toggle")
        title_widget = Static(title, classes="section-title")
        header = Horizontal(toggle, title_widget, classes="section-header")
        content = Container(*children, classes="section-content")
        
        super().__init__(header, content, **kwargs)
        self._collapsed = collapsed
    
    def toggle(self) -> None:
        """Toggle collapsed state."""
        self._collapsed = not self._collapsed
        if self._collapsed:
            self.add_class("-collapsed")
        else:
            self.remove_class("-collapsed")
        
        toggle = self.query_one(".section-toggle", Static)
        toggle.update("▶" if self._collapsed else "▼")


class Breadcrumb(Horizontal):
    """A breadcrumb navigation component."""
    
    DEFAULT_CSS = """
    Breadcrumb {
        layout: horizontal;
        height: 3;
        padding: var(--space-xs) var(--space-sm);
        background: var(--surface-elevated);
        border-bottom: solid var(--border);
        overflow-x: auto;
    }
    
    Breadcrumb > .breadcrumb-item {
        color: var(--text-muted);
        padding: 0 var(--space-xs);
        cursor: pointer;
    }
    
    Breadcrumb > .breadcrumb-item:hover {
        color: var(--brand-primary);
        text-style: underline;
    }
    
    Breadcrumb > .breadcrumb-item.-active {
        color: var(--text-primary);
        text-style: bold;
    }
    
    Breadcrumb > .breadcrumb-separator {
        color: var(--text-muted);
        padding: 0 var(--space-xs);
    }
    """
    
    def __init__(self, paths: list[tuple[str, str]], **kwargs):
        """
        Initialize breadcrumb.
        
        Args:
            paths: List of (label, path) tuples. Last item is current (no link).
        """
        children = []
        for i, (label, path) in enumerate(paths):
            if i > 0:
                children.append(Static(" › ", classes="breadcrumb-separator"))
            
            is_last = i == len(paths) - 1
            item = Static(label, classes=f"breadcrumb-item {'-active' if is_last else ''}")
            item.path = path  # type: ignore
            children.append(item)
        
        super().__init__(*children, **kwargs)


class DiffRow(Container):
    """A single row in the diff view showing base vs updated values."""
    
    DEFAULT_CSS = """
    DiffRow {
        layout: horizontal;
        width: 100%;
        height: auto;
        min-height: 3;
        padding: var(--space-xs) var(--space-sm);
        border-bottom: solid var(--border);
    }
    
    DiffRow:last-child {
        border-bottom: none;
    }
    
    DiffRow.-added {
        background: var(--success-bg);
    }
    
    DiffRow.-removed {
        background: var(--error-bg);
    }
    
    DiffRow.-modified {
        background: var(--warning-bg);
    }
    
    DiffRow > .diff-field {
        width: 20;
        min-width: 18;
        padding: var(--space-xs) var(--space-sm);
        text-style: bold;
        color: var(--text-secondary);
        content-align-horizontal: right;
    }
    
    DiffRow > .diff-base,
    DiffRow > .diff-updated {
        width: 1fr;
        min-width: 25;
        padding: var(--space-xs) var(--space-sm);
    }
    
    DiffRow.-added > .diff-base,
    DiffRow.-added > .diff-updated {
        background: var(--diff-unchanged-bg);
        border-color: var(--border);
    }
    
    DiffRow.-removed > .diff-base,
    DiffRow.-removed > .diff-updated {
        background: var(--diff-unchanged-bg);
        border-color: var(--border);
    }
    """
    
    def __init__(
        self,
        field_name: str,
        base_value: str,
        updated_value: str,
        change_type: Literal["added", "removed", "modified", "unchanged"] = "unchanged",
        **kwargs
    ):
        classes = kwargs.pop("classes", "")
        classes += f" -{change_type}"
        kwargs["classes"] = classes.strip()
        
        field_label = Static(field_name, classes="diff-field")
        base_widget = Static(base_value or "—", classes="diff-base")
        updated_widget = Static(updated_value or "—", classes="diff-updated")
        
        # Add change badge
        if change_type == "added":
            badge = Badge("➕ ADDED", BadgeVariant.ADDED, classes="diff-badge")
        elif change_type == "removed":
            badge = Badge("➖ REMOVED", BadgeVariant.REMOVED, classes="diff-badge")
        elif change_type == "modified":
            badge = Badge("🔄 MODIFIED", BadgeVariant.MODIFIED, classes="diff-badge")
        else:
            badge = Static("", classes="diff-badge")
        
        super().__init__(field_label, base_widget, updated_widget, badge, **kwargs)


class LoadingOverlay(Container):
    """A loading overlay with spinner and message."""
    
    DEFAULT_CSS = """
    LoadingOverlay {
        layer: overlay;
        align: center middle;
        width: 100%;
        height: 100%;
        background: rgba(255, 255, 255, 0.9);
        display: none;
    }
    
    LoadingOverlay.-visible {
        display: block;
    }
    
    LoadingOverlay > .loading-content {
        background: var(--surface);
        border: solid var(--border);
        border-radius: var(--radius-lg);
        padding: var(--space-xl);
        layout: vertical;
        align: center middle;
        min-width: 40;
    }
    
    LoadingOverlay > .loading-content > .spinner {
        color: var(--brand-primary);
        margin-bottom: var(--space-md);
    }
    
    LoadingOverlay > .loading-content > .loading-message {
        color: var(--text-secondary);
        text-align: center;
    }
    """
    
    def __init__(self, message: str = "Loading...", **kwargs):
        spinner = Static("⠋", classes="spinner")
        msg = Static(message, classes="loading-message")
        content = Container(spinner, msg, classes="loading-content")
        super().__init__(content, **kwargs)
        self._frames = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]
        self._frame_index = 0
        self._animation_task = None
    
    def show(self, message: str | None = None) -> None:
        """Show the loading overlay."""
        if message:
            self.query_one(".loading-message", Static).update(message)
        self.add_class("-visible")
        self._start_animation()
    
    def hide(self) -> None:
        """Hide the loading overlay."""
        self.remove_class("-visible")
        self._stop_animation()
    
    def _start_animation(self) -> None:
        """Start spinner animation."""
        if self._animation_task is None:
            self._animation_task = self.set_interval(0.1, self._animate)
    
    def _stop_animation(self) -> None:
        """Stop spinner animation."""
        if self._animation_task is not None:
            self._animation_task.stop()
            self._animation_task = None
    
    def _animate(self) -> None:
        """Animate spinner."""
        self._frame_index = (self._frame_index + 1) % len(self._frames)
        self.query_one(".spinner", Static).update(self._frames[self._frame_index])


class Toast(Static):
    """A toast notification."""
    
    DEFAULT_CSS = """
    Toast {
        background: var(--surface);
        border: solid var(--border);
        border-radius: var(--radius-md);
        padding: var(--space-md) var(--space-lg);
        margin: var(--space-sm);
        layout: horizontal;
        height: auto;
        min-width: 30;
        max-width: 80;
    }
    
    Toast.-success {
        border-left: solid 4 var(--success);
    }
    
    Toast.-warning {
        border-left: solid 4 var(--warning);
    }
    
    Toast.-error {
        border-left: solid 4 var(--error);
    }
    
    Toast.-info {
        border-left: solid 4 var(--info);
    }
    
    Toast > .toast-icon {
        margin-right: var(--space-sm);
        content-align: center middle;
    }
    
    Toast > .toast-message {
        width: 1fr;
        color: var(--text-primary);
    }
    """
    
    class Dismissed(Message):
        """Message sent when toast is dismissed."""
        def __init__(self, toast: "Toast"):
            self.toast = toast
            super().__init__()
    
    def __init__(
        self,
        message: str,
        variant: Literal["success", "warning", "error", "info"] = "info",
        duration: float = 5.0,
        **kwargs
    ):
        classes = kwargs.pop("classes", "")
        classes += f" -{variant}"
        kwargs["classes"] = classes.strip()
        
        icons = {
            "success": "✅",
            "warning": "⚠️",
            "error": "❌",
            "info": "ℹ️",
        }
        
        icon = Static(icons.get(variant, "ℹ️"), classes="toast-icon")
        msg = Static(message, classes="toast-message")
        
        super().__init__(Horizontal(icon, msg), **kwargs)
        self._duration = duration
        self._dismiss_timer = None
    
    def on_mount(self) -> None:
        """Start dismiss timer."""
        self._dismiss_timer = self.set_timer(self._duration, self._dismiss)
    
    def _dismiss(self) -> None:
        """Dismiss the toast."""
        self.post_message(self.Dismissed(self))
        self.remove()
    
    def on_click(self, event) -> None:
        """Dismiss on click."""
        if self._dismiss_timer:
            self._dismiss_timer.stop()
        self._dismiss()


class FormField(Container):
    """A form field with label, input, and validation."""
    
    DEFAULT_CSS = """
    FormField {
        layout: vertical;
        height: auto;
        margin: var(--space-sm) 0;
    }
    
    FormField > .field-label {
        text-style: bold;
        color: var(--text-secondary);
        margin-bottom: var(--space-xs);
        height: auto;
    }
    
    FormField > .field-input {
        height: 3;
    }
    
    FormField > .field-error {
        color: var(--error);
        font-size: 80%;
        margin-top: var(--space-xs);
        display: none;
    }
    
    FormField.-invalid > .field-error {
        display: block;
    }
    
    FormField.-invalid > .field-input {
        border-color: var(--error);
    }
    
    FormField.-valid > .field-input {
        border-color: var(--success);
    }
    """
    
    def __init__(
        self,
        label: str,
        placeholder: str = "",
        value: str = "",
        required: bool = False,
        **kwargs
    ):
        label_widget = Static(f"{label}{' *' if required else ''}", classes="field-label")
        input_widget = Input(
            value=value,
            placeholder=placeholder,
            classes="field-input"
        )
        error_widget = Static("", classes="field-error")
        
        super().__init__(label_widget, input_widget, error_widget, **kwargs)
        self._required = required
    
    def get_value(self) -> str:
        """Get the input value."""
        return self.query_one(".field-input", Input).value
    
    def set_value(self, value: str) -> None:
        """Set the input value."""
        self.query_one(".field-input", Input).value = value
    
    def validate(self) -> bool:
        """Validate the field."""
        value = self.get_value().strip()
        is_valid = not self._required or bool(value)
        
        if is_valid:
            self.remove_class("-invalid")
            self.add_class("-valid")
            self.query_one(".field-error", Static).update("")
        else:
            self.remove_class("-valid")
            self.add_class("-invalid")
            self.query_one(".field-error", Static).update("This field is required")
        
        return is_valid


# Export all components
__all__ = [
    "Card",
    "CardVariant",
    "StatCard",
    "StatCardVariant",
    "Badge",
    "BadgeVariant",
    "ButtonGroup",
    "ButtonVariant",
    "Panel",
    "Section",
    "Breadcrumb",
    "DiffRow",
    "LoadingOverlay",
    "Toast",
    "FormField",
]