import json
import math
import json
from pathlib import Path

import pygame

from .car import Car
from .config import (
    CAR_RADIUS,
    FIXED_TIMESTEP,
    MUD_ACCEL_MULTIPLIER,
    MUD_SPEED_MULTIPLIER,
    MUD_STICKY_TIME,
    MUD_TURN_MULTIPLIER,
    TARGET_FPS,
    TILE_SIZE,
)
from .input import InputState, read_input
from .map.loader import MapData, load_map
from .physics import update_car
from .persistence.db import (
    clear_best_time,
    clear_all_best_times,
    clear_all_creator_beaten,
    clear_creator_beaten,
    init_db,
    load_best_time,
    load_creator_beaten,
    load_creator_time,
    save_best_time,
    save_creator_beaten,
    save_creator_time,
)
from .replay.io import ReplayData, load_replay, save_replay
from .render import (
    render_color_menu,
    render_editor,
    render_frame,
    render_menu,
    render_message,
)


class Game:
    def __init__(self) -> None:
        pygame.init()
        self.is_running = True
        self.map = self._load_default_map()
        self.car = self._spawn_car(self.map)
        self.run_active = False
        self.run_finished = False
        self.run_elapsed_ms = 0.0
        self.elapsed_ms = 0
        self.track_id = "track_01"
        self.db_path = Path("data/best_times.db")
        init_db(self.db_path)
        self.best_time_ms = load_best_time(self.db_path, self.track_id)
        self.creator_time_ms = load_creator_time(self.db_path, self.track_id)
        self.creator_beaten = load_creator_beaten(self.db_path, self.track_id)
        if (
            not self.creator_beaten
            and self.best_time_ms is not None
            and self.creator_time_ms is not None
            and self.best_time_ms <= self.creator_time_ms
        ):
            self.creator_beaten = True
            save_creator_beaten(self.db_path, self.track_id, True)
        self.best_flash_until = 0
        self.creator_beaten_flash_until = 0
        self.finish_flash_until = 0
        self.checkpoints = self.map.checkpoints
        self.visited_checkpoints: set[tuple[int, int]] = set()
        self.replay_path = Path("data/replays") / f"{self.track_id}_last.json"
        self.creator_replay_path = (
            Path("data/replays") / f"{self.track_id}_creator.json"
        )
        self.replay_inputs: list[dict[str, bool]] = []
        self.ghost_inputs: list[dict[str, bool]] = []
        self.ghost_index = 0
        self.ghost_car: Car | None = None
        self.ghost_enabled = True
        self.ghost_active = False
        self.creator_ghost_inputs: list[dict[str, bool]] = []
        self.creator_ghost_index = 0
        self.creator_ghost_car: Car | None = None
        self.creator_ghost_enabled = False
        self.creator_ghost_active = False
        self.accumulator = 0.0
        self.countdown_active = False
        self.countdown_time = 0.0
        self.go_flash_until = 0
        self.freeze_car = False
        self.state = "menu"
        self.menu_index = 0
        self.role = "player"
        self.menu_items = ["Race", "Color", "Track editor", "About", "Exit"]
        self.map_options = [
            ("Track 1", "track_01"),
            ("Track 2", "track_02"),
            ("Track 3", "track_03"),
            ("Custom", "custom"),
        ]
        self.map_index = 0
        self.car_options = [
            ("Green", (80, 170, 110)),
            ("Blue", (70, 120, 210)),
            ("Yellow", (220, 190, 80)),
            ("Red", (210, 80, 70)),
        ]
        self.car_index = 0
        self.car_color = self.car_options[self.car_index][1]
        self.editor_tiles: list[list[str]] = []
        self.editor_cursor = (0, 0)
        self.editor_tile = "0"
        self.editor_status: str | None = None
        self.editor_pending_save = False
        self.editor_start_angle = 0.0
        self.editor_prev_map: MapData | None = None
        self.editor_prev_track_id: str | None = None
        self.editor_prev_best_time: int | None = None
        self.editor_prev_replay_path: Path | None = None
        self.editor_prev_checkpoints: list[tuple[int, int]] | None = None
        self.editor_prev_ghost_enabled: bool | None = None
        self.editor_prev_creator_ghost_enabled: bool | None = None
        self.editor_map_key: str | None = None
        self.editor_map_index = 0
        self.creator_toggle_armed = False
        self.reset_toggle_armed = False
        self.cheat_toggle_armed = False
        self.menu_flash_text: str | None = None
        self.menu_flash_until = 0
        self.screen = pygame.display.set_mode(
            (self.map.width * TILE_SIZE, self.map.height * TILE_SIZE)
        )
        pygame.display.set_caption("Vibe Racer")
        self.clock = pygame.time.Clock()

    def run(self) -> None:
        while self.is_running:
            if self.state == "menu":
                keys = pygame.key.get_pressed()
                combo_active = (
                    keys[pygame.K_2] and keys[pygame.K_4] and keys[pygame.K_7]
                )
                if combo_active and not self.creator_toggle_armed:
                    self._toggle_role()
                    self.creator_toggle_armed = True
                elif not combo_active:
                    self.creator_toggle_armed = False
                reset_combo = keys[pygame.K_2] and keys[pygame.K_5] and keys[pygame.K_0]
                if reset_combo and not self.reset_toggle_armed:
                    self._reset_player_records()
                    self.reset_toggle_armed = True
                elif not reset_combo:
                    self.reset_toggle_armed = False
                cheat_combo = keys[pygame.K_1] and keys[pygame.K_3] and keys[pygame.K_7]
                if cheat_combo and not self.cheat_toggle_armed:
                    self._activate_cheater_mode()
                    self.cheat_toggle_armed = True
                elif not cheat_combo:
                    self.cheat_toggle_armed = False
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.is_running = False
                if self.state in {"race", "editor_test"}:
                    self._handle_race_event(event)
                else:
                    self._handle_menu_event(event)

            if self.state not in {"race", "editor_test"}:
                self._render_menu_state()
                self.clock.tick(TARGET_FPS)
                continue

            dt = self.clock.tick(TARGET_FPS) / 1000.0
            if self.countdown_active:
                self._update_countdown(dt)
                render_frame(
                    self.screen,
                    self.map,
                    self.car,
                    self.ghost_car,
                    self.creator_ghost_car,
                    self.car_color,
                    self.elapsed_ms,
                    self.run_active,
                    self.run_finished,
                    self.best_time_ms,
                    self.creator_time_ms,
                    self._should_show_best_flash(),
                    self.state == "race" and self._should_show_creator_beaten_flash(),
                    self._should_show_finish_flash() if self.state == "race" else False,
                    self.ghost_enabled,
                    self.creator_ghost_enabled,
                    self._creator_ghost_available(),
                    self._checkpoint_status(),
                    self.visited_checkpoints,
                    self._countdown_display(),
                    self._should_show_go_flash(),
                    self.state == "race",
                    self.state == "race" and self._creator_time_beaten(),
                    "R=Restart  B=Back" if self.state == "editor_test" else None,
                )
                continue
            self.accumulator = min(self.accumulator + dt, 0.25)
            inputs = read_input()
            if self._should_start_run(inputs):
                self.run_active = True
                self.run_elapsed_ms = 0.0
                self.replay_inputs = []
                self.visited_checkpoints = set()
                self._start_ghost()

            while self.accumulator >= FIXED_TIMESTEP:
                if not self.freeze_car:
                    previous_x, previous_y = self.car.x, self.car.y
                    accel_multiplier, speed_multiplier, turn_multiplier = (
                        self._surface_multipliers(self.car, FIXED_TIMESTEP)
                    )
                    update_car(
                        self.car,
                        inputs,
                        FIXED_TIMESTEP,
                        accel_multiplier=accel_multiplier,
                        max_speed_multiplier=speed_multiplier,
                        turn_multiplier=turn_multiplier,
                    )
                    self._resolve_collisions(self.car, previous_x, previous_y)

                if self.run_active:
                    self.replay_inputs.append(inputs.to_dict())
                    self.run_elapsed_ms += FIXED_TIMESTEP * 1000.0
                    self.elapsed_ms = int(self.run_elapsed_ms)
                    self._update_checkpoints()
                    if self._is_finish_at(self.car.x, self.car.y):
                        if self._checkpoints_complete():
                            if self.state == "editor_test":
                                self._complete_editor_test(self.elapsed_ms)
                            else:
                                self.run_active = False
                                self.run_finished = True
                                self.freeze_car = True
                                self.car.speed = 0.0
                                self._maybe_save_best_time(self.elapsed_ms)
                                self._save_replay()
                                self.finish_flash_until = pygame.time.get_ticks() + 1500

                self._update_ghost(FIXED_TIMESTEP)
                self._update_creator_ghost(FIXED_TIMESTEP)
                self.accumulator -= FIXED_TIMESTEP

            render_frame(
                self.screen,
                self.map,
                self.car,
                self.ghost_car,
                self.creator_ghost_car,
                self.car_color,
                self.elapsed_ms,
                self.run_active,
                self.run_finished,
                self.best_time_ms,
                self.creator_time_ms,
                self._should_show_best_flash(),
                self.state == "race" and self._should_show_creator_beaten_flash(),
                self._should_show_finish_flash() if self.state == "race" else False,
                self.ghost_enabled,
                self.creator_ghost_enabled,
                self._creator_ghost_available(),
                self._checkpoint_status(),
                self.visited_checkpoints,
                None,
                self._should_show_go_flash(),
                self.state == "race",
                self.state == "race" and self._creator_time_beaten(),
                "R=Restart  B=Back" if self.state == "editor_test" else None,
            )

        pygame.quit()

    def _load_default_map(self) -> MapData:
        map_path = Path("assets/maps/track_01.json")
        return load_map(map_path)

    def _map_path(self, map_key: str) -> Path:
        return Path("assets/maps") / f"{map_key}.json"

    def _apply_map(self, map_key: str) -> None:
        map_path = self._map_path(map_key)
        try:
            self.map = load_map(map_path)
        except ValueError:
            if map_key == "custom":
                self._start_editor("custom")
                self.editor_status = "Custom map invalid. Fix and save."
                return
            raise
        self.checkpoints = self.map.checkpoints
        self.track_id = map_key
        self.replay_path = Path("data/replays") / f"{self.track_id}_last.json"
        self.creator_replay_path = (
            Path("data/replays") / f"{self.track_id}_creator.json"
        )
        self.best_time_ms = load_best_time(self.db_path, self.track_id)
        self.creator_time_ms = load_creator_time(self.db_path, self.track_id)
        self.creator_beaten = load_creator_beaten(self.db_path, self.track_id)
        if (
            not self.creator_beaten
            and self.best_time_ms is not None
            and self.creator_time_ms is not None
            and self.best_time_ms <= self.creator_time_ms
        ):
            self.creator_beaten = True
            save_creator_beaten(self.db_path, self.track_id, True)
        self.creator_ghost_enabled = False
        self.creator_ghost_inputs = []
        self.creator_ghost_index = 0
        self.creator_ghost_car = None
        self.creator_ghost_active = False
        self.screen = pygame.display.set_mode(
            (self.map.width * TILE_SIZE, self.map.height * TILE_SIZE)
        )
        self._reset_run()
        self._start_countdown()

    def _spawn_car(self, map_data: MapData) -> Car:
        start_x, start_y = map_data.start
        return Car(
            x=(start_x + 0.5) * TILE_SIZE,
            y=(start_y + 0.5) * TILE_SIZE,
            angle=map_data.start_angle,
        )

    def _reset_run(self) -> None:
        self.car = self._spawn_car(self.map)
        self.run_active = False
        self.run_finished = False
        self.run_elapsed_ms = 0.0
        self.elapsed_ms = 0
        self.countdown_active = False
        self.countdown_time = 0.0
        self.go_flash_until = 0
        self.freeze_car = False
        self.accumulator = 0.0
        self.replay_inputs = []
        self.ghost_inputs = []
        self.ghost_index = 0
        self.ghost_car = None
        self.ghost_active = False
        self.creator_ghost_inputs = []
        self.creator_ghost_index = 0
        self.creator_ghost_car = None
        self.creator_ghost_active = False
        self.visited_checkpoints = set()
        self.creator_beaten_flash_until = 0

    def _maybe_save_best_time(self, elapsed_ms: int) -> None:
        if self.best_time_ms is None or elapsed_ms < self.best_time_ms:
            self.best_time_ms = elapsed_ms
            save_best_time(self.db_path, self.track_id, elapsed_ms)
            self.best_flash_until = pygame.time.get_ticks() + 1500
        if (
            not self.creator_beaten
            and self.creator_time_ms is not None
            and elapsed_ms <= self.creator_time_ms
        ):
            self.creator_beaten = True
            save_creator_beaten(self.db_path, self.track_id, True)
            self.creator_beaten_flash_until = pygame.time.get_ticks() + 1500

    def _reset_best_time(self) -> None:
        self.best_time_ms = None
        clear_best_time(self.db_path, self.track_id)
        clear_creator_beaten(self.db_path, self.track_id)
        self.creator_beaten = False
        if self.replay_path.exists():
            self.replay_path.unlink()
        self.ghost_inputs = []
        self.ghost_index = 0
        self.ghost_car = None
        self.ghost_active = False
        self.creator_beaten_flash_until = 0

    def _should_show_best_flash(self) -> bool:
        return pygame.time.get_ticks() < self.best_flash_until

    def _should_show_creator_beaten_flash(self) -> bool:
        return pygame.time.get_ticks() < self.creator_beaten_flash_until

    def _surface_multipliers(self, car: Car, dt: float) -> tuple[float, float, float]:
        if self._tile_name_at(car.x, car.y) == "mud":
            car.mud_timer = MUD_STICKY_TIME
        elif car.mud_timer > 0.0:
            car.mud_timer = max(0.0, car.mud_timer - dt)

        if car.mud_timer > 0.0:
            return (MUD_ACCEL_MULTIPLIER, MUD_SPEED_MULTIPLIER, MUD_TURN_MULTIPLIER)
        return (1.0, 1.0, 1.0)

    def _tile_name_at(self, x: float, y: float) -> str:
        tile_x = int(x // TILE_SIZE)
        tile_y = int(y // TILE_SIZE)
        if tile_x < 0 or tile_y < 0:
            return "wall"
        if tile_x >= self.map.width or tile_y >= self.map.height:
            return "wall"
        tile_id = self.map.tile_at(tile_x, tile_y)
        return self.map.legend.get(tile_id, "road")

    def _update_checkpoints(self) -> None:
        tile_x = int(self.car.x // TILE_SIZE)
        tile_y = int(self.car.y // TILE_SIZE)
        if (tile_x, tile_y) in self.checkpoints:
            self.visited_checkpoints.add((tile_x, tile_y))

    def _checkpoints_complete(self) -> bool:
        return len(self.visited_checkpoints) >= len(self.checkpoints)

    def _checkpoint_status(self) -> str:
        total = len(self.checkpoints)
        if total == 0:
            return "CP: --"
        return f"CP: {min(len(self.visited_checkpoints), total)}/{total}"

    def _creator_time_beaten(self) -> bool:
        if self.creator_beaten:
            return True
        if self.best_time_ms is None or self.creator_time_ms is None:
            return False
        return self.best_time_ms <= self.creator_time_ms

    def _creator_ghost_available(self) -> bool:
        if not self._creator_time_beaten():
            return False
        return self.creator_replay_path.exists()

    def _should_show_finish_flash(self) -> bool:
        return pygame.time.get_ticks() < self.finish_flash_until

    def _replay_meta(self) -> dict[str, float | int]:
        return {
            "fixed_timestep": FIXED_TIMESTEP,
            "mud_accel_multiplier": MUD_ACCEL_MULTIPLIER,
            "mud_speed_multiplier": MUD_SPEED_MULTIPLIER,
            "mud_turn_multiplier": MUD_TURN_MULTIPLIER,
            "mud_sticky_time": MUD_STICKY_TIME,
            "start_angle": self.map.start_angle,
        }

    def _is_replay_compatible(self, replay: ReplayData) -> bool:
        if not replay.meta:
            return False
        meta = replay.meta
        return (
            meta.get("fixed_timestep") == FIXED_TIMESTEP
            and meta.get("mud_accel_multiplier") == MUD_ACCEL_MULTIPLIER
            and meta.get("mud_speed_multiplier") == MUD_SPEED_MULTIPLIER
            and meta.get("mud_turn_multiplier") == MUD_TURN_MULTIPLIER
            and meta.get("mud_sticky_time") == MUD_STICKY_TIME
            and meta.get("start_angle") == self.map.start_angle
        )

    def _start_ghost(self) -> None:
        self._start_player_ghost()
        self._start_creator_ghost()

    def _start_player_ghost(self) -> None:
        if not self.ghost_enabled:
            self.ghost_inputs = []
            self.ghost_index = 0
            self.ghost_car = None
            self.ghost_active = False
            return
        if self.replay_path.exists():
            replay = load_replay(self.replay_path)
            if self._is_replay_compatible(replay):
                self.ghost_inputs = replay.inputs
                self.ghost_index = 0
                self.ghost_car = self._spawn_car(self.map)
                self.ghost_active = True
            else:
                self.ghost_inputs = []
                self.ghost_index = 0
                self.ghost_car = None
                self.ghost_active = False
        else:
            self.ghost_inputs = []
            self.ghost_index = 0
            self.ghost_car = None
            self.ghost_active = False

    def _start_creator_ghost(self) -> None:
        if not self.creator_ghost_enabled or not self._creator_ghost_available():
            self.creator_ghost_inputs = []
            self.creator_ghost_index = 0
            self.creator_ghost_car = None
            self.creator_ghost_active = False
            return
        if self.creator_replay_path.exists():
            replay = load_replay(self.creator_replay_path)
            if self._is_replay_compatible(replay):
                self.creator_ghost_inputs = replay.inputs
                self.creator_ghost_index = 0
                self.creator_ghost_car = self._spawn_car(self.map)
                self.creator_ghost_active = True
                return
        self.creator_ghost_inputs = []
        self.creator_ghost_index = 0
        self.creator_ghost_car = None
        self.creator_ghost_active = False

    def _update_ghost(self, dt: float) -> None:
        if not self.ghost_active or not self.ghost_car:
            return
        if self.ghost_index >= len(self.ghost_inputs):
            self.ghost_active = False
            return
        replay_input = InputState.from_dict(self.ghost_inputs[self.ghost_index])
        previous_x, previous_y = self.ghost_car.x, self.ghost_car.y
        accel_multiplier, speed_multiplier, turn_multiplier = self._surface_multipliers(
            self.ghost_car, dt
        )
        update_car(
            self.ghost_car,
            replay_input,
            dt,
            accel_multiplier=accel_multiplier,
            max_speed_multiplier=speed_multiplier,
            turn_multiplier=turn_multiplier,
        )
        self._resolve_collisions(self.ghost_car, previous_x, previous_y)
        self.ghost_index += 1

    def _update_creator_ghost(self, dt: float) -> None:
        if not self.creator_ghost_active or not self.creator_ghost_car:
            return
        if self.creator_ghost_index >= len(self.creator_ghost_inputs):
            self.creator_ghost_active = False
            return
        replay_input = InputState.from_dict(
            self.creator_ghost_inputs[self.creator_ghost_index]
        )
        previous_x, previous_y = self.creator_ghost_car.x, self.creator_ghost_car.y
        accel_multiplier, speed_multiplier, turn_multiplier = self._surface_multipliers(
            self.creator_ghost_car, dt
        )
        update_car(
            self.creator_ghost_car,
            replay_input,
            dt,
            accel_multiplier=accel_multiplier,
            max_speed_multiplier=speed_multiplier,
            turn_multiplier=turn_multiplier,
        )
        self._resolve_collisions(self.creator_ghost_car, previous_x, previous_y)
        self.creator_ghost_index += 1

    def _save_replay(self) -> None:
        self.replay_path.parent.mkdir(parents=True, exist_ok=True)
        save_replay(self.replay_path, self.replay_inputs, self._replay_meta())

    def _save_creator_replay(self) -> None:
        self.creator_replay_path.parent.mkdir(parents=True, exist_ok=True)
        save_replay(
            self.creator_replay_path,
            self.replay_inputs,
            self._replay_meta(),
        )

    def _is_wall_at(self, x: float, y: float) -> bool:
        tile_x = int(x // TILE_SIZE)
        tile_y = int(y // TILE_SIZE)
        if tile_x < 0 or tile_y < 0:
            return True
        if tile_x >= self.map.width or tile_y >= self.map.height:
            return True
        return self.map.is_wall(tile_x, tile_y)

    def _is_finish_at(self, x: float, y: float) -> bool:
        tile_x = int(x // TILE_SIZE)
        tile_y = int(y // TILE_SIZE)
        if tile_x < 0 or tile_y < 0:
            return False
        if tile_x >= self.map.width or tile_y >= self.map.height:
            return False
        tile_id = self.map.tile_at(tile_x, tile_y)
        return self.map.legend.get(tile_id) == "finish"

    def _resolve_collisions(
        self, car: Car, previous_x: float, previous_y: float
    ) -> None:
        if not self._collides_at(car.x, previous_y):
            resolved_x = car.x
        else:
            resolved_x = previous_x

        if not self._collides_at(resolved_x, car.y):
            resolved_y = car.y
        else:
            resolved_y = previous_y

        if resolved_x != car.x or resolved_y != car.y:
            move_x = car.x - previous_x
            move_y = car.y - previous_y
            car.speed *= 0.6
            car.x = resolved_x - move_x * 0.1
            car.y = resolved_y - move_y * 0.1
        else:
            car.x = resolved_x
            car.y = resolved_y

    def _collides_at(self, x: float, y: float) -> bool:
        min_tile_x = int((x - CAR_RADIUS) // TILE_SIZE)
        max_tile_x = int((x + CAR_RADIUS) // TILE_SIZE)
        min_tile_y = int((y - CAR_RADIUS) // TILE_SIZE)
        max_tile_y = int((y + CAR_RADIUS) // TILE_SIZE)

        for tile_y in range(min_tile_y, max_tile_y + 1):
            for tile_x in range(min_tile_x, max_tile_x + 1):
                if tile_x < 0 or tile_y < 0:
                    return True
                if tile_x >= self.map.width or tile_y >= self.map.height:
                    return True
                if not self.map.is_wall(tile_x, tile_y):
                    continue
                if self._circle_intersects_tile(x, y, tile_x, tile_y):
                    return True
        return False

    def _circle_intersects_tile(
        self, center_x: float, center_y: float, tile_x: int, tile_y: int
    ) -> bool:
        rect_left = tile_x * TILE_SIZE
        rect_top = tile_y * TILE_SIZE
        rect_right = rect_left + TILE_SIZE
        rect_bottom = rect_top + TILE_SIZE

        closest_x = min(max(center_x, rect_left), rect_right)
        closest_y = min(max(center_y, rect_top), rect_bottom)

        dx = center_x - closest_x
        dy = center_y - closest_y
        return (dx * dx + dy * dy) <= (CAR_RADIUS * CAR_RADIUS)

    def _should_start_run(self, inputs: InputState) -> bool:
        if self.run_active or self.run_finished:
            return False
        return any(
            (
                inputs.accelerate,
                inputs.brake,
                inputs.turn_left,
                inputs.turn_right,
            )
        )

    def _handle_race_event(self, event: pygame.event.Event) -> None:
        if event.type != pygame.KEYDOWN:
            return
        if event.key == pygame.K_r:
            self._reset_run()
            self._start_countdown()
        elif event.key == pygame.K_p:
            self._reset_best_time()
        elif event.key == pygame.K_q:
            self.is_running = False
        elif event.key == pygame.K_g:
            self.ghost_enabled = not self.ghost_enabled
            if not self.ghost_enabled:
                self.ghost_car = None
                self.ghost_active = False
        elif event.key == pygame.K_c:
            if self._creator_ghost_available():
                self.creator_ghost_enabled = not self.creator_ghost_enabled
                if not self.creator_ghost_enabled:
                    self.creator_ghost_car = None
                    self.creator_ghost_active = False
        elif event.key == pygame.K_b:
            if self.state == "editor_test":
                self._cancel_editor_test()
            else:
                self.state = "map_select"
                self._reset_run()
        elif event.key == pygame.K_ESCAPE:
            self.state = "menu"
            self._reset_run()

    def _handle_menu_event(self, event: pygame.event.Event) -> None:
        if event.type != pygame.KEYDOWN:
            return
        if event.key == pygame.K_q:
            self.is_running = False
            return
        if event.key == pygame.K_b:
            if self.state == "map_select":
                self.state = "menu"
            elif self.state == "editor":
                self._exit_editor()
            elif self.state != "menu":
                self.state = "menu"
            return
        if event.key == pygame.K_ESCAPE:
            if self.state == "editor":
                self._exit_editor()
            elif self.state != "menu":
                self.state = "menu"
            return

        if self.state == "menu":
            self._handle_main_menu(event)
        elif self.state == "map_select":
            self._handle_map_menu(event)
        elif self.state == "car_select":
            self._handle_car_menu(event)
        elif self.state == "editor_select":
            self._handle_editor_select_menu(event)
        elif self.state == "editor":
            self._handle_editor_event(event)
        elif self.state == "about":
            if event.key in {pygame.K_RETURN, pygame.K_KP_ENTER}:
                self.state = "menu"

    def _handle_main_menu(self, event: pygame.event.Event) -> None:
        if event.key == pygame.K_UP:
            self.menu_index = (self.menu_index - 1) % len(self.menu_items)
        elif event.key == pygame.K_DOWN:
            self.menu_index = (self.menu_index + 1) % len(self.menu_items)
        elif event.key in {pygame.K_RETURN, pygame.K_KP_ENTER}:
            selection = self.menu_index
            if selection == 0:
                self.state = "map_select"
            elif selection == 1:
                self.state = "car_select"
            elif selection == 2:
                self.state = "editor_select"
            elif selection == 3:
                self.state = "about"
            elif selection == 4:
                self.is_running = False

    def _handle_map_menu(self, event: pygame.event.Event) -> None:
        if event.key == pygame.K_UP:
            self.map_index = (self.map_index - 1) % len(self.map_options)
        elif event.key == pygame.K_DOWN:
            self.map_index = (self.map_index + 1) % len(self.map_options)
        elif event.key in {pygame.K_RETURN, pygame.K_KP_ENTER}:
            _, map_key = self.map_options[self.map_index]
            self._apply_map(map_key)
            self.state = "race"

    def _handle_editor_select_menu(self, event: pygame.event.Event) -> None:
        options = self._editor_map_options()
        if event.key == pygame.K_UP:
            self.editor_map_index = (self.editor_map_index - 1) % len(options)
        elif event.key == pygame.K_DOWN:
            self.editor_map_index = (self.editor_map_index + 1) % len(options)
        elif event.key in {pygame.K_RETURN, pygame.K_KP_ENTER}:
            _, map_key = options[self.editor_map_index]
            self._start_editor(map_key)

    def _handle_car_menu(self, event: pygame.event.Event) -> None:
        if self.role == "creator":
            self.state = "menu"
            return
        car_options = self._player_car_options()
        if event.key == pygame.K_UP:
            self.car_index = (self.car_index - 1) % len(car_options)
        elif event.key == pygame.K_DOWN:
            self.car_index = (self.car_index + 1) % len(car_options)
        elif event.key in {pygame.K_RETURN, pygame.K_KP_ENTER}:
            self.car_color = car_options[self.car_index][1]
            self.state = "menu"

    def _handle_editor_event(self, event: pygame.event.Event) -> None:
        if event.key == pygame.K_b:
            self._exit_editor()
            return
        if event.key == pygame.K_s:
            self._start_editor_test()
            return
        if event.key == pygame.K_UP:
            self._move_editor_cursor(0, -1)
        elif event.key == pygame.K_DOWN:
            self._move_editor_cursor(0, 1)
        elif event.key == pygame.K_LEFT:
            self._move_editor_cursor(-1, 0)
        elif event.key == pygame.K_RIGHT:
            self._move_editor_cursor(1, 0)
        elif event.key == pygame.K_r:
            self._rotate_editor_start()
        elif event.key == pygame.K_SPACE:
            self._paint_editor_tile()
        elif event.unicode in {"0", "1", "2", "3", "4", "5"}:
            self.editor_tile = event.unicode
            self.editor_status = None

    def _menu_items(self) -> list[str]:
        return [
            "Race",
            "Color",
            "Track editor",
            "About",
            "Exit",
        ]

    def _toggle_role(self) -> None:
        self.role = "creator" if self.role == "player" else "player"
        if self.role == "creator":
            self.car_color = (30, 30, 35)
        else:
            self.car_color = self.car_options[self.car_index][1]
        self.menu_items = self._menu_items()
        self.editor_map_index = 0

    def _reset_player_records(self) -> None:
        clear_all_best_times(self.db_path)
        clear_all_creator_beaten(self.db_path)
        replay_dir = Path("data/replays")
        if replay_dir.exists():
            for replay_path in replay_dir.glob("*_last.json"):
                replay_path.unlink()
        self.best_time_ms = None
        self.ghost_inputs = []
        self.ghost_index = 0
        self.ghost_car = None
        self.ghost_active = False
        self.creator_beaten = False
        if self.role != "creator":
            self.car_index = 0
            self.car_color = self.car_options[self.car_index][1]
        self.menu_flash_text = "Track records reset"
        self.menu_flash_until = pygame.time.get_ticks() + 1000

    def _menu_flash_message(self) -> str | None:
        if self.menu_flash_text is None:
            return None
        if pygame.time.get_ticks() >= self.menu_flash_until:
            self.menu_flash_text = None
            return None
        return self.menu_flash_text

    def _activate_cheater_mode(self) -> None:
        enable_cheat = False
        for _, track_id in self.map_options:
            if not load_creator_beaten(self.db_path, track_id):
                enable_cheat = True
                break
        for _, track_id in self.map_options:
            save_creator_beaten(self.db_path, track_id, enable_cheat)
        self.creator_beaten = enable_cheat
        if enable_cheat:
            self.menu_flash_text = "Cheater Mode Activated"
        else:
            self.menu_flash_text = "Cheater Mode Deactivated"
        self.menu_flash_until = pygame.time.get_ticks() + 1000

    def _editor_map_options(self) -> list[tuple[str, str]]:
        if self.role == "creator":
            return [
                ("Track 1", "track_01"),
                ("Track 2", "track_02"),
                ("Track 3", "track_03"),
                ("Custom", "custom"),
            ]
        return [("Custom", "custom")]

    def _start_editor(self, map_key: str) -> None:
        self.state = "editor"
        self.editor_map_key = map_key
        pygame.key.set_repeat(160, 50)
        self.editor_prev_map = self.map
        self.editor_prev_track_id = self.track_id
        self.editor_prev_best_time = self.best_time_ms
        self.editor_prev_replay_path = self.replay_path
        self.editor_prev_checkpoints = self.checkpoints
        self.editor_prev_ghost_enabled = self.ghost_enabled
        self.editor_prev_creator_ghost_enabled = self.creator_ghost_enabled
        try:
            editor_map = load_map(self._map_path(map_key))
            self.editor_tiles = [row[:] for row in editor_map.tiles]
            self.editor_cursor = editor_map.start
            self.editor_start_angle = editor_map.start_angle
        except ValueError:
            self.editor_tiles = self._default_editor_tiles()
            self.editor_cursor = (1, 1)
            self.editor_start_angle = 0.0
        self.editor_tile = "0"
        self.editor_status = None
        self.editor_pending_save = False

    def _exit_editor(self) -> None:
        if self.editor_prev_map is not None:
            self.map = self.editor_prev_map
        if self.editor_prev_track_id is not None:
            self.track_id = self.editor_prev_track_id
        if self.editor_prev_best_time is not None or self.editor_prev_best_time is None:
            self.best_time_ms = self.editor_prev_best_time
        if self.editor_prev_replay_path is not None:
            self.replay_path = self.editor_prev_replay_path
        if self.editor_prev_checkpoints is not None:
            self.checkpoints = self.editor_prev_checkpoints
        if self.editor_prev_ghost_enabled is not None:
            self.ghost_enabled = self.editor_prev_ghost_enabled
        if self.editor_prev_creator_ghost_enabled is not None:
            self.creator_ghost_enabled = self.editor_prev_creator_ghost_enabled
        pygame.key.set_repeat()
        self.state = "menu"
        self.editor_pending_save = False
        self.editor_status = None

    def _default_editor_tiles(self) -> list[list[str]]:
        width = 20
        height = 20
        tiles: list[list[str]] = []
        for y in range(height):
            row: list[str] = []
            for x in range(width):
                if x == 0 or y == 0 or x == width - 1 or y == height - 1:
                    row.append("1")
                else:
                    row.append("0")
            tiles.append(row)
        return tiles

    def _move_editor_cursor(self, dx: int, dy: int) -> None:
        if not self.editor_tiles:
            return
        height = len(self.editor_tiles)
        width = len(self.editor_tiles[0])
        x, y = self.editor_cursor
        x = max(0, min(width - 1, x + dx))
        y = max(0, min(height - 1, y + dy))
        self.editor_cursor = (x, y)

    def _paint_editor_tile(self) -> None:
        if not self.editor_tiles:
            return
        x, y = self.editor_cursor
        if self.editor_tile in {"3", "4"}:
            self._clear_tile(self.editor_tile)
        self.editor_tiles[y][x] = self.editor_tile
        self.editor_status = None

    def _rotate_editor_start(self) -> None:
        if not self.editor_tiles:
            return
        if self._find_tile(self.editor_tiles, "3") is None:
            self.editor_status = "Place start (3) before rotating"
            return
        self.editor_start_angle = (self.editor_start_angle + math.pi / 2) % math.tau
        self.editor_status = None

    def _start_editor_test(self) -> None:
        if not self._editor_has_required_tiles():
            self.editor_status = "Add start (3) and finish (4) before saving"
            return
        pygame.key.set_repeat()
        editor_map = self._build_editor_map()
        if editor_map is None:
            self.editor_status = "Invalid map layout"
            return
        self.editor_pending_save = True
        self.map = editor_map
        self.checkpoints = editor_map.checkpoints
        self.track_id = self.editor_map_key or "custom"
        self.replay_path = Path("data/replays") / f"{self.track_id}_last.json"
        self.best_time_ms = load_best_time(self.db_path, self.track_id)
        self.creator_replay_path = (
            Path("data/replays") / f"{self.track_id}_creator.json"
        )
        self.creator_time_ms = load_creator_time(self.db_path, self.track_id)
        self.creator_beaten = load_creator_beaten(self.db_path, self.track_id)
        if (
            not self.creator_beaten
            and self.best_time_ms is not None
            and self.creator_time_ms is not None
            and self.best_time_ms <= self.creator_time_ms
        ):
            self.creator_beaten = True
            save_creator_beaten(self.db_path, self.track_id, True)
        self.editor_prev_ghost_enabled = self.ghost_enabled
        self.ghost_enabled = False
        self.ghost_car = None
        self.ghost_active = False
        self.editor_prev_creator_ghost_enabled = self.creator_ghost_enabled
        self.creator_ghost_enabled = False
        self.creator_ghost_car = None
        self.creator_ghost_active = False
        self._reset_run()
        self._start_countdown()
        self.state = "editor_test"
        self.editor_status = "Drive to finish to save"

    def _complete_editor_test(self, elapsed_ms: int) -> None:
        if not self.editor_pending_save:
            return
        self._save_custom_map()
        save_creator_time(self.db_path, self.track_id, elapsed_ms)
        self.creator_time_ms = elapsed_ms
        clear_creator_beaten(self.db_path, self.track_id)
        self.creator_beaten = False
        self._save_creator_replay()
        self.editor_status = f"Saved. Creator: {self._format_time(elapsed_ms)}"
        self.run_active = False
        self.run_finished = True
        self.freeze_car = True
        self.car.speed = 0.0
        self.editor_pending_save = False
        if self.editor_prev_ghost_enabled is not None:
            self.ghost_enabled = self.editor_prev_ghost_enabled
        if self.editor_prev_creator_ghost_enabled is not None:
            self.creator_ghost_enabled = self.editor_prev_creator_ghost_enabled
        self.state = "editor"

    def _cancel_editor_test(self) -> None:
        self.run_active = False
        self.run_finished = False
        self.editor_pending_save = False
        if self.editor_prev_ghost_enabled is not None:
            self.ghost_enabled = self.editor_prev_ghost_enabled
        if self.editor_prev_creator_ghost_enabled is not None:
            self.creator_ghost_enabled = self.editor_prev_creator_ghost_enabled
        self.state = "editor"
        self.editor_status = "Test cancelled"

    def _start_countdown(self) -> None:
        self.countdown_active = True
        self.countdown_time = 3.0

    def _update_countdown(self, dt: float) -> None:
        if not self.countdown_active:
            return
        self.countdown_time = max(0.0, self.countdown_time - dt)
        if self.countdown_time <= 0.0:
            self.countdown_active = False
            self.go_flash_until = pygame.time.get_ticks() + 600
            if not self.run_active and not self.run_finished:
                self.run_active = True
                self.run_elapsed_ms = 0.0
                self.elapsed_ms = 0
                self.replay_inputs = []
                self.visited_checkpoints = set()
                self._start_ghost()

    def _countdown_display(self) -> float | None:
        if not self.countdown_active:
            return None
        return max(1.0, float(int(self.countdown_time + 0.9999)))

    def _should_show_go_flash(self) -> bool:
        return pygame.time.get_ticks() < self.go_flash_until

    def _build_editor_map(self) -> MapData | None:
        if not self.editor_tiles:
            return None
        height = len(self.editor_tiles)
        width = len(self.editor_tiles[0])
        for row in self.editor_tiles:
            if len(row) != width:
                return None
        start = self._find_tile(self.editor_tiles, "3")
        finish = self._find_tile(self.editor_tiles, "4")
        if start is None or finish is None:
            return None
        checkpoints = self._find_tiles(self.editor_tiles, "5")
        return MapData(
            width=width,
            height=height,
            tiles=self.editor_tiles,
            legend=self.map.legend,
            start=start,
            finish=finish,
            checkpoints=checkpoints,
            start_angle=self.editor_start_angle,
        )

    def _find_tile(
        self, tiles: list[list[str]], tile_id: str
    ) -> tuple[int, int] | None:
        for y, row in enumerate(tiles):
            for x, value in enumerate(row):
                if value == tile_id:
                    return (x, y)
        return None

    def _find_tiles(
        self, tiles: list[list[str]], tile_id: str
    ) -> list[tuple[int, int]]:
        results: list[tuple[int, int]] = []
        for y, row in enumerate(tiles):
            for x, value in enumerate(row):
                if value == tile_id:
                    results.append((x, y))
        return results

    def _clear_tile(self, tile_id: str) -> None:
        for y, row in enumerate(self.editor_tiles):
            for x, value in enumerate(row):
                if value == tile_id:
                    self.editor_tiles[y][x] = "0"

    def _save_custom_map(self) -> None:
        map_key = self.editor_map_key or "custom"
        payload = {
            "width": len(self.editor_tiles[0]) if self.editor_tiles else 0,
            "height": len(self.editor_tiles),
            "legend": {
                "0": "road",
                "1": "wall",
                "2": "mud",
                "3": "start",
                "4": "finish",
                "5": "checkpoint",
            },
            "tiles": self.editor_tiles,
            "start_angle": self.editor_start_angle,
        }
        map_path = self._map_path(map_key)
        map_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        clear_best_time(self.db_path, map_key)
        replay_path = Path("data/replays") / f"{map_key}_last.json"
        if replay_path.exists():
            replay_path.unlink()
        creator_replay_path = Path("data/replays") / f"{map_key}_creator.json"
        if creator_replay_path.exists():
            creator_replay_path.unlink()
        clear_creator_beaten(self.db_path, map_key)
        if self.track_id == map_key:
            self.best_time_ms = None
            self.ghost_inputs = []
            self.ghost_index = 0
            self.ghost_car = None
            self.ghost_active = False
            self.creator_ghost_enabled = False
            self.creator_ghost_inputs = []
            self.creator_ghost_index = 0
            self.creator_ghost_car = None
            self.creator_ghost_active = False
            self.creator_beaten = False
        self.editor_status = "Map saved"

    def _editor_has_required_tiles(self) -> bool:
        has_start = any("3" in row for row in self.editor_tiles)
        has_finish = any("4" in row for row in self.editor_tiles)
        return has_start and has_finish

    def _render_menu_state(self) -> None:
        if self.state == "menu":
            render_menu(
                self.screen,
                "Vibe Racer",
                self._menu_items(),
                self.menu_index,
                subtitle=self._menu_flash_message(),
                footer_lines=["CREATOR MODE"] if self.role == "creator" else None,
                footer_color=(230, 200, 90),
                hint_text="Up/Down=move, Enter=select, Q=quit",
            )
            return
        if self.state == "map_select":
            items, highlight_indices, show_footer = self._map_menu_display()
            render_menu(
                self.screen,
                "Select Track",
                items,
                self.map_index,
                subtitle=self._map_total_time_label(),
                highlight_indices=highlight_indices,
                footer_lines=self._map_menu_footer() if show_footer else None,
                footer_color=(230, 200, 90),
                extra_spacing_after=self._map_menu_spacing_after(),
                hint_text="Up/Down=move, Enter=select, B=back, Q=quit",
            )
            return
        if self.state == "editor_select":
            render_menu(
                self.screen,
                "Select Track to Edit",
                [name for name, _ in self._editor_map_options()],
                self.editor_map_index,
                hint_text="Up/Down=move, Enter=select, B=back, Q=quit",
            )
            return
        if self.state == "car_select":
            car_options = self._player_car_options()
            if self.car_index >= len(car_options):
                self.car_index = 0
            render_color_menu(
                self.screen,
                "Select Color",
                [name for name, _ in car_options],
                self.car_index,
                car_options[self.car_index][1],
                hint_text="Up/Down=move, Enter=select, B=back, Q=quit",
            )
            return
        if self.state == "editor":
            render_editor(
                self.screen,
                self.editor_tiles,
                self.map.legend,
                self.editor_cursor,
                self.editor_tile,
                self.editor_status,
                self.editor_start_angle,
            )
            return
        if self.state == "about":
            render_message(
                self.screen,
                "About",
                [
                    "Vibe Racer is made with Pygame.",
                    "Created by Timon + OpenCode.",
                    "Made with GPT-5.2 Codex from OpenAI.",
                ],
                hint_text="Up/Down=move, Enter=select, B=back, Q=quit",
                car_colors=[
                    self.car_options[0][1],
                    self.car_options[1][1],
                    self.car_options[2][1],
                    self.car_options[3][1],
                    (30, 30, 35),
                ],
            )

    def _map_menu_items(self) -> list[str]:
        items: list[str] = []
        for name, track_id in self.map_options:
            best_time = load_best_time(self.db_path, track_id)
            label = f"{name}  Best: {self._format_time(best_time)}"
            items.append(label)
        return items

    def _map_menu_display(self) -> tuple[list[str], set[int], bool]:
        items: list[str] = []
        highlight_indices: set[int] = set()
        all_beaten = True
        for index, (name, track_id) in enumerate(self.map_options):
            best_time = load_best_time(self.db_path, track_id)
            creator_time = load_creator_time(self.db_path, track_id)
            creator_beaten = load_creator_beaten(self.db_path, track_id)
            label = f"{name}  Best: {self._format_time(best_time)}"
            items.append(label)
            beaten = creator_beaten or (
                best_time is not None
                and creator_time is not None
                and best_time <= creator_time
            )
            if beaten and track_id != "custom":
                highlight_indices.add(index)
            if track_id != "custom" and not beaten:
                all_beaten = False
        return items, highlight_indices, all_beaten

    def _map_menu_footer(self) -> list[str]:
        return ["VIBE RACER", "ALL CREATOR TIMES", "BEATEN"]

    def _map_menu_spacing_after(self) -> set[int]:
        if len(self.map_options) >= 4:
            return {2}
        return set()

    def _all_creator_times_beaten(self) -> bool:
        for _, track_id in self.map_options:
            if track_id == "custom":
                continue
            creator_beaten = load_creator_beaten(self.db_path, track_id)
            if creator_beaten:
                continue
            best_time = load_best_time(self.db_path, track_id)
            creator_time = load_creator_time(self.db_path, track_id)
            if best_time is None or creator_time is None:
                return False
            if best_time > creator_time:
                return False
        return True

    def _player_car_options(self) -> list[tuple[str, tuple[int, int, int]]]:
        options = self.car_options[:]
        if self._all_creator_times_beaten():
            options.append(("Black", (30, 30, 35)))
        return options

    def _map_total_time_label(self) -> str | None:
        totals: list[int] = []
        for _, track_id in self.map_options:
            if track_id == "custom":
                continue
            best_time = load_best_time(self.db_path, track_id)
            if best_time is None:
                return "Total: -- (complete all tracks)"
            totals.append(best_time)
        total_ms = sum(totals)
        return f"Total: {self._format_time(total_ms)}"

    def _format_time(self, elapsed_ms: int | None) -> str:
        if elapsed_ms is None:
            return "--"
        return f"{elapsed_ms / 1000.0:0.3f}s"
