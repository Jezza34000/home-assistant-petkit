"""Binary Sensor platform for PetKit integration."""

from __future__ import annotations

from typing import Any

from petkit_api.model import Feeder, LitterBox, Fountain

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, FEEDERS, LITTER_BOXES, PETKIT_COORDINATOR, WATER_FOUNTAINS
from .coordinator import PetKitDataUpdateCoordinator


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set Up PetKit Binary Sensor Entities."""

    coordinator: PetKitDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id][
        PETKIT_COORDINATOR
    ]

    binary_sensors = []

    for wf_id, wf_data in coordinator.data.water_fountains.items():
        # Water Fountains (W5)
        binary_sensors.append(WFWater(coordinator, wf_id))
        if wf_data.type == "ctw3":
            binary_sensors.extend(
                (WFElectricStatus(coordinator, wf_id), WFPumpStatus(coordinator, wf_id))
            )

    for feeder_id, feeder_data in coordinator.data.feeders.items():

        # All feeders except D4s
        if feeder_data.type not in ["d4s", "d4sh"]:
            binary_sensors.append(FoodLevel(coordinator, feeder_id))

        # D4 and D4s feeders
        if feeder_data.type in ["d4", "d4s", "d4sh"]:
            binary_sensors.append(BatteryInstalled(coordinator, feeder_id))

        # D4s Feeder
        if feeder_data.type in ["d4s", "d4sh"]:
            binary_sensors.extend(
                (
                    FoodLevelHopper1(coordinator, feeder_id),
                    FoodLevelHopper2(coordinator, feeder_id),
                )
            )

        # D4sh Feeder
        if feeder_data.type == "d4sh":
            binary_sensors.extend(
                (
                    CameraStatus(coordinator, feeder_id),
                    Eating(coordinator, feeder_id),
                    Feeding(coordinator, feeder_id),
                    CarePlusSubscription(coordinator, feeder_id),
                )
            )

        # D3 Feeder
        if feeder_data.type == "d3":
            binary_sensors.append(BatteryCharging(coordinator, feeder_id))

    # Litter boxes
    for lb_id, lb_data in coordinator.data.litter_boxes.items():
        # Pura X & Pura MAX
        if lb_data.type in ["t3", "t4", "t6"]:
            binary_sensors.extend(
                (
                    LBBinFull(coordinator, lb_id),
                    LBLitterLack(coordinator, lb_id),
                )
            )
        # Pura X & Pura MAX with Pura Air
        if (lb_data.type == "t3") or ("k3Device" in lb_data.device_detail):
            binary_sensors.append(LBDeodorizerLack(coordinator, lb_id))
        # Pura X
        if lb_data.type == "t3":
            binary_sensors.append(LBManuallyPaused(coordinator, lb_id))

        # Pura MAX2 and Purobot ULTRA
        if "boxState" in lb_data.device_detail["state"]:
            binary_sensors.append(LBBWastePresence(coordinator, lb_id))

    async_add_entities(binary_sensors)


class WFWater(CoordinatorEntity, BinarySensorEntity):
    """Representation of Water Fountain lack of water warning."""

    def __init__(self, coordinator, wf_id):
        super().__init__(coordinator)
        self.wf_id = wf_id

    @property
    def wf_data(self) -> Fountain:
        """Handle coordinator Water Fountain data"""

        return self.coordinator.data.water_fountains[self.wf_id]

    @property
    def device_info(self) -> dict[str, Any]:
        """Return device registry information for this entity."""

        return {
            "identifiers": {(DOMAIN, self.wf_data.id)},
            "name": self.wf_data.data["name"],
            "manufacturer": "PetKit",
            "model": (
                WATER_FOUNTAINS.get(
                    self.wf_data.data["typeCode"], "Unidentified Water Fountain"
                )
                if "typeCode" in self.wf_data.data
                else "Unidentified Water Fountain"
            ),
            "sw_version": f'{self.wf_data.data["hardware"]}.{self.wf_data.data["firmware"]}',
        }

    @property
    def unique_id(self) -> str:
        """Sets unique ID for this entity."""

        return str(self.wf_data.id) + "_water_level"

    @property
    def has_entity_name(self) -> bool:
        """Indicate that entity has name defined."""

        return True

    @property
    def translation_key(self) -> str:
        """Translation key for this entity."""

        return "water_level"

    @property
    def device_class(self) -> BinarySensorDeviceClass:
        """Return entity device class."""

        return BinarySensorDeviceClass.PROBLEM

    @property
    def is_on(self) -> bool:
        """Return True if water needs to be added."""

        if self.wf_data.data["lackWarning"] == 1:
            return True
        else:
            return False

    @property
    def icon(self) -> str:
        """Set icon."""

        if self.wf_data.data["lackWarning"] == 1:
            return "mdi:water-alert"
        else:
            return "mdi:water"


class FoodLevel(CoordinatorEntity, BinarySensorEntity):
    """Representation of Feeder lack of food warning."""

    def __init__(self, coordinator, feeder_id):
        super().__init__(coordinator)
        self.feeder_id = feeder_id

    @property
    def feeder_data(self) -> Feeder:
        """Handle coordinator Feeder data."""

        return self.coordinator.data.feeders[self.feeder_id]

    @property
    def device_info(self) -> dict[str, Any]:
        """Return device registry information for this entity."""

        return {
            "identifiers": {(DOMAIN, self.feeder_data.id)},
            "name": self.feeder_data.data["name"],
            "manufacturer": "PetKit",
            "model": FEEDERS[self.feeder_data.type],
            "sw_version": f'{self.feeder_data.data["firmware"]}',
        }

    @property
    def unique_id(self) -> str:
        """Sets unique ID for this entity."""

        return str(self.feeder_data.id) + "_food_level"

    @property
    def has_entity_name(self) -> bool:
        """Indicate that entity has name defined."""

        return True

    @property
    def translation_key(self) -> str:
        """Translation key for this entity."""

        return "food_level"

    @property
    def device_class(self) -> BinarySensorDeviceClass:
        """Return entity device class."""

        return BinarySensorDeviceClass.PROBLEM

    @property
    def is_on(self) -> bool:
        """Return True if food needs to be added."""

        if self.feeder_data.type == "d3":
            if self.feeder_data.data["state"]["food"] < 2:
                return True
            else:
                return False

        if self.feeder_data.type != "d3":
            # The food key for the Fresh Element represents grams left
            if self.feeder_data.data["state"]["food"] == 0:
                return True
            else:
                return False

    @property
    def icon(self) -> str:
        """Set icon."""

        if self.feeder_data.type == "d3":
            if self.feeder_data.data["state"]["food"] < 2:
                return "mdi:food-drumstick-off"
            else:
                return "mdi:food-drumstick"

        if self.feeder_data.type != "d3":
            if self.feeder_data.data["state"]["food"] == 0:
                return "mdi:food-drumstick-off"
            else:
                return "mdi:food-drumstick"


class BatteryInstalled(CoordinatorEntity, BinarySensorEntity):
    """Representation of if Feeder has batteries installed."""

    def __init__(self, coordinator, feeder_id):
        super().__init__(coordinator)
        self.feeder_id = feeder_id

    @property
    def feeder_data(self) -> Feeder:
        """Handle coordinator Feeder data."""

        return self.coordinator.data.feeders[self.feeder_id]

    @property
    def device_info(self) -> dict[str, Any]:
        """Return device registry information for this entity."""

        return {
            "identifiers": {(DOMAIN, self.feeder_data.id)},
            "name": self.feeder_data.data["name"],
            "manufacturer": "PetKit",
            "model": FEEDERS[self.feeder_data.type],
            "sw_version": f'{self.feeder_data.data["firmware"]}',
        }

    @property
    def unique_id(self) -> str:
        """Sets unique ID for this entity."""

        return str(self.feeder_data.id) + "_battery_installed"

    @property
    def has_entity_name(self) -> bool:
        """Indicate that entity has name defined."""

        return True

    @property
    def translation_key(self) -> str:
        """Translation key for this entity."""

        return "battery_installed"

    @property
    def entity_category(self) -> EntityCategory:
        """Set category to diagnostic."""

        return EntityCategory.DIAGNOSTIC

    @property
    def is_on(self) -> bool:
        """Return True if battery installed."""

        if self.feeder_data.data["state"]["batteryPower"] == 1:
            return True
        else:
            return False

    @property
    def icon(self) -> str:
        """Set icon."""

        return "mdi:battery"


class BatteryCharging(CoordinatorEntity, BinarySensorEntity):
    """Representation of if Feeder battery is charging."""

    def __init__(self, coordinator, feeder_id):
        super().__init__(coordinator)
        self.feeder_id = feeder_id

    @property
    def feeder_data(self) -> Feeder:
        """Handle coordinator Feeder data."""

        return self.coordinator.data.feeders[self.feeder_id]

    @property
    def device_info(self) -> dict[str, Any]:
        """Return device registry information for this entity."""

        return {
            "identifiers": {(DOMAIN, self.feeder_data.id)},
            "name": self.feeder_data.data["name"],
            "manufacturer": "PetKit",
            "model": FEEDERS[self.feeder_data.type],
            "sw_version": f'{self.feeder_data.data["firmware"]}',
        }

    @property
    def unique_id(self) -> str:
        """Sets unique ID for this entity."""

        return str(self.feeder_data.id) + "_battery_charging"

    @property
    def has_entity_name(self) -> bool:
        """Indicate that entity has name defined."""

        return True

    @property
    def translation_key(self) -> str:
        """Translation key for this entity."""

        return "battery"

    @property
    def entity_category(self) -> EntityCategory:
        """Set category to diagnostic."""

        return EntityCategory.DIAGNOSTIC

    @property
    def device_class(self) -> BinarySensorDeviceClass:
        """Return entity device class."""

        return BinarySensorDeviceClass.BATTERY_CHARGING

    @property
    def is_on(self) -> bool:
        """Return True if battery is charging."""

        if self.feeder_data.data["state"]["charge"] > 1:
            return True
        else:
            return False

    @property
    def icon(self) -> str:
        """Set icon."""

        return "mdi:battery"


class LBBinFull(CoordinatorEntity, BinarySensorEntity):
    """Representation of litter box wastebin full or not."""

    def __init__(self, coordinator, lb_id):
        super().__init__(coordinator)
        self.lb_id = lb_id

    @property
    def lb_data(self) -> LitterBox:
        """Handle coordinator litter box data."""

        return self.coordinator.data.litter_boxes[self.lb_id]

    @property
    def device_info(self) -> dict[str, Any]:
        """Return device registry information for this entity."""

        return {
            "identifiers": {(DOMAIN, self.lb_data.id)},
            "name": self.lb_data.device_detail["name"],
            "manufacturer": "PetKit",
            "model": LITTER_BOXES[self.lb_data.type],
            "sw_version": f'{self.lb_data.device_detail["firmware"]}',
        }

    @property
    def unique_id(self) -> str:
        """Sets unique ID for this entity."""

        return str(self.lb_data.id) + "_wastebin"

    @property
    def has_entity_name(self) -> bool:
        """Indicate that entity has name defined."""

        return True

    @property
    def translation_key(self) -> str:
        """Translation key for this entity."""

        return "wastebin"

    @property
    def icon(self) -> str:
        """Set icon."""

        return "mdi:delete"

    @property
    def device_class(self) -> BinarySensorDeviceClass:
        """Return entity device class."""

        return BinarySensorDeviceClass.PROBLEM

    @property
    def is_on(self) -> bool:
        """Return True if wastebin is full."""

        return self.lb_data.device_detail["state"]["boxFull"]


class LBLitterLack(CoordinatorEntity, BinarySensorEntity):
    """Representation of litter box lacking sand."""

    def __init__(self, coordinator, lb_id):
        super().__init__(coordinator)
        self.lb_id = lb_id

    @property
    def lb_data(self) -> LitterBox:
        """Handle coordinator litter box data."""

        return self.coordinator.data.litter_boxes[self.lb_id]

    @property
    def device_info(self) -> dict[str, Any]:
        """Return device registry information for this entity."""

        return {
            "identifiers": {(DOMAIN, self.lb_data.id)},
            "name": self.lb_data.device_detail["name"],
            "manufacturer": "PetKit",
            "model": LITTER_BOXES[self.lb_data.type],
            "sw_version": f'{self.lb_data.device_detail["firmware"]}',
        }

    @property
    def unique_id(self) -> str:
        """Sets unique ID for this entity."""

        return str(self.lb_data.id) + "_litter_lack"

    @property
    def has_entity_name(self) -> bool:
        """Indicate that entity has name defined."""

        return True

    @property
    def translation_key(self) -> str:
        """Translation key for this entity."""

        return "litter"

    @property
    def icon(self) -> str:
        """Set icon."""

        return "mdi:landslide"

    @property
    def device_class(self) -> BinarySensorDeviceClass:
        """Return entity device class."""

        return BinarySensorDeviceClass.PROBLEM

    @property
    def is_on(self) -> bool:
        """Return True if litter is empty."""

        return self.lb_data.device_detail["state"]["sandLack"]


class LBDeodorizerLack(CoordinatorEntity, BinarySensorEntity):
    """Representation of litter box lacking deodorizer."""

    def __init__(self, coordinator, lb_id):
        super().__init__(coordinator)
        self.lb_id = lb_id

    @property
    def lb_data(self) -> LitterBox:
        """Handle coordinator litter box data."""

        return self.coordinator.data.litter_boxes[self.lb_id]

    @property
    def device_info(self) -> dict[str, Any]:
        """Return device registry information for this entity."""

        return {
            "identifiers": {(DOMAIN, self.lb_data.id)},
            "name": self.lb_data.device_detail["name"],
            "manufacturer": "PetKit",
            "model": LITTER_BOXES[self.lb_data.type],
            "sw_version": f'{self.lb_data.device_detail["firmware"]}',
        }

    @property
    def unique_id(self) -> str:
        """Sets unique ID for this entity."""

        return str(self.lb_data.id) + "_deodorizer_lack"

    @property
    def has_entity_name(self) -> bool:
        """Indicate that entity has name defined."""

        return True

    @property
    def translation_key(self) -> str:
        """Translation key for this entity."""

        # Pura Air
        if "k3Device" in self.lb_data.device_detail:
            return "pura_air_liquid"
        # Pura X
        else:
            return "deodorizer"

    @property
    def icon(self) -> str:
        """Set icon."""

        # Pura Air
        if "k3Device" in self.lb_data.device_detail:
            return "mdi:cup"
        # Pura X
        else:
            return "mdi:spray"

    @property
    def device_class(self) -> BinarySensorDeviceClass:
        """Return entity device class."""

        return BinarySensorDeviceClass.PROBLEM

    @property
    def is_on(self) -> bool:
        """Return True if deodorizer is empty."""

        return self.lb_data.device_detail["state"]["liquidLack"]

    @property
    def available(self) -> bool:
        """Determine if entity is available.

        Return true if there is a Pura Air
        device associated or this is a Pura X.
        """

        if self.lb_data.type == "t4":
            if "k3Device" in self.lb_data.device_detail:
                return True
            else:
                return False
        else:
            return True


class LBManuallyPaused(CoordinatorEntity, BinarySensorEntity):
    """Representation of if litter box is manually paused by user."""

    def __init__(self, coordinator, lb_id):
        super().__init__(coordinator)
        self.lb_id = lb_id

    @property
    def lb_data(self) -> LitterBox:
        """Handle coordinator litter box data."""

        return self.coordinator.data.litter_boxes[self.lb_id]

    @property
    def device_info(self) -> dict[str, Any]:
        """Return device registry information for this entity."""

        return {
            "identifiers": {(DOMAIN, self.lb_data.id)},
            "name": self.lb_data.device_detail["name"],
            "manufacturer": "PetKit",
            "model": LITTER_BOXES[self.lb_data.type],
            "sw_version": f'{self.lb_data.device_detail["firmware"]}',
        }

    @property
    def unique_id(self) -> str:
        """Sets unique ID for this entity."""

        return str(self.lb_data.id) + "_manually_paused"

    @property
    def has_entity_name(self) -> bool:
        """Indicate that entity has name defined."""

        return True

    @property
    def translation_key(self) -> str:
        """Translation key for this entity."""

        return "manually_paused"

    @property
    def icon(self) -> str:
        """Set icon."""

        return "mdi:pause"

    @property
    def entity_category(self) -> EntityCategory:
        """Set category to diagnostic."""

        return EntityCategory.DIAGNOSTIC

    @property
    def is_on(self) -> bool:
        """Return True if deodorizer is empty."""

        return self.lb_data.manually_paused


class FoodLevelHopper1(CoordinatorEntity, BinarySensorEntity):
    """Representation of Feeder lack of food warning for Hopper 1."""

    def __init__(self, coordinator, feeder_id):
        super().__init__(coordinator)
        self.feeder_id = feeder_id

    @property
    def feeder_data(self) -> Feeder:
        """Handle coordinator Feeder data."""

        return self.coordinator.data.feeders[self.feeder_id]

    @property
    def device_info(self) -> dict[str, Any]:
        """Return device registry information for this entity."""

        return {
            "identifiers": {(DOMAIN, self.feeder_data.id)},
            "name": self.feeder_data.data["name"],
            "manufacturer": "PetKit",
            "model": FEEDERS[self.feeder_data.type],
            "sw_version": f'{self.feeder_data.data["firmware"]}',
        }

    @property
    def unique_id(self) -> str:
        """Sets unique ID for this entity."""

        return str(self.feeder_data.id) + "_food_level_hopper_1"

    @property
    def has_entity_name(self) -> bool:
        """Indicate that entity has name defined."""

        return True

    @property
    def translation_key(self) -> str:
        """Translation key for this entity."""

        return "food_level_hopper_one"

    @property
    def device_class(self) -> BinarySensorDeviceClass:
        """Return entity device class."""

        return BinarySensorDeviceClass.PROBLEM

    @property
    def is_on(self) -> bool:
        """Return True if food needs to be added."""

        if self.feeder_data.data["state"]["food1"] < 1:
            return True
        else:
            return False

    @property
    def icon(self) -> str:
        """Set icon."""

        if self.feeder_data.data["state"]["food1"] == 0:
            return "mdi:food-drumstick-off"
        else:
            return "mdi:food-drumstick"


class FoodLevelHopper2(CoordinatorEntity, BinarySensorEntity):
    """Representation of Feeder lack of food warning for Hopper 2."""

    def __init__(self, coordinator, feeder_id):
        super().__init__(coordinator)
        self.feeder_id = feeder_id

    @property
    def feeder_data(self) -> Feeder:
        """Handle coordinator Feeder data."""

        return self.coordinator.data.feeders[self.feeder_id]

    @property
    def device_info(self) -> dict[str, Any]:
        """Return device registry information for this entity."""

        return {
            "identifiers": {(DOMAIN, self.feeder_data.id)},
            "name": self.feeder_data.data["name"],
            "manufacturer": "PetKit",
            "model": FEEDERS[self.feeder_data.type],
            "sw_version": f'{self.feeder_data.data["firmware"]}',
        }

    @property
    def unique_id(self) -> str:
        """Sets unique ID for this entity."""

        return str(self.feeder_data.id) + "_food_level_hopper_2"

    @property
    def has_entity_name(self) -> bool:
        """Indicate that entity has name defined."""

        return True

    @property
    def translation_key(self) -> str:
        """Translation key for this entity."""

        return "food_level_hopper_two"

    @property
    def device_class(self) -> BinarySensorDeviceClass:
        """Return entity device class."""

        return BinarySensorDeviceClass.PROBLEM

    @property
    def is_on(self) -> bool:
        """Return True if food needs to be added."""

        if self.feeder_data.data["state"]["food2"] < 1:
            return True
        else:
            return False

    @property
    def icon(self) -> str:
        """Set icon."""

        if self.feeder_data.data["state"]["food2"] == 0:
            return "mdi:food-drumstick-off"
        else:
            return "mdi:food-drumstick"


class CameraStatus(CoordinatorEntity, BinarySensorEntity):
    """Representation of if Feeder has Camera turned ON/OFF"""

    def __init__(self, coordinator, feeder_id):
        super().__init__(coordinator)
        self.feeder_id = feeder_id

    @property
    def feeder_data(self) -> Feeder:
        """Handle coordinator Feeder data."""

        return self.coordinator.data.feeders[self.feeder_id]

    @property
    def device_info(self) -> dict[str, Any]:
        """Return device registry information for this entity."""

        return {
            "identifiers": {(DOMAIN, self.feeder_data.id)},
            "name": self.feeder_data.data["name"],
            "manufacturer": "PetKit",
            "model": FEEDERS[self.feeder_data.type],
            "sw_version": f'{self.feeder_data.data["firmware"]}',
        }

    @property
    def unique_id(self) -> str:
        """Sets unique ID for this entity."""

        return str(self.feeder_data.id) + "_camera_status"

    @property
    def has_entity_name(self) -> bool:
        """Indicate that entity has name defined."""

        return True

    @property
    def translation_key(self) -> str:
        """Translation key for this entity."""

        return "camera_status"

    @property
    def entity_category(self) -> EntityCategory:
        """Set category to diagnostic."""

        return EntityCategory.DIAGNOSTIC

    @property
    def is_on(self) -> bool:
        """Return True if battery installed."""

        if self.feeder_data.data["state"]["cameraStatus"] == 1:
            return True
        else:
            return False

    @property
    def icon(self) -> str:
        """Set icon."""

        if self.feeder_data.data["state"]["cameraStatus"] == 1:
            return "mdi:cctv"
        else:
            return "mdi:cctv-off"


class Eating(CoordinatorEntity, BinarySensorEntity):
    """Representation of feeder ????"""

    def __init__(self, coordinator, feeder_id):
        super().__init__(coordinator)
        self.feeder_id = feeder_id

    @property
    def feeder_data(self) -> Feeder:
        """Handle coordinator Feeder data."""

        return self.coordinator.data.feeders[self.feeder_id]

    @property
    def device_info(self) -> dict[str, Any]:
        """Return device registry information for this entity."""

        return {
            "identifiers": {(DOMAIN, self.feeder_data.id)},
            "name": self.feeder_data.data["name"],
            "manufacturer": "PetKit",
            "model": FEEDERS[self.feeder_data.type],
            "sw_version": f'{self.feeder_data.data["firmware"]}',
        }

    @property
    def unique_id(self) -> str:
        """Sets unique ID for this entity."""

        return str(self.feeder_data.id) + "_eating"

    @property
    def has_entity_name(self) -> bool:
        """Indicate that entity has name defined."""

        return True

    @property
    def translation_key(self) -> str:
        """Translation key for this entity."""

        return "eating"

    @property
    def device_class(self) -> BinarySensorDeviceClass:
        """Return the type of state class."""

        return BinarySensorDeviceClass.OCCUPANCY

    @property
    def is_on(self) -> bool:
        """Return True if food needs to be added."""

        if self.feeder_data.data["state"]["eating"] == 1:
            return True
        else:
            return False

    @property
    def icon(self) -> str:
        """Set icon."""

        return "mdi:silverware-fork-knife"


class Feeding(CoordinatorEntity, BinarySensorEntity):
    """Representation of feeder ????"""

    def __init__(self, coordinator, feeder_id):
        super().__init__(coordinator)
        self.feeder_id = feeder_id

    @property
    def feeder_data(self) -> Feeder:
        """Handle coordinator Feeder data."""

        return self.coordinator.data.feeders[self.feeder_id]

    @property
    def device_info(self) -> dict[str, Any]:
        """Return device registry information for this entity."""

        return {
            "identifiers": {(DOMAIN, self.feeder_data.id)},
            "name": self.feeder_data.data["name"],
            "manufacturer": "PetKit",
            "model": FEEDERS[self.feeder_data.type],
            "sw_version": f'{self.feeder_data.data["firmware"]}',
        }

    @property
    def unique_id(self) -> str:
        """Sets unique ID for this entity."""

        return str(self.feeder_data.id) + "_feeding"

    @property
    def has_entity_name(self) -> bool:
        """Indicate that entity has name defined."""

        return True

    @property
    def translation_key(self) -> str:
        """Translation key for this entity."""

        return "feeding"

    @property
    def device_class(self) -> BinarySensorDeviceClass:
        """Return the type of state class."""

        return BinarySensorDeviceClass.OCCUPANCY

    @property
    def is_on(self) -> bool:
        """Return True if food needs to be added."""

        if self.feeder_data.data["state"]["feeding"] == 1:
            return True
        else:
            return False

    @property
    def icon(self) -> str:
        """Set icon."""

        return "mdi:shaker-outline"


class LBBWastePresence(CoordinatorEntity, BinarySensorEntity):
    """Representation of litter box wastebin present or not."""

    def __init__(self, coordinator, lb_id):
        super().__init__(coordinator)
        self.lb_id = lb_id

    @property
    def lb_data(self) -> LitterBox:
        """Handle coordinator litter box data."""

        return self.coordinator.data.litter_boxes[self.lb_id]

    @property
    def device_info(self) -> dict[str, Any]:
        """Return device registry information for this entity."""

        return {
            "identifiers": {(DOMAIN, self.lb_data.id)},
            "name": self.lb_data.device_detail["name"],
            "manufacturer": "PetKit",
            "model": LITTER_BOXES[self.lb_data.type],
            "sw_version": f'{self.lb_data.device_detail["firmware"]}',
        }

    @property
    def unique_id(self) -> str:
        """Sets unique ID for this entity."""

        return str(self.lb_data.id) + "_wastebin_presence"

    @property
    def has_entity_name(self) -> bool:
        """Indicate that entity has name defined."""

        return True

    @property
    def translation_key(self) -> str:
        """Translation key for this entity."""

        return "waste_bin_presence"

    @property
    def icon(self) -> str:
        """Set icon."""

        if self.lb_data.device_detail["state"]["boxState"] == 1:
            return "mdi:inbox"
        else:
            return "mdi:inbox-remove"

    @property
    def device_class(self) -> BinarySensorDeviceClass:
        """Return entity device class."""

        return BinarySensorDeviceClass.PROBLEM

    @property
    def is_on(self) -> bool:
        """Return True if wastebin is present."""

        if self.lb_data.device_detail["state"]["boxState"] == 1:
            return False
        else:
            return True


class CarePlusSubscription(CoordinatorEntity, BinarySensorEntity):
    """Representation of Care Plus subscription status."""

    def __init__(self, coordinator, feeder_id):
        super().__init__(coordinator)
        self.feeder_id = feeder_id

    @property
    def feeder_data(self) -> Feeder:
        """Handle coordinator Feeder data."""
        return self.coordinator.data.feeders[self.feeder_id]

    @property
    def device_info(self) -> dict[str, Any]:
        """Return device registry information for this entity."""
        return {
            "identifiers": {(DOMAIN, self.feeder_data.id)},
            "name": self.feeder_data.data["name"],
            "manufacturer": "PetKit",
            "model": FEEDERS[self.feeder_data.type],
            "sw_version": f'{self.feeder_data.data["firmware"]}',
        }

    @property
    def unique_id(self) -> str:
        """Sets unique ID for this entity."""
        return str(self.feeder_data.id) + "_care_plus_subscription"

    @property
    def has_entity_name(self) -> bool:
        """Indicate that entity has name defined."""
        return True

    @property
    def translation_key(self) -> str:
        """Translation key for this entity."""
        return "care_plus_subscription"

    @property
    def entity_category(self) -> EntityCategory:
        """Set category to diagnostic."""
        return EntityCategory.DIAGNOSTIC

    @property
    def is_on(self) -> bool:
        """Return True if Care Plus subscription is active."""
        return self.feeder_data.data["cloudProduct"]["subscribe"] == 1

    @property
    def icon(self) -> str:
        """Set icon."""
        if self.feeder_data.data["cloudProduct"]["subscribe"] == 1:
            return "mdi:check-circle"
        else:
            return "mdi:cancel"


class WFElectricStatus(CoordinatorEntity, BinarySensorEntity):
    """Representation of Water Fountain electric status."""

    def __init__(self, coordinator, wf_id):
        super().__init__(coordinator)
        self.wf_id = wf_id

    @property
    def wf_data(self) -> Fountain:
        """Handle coordinator Water Fountain data."""
        return self.coordinator.data.water_fountains[self.wf_id]

    @property
    def device_info(self) -> dict[str, Any]:
        """Return device registry information for this entity."""
        return {
            "identifiers": {(DOMAIN, self.wf_data.id)},
            "name": self.wf_data.data["name"],
            "manufacturer": "PetKit",
            "model": (
                WATER_FOUNTAINS.get(
                    self.wf_data.data["typeCode"], "Unidentified Water Fountain"
                )
                if "typeCode" in self.wf_data.data
                else "Unidentified Water Fountain"
            ),
            "sw_version": f'{self.wf_data.data["hardware"]}.{self.wf_data.data["firmware"]}',
        }

    @property
    def unique_id(self) -> str:
        """Sets unique ID for this entity."""
        return str(self.wf_data.id) + "_electric_status"

    @property
    def has_entity_name(self) -> bool:
        """Indicate that entity has name defined."""
        return True

    @property
    def translation_key(self) -> str:
        """Translation key for this entity."""
        return "electric_status"

    @property
    def device_class(self) -> BinarySensorDeviceClass:
        """Return entity device class."""
        return BinarySensorDeviceClass.POWER

    @property
    def is_on(self) -> bool:
        """Return True if the fountain is plugged in."""
        return self.wf_data.data["status"]["electricStatus"] > 0

    @property
    def icon(self) -> str:
        """Set icon."""
        if self.is_on:
            return "mdi:power-plug"
        else:
            return "mdi:power-plug-off"


class WFPumpStatus(CoordinatorEntity, BinarySensorEntity):
    """Representation of Water Fountain pump status."""

    def __init__(self, coordinator, wf_id):
        super().__init__(coordinator)
        self.wf_id = wf_id

    @property
    def wf_data(self) -> Fountain:
        """Handle coordinator Water Fountain data."""
        return self.coordinator.data.water_fountains[self.wf_id]

    @property
    def device_info(self) -> dict[str, Any]:
        """Return device registry information for this entity."""
        return {
            "identifiers": {(DOMAIN, self.wf_data.id)},
            "name": self.wf_data.data["name"],
            "manufacturer": "PetKit",
            "model": (
                WATER_FOUNTAINS.get(
                    self.wf_data.data["typeCode"], "Unidentified Water Fountain"
                )
                if "typeCode" in self.wf_data.data
                else "Unidentified Water Fountain"
            ),
            "sw_version": f'{self.wf_data.data["hardware"]}.{self.wf_data.data["firmware"]}',
        }

    @property
    def unique_id(self) -> str:
        """Sets unique ID for this entity."""
        return str(self.wf_data.id) + "_pump_status"

    @property
    def has_entity_name(self) -> bool:
        """Indicate that entity has name defined."""
        return True

    @property
    def translation_key(self) -> str:
        """Translation key for this entity."""
        return "pump_status"

    @property
    def device_class(self) -> BinarySensorDeviceClass:
        """Return entity device class."""
        return BinarySensorDeviceClass.POWER

    @property
    def is_on(self) -> bool:
        """Return True if the pump is running."""
        return self.wf_data.data["status"]["runStatus"] == 1

    @property
    def icon(self) -> str:
        """Set icon."""
        if self.is_on:
            return "mdi:water-pump"
        else:
            return "mdi:water-pump-off"
