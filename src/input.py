from dataclasses import dataclass

import pygame


@dataclass
class InputState:
    accelerate: bool = False
    brake: bool = False
    turn_left: bool = False
    turn_right: bool = False

    def to_dict(self) -> dict[str, bool]:
        return {
            "accelerate": self.accelerate,
            "brake": self.brake,
            "turn_left": self.turn_left,
            "turn_right": self.turn_right,
        }

    @staticmethod
    def from_dict(values: dict[str, bool]) -> "InputState":
        return InputState(
            accelerate=values.get("accelerate", False),
            brake=values.get("brake", False),
            turn_left=values.get("turn_left", False),
            turn_right=values.get("turn_right", False),
        )


def read_input() -> InputState:
    keys = pygame.key.get_pressed()
    return InputState(
        accelerate=keys[pygame.K_UP] or keys[pygame.K_w],
        brake=keys[pygame.K_DOWN] or keys[pygame.K_s],
        turn_left=keys[pygame.K_LEFT] or keys[pygame.K_a],
        turn_right=keys[pygame.K_RIGHT] or keys[pygame.K_d],
    )
