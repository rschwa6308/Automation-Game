# Display-Related Constants
DEFAULT_SCREEN_WIDTH    = 1400
DEFAULT_SCREEN_HEIGHT   = 1000

MIN_SCREEN_WIDTH        = 300
MIN_SCREEN_HEIGHT       = 200

TARGET_FPS              = 60


# Layout-Related Constants
SHELF_HEIGHT            = 100
EDITOR_WIDTH            = 250
MODAL_WIDTH             = 400
MODAL_HEIGHT            = 650

PALETTE_ITEM_SIZE       = 64
PALETTE_ITEM_SPACING    = 8 
SHELF_ICON_SIZE         = 48    # (play/pause button size)
SHELF_ICON_SPACING      = 16
SHELF_ICON_PADDING      = 25
EDITOR_WIDGET_SPACING   = 8 


# Aesthetics-Related Constants
SHELF_BG_COLOR              = (127, 127, 127, 240)  # mostly opaque
EDITOR_BG_COLOR             = (127, 127, 127, 240)  # mostly opaque
SHELF_ICON_BG_COLOR         = (127, 127, 127, 191)  # 3/4 opaque
SHELF_ICON_BG_COLOR_PRESSED = (150, 150, 150, 191)  # 3/4 opaque
SHELF_ICON_COLOR            = (0, 0, 0)
SHELF_ICON_COLOR_PRESSED    = (63, 63, 63)
SHELF_ICON_COLOR_OFF        = (110, 110, 110)
MODAL_MAT_COLOR             = (0, 0, 0, 127)        # 1/2 opaque
MODAL_BG_COLOR              = (255, 255, 255)
MODAL_PRIMARY_COLOR         = (0, 0, 0) # (63, 63, 63)
MODAL_HIGHLIGHT_COLOR       = (191, 191, 191)
WARNING_COLOR               = (179, 58, 58)         # e.g. blinking read-only indicator


# Rendering-Related Constants
HIGHLIGHT_COLOR         = (253, 255, 50)

VIEWPORT_BG_COLOR       = (255, 255, 255)
GRID_LINE_COLOR         = (0, 0, 0)
WIRE_COLOR_OFF          = (127, 0, 0)
WIRE_COLOR_ON           = (255, 0, 0)

DEFAULT_CELL_SIZE           = 64
DEFAULT_GRID_LINE_WIDTH     = 2
MIN_GRID_LINE_WIDTH         = 1
MAX_GRID_LINE_WIDTH         = 5
DEFAULT_WIRE_WIDTH          = 4


# Misc Constants
SHELF_ANIMATION_SPEED   = 15    # pixels per frame
EDITOR_ANIMATION_SPEED  = 30    # pixels per frame

EDITOR_SCROLL_SPEED     = 50    # pixels per scroll event

LEVEL_SUBSTEP_INTERVAL  = 500   # milliseconds
FAST_FORWARD_FACTOR     = 5
SLOW_MOTION_FACTOR      = 0.2

BLINK_DURATION          = 20    # frames (for full on/off cycle)
