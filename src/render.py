import math

import pygame

from .car import Car
from .config import TILE_SIZE
from .map.loader import MapData


_TILE_COLORS = {
    "road": (70, 72, 78),
    "wall": (24, 26, 30),
    "mud": (110, 80, 50),
    "start": (46, 130, 70),
    "finish": (170, 60, 55),
    "checkpoint": (200, 170, 70),
}


def render_frame(
    screen: pygame.Surface,
    map_data: MapData,
    car: Car,
    ghost_car: Car | None,
    creator_ghost_car: Car | None,
    car_color: tuple[int, int, int],
    elapsed_ms: int,
    run_active: bool,
    run_finished: bool,
    best_time_ms: int | None,
    creator_time_ms: int | None,
    show_new_best: bool,
    show_creator_beaten: bool,
    show_finish_flash: bool,
    ghost_enabled: bool,
    creator_ghost_enabled: bool,
    creator_ghost_available: bool,
    checkpoint_status: str,
    last_checkpoint_time_ms: int | None,
    last_checkpoint_delta_ms: int | None,
    visited_checkpoints: set[tuple[int, int]],
    countdown_value: float | None,
    show_go_flash: bool,
    show_best_time: bool,
    show_creator_time: bool,
    hint_text: str | None,
) -> None:
    screen.fill((18, 20, 24))
    for y, row in enumerate(map_data.tiles):
        for x, tile_id in enumerate(row):
            tile_name = map_data.legend.get(tile_id, "road")
            if tile_name == "checkpoint":
                if (x, y) in visited_checkpoints:
                    color = (230, 210, 140)
                else:
                    color = (160, 130, 60)
            else:
                color = _TILE_COLORS.get(tile_name, _TILE_COLORS["road"])
            rect = pygame.Rect(
                x * TILE_SIZE,
                y * TILE_SIZE,
                TILE_SIZE,
                TILE_SIZE,
            )
            pygame.draw.rect(screen, color, rect)

    if creator_ghost_car is not None:
        _draw_car(screen, creator_ghost_car, (20, 20, 20), outline_only=True)
    if ghost_car is not None:
        _draw_car(screen, ghost_car, (200, 200, 200), outline_only=True)
    _draw_car(screen, car, car_color)
    _draw_hud(
        screen,
        elapsed_ms,
        run_active,
        run_finished,
        best_time_ms,
        creator_time_ms,
        show_new_best,
        show_creator_beaten,
        ghost_enabled,
        creator_ghost_enabled,
        creator_ghost_available,
        checkpoint_status,
        last_checkpoint_time_ms,
        last_checkpoint_delta_ms,
        show_best_time,
        show_creator_time,
        hint_text,
    )

    if show_finish_flash:
        _draw_finish_flash(screen)

    if countdown_value is not None:
        _draw_countdown(screen, countdown_value)

    if show_go_flash:
        _draw_go_flash(screen)

    pygame.display.flip()


def _draw_car(
    screen: pygame.Surface,
    car: Car,
    color: tuple[int, int, int],
    outline_only: bool = False,
) -> None:
    body_length = TILE_SIZE * 0.9
    body_width = TILE_SIZE * 0.55
    nose_length = TILE_SIZE * 0.4

    half_length = body_length * 0.5
    half_width = body_width * 0.5

    body_points = [
        (half_length, -half_width),
        (half_length, half_width),
        (-half_length, half_width),
        (-half_length, -half_width),
    ]
    nose_points = [
        (half_length + nose_length, 0.0),
        (half_length * 0.9, -half_width * 0.6),
        (half_length * 0.9, half_width * 0.6),
    ]

    body = [_rotate_point(point, car.angle, car.x, car.y) for point in body_points]
    nose = [_rotate_point(point, car.angle, car.x, car.y) for point in nose_points]

    if outline_only:
        pygame.draw.polygon(screen, color, body, width=2)
        pygame.draw.polygon(screen, color, nose, width=2)
    else:
        pygame.draw.polygon(screen, color, body)
        pygame.draw.polygon(screen, (235, 120, 90), nose)


def _rotate_point(
    point: tuple[float, float],
    angle: float,
    origin_x: float,
    origin_y: float,
) -> tuple[int, int]:
    cos_a = math.cos(angle)
    sin_a = math.sin(angle)
    x, y = point
    rotated_x = x * cos_a - y * sin_a
    rotated_y = x * sin_a + y * cos_a
    return (int(origin_x + rotated_x), int(origin_y + rotated_y))


def _draw_hud(
    screen: pygame.Surface,
    elapsed_ms: int,
    run_active: bool,
    run_finished: bool,
    best_time_ms: int | None,
    creator_time_ms: int | None,
    show_new_best: bool,
    show_creator_beaten: bool,
    ghost_enabled: bool,
    creator_ghost_enabled: bool,
    creator_ghost_available: bool,
    checkpoint_status: str,
    last_checkpoint_time_ms: int | None,
    last_checkpoint_delta_ms: int | None,
    show_best_time: bool,
    show_creator_time: bool,
    hint_text: str | None,
) -> None:
    font = pygame.font.SysFont(
        ["Consolas", "Menlo", "Courier New", "Courier", "monospace"],
        16,
    )
    font_bold = pygame.font.SysFont(
        ["Consolas", "Menlo", "Courier New", "Courier", "monospace"],
        20,
        bold=True,
    )
    elapsed_seconds = elapsed_ms / 1000.0
    timer_text = f"Time: {elapsed_seconds:0.3f}s"
    if show_best_time:
        best_text = (
            "Best: --"
            if best_time_ms is None
            else f"Best: {best_time_ms / 1000.0:0.3f}s"
        )
        header_text = f"{timer_text}  |  {best_text}"
        if show_creator_time:
            creator_text = (
                "Creator: --"
                if creator_time_ms is None
                else f"Creator: {creator_time_ms / 1000.0:0.3f}s"
            )
            header_text = f"{header_text}  |  {creator_text}"
    else:
        header_text = timer_text
    surface = font.render(header_text, True, (230, 230, 235))
    screen.blit(surface, (12, 12))

    checkpoint_surface = font.render(checkpoint_status, True, (230, 230, 235))
    checkpoint_x = screen.get_width() - checkpoint_surface.get_width() - 12
    screen.blit(checkpoint_surface, (checkpoint_x, 12))

    if last_checkpoint_time_ms is not None:
        time_text = f"CP Time: {last_checkpoint_time_ms / 1000.0:0.3f}s"

        if last_checkpoint_delta_ms is not None:
            delta_seconds = last_checkpoint_delta_ms / 1000.0
            sign = "+" if delta_seconds > 0 else ""
            delta_text = f"Delta: {sign}{delta_seconds:0.3f}s"
            if last_checkpoint_delta_ms < 0:
                delta_color = (120, 210, 140)
            elif last_checkpoint_delta_ms > 0:
                delta_color = (220, 110, 100)
            else:
                delta_color = (180, 180, 190)
            time_color = delta_color
        else:
            delta_text = "Delta: --"
            delta_color = (180, 180, 190)
            time_color = (200, 200, 210)
        time_surface = font_bold.render(time_text, True, time_color)
        time_rect = time_surface.get_rect(
            center=(screen.get_width() // 2, screen.get_height() // 2 + 48)
        )
        screen.blit(time_surface, time_rect)
        delta_surface = font_bold.render(delta_text, True, delta_color)
        delta_rect = delta_surface.get_rect(
            center=(screen.get_width() // 2, screen.get_height() // 2 + 74)
        )
        screen.blit(delta_surface, delta_rect)

    if hint_text is None:
        ghost_label = "Ghost:On" if ghost_enabled else "Ghost:Off"
        hint_text = f"R=Restart  P=Clear Best  G={ghost_label}"
        if creator_ghost_available:
            creator_label = "On" if creator_ghost_enabled else "Off"
            hint_text = f"{hint_text}  C=Creator:{creator_label}"
        hint_text = f"{hint_text}  B=Back  Q=Quit"
    hint_surface = font.render(hint_text, True, (200, 200, 210))
    hint_x = (screen.get_width() - hint_surface.get_width()) // 2
    hint_y = screen.get_height() - hint_surface.get_height() - 8
    screen.blit(hint_surface, (hint_x, hint_y))

    badges: list[tuple[str, int, tuple[int, int, int]]] = []
    if show_new_best:
        badges.append(("NEW BEST!", 28, (235, 130, 80)))
    if show_creator_beaten:
        badges.append(("CREATOR BEAT!", 26, (230, 190, 90)))
    if badges:
        badge_pad_x = 14
        badge_pad_y = 8
        badge_gap = 8
        badge_surfaces: list[
            tuple[pygame.Surface, pygame.Rect, tuple[int, int, int]]
        ] = []
        total_height = 0
        for text, size, bg_color in badges:
            badge_font = pygame.font.Font(None, size)
            badge_text = badge_font.render(text, True, (255, 250, 235))
            badge_rect = badge_text.get_rect()
            total_height += badge_rect.height + badge_pad_y * 2
            badge_surfaces.append((badge_text, badge_rect, bg_color))
        total_height += badge_gap * (len(badge_surfaces) - 1)
        start_y = (screen.get_height() - total_height) // 2
        for badge_text, badge_rect, bg_color in badge_surfaces:
            badge_rect.centerx = screen.get_width() // 2
            badge_rect.y = start_y + badge_pad_y
            badge_bg = pygame.Surface(
                (
                    badge_rect.width + badge_pad_x * 2,
                    badge_rect.height + badge_pad_y * 2,
                ),
                pygame.SRCALPHA,
            )
            badge_bg.fill((*bg_color, 200))
            badge_bg_rect = badge_bg.get_rect(center=badge_rect.center)
            screen.blit(badge_bg, badge_bg_rect)
            screen.blit(badge_text, badge_rect)
            start_y += badge_rect.height + badge_pad_y * 2 + badge_gap


def _draw_finish_flash(screen: pygame.Surface) -> None:
    font = pygame.font.Font(None, 44)
    text = font.render("Finish!", True, (255, 245, 230))
    text_rect = text.get_rect(center=(screen.get_width() // 2, 60))

    pad_x = 18
    pad_y = 10
    backdrop = pygame.Surface(
        (text_rect.width + pad_x * 2, text_rect.height + pad_y * 2),
        pygame.SRCALPHA,
    )
    backdrop.fill((245, 220, 120, 90))
    screen.blit(backdrop, (text_rect.x - pad_x, text_rect.y - pad_y))
    screen.blit(text, text_rect)


def _draw_countdown(screen: pygame.Surface, countdown_value: float) -> None:
    font = pygame.font.Font(None, 72)
    text = f"{countdown_value:0.1f}".rstrip("0").rstrip(".")
    text_surface = font.render(text, True, (245, 245, 250))
    text_rect = text_surface.get_rect(
        center=(screen.get_width() // 2, screen.get_height() // 2)
    )
    backdrop = pygame.Surface(
        (text_rect.width + 40, text_rect.height + 24),
        pygame.SRCALPHA,
    )
    backdrop.fill((20, 22, 28, 180))
    screen.blit(backdrop, (text_rect.x - 20, text_rect.y - 12))
    screen.blit(text_surface, text_rect)


def _draw_go_flash(screen: pygame.Surface) -> None:
    font = pygame.font.Font(None, 72)
    text_surface = font.render("GO!", True, (245, 245, 250))
    text_rect = text_surface.get_rect(
        center=(screen.get_width() // 2, screen.get_height() // 2)
    )
    backdrop = pygame.Surface(
        (text_rect.width + 40, text_rect.height + 24),
        pygame.SRCALPHA,
    )
    backdrop.fill((40, 140, 90, 190))
    screen.blit(backdrop, (text_rect.x - 20, text_rect.y - 12))
    screen.blit(text_surface, text_rect)


def render_menu(
    screen: pygame.Surface,
    title: str,
    items: list[str],
    selected_index: int,
    subtitle: str | None = None,
    highlight_indices: set[int] | None = None,
    footer_lines: list[str] | None = None,
    footer_color: tuple[int, int, int] = (190, 190, 205),
    extra_spacing_after: set[int] | None = None,
    hint_text: str | None = None,
) -> None:
    screen.fill((18, 20, 24))
    title_font = pygame.font.Font(None, 52)
    item_font = pygame.font.Font(None, 32)
    hint_font = pygame.font.Font(None, 22)

    title_surface = title_font.render(title, True, (245, 245, 250))
    title_rect = title_surface.get_rect(center=(screen.get_width() // 2, 70))
    screen.blit(title_surface, title_rect)

    if subtitle:
        subtitle_surface = hint_font.render(subtitle, True, (190, 190, 205))
        subtitle_rect = subtitle_surface.get_rect(
            center=(screen.get_width() // 2, title_rect.bottom + 18)
        )
        screen.blit(subtitle_surface, subtitle_rect)

    start_y = 160
    current_y = start_y
    for index, item in enumerate(items):
        color = (240, 210, 140) if index == selected_index else (210, 210, 220)
        item_surface = item_font.render(item, True, color)
        item_rect = item_surface.get_rect(center=(screen.get_width() // 2, current_y))
        screen.blit(item_surface, item_rect)
        if highlight_indices and index in highlight_indices:
            border_rect = item_rect.inflate(26, 12)
            pygame.draw.rect(screen, (230, 190, 90), border_rect, width=2)
        current_y += 42
        if extra_spacing_after and index in extra_spacing_after:
            current_y += 18

    if footer_lines:
        footer_font = pygame.font.Font(None, 22)
        line_height = footer_font.get_linesize()
        footer_height = line_height * len(footer_lines)
        footer_y = screen.get_height() - 40 - 12 - footer_height
        for index, line in enumerate(footer_lines):
            footer_surface = footer_font.render(line, True, footer_color)
            footer_rect = footer_surface.get_rect(
                center=(screen.get_width() // 2, footer_y + index * line_height)
            )
            screen.blit(footer_surface, footer_rect)

    if hint_text is None:
        hint_text = "Up/Down=move, Enter=select, B=back, Q=quit"
    hint_surface = hint_font.render(hint_text, True, (160, 160, 175))
    hint_rect = hint_surface.get_rect(
        center=(screen.get_width() // 2, screen.get_height() - 40)
    )
    screen.blit(hint_surface, hint_rect)

    pygame.display.flip()


def render_color_menu(
    screen: pygame.Surface,
    title: str,
    items: list[str],
    selected_index: int,
    preview_color: tuple[int, int, int],
    subtitle: str | None = None,
    hint_text: str | None = None,
) -> None:
    screen.fill((18, 20, 24))
    title_font = pygame.font.Font(None, 52)
    item_font = pygame.font.Font(None, 32)
    hint_font = pygame.font.Font(None, 22)

    title_surface = title_font.render(title, True, (245, 245, 250))
    title_rect = title_surface.get_rect(center=(screen.get_width() // 2, 70))
    screen.blit(title_surface, title_rect)

    if subtitle:
        subtitle_surface = hint_font.render(subtitle, True, (190, 190, 205))
        subtitle_rect = subtitle_surface.get_rect(
            center=(screen.get_width() // 2, title_rect.bottom + 18)
        )
        screen.blit(subtitle_surface, subtitle_rect)

    start_y = 160
    for index, item in enumerate(items):
        color = (240, 210, 140) if index == selected_index else (210, 210, 220)
        item_surface = item_font.render(item, True, color)
        item_rect = item_surface.get_rect(
            center=(screen.get_width() // 2, start_y + index * 42)
        )
        screen.blit(item_surface, item_rect)

    preview_x = screen.get_width() // 2
    preview_y = screen.get_height() - 120
    preview_car = Car(x=preview_x, y=preview_y, angle=-math.pi / 2)
    _draw_car(screen, preview_car, preview_color)

    if hint_text is None:
        hint_text = "Up/Down=move, Enter=select, B=back, Q=quit"
    hint_surface = hint_font.render(hint_text, True, (160, 160, 175))
    hint_rect = hint_surface.get_rect(
        center=(screen.get_width() // 2, screen.get_height() - 40)
    )
    screen.blit(hint_surface, hint_rect)

    pygame.display.flip()


def render_message(
    screen: pygame.Surface,
    title: str,
    lines: list[str],
    hint_text: str | None = None,
    car_colors: list[tuple[int, int, int]] | None = None,
) -> None:
    screen.fill((18, 20, 24))
    title_font = pygame.font.Font(None, 48)
    text_font = pygame.font.Font(None, 24)

    title_surface = title_font.render(title, True, (245, 245, 250))
    title_rect = title_surface.get_rect(center=(screen.get_width() // 2, 70))
    screen.blit(title_surface, title_rect)

    start_y = 150
    for line in lines:
        line_surface = text_font.render(line, True, (210, 210, 220))
        line_rect = line_surface.get_rect(center=(screen.get_width() // 2, start_y))
        screen.blit(line_surface, line_rect)
        start_y += 32

    if car_colors:
        spacing = int(TILE_SIZE * 1.2)
        total_width = spacing * (len(car_colors) - 1)
        start_x = (screen.get_width() - total_width) // 2
        car_y = screen.get_height() - 92
        for index, color in enumerate(car_colors):
            car_x = start_x + index * spacing
            preview_car = Car(x=car_x, y=car_y, angle=-math.pi / 2)
            _draw_car(screen, preview_car, color)

    if hint_text is None:
        hint_text = "Up/Down=move, Enter=select, B=back, Q=quit"
    hint_surface = text_font.render(hint_text, True, (170, 170, 185))
    hint_rect = hint_surface.get_rect(
        center=(screen.get_width() // 2, screen.get_height() - 40)
    )
    screen.blit(hint_surface, hint_rect)

    pygame.display.flip()


def _find_tile(tiles: list[list[str]], tile_id: str) -> tuple[int, int] | None:
    for y, row in enumerate(tiles):
        for x, value in enumerate(row):
            if value == tile_id:
                return (x, y)
    return None


def _draw_start_direction(
    screen: pygame.Surface,
    start_tile: tuple[int, int],
    angle: float,
) -> None:
    center_x = (start_tile[0] + 0.5) * TILE_SIZE
    center_y = (start_tile[1] + 0.5) * TILE_SIZE
    shaft_length = TILE_SIZE * 0.38
    head_length = TILE_SIZE * 0.22
    tip_x = center_x + math.cos(angle) * (shaft_length + head_length)
    tip_y = center_y + math.sin(angle) * (shaft_length + head_length)
    base_x = center_x + math.cos(angle) * shaft_length
    base_y = center_y + math.sin(angle) * shaft_length
    perp_x = -math.sin(angle)
    perp_y = math.cos(angle)
    half_width = TILE_SIZE * 0.16
    left_x = base_x + perp_x * half_width
    left_y = base_y + perp_y * half_width
    right_x = base_x - perp_x * half_width
    right_y = base_y - perp_y * half_width
    color = (245, 235, 210)
    pygame.draw.line(screen, color, (center_x, center_y), (base_x, base_y), width=3)
    pygame.draw.polygon(
        screen,
        color,
        [(tip_x, tip_y), (left_x, left_y), (right_x, right_y)],
    )


def render_editor(
    screen: pygame.Surface,
    tiles: list[list[str]],
    legend: dict[str, str],
    cursor: tuple[int, int],
    selected_tile: str,
    status: str | None,
    start_angle: float,
    creator_time_ms: int | None,
) -> None:
    screen.fill((18, 20, 24))
    height = len(tiles)
    width = len(tiles[0]) if height else 0

    for y in range(height):
        for x in range(width):
            tile_id = tiles[y][x]
            tile_name = legend.get(tile_id, "road")
            color = _TILE_COLORS.get(tile_name, _TILE_COLORS["road"])
            rect = pygame.Rect(
                x * TILE_SIZE,
                y * TILE_SIZE,
                TILE_SIZE,
                TILE_SIZE,
            )
            pygame.draw.rect(screen, color, rect)

    cursor_x, cursor_y = cursor
    cursor_rect = pygame.Rect(
        cursor_x * TILE_SIZE,
        cursor_y * TILE_SIZE,
        TILE_SIZE,
        TILE_SIZE,
    )
    pygame.draw.rect(screen, (245, 245, 250), cursor_rect, width=2)

    start_tile = _find_tile(tiles, "3")
    if start_tile is not None:
        _draw_start_direction(screen, start_tile, start_angle)

    font = pygame.font.Font(None, 22)
    selected_name = legend.get(selected_tile, "road")
    palette_text = "Tile Type: 0=road, 1=wall, 2=mud, 3=start, 4=finish, 5=checkpoint"
    palette_surface = font.render(palette_text, True, (170, 170, 185))
    palette_rect = palette_surface.get_rect(center=(screen.get_width() // 2, 18))
    screen.blit(palette_surface, palette_rect)

    current_text = f"Current Tile: {selected_name}"
    current_surface = font.render(current_text, True, (220, 220, 230))
    current_rect = current_surface.get_rect(center=(screen.get_width() // 2, 42))
    screen.blit(current_surface, current_rect)

    solved_text = (
        "Creator solved: Yes" if creator_time_ms is not None else "Creator solved: No"
    )
    solved_surface = font.render(solved_text, True, (210, 210, 220))
    solved_rect = solved_surface.get_rect(
        center=(screen.get_width() // 2, screen.get_height() // 2 - 14)
    )
    screen.blit(solved_surface, solved_rect)

    if creator_time_ms is not None:
        creator_text = f"Creator best: {creator_time_ms / 1000.0:0.3f}s"
    else:
        creator_text = "Creator best: --"
    creator_surface = font.render(creator_text, True, (210, 210, 220))
    creator_rect = creator_surface.get_rect(
        center=(screen.get_width() // 2, screen.get_height() // 2 + 14)
    )
    screen.blit(creator_surface, creator_rect)

    hint_text = "Arrows=move, Space=paint, R=rotate start, S=test+save, B=back"
    hint_surface = font.render(hint_text, True, (200, 200, 210))
    hint_rect = hint_surface.get_rect(
        center=(screen.get_width() // 2, screen.get_height() - 28)
    )
    screen.blit(hint_surface, hint_rect)

    if status:
        status_surface = font.render(status, True, (235, 180, 90))
        status_rect = status_surface.get_rect(
            center=(screen.get_width() // 2, screen.get_height() - 68)
        )
        screen.blit(status_surface, status_rect)

    pygame.display.flip()
