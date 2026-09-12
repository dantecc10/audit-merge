"""
Design tokens and theme system for Audit Merge TUI.

Centralized design system providing consistent colors, spacing, typography,
and component styling across the application.
"""

from dataclasses import dataclass
from typing import ClassVar


@dataclass(frozen=True)
class Color:
    """Color value with hex and RGB representations."""
    hex: str
    
    @property
    def rgb(self) -> tuple[int, int, int]:
        h = self.hex.lstrip('#')
        return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))
    
    def with_alpha(self, alpha: float) -> str:
        r, g, b = self.rgb
        return f"rgba({r}, {g}, {b}, {alpha})"
    
    def lighter(self, factor: float = 0.1) -> "Color":
        r, g, b = self.rgb
        r = min(255, int(r + (255 - r) * factor))
        g = min(255, int(g + (255 - g) * factor))
        b = min(255, int(b + (255 - b) * factor))
        return Color(f"#{r:02x}{g:02x}{b:02x}")
    
    def darker(self, factor: float = 0.1) -> "Color":
        r, g, b = self.rgb
        r = max(0, int(r * (1 - factor)))
        g = max(0, int(g * (1 - factor)))
        b = max(0, int(b * (1 - factor)))
        return Color(f"#{r:02x}{g:02x}{b:02x}")


class Palette:
    """Complete color palette for the application."""
    
    # Brand colors
    BRAND_PRIMARY = Color("#1e3a5f")      # Dark navy
    BRAND_SECONDARY = Color("#2d6a9e")    # Medium blue
    BRAND_ACCENT = Color("#00b4d8")       # Cyan accent
    BRAND_ACCENT_SOFT = Color("#90e0ef")  # Light cyan
    
    # Semantic colors
    SUCCESS = Color("#2e7d32")
    SUCCESS_BG = Color("#e8f5e9")
    SUCCESS_BORDER = Color("#a5d6a7")
    
    WARNING = Color("#f57c00")
    WARNING_BG = Color("#fff3e0")
    WARNING_BORDER = Color("#ffcc80")
    
    ERROR = Color("#c62828")
    ERROR_BG = Color("#fce4ec")
    ERROR_BORDER = Color("#ef9a9a")
    
    INFO = Color("#0288d1")
    INFO_BG = Color("#e3f2fd")
    INFO_BORDER = Color("#90caf9")
    
    # Neutral / Surface colors
    SURFACE = Color("#ffffff")
    SURFACE_ELEVATED = Color("#f8f9fa")
    SURFACE_HOVER = Color("#eef1f5")
    SURFACE_PRESSED = Color("#dee2e6")
    
    # Border colors
    BORDER = Color("#dee2e6")
    BORDER_FOCUS = Color("#2d6a9e")
    BORDER_STRONG = Color("#adb5bd")
    
    # Text colors
    TEXT_PRIMARY = Color("#1a1a2e")
    TEXT_SECONDARY = Color("#4a4a6a")
    TEXT_MUTED = Color("#888899")
    TEXT_ON_PRIMARY = Color("#ffffff")
    TEXT_ON_ACCENT = Color("#001f3f")
    
    # Status badge colors
    BADGE_AUTO = Color("#2e7d32")       # Green
    BADGE_CONFLICT = Color("#f57c00")   # Orange
    BADGE_REMOVED = Color("#c62828")    # Red
    BADGE_ADDED = Color("#0288d1")      # Blue
    BADGE_MODIFIED = Color("#6a1b9a")   # Purple
    BADGE_NEUTRAL = Color("#546e7a")    # Blue-grey
    
    # Diff view colors
    DIFF_ADDED_BG = Color("#e8f5e9")
    DIFF_REMOVED_BG = Color("#fce4ec")
    DIFF_MODIFIED_BG = Color("#fff3e0")
    DIFF_UNCHANGED_BG = Color("#f5f5f5")


class Spacing:
    """Spacing scale (in terminal character units)."""
    XS = 1
    SM = 2
    MD = 3
    LG = 4
    XL = 6
    XXL = 8


class Typography:
    """Typography scale and weights."""
    
    # Font families (terminal-dependent, but we can hint)
    MONO = "monospace"
    UI = "sans-serif"
    
    # Sizes (relative to terminal base)
    SIZE_XS = "small"
    SIZE_SM = "small"
    SIZE_BASE = "normal"
    SIZE_LG = "normal"
    SIZE_XL = "normal"
    SIZE_2XL = "normal"
    
    # Weights
    WEIGHT_NORMAL = "normal"
    WEIGHT_BOLD = "bold"
    WEIGHT_LIGHT = "normal"
    
    # Line heights (approximate)
    LINE_TIGHT = 1.2
    LINE_NORMAL = 1.5
    LINE_RELAXED = 1.8


class BorderRadius:
    """Border radius values (CSS-like, for reference)."""
    NONE = 0
    SM = 1
    MD = 2
    LG = 3
    FULL = 9999


class Shadows:
    """Box shadow definitions (for reference, terminal uses borders)."""
    NONE = "none"
    SM = "0 1 2 rgba(0,0,0,0.05)"
    MD = "0 2 4 rgba(0,0,0,0.1)"
    LG = "0 4 8 rgba(0,0,0,0.15)"
    XL = "0 8 16 rgba(0,0,0,0.2)"


class ZIndex:
    """Z-index layers."""
    BASE = 0
    DROPDOWN = 100
    MODAL = 200
    TOAST = 300
    TOOLTIP = 400


class Breakpoints:
    """Responsive breakpoints (terminal columns)."""
    SM = 60
    MD = 80
    LG = 100
    XL = 120
    XXL = 140


class Transitions:
    """Animation durations (milliseconds)."""
    FAST = 100
    NORMAL = 200
    SLOW = 300


# Component-specific token groups
class ComponentTokens:
    """Tokens organized by component."""
    
    # Card
    CARD = {
        "background": Palette.SURFACE,
        "border": Palette.BORDER,
        "border_focus": Palette.BORDER_FOCUS,
        "padding": Spacing.MD,
        "gap": Spacing.SM,
    }
    
    CARD_ELEVATED = {
        "background": Palette.SURFACE_ELEVATED,
        "border": Palette.BORDER,
        "padding": Spacing.LG,
        "gap": Spacing.MD,
    }
    
    # StatCard
    STAT_CARD = {
        "background": Palette.SURFACE,
        "border": Palette.BORDER,
        "padding": Spacing.LG,
        "gap": Spacing.XS,
        "min_width": 22,
        "min_height": 10,
    }
    
    # Button
    BUTTON_PRIMARY = {
        "background": Palette.BRAND_PRIMARY,
        "color": Palette.TEXT_ON_PRIMARY,
        "border": Palette.BRAND_PRIMARY,
        "padding_h": Spacing.MD,
        "padding_v": Spacing.XS,
    }
    
    BUTTON_SECONDARY = {
        "background": Palette.SURFACE,
        "color": Palette.BRAND_PRIMARY,
        "border": Palette.BRAND_PRIMARY,
        "padding_h": Spacing.MD,
        "padding_v": Spacing.XS,
    }
    
    BUTTON_SUCCESS = {
        "background": Palette.SUCCESS,
        "color": Palette.TEXT_ON_PRIMARY,
        "border": Palette.SUCCESS,
        "padding_h": Spacing.MD,
        "padding_v": Spacing.XS,
    }
    
    BUTTON_WARNING = {
        "background": Palette.WARNING,
        "color": Palette.TEXT_ON_PRIMARY,
        "border": Palette.WARNING,
        "padding_h": Spacing.MD,
        "padding_v": Spacing.XS,
    }
    
    BUTTON_ERROR = {
        "background": Palette.ERROR,
        "color": Palette.TEXT_ON_PRIMARY,
        "border": Palette.ERROR,
        "padding_h": Spacing.MD,
        "padding_v": Spacing.XS,
    }
    
    BUTTON_GHOST = {
        "background": "transparent",
        "color": Palette.TEXT_SECONDARY,
        "border": "transparent",
        "padding_h": Spacing.SM,
        "padding_v": Spacing.XS,
    }
    
    # Badge
    BADGE = {
        "padding_h": Spacing.SM,
        "padding_v": 0,
        "border_radius": BorderRadius.FULL,
        "font_size": Typography.SIZE_XS,
        "font_weight": Typography.WEIGHT_BOLD,
    }
    
    # Input
    INPUT = {
        "background": Palette.SURFACE,
        "border": Palette.BORDER,
        "border_focus": Palette.BORDER_FOCUS,
        "color": Palette.TEXT_PRIMARY,
        "placeholder_color": Palette.TEXT_MUTED,
        "padding_h": Spacing.SM,
        "padding_v": Spacing.XS,
    }
    
    # Table/DataTable
    TABLE = {
        "header_background": Palette.SURFACE_ELEVATED,
        "header_color": Palette.TEXT_SECONDARY,
        "row_background_even": Palette.SURFACE,
        "row_background_odd": Palette.SURFACE_ELEVATED,
        "row_hover": Palette.SURFACE_HOVER,
        "border": Palette.BORDER,
        "cell_padding_h": Spacing.SM,
        "cell_padding_v": Spacing.XS,
    }
    
    # Diff view
    DIFF = {
        "added_bg": Palette.DIFF_ADDED_BG,
        "removed_bg": Palette.DIFF_REMOVED_BG,
        "modified_bg": Palette.DIFF_MODIFIED_BG,
        "unchanged_bg": Palette.DIFF_UNCHANGED_BG,
        "added_border": Palette.SUCCESS_BORDER,
        "removed_border": Palette.ERROR_BORDER,
        "modified_border": Palette.WARNING_BORDER,
        "gutter_width": 2,
        "content_padding": Spacing.SM,
    }
    
    # Panel/Container
    PANEL = {
        "background": Palette.SURFACE,
        "border": Palette.BORDER,
        "padding": Spacing.LG,
    }
    
    PANEL_SECTION = {
        "background": Palette.SURFACE_ELEVATED,
        "border": Palette.BORDER,
        "padding": Spacing.MD,
        "margin": Spacing.SM,
    }
    
    # Split view
    SPLIT_VIEW = {
        "divider_width": 1,
        "divider_color": Palette.BORDER,
        "min_panel_width": 30,
    }
    
    # Breadcrumb
    BREADCRUMB = {
        "separator": " › ",
        "color": Palette.TEXT_MUTED,
        "active_color": Palette.TEXT_PRIMARY,
        "hover_color": Palette.BRAND_PRIMARY,
        "padding_h": Spacing.XS,
        "padding_v": 0,
    }
    
    # Progress
    PROGRESS = {
        "track_background": Palette.SURFACE_ELEVATED,
        "track_height": 1,
        "border_radius": BorderRadius.FULL,
    }


# CSS variable names (for Textual CSS)
CSS_VARIABLES = {
    # Brand
    "--brand-primary": Palette.BRAND_PRIMARY.hex,
    "--brand-secondary": Palette.BRAND_SECONDARY.hex,
    "--brand-accent": Palette.BRAND_ACCENT.hex,
    "--brand-accent-soft": Palette.BRAND_ACCENT_SOFT.hex,
    
    # Semantic
    "--success": Palette.SUCCESS.hex,
    "--success-bg": Palette.SUCCESS_BG.hex,
    "--success-border": Palette.SUCCESS_BORDER.hex,
    "--warning": Palette.WARNING.hex,
    "--warning-bg": Palette.WARNING_BG.hex,
    "--warning-border": Palette.WARNING_BORDER.hex,
    "--error": Palette.ERROR.hex,
    "--error-bg": Palette.ERROR_BG.hex,
    "--error-border": Palette.ERROR_BORDER.hex,
    "--info": Palette.INFO.hex,
    "--info-bg": Palette.INFO_BG.hex,
    "--info-border": Palette.INFO_BORDER.hex,
    
    # Surface
    "--surface": Palette.SURFACE.hex,
    "--surface-elevated": Palette.SURFACE_ELEVATED.hex,
    "--surface-hover": Palette.SURFACE_HOVER.hex,
    "--surface-pressed": Palette.SURFACE_PRESSED.hex,
    
    # Border
    "--border": Palette.BORDER.hex,
    "--border-focus": Palette.BORDER_FOCUS.hex,
    "--border-strong": Palette.BORDER_STRONG.hex,
    
    # Text
    "--text-primary": Palette.TEXT_PRIMARY.hex,
    "--text-secondary": Palette.TEXT_SECONDARY.hex,
    "--text-muted": Palette.TEXT_MUTED.hex,
    "--text-on-primary": Palette.TEXT_ON_PRIMARY.hex,
    "--text-on-accent": Palette.TEXT_ON_ACCENT.hex,
    
    # Spacing
    "--space-xs": f"{Spacing.XS}",
    "--space-sm": f"{Spacing.SM}",
    "--space-md": f"{Spacing.MD}",
    "--space-lg": f"{Spacing.LG}",
    "--space-xl": f"{Spacing.XL}",
    
    # Typography
    "--font-mono": Typography.MONO,
    "--font-ui": Typography.UI,
    
    # Shadows (reference)
    "--shadow-sm": Shadows.SM,
    "--shadow-md": Shadows.MD,
    "--shadow-lg": Shadows.LG,
    "--shadow-xl": Shadows.XL,
    
    # Border radius
    "--radius-sm": f"{BorderRadius.SM}",
    "--radius-md": f"{BorderRadius.MD}",
    "--radius-lg": f"{BorderRadius.LG}",
    "--radius-full": f"{BorderRadius.FULL}",
    
    # Transitions
    "--transition-fast": f"{Transitions.FAST}ms",
    "--transition-normal": f"{Transitions.NORMAL}ms",
    "--transition-slow": f"{Transitions.SLOW}ms",
}


def generate_css_variables() -> str:
    """Generate CSS custom properties string for Textual CSS."""
    lines = [":host {"]
    for name, value in CSS_VARIABLES.items():
        lines.append(f"    {name}: {value};")
    lines.append("}")
    return "\n".lines(lines)


def get_css_variables_dict() -> dict[str, str]:
    """Return CSS variables as dictionary for programmatic use."""
    return CSS_VARIABLES.copy()