import math

from .car import Car
from .input import InputState


def update_car(
    car: Car,
    inputs: InputState,
    dt: float,
    accel_multiplier: float = 1.0,
    max_speed_multiplier: float = 1.0,
    turn_multiplier: float = 1.0,
) -> None:
    max_speed = car.max_speed * max_speed_multiplier
    acceleration = car.acceleration * accel_multiplier

    if inputs.accelerate:
        car.speed = min(max_speed, car.speed + acceleration * dt)
    elif inputs.brake:
        car.speed = max(0.0, car.speed - acceleration * dt)
    else:
        car.speed = max(0.0, car.speed - acceleration * 0.4 * dt)

    if inputs.turn_left:
        car.angle -= car.turn_rate * turn_multiplier * dt
    if inputs.turn_right:
        car.angle += car.turn_rate * turn_multiplier * dt

    car.x += math.cos(car.angle) * car.speed * dt
    car.y += math.sin(car.angle) * car.speed * dt
