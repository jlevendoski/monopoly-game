"""
Board visualization widget.

Draws the Monopoly board with properties, players, and buildings.
Pokemon-themed properties display Pokemon images with evolution chains.
"""

from typing import Optional
from PyQt6.QtWidgets import QWidget, QToolTip
from PyQt6.QtCore import Qt, QRect, QPoint, pyqtSignal
from PyQt6.QtGui import QPainter, QColor, QFont, QPen, QBrush, QFontMetrics, QPixmap

from shared.constants import BOARD_SIZE, BOARD_SPACES
from client.gui.styles import (
    PROPERTY_COLORS, PLAYER_COLORS, SPACE_COLORS,
    BACKGROUND_COLOR, BOARD_EDGE_COLOR, MORTGAGED_OVERLAY
)
from client.gui.pokemon_image_cache import get_image_cache


class BoardWidget(QWidget):
    """
    Widget that draws the Monopoly board.
    
    The board is drawn as a square with spaces around the edges.
    Players are shown as colored circles on their current positions.
    """
    
    # Signal emitted when a space is clicked
    space_clicked = pyqtSignal(int)  # position
    
    # Board layout: positions 0-9 bottom, 10-19 left, 20-29 top, 30-39 right
    SPACES_PER_SIDE = 11  # Including corners
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        self._game_state: Optional[dict] = None
        self._player_id: Optional[str] = None
        self._hovered_space: Optional[int] = None
        
        # Enable mouse tracking for hover effects
        self.setMouseTracking(True)
        
        # Minimum size
        self.setMinimumSize(500, 500)
    
    def set_game_state(self, state: dict, player_id: str) -> None:
        """Update the game state and redraw."""
        self._game_state = state
        self._player_id = player_id
        self.update()
    
    def clear(self) -> None:
        """Clear the game state."""
        self._game_state = None
        self.update()
    
    def _get_space_rect(self, position: int) -> QRect:
        """Get the rectangle for a board position."""
        size = min(self.width(), self.height())
        margin = 10
        board_size = size - 2 * margin
        
        # Corner spaces are square, edge spaces are rectangular
        corner_size = board_size // 8
        edge_width = (board_size - 2 * corner_size) // 9
        edge_height = corner_size
        
        if position == 0:  # GO - bottom right corner
            return QRect(
                margin + board_size - corner_size,
                margin + board_size - corner_size,
                corner_size, corner_size
            )
        elif position == 10:  # Jail - bottom left corner
            return QRect(margin, margin + board_size - corner_size, corner_size, corner_size)
        elif position == 20:  # Free Parking - top left corner
            return QRect(margin, margin, corner_size, corner_size)
        elif position == 30:  # Go To Jail - top right corner
            return QRect(margin + board_size - corner_size, margin, corner_size, corner_size)
        elif 1 <= position <= 9:  # Bottom edge (right to left)
            x = margin + board_size - corner_size - (position) * edge_width
            y = margin + board_size - edge_height
            return QRect(x, y, edge_width, edge_height)
        elif 11 <= position <= 19:  # Left edge (bottom to top)
            x = margin
            y = margin + board_size - corner_size - (position - 10) * edge_width
            return QRect(x, y, edge_height, edge_width)
        elif 21 <= position <= 29:  # Top edge (left to right)
            x = margin + corner_size + (position - 21) * edge_width
            y = margin
            return QRect(x, y, edge_width, edge_height)
        elif 31 <= position <= 39:  # Right edge (top to bottom)
            x = margin + board_size - edge_height
            y = margin + corner_size + (position - 31) * edge_width
            return QRect(x, y, edge_height, edge_width)
        
        return QRect()
    
    def _position_from_point(self, point: QPoint) -> Optional[int]:
        """Get the board position from a point."""
        for pos in range(BOARD_SIZE):
            if self._get_space_rect(pos).contains(point):
                return pos
        return None
    
    def paintEvent(self, event) -> None:
        """Draw the board."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Draw background
        size = min(self.width(), self.height())
        margin = 10
        board_size = size - 2 * margin
        
        # Board background (center area)
        painter.fillRect(
            margin, margin, board_size, board_size,
            BACKGROUND_COLOR
        )
        
        # Draw "POKEMON" in center with subtitle
        painter.setPen(QPen(BOARD_EDGE_COLOR))
        font = QFont("Arial", 24, QFont.Weight.Bold)
        painter.setFont(font)
        
        # Main title
        title_rect = QRect(margin, margin + board_size // 3, board_size, board_size // 4)
        painter.drawText(title_rect, Qt.AlignmentFlag.AlignCenter, "POKÉMON")
        
        # Subtitle
        font.setPointSize(12)
        painter.setFont(font)
        subtitle_rect = QRect(margin, margin + board_size // 2, board_size, board_size // 6)
        painter.drawText(subtitle_rect, Qt.AlignmentFlag.AlignCenter, "MONOPOLY")
        
        # Draw all spaces
        for pos in range(BOARD_SIZE):
            self._draw_space(painter, pos)
        
        # Draw players
        if self._game_state:
            self._draw_players(painter)
    
    def _draw_space(self, painter: QPainter, position: int) -> None:
        """Draw a single board space."""
        # Save painter state at start to prevent any color/brush bleeding between spaces
        painter.save()
        
        rect = self._get_space_rect(position)
        space_data = BOARD_SPACES.get(position, {})
        space_type = space_data.get("type", "")
        space_name = space_data.get("name", f"Space {position}")
        space_group = space_data.get("group")
        space_cost = space_data.get("cost")
        
        # Get property data if we have game state
        prop_data = None
        pokemon_data = None
        item_data = None
        if self._game_state:
            prop_data = self._game_state.get("board", {}).get(str(position))
            if prop_data:
                pokemon_data = prop_data.get("pokemon")
                item_data = prop_data.get("item")
                # Use Pokemon name if available (for color properties)
                if pokemon_data and pokemon_data.get("name"):
                    space_name = pokemon_data["name"]
                # Use item name if available (for railroads/utilities)
                elif item_data and item_data.get("name"):
                    space_name = item_data["name"]
        
        # Background color - properties get WHITE background, special spaces get their color
        # The property COLOR is shown only in the color bar, not the whole space
        if space_type == "PROPERTY" or space_type == "RAILROAD" or space_type == "UTILITY":
            # Purchasable properties have white/cream background
            bg_color = QColor(255, 250, 240)  # Cream/off-white
        elif space_type in SPACE_COLORS:
            bg_color = SPACE_COLORS[space_type]
        else:
            bg_color = QColor(255, 255, 255)
        
        # Draw background
        painter.fillRect(rect, bg_color)
        
        # Draw border
        painter.setPen(QPen(Qt.GlobalColor.black, 1))
        painter.drawRect(rect)
        
        # For Pokemon-themed properties, use new layout:
        # Top 15%: color bar, Middle 70%: image + name, Bottom 15%: price
        is_vertical = position in range(11, 20) or position in range(31, 40)
        
        if space_type == "PROPERTY" and space_group and space_group in PROPERTY_COLORS:
            if pokemon_data:
                self._draw_pokemon_property(
                    painter, rect, position, space_group, 
                    pokemon_data, space_cost, is_vertical, prop_data
                )
            else:
                # Fallback to old style if no Pokemon data
                self._draw_classic_property(
                    painter, rect, position, space_group, 
                    space_name, space_cost, is_vertical, prop_data
                )
        else:
            # Non-property spaces (railroads, utilities, special spaces)
            self._draw_non_property_space(
                painter, rect, position, space_type, 
                space_name, space_cost, is_vertical, prop_data, item_data
            )
        
        # Draw mortgaged overlay (on top of everything)
        if prop_data and prop_data.get("is_mortgaged"):
            painter.fillRect(rect, MORTGAGED_OVERLAY)
            painter.setPen(QPen(Qt.GlobalColor.red, 2))
            painter.drawLine(rect.topLeft(), rect.bottomRight())
            painter.drawLine(rect.topRight(), rect.bottomLeft())
        
        # Draw buildings
        if prop_data:
            houses = prop_data.get("houses", 0)
            has_hotel = prop_data.get("has_hotel", False)
            
            if has_hotel or houses > 0:
                self._draw_buildings(painter, rect, houses, has_hotel, position)
        
        # Draw owner indicator
        if prop_data and prop_data.get("owner_id"):
            owner_id = prop_data["owner_id"]
            if self._game_state:
                players = self._game_state.get("players", [])
                for i, p in enumerate(players):
                    if p.get("id") == owner_id:
                        color = PLAYER_COLORS[i % len(PLAYER_COLORS)]
                        # Save painter state before changing brush
                        painter.save()
                        painter.setBrush(QBrush(color))
                        painter.setPen(QPen(Qt.GlobalColor.black, 1))
                        # Small circle in corner
                        indicator_size = 8
                        painter.drawEllipse(
                            rect.left() + 2, 
                            rect.bottom() - indicator_size - 2,
                            indicator_size, indicator_size
                        )
                        # Restore painter state to prevent color bleeding
                        painter.restore()
                        break
        
        # Highlight hovered space
        if self._hovered_space == position:
            painter.fillRect(rect, QColor(255, 255, 0, 50))
        
        # Restore painter state at end of drawing this space
        painter.restore()
    
    def _draw_pokemon_property(
        self,
        painter: QPainter,
        rect: QRect,
        position: int,
        group: str,
        pokemon_data: dict,
        cost: Optional[int],
        is_vertical: bool,
        prop_data: Optional[dict]
    ) -> None:
        """Draw a Pokemon-themed property space."""
        pokemon_name = pokemon_data.get("name", "???")
        image_url = pokemon_data.get("image_url", "")
        
        # Calculate regions: 15% color bar, 70% image area, 15% price
        if is_vertical:
            # Vertical spaces (left and right edges)
            bar_size = max(rect.width() // 7, 6)
            price_size = max(rect.width() // 7, 6)
            image_size = rect.width() - bar_size - price_size
            
            if position in range(11, 20):  # Left side
                # Color bar on right edge
                bar_rect = QRect(rect.right() - bar_size, rect.top(), bar_size, rect.height())
                # Price on left edge
                price_rect = QRect(rect.left(), rect.top(), price_size, rect.height())
                # Image in middle
                image_rect = QRect(rect.left() + price_size, rect.top(), image_size, rect.height())
            else:  # Right side
                # Color bar on left edge
                bar_rect = QRect(rect.left(), rect.top(), bar_size, rect.height())
                # Price on right edge
                price_rect = QRect(rect.right() - price_size, rect.top(), price_size, rect.height())
                # Image in middle
                image_rect = QRect(rect.left() + bar_size, rect.top(), image_size, rect.height())
        else:
            # Horizontal spaces (top and bottom edges)
            bar_size = max(rect.height() // 7, 6)
            price_size = max(rect.height() // 7, 6)
            image_size = rect.height() - bar_size - price_size
            
            if position in range(1, 10):  # Bottom edge
                # Color bar on top
                bar_rect = QRect(rect.left(), rect.top(), rect.width(), bar_size)
                # Price on bottom
                price_rect = QRect(rect.left(), rect.bottom() - price_size, rect.width(), price_size)
                # Image in middle
                image_rect = QRect(rect.left(), rect.top() + bar_size, rect.width(), image_size)
            else:  # Top edge
                # Color bar on bottom
                bar_rect = QRect(rect.left(), rect.bottom() - bar_size, rect.width(), bar_size)
                # Price on top
                price_rect = QRect(rect.left(), rect.top(), rect.width(), price_size)
                # Image in middle
                image_rect = QRect(rect.left(), rect.top() + price_size, rect.width(), image_size)
        
        # Draw color bar
        painter.fillRect(bar_rect, PROPERTY_COLORS[group])
        painter.setPen(QPen(Qt.GlobalColor.black, 1))
        painter.drawRect(bar_rect)
        
        # Draw Pokemon image
        self._draw_pokemon_image(painter, image_rect, image_url, pokemon_name, is_vertical)
        
        # Draw price
        if cost:
            self._draw_price(painter, price_rect, cost, is_vertical)
    
    def _draw_pokemon_image(
        self,
        painter: QPainter,
        rect: QRect,
        image_url: str,
        pokemon_name: str,
        is_vertical: bool
    ) -> None:
        """Draw a Pokemon image with name underneath."""
        # Try to get the cached image
        cache = get_image_cache()
        
        # Calculate image dimensions (leave room for name)
        name_height = 10
        if is_vertical:
            img_width = rect.width() - 4
            img_height = rect.height() - name_height - 4
        else:
            img_width = rect.width() - 4
            img_height = rect.height() - name_height - 4
        
        pixmap = cache.get_pixmap(image_url, img_width, img_height) if image_url else None
        
        if pixmap and not pixmap.isNull():
            # Center the image in the available space
            img_x = rect.left() + (rect.width() - pixmap.width()) // 2
            img_y = rect.top() + 2
            painter.drawPixmap(img_x, img_y, pixmap)
        
        # Draw Pokemon name at the bottom of the image area
        painter.setPen(QPen(Qt.GlobalColor.black))
        font = QFont("Arial", 5)
        font.setBold(True)
        painter.setFont(font)
        
        # Truncate name if too long
        fm = QFontMetrics(font)
        display_name = pokemon_name
        max_width = rect.width() - 4 if not is_vertical else rect.height() - 4
        if fm.horizontalAdvance(display_name) > max_width:
            while fm.horizontalAdvance(display_name + "..") > max_width and len(display_name) > 1:
                display_name = display_name[:-1]
            display_name += ".."
        
        name_rect = QRect(
            rect.left(), 
            rect.bottom() - name_height,
            rect.width(),
            name_height
        )
        
        painter.save()
        if is_vertical:
            # Rotate text for vertical spaces
            painter.translate(rect.center())
            painter.rotate(90 if rect.left() < rect.right() else -90)
            painter.drawText(
                QRect(-rect.height()//2, -rect.width()//2 + rect.width() - name_height,
                      rect.height(), name_height),
                Qt.AlignmentFlag.AlignCenter,
                display_name
            )
        else:
            painter.drawText(name_rect, Qt.AlignmentFlag.AlignCenter, display_name)
        painter.restore()
    
    def _draw_price(
        self,
        painter: QPainter,
        rect: QRect,
        cost: int,
        is_vertical: bool
    ) -> None:
        """Draw the property price."""
        painter.setPen(QPen(Qt.GlobalColor.black))
        font = QFont("Arial", 5)
        painter.setFont(font)
        
        price_text = f"${cost}"
        
        painter.save()
        if is_vertical:
            painter.translate(rect.center())
            painter.rotate(90 if rect.x() < rect.center().x() else -90)
            painter.drawText(
                QRect(-rect.height()//2, -rect.width()//2, rect.height(), rect.width()),
                Qt.AlignmentFlag.AlignCenter,
                price_text
            )
        else:
            painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, price_text)
        painter.restore()
    
    def _draw_classic_property(
        self,
        painter: QPainter,
        rect: QRect,
        position: int,
        group: str,
        name: str,
        cost: Optional[int],
        is_vertical: bool,
        prop_data: Optional[dict]
    ) -> None:
        """Draw a classic (non-Pokemon) property space as fallback."""
        # Draw color bar
        bar_height = rect.height() // 5 if not is_vertical else rect.width() // 5
        
        if is_vertical:
            if position in range(11, 20):  # Left side
                bar_rect = QRect(rect.right() - bar_height, rect.top(), bar_height, rect.height())
            else:  # Right side
                bar_rect = QRect(rect.left(), rect.top(), bar_height, rect.height())
        else:
            if position in range(1, 10):  # Bottom
                bar_rect = QRect(rect.left(), rect.top(), rect.width(), bar_height)
            else:  # Top
                bar_rect = QRect(rect.left(), rect.bottom() - bar_height, rect.width(), bar_height)
        
        painter.fillRect(bar_rect, PROPERTY_COLORS[group])
        painter.drawRect(bar_rect)
        
        # Draw name
        painter.setPen(QPen(Qt.GlobalColor.black))
        font = QFont("Arial", 6)
        painter.setFont(font)
        
        short_name = name
        if len(short_name) > 12:
            short_name = short_name[:10] + ".."
        
        painter.save()
        if is_vertical:
            painter.translate(rect.center())
            painter.rotate(90 if position in range(11, 20) else -90)
            painter.drawText(
                QRect(-rect.height()//2, -rect.width()//2, rect.height(), rect.width()),
                Qt.AlignmentFlag.AlignCenter,
                short_name
            )
        else:
            painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, short_name)
        painter.restore()
    
    def _draw_non_property_space(
        self,
        painter: QPainter,
        rect: QRect,
        position: int,
        space_type: str,
        name: str,
        cost: Optional[int],
        is_vertical: bool,
        prop_data: Optional[dict],
        item_data: Optional[dict] = None
    ) -> None:
        """Draw non-property spaces (railroads, utilities, special spaces)."""
        # If we have item data (for railroads/utilities), draw with image
        if item_data and item_data.get("image_url"):
            self._draw_item_space(painter, rect, position, space_type, name, 
                                  cost, is_vertical, item_data)
            return
        
        # Fallback: Draw name only (for special spaces or when no item data)
        painter.setPen(QPen(Qt.GlobalColor.black))
        font = QFont("Arial", 6)
        painter.setFont(font)
        
        short_name = name
        if len(short_name) > 12:
            short_name = short_name[:10] + ".."
        
        painter.save()
        if is_vertical:
            painter.translate(rect.center())
            painter.rotate(90 if position in range(11, 20) else -90)
            painter.drawText(
                QRect(-rect.height()//2, -rect.width()//2, rect.height(), rect.width()),
                Qt.AlignmentFlag.AlignCenter,
                short_name
            )
        else:
            painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, short_name)
        painter.restore()
    
    def _draw_item_space(
        self,
        painter: QPainter,
        rect: QRect,
        position: int,
        space_type: str,
        name: str,
        cost: Optional[int],
        is_vertical: bool,
        item_data: dict
    ) -> None:
        """Draw a railroad or utility space with item image."""
        image_url = item_data.get("image_url", "")
        item_name = item_data.get("name", name)
        
        # Calculate regions: image area (70%) and price area (30%)
        if is_vertical:
            price_size = max(rect.width() // 5, 8)
            image_size = rect.width() - price_size
            
            if position in range(11, 20):  # Left side
                price_rect = QRect(rect.left(), rect.top(), price_size, rect.height())
                image_rect = QRect(rect.left() + price_size, rect.top(), image_size, rect.height())
            else:  # Right side
                price_rect = QRect(rect.right() - price_size, rect.top(), price_size, rect.height())
                image_rect = QRect(rect.left(), rect.top(), image_size, rect.height())
        else:
            price_size = max(rect.height() // 5, 8)
            image_size = rect.height() - price_size
            
            if position in range(1, 10):  # Bottom edge
                price_rect = QRect(rect.left(), rect.bottom() - price_size, rect.width(), price_size)
                image_rect = QRect(rect.left(), rect.top(), rect.width(), image_size)
            else:  # Top edge
                price_rect = QRect(rect.left(), rect.top(), rect.width(), price_size)
                image_rect = QRect(rect.left(), rect.top() + price_size, rect.width(), image_size)
        
        # Draw item image with name
        self._draw_item_image(painter, image_rect, image_url, item_name, is_vertical, position)
        
        # Draw price
        if cost:
            self._draw_price(painter, price_rect, cost, is_vertical)
    
    def _draw_item_image(
        self,
        painter: QPainter,
        rect: QRect,
        image_url: str,
        item_name: str,
        is_vertical: bool,
        position: int
    ) -> None:
        """Draw an item image with name underneath."""
        cache = get_image_cache()
        
        # Calculate image dimensions (leave room for name)
        name_height = 10
        if is_vertical:
            img_width = rect.width() - 4
            img_height = rect.height() - name_height - 4
        else:
            img_width = rect.width() - 4
            img_height = rect.height() - name_height - 4
        
        pixmap = cache.get_pixmap(image_url, img_width, img_height) if image_url else None
        
        if pixmap and not pixmap.isNull():
            # Center the image in the available space
            img_x = rect.left() + (rect.width() - pixmap.width()) // 2
            img_y = rect.top() + 2
            painter.drawPixmap(img_x, img_y, pixmap)
        
        # Draw item name at the bottom of the image area
        painter.setPen(QPen(Qt.GlobalColor.black))
        font = QFont("Arial", 5)
        font.setBold(True)
        painter.setFont(font)
        
        # Truncate name if too long
        fm = QFontMetrics(font)
        display_name = item_name
        max_width = rect.width() - 4 if not is_vertical else rect.height() - 4
        if fm.horizontalAdvance(display_name) > max_width:
            while fm.horizontalAdvance(display_name + "..") > max_width and len(display_name) > 1:
                display_name = display_name[:-1]
            display_name += ".."
        
        name_rect = QRect(
            rect.left(), 
            rect.bottom() - name_height,
            rect.width(),
            name_height
        )
        
        painter.save()
        if is_vertical:
            painter.translate(rect.center())
            painter.rotate(90 if position in range(11, 20) else -90)
            painter.drawText(
                QRect(-rect.height()//2, -rect.width()//2 + rect.width() - name_height,
                      rect.height(), name_height),
                Qt.AlignmentFlag.AlignCenter,
                display_name
            )
        else:
            painter.drawText(name_rect, Qt.AlignmentFlag.AlignCenter, display_name)
        painter.restore()
    
    def _draw_buildings(
        self, 
        painter: QPainter, 
        rect: QRect, 
        houses: int, 
        has_hotel: bool,
        position: int
    ) -> None:
        """Draw houses or hotel on a property."""
        # Save painter state to prevent color bleeding
        painter.save()
        
        building_size = 6
        spacing = 2
        
        # Determine building placement based on position
        is_vertical = position in range(11, 20) or position in range(31, 40)
        
        if has_hotel:
            # Draw red hotel
            painter.setBrush(QBrush(QColor(255, 0, 0)))
            painter.setPen(QPen(Qt.GlobalColor.black, 1))
            if is_vertical:
                x = rect.center().x() - building_size // 2
                y = rect.top() + 4
                painter.drawRect(x, y, building_size, building_size + 2)
            else:
                x = rect.left() + 4
                y = rect.center().y() - building_size // 2
                painter.drawRect(x, y, building_size + 2, building_size)
        else:
            # Draw green houses
            painter.setBrush(QBrush(QColor(0, 128, 0)))
            painter.setPen(QPen(Qt.GlobalColor.black, 1))
            
            for i in range(houses):
                if is_vertical:
                    x = rect.center().x() - building_size // 2
                    y = rect.top() + 4 + i * (building_size + spacing)
                else:
                    x = rect.left() + 4 + i * (building_size + spacing)
                    y = rect.center().y() - building_size // 2
                
                painter.drawRect(x, y, building_size, building_size)
        
        # Restore painter state
        painter.restore()
    
    def _draw_players(self, painter: QPainter) -> None:
        """Draw player tokens on the board."""
        if not self._game_state:
            return
        
        players = self._game_state.get("players", [])
        
        # Group players by position
        positions: dict[int, list[tuple[int, dict]]] = {}
        for i, player in enumerate(players):
            if player.get("state") == "BANKRUPT":
                continue
            pos = player.get("position", 0)
            if pos not in positions:
                positions[pos] = []
            positions[pos].append((i, player))
        
        # Draw players at each position
        for pos, player_list in positions.items():
            rect = self._get_space_rect(pos)
            token_size = 14
            
            for offset, (i, player) in enumerate(player_list):
                color = PLAYER_COLORS[i % len(PLAYER_COLORS)]
                
                # Offset multiple players on same space
                x = rect.center().x() - token_size // 2 + offset * 6
                y = rect.center().y() - token_size // 2 + offset * 6
                
                # Draw token
                painter.setBrush(QBrush(color))
                painter.setPen(QPen(Qt.GlobalColor.black, 2))
                painter.drawEllipse(x, y, token_size, token_size)
                
                # Highlight current player's token
                if player.get("id") == self._player_id:
                    painter.setPen(QPen(Qt.GlobalColor.white, 2))
                    painter.setBrush(Qt.BrushStyle.NoBrush)
                    painter.drawEllipse(x - 2, y - 2, token_size + 4, token_size + 4)
    
    def mouseMoveEvent(self, event) -> None:
        """Handle mouse movement for hover effects."""
        pos = self._position_from_point(event.pos())
        
        if pos != self._hovered_space:
            self._hovered_space = pos
            self.update()
            
            # Show tooltip with space info
            if pos is not None:
                space_data = BOARD_SPACES.get(pos, {})
                name = space_data.get("name", f"Space {pos}")
                cost = space_data.get("cost")
                
                tooltip = name
                
                # Add property info from game state
                if self._game_state:
                    prop_data = self._game_state.get("board", {}).get(str(pos))
                    if prop_data:
                        # Show Pokemon info if available
                        pokemon_data = prop_data.get("pokemon")
                        if pokemon_data:
                            pokemon_name = pokemon_data.get("name", "")
                            pokemon_types = pokemon_data.get("types", [])
                            if pokemon_name:
                                tooltip = f"🔮 {pokemon_name}"
                            if pokemon_types:
                                tooltip += f"\nType: {'/'.join(pokemon_types)}"
                        
                        if cost:
                            tooltip += f"\nCost: ${cost}"
                        
                        if prop_data.get("owner_id"):
                            # Find owner name
                            for p in self._game_state.get("players", []):
                                if p.get("id") == prop_data["owner_id"]:
                                    tooltip += f"\nOwner: {p.get('name', 'Unknown')}"
                                    break
                        if prop_data.get("houses", 0) > 0:
                            tooltip += f"\nHouses: {prop_data['houses']}"
                        if prop_data.get("has_hotel"):
                            tooltip += "\nHas Hotel"
                        if prop_data.get("is_mortgaged"):
                            tooltip += "\n(MORTGAGED)"
                elif cost:
                    tooltip += f"\nCost: ${cost}"
                
                QToolTip.showText(event.globalPosition().toPoint(), tooltip, self)
            else:
                QToolTip.hideText()
    
    def mousePressEvent(self, event) -> None:
        """Handle mouse click on spaces."""
        if event.button() == Qt.MouseButton.LeftButton:
            pos = self._position_from_point(event.pos())
            if pos is not None:
                self.space_clicked.emit(pos)
    
    def leaveEvent(self, event) -> None:
        """Handle mouse leaving widget."""
        self._hovered_space = None
        self.update()
        QToolTip.hideText()
