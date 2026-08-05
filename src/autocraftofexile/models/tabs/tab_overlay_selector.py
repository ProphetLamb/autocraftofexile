from __future__ import annotations

import base64
import json
from collections.abc import Mapping
from dataclasses import dataclass
from importlib import resources
from typing import Any, Literal, Self

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
class OverlayShape:
    """One shape in normalized template coordinates."""

    kind: Literal["rectangle", "ellipse"]
    left: float
    top: float
    right: float
    bottom: float
    fill: str = "#101619"
    outline: str = "#74d4dc"
    width: int = 1
    stipple: str = "gray50"

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> Self:
        return cls(
            kind=data["kind"],
            left=float(data["left"]),
            top=float(data["top"]),
            right=float(data["right"]),
            bottom=float(data["bottom"]),
            fill=str(data.get("fill", "#101619")),
            outline=str(data.get("outline", "#74d4dc")),
            width=int(data.get("width", 1)),
            stipple=str(data.get("stipple", "gray50")),
        )


@dataclass(slots=True, frozen=True)
class TabOverlayDefinition:
    """Data-driven description of a selectable stash-tab overlay."""

    template_width: int
    template_height: int
    entries: Mapping[str, tuple[float, float]]
    shapes: tuple[OverlayShape, ...]
    title: str = "Select stash tab"
    instructions: str = (
        "Drag to create the mask. Drag inside to move it. "
        "Drag a handle to resize it. Enter confirms; Escape cancels."
    )

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> Self:
        template_size = data["template_size"]
        width, height = int(template_size[0]), int(template_size[1])
        return cls(
            template_width=width,
            template_height=height,
            entries={
                str(name): (float(point[0]) / width, float(point[1]) / height)
                for name, point in data["entries"].items()
            },
            shapes=tuple(OverlayShape.from_dict(shape) for shape in data["shapes"]),
            title=str(data.get("title", "Select stash tab")),
            instructions=str(data.get("instructions", cls.instructions)),
        )

    @classmethod
    def from_resource(cls, package: str, name: str) -> Self:
        """Load a definition from a resource bundled inside the Python module."""
        resource = resources.files(package).joinpath(name)
        return cls.from_dict(json.loads(resource.read_text(encoding="utf-8")))

    def map_selection(
        self,
        selection: OverlaySelection,
    ) -> dict[str, Coordinates]:
        return {
            name: Coordinates(
                x=selection.left + round(x * selection.width),
                y=selection.top + round(y * selection.height),
            )
            for name, (x, y) in self.entries.items()
        }


class TabOverlaySelector:
    """Reusable data-driven, movable, resizable alignment mask."""

    HANDLE_RADIUS = 7
    MINIMUM_SIZE = 48

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
        if selection is None:
            return None
        return self.definition.map_selection(selection)

    @staticmethod
    def _background_photo(tk: Any, screenshot: np.ndarray) -> Any:
        """Create a Tk image without requiring Pillow as a direct dependency."""
        success, encoded = cv2.imencode(".png", screenshot)
        if not success:
            raise ValueError("Unable to encode screenshot for the overlay window")
        return tk.PhotoImage(data=base64.b64encode(encoded).decode("ascii"))

    def select(self, screenshot: np.ndarray) -> OverlaySelection | None:
        import tkinter as tk

        if screenshot.ndim != 3 or screenshot.shape[2] != 3:
            raise ValueError("Expected a BGR screenshot")

        window = tk.Tk()
        window.title(self.definition.title)
        window.attributes("-fullscreen", True)  # pyright: ignore[reportUnknownMemberType]
        window.attributes("-topmost", True)  # pyright: ignore[reportUnknownMemberType]

        background_photo = self._background_photo(tk, screenshot)
        canvas = tk.Canvas(
            window,
            width=screenshot.shape[1],
            height=screenshot.shape[0],
            cursor="crosshair",
            highlightthickness=0,
        )
        canvas.pack(fill=tk.BOTH, expand=True)
        canvas.create_image(0, 0, anchor=tk.NW, image=background_photo)  # pyright: ignore[reportUnknownMemberType]
        canvas.create_rectangle(
            8,
            8,
            screenshot.shape[1] - 8,
            50,
            fill="#101010",
            stipple="gray50",
            outline="",
        )
        canvas.create_text(
            18,
            18,
            anchor=tk.NW,
            text=self.definition.instructions,
            fill="white",
            font=("Segoe UI", 13, "bold"),
        )

        state: dict[str, Any] = {
            "selection": None,
            "interaction": None,
            "origin": None,
            "initial": None,
            "rendered": [],
        }

        def handle_points(
            selection: OverlaySelection,
        ) -> dict[str, tuple[int, int]]:
            center_x = (selection.left + selection.right) // 2
            center_y = (selection.top + selection.bottom) // 2
            return {
                "nw": (selection.left, selection.top),
                "n": (center_x, selection.top),
                "ne": (selection.right, selection.top),
                "e": (selection.right, center_y),
                "se": (selection.right, selection.bottom),
                "s": (center_x, selection.bottom),
                "sw": (selection.left, selection.bottom),
                "w": (selection.left, center_y),
            }

        def hit_handle(x: int, y: int) -> str | None:
            selection = state["selection"]
            if selection is None:
                return None
            for name, (handle_x, handle_y) in handle_points(selection).items():
                if (
                    abs(x - handle_x) <= self.HANDLE_RADIUS + 3
                    and abs(y - handle_y) <= self.HANDLE_RADIUS + 3
                ):
                    return name
            return None

        @staticmethod
        def contains(selection: OverlaySelection, x: int, y: int) -> bool:
            return (
                selection.left <= x <= selection.right
                and selection.top <= y <= selection.bottom
            )

        def clear_rendering() -> None:
            for identifier in state["rendered"]:
                canvas.delete(identifier)
            state["rendered"] = []

        def scale_shape(
            shape: OverlayShape,
            selection: OverlaySelection,
        ) -> tuple[int, int, int, int]:
            return (
                selection.left + round(shape.left * selection.width),
                selection.top + round(shape.top * selection.height),
                selection.left + round(shape.right * selection.width),
                selection.top + round(shape.bottom * selection.height),
            )

        def render(selection: OverlaySelection) -> None:
            clear_rendering()

            # One semi-transparent alignment mask generated entirely from the
            # definition. There is no preview image or duplicated screenshot.
            state["rendered"].append(
                canvas.create_rectangle(
                    selection.left,
                    selection.top,
                    selection.right,
                    selection.bottom,
                    fill="#0b1718",
                    stipple="gray50",
                    outline="#55ff88",
                    width=3,
                )
            )
            for shape in self.definition.shapes:
                coordinates = scale_shape(shape, selection)
                options: dict[str, Any] = {
                    "fill": shape.fill,
                    "outline": shape.outline,
                    "width": shape.width,
                    "stipple": shape.stipple,
                }
                if shape.kind == "rectangle":
                    identifier = canvas.create_rectangle(*coordinates, **options)
                else:
                    identifier = canvas.create_oval(*coordinates, **options)
                state["rendered"].append(identifier)

            for handle_x, handle_y in handle_points(selection).values():
                radius = self.HANDLE_RADIUS
                state["rendered"].append(
                    canvas.create_rectangle(
                        handle_x - radius,
                        handle_y - radius,
                        handle_x + radius,
                        handle_y + radius,
                        fill="#55ff88",
                        outline="#102414",
                    )
                )

        def clamp(selection: OverlaySelection) -> OverlaySelection:
            screen_width = screenshot.shape[1]
            screen_height = screenshot.shape[0]
            width = min(screen_width, max(self.MINIMUM_SIZE, selection.width))
            height = min(screen_height, max(self.MINIMUM_SIZE, selection.height))
            left = min(max(0, selection.left), screen_width - width)
            top = min(max(0, selection.top), screen_height - height)
            return OverlaySelection(left, top, left + width, top + height)

        def resized_selection(
            initial: OverlaySelection,
            handle: str,
            x: int,
            y: int,
        ) -> OverlaySelection:
            left, top, right, bottom = (
                initial.left,
                initial.top,
                initial.right,
                initial.bottom,
            )
            if "w" in handle:
                left = min(x, right - self.MINIMUM_SIZE)
            if "e" in handle:
                right = max(x, left + self.MINIMUM_SIZE)
            if "n" in handle:
                top = min(y, bottom - self.MINIMUM_SIZE)
            if "s" in handle:
                bottom = max(y, top + self.MINIMUM_SIZE)
            return clamp(OverlaySelection(left, top, right, bottom))

        def mouse_down(event: tk.Event) -> None:
            selection = state["selection"]
            handle = hit_handle(event.x, event.y)
            state["origin"] = (event.x, event.y)
            state["initial"] = selection
            if handle is not None:
                state["interaction"] = ("resize", handle)
            elif selection is not None and contains(selection, event.x, event.y):
                state["interaction"] = ("move", None)
            else:
                state["interaction"] = ("create", None)
                state["selection"] = None
                clear_rendering()

        def mouse_move(event: tk.Event) -> None:
            interaction = state["interaction"]
            origin = state["origin"]
            if interaction is None or origin is None:
                return
            mode, handle = interaction
            origin_x, origin_y = origin
            initial = state["initial"]

            if mode == "create":
                left, right = sorted((origin_x, event.x))
                top, bottom = sorted((origin_y, event.y))
                if right - left < self.MINIMUM_SIZE or bottom - top < self.MINIMUM_SIZE:
                    return
                selection = OverlaySelection(left, top, right, bottom)
            elif mode == "move" and initial is not None:
                delta_x = event.x - origin_x
                delta_y = event.y - origin_y
                selection = clamp(
                    OverlaySelection(
                        initial.left + delta_x,
                        initial.top + delta_y,
                        initial.right + delta_x,
                        initial.bottom + delta_y,
                    )
                )
            elif mode == "resize" and initial is not None and handle is not None:
                selection = resized_selection(initial, handle, event.x, event.y)
            else:
                return

            state["selection"] = selection
            render(selection)

        def mouse_up(_event: tk.Event) -> None:
            state["interaction"] = None
            state["origin"] = None
            state["initial"] = None

        def confirm(_event: tk.Event | None = None) -> None:
            if state["selection"] is not None:
                window.quit()

        def cancel(_event: tk.Event | None = None) -> None:
            state["selection"] = None
            window.quit()

        canvas.bind("<ButtonPress-1>", mouse_down)
        canvas.bind("<B1-Motion>", mouse_move)
        canvas.bind("<ButtonRelease-1>", mouse_up)
        window.bind("<Return>", confirm)
        window.bind("<Escape>", cancel)
        window.mainloop()
        selection = state["selection"]
        window.destroy()
        return selection
