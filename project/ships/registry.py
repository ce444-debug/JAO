# project/ships/registry.py
from project.ships.ship_a import ShipA
from project.ships.ship_b import ShipB
from project.ships.ship_terminator import ShipTerminator

SHIP_CLASSES = {
    "Earthling Cruiser": ShipA,
    "KOHR-AH MARAUDER": ShipB,
    "YEHAT TERMINATOR": ShipTerminator,
}
