"""DataUpdateCoordinator for the PetKit integration."""

from __future__ import annotations

from datetime import timedelta

from petkit_api import PetKitClient
from petkit_api.exceptions import AuthError, PetKitError, RegionError, ServerError
from petkit_api.model import PetKitData


from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_EMAIL, CONF_PASSWORD
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import DOMAIN, LOGGER, POLLING_INTERVAL, REGION, TIMEOUT, TIMEZONE


class PetKitDataUpdateCoordinator(DataUpdateCoordinator):
    """PetKit Data Update Coordinator."""

    data: PetKitData

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        """Initialize the PetKit coordinator."""
        try:
            LOGGER.debug(
                f"Creating PetKit client with email: {entry.data[CONF_EMAIL]}, region: {entry.options[REGION]}, timezone: {entry.options[TIMEZONE]}"
            )
            self.client = PetKitClient(
                entry.data[CONF_EMAIL],
                entry.data[CONF_PASSWORD],
                region=entry.options[REGION],
                timezone=entry.options[TIMEZONE],
                session=async_get_clientsession(hass),
                timeout=TIMEOUT,
            )
            super().__init__(
                hass,
                LOGGER,
                name=DOMAIN,
                update_interval=timedelta(seconds=entry.options[POLLING_INTERVAL]),
            )
        except RegionError as error:
            raise ConfigEntryAuthFailed(error) from error

    async def _async_update_data(self) -> PetKitData:
        """Fetch data from PetKit."""

        try:
            data = await self.client.get_petkit_data()
            LOGGER.debug(f"Found the following PetKit devices/pets: {data}")
        except (AuthError, RegionError) as error:
            raise ConfigEntryAuthFailed(error) from error
        except (ServerError, PetKitError) as error:
            raise UpdateFailed(error) from error
        else:
            return data
