from __future__ import annotations

import base64
import json
from collections.abc import Mapping
from dataclasses import dataclass, field
from importlib import resources
from typing import Any, ClassVar, Self

import cv2
import numpy as np

from ..coordinates import Coordinates


@dataclass(slots=True, frozen=True)
class OverlaySelection:
    left: int
    top: int
    right: int
    bottom: int

    @property
    def width(self) -> int:
        return self.right - self.left

    @property
    def height(self) -> int:
        return self.bottom - self.top


@dataclass(slots=True, frozen=True)
class OverlayStyle:
    fill: str = "#101619"
    outline: str = "#74d4dc"
    stroke: int = 1
    stipple: str = "gray50"

    @classmethod
    def from_dict(
        cls,
        data: Mapping[str, Any] | None,
    ) -> Self:
        values = data or {}
        return cls(
            fill=values.get("fill") or "#101619",
            outline=values.get("outline") or "#74d4dc",
            stroke=values.get("stroke") or 1,
            stipple=values.get("stipple") or "gray50",
        )


@dataclass(slots=True, frozen=True)
class OverlayItem:
    """One rendered shape and, unless a placeholder, one detected entry."""

    name: str
    center: tuple[float, float]
    size: tuple[float, float]
    style: OverlayStyle

    @property
    def is_placeholder(self) -> bool:
        return self.name.startswith("placeholder")

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> Self:
        center = data["center"]
        size = data.get("size") or [0.0778, 0.0778]
        return cls(
            name=str(data["name"]),
            center=(center[0], center[1]),
            size=(size[0], size[1]),
            style=OverlayStyle.from_dict(data.get("style")),
        )


@dataclass(slots=True, frozen=True)
class TabOverlayDefinition:
    template_size: tuple[int, int]
    title: str
    instructions: str
    items: tuple[OverlayItem, ...]

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> Self:
        template = data["template_size"]
        items = tuple(
            OverlayItem.from_dict(item) for item in data["items"] if item["name"]
        )
        names = [item.name for item in items]
        if len(names) != len(set(names)):
            raise ValueError("Overlay item names must be unique")
        return cls(
            template_size=(int(template[0]), int(template[1])),
            title=str(data.get("title", "Select stash tab")),
            instructions=str(
                data.get("instructions", "Align the mask and press Enter.")
            ),
            items=items,
        )

    @classmethod
    def from_resource(cls, package: str, name: str) -> Self:
        resource = resources.files(package).joinpath(name)
        return cls.from_dict(json.loads(resource.read_text(encoding="utf-8")))

    @property
    def entry_names(self) -> tuple[str, ...]:
        return tuple(item.name for item in self.items if not item.is_placeholder)

    def map_selection(
        self,
        selection: OverlaySelection,
    ) -> dict[str, Coordinates]:
        return {
            item.name: Coordinates(
                x=selection.left + round(item.center[0] * selection.width),
                y=selection.top + round(item.center[1] * selection.height),
            )
            for item in self.items
            if not item.is_placeholder
        }


@dataclass(slots=True)
class _State:
    selection: OverlaySelection | None = None
    mode: tuple[str, str | None] | None = None
    origin: tuple[int, int] | None = None
    initial: OverlaySelection | None = None
    rendered: list[int] = field(default_factory=list[int])


class TabOverlaySelector:
    """Data-driven movable and resizable stash-tab alignment mask."""

    HANDLE_RADIUS = 7
    HANDLE_HIT_PADDING = 3
    MINIMUM_SIZE = 48

    # Tk stipple patterns simulate alpha on canvas primitives. gray75 means
    # roughly 75 percent of the dark fill is drawn outside the selection.
    OUTSIDE_MASK_FILL = "#050708"
    OUTSIDE_MASK_STIPPLE = "gray75"
    SELECTION_OUTLINE = "#62f59a"

    HANDLE_CURSORS: ClassVar[Mapping[str, str]] = {
        "nw": "top_left_corner",
        "n": "top_side",
        "ne": "top_right_corner",
        "e": "right_side",
        "se": "bottom_right_corner",
        "s": "bottom_side",
        "sw": "bottom_left_corner",
        "w": "left_side",
    }

    def __init__(self, definition: TabOverlayDefinition) -> None:
        self.definition = definition

    @classmethod
    def from_resource(cls, package: str, name: str) -> Self:
        return cls(TabOverlayDefinition.from_resource(package, name))

    def detect(
        self,
        screenshot: np.ndarray,
    ) -> dict[str, Coordinates] | None:
        selection = self.select(screenshot)
        return None if selection is None else self.definition.map_selection(selection)

    @staticmethod
    def _background_photo(tk: Any, screenshot: np.ndarray) -> Any:
        success, encoded = cv2.imencode(".png", screenshot)
        if not success:
            raise ValueError("Unable to encode screenshot")
        return tk.PhotoImage(data=base64.b64encode(encoded).decode("ascii"))

    def select(
        self,
        screenshot: np.ndarray,
    ) -> OverlaySelection | None:
        import tkinter as tk

        if screenshot.ndim != 3 or screenshot.shape[2] != 3:
            raise ValueError("Expected a BGR screenshot")

        screen_height, screen_width = screenshot.shape[:2]
        window = tk.Tk()
        window.title(self.definition.title)
        window.attributes("-fullscreen", True)  # type: ignore
        window.attributes("-topmost", True)  # type: ignore

        background = self._background_photo(tk, screenshot)
        canvas = tk.Canvas(
            window,
            width=screen_width,
            height=screen_height,
            cursor="crosshair",
            highlightthickness=0,
        )
        canvas.pack(fill=tk.BOTH, expand=True)
        canvas.create_image(  # type: ignore
            0,
            0,
            anchor=tk.NW,
            image=background,
        )

        # Persistent, high-contrast instruction panel. A shadow and solid dark
        # backing keep the text readable over both bright and dark screenshots.
        instruction_margin = 12
        instruction_top = 12
        instruction_height = 48

        state = _State()

        def handles(
            box: OverlaySelection,
        ) -> dict[str, tuple[int, int]]:
            center_x = (box.left + box.right) // 2
            center_y = (box.top + box.bottom) // 2
            return {
                "nw": (box.left, box.top),
                "n": (center_x, box.top),
                "ne": (box.right, box.top),
                "e": (box.right, center_y),
                "se": (box.right, box.bottom),
                "s": (center_x, box.bottom),
                "sw": (box.left, box.bottom),
                "w": (box.left, center_y),
            }

        def hit_handle(x: int, y: int) -> str | None:
            box = state.selection
            if box is None:
                return None

            hit_radius = self.HANDLE_RADIUS + self.HANDLE_HIT_PADDING
            for name, (handle_x, handle_y) in handles(box).items():
                if abs(x - handle_x) <= hit_radius and abs(y - handle_y) <= hit_radius:
                    return name
            return None

        @staticmethod
        def selection_contains(
            box: OverlaySelection,
            x: int,
            y: int,
        ) -> bool:
            return box.left <= x <= box.right and box.top <= y <= box.bottom

        def set_cursor(cursor: str) -> None:
            if canvas.cget("cursor") == cursor:
                return
            try:
                canvas.configure(cursor=cursor)
            except tk.TclError:
                canvas.configure(cursor="crosshair")

        def cursor_for_position(x: int, y: int) -> str:
            box = state.selection
            if box is None:
                return "crosshair"
            handle = hit_handle(x, y)
            if handle is not None:
                return self.HANDLE_CURSORS[handle]
            if selection_contains(box, x, y):
                return "fleur"
            return "crosshair"

        def cursor_for_mode(
            mode: str,
            handle: str | None,
        ) -> str:
            if mode == "move":
                return "fleur"
            if mode == "resize" and handle is not None:
                return self.HANDLE_CURSORS[handle]
            return "crosshair"

        def update_cursor(event: tk.Event) -> None:
            if state.mode is None:
                set_cursor(cursor_for_position(event.x, event.y))

        def mouse_leave(_event: tk.Event) -> None:
            if state.mode is None:
                set_cursor("crosshair")

        def clear() -> None:
            for identifier in state.rendered:
                canvas.delete(identifier)
            state.rendered = []
            render_instructions()

        def item_bounds(
            item: OverlayItem,
            box: OverlaySelection,
        ) -> tuple[int, int, int, int]:
            center_x = box.left + item.center[0] * box.width
            center_y = box.top + item.center[1] * box.height
            width = item.size[0] * box.width
            height = item.size[1] * box.height
            return (
                round(center_x - width / 2),
                round(center_y - height / 2),
                round(center_x + width / 2),
                round(center_y + height / 2),
            )

        def draw_outside_mask(box: OverlaySelection) -> None:
            """Darken everything except the selected rectangle."""
            mask_options = {
                "fill": self.OUTSIDE_MASK_FILL,
                "stipple": self.OUTSIDE_MASK_STIPPLE,
                "outline": "",
            }
            rectangles = (
                (0, 0, screen_width, box.top),
                (0, box.bottom, screen_width, screen_height),
                (0, box.top, box.left, box.bottom),
                (box.right, box.top, screen_width, box.bottom),
            )
            for left, top, right, bottom in rectangles:
                if right > left and bottom > top:
                    state.rendered.append(
                        canvas.create_rectangle(
                            left,
                            top,
                            right,
                            bottom,
                            **mask_options,  # type: ignore
                        )
                    )

        def draw_item_label(item: OverlayItem, box: OverlaySelection) -> None:
            label = _item_label(item)
            if not label:
                return

            x = box.left + item.center[0] * box.width
            y = box.top + item.center[1] * box.height
            # A one-pixel shadow improves legibility without covering the item.
            state.rendered.append(
                canvas.create_text(
                    x + 1,
                    y + 1,
                    anchor=tk.CENTER,
                    text=label,
                    fill="#000000",
                    font=("Segoe UI", 9, "bold"),
                )
            )
            state.rendered.append(
                canvas.create_text(
                    x,
                    y,
                    anchor=tk.CENTER,
                    text=label,
                    fill="#ffffff",
                    font=("Segoe UI", 9, "bold"),
                )
            )

        def render_instructions():
            state.rendered.extend(
                [
                    canvas.create_rectangle(
                        instruction_margin,
                        instruction_top,
                        screen_width - instruction_margin,
                        instruction_top + instruction_height,
                        fill="#11181a",
                        width=2,
                    ),
                    canvas.create_text(
                        instruction_margin + 14,
                        instruction_top + instruction_height // 2,
                        anchor=tk.W,
                        text=self.definition.instructions,
                        fill="#f7fffb",
                        font=("Segoe UI", 13, "bold"),
                    ),
                ]
            )

        def render(box: OverlaySelection) -> None:
            clear()
            draw_outside_mask(box)

            # The selection itself has no background fill. The original
            # screenshot therefore remains fully visible inside the selection.
            state.rendered.append(
                canvas.create_rectangle(
                    box.left,
                    box.top,
                    box.right,
                    box.bottom,
                    fill="",
                    outline=self.SELECTION_OUTLINE,
                    width=3,
                )
            )

            for item in self.definition.items:
                style = item.style
                state.rendered.append(
                    canvas.create_rectangle(
                        *item_bounds(item, box),
                        fill=style.fill,
                        outline=style.outline,
                        width=style.stroke,
                        stipple=style.stipple,
                    )
                )
                draw_item_label(item, box)

            for handle_x, handle_y in handles(box).values():
                radius = self.HANDLE_RADIUS
                state.rendered.append(
                    canvas.create_oval(
                        handle_x - radius,
                        handle_y - radius,
                        handle_x + radius,
                        handle_y + radius,
                        fill="#f7fffb",
                        outline="#102414",
                        width=2,
                    )
                )
            render_instructions()

        def clamp(box: OverlaySelection) -> OverlaySelection:
            width = min(
                screen_width,
                max(self.MINIMUM_SIZE, box.width),
            )
            height = min(
                screen_height,
                max(self.MINIMUM_SIZE, box.height),
            )
            left = min(max(0, box.left), screen_width - width)
            top = min(max(0, box.top), screen_height - height)
            return OverlaySelection(
                left,
                top,
                left + width,
                top + height,
            )

        def mouse_down(event: tk.Event) -> None:
            box = state.selection
            handle = hit_handle(event.x, event.y)
            state.origin = (event.x, event.y)
            state.initial = box

            if handle is not None:
                state.mode = ("resize", handle)
            elif box is not None and selection_contains(box, event.x, event.y):
                state.mode = ("move", None)
            else:
                state.mode = ("create", None)
                state.selection = None
                clear()

            mode, active_handle = state.mode
            set_cursor(cursor_for_mode(mode, active_handle))

        def mouse_move(event: tk.Event) -> None:
            if state.mode is None or state.origin is None:
                return

            mode, handle = state.mode
            origin_x, origin_y = state.origin
            initial = state.initial

            if mode == "create":
                left, right = sorted((origin_x, event.x))
                top, bottom = sorted((origin_y, event.y))
                if right - left < self.MINIMUM_SIZE or bottom - top < self.MINIMUM_SIZE:
                    return
                box = OverlaySelection(left, top, right, bottom)
            elif mode == "move" and initial is not None:
                delta_x = event.x - origin_x
                delta_y = event.y - origin_y
                box = clamp(
                    OverlaySelection(
                        initial.left + delta_x,
                        initial.top + delta_y,
                        initial.right + delta_x,
                        initial.bottom + delta_y,
                    )
                )
            elif mode == "resize" and initial is not None and handle is not None:
                left = initial.left
                top = initial.top
                right = initial.right
                bottom = initial.bottom

                if "w" in handle:
                    left = min(event.x, right - self.MINIMUM_SIZE)
                if "e" in handle:
                    right = max(event.x, left + self.MINIMUM_SIZE)
                if "n" in handle:
                    top = min(event.y, bottom - self.MINIMUM_SIZE)
                if "s" in handle:
                    bottom = max(event.y, top + self.MINIMUM_SIZE)

                box = clamp(OverlaySelection(left, top, right, bottom))
            else:
                return

            state.selection = box
            render(box)

        def mouse_up(event: tk.Event) -> None:
            state.mode = None
            state.origin = None
            state.initial = None
            update_cursor(event)

        def confirm(_event: tk.Event | None = None) -> None:
            if state.selection is not None:
                window.quit()

        def cancel(_event: tk.Event | None = None) -> None:
            state.selection = None
            window.quit()

        canvas.bind("<Motion>", update_cursor)
        canvas.bind("<Leave>", mouse_leave)
        canvas.bind("<ButtonPress-1>", mouse_down)
        canvas.bind("<B1-Motion>", mouse_move)
        canvas.bind("<ButtonRelease-1>", mouse_up)
        window.bind("<Return>", confirm)
        window.bind("<Escape>", cancel)
        window.bind("<Control-c>", cancel)

        render(OverlaySelection(0, 0, 0, 0))
        window.mainloop()
        selection = state.selection
        window.destroy()
        return selection


def _item_label(item: OverlayItem) -> str:
    orb = item.name.removeprefix("orb_of_")
    if orb != item.name:
        return orb[:3]

    orb = item.name.removesuffix("_orb")
    if orb != item.name:
        return orb[:3]

    return "".join(part[0] for part in item.name.split("_"))
