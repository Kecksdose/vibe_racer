from enum import Enum


class TileType(str, Enum):
    ROAD = "road"
    WALL = "wall"
    MUD = "mud"
    START = "start"
    FINISH = "finish"
    CHECKPOINT = "checkpoint"
