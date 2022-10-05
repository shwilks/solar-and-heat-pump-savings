from dataclasses import dataclass
from typing import Dict

import pandas as pd
import streamlit as st

import constants


def render_questions() -> 'House':
    st.header("Your house")
    envelope = render_house_questions()
    heating_system_name = render_heating_system_questions()
    house = House(envelope=envelope, heating_name=heating_system_name)
    return house


def render_outputs(house: 'House') -> 'House':
    st.header("Your current energy use ")
    st.write("Based on your answers in the last tab, we calculate that your home needs")
    with st.expander("Expand demand assumptions"):
        house.envelope = render_and_allow_overwrite_of_envelope_outputs(envelope=house.envelope)
    with st.expander("Expand heating system assumptions"):
        house.heating_system = render_and_allow_overwrite_of_heating_system(heating_system=house.heating_system)

    render_consumption_outputs(house=house)
    with st.expander("Expand tariff assumptions"):
        house = render_and_allow_overwrite_of_tariffs(house=house)
    render_bill_outputs(house=house)
    return house


def render_house_questions() -> 'BuildingEnvelope':
    house_type = st.selectbox('House Type', options=constants.HOUSE_TYPES)
    house_floor_area_m2 = st.number_input(label='House floor area (m2)', min_value=0, max_value=500, value=80)
    envelope = BuildingEnvelope(house_type=house_type, floor_area_m2=house_floor_area_m2)
    return envelope


def render_heating_system_questions() -> str:
    heating_system_name = st.selectbox('Heating System', options=constants.DEFAULT_HEATING_CONSTANTS.keys())
    return heating_system_name


def render_and_allow_overwrite_of_envelope_outputs(envelope: 'BuildingEnvelope') -> 'BuildingEnvelope':
    st.write(f"We assume that an {envelope.floor_area_m2}m\u00b2 {envelope.house_type.lower()} needs about: ")
    envelope.space_heating_demand = render_and_allow_overwrite_of_annual_demand(label='Heating (kWh): ',
                                                                                demand=envelope.space_heating_demand)
    envelope.water_heating_demand = render_and_allow_overwrite_of_annual_demand(label='Hot water (kWh): ',
                                                                                demand=envelope.water_heating_demand)
    envelope.base_demand = render_and_allow_overwrite_of_annual_demand(label='Other (lighting/appliances etc.) (kWh): ',
                                                                       demand=envelope.base_demand)
    return envelope


def render_and_allow_overwrite_of_annual_demand(label: str, demand: 'Demand') -> 'Demand':
    """ If user overwrites annual total then scale whole profile by multiplier"""
    demand_overwrite = st.number_input(label=label, min_value=0, max_value=100000, value=int(demand.annual_sum))
    if demand_overwrite != int(demand.annual_sum):  # scale profile  by correction factor
        demand.profile_kWh = demand_overwrite / int(demand.annual_sum) * demand.profile_kWh
    return demand


def render_and_allow_overwrite_of_heating_system(heating_system: 'HeatingSystem') -> 'HeatingSystem':
    heating_system.space_heating_efficiency = st.number_input(label='Efficiency for space heating: ',
                                                                    min_value=0.0,
                                                                    max_value=8.0,
                                                                    value=heating_system.space_heating_efficiency)
    heating_system.water_heating_efficiency = st.number_input(label='Efficiency for water heating: ',
                                                                    min_value=0.0,
                                                                    max_value=8.0,
                                                                    value=heating_system.water_heating_efficiency)
    return heating_system


def render_consumption_outputs(house: 'House'):
    if house.heating_system.fuel.name == 'electricity':
        st.write(
            f"We calculate that your house needs about "
            f"{int(house.consumption_dict['electricity'].annual_sum):,} kWh of electricity a year")
    else:
        st.write(
            f"We calculate that your house needs about "
            f"{int(house.consumption_dict['electricity'].annual_sum):,} kWh of electricity per year"
            f" and {int(house.consumption_dict[house.heating_system.fuel.name].annual_sum):,}"
            f" {house.heating_system.fuel.units} of {house.heating_system.fuel.name}")


def render_and_allow_overwrite_of_tariffs(house: 'House') -> 'House':
    st.write(f"We have assumed that you are on a default energy tariff, but if you have fixed at a different rate"
             " then you can edit the numbers. Unfortunately we can't deal with variable rates like Octopus Agile/Go "
             "or Economy 7 right now, but we are working on it!")

    st.subheader('Electricity')
    house.tariffs['electricity'].p_per_unit = st.number_input(label='Unit rate (p/kWh), electricity',
                                                              min_value=0.0,
                                                              max_value=100.0,
                                                              value=house.tariffs['electricity'].p_per_unit)
    house.tariffs['electricity'].p_per_day = st.number_input(label='Standing charge (p/day), electricity',
                                                             min_value=0.0,
                                                             max_value=100.0,
                                                             value=house.tariffs['electricity'].p_per_day)
    match house.heating_system.fuel.name:
        case 'gas':
            st.subheader('Gas')
            house.tariffs['gas'].p_per_unit = st.number_input(label='Unit rate (p/kWh), gas',
                                                              min_value=0.0,
                                                              max_value=100.0,
                                                              value=house.tariffs['gas'].p_per_unit)
            house.tariffs['gas'].p_per_day = st.number_input(label='Standing charge (p/day), gas',
                                                             min_value=0.0,
                                                             max_value=100.0,
                                                             value=house.tariffs['gas'].p_per_day)
        case 'oil':
            st.subheader('Oil')
            house.tariffs['oil'].p_per_unit = st.number_input(label='Oil price, (p/litre)',
                                                              min_value=0.0,
                                                              max_value=200.0,
                                                              value=house.tariffs['oil'].p_per_unit)
    return house


def render_bill_outputs(house: 'House'):
    breakdown = f'({", ".join(f"£{int(amount):,} for {fuel_name}" for fuel_name, amount in house.bills_dict.items())})'
    st.write(f'We calculate that your annual energy bill on this tariff will be £{int(house.bill_annual_sum):,}'
             f' {breakdown if house.has_multiple_fuels else ""}')


class House:
    """ Stores info on consumption and bills """

    def __init__(self, envelope: 'BuildingEnvelope', heating_name: str):

        self.envelope = envelope
        # Set up initial values for heating system and tariffs but allow to be modified by the user later
        # Maybe I should be using getters and setters here?
        self.heating_system = HeatingSystem.from_constants(name=heating_name,
                                                           parameters=constants.DEFAULT_HEATING_CONSTANTS[heating_name])
        self.tariffs = self.set_up_standard_tariffs()

    def set_up_standard_tariffs(self) -> Dict[str, 'Tariff']:

        tariffs = {'electricity': Tariff(p_per_unit=constants.STANDARD_TARIFF.p_per_kWh_elec,
                                         p_per_day=constants.STANDARD_TARIFF.p_per_day_elec,
                                         fuel=constants.ELECTRICITY)}
        match self.heating_system.fuel.name:
            case 'gas':
                tariffs['gas'] = Tariff(p_per_unit=constants.STANDARD_TARIFF.p_per_kWh_gas,
                                        p_per_day=constants.STANDARD_TARIFF.p_per_day_gas,
                                        fuel=self.heating_system.fuel)
            case 'oil':
                tariffs['oil'] = Tariff(p_per_unit=constants.STANDARD_TARIFF.p_per_L_oil,
                                        p_per_day=0.0,
                                        fuel=self.heating_system.fuel)
        return tariffs

    @property
    def has_multiple_fuels(self) -> bool:
        return len(self.tariffs) > 1

    @property
    def consumption_dict(self) -> Dict[str, 'Consumption']:

        # Base demand is always electricity (lighting/plug loads etc.)
        base_consumption = Consumption(profile=self.envelope.base_demand.profile_kWh,
                                       fuel=constants.ELECTRICITY)
        space_heating_consumption = self.heating_system.calculate_space_heating_consumption(
            self.envelope.space_heating_demand)
        water_heating_consumption = self.heating_system.calculate_water_heating_consumption(
            self.envelope.water_heating_demand)
        heating_consumption = water_heating_consumption.add(space_heating_consumption)

        match self.heating_system.fuel:
            case base_consumption.fuel:  # only one fuel (electricity)
                consumption_dict = {self.heating_system.fuel.name: base_consumption.add(heating_consumption)}
            case _:
                consumption_dict = {base_consumption.fuel.name: base_consumption,
                                    heating_consumption.fuel.name: heating_consumption}

        return consumption_dict

    @property
    def bills_dict(self) -> Dict[str, float]:
        bills_dict = {}
        for fuel_name, consumption in self.consumption_dict.items():
            bills_dict[fuel_name] = self.tariffs[fuel_name].calculate_annual_cost(consumption)
        return bills_dict

    @property
    def bill_annual_sum(self) -> float:
        return sum(self.bills_dict.values())


@dataclass()
class BuildingEnvelope:
    """ Stores info on the building and its energy demand"""

    def __init__(self, floor_area_m2: float, house_type: str):
        self.floor_area_m2 = floor_area_m2
        self.house_type = house_type
        self.time_series_idx: pd.Index = constants.BASE_YEAR_HALF_HOUR_INDEX
        self.units: str = 'kWh'

        # Set initial demand values - user can overwrite later
        # Dummy data for now TODO get profiles from elsewhere
        self.base_demand = Demand(profile_kWh=pd.Series(index=self.time_series_idx, data=0.001 * self.floor_area_m2))
        self.water_heating_demand = Demand(
            profile_kWh=pd.Series(index=self.time_series_idx, data=0.004 * self.floor_area_m2))
        self.space_heating_demand = Demand(
            profile_kWh=pd.Series(index=self.time_series_idx, data=0.005 * self.floor_area_m2))


@dataclass
class Demand:
    profile_kWh: pd.Series  # TODO: figure out how to specify index should be datetime in typing?

    @property
    def annual_sum(self) -> float:
        annual_sum = self.profile_kWh.sum()
        return annual_sum

    def add(self, other: 'Demand') -> 'Demand':
        combined_time_series = self.profile_kWh + other.profile_kWh
        combined = Demand(profile_kWh=combined_time_series)
        return combined


@dataclass
class Consumption:
    profile: pd.Series
    fuel: constants.Fuel = constants.ELECTRICITY

    @property
    def annual_sum(self) -> float:
        annual_sum = self.profile.sum()
        return annual_sum

    def add(self, other: 'Consumption') -> 'Consumption':
        if self.fuel == other.fuel:
            combined_time_series = self.profile + other.profile
            combined = Consumption(profile=combined_time_series, fuel=self.fuel)
        else:
            raise ValueError("The fuel of the two consumptions must match")
            # idea: maybe this should work and just return a list?
        return combined


@dataclass
class HeatingSystem:
    name: str
    space_heating_efficiency: float
    water_heating_efficiency: float
    fuel: constants.Fuel

    @classmethod
    def from_constants(cls, name, parameters: constants.HeatingConstants):
        return cls(name=name,
                   space_heating_efficiency=parameters.space_heating_efficiency,
                   water_heating_efficiency=parameters.water_heating_efficiency,
                   fuel=parameters.fuel)

    def __post_init__(self):
        if self.fuel not in constants.FUELS:
            raise ValueError(f"fuel must be one of {constants.FUELS}")

    def calculate_space_heating_consumption(self, space_heating_demand: Demand) -> Consumption:
        return self.calculate_consumption(demand=space_heating_demand, efficiency=self.space_heating_efficiency)

    def calculate_water_heating_consumption(self, water_heating_demand: Demand) -> Consumption:
        return self.calculate_consumption(demand=water_heating_demand, efficiency=self.water_heating_efficiency)

    def calculate_consumption(self, demand: Demand, efficiency: float) -> Consumption:
        profile_kwh = demand.profile_kWh / efficiency
        profile = profile_kwh / self.fuel.converter_consumption_units_to_kWh
        return Consumption(profile=profile, fuel=self.fuel)


@dataclass
class Tariff:
    p_per_unit: float  # unit defined by the fuel
    p_per_day: float
    fuel: constants.Fuel

    def calculate_annual_cost(self, consumption: 'Consumption') -> float:
        if self.fuel != consumption.fuel:
            raise ValueError("To calculate annual costs the tariff fuel must match the consumption fuel, they are"
                             f"{self.fuel} and {consumption.fuel}")
        annual_cost = (365 * self.p_per_day + consumption.annual_sum * self.p_per_unit) / 100
        return annual_cost
