import plotly.express as px
import streamlit as st

import building_model
from building_model import *
from solar import Solar


def render(house: 'House', solar: 'Solar'):
    st.header("Your Heat Pump and Solar Savings")
    st.subheader("Energy Bills")
    bills_chart = st.empty()
    bills_text = st.empty()
    st.subheader("Carbon Emissions")
    carbon_chart = st.empty()
    carbon_text = st.empty()
    st.subheader("Energy Consumption")
    energy_chart = st.empty()
    energy_text = st.empty()

    with st.sidebar:
        st.header("Assumptions")
        st.subheader("Current Performance")
        house = render_and_update_current_home(house)

        st.subheader("Improvement Options")
        upgrade_heating, upgrade_solar = render_and_update_improvement_options(solar=solar)

    # Upgraded buildings
    hp_house, solar_house, both_house = building_model.upgrade_buildings(baseline_house=house,
                                                                         upgrade_heating=upgrade_heating,
                                                                         upgrade_solar=upgrade_solar)

    # Combine results
    results_df = combine_results_dfs_multiple_houses([house, solar_house, hp_house, both_house],
                                                     ['Current', 'With solar', 'With a heat pump',
                                                      'With solar and a heat pump'])

    with bills_chart:
        render_bill_chart(results_df)
    with bills_text:
        render_bill_outputs(house=house, solar_house=solar_house, hp_house=hp_house, both_house=both_house)

    with energy_chart:
        render_consumption_chart(results_df)
    with energy_text:
        render_consumption_outputs(house=house, solar_house=solar_house, hp_house=hp_house, both_house=both_house)

    with carbon_chart:
        render_carbon_chart(results_df)
    with carbon_text:
        render_carbon_outputs(house=house, solar_house=solar_house, hp_house=hp_house, both_house=both_house)


def render_and_update_current_home(house: House):
    with st.expander("Demand assumptions"):
        house.envelope = render_and_update_envelope_outputs(envelope=house.envelope)
    with st.expander("Baseline heating system assumptions"):
        house.heating_system = render_and_update_heating_system(heating_system=house.heating_system)
    with st.expander("Tariff assumptions"):
        house = render_and_update_tariffs(house=house)
    return house


def render_and_update_envelope_outputs(envelope: 'BuildingEnvelope') -> 'BuildingEnvelope':
    st.write(f"We assume that an {envelope.floor_area_m2}m\u00b2 {envelope.house_type.lower()} needs: ")
    envelope.annual_heating_demand = render_and_update_annual_demand(label='Space and water heating (kwh): ',
                                                                     demand=envelope.annual_heating_demand)
    envelope.base_demand = render_and_update_annual_demand(label='Lighting, appliances, plug loads etc. (kwh): ',
                                                           demand=envelope.base_demand)
    return envelope


def render_and_update_annual_demand(label: str, demand: pd.Series | float) -> pd.Series:
    """ If user overwrites annual total then scale whole profile by multiplier"""
    if type(demand) is pd.Series:
        demand_overwrite = st.number_input(label=label, min_value=0, max_value=100000, value=int(demand.sum()))
        if demand_overwrite != int(demand.sum()):  # scale profile  by correction factor
            demand = demand_overwrite / int(demand.sum()) * demand
    else:
        demand_overwrite = st.number_input(label=label, min_value=0, max_value=100000, value=int(demand))
        demand = demand_overwrite
    return demand


def render_and_update_heating_system(heating_system: 'HeatingSystem') -> 'HeatingSystem':
    heating_system.efficiency = st.number_input(label='Heating efficiency: ',
                                                min_value=0.0,
                                                max_value=8.0,
                                                value=heating_system.efficiency)
    return heating_system


def render_and_update_tariffs(house: 'House') -> 'House':
    st.subheader('Electricity')
    house.tariffs['electricity'].p_per_unit_import = st.number_input(label='Unit rate (p/kwh), electricity import',
                                                                     min_value=0.0,
                                                                     max_value=100.0,
                                                                     value=house.tariffs[
                                                                         'electricity'].p_per_unit_import)
    house.tariffs['electricity'].p_per_unit_export = st.number_input(label='Unit rate (p/kwh), electricity export',
                                                                     min_value=0.0,
                                                                     max_value=100.0,
                                                                     value=house.tariffs[
                                                                         'electricity'].p_per_unit_export)
    house.tariffs['electricity'].p_per_day = st.number_input(label='Standing charge (p/day), electricity',
                                                             min_value=0.0,
                                                             max_value=100.0,
                                                             value=house.tariffs['electricity'].p_per_day)
    match house.heating_system.fuel.name:
        case 'gas':
            st.subheader('Gas')
            house.tariffs['gas'].p_per_unit_import = st.number_input(label='Unit rate (p/kwh), gas',
                                                                     min_value=0.0,
                                                                     max_value=100.0,
                                                                     value=house.tariffs['gas'].p_per_unit_import)
            house.tariffs['gas'].p_per_day = st.number_input(label='Standing charge (p/day), gas',
                                                             min_value=0.0,
                                                             max_value=100.0,
                                                             value=house.tariffs['gas'].p_per_day)
        case 'oil':
            st.subheader('Oil')
            house.tariffs['oil'].p_per_unit_import = st.number_input(label='Oil price, (p/litre)',
                                                                     min_value=0.0,
                                                                     max_value=200.0,
                                                                     value=house.tariffs['oil'].p_per_unit_import)
    return house


def render_and_update_improvement_options(solar: Solar) -> Tuple[HeatingSystem, Solar]:
    with st.expander("Heat pump assumptions"):
        upgrade_heating = HeatingSystem.from_constants(name='Heat pump',
                                                       parameters=constants.DEFAULT_HEATING_CONSTANTS['Heat pump'])
        upgrade_heating = render_and_update_heating_system(heating_system=upgrade_heating)
    with st.expander("Solar PV assumptions "):
        solar = render_and_update_solar(solar=solar)

    return upgrade_heating, solar


def render_and_update_solar(solar: 'Solar'):
    solar.number_of_panels = st.number_input(label='Number of panels',
                                             min_value=0,
                                             max_value=40,
                                             value=int(solar.number_of_panels))
    solar.kwp_per_panel = st.number_input(label='capacity_per_panel',
                                          min_value=0.0,
                                          max_value=0.8,
                                          value=solar.kwp_per_panel)
    return solar


def render_bill_chart(results_df: pd.DataFrame):
    render_savings_chart(results_df=results_df, y_variable='Your annual energy bill £')


def render_bill_outputs(house: 'House', solar_house: 'House', hp_house: 'House', both_house: 'House'):
    st.write(f'We calculate that {produce_current_bill_sentence(house)}  \n'
             f'- with solar {produce_hypothetical_bill_sentence(solar_house)}, '
             f' {produce_bill_saving_sentence(house=solar_house, baseline_house=house)}  \n'
             f'- with a heat pump {produce_hypothetical_bill_sentence(hp_house)}, '
             f' {produce_bill_saving_sentence(house=hp_house, baseline_house=house)}  \n'
             f'- with solar and a heat pump {produce_hypothetical_bill_sentence(both_house)}, '
             f' {produce_bill_saving_sentence(house=both_house, baseline_house=house)}  \n'
             )


def produce_current_bill_sentence(house) -> str:
    sentence = f'your energy bills for the next year will be £{int(house.total_annual_bill):,}'
    return sentence


def produce_hypothetical_bill_sentence(house) -> str:
    sentence = f'they would be £{int(house.total_annual_bill):,}'
    return sentence


def produce_bill_saving_sentence(house: 'House', baseline_house: 'House') -> str:
    sentence = f"that's a saving of £{int(baseline_house.total_annual_bill - house.total_annual_bill):,}"
    return sentence


def render_carbon_chart(results_df: pd.DataFrame):
    render_savings_chart(results_df=results_df, y_variable='Your annual carbon emissions tCO2')


def render_carbon_outputs(house: 'House', solar_house: 'House', hp_house: 'House', both_house: 'House'):
    st.write(
        f"We calculate that your house emits {house.total_annual_tco2:.2f} tonnes of CO2 per year  \n"
        f"- with solar that would fall to {solar_house.total_annual_tco2:.2f} tonnes of CO2 per year  \n"
        f"- with a heat pump that would fall to {hp_house.total_annual_tco2:.2f} tonnes of CO2 per year  \n"
        f"- with solar and a heat pump that would fall to {both_house.total_annual_tco2:.2f} "
        f"tonnes of CO2 per year  \n"
    )


def render_consumption_chart(results_df: pd.DataFrame):
    render_savings_chart(results_df=results_df, y_variable='Your annual energy use kwh')


def render_consumption_outputs(house: 'House', solar_house: 'House', hp_house: 'House', both_house: 'House'):
    st.write(
        f"We calculate that your house currently needs {produce_consumption_sentence(house)}  \n"
        f"- with solar that would fall to {produce_consumption_sentence(solar_house)}  \n"
        f"- with a heat pump that would fall to {produce_consumption_sentence(hp_house)}  \n"
        f"- with solar and a heat pump that would fall to {produce_consumption_sentence(both_house)} "
    )


def produce_consumption_sentence(house):
    if house.has_multiple_fuels:
        sentence = (f"{int(house.consumption_per_fuel['electricity'].overall.annual_sum_kwh):,} "
                    f"kwh of electricity and "
                    f"{int(house.consumption_per_fuel[house.heating_system.fuel.name].overall.annual_sum_fuel_units):,}"
                    f" {house.heating_system.fuel.units} of {house.heating_system.fuel.name} per year")
    else:
        sentence = f"{int(house.consumption_per_fuel['electricity'].overall.annual_sum_kwh):,}" \
                   f" kwh of electricity per year "
    return sentence


def render_savings_chart(results_df: pd.DataFrame, y_variable: str):
    bills_fig = px.bar(results_df, x='Upgrade option', y=y_variable, color='fuel')
    st.plotly_chart(bills_fig, use_container_width=True, sharing="streamlit")
