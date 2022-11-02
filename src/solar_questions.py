import streamlit as st

from constants import SolarConstants
import roof
from building_model import Solar


def render() -> 'Solar':

    st.header("How much solar power could you generate?")

    st.write(
        "Search for your home below and outline where you think solar panels might go. If you have"
        " multiple options, choose your most South facing roof.  "
    )
    polygons = roof.roof_mapper(800, 400)

    orientation: str = st.selectbox("Solar Orientation", SolarConstants.SOLAR_ORIENTATIONS)

    solar_install = Solar(orientation=orientation, roof_plan_area=polygons.area if polygons else 0)
    if polygons:
        st.write(f"We estimate you can fit {solar_install.number_of_panels} solar panels on your roof!")

    return solar_install


