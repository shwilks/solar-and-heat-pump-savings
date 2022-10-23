from dataclasses import dataclass
from enum import Enum

import pandas as pd

from fuels import Fuel

HOUSE_TYPES = ["Terrace", "Semi-detached", "Detached", "Flat"]

BASE_YEAR_HALF_HOUR_INDEX = pd.date_range(start="2020-01-01", end="2021-01-01", freq="30T")
EMPTY_TIMESERIES = pd.Series(index=BASE_YEAR_HALF_HOUR_INDEX, data=0)

kwh_PER_LITRE_OF_OIL = 10.35  # https://www.thegreenage.co.uk/is-heating-oil-a-cheap-way-to-heat-my-home/

ELECTRICITY = Fuel("electricity", tco2_per_kwh=180 / 10 ** 6)  # Emission factors approximate for now
GAS = Fuel(name="gas", tco2_per_kwh=300 / 10 ** 6)
OIL = Fuel(name="oil", units="litres", converter_consumption_units_to_kwh=kwh_PER_LITRE_OF_OIL,
           tco2_per_kwh=400 / 10 ** 6)
FUELS = [ELECTRICITY, GAS, OIL]


@dataclass
class HeatingConstants:
    space_heating_efficiency: float
    water_heating_efficiency: float
    fuel: Fuel


DEFAULT_HEATING_CONSTANTS = {
    "Gas boiler": HeatingConstants(space_heating_efficiency=0.85, water_heating_efficiency=0.8, fuel=GAS),
    "Oil boiler": HeatingConstants(space_heating_efficiency=0.8, water_heating_efficiency=0.75, fuel=OIL),
    "Direct electric": HeatingConstants(space_heating_efficiency=1.0, water_heating_efficiency=1.0, fuel=ELECTRICITY),
    "Heat pump": HeatingConstants(space_heating_efficiency=3.5, water_heating_efficiency=3.0, fuel=ELECTRICITY),
}


@dataclass
class TariffConstants:
    p_per_kwh_gas: float
    p_per_kwh_elec_import: float
    p_per_kwh_elec_export: float
    p_per_L_oil: float
    p_per_day_gas: float
    p_per_day_elec: float


STANDARD_TARIFF = TariffConstants(
    p_per_kwh_gas=10.3, p_per_kwh_elec_import=34.0, p_per_kwh_elec_export=15.0, p_per_L_oil=95.0,
    p_per_day_gas=28.0, p_per_day_elec=46.0
)


@dataclass()
class Orientation:
    """ Azimuth is degrees clockwise from South, max absolute value of 180"""
    azimuth_degrees: float

    # https://re.jrc.ec.europa.eu/pvg_tools/en/

    def __post_init__(self):
        if self.azimuth_degrees > 180:
            self.azimuth_degrees += -360
        elif self.azimuth_degrees <= -180:
            self.azimuth_degrees += 360


@dataclass()
class OrientationOptions:
    SOUTH = Orientation(0)
    SOUTHWEST = Orientation(45)
    WEST = Orientation(90)
    NORTHWEST = Orientation(135)
    NORTH = Orientation(180)
    NORTHEAST = Orientation(-45)
    EAST = Orientation(-90)
    SOUTHEAST = Orientation(-135)


class SolarConstants:
    SOLAR_ORIENTATIONS = OrientationOptions
    MIN_ROOF_AREA = 0
    MAX_ROOF_AREA = 20
    DEFAULT_ROOF_AREA = 20
    ROOF_PITCH_DEGREES = 30
    PANEL_HEIGHT_M = 1.67
    PANEL_WIDTH_M = 1.0
    PANEL_AREA = PANEL_HEIGHT_M * PANEL_WIDTH_M
    KW_PEAK_PER_PANEL = 0.30  # output with incident radiation of 1kW/m2
    # Panel dimensions and kW_peak from https://www.greenmatch.co.uk/blog/how-many-solar-panels-do-i-need
    PERCENT_SQUARE_USABLE = 0.8  # complete guess
    API_YEAR = 2020  # Based on quick comparison of years for one location in the uk.
    # If you don't pass years to the API it gives you all hours from first to last year they have data for.
    SYSTEM_LOSS = 14  # percentage loss in the system - the PVGIS documentation suggests 14 %

