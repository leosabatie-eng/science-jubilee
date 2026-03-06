from optparse import Option
import os
import json
from typing import Optional
from science_jubilee.labware.Labware import Labware
from science_jubilee.utils.exceptions import ToolConfigurationError
from science_jubilee.JubileeManager import JubileeManager
from science_jubilee.tools.Tool import Tool


def load_all(jm: JubileeManager, deck_filename: str, path: Optional[str] = None) -> None:
    """       
    Load all tools defined in a deck JSON file and register them
    using the existing load_tool() method.

    The JSON file must define a 'tool_slots' dictionary:
    {
        "tool_slots": {
            "1": "Pipette",
            "2": "wash_station"
        }
    }
    """

    # Resolve path
    if path is None:
        path = os.path.join(os.path.dirname(__file__), "deck_definition")

    if not deck_filename.endswith(".json"):
        deck_filename += ".json"

    config_path = os.path.join(path, deck_filename)

    if not os.path.exists(config_path):
        raise ToolConfigurationError(f"Deck file not found: {config_path}")

    # Load JSON
    with open(config_path, "r") as f:
        deck_config = json.load(f)

    slots_cfg = deck_config.get("tool_slots")
    if not isinstance(slots_cfg, dict):
        raise ToolConfigurationError(
            "'tool_slots' must be defined as a dictionary in deck JSON"
        )

    # Load each tool using the existing load_tool() method
    for slot_index_str, tool_name in slots_cfg.items():
        try:
            index = int(slot_index_str)
        except ValueError:
            raise ToolConfigurationError(
                f"Invalid tool index '{slot_index_str}' (must be an integer)"
            )

        tool = Tool(index=index, name=tool_name)
        jm.load_tool(tool, index)
        offset
        jm.set_tool_offset(0, (0, -43.5,0))

    slots_cfg = deck_config.get("slots")
    if not isinstance(slots_cfg, dict):
        raise ToolConfigurationError(
            "'slots' must be defined as a dictionary in deck JSON"
        )
    
    for slot_index_str, slot_data in slots_cfg.items():
        try:
            index = int(slot_index_str)
        except ValueError:
            raise ToolConfigurationError(
                f"Invalid slot index '{slot_index_str}' (must be an integer)"
            )

        # Vérifie si labware présent
        if not slot_data.get("has_labware", False):
            continue

        labware_name = slot_data.get("labware")
        if not labware_name:
            raise ToolConfigurationError(
                f"No labware filename defined for slot {slot_index_str}"
            )

        # Chargement du labware via le deck
        labware = Labware(labware_name, order="rows")
        slot_obj = jm.deck.get_slot(slot_index_str)
        slot_obj.labware = labware

    
