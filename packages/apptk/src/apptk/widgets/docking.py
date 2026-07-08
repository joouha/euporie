"""Define a docking split container widget."""

from __future__ import annotations

import logging
from enum import Enum, auto
from typing import TYPE_CHECKING

from apptk.application.current import get_app
from apptk.border import OutsetGrid
from apptk.filters import Condition, to_filter
from apptk.layout.containers import (
    ConditionalContainer,
    DynamicContainer,
    Float,
    FloatContainer,
    HSplit,
    VSplit,
    Window,
)
from apptk.layout.decor import DropShadow
from apptk.layout.dimension import Dimension as D
from apptk.layout.mouse import MouseHandlerWrapper
from apptk.mouse_events import MouseButton, MouseEventType
from apptk.widgets.panel import Panel
from apptk.widgets.tab_bar import TabBarControl

if TYPE_CHECKING:
    from collections.abc import Callable, Iterator, Sequence

    from apptk.border import GridStyle
    from apptk.color import Color
    from apptk.filters import FilterOrBool
    from apptk.key_binding.key_bindings import NotImplementedOrNone
    from apptk.layout.containers import AnyContainer, Container
    from apptk.layout.dimension import AnyDimension
    from apptk.mouse_events import MouseEvent

log = logging.getLogger(__name__)


class DockPosition(Enum):
    """Position where a panel can be docked."""

    CENTER = auto()
    LEFT = auto()
    RIGHT = auto()
    TOP = auto()
    BOTTOM = auto()


class DockingGroup:
    """A leaf node in the docking tree containing tabbed panels.

    This represents a group of panels displayed as tabs. Users can drag
    tabs to rearrange them within the group or dock them elsewhere.

    Args:
        panels: Initial list of panels in this group.
        active: Index of the initially active panel.
        docking_split: Reference to the parent DockingSplit for drag coordination.
    """

    def __init__(
        self,
        panels: list[Panel],
        active: int = 0,
        docking_split: DockingSplit | None = None,
    ) -> None:
        """Initialize the docking group."""
        self.panels = list(panels)
        self._active = min(active, max(0, len(panels) - 1))
        self.docking_split = docking_split
        self._built_container: AnyContainer | None = None
        self._drop_zones: list[DropZone] = []

    @property
    def active(self) -> int:
        """Return the index of the active panel."""
        return self._active

    @active.setter
    def active(self, value: int) -> None:
        """Set the active panel index."""
        if self.panels:
            self._active = max(0, min(value, len(self.panels) - 1))
        else:
            self._active = 0

    def active_content(self) -> AnyContainer:
        """Return the currently active panel's content."""
        if self.panels:
            return self.panels[self.active].content
        return Window()

    def load_tabs(self) -> list[Panel]:
        """Generate Panel entries for the tab bar control."""
        tabs: list[Panel] = []
        for i, panel in enumerate(self.panels):
            tabs.append(
                Panel(
                    title=panel.title,
                    on_activate=lambda sender, i=i: self._activate_tab(i),
                    on_deactivate=None,
                    on_close=(
                        (lambda sender, i=i: self._close_tab(i))
                        if panel.closeable()
                        else None
                    ),
                    closeable=panel.closeable,
                )
            )
        return tabs

    def _activate_tab(self, index: int) -> None:
        """Activate a tab by index."""
        if index != self._active:
            # Deactivate old panel
            if 0 <= self._active < len(self.panels):
                old_panel = self.panels[self._active]
                old_panel.on_deactivate()
            # Set new active
            self.active = index
        # Always activate the panel (even if already active in this group,
        # the group itself may not be focused)
        if 0 <= index < len(self.panels):
            panel = self.panels[index]
            panel.on_activate()
            # Move focus to the panel's content so clicking a tab focuses it.
            # This is required when activate_on_focus is enabled, where the
            # highlight follows focus rather than activation.
            try:
                get_app().layout.focus(panel.content)
            except ValueError:
                # Content may not be focusable or not currently in the layout
                pass
        # Notify parent that this group is now the active one
        if self.docking_split:
            self.docking_split._set_active_group(self)

    def _close_tab(self, index: int) -> None:
        """Close a tab by index."""
        if 0 <= index < len(self.panels):
            panel = self.panels[index]
            if panel.on_close._handlers:
                # Delegate to external handler
                panel.on_close()
            else:
                self.panels.pop(index)
                self._clamp_active()
                self._built_container = None
                if self.docking_split:
                    self.docking_split.cleanup_empty_groups()

    def _clamp_active(self) -> None:
        """Clamp active index to valid range without firing callbacks."""
        if self.panels:
            self._active = max(0, min(self._active, len(self.panels) - 1))
        else:
            self._active = 0

    def remove_panel(self, index: int) -> Panel:
        """Remove and return a panel at the given index.

        Args:
            index: The index of the panel to remove.

        Returns:
            The removed panel.
        """
        panel = self.panels.pop(index)
        self._clamp_active()
        self._built_container = None
        return panel

    def insert_panel(self, panel: Panel, index: int | None = None) -> None:
        """Insert a panel at the given index.

        Args:
            panel: The panel to insert.
            index: Position to insert at. If None, appends to end.
        """
        if index is None:
            self.panels.append(panel)
        else:
            self.panels.insert(index, panel)
        self._built_container = None


class DockingNode:
    """A split node in the docking tree.

    Contains two children arranged either horizontally or vertically.

    Args:
        direction: "horizontal" for top/bottom split, "vertical" for left/right.
        first: The first child (top or left).
        second: The second child (bottom or right).
    """

    def __init__(
        self,
        direction: str,
        first: DockingGroup | DockingNode,
        second: DockingGroup | DockingNode,
    ) -> None:
        """Initialize the docking node."""
        self.direction = direction
        self.first = first
        self.second = second


class DragState:
    """State tracking for an active drag operation.

    Args:
        source_group: The group the tab is being dragged from.
        tab_index: The index of the tab being dragged.
    """

    def __init__(self, source_group: DockingGroup, tab_index: int) -> None:
        """Initialize drag state."""
        self.source_group = source_group
        self.tab_index = tab_index
        self.target_group: DockingGroup | None = None
        self.position: DockPosition = DockPosition.CENTER


class DockingTabBarControl(TabBarControl):
    """A tab bar control that supports drag-to-dock.

    Extends TabBarControl to detect mouse drag events on tabs and
    communicate with the parent DockingSplit to initiate docking operations.
    """

    def __init__(
        self,
        group: DockingGroup,
        docking_split: DockingSplit,
        **kwargs: object,
    ) -> None:
        """Initialize the docking tab bar control.

        Args:
            group: The DockingGroup this tab bar belongs to.
            docking_split: The parent DockingSplit managing docking state.
            **kwargs: Additional arguments passed to TabBarControl.
        """
        self.group = group
        self.docking_split = docking_split
        super().__init__(
            tabs=group.load_tabs,
            active=lambda: (
                group.active if docking_split._active_group is group else None
            ),
            **kwargs,
        )

    def mouse_handler(self, mouse_event: MouseEvent) -> NotImplementedOrNone:
        """Handle mouse events, detecting drag initiation."""
        # Let the parent handle close buttons, scroll, and tab activation first
        result = super().mouse_handler(mouse_event)

        # Parent handled it (e.g., close button click) - cancel any drag
        if result is None and self.docking_split.drag_state is not None:
            self.docking_split.drag_state = None
            self.docking_split.show_drop_zones()

        row = mouse_event.position.y
        col = mouse_event.position.x

        if row == 1 and mouse_event.button == MouseButton.LEFT:
            if mouse_event.event_type == MouseEventType.MOUSE_DOWN:
                # Determine which tab was clicked
                tab_index = self.col_to_tab.get(col)
                if tab_index is not None:
                    self.docking_split.start_drag(self.group, tab_index)
                    result = None

            if (
                mouse_event.event_type == MouseEventType.MOUSE_MOVE
                and self.docking_split.drag_state is not None
            ):
                # The mouse is over a tab bar, not a drop zone, so clear any
                # pending target but keep the drop zones visible
                self.docking_split.drag_state.target_group = None
                self.docking_split.show_drop_zones()
                result = None

        if (
            mouse_event.event_type == MouseEventType.MOUSE_UP
            and self.docking_split.drag_state is not None
        ):
            # Fallback for releasing the mouse over a tab bar rather than a drop
            # zone. DropZone.mouse_handler also calls end_drag() on MOUSE_UP, but
            # end_drag() guards on drag_state being None, so the dual handling is
            # safe.
            self.docking_split.end_drag()
            result = None

        return result


class DropZone:
    """A drop zone overlay that highlights during drag operations."""

    def __init__(
        self,
        docking_split: DockingSplit,
        group: DockingGroup,
        position: DockPosition,
        color: Color | str = "#000000",
        highlight: Color | str = "#0000FF",
    ) -> None:
        """Initialize the drop zone control."""
        self.docking_split = docking_split
        self.group = group
        self.position = position
        self.color = color
        self.highlight = highlight
        self.shadow = DropShadow(amount=0.0, color=color)
        self.container = MouseHandlerWrapper(
            content=self.shadow,
            handler=self.mouse_handler,
        )

    def hide(self) -> None:
        """Restyle when the mouse exits."""
        self.shadow.amount = 0.0

    def show(self) -> None:
        """Restyle when the drop zone becomes available during a drag."""
        self.shadow.amount = 0.25
        self.shadow.color = self.color

    def indicate(self) -> None:
        """Restyle when the mouse enters."""
        self.shadow.amount = 0.5
        self.shadow.color = self.highlight

    def mouse_handler(self, mouse_event: MouseEvent) -> NotImplementedOrNone:
        """Handle mouse events to set the drop zone during drag.

        Returns:
            None if handled, NotImplemented otherwise.
        """
        drag_state = self.docking_split.drag_state
        if drag_state is None:
            self.hide()
            return None

        if mouse_event.event_type == MouseEventType.MOUSE_MOVE:
            self.docking_split.show_drop_zones(active=self)
            drag_state.target_group = self.group
            drag_state.position = self.position
            self.indicate()
            return None

        elif (
            mouse_event.event_type == MouseEventType.MOUSE_UP
            and mouse_event.button == MouseButton.LEFT
        ):
            # Primary end-drag path when releasing over a drop zone.
            # DockingTabBarControl.mouse_handler provides a fallback for releases
            # outside any zone; end_drag() guards on drag_state so this is safe.
            drag_state.target_group = self.group
            drag_state.position = self.position
            self.docking_split.end_drag()
            return None

        return NotImplemented

    def __pt_container__(self) -> Container:
        """Return the container."""
        return self.container


class DockingSplit:
    """A container that supports docking panels by dragging tabs.

    Panels can be arranged in tabs (stacked) or tiled by dragging a tab
    to the edge of a group. Dragging to the left/right creates a vertical
    split, dragging to the top/bottom creates a horizontal split, and
    dragging to the center adds the panel as a tab.

    Args:
        panels: Initial list of panels to display.
        style: Style string for the container.
        width: Width dimension.
        height: Height dimension.
        border: Grid style for borders.
        h_padding: Horizontal padding between vertical splits.
        h_padding_char: Character used for horizontal padding.
        v_padding: Vertical padding between horizontal splits.
        v_padding_char: Character used for vertical padding.
        hide_single_tab: If True, hide the tab bar when a group has only one panel.
        activate_on_focus: If True, automatically activate the group and panel
            whose content currently has focus on each render.
    """

    def __init__(
        self,
        panels: Sequence[Panel],
        style: str | Callable[[], str] = "",
        width: AnyDimension = None,
        height: AnyDimension = None,
        border: GridStyle = OutsetGrid,
        h_padding: int = 0,
        h_padding_char: str | None = "│",
        v_padding: int = 0,
        v_padding_char: str | None = "─",
        zone_color: Color | str = "#000000",
        zone_highlight: Color | str = "#000000",
        hide_single_tab: FilterOrBool = False,
        activate_on_focus: FilterOrBool = True,
    ) -> None:
        """Initialize the docking split."""
        self.style = style
        self.width = width
        self.height = height
        self.border = border
        self.h_padding = h_padding
        self.h_padding_char = h_padding_char
        self.v_padding = v_padding
        self.v_padding_char = v_padding_char
        self.zone_color = zone_color
        self.zone_highlight = zone_highlight
        self.hide_single_tab = to_filter(hide_single_tab)
        self.activate_on_focus = to_filter(activate_on_focus)
        self.drag_state: DragState | None = None
        self._drop_zones: list[DropZone] = []
        self.panels: list[Panel] = list(panels)

        # Create initial root as a single group with all panels
        self.root: DockingGroup | DockingNode = DockingGroup(
            panels=list(panels),
            active=0,
            docking_split=self,
        )

        # Track which group is currently active (only its tab is highlighted)
        self._active_group: DockingGroup | None = (
            self.root if isinstance(self.root, DockingGroup) else None
        )

        self.container = HSplit(
            [DynamicContainer(self._build_layout)],
            style=style,
            width=width,
            height=height,
        )

    def _build_layout(self) -> AnyContainer:
        """Build the layout from the docking tree."""
        if self.activate_on_focus():
            self._sync_focused_panel()
        return self._build_node(self.root)

    def _sync_focused_panel(self) -> None:
        """Activate the group and panel whose content currently has focus.

        Walks the tree and, if a panel's content has focus, marks it as the
        active panel of its group and sets that group as the active group.
        This updates the highlight without firing activation callbacks.
        """
        layout = get_app().layout
        for group in self._walk_groups():
            for i, panel in enumerate(group.panels):
                try:
                    has_focus = layout.has_focus(panel.content)
                except Exception:
                    has_focus = False
                if has_focus:
                    group._active = i
                    self._set_active_group(group)
                    return

    def _build_node(self, node: DockingGroup | DockingNode) -> AnyContainer:
        """Recursively build the container layout from a tree node.

        Args:
            node: The tree node to build.

        Returns:
            A container representing this node.
        """
        if isinstance(node, DockingGroup):
            return self._build_group(node)
        else:
            first = self._build_node(node.first)
            second = self._build_node(node.second)
            if node.direction == "horizontal":
                return HSplit(
                    [first, second],
                    style="class:docking-split",
                    padding=self.v_padding,
                    padding_char=self.v_padding_char,
                )
            else:
                return VSplit(
                    [first, second],
                    style="class:docking-split",
                    padding=self.h_padding,
                    padding_char=self.h_padding_char,
                )

    def _build_group(self, group: DockingGroup) -> AnyContainer:
        """Build the container for a single docking group.

        Returns a cached container for the group, only creating it once.
        The group is wrapped in a FloatContainer with per-zone Float overlays
        that appear during drag operations.

        Args:
            group: The group to build.

        Returns:
            A container with a tab bar, content area, and drop zone overlays.
        """
        if group._built_container is None:
            tab_bar = DockingTabBarControl(
                group=group,
                docking_split=self,
                grid=self.border,
            )

            show_tab_bar = Condition(
                lambda: not self.hide_single_tab() or len(self.panels) > 1
            )
            is_dragging = Condition(lambda: self.drag_state is not None)

            def _make_zone(
                position: DockPosition,
                *,
                width: AnyDimension = None,
                height: AnyDimension = None,
            ) -> AnyContainer:
                zone = DropZone(
                    self,
                    group,
                    position,
                    color=self.zone_color,
                    highlight=self.zone_highlight,
                )
                self._drop_zones.append(zone)
                group._drop_zones.append(zone)
                return HSplit([zone], width=width, height=height)

            group._built_container = HSplit(
                [
                    ConditionalContainer(
                        Window(
                            tab_bar,
                            style="class:tab-bar",
                            height=2,
                        ),
                        filter=show_tab_bar,
                    ),
                    FloatContainer(
                        content=DynamicContainer(group.active_content),
                        floats=[
                            Float(
                                content=VSplit(
                                    [
                                        _make_zone(
                                            DockPosition.LEFT,
                                            width=D(weight=1),
                                        ),
                                        HSplit(
                                            [
                                                _make_zone(
                                                    DockPosition.TOP,
                                                    height=D(weight=1),
                                                ),
                                                _make_zone(
                                                    DockPosition.CENTER,
                                                    height=D(weight=3),
                                                ),
                                                _make_zone(
                                                    DockPosition.BOTTOM,
                                                    height=D(weight=1),
                                                ),
                                            ],
                                            width=D(weight=3),
                                        ),
                                        _make_zone(
                                            DockPosition.RIGHT,
                                            width=D(weight=1),
                                        ),
                                    ]
                                ),
                                top=0,
                                right=0,
                                bottom=0,
                                left=0,
                                # Hide the float when not dragging by sizing it to zero
                                # This is done instead of a conditional container as
                                # we use `transparent=True` to block mouse events over
                                # the whole float area
                                width=lambda: None if is_dragging() else 0,
                                height=lambda: None if is_dragging() else 0,
                                transparent=True,
                            ),
                        ],
                    ),
                ],
                style=self.style,
            )

        return group._built_container

    def _set_active_group(self, group: DockingGroup) -> None:
        """Set the given group as the active group for tab highlighting.

        Args:
            group: The group that should show its active tab highlighted.
        """
        self._active_group = group

    def _walk_groups(
        self, node: DockingGroup | DockingNode | None = None
    ) -> Iterator[DockingGroup]:
        """Yield all DockingGroups in tree order.

        Args:
            node: The node to start from. Defaults to the tree root.

        Yields:
            Each DockingGroup found during tree traversal.
        """
        node = node or self.root
        if isinstance(node, DockingGroup):
            yield node
        else:
            yield from self._walk_groups(node.first)
            yield from self._walk_groups(node.second)

    def get_group_for_content(self, content: AnyContainer) -> DockingGroup | None:
        """Return the group containing the given content.

        Args:
            content: The content to find.

        Returns:
            The DockingGroup containing the content, or None.
        """
        for group in self._walk_groups():
            if any(panel.content is content for panel in group.panels):
                return group
        return None

    def start_drag(self, group: DockingGroup, tab_index: int) -> None:
        """Begin a drag operation.

        Args:
            group: The group containing the tab being dragged.
            tab_index: The index of the tab being dragged.
        """
        if len(group.panels) > 0:
            self.drag_state = DragState(source_group=group, tab_index=tab_index)

    def hide_drop_zones(self) -> None:
        """Hide all drop zone shadows."""
        for drop_zone in self._drop_zones:
            drop_zone.hide()

    def show_drop_zones(self, active: DropZone | None = None) -> None:
        """Show drop zone shadows, highlighting the active one.

        Args:
            active: The drop zone that should remain highlighted.
        """
        for drop_zone in self._drop_zones:
            if drop_zone is active:
                drop_zone.indicate()
            else:
                drop_zone.show()

    def end_drag(self) -> None:
        """Complete a drag operation, docking the panel."""
        if self.drag_state is None:
            self.hide_drop_zones()
            return

        state = self.drag_state
        self.drag_state = None
        self.hide_drop_zones()

        target_group = state.target_group
        if target_group is None:
            return

        source_group = state.source_group
        tab_index = state.tab_index
        position = state.position

        # Don't do anything if dropping on same group center with only one tab
        if source_group is target_group and position == DockPosition.CENTER:
            return

        # Don't dock if source only has one panel and target is same group
        if source_group is target_group and len(source_group.panels) <= 1:
            return

        # Remove panel from source
        if tab_index >= len(source_group.panels):
            return
        panel = source_group.remove_panel(tab_index)

        if position == DockPosition.CENTER:
            # Add as a tab to the target group
            target_group.insert_panel(panel)
        else:
            # Create a new group for the dragged panel
            new_group = DockingGroup(
                panels=[panel],
                active=0,
                docking_split=self,
            )

            # Determine split direction and order
            if position in (DockPosition.LEFT, DockPosition.RIGHT):
                direction = "vertical"
                if position == DockPosition.LEFT:
                    first, second = new_group, target_group
                else:
                    first, second = target_group, new_group
            else:
                direction = "horizontal"
                if position == DockPosition.TOP:
                    first, second = new_group, target_group
                else:
                    first, second = target_group, new_group

            # Create new split node
            new_node = DockingNode(
                direction=direction,
                first=first,
                second=second,
            )

            # Replace target_group in the tree with new_node
            self._replace_node(target_group, new_node)

        # Clean up empty groups
        self.cleanup_empty_groups()

    def _replace_node(
        self,
        old: DockingGroup | DockingNode,
        new: DockingGroup | DockingNode,
        parent: DockingGroup | DockingNode | None = None,
    ) -> None:
        """Replace a node in the tree with a new node.

        Args:
            old: The node to replace.
            new: The replacement node.
            parent: Current node being searched.
        """
        if parent is None:
            if self.root is old:
                self.root = new
                return
            parent = self.root

        if isinstance(parent, DockingNode):
            if parent.first is old:
                parent.first = new
            elif parent.second is old:
                parent.second = new
            else:
                self._replace_node(old, new, parent.first)
                self._replace_node(old, new, parent.second)

    def _discard_group(self, group: DockingGroup) -> None:
        """Release a group's resources so it can be garbage-collected.

        Removes the group's drop zones from the split's tracking list and clears
        the group's references to its zones and cached container, breaking any
        cycles that would otherwise keep the group, its panels and zones alive.

        Args:
            group: The group being removed from the tree.
        """
        zones = set(group._drop_zones)
        if zones:
            self._drop_zones = [z for z in self._drop_zones if z not in zones]
        group._drop_zones.clear()
        group._built_container = None
        group.docking_split = None

    def cleanup_empty_groups(self) -> None:
        """Remove empty groups from the tree and collapse unnecessary splits."""
        self.root = self._cleanup_node(self.root)
        self.panels = self._collect_panels()
        get_app().invalidate()

    def _cleanup_node(
        self, node: DockingGroup | DockingNode
    ) -> DockingGroup | DockingNode:
        """Recursively clean up empty groups and collapse single-child splits.

        Args:
            node: The node to clean up.

        Returns:
            The cleaned-up node (may be a different node if collapsed).
        """
        if isinstance(node, DockingGroup):
            return node

        # Recursively clean children
        node.first = self._cleanup_node(node.first)
        node.second = self._cleanup_node(node.second)

        # If first child is empty group, return second
        if isinstance(node.first, DockingGroup) and not node.first.panels:
            self._discard_group(node.first)
            return node.second

        # If second child is empty group, return first
        if isinstance(node.second, DockingGroup) and not node.second.panels:
            self._discard_group(node.second)
            return node.first

        return node

    def _collect_panels(self) -> list[Panel]:
        """Collect all panels from all groups in the docking tree.

        Returns:
            A flat list of all panels in tree traversal order.
        """
        return [panel for group in self._walk_groups() for panel in group.panels]

    def _find_first_group(self) -> DockingGroup | None:
        """Locate the first DockingGroup in the tree.

        Returns:
            The first DockingGroup found, or None if the tree is empty.
        """
        return next(self._walk_groups(), None)

    def add_panel(self, panel: Panel, group: DockingGroup | None = None) -> None:
        """Add a panel to the docking tree and sync the panels list.

        Args:
            panel: The panel to add.
            group: The target group. If None, uses the first group found.
        """
        if group is None:
            group = self._find_first_group()
        if group is None:
            # Tree is empty; create a new root group
            group = DockingGroup(panels=[], active=0, docking_split=self)
            self.root = group
        group.insert_panel(panel)
        self.panels = self._collect_panels()
        get_app().invalidate()

    def remove_panel(self, panel: Panel) -> None:
        """Remove a panel from the docking tree and sync the panels list.

        Args:
            panel: The panel to remove.
        """
        if (
            group := self.get_group_for_content(panel.content)
        ) and panel in group.panels:
            group.remove_panel(group.panels.index(panel))
            self.cleanup_empty_groups()

    def _reset_tree(self, root: DockingGroup | DockingNode) -> None:
        """Replace the tree with a new root and refresh derived state.

        Args:
            root: The new tree root.
        """
        # Discard existing groups so their drop zones and cached containers
        # do not leak into the new tree.
        for group in list(self._walk_groups()):
            self._discard_group(group)
        self.root = root
        self.panels = self._collect_panels()
        # Choose an active group from the new tree
        self._active_group = self._find_first_group()
        get_app().invalidate()

    def stack_panels(self) -> None:
        """Collapse all panels into a single tabbed group."""
        panels = self._collect_panels()
        if not panels:
            return
        new_root = DockingGroup(
            panels=panels,
            active=0,
            docking_split=self,
        )
        self._reset_tree(new_root)

    def tile_panels(self) -> None:
        """Arrange all panels in a spiral tiled layout.

        Each panel occupies its own group. Splits alternate between vertical
        and horizontal, producing a spiral where each successive panel takes
        the remaining space.
        """
        panels = self._collect_panels()
        if not panels:
            return

        # Build the tree from the innermost pair outwards so the outermost
        # split is the first one the user sees on the left/top.
        groups = [
            DockingGroup(panels=[panel], active=0, docking_split=self)
            for panel in panels
        ]

        directions = ("vertical", "horizontal")
        node: DockingGroup | DockingNode = groups[-1]
        for i in range(len(groups) - 2, -1, -1):
            direction = directions[i % 2]
            node = DockingNode(
                direction=direction,
                first=groups[i],
                second=node,
            )

        self._reset_tree(node)

    def sync_active_panel(self, content: AnyContainer) -> None:
        """Sync the active group highlight without firing activation callbacks.

        This is used during rendering to update which tab appears highlighted
        based on the current focus, without triggering side effects like
        re-focusing or re-activating panels.

        Args:
            content: The content that should be shown as active.
        """
        for group in self._walk_groups():
            for i, panel in enumerate(group.panels):
                if panel.content is content:
                    group._active = i
                    self._set_active_group(group)
                    return

    def __pt_container__(self) -> Container:
        """Return the container."""
        return self.container
