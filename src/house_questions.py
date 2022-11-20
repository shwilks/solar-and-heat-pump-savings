import streamlit as st
import constants

from building_model import House, BuildingEnvelope, HeatingSystem, Tariff


def render() -> "House":
    house = get_house_from_session_state_if_exists_or_create_default()

    st.header("Start by telling us about your home")
    st.markdown(
        f"<p class='more-info'> If you know lots more about your home and tariff, you can"
        f"  <a  href='javascript:document.getElementsByClassName({constants.CLASS_NAME_OF_SIDEBAR_DIV}"
        f")[1].click();' target='_self'> enter more details here!</a></p>",
        unsafe_allow_html=True,
    )

    house.envelope = render_building_envelope_questions(house.envelope)
    house = render_heating_system_questions(house=house)
    house = render_assumptions_sidebar(house=house)

    render_results(house)

    return house


def get_house_from_session_state_if_exists_or_create_default():
    if st.session_state["page_state"]["house"] == {}:
        print("Setting up default house")
        house = set_up_default_house()
        st.session_state["page_state"]["house"] = dict(house=house)  # in case this page isn't always rendered
    else:
        print("reading house from session state")
        house = st.session_state["page_state"]["house"]["house"]
    return house


def set_up_default_house() -> "House":
    envelope = BuildingEnvelope.from_building_type_constants(constants.BUILDING_TYPE_OPTIONS["Terrace"])
    heating_system_name = list(constants.DEFAULT_HEATING_CONSTANTS.keys())[0]
    house = House.set_up_from_heating_name(envelope=envelope, heating_name=heating_system_name)
    return house


def render_building_envelope_questions(envelope: BuildingEnvelope) -> BuildingEnvelope:
    with st.container():
        col1, col2 = st.columns(2)
        with col1:
            st.write("I live in a")
        with col2:
            if "house_type" not in st.session_state:
                st.session_state.house_type = envelope.house_type
                st.session_state.heating_demand_set_by_dropdown = False
                st.session_state.base_demand_set_by_dropdown = False

            house_type = st.selectbox("", options=constants.BUILDING_TYPE_OPTIONS.keys(), key="house_type")

            if house_type != envelope.house_type:  # only overwrite if house type changed by user
                print("Behaves as if house changed")
                envelope = BuildingEnvelope.from_building_type_constants(constants.BUILDING_TYPE_OPTIONS[house_type])
                st.session_state.heating_demand_set_by_dropdown = False
                st.session_state.base_demand_set_by_dropdown = False

    return envelope


def render_heating_system_questions(house: House) -> House:
    with st.container():
        col1, col2 = st.columns(2)
        with col1:
            st.write("My home is heated with a")
        with col2:
            if "baseline_heating_efficiency" not in st.session_state:
                # initialise
                st.session_state.baseline_heating_efficiency = house.heating_system.efficiency
                st.session_state.baseline_heating_efficiency_set_by_dropdown = False
                st.session_state.heating_fuel_tariff_defined_by_dropdown = False

            heating_name = st.selectbox(
                "", options=list(constants.DEFAULT_HEATING_CONSTANTS.keys()), key="heating_system_name")

            if heating_name != house.heating_system.name:  # only overwrite heating system if changed by user
                print("Behaves as if heating system changed")
                original_fuel_name = house.heating_system.fuel.name
                house.heating_system = HeatingSystem.from_constants(
                    name=heating_name, parameters=constants.DEFAULT_HEATING_CONSTANTS[heating_name])
                st.session_state.baseline_heating_efficiency_set_by_dropdown = False

                if house.heating_system.fuel.name != original_fuel_name:
                    # only overwrite tariffs if heating fuel changed, keep any overwrites otherwise
                    house.tariffs = house.set_up_standard_tariffs()
                    st.session_state.heating_fuel_tariff_defined_by_dropdown = False

    return house


def render_assumptions_sidebar(house: House) -> House:
    with st.sidebar:
        st.header("Assumptions")
        st.markdown(
            "<p>If you know details of your current usage or tariff, enter below for greater accuracy</p>",
            unsafe_allow_html=True,
        )
        st.subheader("Current Performance")
        house = overwrite_house_assumptions(house)
    return house


def overwrite_house_assumptions(house: House):
    with st.expander("Demand"):
        house.envelope = overwrite_envelope_assumptions(envelope=house.envelope)
    with st.expander("Baseline heating system"):
        house.heating_system = overwrite_baseline_heating_system_assumptions(heating_system=house.heating_system)
    with st.expander("Tariff"):
        house.tariffs = overwrite_tariffs(tariffs=house.tariffs, fuel_name=house.heating_system.fuel.name)
    return house


def overwrite_envelope_assumptions(envelope: BuildingEnvelope) -> BuildingEnvelope:

    if "annual_heating_demand" not in st.session_state or st.session_state.heating_demand_set_by_dropdown is False:
        print("Set heating demand state from object")
        st.session_state.annual_heating_demand = int(envelope.annual_heating_demand)

    if "annual_base_demand" not in st.session_state or st.session_state.base_demand_set_by_dropdown is False:
        print("Set base demand state from object")
        st.session_state.annual_base_demand = int(envelope.base_demand.sum())

    envelope.annual_heating_demand = st.number_input(
        label="Space and water heating (kwh): ", min_value=0, max_value=100000, key="annual_heating_demand",
        on_change=flag_that_heating_demand_defined_by_dropdown
    )

    annual_base_demand_overwrite = st.number_input(
        label="Lighting, appliances, plug loads etc. (kwh): ", min_value=0, max_value=100000, key="annual_base_demand",
        on_change=flag_that_base_demand_defined_by_dropdown
    )
    if annual_base_demand_overwrite != int(envelope.base_demand.sum()):  # scale profile  by correction factor
        envelope.base_demand = annual_base_demand_overwrite / int(envelope.base_demand.sum()) * envelope.base_demand

    st.caption(
        f"A typical {envelope.house_type.lower()} home needs "
        f"{constants.BUILDING_TYPE_OPTIONS[envelope.house_type].annual_heat_demand_kWh:,} kWh for heating, "
        f"and {constants.BUILDING_TYPE_OPTIONS[envelope.house_type].annual_base_electricity_demand_kWh:,} "
        f"kWh for lighting, appliances, etc. "
        f"The better your home is insulated, the less energy it will need for heating. "
    )
    return envelope


def flag_that_heating_demand_defined_by_dropdown():
    st.session_state.heating_demand_set_by_dropdown = True


def flag_that_base_demand_defined_by_dropdown():
    st.session_state.base_demand_set_by_dropdown = True


def overwrite_baseline_heating_system_assumptions(heating_system: "HeatingSystem") -> "HeatingSystem":

    if ("baseline_heating_efficiency" not in st.session_state
            or st.session_state.baseline_heating_efficiency_set_by_dropdown is False):
        print("Set heating efficiency state from object")
        st.session_state.baseline_heating_efficiency = heating_system.efficiency

    heating_system.efficiency = st.number_input(
        label="Efficiency: ", min_value=0.1, max_value=8.0, key="baseline_heating_efficiency",
        on_change=flag_that_baseline_heating_efficiency_defined_by_dropdown)

    if heating_system.fuel.name == "gas":
        st.caption(
            "Many modern boilers have a low efficiency because they run at a high a flow temperature. "
            "Your boiler may be able to run at 90% or better but in most cases the flow temperature will be too high to "
            "achieve the boiler's stated efficiency. "
            "You can learn how to turn down your flow temperature "
            "[here](https://www.nesta.org.uk/project/lowering-boiler-flow-temperature-reduce-emissions)."
        )
    return heating_system


def flag_that_baseline_heating_efficiency_defined_by_dropdown():
    st.session_state.baseline_heating_efficiency_set_by_dropdown = True


def overwrite_tariffs(tariffs: Tariff, fuel_name: "str") -> Tariff:

    if "p_per_unit_elec_import" not in st.session_state:
        # Set initial values
        st.session_state.p_per_unit_elec_import = tariffs["electricity"].p_per_unit_import
        st.session_state.p_per_unit_elec_export = tariffs["electricity"].p_per_unit_export
        st.session_state.p_per_day_elec = tariffs["electricity"].p_per_day

    st.subheader("Electricity")
    tariffs["electricity"].p_per_unit_import = st.number_input(
        label="Unit rate (p/kwh), electricity import", min_value=0.0, max_value=100.0, key="p_per_unit_elec_import",
        value=constants.STANDARD_TARIFF.p_per_kwh_elec_import
    )
    tariffs["electricity"].p_per_unit_export = st.number_input(
        label="Unit rate (p/kwh), electricity export", min_value=0.0, max_value=100.0, key="p_per_unit_elec_export",
        value=constants.STANDARD_TARIFF.p_per_kwh_elec_export
    )
    tariffs["electricity"].p_per_day = st.number_input(
        label="Standing charge (p/day), electricity", min_value=0.0, max_value=100.0, key="p_per_day_elec",
        value=constants.STANDARD_TARIFF.p_per_day_elec
    )
    match fuel_name:
        case "gas":
            if ("p_per_unit_gas_import" not in st.session_state
                    or st.session_state.heating_fuel_tariff_defined_by_dropdown is False):
                # reset values when the overwrites do not apply
                st.session_state.fuel_name_tariffs_is_for = fuel_name
                st.session_state.p_per_unit_gas_import = tariffs["gas"].p_per_unit_import
                st.session_state.p_per_day_gas = tariffs["gas"].p_per_day

            st.subheader("Gas")
            tariffs["gas"].p_per_unit_import = st.number_input(
                label="Unit rate (p/kwh), gas", min_value=0.0, max_value=100.0, key="p_per_unit_gas_import",
                value=constants.STANDARD_TARIFF.p_per_kwh_gas,
                on_change=flag_that_heating_fuel_tariff_defined_by_dropdown
            )
            tariffs["gas"].p_per_day = st.number_input(
                label="Standing charge (p/day), gas", min_value=0.0, max_value=100.0, key="p_per_day_gas",
                value=constants.STANDARD_TARIFF.p_per_day_gas,
                on_change=flag_that_heating_fuel_tariff_defined_by_dropdown
            )
        case "oil":
            if ("p_per_unit_oil_import" not in st.session_state
                    or st.session_state.heating_fuel_tariff_defined_by_dropdown is False):
                # reset values when the overwrites do not apply
                st.session_state.fuel_name_tariffs_is_for = fuel_name
                st.session_state.p_per_unit_oil_import = tariffs["oil"].p_per_unit_import

            st.subheader("Oil")
            tariffs["oil"].p_per_unit_import = st.number_input(
                label="Oil price, (p/litre)", min_value=0.0, max_value=200.0, key="p_per_unit_oil_import",
                value=constants.STANDARD_TARIFF.p_per_L_oil,
                on_change=flag_that_heating_fuel_tariff_defined_by_dropdown
            )
    st.caption(
        "Our default tariffs reflect the [Energy Price Guarantee]("
        "https://www.gov.uk/government/publications/energy-bills-support/energy-bills-support-factsheet-8-september-2022)"
        ", but you can change them if you have fixed at a different rate."
    )
    return tariffs


def flag_that_heating_fuel_tariff_defined_by_dropdown():
    st.session_state.heating_fuel_tariff_defined_by_dropdown = True


def render_results(house: House):

    st.markdown(
        f"<div class='results-container'>"
        f"<p class='bill-label'>Your bill next year will be around <p>"
        f"<p class='bill-estimate'>£{int(house.total_annual_bill):,d}"
        f"</p>"
        f"<p class='bill-details'>Based on estimated usage of "
        f"<a class='bill-consumption-kwh' href='javascript:document.getElementsByClassName("
        f"{constants.CLASS_NAME_OF_SIDEBAR_DIV})[1].click();' target='_self'>"
        f"{int(house.total_annual_consumption_kwh):,d} kwh</a> </p>"
        f"</div>",
        unsafe_allow_html=True,
    )
