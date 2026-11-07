"""Build the Raqeem sidebar icon set.

Writes:
  raqim_sales/public/icons/raqeem-sidebar.svg  (sprite, symbols id="rq-<lucide name>")
  raqim_sales/public/js/raqeem_icon_names.js     (list of names the swapper may replace)

Style: duotone. A soft fill layer (orange-tinted through --rq-icon-fill) under a
bold 1.9px rounded outline, so the sidebar no longer looks like stock ERPNext's
thin Lucide line icons. The originals are untouched; see raqeem_icons.js to roll back.
"""
import os

HERE = os.path.dirname(os.path.abspath(__file__))
PUB = os.path.join(HERE, "../raqim_sales/public")

# name: (fill layer, outline layer)
ICONS = {
    "house": ('<path d="M4.5 10.2 12 4.2l7.5 6V20h-15z"/>',
              '<path d="M3 11 12 3.8 21 11"/><path d="M5.5 9.6V20h13V9.6"/><path d="M10 20v-5h4v5"/>'),
    "chart-column": ('<rect x="3" y="3" width="18" height="18" rx="5"/>',
                     '<rect x="3" y="3" width="18" height="18" rx="5"/><path d="M8 16.5v-4M12 16.5v-9M16 16.5v-6"/>'),
    "database": ('<path d="M5 6v12c0 1.7 3.1 3 7 3s7-1.3 7-3V6z"/>',
                 '<ellipse cx="12" cy="6" rx="7" ry="3"/><path d="M5 12c0 1.7 3.1 3 7 3s7-1.3 7-3"/><path d="M5 6v12c0 1.7 3.1 3 7 3s7-1.3 7-3V6"/>'),
    "settings": ('<circle cx="9" cy="7" r="2.6"/><circle cx="15" cy="12" r="2.6"/><circle cx="8" cy="17" r="2.6"/>',
                 '<path d="M4 7h2.4M11.6 7H20M4 12h8.4M17.6 12H20M4 17h1.4M10.6 17H20"/><circle cx="9" cy="7" r="2.6"/><circle cx="15" cy="12" r="2.6"/><circle cx="8" cy="17" r="2.6"/>'),
    "sheet": ('<path d="M6 3h8l4 4v14H6z"/>',
              '<path d="M14 3H7a1 1 0 0 0-1 1v16a1 1 0 0 0 1 1h10a1 1 0 0 0 1-1V7z"/><path d="M14 3v4h4"/><path d="M9.5 17v-3M12 17v-5.5M14.5 17v-2"/>'),
    "rocket": ('<path d="M12 3c3 2 4.5 5.5 4 10l-2 3h-4l-2-3c-.5-4.5 1-8 4-10z"/>',
               '<path d="M12 3c3 2 4.5 5.5 4 10l-2 3h-4l-2-3c-.5-4.5 1-8 4-10z"/><path d="M8 13l-3 2.5V19l3.5-1.5M16 13l3 2.5V19l-3.5-1.5"/><circle cx="12" cy="9" r="1.6"/><path d="M11 19.5 12 21l1-1.5"/>'),
    "package": ('<path d="M12 3 20 7.5 12 12 4 7.5z"/>',
                '<path d="M12 3 20 7.5v9L12 21l-8-4.5v-9z"/><path d="M4 7.5 12 12l8-4.5M12 12v9M8 5.3l8 4.5"/>'),
    "notepad-text": ('<rect x="5" y="4.5" width="14" height="16.5" rx="3"/>',
                     '<rect x="5" y="4.5" width="14" height="16.5" rx="3"/><path d="M9 3h6v3H9z"/><path d="M9 11h6M9 15h4"/>'),
    "receipt-text": ('<path d="M6 3h12v18l-2-1.5-2 1.5-2-1.5-2 1.5-2-1.5L6 21z"/>',
                     '<path d="M6 3h12v18l-2-1.5-2 1.5-2-1.5-2 1.5-2-1.5L6 21z"/><path d="M9 8h6M9 12h6M9 16h3"/>'),
    "store": ('<path d="M4 9 5.5 4h13L20 9z"/>',
              '<path d="M4 9l1.5-5h13L20 9"/><path d="M4 9c0 1.4 1.1 2.5 2.7 2.5S9.3 10.4 9.3 9c0 1.4 1.2 2.5 2.7 2.5s2.7-1.1 2.7-2.5c0 1.4 1.1 2.5 2.6 2.5S20 10.4 20 9"/><path d="M5.5 11.5V20h13v-8.5M10 20v-4h4v4"/>'),
    "folder-kanban": ('<path d="M3 7a2 2 0 0 1 2-2h4l2 2h8a2 2 0 0 1 2 2v9a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/>',
                      '<path d="M3 7a2 2 0 0 1 2-2h4l2 2h8a2 2 0 0 1 2 2v9a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/><path d="M8 11v5M12 11v3M16 11v6"/>'),
    "computer": ('<rect x="3" y="4" width="18" height="12" rx="2.5"/>',
                 '<rect x="3" y="4" width="18" height="12" rx="2.5"/><path d="M9 20h6M12 16v4M7 9h5"/><path d="M15 9.5h2"/>'),
    "wallet": ('<rect x="3" y="6.5" width="18" height="13.5" rx="3"/>',
               '<rect x="3" y="6.5" width="18" height="13.5" rx="3"/><path d="M5.5 6.5 15 3.5l1.2 3"/><path d="M21 11h-4a2 2 0 0 0 0 4h4"/>'),
    "arrow-left-to-line": ('<circle cx="12" cy="12" r="9"/>',
                           '<circle cx="12" cy="12" r="9"/><path d="M16 12H8M11 8.8 7.8 12l3.2 3.2"/>'),
    "arrow-right-from-line": ('<circle cx="12" cy="12" r="9"/>',
                              '<circle cx="12" cy="12" r="9"/><path d="M8 12h8M13 8.8l3.2 3.2-3.2 3.2"/>'),
    "wrench": ('<path d="M14.7 6.3a4 4 0 0 0-5.4 5.4L4 17l3 3 5.3-5.3a4 4 0 0 0 5.4-5.4l-2.4 2.4-2.6-.6-.6-2.6z"/>',
               '<path d="M14.7 6.3a4 4 0 0 0-5.4 5.4L4 17l3 3 5.3-5.3a4 4 0 0 0 5.4-5.4l-2.4 2.4-2.6-.6-.6-2.6z"/>'),
    "list-tree": ('<rect x="3" y="3.5" width="6" height="5" rx="1.5"/><rect x="13" y="10" width="8" height="4.5" rx="1.5"/><rect x="13" y="16.5" width="8" height="4.5" rx="1.5"/>',
                  '<rect x="3" y="3.5" width="6" height="5" rx="1.5"/><rect x="13" y="10" width="8" height="4.5" rx="1.5"/><rect x="13" y="16.5" width="8" height="4.5" rx="1.5"/><path d="M6 8.5v10.25h7M6 12.25h7"/>'),
    "grid-2x2-check": ('<rect x="3" y="3" width="18" height="18" rx="5"/>',
                       '<rect x="3" y="3" width="18" height="18" rx="5"/><path d="M8.3 12.4l2.6 2.6 4.8-5.6"/>'),
    "coins": ('<circle cx="9" cy="9" r="5.5"/>',
              '<circle cx="9" cy="9" r="5.5"/><path d="M14.4 9.6a5.5 5.5 0 1 1-4.8 4.8"/><path d="M9 6.8v4.4"/>'),
    "laptop": ('<rect x="5" y="5" width="14" height="10" rx="2"/>',
               '<rect x="5" y="5" width="14" height="10" rx="2"/><path d="M3 19h18l-2-4H5z"/>'),
    "trending-down": ('<path d="M3 7l6 6 4-4 8 8v3H3z"/>',
                      '<path d="M3 7l6 6 4-4 8 8"/><path d="M21 12v5h-5"/>'),
    "sprout": ('<path d="M12 12C12 8 9 6 5 6c0 4 3 6 7 6z"/><path d="M12 10.5c0-3.2 2.5-5.8 7-5.8 0 3.6-2.6 6-7 6z"/>',
               '<path d="M12 21v-9"/><path d="M12 12C12 8 9 6 5 6c0 4 3 6 7 6z"/><path d="M12 10.5c0-3.2 2.5-5.8 7-5.8 0 3.6-2.6 6-7 6"/><path d="M8 21h8"/>'),
    "move-horizontal": ('<rect x="3" y="6" width="18" height="12" rx="6"/>',
                        '<rect x="3" y="6" width="18" height="12" rx="6"/><path d="M8 12h8M10 9.5 7.5 12l2.5 2.5M14 9.5l2.5 2.5-2.5 2.5"/>'),
    "git-pull-request-arrow": ('<path d="M4 5h16v11H9l-5 4z"/>',
                               '<path d="M4 6a1 1 0 0 1 1-1h14a1 1 0 0 1 1 1v9a1 1 0 0 1-1 1H9l-5 4z"/><path d="M10 8.7a2 2 0 1 1 2.6 1.9c-.4.2-.6.5-.6.9v.3"/><path d="M12 13.6h.01"/>'),
    "book-open-text": ('<path d="M3 5.5C5.5 4 9 4 12 6c3-2 6.5-2 9-.5V19c-2.5-1.5-6-1.5-9 .5-3-2-6.5-2-9-.5z"/>',
                       '<path d="M3 5.5C5.5 4 9 4 12 6c3-2 6.5-2 9-.5V19c-2.5-1.5-6-1.5-9 .5-3-2-6.5-2-9-.5z"/><path d="M12 6v13.5M6 9h3M6 12.5h3M15 9h3"/>'),
    "scale": ('<path d="M5 8 2.5 14a2.5 2.5 0 0 0 5 0z"/><path d="M19 8l-2.5 6a2.5 2.5 0 0 0 5 0z"/>',
              '<path d="M12 4v16M8 20h8M5 8h14"/><path d="M5 8 2.5 14a2.5 2.5 0 0 0 5 0z"/><path d="M19 8l-2.5 6a2.5 2.5 0 0 0 5 0z"/><circle cx="12" cy="4" r="1"/>'),
    "list-todo": ('<rect x="3" y="4" width="6.5" height="6.5" rx="1.8"/><rect x="3" y="13.5" width="6.5" height="6.5" rx="1.8"/>',
                  '<rect x="3" y="4" width="6.5" height="6.5" rx="1.8"/><rect x="3" y="13.5" width="6.5" height="6.5" rx="1.8"/><path d="M4.7 7.3l1.3 1.3 2-2.3M13 7.2h8M13 16.8h8"/>'),
    "calendar-clock": ('<rect x="3" y="5" width="18" height="16" rx="3"/>',
                       '<rect x="3" y="5" width="18" height="16" rx="3"/><path d="M3 10h18M8 3v4M16 3v4"/><path d="M12 13v3l2 1.5"/>'),
    "receipt": ('<path d="M6 3h12v18l-2-1.5-2 1.5-2-1.5-2 1.5-2-1.5L6 21z"/>',
                '<path d="M6 3h12v18l-2-1.5-2 1.5-2-1.5-2 1.5-2-1.5L6 21z"/><path d="M12 6.5v10"/><path d="M14.4 8.6c-.4-.7-1.3-1.1-2.4-1.1-1.4 0-2.4.7-2.4 1.7 0 2.3 4.8 1.2 4.8 3.5 0 1-1.1 1.7-2.4 1.7-1.2 0-2.1-.5-2.5-1.2"/>'),
    "earth": ('<circle cx="12" cy="12" r="9"/>',
              '<circle cx="12" cy="12" r="9"/><path d="M3 12h18"/><path d="M12 3c2.5 2.5 3.5 5.5 3.5 9s-1 6.5-3.5 9c-2.5-2.5-3.5-5.5-3.5-9S9.5 5.5 12 3z"/>'),
    "washing-machine": ('<rect x="6" y="6" width="12" height="12" rx="2.5"/>',
                        '<rect x="6" y="6" width="12" height="12" rx="2.5"/><rect x="9.5" y="9.5" width="5" height="5" rx="1"/><path d="M9.5 3v3M14.5 3v3M9.5 18v3M14.5 18v3M3 9.5h3M3 14.5h3M18 9.5h3M18 14.5h3"/>'),
    "shopping-cart": ('<path d="M6.4 7H21l-2.5 7.5H7.7z"/>',
                      '<path d="M3 4h2.5l2.2 10.5h10.8L21 7H6.4"/><circle cx="9.5" cy="19" r="1.5"/><circle cx="17" cy="19" r="1.5"/>'),
    "building-complex": ('<path d="M10 9h10v12H10z"/>',
                         '<path d="M4 21V8l6-4v17M10 9h10v12M3 21h18"/><path d="M14 13h2M14 17h2M6.5 11h1.5M6.5 15h1.5"/>'),
    "handshake": ('<path d="M4 5h11v8H8l-4 3z"/>',
                  '<path d="M4 6a1 1 0 0 1 1-1h9a1 1 0 0 1 1 1v6a1 1 0 0 1-1 1H8l-4 3z"/><path d="M15 9h4a1 1 0 0 1 1 1v8l-3-2.5h-5a1 1 0 0 1-1-1V13"/>'),
    "headset": ('<rect x="3" y="13" width="4" height="6" rx="1.5"/><rect x="17" y="13" width="4" height="6" rx="1.5"/>',
                '<path d="M4 14v-2a8 8 0 0 1 16 0v2"/><rect x="3" y="13" width="4" height="6" rx="1.5"/><rect x="17" y="13" width="4" height="6" rx="1.5"/><path d="M19 19c0 1.5-2 2.5-5 2.5"/>'),
    "truck": ('<rect x="2.5" y="6" width="11" height="10" rx="1.5"/>',
              '<rect x="2.5" y="6" width="11" height="10" rx="1.5"/><path d="M13.5 9h4l3.5 4v3h-7.5"/><circle cx="7" cy="17.5" r="2"/><circle cx="17" cy="17.5" r="2"/>'),
    "caravan": ('<rect x="4" y="11" width="16" height="9" rx="2"/>',
                '<rect x="4" y="11" width="16" height="9" rx="2"/><path d="M12 3v8M9 6l3-3 3 3M9 15.5h6"/>'),
    "factory": ('<path d="M3 20V11l5 3v-3l5 3v-3l5 3V4h3v16z"/>',
                '<path d="M3 20V11l5 3v-3l5 3v-3l5 3V4h3v16z"/><path d="M7 17h2M12 17h2"/>'),
    "person-standing": ('<rect x="3" y="5" width="18" height="14" rx="3"/>',
                        '<rect x="3" y="5" width="18" height="14" rx="3"/><circle cx="9" cy="10.5" r="2"/><path d="M6 15.5c.6-1.3 1.7-2 3-2s2.4.7 3 2M14.5 10h3.5M14.5 14h3.5"/>'),
    "file-question-mark": ('<circle cx="12" cy="12" r="9"/>',
                           '<circle cx="12" cy="12" r="9"/><path d="M12 7.5v5.5"/><path d="M12 16.5h.01"/>'),
    "calendar-days": ('<rect x="3" y="5" width="18" height="16" rx="3"/>',
                      '<rect x="3" y="5" width="18" height="16" rx="3"/><path d="M3 10h18M8 3v4M16 3v4"/><path d="M8 14h.01M12 14h.01M16 14h.01M8 17.5h.01M12 17.5h.01"/>'),
    "calendar-check-2": ('<rect x="3" y="5" width="18" height="16" rx="3"/>',
                         '<rect x="3" y="5" width="18" height="16" rx="3"/><path d="M3 10h18M8 3v4M16 3v4"/><path d="M8.8 15.2l2.2 2.2 4.2-4.6"/>'),
    "inspection-panel": ('<circle cx="10.5" cy="10.5" r="6.5"/>',
                         '<circle cx="10.5" cy="10.5" r="6.5"/><path d="M15.4 15.4 21 21"/><path d="M7.8 10.6l1.9 1.9 3.3-3.6"/>'),
    "goal": ('<circle cx="11" cy="13" r="8"/>',
             '<circle cx="11" cy="13" r="8"/><circle cx="11" cy="13" r="4"/><path d="M11 13l8-8M16 5h3v3"/>'),
    "star": ('<path d="M12 3.5l2.6 5.3 5.9.9-4.2 4.1 1 5.8L12 16.9l-5.3 2.7 1-5.8-4.2-4.1 5.9-.9z"/>',
             '<path d="M12 3.5l2.6 5.3 5.9.9-4.2 4.1 1 5.8L12 16.9l-5.3 2.7 1-5.8-4.2-4.1 5.9-.9z"/>'),
    "square-activity": ('<rect x="3" y="3" width="18" height="18" rx="5"/>',
                        '<rect x="3" y="3" width="18" height="18" rx="5"/><path d="M7 12h2.5l1.5-3.5 2.5 7 1.5-3.5H17"/>'),
    "thumbs-up": ('<path d="M7 10v11H4a1 1 0 0 1-1-1v-9a1 1 0 0 1 1-1z"/><path d="M7 10l4-7.5a2.5 2.5 0 0 1 3 3.2L13.4 10h5.8a2 2 0 0 1 1.9 2.6l-2.2 7A2 2 0 0 1 17 21H7z"/>',
                  '<path d="M7 10v11"/><path d="M7 10l4-7.5a2.5 2.5 0 0 1 3 3.2L13.4 10h5.8a2 2 0 0 1 1.9 2.6l-2.2 7A2 2 0 0 1 17 21H4a1 1 0 0 1-1-1v-9a1 1 0 0 1 1-1z"/>'),
    "users": ('<circle cx="9" cy="8" r="3.5"/>',
              '<circle cx="9" cy="8" r="3.5"/><path d="M3 20c.8-3.4 3.2-5 6-5s5.2 1.6 6 5"/><path d="M16 4.6a3.5 3.5 0 0 1 0 6.8"/><path d="M18 15c1.6.5 2.7 2.2 3 5"/>'),
    "users-round": ('<circle cx="10" cy="8" r="4"/>',
                    '<circle cx="10" cy="8" r="4"/><path d="M3.5 20c.9-3.6 3.4-5.5 6.5-5.5 1.5 0 2.9.4 4 1.3"/><path d="M18 14v6M15 17h6"/>'),
    "lightbulb": ('<path d="M12 3a6 6 0 0 0-3.6 10.8c.6.5 1 1.3 1 2.2h5.2c0-.9.4-1.7 1-2.2A6 6 0 0 0 12 3z"/>',
                  '<path d="M12 3a6 6 0 0 0-3.6 10.8c.6.5 1 1.3 1 2.2h5.2c0-.9.4-1.7 1-2.2A6 6 0 0 0 12 3z"/><path d="M9.5 18.5h5M10.5 21h3"/>'),
    "user": ('<circle cx="12" cy="8" r="4"/>',
             '<circle cx="12" cy="8" r="4"/><path d="M4.5 20.5c1-3.8 4-5.8 7.5-5.8s6.5 2 7.5 5.8"/>'),
    "funnel": ('<path d="M3 4h18l-7 8.5V19l-4 2v-8.5z"/>',
               '<path d="M3 4h18l-7 8.5V19l-4 2v-8.5z"/>'),
    "book-text": ('<path d="M5 4.5A1.5 1.5 0 0 1 6.5 3H19v15H6.5A1.5 1.5 0 0 0 5 19.5z"/>',
                  '<path d="M5 19.5v-15A1.5 1.5 0 0 1 6.5 3H19v15H6.5A1.5 1.5 0 0 0 5 19.5 1.5 1.5 0 0 0 6.5 21H19"/><path d="M9 7.5h6M9 11h4"/>'),
    "dollar-sign": ('<circle cx="12" cy="12" r="9"/>',
                    '<circle cx="12" cy="12" r="9"/><path d="M7.5 15l3-3 2 2 4-4.5"/><path d="M14 9.5h2.5V12"/>'),
    "scroll-text": ('<rect x="7" y="3" width="13" height="15" rx="2.5"/>',
                    '<rect x="7" y="3" width="13" height="15" rx="2.5"/><path d="M4 7v11.5A2.5 2.5 0 0 0 6.5 21H16"/><path d="M10.5 8h6M10.5 12h6"/>'),
}

# Dock (app rail) icons: Frappe 16 names them "<thing>-soft" (module-icons.svg).
_I = ICONS
DOCK = {
    "sliders-soft": _I["settings"],
    "calculator-soft": ('<rect x="5" y="3" width="14" height="18" rx="3"/>',
                        '<rect x="5" y="3" width="14" height="18" rx="3"/><rect x="8" y="6" width="8" height="3.5" rx="1"/>'
                        '<circle cx="8.8" cy="13.2" r=".5"/><circle cx="12" cy="13.2" r=".5"/><circle cx="15.2" cy="13.2" r=".5"/>'
                        '<circle cx="8.8" cy="17" r=".5"/><circle cx="12" cy="17" r=".5"/><circle cx="15.2" cy="17" r=".5"/>'),
    "storefront-soft": _I["store"],
    "shopping-cart-soft": _I["shopping-cart"],
    "shelf-rack-soft": ('<rect x="7" y="5" width="4.5" height="4" rx=".8"/><rect x="12.5" y="11" width="5" height="4" rx=".8"/><rect x="6.5" y="17" width="6" height="4" rx=".8"/>',
                        '<path d="M4 3v18M20 3v18M4 9h16M4 15h16M4 21h16"/><rect x="7" y="5" width="4.5" height="4" rx=".8"/><rect x="12.5" y="11" width="5" height="4" rx=".8"/><rect x="6.5" y="17" width="6" height="4" rx=".8"/>'),
    "factory-soft": _I["factory"],
    "gantt-chart-soft": ('<rect x="3" y="3" width="18" height="18" rx="5"/>',
                         '<rect x="3" y="3" width="18" height="18" rx="5"/><path d="M7 8h6M10 12h7M8 16h5"/>'),
    "asset-hand-soft": ('<rect x="9" y="3.5" width="8" height="7" rx="1.5"/>',
                        '<rect x="9" y="3.5" width="8" height="7" rx="1.5"/><path d="M13 3.5v3"/><path d="M3 15h3l4 2h4a1.5 1.5 0 0 0 0-3h-3"/><path d="M14 17l5-2.2a1.6 1.6 0 0 1 1.5 2.8L14 21H3"/>'),
    "quality-seal-soft": ('<circle cx="12" cy="9.5" r="6"/>',
                          '<circle cx="12" cy="9.5" r="6"/><path d="M8.6 14.5 7 21l5-2.5 5 2.5-1.6-6.5"/><path d="M9.5 9.6l1.7 1.7 3.3-3.4"/>'),
    "handshake-soft": _I["handshake"],
    "headset-soft": _I["headset"],
    "portal-user-soft": ('<rect x="3" y="4" width="18" height="16" rx="3"/>',
                         '<rect x="3" y="4" width="18" height="16" rx="3"/><path d="M3 8.5h18"/><circle cx="12" cy="12.8" r="2"/><path d="M8.5 18c.7-1.4 2-2.2 3.5-2.2s2.8.8 3.5 2.2"/>'),
    "code-app-soft": ('<rect x="3" y="3" width="18" height="18" rx="5"/>',
                      '<rect x="3" y="3" width="18" height="18" rx="5"/><path d="M9.5 9.5 7 12l2.5 2.5M14.5 9.5 17 12l-2.5 2.5M12.8 8.5l-1.6 7"/>'),
    "users-soft": _I["users"],
    "email-envelope-soft": ('<rect x="3" y="5" width="18" height="14" rx="3"/>',
                            '<rect x="3" y="5" width="18" height="14" rx="3"/><path d="M4 7.5l8 5.5 8-5.5"/>'),
    "website-browser-soft": ('<path d="M3 9V7a3 3 0 0 1 3-3h12a3 3 0 0 1 3 3v2z"/>',
                             '<rect x="3" y="4" width="18" height="16" rx="3"/><path d="M3 9h18M7 13h6M7 16h10"/><circle cx="6.3" cy="6.5" r=".4"/><circle cx="8.8" cy="6.5" r=".4"/>'),
    "data-table-soft": ('<path d="M3 9.5V7a3 3 0 0 1 3-3h12a3 3 0 0 1 3 3v2.5z"/>',
                        '<rect x="3" y="4" width="18" height="16" rx="3"/><path d="M3 9.5h18M3 14.75h18M9 9.5V20"/>'),
    "workflow-builder-soft": ('<rect x="3" y="3" width="7" height="6" rx="1.8"/><rect x="14" y="9" width="7" height="6" rx="1.8"/><rect x="3" y="15" width="7" height="6" rx="1.8"/>',
                              '<rect x="3" y="3" width="7" height="6" rx="1.8"/><rect x="14" y="9" width="7" height="6" rx="1.8"/><rect x="3" y="15" width="7" height="6" rx="1.8"/><path d="M10 6h7.5v3M10 18h7.5v-3"/>'),
    "printing-printer-soft": ('<rect x="3" y="9" width="18" height="8" rx="2.5"/>',
                              '<path d="M7 9V3.5h10V9"/><rect x="3" y="9" width="18" height="8" rx="2.5"/><path d="M7 14h10v6.5H7z"/><circle cx="17.5" cy="12" r=".4"/>'),
    "integrations-cable-soft": ('<path d="M6 7h12v3a6 6 0 0 1-12 0z"/>',
                                '<path d="M9 3v4M15 3v4"/><path d="M6 7h12v3a6 6 0 0 1-12 0z"/><path d="M12 16v5"/>'),
    "contacts-cards-soft": ('<rect x="4" y="3" width="16" height="18" rx="3"/>',
                            '<rect x="4" y="3" width="16" height="18" rx="3"/><circle cx="12" cy="10" r="2.5"/><path d="M8 16.5c.8-1.6 2.3-2.5 4-2.5s3.2.9 4 2.5M2.5 8h3M2.5 12h3M2.5 16h3"/>'),
    "automation-cycle-soft": ('<circle cx="12" cy="12" r="6.5"/>',
                              '<path d="M20 11a8 8 0 0 0-14.3-4.3L4 8.5M4 4v4.5h4.5"/><path d="M4 13a8 8 0 0 0 14.3 4.3L20 15.5M20 20v-4.5h-4.5"/><path d="M12.8 8 10.3 12.3h3.6L11.4 16"/>'),
    "geo-pin-soft": ('<path d="M12 21s-6.5-5.6-6.5-11a6.5 6.5 0 0 1 13 0c0 5.4-6.5 11-6.5 11z"/>',
                     '<path d="M12 21s-6.5-5.6-6.5-11a6.5 6.5 0 0 1 13 0c0 5.4-6.5 11-6.5 11z"/><circle cx="12" cy="10" r="2.5"/>'),
    "system-monitor-soft": ('<rect x="3" y="4" width="18" height="12" rx="2.5"/>',
                            '<rect x="3" y="4" width="18" height="12" rx="2.5"/><path d="M9 20h6M12 16v4"/><path d="M6.5 10.5h2.5l1.5-2.5 2.5 5 1.5-2.5h3"/>'),
}
ICONS = {**ICONS, **DOCK}

FILL = ('<g stroke="none" style="fill:var(--rq-icon-fill,currentColor);'
        'fill-opacity:var(--rq-icon-fill-opacity,.22)">')
LINE = ('<g fill="none" stroke="currentColor" stroke-width="1.9" '
        'stroke-linecap="round" stroke-linejoin="round">')

out = ['<!-- Raqeem sidebar icons (generated by scripts/gen_icons.py) -->',
       '<svg id="raqeem-symbols" aria-hidden="true" style="display:none" xmlns="http://www.w3.org/2000/svg">']
for name, (fill, line) in ICONS.items():
    out.append(f'  <symbol viewBox="0 0 24 24" id="rq-{name}">{FILL}{fill}</g>{LINE}{line}</g></symbol>')
out.append('</svg>\n')
os.makedirs(os.path.join(PUB, "icons"), exist_ok=True)
open(os.path.join(PUB, "icons/raqeem-sidebar.svg"), "w", encoding="utf-8").write("\n".join(out))

names = ",\n\t".join(f'"{n}"' for n in ICONS)
open(os.path.join(PUB, "js/raqeem_icon_names.js"), "w", encoding="utf-8").write(
    "/* generated by scripts/gen_icons.py — icon names that have a Raqeem version */\n"
    f"window.RAQEEM_ICON_NAMES = [\n\t{names},\n];\n")
print(len(ICONS), "icons")


# ---- CSS-drawn dock icons (no JavaScript involved) -------------------------
# Each dock tile we drew gets its <svg> hidden and the Raqeem drawing painted
# with two CSS masks: ::before = orange-tinted fill layer, ::after = outline.
# Matched with :has(use[href="#icon-<name>"]); other tiles are left alone.
from urllib.parse import quote

def mask_uri(inner, stroke):
    g = ('<g fill="none" stroke="black" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round">'
         if stroke else '<g fill="black">')
    svg = f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24">{g}{inner}</g></svg>'
    return 'url("data:image/svg+xml,' + quote(svg, safe=" =:/,.-") + '")'

def group(suffix=""):
    return ",\n".join(f'.dock .dock-item-icon:has(use[href="#icon-{n}"]){suffix}' for n in DOCK)

css = f"""/* ==========================================================================
   ALRAQEEM — dock icons drawn in CSS (generated by scripts/gen_icons.py)
   ROLLBACK: remove raqeem_icons.css from app_include_css in hooks.py.
   ========================================================================== */
{group()} {{
    position: relative;
}}
{group(" > svg")} {{
    visibility: hidden;
}}
{group("::before")},
{group("::after")} {{
    content: "";
    position: absolute;
    left: 50%; top: 50%;
    width: 26px; height: 26px;
    transform: translate(-50%, -50%);
    -webkit-mask: var(--rqm) center / contain no-repeat;
    mask: var(--rqm) center / contain no-repeat;
    pointer-events: none;
}}
{group("::before")} {{ --rqm: var(--rqm-fill); background: var(--rq-accent, #f97316); opacity: .30; }}
{group("::after")} {{ --rqm: var(--rqm-line); background: currentColor; }}
.dock .dock-item:hover .dock-item-icon::before {{ opacity: .45; }}
.dock .dock-item.active .dock-item-icon::before {{ background: #1a0d03; opacity: .22; }}

"""
for name in DOCK:
    fill, line = ICONS[name]
    css += (f'.dock .dock-item-icon:has(use[href="#icon-{name}"]) {{\n'
            f'    --rqm-fill: {mask_uri(fill, False)};\n'
            f'    --rqm-line: {mask_uri(line, True)};\n}}\n')
open(os.path.join(PUB, "css/raqeem_icons.css"), "w", encoding="utf-8").write(css)
print("wrote raqeem_icons.css")
