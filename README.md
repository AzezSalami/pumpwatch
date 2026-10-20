# PumpWatch

Home Assistant integration for fuel and heating-oil prices: Belgium, France, Luxembourg,
Germany, Italy, the Netherlands, Spain and the US. It provides price sensors for the
cheapest station near a postal code (0/5/10 km), official maximum prices, price-trend
predictions (BE/FR/LU), heating-oil prices, and services to find the cheapest station
near a point or along a route.

> PumpWatch is a community-maintained continuation of the `carbu_com` integration by
> [myTselection](https://github.com/myTselection), whose repository is no longer available.
> It is a separate integration (domain `pumpwatch`), so it can run next to the old one.
> Data comes from Carbu.com, Mazout.com, clever-tanken.de, prezzibenzina.it,
> brandstof-zoeker.nl, the Spanish MINETUR API and GasBuddy.

## Install (HACS)

1. HACS → ⋮ → **Custom repositories** → add `https://github.com/azezsalami/pumpwatch`, category **Integration**.
2. Download **PumpWatch**, restart Home Assistant.
3. Settings → Devices & services → **Add integration** → PumpWatch.

A free [Geoapify](https://www.geoapify.com/) API key is required for NL/IT/ES/US and for the
coordinate/route services.

## Updates

HACS shows an update whenever a new GitHub release is published. To install updates
automatically, add an automation that calls `update.install` for the PumpWatch update
entity (then restart HA when it finishes).

## Services

All services also return their result (usable with `response_variable`) and fire an event
`pumpwatch_<service suffix>`:

| Service | Event |
|---|---|
| `pumpwatch.get_lowest_fuel_price` | `pumpwatch_lowest_fuel_price` |
| `pumpwatch.get_lowest_fuel_price_coor` | `pumpwatch_lowest_fuel_price_coor` |
| `pumpwatch.get_lowest_fuel_price_on_route` | `pumpwatch_lowest_fuel_price_on_route` |
| `pumpwatch.get_lowest_fuel_price_on_route_coor` | `pumpwatch_lowest_fuel_price_on_route_coor` |

## Migrating from carbu_com

Entity IDs change (`sensor.carbu_com_…` → `sensor.pumpwatch_…`). Add PumpWatch with the
same settings, update dashboards/automations, then remove the old integration.

## Releasing

Bump nothing by hand: `git tag v1.0.1 && git push --tags` builds the release and stamps the version.
