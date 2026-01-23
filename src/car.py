from dataclasses import dataclass


@dataclass
class Car:
    x: float = 0.0
    y: float = 0.0
    angle: float = 0.0
    speed: float = 0.0
    max_speed: float = 420.0
    acceleration: float = 420.0
    turn_rate: float = 3.2
    mud_timer: float = 0.0
