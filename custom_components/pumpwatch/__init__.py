"""PumpWatch: fuel and heating oil prices for Home Assistant."""
import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant, ServiceCall, SupportsResponse
from homeassistant.exceptions import ServiceValidationError
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.typing import ConfigType

from .utils import check_settings, FuelType, ComponentSession

DOMAIN = "pumpwatch"
NAME = "PumpWatch"
PLATFORMS = [Platform.SENSOR]

SERVICES = [
    "get_lowest_fuel_price",
    "get_lowest_fuel_price_coor",
    "get_lowest_fuel_price_on_route",
    "get_lowest_fuel_price_on_route_coor",
]

_LOGGER = logging.getLogger(DOMAIN)

CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up the integration (config entries only, no YAML)."""
    return True


async def async_update_options(hass: HomeAssistant, config_entry: ConfigEntry):
    """Reload integration when options changed."""
    await hass.config_entries.async_reload(config_entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, config_entry: ConfigEntry) -> bool:
    unload_ok = await hass.config_entries.async_unload_platforms(config_entry, PLATFORMS)
    if unload_ok:
        hass.data.get(DOMAIN, {}).pop(config_entry.entry_id, None)
        # Services are shared by all entries: drop them with the last one.
        if not hass.data.get(DOMAIN):
            for service in SERVICES:
                hass.services.async_remove(DOMAIN, service)

    return unload_ok


async def async_setup_entry(hass: HomeAssistant, config_entry: ConfigEntry) -> bool:
    """Set up component as config entry."""
    from .sensor import PumpWatchDataUpdateCoordinator, ComponentData

    config = config_entry.data
    check_settings(config, hass)

    component_data = ComponentData(config, hass)
    coordinator = PumpWatchDataUpdateCoordinator(hass, component_data)
    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][config_entry.entry_id] = coordinator

    try:
        await hass.config_entries.async_forward_entry_setups(config_entry, PLATFORMS)
    except Exception:
        hass.data[DOMAIN].pop(config_entry.entry_id, None)
        raise

    config_entry.async_on_unload(config_entry.add_update_listener(async_update_options))
    register_services(hass)
    return True


def _geo_api_key(hass: HomeAssistant, required: bool) -> str:
    """Return the GeoApify key of the first configured entry."""
    for entry in hass.config_entries.async_entries(DOMAIN):
        key = entry.data.get("GEO_API_KEY")
        if key and key != "GEO_API_KEY":
            return key
    if required:
        raise ServiceValidationError("No GEO_API_KEY set")
    return ""


def _fuel_type(call: ServiceCall) -> FuelType:
    fuel_type = getattr(FuelType, str(call.data.get("fuel_type", "")).upper(), None)
    if fuel_type is None:
        raise ServiceValidationError(f"Unknown fuel_type: {call.data.get('fuel_type')}")
    return fuel_type


def register_services(hass: HomeAssistant):
    """Register the integration services once (shared by all config entries)."""
    if hass.services.has_service(DOMAIN, SERVICES[0]):
        return

    async def _run(event_suffix, call, func):
        station_info = await hass.async_add_executor_job(func)
        _LOGGER.debug(f"{NAME} {event_suffix} info found: {station_info}")
        hass.bus.async_fire(f"{DOMAIN}_{event_suffix}", station_info)
        return station_info

    async def handle_get_lowest_fuel_price(call: ServiceCall):
        fuel_type = _fuel_type(call)
        session = ComponentSession(_geo_api_key(hass, False))
        return await _run("lowest_fuel_price", call, lambda: session.getStationInfo(
            call.data.get("postalcode"),
            call.data.get("country"),
            fuel_type,
            call.data.get("town") or "",
            call.data.get("max_distance") or 0,
            call.data.get("filter") or "",
            True,
        ))

    async def handle_get_lowest_fuel_price_coor(call: ServiceCall):
        fuel_type = _fuel_type(call)
        session = ComponentSession(_geo_api_key(hass, True))
        return await _run("lowest_fuel_price_coor", call, lambda: session.getStationInfoLatLon(
            call.data.get("latitude"),
            call.data.get("longitude"),
            fuel_type,
            call.data.get("max_distance") or 0,
            call.data.get("filter") or "",
        ))

    async def handle_get_lowest_fuel_price_on_route(call: ServiceCall):
        fuel_type = _fuel_type(call)
        country = call.data.get("country")
        session = ComponentSession(_geo_api_key(hass, True))
        return await _run("lowest_fuel_price_on_route", call, lambda: session.getPriceOnRoute(
            country,
            fuel_type,
            call.data.get("from_postalcode"),
            call.data.get("to_postalcode"),
            call.data.get("to_country", country),
            call.data.get("filter") or "",
        ))

    async def handle_get_lowest_fuel_price_on_route_coor(call: ServiceCall):
        fuel_type = _fuel_type(call)
        session = ComponentSession(_geo_api_key(hass, True))
        return await _run("lowest_fuel_price_on_route_coor", call, lambda: session.getPriceOnRouteLatLon(
            fuel_type,
            call.data.get("from_latitude"),
            call.data.get("from_longitude"),
            call.data.get("to_latitude"),
            call.data.get("to_longitude"),
            call.data.get("filter") or "",
        ))

    handlers = {
        "get_lowest_fuel_price": handle_get_lowest_fuel_price,
        "get_lowest_fuel_price_coor": handle_get_lowest_fuel_price_coor,
        "get_lowest_fuel_price_on_route": handle_get_lowest_fuel_price_on_route,
        "get_lowest_fuel_price_on_route_coor": handle_get_lowest_fuel_price_on_route_coor,
    }
    for name, handler in handlers.items():
        # Results are fired on the event bus (as before) and also returned,
        # so they can be used directly with `response_variable`.
        hass.services.async_register(
            DOMAIN, name, handler, supports_response=SupportsResponse.OPTIONAL
        )
    _LOGGER.debug(f"{NAME} services registered")
