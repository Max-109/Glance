from __future__ import annotations

from urllib.parse import quote

from PySide6.QtCore import QObject, Slot


ICON_PATHS = {
    "audio-lines": (
        '<path d="M2 10v3" />'
        '<path d="M6 6v11" />'
        '<path d="M10 3v18" />'
        '<path d="M14 8v7" />'
        '<path d="M18 5v13" />'
        '<path d="M22 10v3" />'
    ),
    "bot": (
        '<path d="M12 8V4H8" />'
        '<rect width="16" height="12" x="4" y="8" rx="2" />'
        '<path d="M2 14h2" />'
        '<path d="M20 14h2" />'
        '<path d="M15 13v2" />'
        '<path d="M9 13v2" />'
    ),
    "brain": (
        '<path d="M12 18V5" />'
        '<path d="M15 13a4.17 4.17 0 0 1-3-4 4.17 4.17 0 0 1-3 4" />'
        '<path d="M17.598 6.5A3 3 0 1 0 12 5a3 3 0 1 0-5.598 1.5" />'
        '<path d="M17.997 5.125a4 4 0 0 1 2.526 5.77" />'
        '<path d="M18 18a4 4 0 0 0 2-7.464" />'
        '<path d="M19.967 17.483A4 4 0 1 1 12 18a4 4 0 1 1-7.967-.517" />'
        '<path d="M6 18a4 4 0 0 1-2-7.464" />'
        '<path d="M6.003 5.125a4 4 0 0 0-2.526 5.77" />'
    ),
    "brain-circuit": (
        '<path d="M12 5a3 3 0 1 0-5.997.125 4 4 0 0 0-2.526 5.77 4 4 0 0 0 .556 6.588A4 4 0 1 0 12 18Z" />'
        '<path d="M9 13a4.5 4.5 0 0 0 3-4" />'
        '<path d="M6.003 5.125A3 3 0 0 0 6.401 6.5" />'
        '<path d="M3.477 10.896a4 4 0 0 1 .585-.396" />'
        '<path d="M6 18a4 4 0 0 1-1.967-.516" />'
        '<path d="M12 13h4" />'
        '<path d="M12 18h6a2 2 0 0 1 2 2v1" />'
        '<path d="M12 8h8" />'
        '<path d="M16 8V5a2 2 0 0 1 2-2" />'
        '<circle cx="16" cy="13" r=".5" />'
        '<circle cx="18" cy="3" r=".5" />'
        '<circle cx="20" cy="21" r=".5" />'
        '<circle cx="20" cy="8" r=".5" />'
    ),
    "check": '<path d="M20 6 9 17l-5-5" />',
    "chevron-down": '<path d="m6 9 6 6 6-6" />',
    "circle-question-mark": (
        '<circle cx="12" cy="12" r="10" />'
        '<path d="M9.09 9a3 3 0 0 1 5.83 1c0 2-3 3-3 3" />'
        '<path d="M12 17h.01" />'
    ),
    "clock-3": ('<circle cx="12" cy="12" r="10" /><path d="M12 6v6h4" />'),
    "eye": (
        '<path d="M2.062 12.348a1 1 0 0 1 0-.696 10.75 10.75 0 0 1 19.876 0 1 1 0 0 1 0 .696 10.75 10.75 0 0 1-19.876 0" />'
        '<circle cx="12" cy="12" r="3" />'
    ),
    "gauge": ('<path d="m12 14 4-4" /><path d="M3.34 19a10 10 0 1 1 17.32 0" />'),
    "headphones": '<path d="M3 14h3a2 2 0 0 1 2 2v3a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-7a9 9 0 0 1 18 0v7a2 2 0 0 1-2 2h-1a2 2 0 0 1-2-2v-3a2 2 0 0 1 2-2h3" />',
    "history": (
        '<path d="M3 12a9 9 0 1 0 9-9 9.75 9.75 0 0 0-6.74 2.74L3 8" />'
        '<path d="M3 3v5h5" />'
        '<path d="M12 7v5l4 2" />'
    ),
    "key-round": (
        '<path d="M2.586 17.414A2 2 0 0 0 2 18.828V21a1 1 0 0 0 1 1h3a1 1 0 0 0 1-1v-1a1 1 0 0 1 1-1h1a1 1 0 0 0 1-1v-1a1 1 0 0 1 1-1h.172a2 2 0 0 0 1.414-.586l.814-.814a6.5 6.5 0 1 0-4-4z" />'
        '<circle cx="16.5" cy="7.5" r=".5" fill="currentColor" />'
    ),
    "languages": (
        '<path d="m5 8 6 6" />'
        '<path d="m4 14 6-6 2-3" />'
        '<path d="M2 5h12" />'
        '<path d="M7 2h1" />'
        '<path d="m22 22-5-10-5 10" />'
        '<path d="M14 18h6" />'
    ),
    "link-2": (
        '<path d="M9 17H7A5 5 0 0 1 7 7h2" />'
        '<path d="M15 7h2a5 5 0 1 1 0 10h-2" />'
        '<line x1="8" x2="16" y1="12" y2="12" />'
    ),
    "message-square-quote": (
        '<path d="M14 14a2 2 0 0 0 2-2V8h-2" />'
        '<path d="M22 17a2 2 0 0 1-2 2H6.828a2 2 0 0 0-1.414.586l-2.202 2.202A.71.71 0 0 1 2 21.286V5a2 2 0 0 1 2-2h16a2 2 0 0 1 2 2z" />'
        '<path d="M8 14a2 2 0 0 0 2-2V8H8" />'
    ),
    "mic": (
        '<path d="M12 19v3" />'
        '<path d="M19 10v2a7 7 0 0 1-14 0v-2" />'
        '<rect x="9" y="2" width="6" height="13" rx="3" />'
    ),
    "rotate-ccw": (
        '<path d="M3 12a9 9 0 1 0 9-9 9.75 9.75 0 0 0-6.74 2.74L3 8" />'
        '<path d="M3 3v5h5" />'
    ),
    "scan-search": (
        '<path d="M3 7V5a2 2 0 0 1 2-2h2" />'
        '<path d="M17 3h2a2 2 0 0 1 2 2v2" />'
        '<path d="M21 17v2a2 2 0 0 1-2 2h-2" />'
        '<path d="M7 21H5a2 2 0 0 1-2-2v-2" />'
        '<circle cx="12" cy="12" r="3" />'
        '<path d="m16 16-1.9-1.9" />'
    ),
    "settings-2": (
        '<path d="M14 17H5" />'
        '<path d="M19 7h-9" />'
        '<circle cx="17" cy="17" r="3" />'
        '<circle cx="7" cy="7" r="3" />'
    ),
    "speech": (
        '<path d="M8.8 20v-4.1l1.9.2a2.3 2.3 0 0 0 2.164-2.1V8.3A5.37 5.37 0 0 0 2 8.25c0 2.8.656 3.054 1 4.55a5.77 5.77 0 0 1 .029 2.758L2 20" />'
        '<path d="M19.8 17.8a7.5 7.5 0 0 0 .003-10.603" />'
        '<path d="M17 15a3.5 3.5 0 0 0-.025-4.975" />'
    ),
    "sun-moon": (
        '<path d="M12 2v2" />'
        '<path d="M14.837 16.385a6 6 0 1 1-7.223-7.222c.624-.147.97.66.715 1.248a4 4 0 0 0 5.26 5.259c.589-.255 1.396.09 1.248.715" />'
        '<path d="M16 12a4 4 0 0 0-4-4" />'
        '<path d="m19 5-1.256 1.256" />'
        '<path d="M20 12h2" />'
    ),
    "trash-2": (
        '<path d="M10 11v6" />'
        '<path d="M14 11v6" />'
        '<path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6" />'
        '<path d="M3 6h18" />'
        '<path d="M8 6V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2" />'
    ),
    "triangle-alert": (
        '<path d="m21.73 18-8-14a2 2 0 0 0-3.48 0l-8 14A2 2 0 0 0 4 21h16a2 2 0 0 0 1.73-3" />'
        '<path d="M12 9v4" />'
        '<path d="M12 17h.01" />'
    ),
    "x": ('<path d="M18 6 6 18" /><path d="m6 6 12 12" />'),
    "zap": '<path d="M4 14a1 1 0 0 1-.78-1.63l9.9-10.2a.5.5 0 0 1 .86.46l-1.92 6.02A1 1 0 0 0 13 10h7a1 1 0 0 1 .78 1.63l-9.9 10.2a.5.5 0 0 1-.86-.46l1.92-6.02A1 1 0 0 0 11 14z" />',
}


class IconLibrary(QObject):
    @Slot(str, str, result=str)
    def svgData(self, name: str, color: str) -> str:
        path_markup = ICON_PATHS.get(name, "")
        if not path_markup:
            return ""
        svg_markup = (
            f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" '
            f'fill="none" stroke="{color}" stroke-width="2" '
            f'stroke-linecap="round" stroke-linejoin="round">'
            f"{path_markup.replace('currentColor', color)}</svg>"
        )
        return f"data:image/svg+xml;utf8,{quote(svg_markup)}"
